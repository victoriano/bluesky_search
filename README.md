# Bluesky Search

A Python package for retrieving, searching, and exporting posts from Bluesky (AT Protocol) social network.

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

### Development Installation

```bash
# Clone the repository
git clone https://github.com/your-username/bluesky-search.git
cd bluesky-search

# Using uv (recommended)
uv venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install in development mode
uv pip install -e .

# Alternative with pip
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
pip install -e .
```

### Regular Installation (once published to PyPI)

```bash
# Using uv
uv pip install bluesky-search

# Using pip
pip install bluesky-search
```

## Usage

### As a Command Line Tool

The package includes a command-line interface for easy access to all functionality:

```bash
# Run directly after installation
bluesky-search --help

# Or from the source directory
python -m src.bluesky_search.cli --help
```

### Programmatic Usage

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with authentication
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Get posts from a user
posts = fetcher.get_user_posts("username.bsky.social", limit=20)

# Search for posts
search_results = fetcher.search_posts("keyword", limit=50)

# Export results
fetcher.export_to_json(posts, "output.json")
fetcher.export_to_csv(posts, "output.csv")
fetcher.export_to_parquet(posts, "output.parquet")
```

### Command Line Parameters

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
bluesky-search -u your_username -p your_password -a user1.bsky.social

# Get posts from users in a file
bluesky-search -u your_username -p your_password -f users.txt

# Specify post limit per user and output file
bluesky-search -u your_username -p your_password -a user1.bsky.social -n 50 -o results.json

# Using the CLI with export to CSV
bluesky-search -a user.bsky.social -e csv -o user_posts.csv

# Export to Parquet format
bluesky-search -a user.bsky.social -e parquet -o my_posts.parquet
```

## Complete Search Guide

The script offers multiple ways to search and retrieve Bluesky posts. Here are all available options:

### 1. User Post Retrieval

```bash
# Get posts from specific user
bluesky-search -a user.bsky.social

# Load users from file
bluesky-search -f users.txt

# Limit posts per user
bluesky-search -a user.bsky.social -n 50
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Get posts from a single user
posts = fetcher.get_user_posts("user.bsky.social", limit=50)

# Process the posts
for post in posts:
    print(f"Post from {post['author']['handle']}: {post['text'][:50]}...")

# Export the results
fetcher.export_to_json(posts, "user_posts.json")
```

### 2. Bluesky List Retrieval

```bash
# Get posts from all users in a Bluesky list
bluesky-search -l https://bsky.app/profile/user.bsky.social/lists/123abc

# Limit posts per list user
bluesky-search -l https://bsky.app/profile/user.bsky.social/lists/123abc -n 30
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Get posts from a Bluesky list
list_url = "https://bsky.app/profile/user.bsky.social/lists/123abc"
list_posts = fetcher.get_list_posts(list_url, limit=30)

# Export the results
fetcher.export_to_csv(list_posts, "list_posts.csv")
```

### 3. Keyword Search

```bash
# Simple keyword/phrase search
bluesky-search -s "artificial intelligence"

# Limit search results
bluesky-search -s "artificial intelligence" -n 50
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Search for posts with a keyword
search_results = fetcher.search_posts("artificial intelligence", limit=50)

# Print number of results
print(f"Found {len(search_results)} posts about AI")

# Export the results
fetcher.export_to_parquet(search_results, "ai_posts.parquet")
```

### 4. Filtered Search

```bash
# Filter by language
bluesky-search -s "inteligencia artificial" --language es
bluesky-search -s "artificial intelligence" --language en

# Filter by author (posts from specific user)
bluesky-search -s "economics" --from economist.bsky.social

# Filter by mentions (posts mentioning user)
bluesky-search -s "event" --mention organizer.bsky.social

# Date range filter
bluesky-search -s "news" --since 2025-01-01 --until 2025-01-31

# Domain filter
bluesky-search -s "analysis" --domain example.com
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Advanced search with filters
results = fetcher.search_posts(
    "economics",
    limit=100,
    from_user="economist.bsky.social",
    since="2025-01-01",
    until="2025-01-31",
    language="en"
)

# Export the results
fetcher.export_to_csv(results, "economics_articles.csv")
```

### 5. Combined Filters

```bash
# Combine multiple filters in one search
bluesky-search -s "politics" --from journalist.bsky.social --language es --since 2025-02-01

# Advanced multi-criteria search with specific export
bluesky-search -s "elections" --language es --since 2025-01-01 --until 2025-02-29 --domain news.com -n 200 -e csv -o elections_2025.csv
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Complex search with multiple filters
results = fetcher.search_posts(
    query="elections",
    limit=200,
    language="es",
    since="2025-01-01",
    until="2025-02-29",
    domain="news.com"
)

# Export directly to CSV
fetcher.export_to_csv(results, "elections_2025.csv")
```

### 6. Pagination for Large Datasets

```bash
# Get large number of posts (500+) with auto-pagination
bluesky-search -s "Granada" -n 500 -e csv -o granada_posts.csv

# Build extensive dataset on a topic
bluesky-search -s "climate" --since 2024-01-01 -n 1000 -e parquet -o climate_dataset.parquet
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Large-scale search with automatic pagination
big_dataset = fetcher.search_posts("climate", limit=1000, since="2024-01-01")
print(f"Collected {len(big_dataset)} posts about climate")

# Export as Parquet for efficient storage and analysis
fetcher.export_to_parquet(big_dataset, "climate_dataset.parquet")
```

### 7. Export Formats

```bash
# Export to JSON (default format)
bluesky-search -s "sports" -o sports.json

# Export to CSV for spreadsheet analysis
bluesky-search -s "sports" -e csv -o sports.csv

# Export to Parquet for big data analysis
bluesky-search -s "sports" -e parquet -o sports.parquet
```

Using the Python API:

```python
from src.bluesky_search import BlueskyPostsFetcher

# Initialize with your credentials
fetcher = BlueskyPostsFetcher(username="your_username", password="your_password")

# Get posts to export
sports_posts = fetcher.search_posts("sports", limit=100)

# Export in multiple formats
fetcher.export_to_json(sports_posts, "sports.json")
fetcher.export_to_csv(sports_posts, "sports.csv")
fetcher.export_to_parquet(sports_posts, "sports.parquet")
```

## Running Manual Queries During Development

During development or for ad-hoc analysis, you can run manual queries directly from the command line without installing the package. This is useful for quick data exploration, testing new search parameters, or during the development process.

### Using the `uv run` Command

`uv` is a fast Python package installer and resolver that can also run Python modules directly. This is ideal for development usage:

```bash
# Basic search query
uv run -m src.bluesky_search.cli -u your_username -p your_password -s "search term" -n 100

# Search with export to parquet
uv run -m src.bluesky_search.cli -u your_username -p your_password -s "search term" -n 350 -e parquet -o results.parquet

# Search with legacy -x parameter for export format
uv run -m src.bluesky_search.cli -u your_username -p your_password -s "search term" -n 350 -x parquet -o results.parquet
```

### Using `python -m` Command

Alternatively, you can use Python's module execution capability:

```bash
# Using python -m
python -m src.bluesky_search.cli -u your_username -p your_password -s "search term" -n 100 -e json -o results.json
```

### Tips for Manual Queries

- Add the `-o` parameter to specify the output file name, otherwise a timestamped file will be generated automatically
- Include the `-n` parameter to control the number of results (especially useful for large searches)
- Use quotes around search terms containing spaces or special characters
- For regular usage of the tool, consider installing it in development mode with `uv pip install -e .` or `pip install -e .`
- When searching for a large number of posts, use progress indicators in the terminal output to monitor the collection process

## Package Structure

The package is organized into logical modules:

```
bluesky_search/
├── src/
│   └── bluesky_search/
│       ├── __init__.py          # Package exports
│       ├── client.py            # Base client functionality
│       ├── fetcher.py           # Post fetching functionality
│       ├── search.py            # Search functionality
│       ├── list.py              # List handling functionality
│       ├── cli.py               # Command-line interface
│       ├── export/              # Export utilities
│       │   ├── __init__.py
│       │   ├── json.py          # JSON export
│       │   ├── csv.py           # CSV export
│       │   └── parquet.py       # Parquet export
│       └── utils/               # Utility functions
│           ├── __init__.py
│           ├── url.py           # URL handling
│           └── text.py          # Text processing
├── test/                        # Test suite
└── pyproject.toml              # Package configuration
```

### Advanced Features

#### Automatic Pagination

The package supports retrieving more than 100 posts per search (Bluesky API limit) through automatic pagination:

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

### Export Formats Specification

All export formats (CSV, JSON, and Parquet) maintain the exact same column order and structure for consistency across different output formats. This allows for easy switching between formats based on your specific needs.

#### Exact Column Order

All exports follow this precise column order:

1. `user_handle` - The handle under which the post was found (useful for search results)
2. `author_handle` - The post author's handle
3. `author_display_name` - The post author's display name
4. `created_at` - Timestamp when the post was created
5. `post_type` - Type of post (original, reply, repost, etc.)
6. `text` - The main text content of the post
7. `web_url` - URL to view the post on Bluesky's web interface
8. `likes` - Number of likes the post has received
9. `reposts` - Number of reposts the post has received
10. `replies` - Number of replies the post has received
11. `urls` - Array of URLs mentioned in the post
12. `images` - Array of image URLs in the post
13. `mentions` - Array of user mentions in the post
14. `lang` - Language of the post (e.g., 'en' for English)
15. `cid` - Content identifier for the post
16. `author_did` - Decentralized identifier for the post author
17. `uri` - AT Protocol URI for the post

#### Format-Specific Details

##### CSV Export
- Array fields (`urls`, `images`, `mentions`) are preserved as JSON-formatted arrays in string form
- Example: `["https://example.com", "https://another-example.com"]`
- Requires the `polars` package

##### JSON Export
- Maintains native array formats for `urls`, `images`, and `mentions`
- Preserves the nested dictionary structure where each key is an author handle
- Empty arrays are preserved as `[]` rather than being omitted

##### Parquet Export
- Array fields (`urls`, `images`, `mentions`) are stored as JSON-formatted array strings
- Example: `["https://example.com", "https://another-example.com"]`
- Consistent format across CSV and Parquet exports for easier data integration
- Most efficient for analytical workloads and data science pipelines
- Requires the `polars` package
