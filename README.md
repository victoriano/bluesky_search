# Bluesky Posts Fetcher

Este script permite obtener los posts recientes de una lista de usuarios de Bluesky (AT Protocol) y exportarlos en varios formatos.

## Características

- Autenticación segura con la API oficial de AT Protocol
- Obtención de posts de múltiples usuarios
- Personalización del número de posts a obtener por usuario
- Exportación de resultados en múltiples formatos:
  - JSON (estructurado por usuario)
  - CSV (datos aplanados para análisis)
  - Parquet (optimizado para big data)

## Requisitos

- Python 3.8 o superior
- Biblioteca `atproto`
- Biblioteca `polars` (para exportación CSV/Parquet)

## Instalación

### Usando uv (recomendado)

```bash
# Crear y activar un entorno virtual con uv
uv venv

# Activar el entorno virtual
source .venv/bin/activate  # En Linux/macOS
# o
.venv\Scripts\activate     # En Windows

# Instalar dependencias con uv
uv pip install -r requirements.txt
```

### Método alternativo (pip)

```bash
# Crear un entorno virtual
python -m venv venv

# Activar el entorno virtual
source venv/bin/activate  # En Linux/macOS
# o
venv\Scripts\activate     # En Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Parámetros disponibles

- `-u`, `--username`: Nombre de usuario o correo electrónico para autenticación
- `-p`, `--password`: Contraseña para autenticación
- `-f`, `--file`: Archivo con lista de usuarios (uno por línea)
- `-l`, `--list`: Lista de usuarios separados por espacios
- `-n`, `--limit`: Número máximo de posts por usuario (predeterminado: 20)
- `-o`, `--output`: Nombre del archivo de salida
- `-x`, `--format`: Formato de exportación (`json`, `csv`, o `parquet`, predeterminado: `json`)

### Ejemplos

```bash
# Obtener posts de usuarios específicos
python bluesky_posts.py -u tu_usuario -p tu_contraseña -l usuario1 usuario2 usuario3

# Obtener posts de usuarios desde un archivo
python bluesky_posts.py -u tu_usuario -p tu_contraseña -f usuarios.txt

# Especificar el límite de posts por usuario y el archivo de salida
python bluesky_posts.py -u tu_usuario -p tu_contraseña -l usuario1 usuario2 -n 50 -o resultados.json

# Usando el entorno virtual con uv y exportando a CSV
uv run bluesky_posts.py -x csv

# Exportando a formato Parquet
uv run bluesky_posts.py -x parquet -o mis_posts.parquet
```

### Formato del archivo de usuarios

Si prefieres usar un archivo con la lista de usuarios, simplemente crea un archivo de texto con un nombre de usuario por línea:

```
usuario1
usuario2
usuario3
```

## Formatos de salida

### JSON
El script genera un archivo JSON con la siguiente estructura:

```json
{
  "usuario1": [
    {
      "uri": "at://...",
      "cid": "...",
      "author": {
        "did": "did:plc:...",
        "handle": "usuario1",
        "display_name": "Nombre mostrado"
      },
      "text": "Contenido del post",
      "created_at": "2023-...",
      "likes": 5,
      "reposts": 2,
      "replies": 3
    },
    ...
  ],
  "usuario2": [
    ...
  ]
}
```

### CSV y Parquet
Los formatos CSV y Parquet contienen una estructura aplanada con las siguientes columnas:

- `user_handle`: Handle del usuario (nombre de usuario con dominio)
- `post_uri`: URI completo del post
- `post_cid`: CID único del post
- `author_did`: DID del autor
- `author_handle`: Handle del autor
- `author_display_name`: Nombre mostrado del autor
- `text`: Contenido de texto del post
- `created_at`: Fecha y hora de creación
- `likes`: Número de likes
- `reposts`: Número de reposts
- `replies`: Número de respuestas
- `images`: Imágenes adjuntas (si existen)
