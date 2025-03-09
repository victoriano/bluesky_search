#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parquet export functionality for Bluesky posts.
"""

import os
import datetime
import json
from typing import Dict, List, Any, Optional

def save_results_to_parquet(results: Dict[str, List[Dict[str, Any]]], filename: Optional[str] = None, 
                         sort_by_date: bool = True) -> Optional[str]:
    """
    Save search results to a Parquet file.
    
    Args:
        results: Dictionary with results (author handles as keys, posts as values)
        filename: Name of the output file (optional)
        sort_by_date: If True, sorts posts by creation date (newest first)
        
    Returns:
        str: Path to the saved file, or None if saving failed
    """
    try:
        # Check if polars is available
        try:
            import polars as pl
        except ImportError:
            print("❌ Error: polars is required for Parquet export")
            print("Install with: uv pip install polars")
            return None
            
        # Generate default filename if none provided
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bluesky_posts_{timestamp}.parquet"
            
        # Add .parquet extension if not already present
        if not filename.endswith('.parquet'):
            filename = f"{filename}.parquet"
            
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Path to save file
        filepath = os.path.join('data', filename)
        
        # Flatten the posts data for Parquet format while preserving arrays
        flattened_data = []
        for author, posts in results.items():
            for post in posts:
                # Get array values and standardize to empty lists if missing
                urls_array = post.get('urls', [])
                if urls_array is None:
                    urls_array = []
                elif not isinstance(urls_array, list):
                    try:
                        urls_array = list(urls_array) if urls_array else []
                    except:
                        urls_array = []
                
                images_array = post.get('images', [])
                if images_array is None:
                    images_array = []
                elif not isinstance(images_array, list):
                    try:
                        images_array = list(images_array) if images_array else []
                    except:
                        images_array = []
                
                mentions_array = post.get('mentions', [])
                if mentions_array is None:
                    mentions_array = []
                elif not isinstance(mentions_array, list):
                    try:
                        mentions_array = list(mentions_array) if mentions_array else []
                    except:
                        mentions_array = []
                
                # Format arrays as properly formatted JSON strings exactly like the CSV export
                # This ensures consistent formatting across export types
                
                # Format URLs array
                if urls_array:
                    urls_json = '['
                    for i, url in enumerate(urls_array):
                        if i > 0:
                            urls_json += ', '
                        # Format URL as a string
                        urls_json += json.dumps(url)  # This adds quotes around the URL
                    urls_json += ']'
                else:
                    urls_json = '[]'
                
                # Format images array
                if images_array:
                    images_json = '['
                    for i, img in enumerate(images_array):
                        if i > 0:
                            images_json += ', '
                        # Format image URL as a string
                        images_json += json.dumps(img)  # This adds quotes around the image URL
                    images_json += ']'
                else:
                    images_json = '[]'
                
                # Format mentions array
                if mentions_array:
                    mentions_json = '['
                    for i, mention in enumerate(mentions_array):
                        if i > 0:
                            mentions_json += ', '
                        # Format mention as a string
                        mentions_json += json.dumps(mention)  # This adds quotes around the mention
                    mentions_json += ']'
                else:
                    mentions_json = '[]'
                
                # Column order exactly as requested by user
                flat_post = {
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
                    'urls': urls_json,  # Store as JSON string
                    'images': images_json,  # Store as JSON string
                    'mentions': mentions_json,  # Store as JSON string
                    'lang': post.get('lang', ''),  # Language field
                    'replied_to_id': post.get('replied_to_id', ''),  # ID of the user being replied to
                    'cid': post.get('cid', ''),
                    'author_did': post.get('author', {}).get('did', ''),
                    'uri': post.get('uri', '')
                }
                
                flattened_data.append(flat_post)
        
        # No need for additional processing as we're already storing the arrays as JSON strings
        
        # Create a Polars DataFrame
        df = pl.DataFrame(flattened_data)
        
        # Sort by date if requested
        if sort_by_date and 'created_at' in df.columns:
            df = df.sort('created_at', descending=True)
        
        # Write to Parquet
        df.write_parquet(filepath)
        
        print(f"✅ Results exported to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving results to Parquet: {str(e)}")
        return None
