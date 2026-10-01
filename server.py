# -*- coding: utf-8 -*-
"""Servidor local del gestor de tickets. Solo libreria estandar.

Datos en data/tickets.json, data/contacts.json y data/reminders.json. Variables de entorno: PORT (8791), HOST (127.0.0.1),
DATA_DIR (./data) para cuando se pase a Docker.
"""
import json
import mimetypes
import os
import re
import shutil
import threading
import time
import uuid
from urllib.parse import parse_qs, quote, unquote, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE, "data"))
COLLECTIONS = ("tickets", "contacts", "reminders")
LOCK = threading.Lock()
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
KEEP_DAILY = 30
FILES_DIR = os.path.join(DATA_DIR, "files")
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD_MB", "50")) * 1024 * 1024
# tipos que el navegador puede mostrar sin riesgo; el resto (html, svg, js...) se descarga
INLINE_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp", "text/plain"}


def load(col):
    path = os.path.join(DATA_DIR, col + ".json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(col, items):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, col + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def safe_name(name):
    name = os.path.basename((name or "archivo").replace("\\", "/"))
    name = re.sub(r"[^\w.\- ()\u00C0-\u017F]", "_", name).strip(" .") or "archivo"
    return name[:120]


def file_path(tid, fid, name):
    return os.path.join(FILES_DIR, tid, fid + "_" + name)


def snapshot(name=None):
    """Copia de seguridad: una por dia (la primera del dia) o con nombre explicito."""
    name = name or "backup-%s.json" % time.strftime("%Y-%m-%d")
    path = os.path.join(BACKUP_DIR, name)
    if os.path.exists(path):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({c: load(c) for c in COLLECTIONS}, f, ensure_ascii=False)
    daily = sorted(n for n in os.listdir(BACKUP_DIR) if n.startswith("backup-"))
    for old in daily[:-KEEP_DAILY]:
        os.remove(os.path.join(BACKUP_DIR, old))


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self):
        m = re.fullmatch(r"/api/(tickets|contacts|reminders)/([\w-]+)", self.path)
        return (m.group(1), m.group(2)) if m else (None, None)

    def do_GET(self):
        m = re.fullmatch(r"/api/(tickets|contacts|reminders)", self.path)
        if m:
            with LOCK:
                return self._json(load(m.group(1)))
        m = re.fullmatch(r"/api/files/([\w-]+)/([\w-]+)", self.path.split("?")[0])
        if m:
            return self._serve_file(m.group(1), m.group(2))
        if self.path == "/api/export":
            with LOCK:
                data = {"exported": time.strftime("%Y-%m-%d %H:%M:%S")}
                data.update({c: load(c) for c in COLLECTIONS})
            body = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="tickets-%s.json"' % time.strftime("%Y-%m-%d"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json({"error": "no encontrado"}, 404)

    def _serve_file(self, tid, fid):
        with LOCK:
            t = next((x for x in load("tickets") if x["id"] == tid), None)
            meta = next((f for f in (t or {}).get("files", []) if f["id"] == fid), None)
        path = file_path(tid, fid, meta["name"]) if meta else None
        if not path or not os.path.isfile(path):
            return self._json({"error": "archivo no encontrado"}, 404)
        ctype = meta.get("type") or mimetypes.guess_type(meta["name"])[0] or "application/octet-stream"
        if ctype == "text/plain":
            ctype = "text/plain; charset=utf-8"
        inline = ctype.split(";")[0] in INLINE_TYPES
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype if inline else "application/octet-stream")
        self.send_header("Content-Disposition", "%s; filename*=UTF-8''%s" % (
            "inline" if inline else "attachment", quote(meta["name"])))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _upload(self, tid):
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return self._json({"error": "fichero vacio"}, 400)
        if n > MAX_UPLOAD:
            return self._json({"error": "supera el maximo de %d MB" % (MAX_UPLOAD // 1048576)}, 413)
        name = safe_name(unquote(parse_qs(urlparse(self.path).query).get("name", ["archivo"])[0]))
        data = self.rfile.read(n)
        with LOCK:
            tickets = load("tickets")
            t = next((x for x in tickets if x["id"] == tid), None)
            if not t:
                return self._json({"error": "ticket no encontrado"}, 404)
            snapshot()
            fid = uuid.uuid4().hex[:12]
            path = file_path(tid, fid, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            meta = {"id": fid, "name": name, "size": len(data),
                    "type": self.headers.get("Content-Type", "") or mimetypes.guess_type(name)[0] or "",
                    "added": time.strftime("%Y-%m-%dT%H:%M:%S")}
            t.setdefault("files", []).append(meta)
            t["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            save("tickets", tickets)
        self._json(meta)

    def do_POST(self):
        m = re.fullmatch(r"/api/tickets/([\w-]+)/files", self.path.split("?")[0])
        if m:
            return self._upload(m.group(1))
        if self.path != "/api/import":
            return self._json({"error": "ruta invalida"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            tickets, contacts, reminders = data["tickets"], data.get("contacts", []), data.get("reminders", [])
            assert isinstance(tickets, list) and isinstance(contacts, list) and isinstance(reminders, list)
            assert all(isinstance(x, dict) and x.get("id") for x in tickets + contacts + reminders)
        except (ValueError, KeyError, AssertionError, TypeError):
            return self._json({"error": "fichero de copia invalido"}, 400)
        with LOCK:
            snapshot("pre-import-%s.json" % time.strftime("%Y-%m-%d-%H%M%S"))
            save("tickets", tickets)
            save("contacts", contacts)
            save("reminders", reminders)
        self._json({"ok": True, "tickets": len(tickets), "contacts": len(contacts), "reminders": len(reminders)})

    def do_PUT(self):
        col, tid = self._route()
        if not tid:
            return self._json({"error": "ruta invalida"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            ticket = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return self._json({"error": "json invalido"}, 400)
        ticket["id"] = tid
        with LOCK:
            snapshot()
            items = load(col)
            for i, t in enumerate(items):
                if t["id"] == tid:
                    if col == "tickets" and "files" in t:
                        ticket["files"] = t["files"]
                    items[i] = ticket
                    break
            else:
                items.append(ticket)
            save(col, items)
        self._json({"ok": True})

    def do_DELETE(self):
        m = re.fullmatch(r"/api/tickets/([\w-]+)/files/([\w-]+)", self.path)
        if m:
            tid, fid = m.groups()
            with LOCK:
                tickets = load("tickets")
                t = next((x for x in tickets if x["id"] == tid), None)
                meta = next((f for f in (t or {}).get("files", []) if f["id"] == fid), None)
                if not meta:
                    return self._json({"error": "archivo no encontrado"}, 404)
                snapshot()
                t["files"] = [f for f in t["files"] if f["id"] != fid]
                save("tickets", tickets)
                try:
                    os.remove(file_path(tid, fid, meta["name"]))
                except OSError:
                    pass
            return self._json({"ok": True})
        col, tid = self._route()
        if not tid:
            return self._json({"error": "ruta invalida"}, 404)
        with LOCK:
            snapshot()
            save(col, [t for t in load(col) if t["id"] != tid])
            if col == "tickets":
                shutil.rmtree(os.path.join(FILES_DIR, tid), ignore_errors=True)
        self._json({"ok": True})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8791"))
    with LOCK:
        snapshot()
    print("Gestor de tickets en http://%s:%d" % (host, port))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
