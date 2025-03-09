#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Posts Fetcher

This module provides the main functionality for fetching and processing
posts from the Bluesky social network.
"""

import re
import time
import datetime
from typing import List, Dict, Any, Optional, Tuple

from .client import BlueskyClient
from .search import BlueskySearch
from .list import BlueskyList
from .utils.url import get_web_url_from_uri, parse_bluesky_list_url
from .utils.text import sanitize_uri_component, extract_urls_from_text
from .export.json import save_results_to_json
from .export.csv import save_results_to_csv
from .export.parquet import save_results_to_parquet

class BlueskyPostsFetcher(BlueskyClient):
    """Class for fetching posts from Bluesky users."""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize the Bluesky Posts Fetcher.
        
        Args:
            username: Username or email for authentication
            password: Password for authentication
        """
        super().__init__(username, password)
        
        # Initialize the search and list components
        self._search = None
        self._list = None
    
    def get_user_posts(self, handle: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent posts from a user.
        
        Args:
            handle: Bluesky username (with or without @)
            limit: Maximum number of posts to retrieve
            
        Returns:
            List[Dict]: List of posts with relevant information
        """
        # Make sure the handle doesn't start with @
        if handle.startswith('@'):
            handle = handle[1:]
        
        try:
            # Get the user profile
            profile = self.get_profile(handle)
            
            # Get user posts with pagination to respect the API's 100-post limit
            posts = []
            cursor = None
            posts_collected = 0
            original_limit = limit
            
            # Calculate approximate number of needed API calls
            api_calls_needed = max(1, (original_limit + 99) // 100)  # Round up
            
            # Iterate until we reach the limit or run out of results
            for call_num in range(api_calls_needed):
                # Calculate the limit for this call (max 100)
                current_call_limit = min(100, original_limit - posts_collected)
                
                if current_call_limit <= 0:
                    break
                
                # Parameters for getting the feed
                feed_params = {
                    "actor": handle,
                    "limit": current_call_limit
                }
                
                # Add cursor if this isn't the first call
                if cursor:
                    feed_params["cursor"] = cursor
                
                # Get the posts
                try:
                    author_feed = self.client.get_author_feed(**feed_params)
                    
                    # Save cursor for next page if it exists
                    cursor = getattr(author_feed, 'cursor', None)
                    
                    # If no results or no cursor, end the loop
                    if not hasattr(author_feed, 'feed') or len(author_feed.feed) == 0:
                        break
                    
                    # Process posts from this page
                    for feed_view in author_feed.feed:
                        try:
                            post = feed_view.post
                            posts_collected += 1
                            
                            # Extract relevant information
                            post_data = {
                                'uri': post.uri,
                                'cid': post.cid,
                                'web_url': get_web_url_from_uri(post.uri, post.author.handle),
                                'author': {
                                    'did': post.author.did,
                                    'handle': post.author.handle,
                                    'display_name': getattr(post.author, 'display_name', post.author.handle)
                                },
                                'text': post.record.text,
                                'created_at': post.record.created_at,
                                'likes': getattr(post, 'like_count', 0),
                                'reposts': getattr(post, 'repost_count', 0),
                                'replies': getattr(post, 'reply_count', 0)
                            }
                            
                            # Add images if they exist
                            if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
                                # Extract image URLs
                                image_urls = []
                                for img in post.record.embed.images:
                                    if hasattr(img, 'image'):
                                        img_obj = img.image
                                        if hasattr(img_obj, 'cid') and img_obj.cid:
                                            # Convert CID object to string
                                            cid_str = str(img_obj.cid)
                                            author_did = post.author.did
                                            # Build URL using the valid CID string
                                            image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                            image_urls.append(image_url)
                                
                                if image_urls:
                                    post_data['images'] = image_urls
                            
                            # Determine post type
                            # First check if it's a reply based on the existence of a non-null reply attribute
                            if hasattr(post.record, 'reply') and post.record.reply is not None:
                                post_data['post_type'] = 'reply'
                            else:
                                # For non-reply posts, check if they're reposts
                                # First see if the author DID matches the requested user's DID
                                try:
                                    # Get the DID of the user whose timeline we're viewing
                                    user_profile = None
                                    if hasattr(self.client, '_me') and self.client._me:
                                        user_did = self.client._me.did
                                    else:
                                        # If we don't have the DID in the session, try to get it from the API
                                        user_profile = self.client.app.bsky.actor.get_profile({'actor': handle})
                                        user_did = user_profile.did
                                    
                                    # If the DIDs of the user and post author are different, it's a repost
                                    if post.author.did != user_did:
                                        post_data['post_type'] = 'repost'
                                    else:
                                        post_data['post_type'] = 'original'
                                except Exception:
                                    # If there's an error comparing DIDs, use alternative method
                                    # Check for repost indicators as in previous version
                                    if hasattr(post, 'reason') and post.reason is not None:
                                        if hasattr(post.reason, 'py_type') and 'repost' in str(post.reason.py_type).lower():
                                            post_data['post_type'] = 'repost'
                                        else:
                                            post_data['post_type'] = 'original'
                                    else:
                                        post_data['post_type'] = 'original'
                            
                            # Extract URLs from post content (two methods)
                            urls = []
                            
                            # Extract user mentions
                            mentions = []
                            
                            # Extract URLs and mentions from facets (Bluesky's structured format)
                            if hasattr(post.record, 'facets') and post.record.facets:
                                for facet in post.record.facets:
                                    if hasattr(facet, 'features'):
                                        for feature in facet.features:
                                            # Identify feature type by py_type
                                            if hasattr(feature, 'py_type'):
                                                # Extract links
                                                if feature.py_type == 'app.bsky.richtext.facet#link' and hasattr(feature, 'uri'):
                                                    urls.append(feature.uri)
                                                # Extract mentions
                                                elif feature.py_type == 'app.bsky.richtext.facet#mention' and hasattr(feature, 'did'):
                                                    # Try to get handle if available
                                                    if hasattr(feature, 'handle'):
                                                        mentions.append(feature.handle)
                                                    else:
                                                        mentions.append(feature.did)
                            
                            # 2. As backup, also search for URLs with regex in the text
                            if post.record.text:
                                regex_urls = extract_urls_from_text(post.record.text)
                                # Add URLs not found in facets
                                for url in regex_urls:
                                    if url not in urls:
                                        urls.append(url)
                            
                            # Store URLs if found
                            if urls:
                                post_data['urls'] = urls
                                
                            # Store mentions if found
                            if mentions:
                                post_data['mentions'] = mentions
                            
                            posts.append(post_data)
                        except Exception as inner_e:
                            # If there's an error processing an individual post, continue with the next one
                            print(f"⚠️ Error processing a post from @{handle}: {str(inner_e)}")
                            continue
                except Exception as e:
                    print(f"❌ Error getting posts (page {call_num + 1}) from @{handle}: {str(e)}")
                    break
            
            print(f"✅ Retrieved {len(posts)} posts from @{handle}")
            return posts
        
        except Exception as e:
            print(f"❌ Error getting posts from @{handle}: {str(e)}")
            return []
    
    def _sanitize_uri_component(self, component: str) -> str:
        """
        Sanitize a URI component.
        
        Args:
            component: URI component to sanitize
            
        Returns:
            str: Sanitized component
        """
        return sanitize_uri_component(component)
    
    def get_posts_from_users(self, handles: List[str], limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts from multiple users.
        
        Args:
            handles: List of Bluesky usernames
            limit: Maximum number of posts per user
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        results = {}
        
        for handle in handles:
            # Clean up the handle
            clean_handle = handle.strip()
            if clean_handle.startswith('@'):
                clean_handle = clean_handle[1:]
                
            print(f"📊 Getting posts from @{clean_handle}...")
            
            # Get posts for this user
            user_posts = self.get_user_posts(clean_handle, limit)
            
            # Store in results if we got any posts
            if user_posts:
                results[clean_handle] = user_posts
            
            # Add a small delay between requests to avoid rate limiting
            time.sleep(0.5)
        
        return results
    
    def get_posts_from_bluesky_list_url(self, list_url: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts from a Bluesky list URL.
        
        Args:
            list_url: URL of the Bluesky list
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        # Initialize the list component if needed
        if self._list is None:
            self._list = BlueskyList(self.client)
        
        # Delegate to the list component
        return self._list.get_posts_from_bluesky_list_url(list_url, limit)
    
    def get_posts_from_bluesky_list(self, handle: str, list_id: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts directly from a Bluesky list.
        
        Args:
            handle: Handle of the list owner
            list_id: ID of the list
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        # Initialize the list component if needed
        if self._list is None:
            self._list = BlueskyList(self.client)
        
        # Delegate to the list component
        return self._list.get_posts_from_bluesky_list(handle, list_id, limit)
    
    def search_posts(self, query: str, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for posts matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            **kwargs: Additional search parameters
            
        Returns:
            List[Dict]: List of matching posts
        """
        # Initialize the search component if needed
        if self._search is None:
            self._search = BlueskySearch(self.client)
        
        # Delegate to the search component
        return self._search.search_posts(query, limit, **kwargs)
    
    def get_posts_from_search(self, query: str, limit: int = 50, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts from a search and organize them by author.
        
        Args:
            query: Search query
            limit: Maximum number of results
            **kwargs: Additional search parameters
            
        Returns:
            Dict: Dictionary with posts organized by author
        """
        # search_posts already handles pagination internally
        search_posts = self.search_posts(query, limit, **kwargs)
        if not search_posts:
            return {}
        
        # Organize posts by author
        results = {}
        for post in search_posts:
            author_handle = post['author']['handle']
            if author_handle not in results:
                results[author_handle] = []
            results[author_handle].append(post)
        
        print(f"📊 Posts organized by author: {len(results)} different authors")
        return results
    
    def export_results(self, results: Dict[str, List[Dict[str, Any]]], format: str = 'json', 
                    filename: str = None, sort_by_date: bool = True) -> Optional[str]:
        """
        Export results in the specified format.
        
        Args:
            results: Dictionary with results
            format: Export format ('json', 'csv', or 'parquet')
            filename: Name of the output file (optional)
            sort_by_date: If True, sorts posts by creation date (newest first)
            
        Returns:
            str: Path to the saved file, or None if there was an error
        """
        format = format.lower()
        
        if format == 'json':
            return save_results_to_json(results, filename)
        elif format == 'csv':
            return save_results_to_csv(results, filename, sort_by_date=sort_by_date)
        elif format == 'parquet':
            return save_results_to_parquet(results, filename, sort_by_date=sort_by_date)
        else:
            print(f"❌ Unsupported format: {format}")
            print("Available formats: json, csv, parquet")
            return None
            
    def export_to_json(self, posts, output_file: str) -> None:
        """
        Export posts to a JSON file.
        
        Args:
            posts: Posts to export (list or dict)
            output_file: Output file path
        """
        if isinstance(posts, list):
            # If posts is a list, transform it to a dict format for save_results_to_json
            # Group by author for consistency
            results = {}
            for post in posts:
                author_handle = post['author']['handle']
                if author_handle not in results:
                    results[author_handle] = []
                results[author_handle].append(post)
        else:
            # If already a dict, use as is
            results = posts
            
        save_results_to_json(results, output_file)
        
    def export_to_csv(self, posts, output_file: str, sort_by_date: bool = True) -> None:
        """
        Export posts to a CSV file.
        
        Args:
            posts: Posts to export (list or dict)
            output_file: Output file path
            sort_by_date: If True, sorts posts by creation date (newest first)
        """
        if isinstance(posts, list):
            # If posts is a list, transform it to a dict format for save_results_to_csv
            results = {}
            for post in posts:
                author_handle = post['author']['handle']
                if author_handle not in results:
                    results[author_handle] = []
                results[author_handle].append(post)
        else:
            # If already a dict, use as is
            results = posts
            
        save_results_to_csv(results, output_file, sort_by_date=sort_by_date)
        
    def export_to_parquet(self, posts, output_file: str, sort_by_date: bool = True) -> None:
        """
        Export posts to a Parquet file.
        
        Args:
            posts: Posts to export (list or dict)
            output_file: Output file path
            sort_by_date: If True, sorts posts by creation date (newest first)
        """
        if isinstance(posts, list):
            # If posts is a list, transform it to a dict format for save_results_to_parquet
            results = {}
            for post in posts:
                author_handle = post['author']['handle']
                if author_handle not in results:
                    results[author_handle] = []
                results[author_handle].append(post)
        else:
            # If already a dict, use as is
            results = posts
            
        save_results_to_parquet(results, output_file, sort_by_date=sort_by_date)
