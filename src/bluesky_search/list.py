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
        
        # Get posts from the list
        return self.get_posts_from_bluesky_list(list_info['handle'], list_info['list_id'], limit)
