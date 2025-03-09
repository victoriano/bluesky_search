#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON export functionality for Bluesky posts.
"""

import json
import os
import datetime
from typing import Dict, List, Any, Optional

def save_results_to_json(results: Dict[str, List[Dict[str, Any]]], filename: Optional[str] = None) -> Optional[str]:
    """
    Save search results to a JSON file.
    
    Args:
        results: Dictionary with results (author handles as keys, posts as values)
        filename: Name of the output file (optional)
        
    Returns:
        str: Path to the saved file, or None if saving failed
    """
    try:
        # Generate default filename if none provided
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bluesky_posts_{timestamp}.json"
            
        # Add .json extension if not already present
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
            
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Path to save file
        filepath = os.path.join('data', filename)
        
        # Ensure arrays are properly formatted
        normalized_results = {}
        for author, posts in results.items():
            normalized_posts = []
            for post in posts:
                # Create a new post dictionary with the exact column order as requested
                normalized_post = {
                    'user_handle': author,  # The handle under which we found this post
                    'author_handle': post.get('author', {}).get('handle', author),
                    'author_display_name': post.get('author', {}).get('display_name', ''),
                    'created_at': post.get('created_at', ''),
                    'post_type': post.get('post_type', 'unknown'),
                    'text': post.get('text', ''),
                    'web_url': post.get('web_url', ''),
                    'likes': post.get('likes', 0),
                    'reposts': post.get('reposts', 0),
                    'replies': post.get('replies', 0),
                    'urls': post.get('urls', []),
                    'images': post.get('images', []),
                    'mentions': post.get('mentions', []),
                    'cid': post.get('cid', ''),
                    'author_did': post.get('author', {}).get('did', ''),
                    'uri': post.get('uri', '')
                }
                
                normalized_posts.append(normalized_post)
            normalized_results[author] = normalized_posts
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized_results, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Results exported to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving results to JSON: {str(e)}")
        return None
