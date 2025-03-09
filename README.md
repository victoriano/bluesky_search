# Bluesky Posts Fetcher

This script retrieves recent posts from Bluesky (AT Protocol) users and exports them in multiple formats.

## Features

- Secure authentication with official AT Protocol API
- Post retrieval from multiple users
- Customizable number of posts per user
- **Advanced post search** with multiple criteria:
  - Keyword/phrase search
  - Filter by author, mentions, or language
  - Date range filtering
  - Domain filtering
  - **Automatic pagination** to retrieve beyond 100-post API limit
- Multiple export formats:
  - JSON (structured by user)
  - CSV (flattened for analysis)
  - Parquet (optimized for big data)

## Requirements

- Python 3.8+
- `atproto` library
- `polars` library (for CSV/Parquet export)

## Installation

### Using uv (recommended)

```bash
# Create and activate virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
```

### Alternative Method (pip)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Available Parameters

- `-u`, `--username`: Username/email for authentication
- `-p`, `--password`: Password for authentication
- `-f`, `--file`: File containing user list (one per line)
- `-l`, `--list`: Space-separated list of users
- `-b`, `--bsky-list`: Bluesky list URL
- `-n`, `--limit`: Max posts per user/search (default: 20, no upper limit for searches)
- `-o`, `--output`: Output filename
- `-x`, `--format`: Export format (`json`, `csv`, or `parquet`, default: `json`)

#### Search Parameters

- `-s`, `--search`: Search posts (use quotes for exact phrases)
- `--from`: Search posts from specific user
- `--mention`: Search posts mentioning specific user
- `--lang`: Search posts in specific language (e.g., es, en, fr)
- `--since`: Search posts from date (YYYY-MM-DD)
- `--until`: Search posts until date (YYYY-MM-DD)
- `--domain`: Search posts containing links to specific domain

### Examples

```bash
# Get posts from specific users
python bluesky_posts.py -u your_username -p your_password -l user1 user2 user3

# Get posts from users in a file
python bluesky_posts.py -u your_username -p your_password -f users.txt

# Specify post limit per user and output file
python bluesky_posts.py -u your_username -p your_password -l user1 user2 -n 50 -o results.json

# Using uv virtual environment and export to CSV
uv run bluesky_posts.py -x csv

# Export to Parquet format
uv run bluesky_posts.py -x parquet -o my_posts.parquet
```

## Complete Search Guide

The script offers multiple ways to search and retrieve Bluesky posts. Here are all available options:

### 1. User Post Retrieval

```bash
# Get posts from specific user
uv run bluesky_posts.py -l user.bsky.social

# Get posts from multiple users
uv run bluesky_posts.py -l user1.bsky.social user2.bsky.social user3.bsky.social

# Limit posts per user
uv run bluesky_posts.py -l user.bsky.social -n 50

# Load users from file
uv run bluesky_posts.py -f users.txt
```

### 2. Bluesky List Retrieval

```bash
# Get posts from all users in a Bluesky list
uv run bluesky_posts.py -b https://bsky.app/profile/user.bsky.social/lists/123abc

# Limit posts per list user
uv run bluesky_posts.py -b https://bsky.app/profile/user.bsky.social/lists/123abc -n 30
```

### 3. Keyword Search

```bash
# Simple keyword/phrase search
uv run bluesky_posts.py -s "artificial intelligence"

# Limit search results
uv run bluesky_posts.py -s "artificial intelligence" -n 50
```

### 4. Filtered Search

```bash
# Filter by language
uv run bluesky_posts.py -s "inteligencia artificial" --lang es
uv run bluesky_posts.py -s "artificial intelligence" --lang en

# Filter by author (posts from specific user)
uv run bluesky_posts.py -s "economics" --from economist.bsky.social

# Filter by mentions (posts mentioning user)
uv run bluesky_posts.py -s "event" --mention organizer.bsky.social

# Date range filter
uv run bluesky_posts.py -s "news" --since 2025-01-01 --until 2025-01-31

# Domain filter
uv run bluesky_posts.py -s "analysis" --domain example.com
```

### 5. Combined Filters

```bash
# Combine multiple filters in one search
uv run bluesky_posts.py -s "politics" --from journalist.bsky.social --lang es --since 2025-02-01

# Advanced multi-criteria search with specific export
uv run bluesky_posts.py -s "elections" --lang es --since 2025-01-01 --until 2025-02-29 --domain news.com -n 200 -x csv -o elections_2025.csv
```

### 6. Pagination for Large Datasets

```bash
# Get large number of posts (500+) with auto-pagination
uv run bluesky_posts.py -s "Granada" --limit 500 -x csv

# Build extensive dataset on a topic
uv run bluesky_posts.py -s "climate" --since 2024-01-01 --limit 1000 -x parquet -o climate_dataset.parquet
```

### 7. Export Formats

```bash
# Export to JSON (default format)
uv run bluesky_posts.py -s "sports" -o sports.json

# Export to CSV for spreadsheet analysis
uv run bluesky_posts.py -s "sports" -x csv -o sports.csv

# Export to Parquet for big data analysis
uv run bluesky_posts.py -s "sports" -x parquet -o sports.parquet
```

### Advanced Features

#### Automatic Pagination

The script supports retrieving more than 100 posts per search (Bluesky API limit) through automatic pagination:

- Makes multiple API calls automatically
- Shows progress for each call and total collected posts
- Combines results into single dataset
- Includes brief pauses between calls to avoid API overload

#### Web URLs for Posts

All retrieved posts include web URLs for direct browser access:

- Format: `https://bsky.app/profile/user.bsky.social/post/identifier`
- Included in all export formats (JSON, CSV, Parquet)
- Enables direct verification and access to original posts

#### Example web_url in exported data:

```
https://bsky.app/profile/user.bsky.social/post/3abc123xyz
```

This allows easy verification of any post from exported data.

### User File Format

Create a text file with one username per line:

```
user1
user2
user3
```

### Console Input

If no parameters are provided, the script will prompt for:

- Comma-separated list of users
- Bluesky list URL
- Search query with `search:` prefix (e.g., `search:artificial intelligence`)

## Output Formats

### JSON
Structured output format:

```json
{
  "user1": [
    {
      "uri": "at://...",
      "cid": "...",
      "web_url": "https://bsky.app/profile/user.bsky.social/post/abc123",
      "author": {
        "did": "did:plc:...",
        "handle": "user1",
        "display_name": "Display Name"
      },
      "text": "Post content",
      "created_at": "2025-...",
      "likes": 5,
      "reposts": 2,
      "replies": 3
    },
    ...
  ]
}
```

### CSV & Parquet
Flattened structure with columns:

- `user_handle`: User's handle
- `post_uri`: AT Protocol post URI
- `post_web_url`: Web URL for direct access
- `post_cid`: Unique post CID
- `author_did`: Author's DID
- `author_handle`: Author's handle
- `author_display_name`: Author's display name
- `text`: Post content
- `created_at`: Creation timestamp
- `likes`: Like count
- `reposts`: Repost count
- `replies`: Reply count
- `images`: Attached images (if any)
