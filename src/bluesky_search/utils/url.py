#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
URL utilities for Bluesky Search.

This module contains functions for handling URLs and URIs related to Bluesky.
"""

import re
from typing import Dict, Optional

def get_web_url_from_uri(uri: str, author_handle: str) -> Optional[str]:
    """
    Convert an AT Protocol URI to a web URL visible in a browser.
    
    Args:
        uri: URI of the post in format at://did:plc:xyz/app.bsky.feed.post/abc123
        author_handle: Handle of the post author
        
    Returns:
        str: Web URL in format https://bsky.app/profile/handle/post/abc123
             or None if conversion fails
    """
    try:
        # Extract the post ID from the URI (the last part of the path)
        post_id = uri.split('/')[-1]
        
        # Create the Bluesky web URL
        web_url = f"https://bsky.app/profile/{author_handle}/post/{post_id}"
        return web_url
    except Exception:
        # Return None in case of error
        return None

def parse_bluesky_list_url(url: str) -> Optional[Dict[str, str]]:
    """
    Extract the handle and list ID from a Bluesky list URL.
    
    Args:
        url: Bluesky list URL. Supported formats:
            - https://bsky.app/profile/user.bsky.social/lists/123abc
            - at://did:plc:xxx/app.bsky.graph.list/123abc
            - did:plc:xxx/app.bsky.graph.list/123abc
            
    Returns:
        Dict: Dictionary with 'handle' and 'list_id', or None if URL is invalid
    """
    # 1. Check if it's a browser URL (bsky.app)
    browser_pattern = r'bsky\.app/profile/([^/]+)/lists/([^/]+)'
    browser_match = re.search(browser_pattern, url)
    if browser_match:
        return {
            'handle': browser_match.group(1).strip().strip('"').strip("'"),
            'list_id': browser_match.group(2).strip().strip('"').strip("'")
        }
    
    # 2. Check if it's a complete AT Protocol URI (at://did:plc:...)
    at_uri_pattern = r'at://([^/]+)/app\.bsky\.graph\.list/([^/]+)'
    at_uri_match = re.search(at_uri_pattern, url)
    if at_uri_match:
        return {
            'handle': at_uri_match.group(1).strip().strip('"').strip("'"),  # This will be a DID
            'list_id': at_uri_match.group(2).strip().strip('"').strip("'")
        }
    
    # 3. Check if it's a partial URI (did:plc:...)
    did_uri_pattern = r'(did:[^/]+)/app\.bsky\.graph\.list/([^/]+)'
    did_uri_match = re.search(did_uri_pattern, url)
    if did_uri_match:
        return {
            'handle': did_uri_match.group(1).strip().strip('"').strip("'"),  # This will be a DID
            'list_id': did_uri_match.group(2).strip().strip('"').strip("'")
        }
        
    # If no patterns match, the URL is invalid
    print(f"❌ Unrecognized list URL format: {url}")
    print("Supported formats:")
    print(" - https://bsky.app/profile/user.bsky.social/lists/123abc")
    print(" - at://did:plc:xxx/app.bsky.graph.list/123abc")
    print(" - did:plc:xxx/app.bsky.graph.list/123abc")
    return None
