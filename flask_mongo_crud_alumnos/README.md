# Proyecto: Flask + MongoDB (CRUD de Alumnos)

Proyecto educativo para que los alumnos experimenten con Flask (Python) y MongoDB (NoSQL).
La app provee un CRUD (Crear, Leer, Actualizar, Borrar) para la colección `alumnos`.

## Estructura principal
```
flask_mongo_crud_alumnos/
├── app.py
├── requirements.txt
├── seed.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── create.html
│   ├── edit.html
│   └── view.html
└── static/
    └── style.css
```

## Requisitos
- Python 3.8+
- MongoDB corriendo localmente en `mongodb://localhost:27017/`
- Visual Studio Code (recomendado) o cualquier editor

## Instalación paso a paso

1. Crear y activar entorno virtual:
   - Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. (Opcional) Ejecutar `seed.py` para poblar datos de ejemplo:
   ```bash
   python seed.py
   ```

4. Iniciar la aplicación:
   ```bash
   python app.py
   ```
   Abrir en el navegador: `http://127.0.0.1:5000`

## Explicación del código (resumida)

- `app.py`:
  - Conecta a MongoDB usando `pymongo.MongoClient`.
  - Rutas principales:
    - `/` - lista de alumnos.
    - `/alumnos/new` - formulario para crear.
    - `/alumnos/<id>` - (opcional) ver un alumno.
    - `/alumnos/edit/<id>` - editar.
    - `/alumnos/delete/<id>` - eliminar (POST).
  - Manejo simple de conversiones (edad a int, promedio a float) y conversión de `_id` a string cuando se pasa a templates.

- `seed.py`:
  - Población rápida de la colección `alumnos` con ejemplos.


