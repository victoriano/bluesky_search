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
            limit: Maximum number of posts to retrieve (with automatic pagination if greater than 100)
            
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
                except Exception as e2:
                    print('Error with alternative format:', str(e2))
                    
                    # One final attempt eliminating any non-alphanumeric characters from the list_id
                    final_list_id = re.sub(r'[^a-zA-Z0-9]+', '', list_id)
                    if final_list_id != clean_list_id:
                        try:
                            final_uri = f"{clean_profile_did}/app.bsky.graph.list/{final_list_id}"
                            print('Trying URI with only alphanumeric characters:', final_uri)
                            response = self.client.app.bsky.graph.get_list({"list": final_uri})
                        except Exception:
                            pass
                    
                    # If all attempts fail, show debugging information
                    print('\n⛔ All URI formats failed. Debug information:')
                    print(f"  - Profile DID: '{profile_did}'")
                    print(f"  - List ID (original): '{list_id}'")
                    print(f"  - List ID (clean): '{clean_list_id}'")
                    print(f"  - Complete URI: '{list_uri}'")
                    print(f"  - Alternative URI: '{alt_list_uri}'")
                    print("\nPlease verify that the list ID is correct in the source URL.")
                    return {}
            
            list_name = "List"
            if hasattr(response, 'list') and hasattr(response.list, 'name'):
                list_name = response.list.name
                print(f"List found: {list_name}")
                
            # Implement pagination to retrieve more than 100 posts (API limit)
            original_limit = limit
            posts = []
            posts_collected = 0
            cursor = None
            
            # Calculate the approximate number of API calls needed
            api_call_limit = min(100, limit)  # API allows maximum 100 posts per call
            api_calls_needed = (limit + api_call_limit - 1) // api_call_limit  # Round up
            
            if api_calls_needed > 1:
                print(f"📢 Requesting {original_limit} posts from the list (will make approximately {api_calls_needed} API calls)")
            
            # Pagination loop
            for call_num in range(1, api_calls_needed + 1):
                # Calculate how many posts remain to be retrieved
                remaining_limit = min(api_call_limit, limit - posts_collected)
                
                if api_calls_needed > 1:
                    print(f"🔍 Making call {call_num} of ~{api_calls_needed} (getting {remaining_limit} posts)")
                
                # Prepare parameters for the API call
                params = {"list": list_uri, "limit": remaining_limit}
                if cursor:
                    params["cursor"] = cursor
                
                # Make the API call
                list_feed = self.client.app.bsky.feed.get_list_feed(params)
                
                # Get the cursor for the next page
                cursor = getattr(list_feed, 'cursor', None)
                
                page_posts = []
                # Process the posts on this page
                if hasattr(list_feed, 'feed'):
                    for feed_view in list_feed.feed:
                        post = feed_view.post
                        
                        # Extract relevant information (same format as get_user_posts)
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
                            'created_at': getattr(post.record, 'createdAt', post.record.created_at if hasattr(post.record, 'created_at') else ''),
                            'likes': getattr(post, 'like_count', 0),
                            'reposts': getattr(post, 'repost_count', 0),
                            'replies': getattr(post, 'reply_count', 0),
                            'urls': [],
                            'mentions': []
                        }
                        
                        # Determine post type (reply, repost, or original)
                        if hasattr(post.record, 'reply') and post.record.reply is not None:
                            post_data['post_type'] = 'reply'
                            # Store the ID of the post being replied to if available
                            if hasattr(post.record.reply, 'parent') and hasattr(post.record.reply.parent, 'uri'):
                                post_data['replied_to_id'] = post.record.reply.parent.uri
                            else:
                                post_data['replied_to_id'] = ''
                        else:
                            # For posts that aren't replies, check if they're reposts
                            if hasattr(post, 'reason') and post.reason is not None:
                                if hasattr(post.reason, 'py_type') and 'repost' in str(post.reason.py_type).lower():
                                    post_data['post_type'] = 'repost'
                                else:
                                    post_data['post_type'] = 'original'
                            else:
                                post_data['post_type'] = 'original'
                            post_data['replied_to_id'] = ''
                        
                        # Process images exactly as in search_posts
                        if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
                            # Extract image URLs
                            image_urls = []
                            
                            for img in post.record.embed.images:
                                if hasattr(img, 'image'):
                                    # Try to get valid CID
                                    img_obj = img.image
                                    
                                    # Extract CID as string for the URL
                                    if hasattr(img_obj, 'cid') and img_obj.cid:
                                        # Convert CID object to string
                                        cid_str = str(img_obj.cid)
                                        author_did = post.author.did
                                        # Build URL using the valid CID as string
                                        image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                        image_urls.append(image_url)
                            
                            # Only add the 'images' field if there are valid URLs
                            if image_urls:
                                post_data['images'] = image_urls
                            
                        # Extract user mentions and URLs exactly as in search_posts
                        urls = []
                        mentions = []
                        
                        # Extract URLs and mentions from facets (Bluesky's structured format)
                        if hasattr(post.record, 'facets') and post.record.facets:
                            for facet in post.record.facets:
                                if hasattr(facet, 'features'):
                                    for feature in facet.features:
                                        # Identify the feature type by its py_type
                                        if hasattr(feature, 'py_type'):
                                            # Extract links
                                            if feature.py_type == 'app.bsky.richtext.facet#link' and hasattr(feature, 'uri'):
                                                urls.append(feature.uri)
                                            # Extract mentions
                                            elif feature.py_type == 'app.bsky.richtext.facet#mention' and hasattr(feature, 'did'):
                                                # Try to get the handle if available
                                                if hasattr(feature, 'handle'):
                                                    mentions.append(feature.handle)
                                                else:
                                                    mentions.append(feature.did)
                        
                        # As a backup, also search URLs with regex in the text
                        import re
                        url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./%?&=+#]*)?'
                        if post.record.text:
                            regex_urls = re.findall(url_pattern, post.record.text)
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
                        
                        # Add language information if available
                        if hasattr(post.record, 'langs') and post.record.langs:
                            # Use the first language in the list if it's a list
                            if isinstance(post.record.langs, list) and len(post.record.langs) > 0:
                                post_data['lang'] = post.record.langs[0]
                            else:
                                post_data['lang'] = str(post.record.langs)
                        else:
                            post_data['lang'] = getattr(post.record, 'lang', '')
                        
                        page_posts.append(post_data)
                
                # Add the posts from this page to the complete list
                posts.extend(page_posts)
                posts_collected += len(page_posts)
                
                # Show progress
                if api_calls_needed > 1:
                    print(f"ℹ️ Retrieved {posts_collected} of {original_limit} requested posts")
                
                # If there's no cursor or we've reached the limit, finish
                if not cursor or posts_collected >= original_limit:
                    break
                    time.sleep(0.5)  # Half-second pause between calls
            
            if posts:
                # Get the date range to display
                if len(posts) > 1:
                    dates = [post['created_at'] for post in posts]
                    oldest = min(dates)
                    newest = max(dates)
                    print(f"📅 Date range: {oldest} to {newest}")
            
            print(f"✅ Retrieved {len(posts)} posts from list '{list_name}' by @{handle}")
            
            # Organize posts by author
            results = {}
            for post in posts:
                author_handle = post['author']['handle']
                if author_handle not in results:
                    results[author_handle] = []
                results[author_handle].append(post)
                
            return results
            
        except Exception as e:
            print(f"❌ Error retrieving posts from list: {str(e)}")
            import traceback
            traceback.print_exc()
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
            
            # DIRECT APPROACH: Use the feed.get_list_feed endpoint which is designed specifically for lists
            try:
                # Set up parameters for pagination
                params = {
                    "list": list_uri,
                    "limit": min(100, limit)  # API limit is 100 per request
                }
                
                print(f"🔍 Using direct list feed API endpoint...")
                
                all_posts = []
                cursor = None
                
                # Fetch posts with pagination
                while len(all_posts) < limit:
                    if cursor:
                        params["cursor"] = cursor
                    
                    # Call the list feed API which gives posts from list members
                    try:
                        list_feed_response = self.client.app.bsky.feed.get_list_feed(params)
                        feed_items = getattr(list_feed_response, 'feed', [])
                        
                        if not feed_items:
                            print(f"No more posts found in list")
                            break
                            
                        # Extract posts from feed
                        for item in feed_items:
                            if hasattr(item, 'post') and hasattr(item.post, 'author'):
                                # Extract relevant data for each post
                                author_handle = item.post.author.handle
                                author_display_name = getattr(item.post.author, 'display_name', author_handle)
                                
                                # Create standardized post object with all details
                                post_data = {
                                    'uri': item.post.uri,
                                    'cid': item.post.cid,
                                    'author': {
                                        'did': item.post.author.did,
                                        'handle': author_handle,
                                        'display_name': author_display_name
                                    },
                                    'indexed_at': item.post.indexed_at
                                }
                                
                                # Extract the record data (contains the actual post content)
                                record = item.post.record
                                
                                # Get basic post details
                                if hasattr(record, 'text'):
                                    post_data['text'] = record.text
                                else:
                                    post_data['text'] = ''
                                    
                                # Get created_at timestamp
                                if hasattr(record, 'createdAt'):
                                    post_data['created_at'] = record.createdAt
                                elif 'indexed_at' in post_data and post_data['indexed_at']:
                                    # Fallback to indexed_at if createdAt not available
                                    post_data['created_at'] = post_data['indexed_at']
                                else:
                                    post_data['created_at'] = ''
                                    
                                # Extract engagement metrics
                                post_data['likes'] = getattr(item.post, 'likeCount', 0)
                                post_data['reposts'] = getattr(item.post, 'repostCount', 0)
                                post_data['replies'] = getattr(item.post, 'replyCount', 0)
                                
                                # Process external links/URLs
                                post_data['urls'] = []
                                facets = getattr(record, 'facets', [])
                                if facets:
                                    for facet in facets:
                                        if hasattr(facet, 'features'):
                                            for feature in facet.features:
                                                # Extract links
                                                if hasattr(feature, '$type') and 'app.bsky.richtext.facet#link' in getattr(feature, '$type', ''):
                                                    if hasattr(feature, 'uri'):
                                                        post_data['urls'].append(feature.uri)
                                
                                # Also extract URLs using regex as backup
                                import re
                                url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./\%\?\&\=\+\#]*)?'
                                if post_data.get('text'):
                                    regex_urls = re.findall(url_pattern, post_data['text'])
                                    # Add URLs not found in facets
                                    for url in regex_urls:
                                        if url not in post_data['urls']:
                                            post_data['urls'].append(url)
                                            
                                # Extract any embedded media (images)
                                post_data['images'] = []
                                if hasattr(record, 'embed'):
                                    embed = record.embed
                                    if hasattr(embed, '$type') and 'app.bsky.embed.images' in getattr(embed, '$type', ''):
                                        if hasattr(embed, 'images'):
                                            for img in embed.images:
                                                if hasattr(img, 'fullsize'):
                                                    post_data['images'].append(img.fullsize)
                                                elif hasattr(img, 'image') and hasattr(img.image, 'ref'):
                                                    # Alternative way to get the image URL
                                                    author_did = item.post.author.did
                                                    cid_str = str(img.image.ref.toString())
                                                    image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                                    post_data['images'].append(image_url)
                                                    
                                # Extract mentions
                                post_data['mentions'] = []
                                if facets:
                                    for facet in facets:
                                        if hasattr(facet, 'features'):
                                            for feature in facet.features:
                                                if hasattr(feature, '$type') and 'app.bsky.richtext.facet#mention' in getattr(feature, '$type', ''):
                                                    if hasattr(feature, 'did'):
                                                        mention = feature.handle if hasattr(feature, 'handle') else feature.did
                                                        post_data['mentions'].append(mention)
                                                        
                                # Determine post type (text, reply, repost, etc.)
                                post_type = 'post'  # Default type
                                if hasattr(record, 'reply'):
                                    post_type = 'reply'
                                    # Store the ID of the post being replied to
                                    if hasattr(record.reply, 'parent') and hasattr(record.reply.parent, 'uri'):
                                        post_data['replied_to_id'] = record.reply.parent.uri
                                    else:
                                        post_data['replied_to_id'] = ''
                                else:
                                    post_data['replied_to_id'] = ''
                                    
                                post_data['post_type'] = post_type
                                
                                # Add language information if available
                                if hasattr(record, 'langs') and record.langs:
                                    # Use the first language in the list if it's a list
                                    if isinstance(record.langs, list) and len(record.langs) > 0:
                                        post_data['lang'] = record.langs[0]
                                    else:
                                        post_data['lang'] = str(record.langs)
                                else:
                                    post_data['lang'] = getattr(record, 'lang', '')
                                
                                # Generate web URL for convenient access
                                post_data['web_url'] = f"https://bsky.app/profile/{author_handle}/post/{item.post.uri.split('/')[-1]}"
                                all_posts.append(post_data)
                                
                        # Check if we reached the desired limit
                        if len(all_posts) >= limit:
                            break
                            
                        # Get cursor for next page if available
                        cursor = getattr(list_feed_response, 'cursor', None)
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
    
    def get_list_details(self, handle: str, list_id: str) -> Dict[str, Any]:
        """
        Get details of a Bluesky list.
        
        Args:
            handle: Handle of the list owner
            list_id: ID of the list
            
        Returns:
            Dict: Information about the list
        """
        try:
            # Get the list DID if handle is provided
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
            
            # Get the list details
            response = self.client.app.bsky.graph.get_list({"list": list_uri})
            
            if not hasattr(response, 'list'):
                return {'name': list_id}
            
            # Extract list details
            list_data = {
                'name': getattr(response.list, 'name', list_id),
                'purpose': getattr(response.list, 'purpose', ''),
                'description': getattr(response.list, 'description', ''),
                'creator': handle
            }
            
            return list_data
            
        except Exception as e:
            print(f"❌ Error getting list details: {str(e)}")
            return {'name': list_id}
    
    def get_posts_from_bluesky_list_url(self, list_url: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts directly from a Bluesky list using the list URL.
        
        Args:
            list_url: URL of the Bluesky list (e.g., https://bsky.app/profile/user.bsky.social/lists/123abc)
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dict: Dictionary with usernames as keys and lists of posts as values
        """
        # Remove all types of unwanted characters from the URL
        # using the specialized cleaning method
        list_url = sanitize_uri_component(list_url)
        print('Processed list URL:', list_url)
        
        list_info = parse_bluesky_list_url(list_url)
        if not list_info:
            print('❌ Invalid list URL:', list_url)
            print("Expected format: https://bsky.app/profile/user.bsky.social/lists/123abc")
            return {}
        
        # Clean the handle and list_id of any unwanted characters with the specialized method
        handle = sanitize_uri_component(list_info['handle'])
        list_id = sanitize_uri_component(list_info['list_id'])
        
        print('Clean handle:', handle)
        print('Clean list ID:', list_id)
        
        # Get posts directly from the list
        return self.get_posts_from_bluesky_list(handle, list_id, limit)
