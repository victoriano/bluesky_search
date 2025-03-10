#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky List Module

This module provides functionality for working with Bluesky lists.
"""

import time
import re
from typing import List, Dict, Any, Optional

from .utils.url import get_web_url_from_uri, parse_bluesky_list_url
from .utils.text import sanitize_uri_component, extract_urls_from_text

class BlueskyList:
    """Class for working with Bluesky lists."""
    
    def __init__(self, client):
        """
        Initialize the BlueskyList module.
        
        Args:
            client: An authenticated Bluesky client instance
        """
        self.client = client
    
    def _process_list_response(self, response, list_id: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process a list response from the Bluesky API.
        
        Args:
            response: The API response containing list data
            list_id: ID of the list
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary of posts organized by user
        """
        try:
            # Extract list items (users)
            list_items = getattr(response, 'items', [])
            
            if not list_items:
                print(f"❌ No users found in list {list_id}")
                return {}
            
            # Extract handles from list items
            handles = []
            for item in list_items:
                if hasattr(item, 'subject') and hasattr(item.subject, 'handle'):
                    handle = item.subject.handle
                    handles.append(handle)
            
            # If we have handles, fetch posts for each user
            if handles:
                print(f"✅ Found {len(handles)} users in list {list_id}")
                print(f"📊 Fetching posts from list members...")
                
                # Calculate posts per user to respect the total limit
                posts_per_user = max(1, limit // len(handles))
                
                # Get posts for each user in the list
                from .fetcher import BlueskyPostsFetcher
                fetcher = BlueskyPostsFetcher()
                fetcher.client = self.client  # Share the authenticated client
                
                return fetcher.get_posts_from_users(handles, posts_per_user)
            else:
                print("❌ Could not extract any user handles from the list")
                return {}
                
        except Exception as e:
            print(f"❌ Error processing list: {str(e)}")
            return {}
    
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
        try:
            # Check if the handle is already a DID
            if handle.startswith('did:'):
                profile_did = handle
            else:
                # Get the DID from the handle
                profile = self.client.get_profile(actor=handle)
                profile_did = profile.did
            
            # Apply thorough cleaning with the specialized method
            list_id = sanitize_uri_component(list_id)
            profile_did = sanitize_uri_component(profile_did)
            
            # Build the list URI in the correct format for the AT Protocol API
            # Format should be: at://did:plc:xxx/app.bsky.graph.list/listname without quotes
            list_uri = f"at://{profile_did}/app.bsky.graph.list/{list_id}"
            
            # Validate that there are no quotes or spaces in the final URI
            if '"' in list_uri or "'" in list_uri:
                print('\n⚠️ Detected quotes in the URI. Cleaning...')
                list_uri = re.sub(r'["\']+', '', list_uri)
            # Use single quotes for the print to avoid issues with extra quotes
            print('Getting list:', list_uri)
            
            # Get basic list information
            try:
                # Make sure the API parameter has no extra quotes
                response = self.client.app.bsky.graph.get_list({"list": list_uri})
            except Exception as e:
                print('Error getting list with URI:', list_uri)
                print('Error details:', e.content.message if hasattr(e, 'content') and hasattr(e.content, 'message') else str(e))
                
                # Check if there's rate limiting information in the headers
                if hasattr(self.client, '_check_rate_limit_info'):
                    self.client._check_rate_limit_info(e)
                
                # Try with the URI without the last quote if there's one
                if list_uri.endswith('"'):
                    list_uri = list_uri[:-1]
                    print('Trying without final quote:', list_uri)
                    try:
                        response = self.client.app.bsky.graph.get_list({"list": list_uri})
                        return self._process_list_response(response, list_id, limit)
                    except Exception:
                        pass
                
                # Ensure components are completely clean
                clean_profile_did = sanitize_uri_component(profile_did)
                clean_list_id = sanitize_uri_component(list_id)
                
                # Try with the correct URI format for the API (without the at:// prefix)
                alt_list_uri = f"{clean_profile_did}/app.bsky.graph.list/{clean_list_id}"
                print('Trying alternative format:', alt_list_uri)
                
                try:
                    response = self.client.app.bsky.graph.get_list({"list": alt_list_uri})
                    return self._process_list_response(response, list_id, limit)
                except Exception as e2:
                    print('Error with alternative format:', str(e2))
                    
                    # One last attempt with just the list ID
                    print('Final attempt with list ID only...')
                    try:
                        response = self.client.app.bsky.graph.get_list({"list": list_id})
                        return self._process_list_response(response, list_id, limit)
                    except Exception as e3:
                        print('All attempts failed:', str(e3))
                        return {}
            
            # Process the list if we get here
            return self._process_list_response(response, list_id, limit)
            
        except Exception as e:
            print(f"❌ Error getting list: {str(e)}")
            return {}
    
    def get_list_feed(self, handle: str, list_id: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts directly from a Bluesky list feed/timeline using the app.bsky.feed.get_timeline endpoint.
        
        Args:
            handle: Handle of the list owner
            list_id: ID of the list
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        try:
            # Get the list DID
            if handle.startswith('did:'):
                profile_did = handle
            else:
                profile = self.client.get_profile(actor=handle)
                profile_did = profile.did
            
            # Sanitize components
            list_id = sanitize_uri_component(list_id)
            profile_did = sanitize_uri_component(profile_did)
            
            # Build the list URI in the correct format for the AT Protocol API
            list_uri = f"at://{profile_did}/app.bsky.graph.list/{list_id}"
            
            print(f"📊 Getting feed for list: {list_uri}")
            
            # DIRECT APPROACH: Use the feed.getTimeline with the list parameter
            try:
                # Set up parameters for pagination
                params = {
                    "algorithm": "reverse-chronological",  # Standard feed algorithm
                    "limit": min(100, limit)            # API limit is 100 per request
                }
                
                # Add list parameter which is the correct way to filter by list
                params["list"] = list_uri
                
                print(f"🔍 Using direct list timeline API endpoint...")
                
                all_posts = []
                cursor = None
                
                # Fetch posts with pagination
                while len(all_posts) < limit:
                    if cursor:
                        params["cursor"] = cursor
                    
                    # Call the timeline API with the list filter
                    try:
                        timeline_response = self.client.app.bsky.feed.get_timeline(params)
                        feed_items = getattr(timeline_response, 'feed', [])
                        
                        if not feed_items:
                            print(f"No more posts found in list")
                            break
                            
                        # Extract posts from feed
                        for item in feed_items:
                            if hasattr(item, 'post') and hasattr(item.post, 'author'):
                                # Extract relevant data for each post
                                author_handle = item.post.author.handle
                                author_display_name = getattr(item.post.author, 'display_name', author_handle)
                                
                                # Create standardized post object
                                post_data = {
                                    'uri': item.post.uri,
                                    'cid': item.post.cid,
                                    'author': {
                                        'did': item.post.author.did,
                                        'handle': author_handle,
                                        'display_name': author_display_name
                                    },
                                    'record': item.post.record,
                                    'indexed_at': item.post.indexed_at
                                }
                                all_posts.append(post_data)
                                
                        # Check if we reached the desired limit
                        if len(all_posts) >= limit:
                            break
                            
                        # Get cursor for next page if available
                        cursor = getattr(timeline_response, 'cursor', None)
                        if not cursor:
                            break
                            
                        # Small delay between requests
                        time.sleep(0.3)
                        
                    except Exception as e:
                        print(f"Error fetching timeline: {str(e)}")
                        break
                
                # Organize posts by author
                results = {}
                for post in all_posts:
                    author_handle = post['author']['handle']
                    if author_handle not in results:
                        results[author_handle] = []
                    results[author_handle].append(post)
                    
                if results:
                    print(f"✅ Successfully retrieved {len(all_posts)} posts directly from list timeline")
                    # Print each author and number of posts
                    for author, posts in results.items():
                        print(f"✅ Retrieved {len(posts)} posts from @{author}")
                    return results
                        
            except Exception as e:
                print(f"❌ Error with direct list timeline: {str(e)}")
                
            # If we get here, direct approach failed - try with list members
            print(f"⚠️ Direct list timeline fetch failed, getting list members...")
            
            # Get the list members
            list_response = self.client.app.bsky.graph.get_list({"list": list_uri})
            
            if not hasattr(list_response, 'items') or not list_response.items:
                print(f"❌ No members found in list")
                return {}
                
            # Extract member handles
            handles = []
            for item in list_response.items:
                if hasattr(item, 'subject') and hasattr(item.subject, 'handle'):
                    handles.append(item.subject.handle)
            
            print(f"✅ Found {len(handles)} users in list {list_id}")
            print(f"⚠️ Falling back to member-by-member approach")
            
            if handles:
                # Calculate posts per user to respect the total limit
                posts_per_user = max(1, limit // len(handles))
                
                # Get posts for each user in the list
                from .fetcher import BlueskyPostsFetcher
                fetcher = BlueskyPostsFetcher()
                fetcher.client = self.client  # Share the authenticated client
                
                return fetcher.get_posts_from_users(handles, posts_per_user)
            else:
                print("❌ Could not extract any user handles from the list")
                return {}
        except Exception as e:
            print(f"❌ Error with list feed: {str(e)}")
            return {}
    
    def get_posts_from_bluesky_list_url(self, list_url: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts from a Bluesky list URL.
        
        Args:
            list_url: URL of the Bluesky list
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        # Parse the list URL
        list_info = parse_bluesky_list_url(list_url)
        
        if not list_info:
            return {}
        
        # Try to get the feed directly first
        result = self.get_list_feed(list_info['handle'], list_info['list_id'], limit)
        
        # If direct feed fetch fails, fall back to the member-by-member approach
        if not result:
            print("⚠️ Direct list feed fetch failed, falling back to member-by-member approach")
            return self.get_posts_from_bluesky_list(list_info['handle'], list_info['list_id'], limit)
            
        return result
