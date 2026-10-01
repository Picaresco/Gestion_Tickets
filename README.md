# Gestion_Tickets

Gestor personal de tickets de incidencias y notas de trabajo. Cada nota es un **ticket** que avanza por una serie de **pasos**, y la app te dice en cada momento qué te toca hacer a ti y qué estás esperando de otros.

Es una web local sin dependencias: un servidor en Python (solo librería estándar) y una página HTML de un solo fichero. Los datos se guardan en ficheros JSON.

## Arranque rápido

Requisitos: Python 3.8 o superior.

```bash
python server.py
```

Abre <http://localhost:8791>. En Windows también puedes hacer doble clic en `iniciar.bat`, que arranca el servidor y abre el navegador.

| Variable de entorno | Por defecto | Uso |
|---|---|---|
| `PORT` | `8791` | Puerto del servidor |
| `HOST` | `127.0.0.1` | Dirección de escucha (`0.0.0.0` para exponerlo en la red o en Docker) |
| `DATA_DIR` | `./data` | Carpeta donde se guardan los datos |

> El servidor no tiene autenticación. Mantenlo en `127.0.0.1` o detrás de una red de confianza.

## Cómo funciona

### Tickets y pasos

Un ticket es una lista de pasos, en orden. Cada paso tiene un texto y un estado:

| Estado | Significado |
|---|---|
| **A realizar** | Te toca a ti. Es el estado del primer paso de todo ticket nuevo. |
| **Pendiente** | Esperas una acción de otra persona o empresa. |
| **Realizada** | El paso está hecho. |

Ejemplo de un ticket completo:

```
Enviado correo a Sage para comentar la actualización de SQL 2019          A realizar  -> Realizada
  Quedamos a la espera de respuesta                                       Pendiente   -> Realizada
  Me ha llamado Juan Luis con las opciones, que enviará por mail          Pendiente   -> Realizada
  He recibido presupuesto y tengo que revisarlo con dirección             A realizar  -> Realizada
  Decidimos ir a cloud por flexibilidad y ahorro, falta la firma          A realizar  -> Realizada (cerrado)
```

### Flujo

1. Escribe una nota en la caja superior y pulsa Enter. Se crea el ticket con su primer paso en **A realizar**.
2. Al marcar un paso **A realizar** como Realizada, la app pregunta: *¿hay más pasos?*
   - **Se acaba aquí**: el ticket se cierra y se oculta de la vista diaria.
   - **Hay más pasos**: aparece debajo una línea nueva, con sangría, para escribir el siguiente paso. Lo guardas como **A realizar** o como **Pendiente**.
3. Al marcar un paso **Pendiente** como Realizada (la otra parte ya ha actuado), se abre automáticamente la línea siguiente, vacía.
4. Si marcas **Realizada** en esa línea vacía sin escribir nada, el ticket se cierra.

Puedes cambiar un paso entre A realizar y Pendiente pulsando su etiqueta, editar su texto (✎) y reabrir (↩) o borrar (✕) un ticket. Estos botones aparecen al pasar el ratón por encima del ticket.

### Vista "Mi día"

Cabecera de libreta con una frase-resumen ("Tienes 4 cosas por hacer y 4 esperando respuesta; hoy toca reclamar 1") y pestañas **Todo / A realizar / Pendiente / Cerrados** (más **Contactos**), cada una con su contador. Los tickets que hay que reclamar salen siempre primero.

Cada ticket es una ficha numerada con el nombre de la empresa en el margen (la del contacto mencionado) y un borde de color según su estado: naranja (A realizar), ámbar (Pendiente), rojo (Reclamar) y verde (cerrado). La primera línea hace de título y el primer paso abierto lleva sus botones **Hecho** y **Pasar a Pendiente / A realizar** debajo. A la derecha hay una columna de paneles: los próximos 7 días, los recordatorios, los seguimientos programados y los contactos.

Con el tema claro u oscuro del sistema, la app cambia automáticamente de paleta (papel o cuaderno nocturno).

### Contraer y expandir

Los tickets con más de un paso tienen una flecha (▼) o se pliegan pulsando la cabecera. Plegado, se ve la primera línea, las etiquetas de estado y el texto del paso en curso ("Ahora → …"); desplegado, aparece la línea de tiempo con todos los pasos. Hay también botones **Contraer todo / Expandir todo**. El navegador recuerda lo que dejaste contraído.

### Fecha de seguimiento

Cada paso Pendiente puede llevar una fecha de seguimiento (selector de fecha en la línea, o "Recordar el" al crear el paso). Cuando llega ese día, el ticket sube a **Reclamar hoy** con una etiqueta roja, para que no se quede olvidado.

### Recordatorios

Notas sueltas para un día concreto que no son un ticket ("Cambiar la copia de seguridad"). Se crean en su panel con un texto y una fecha (por defecto, hoy). Los de hoy y los atrasados salen arriba en rojo, marcan un punto en "Próximos 7 días" y se suman a la frase de la cabecera. Al pasar el ratón aparecen **✓ Hecho** (lo quita de la vista y guarda la fecha en que se hizo), **✎** editar y **✕** borrar. No se repiten: cada recordatorio es para una sola fecha.

### Paneles laterales

Cada panel de la derecha tiene un botón **ocultar** en su esquina. Los ocultos se recuperan con **+ Añadir widget**, encima de la columna, y vuelven a su sitio. El navegador recuerda qué paneles ocultaste.

### Búsqueda

**Ctrl+K** (o `/`, o pulsar la caja de la cabecera) abre un buscador. Busca en todo el texto de los tickets, **incluidos los cerrados**, en los nombres de los archivos adjuntos y en los contactos:

- No distingue mayúsculas ni acentos.
- Un teléfono se encuentra aunque lo escribas con otro formato (`600 111 222`, `600111222`).
- Los tickets salen de más reciente a más antiguo, según la última actividad.
- Si buscas una empresa o una persona, salen también los tickets enlazados a sus contactos.
- Flechas y Enter para abrir; "Ver todos los resultados" muestra la lista completa.

### Archivos adjuntos

Cada ticket tiene un botón con un clip en la cabecera para **adjuntar archivos** (PDF, imágenes, Word, Excel, correos guardados, lo que sea) o puedes **arrastrarlos encima del ticket**. Se muestran como fichas (con miniatura si son imágenes); al pulsar una se abre en el navegador (PDF, imágenes y texto) o se descarga. Cada fichero puede pesar hasta 50 MB (`MAX_UPLOAD_MB`).

Los archivos se guardan en `data/files/<ticket>/`; los datos del ticket solo guardan su nombre y tamaño. Si haces copia de la carpeta `data/`, llevas también los adjuntos. El botón **Exportar** del pie descarga solo el JSON de tickets y contactos, sin los ficheros adjuntos.

### Contactos

La pestaña **Contactos** guarda nombre, empresa, puesto, teléfono y correo, agrupados por empresa. Cada contacto muestra los tickets en los que aparece.

- **Mencionar con `@`**: en cualquier nota o paso, escribe `@Juan` y aparece la lista de todos los Juan, con empresa, teléfono y correo. `@sage` muestra todos los contactos de Sage. Se elige con las flechas y Enter (o con el ratón). La mención queda como una etiqueta azul; al pulsarla se abre el contacto.
- **Alta automática**: al guardar una nota con un teléfono o correo que no tengas, se abre un formulario ya relleno. Con "he hablado con Laura de Fortinet al 699 888 777" propone *Laura*, *Fortinet* y el teléfono (y si hay correo, deduce la empresa del dominio). Confirmas o corriges. Funciona con reglas, sin IA y sin conexión a internet.

### Copias de seguridad

- Se guarda una copia automática al día en `data/backups/backup-AAAA-MM-DD.json` (la primera del día y al arrancar). Se conservan las últimas 30.
- **Exportar** descarga todos los tickets, contactos y recordatorios en un único JSON.
- **Importar** restaura desde ese fichero, reemplazando los datos actuales (los adjuntos no viajan en el JSON: copia `data/files/` aparte). Antes guarda una copia `pre-import-*.json` por si te arrepientes.

## Estructura

```
server.py          Servidor HTTP (librería estándar) y API JSON
static/index.html  Toda la interfaz (HTML + CSS + JS)
data/              Datos: tickets.json, contacts.json, reminders.json, files/, backups/   (no se sube al repo)
iniciar.bat        Arranque en Windows
```

### API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/tickets`, `/api/contacts`, `/api/reminders` | Lista completa |
| PUT | `/api/tickets/<id>`, `/api/contacts/<id>`, `/api/reminders/<id>` | Crea o reemplaza un elemento |
| DELETE | `/api/tickets/<id>`, `/api/contacts/<id>`, `/api/reminders/<id>` | Borra un elemento |
| POST | `/api/tickets/<id>/files?name=<nombre>` | Adjunta un archivo (cuerpo = bytes del fichero) |
| GET | `/api/files/<ticket>/<archivo>` | Abre o descarga un adjunto |
| DELETE | `/api/tickets/<id>/files/<archivo>` | Quita un adjunto |
| GET | `/api/export` | Descarga todo en un JSON |
| POST | `/api/import` | Restaura desde un JSON exportado |

### Modelo de datos

```jsonc
// ticket
{ "id": "...", "created": "ISO", "updated": "ISO", "closed": null,
  "lines": [ { "text": "...", "status": "A realizar|Pendiente|Realizada",
               "created": "ISO", "done": null, "remind": "AAAA-MM-DD", "contacts": ["id"] } ],
  "files": [ { "id": "...", "name": "presupuesto.pdf", "size": 12345, "type": "application/pdf", "added": "ISO" } ] }
// contacto
{ "id": "...", "name": "", "company": "", "role": "", "phone": "", "email": "" }
// recordatorio
{ "id": "...", "text": "...", "date": "AAAA-MM-DD", "created": "ISO", "done": null }
```

## Hoja de ruta

- Dockerfile / docker-compose.
- Deshacer y más atajos de teclado.
- Incluir los adjuntos en la exportación (ZIP).

### Ideas con IA (pendientes, opcionales)

Todas serían opcionales: se activarían con una variable de entorno (`ANTHROPIC_API_KEY`) y, sin ella, la app funciona como ahora. Bastaría un modelo pequeño (coste de céntimos al mes) y solo se enviaría el texto de la nota o del ticket consultado, nunca toda la base de datos. Como alternativa sin nube se podría usar un modelo local.

1. **Captura inteligente de notas**: escribir texto libre ("hablé con Juan de Sage, me llama el jueves con el precio") y que la IA proponga el contacto (nombre, empresa, puesto, teléfono, correo), el estado del paso (A realizar / Pendiente) y la fecha de seguimiento. El usuario solo confirma. Sustituye a las reglas actuales de detección.
2. **Pegar un correo y crear el ticket**: a partir de un correo o hilo, generar el ticket con los pasos resumidos, los contactos de la firma y el correo original como adjunto.
3. **Borrador de correo para "Reclamar hoy"**: un botón que redacta el correo de seguimiento con el contexto del ticket, para revisarlo y enviarlo a mano (nunca se envía solo).
4. **Preguntar a las notas**: consultas en lenguaje natural ("¿en qué quedamos con Fortinet?", "¿qué tengo abierto con Sage?").
5. **Leer los adjuntos**: extraer importe, fecha y proveedor de PDFs de presupuestos y añadirlo como paso.
6. **Resumen de la mañana**: un párrafo con lo prioritario del día.

Orden recomendado: 1, 2 y 3 primero; la 4 cuando haya muchas notas.
