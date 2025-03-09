"""
Bluesky Search

A package to search, fetch, and export posts from Bluesky social network.
"""

__version__ = "0.1.0"

from .client import BlueskyClient
from .fetcher import BlueskyPostsFetcher
from .search import BlueskySearch
from .list import BlueskyList
from .cli import main as cli_main

# Create an alias for backward compatibility with existing code
# This ensures any code importing BlueskyPostsFetcher from the original module will still work
BlueskyPosts = BlueskyPostsFetcher

__all__ = ["BlueskyClient", "BlueskyPostsFetcher", "BlueskySearch", "BlueskyList", "BlueskyPosts", "cli_main"]
