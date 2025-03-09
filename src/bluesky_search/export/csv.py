#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSV export functionality for Bluesky posts.
"""

import os
import datetime
import json
from typing import Dict, List, Any, Optional

def save_results_to_csv(results: Dict[str, List[Dict[str, Any]]], filename: Optional[str] = None, 
                     sort_by_date: bool = True) -> Optional[str]:
    """
    Save search results to a CSV file.
    
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
            print("❌ Error: polars is required for CSV export")
            print("Install with: uv pip install polars")
            return None
            
        # Generate default filename if none provided
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bluesky_posts_{timestamp}.csv"
            
        # Add .csv extension if not already present
        if not filename.endswith('.csv'):
            filename = f"{filename}.csv"
            
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Path to save file
        filepath = os.path.join('data', filename)
        
        # Flatten the posts data for CSV format while preserving arrays
        flattened_data = []
        for author, posts in results.items():
            for post in posts:
                # Column order exactly as requested by user
                # Get the raw array values
                urls_array = post.get('urls', [])
                images_array = post.get('images', [])
                mentions_array = post.get('mentions', [])
                
                # Process URLs to ensure proper formatting
                # This custom formatting removes the extra escaping that happens in CSV
                if urls_array:
                    # Start with opening bracket
                    urls_str = '['  
                    for i, url in enumerate(urls_array):
                        # Add double quotes around each string item
                        urls_str += f'"{url}"'
                        # Add comma if not the last item
                        if i < len(urls_array) - 1:
                            urls_str += ','  
                    # Close with closing bracket
                    urls_str += ']'  
                else:
                    urls_str = '[]'
                
                # Process images arrays
                if images_array:
                    # Start with opening bracket
                    images_str = '['
                    for i, img in enumerate(images_array):
                        # Add double quotes around each string item
                        images_str += f'"{img}"'
                        # Add comma if not the last item
                        if i < len(images_array) - 1:
                            images_str += ','
                    # Close with closing bracket
                    images_str += ']'
                else:
                    images_str = '[]'
                
                # Process mentions arrays
                if mentions_array:
                    # Start with opening bracket
                    mentions_str = '['
                    for i, mention in enumerate(mentions_array):
                        # Add double quotes around each string item
                        mentions_str += f'"{mention}"'
                        # Add comma if not the last item
                        if i < len(mentions_array) - 1:
                            mentions_str += ','
                    # Close with closing bracket
                    mentions_str += ']'
                else:
                    mentions_str = '[]'
                
                # Create dictionary with fields in exact order requested
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
                    'urls': urls_str,
                    'images': images_str,
                    'mentions': mentions_str,
                    'lang': post.get('lang', ''),  # Language field
                    'replied_to_handle': post.get('replied_to_handle', ''),  # Handle of the user being replied to
                    'replied_to_id': post.get('replied_to_id', ''),  # ID of the user being replied to
                    'cid': post.get('cid', ''),
                    'author_did': post.get('author', {}).get('did', ''),
                    'uri': post.get('uri', '')
                }
                
                flattened_data.append(flat_post)
        
        # Create a Polars DataFrame
        df = pl.DataFrame(flattened_data)
        
        # Sort by date if requested
        if sort_by_date and 'created_at' in df.columns:
            df = df.sort('created_at', descending=True)
        
        # Write to CSV
        df.write_csv(filepath)
        
        print(f"✅ Results exported to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving results to CSV: {str(e)}")
        return None
