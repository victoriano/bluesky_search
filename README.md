# Bluesky Posts Fetcher

Este script permite obtener los posts recientes de una lista de usuarios de Bluesky (AT Protocol) y exportarlos en varios formatos.

## Características

- Autenticación segura con la API oficial de AT Protocol
- Obtención de posts de múltiples usuarios
- Personalización del número de posts a obtener por usuario
- **Búsqueda avanzada de posts** con múltiples criterios:
  - Búsqueda por palabras clave o frases
  - Filtrado por autor, menciones o idioma
  - Búsqueda por fechas o dominios
  - **Paginación automática** para obtener más de 100 posts (superando el límite de la API)
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
- `-b`, `--bsky-list`: URL de una lista de Bluesky
- `-n`, `--limit`: Número máximo de posts por usuario o búsqueda (predeterminado: 20, sin límite superior para búsquedas gracias a la paginación automática)
- `-o`, `--output`: Nombre del archivo de salida
- `-x`, `--format`: Formato de exportación (`json`, `csv`, o `parquet`, predeterminado: `json`)

#### Parámetros de búsqueda

- `-s`, `--search`: Buscar posts (usar comillas para frases exactas)
- `--from`: Buscar posts de un usuario específico
- `--mention`: Buscar posts que mencionan a un usuario específico
- `--lang`: Buscar posts en un idioma específico (ej: es, en, fr)
- `--since`: Buscar posts desde una fecha (formato: YYYY-MM-DD)
- `--until`: Buscar posts hasta una fecha (formato: YYYY-MM-DD)
- `--domain`: Buscar posts que contienen enlaces a un dominio específico

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

### Ejemplos de búsqueda

```bash
# Búsqueda simple por palabra clave
uv run bluesky_posts.py -s "inteligencia artificial" 

# Búsqueda de posts en inglés
uv run bluesky_posts.py -s "artificial intelligence" --lang en

# Búsqueda de posts de un usuario específico
uv run bluesky_posts.py -s "economía" --from usuario.bsky.social

# Búsqueda de posts que mencionan a un usuario
uv run bluesky_posts.py -s "eventos" --mention usuario.bsky.social

# Búsqueda por rango de fechas
uv run bluesky_posts.py -s "noticias" --since 2025-01-01 --until 2025-03-01

# Combinación de múltiples criterios
uv run bluesky_posts.py -s "política" --from periodista.bsky.social --lang es --limit 100 -x csv

# Búsqueda de posts que contienen enlaces a un dominio específico
uv run bluesky_posts.py -s "análisis" --domain ejemplo.com

# Obteniendo un gran número de posts (con paginación automática)
uv run bluesky_posts.py -s "Granada" --limit 500 -x csv

# Recopilando un conjunto de datos extenso de un tema
uv run bluesky_posts.py -s "clima" --since 2024-01-01 --limit 1000 -x parquet
```

### Paginación automática

El script soporta la obtención de más de 100 posts por búsqueda (límite de la API de Bluesky) mediante paginación automática. Al solicitar más de 100 posts:

- El sistema realizará múltiples llamadas a la API automáticamente
- Mostrará el progreso de cada llamada y el total de posts recopilados
- Combinará todos los resultados en un único conjunto de datos
- Incluirá breves pausas entre llamadas para no sobrecargar la API

### Formato del archivo de usuarios

Si prefieres usar un archivo con la lista de usuarios, simplemente crea un archivo de texto con un nombre de usuario por línea:

```
usuario1
usuario2
usuario3
```

### Entrada por consola

Si no proporcionas ningún parámetro de usuario o búsqueda, el script te pedirá introducir uno de los siguientes:

- Lista de usuarios separados por comas
- URL de una lista de Bluesky
- Búsqueda con el prefijo `buscar:` (ej: `buscar:inteligencia artificial`)

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
