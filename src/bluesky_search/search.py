#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Search Module

This module provides functionality for searching posts on the Bluesky social network.
"""

import time
import re
from typing import List, Dict, Any, Optional

from .utils.url import get_web_url_from_uri
from .utils.text import extract_urls_from_text

class BlueskySearch:
    """Class for searching posts on Bluesky."""
    
    def __init__(self, client):
        """
        Initialize the BlueskySearch module.
        
        Args:
            client: An authenticated Bluesky client instance
        """
        self.client = client
    
    def search_posts(self, query: str, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for posts matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results (uses pagination for >100)
            **kwargs: Additional search parameters:
                - from_user: Filter by author
                - mention: Filter by mentioned user
                - language: Filter by language
                - since: Filter by start date (YYYY-MM-DD)
                - until: Filter by end date (YYYY-MM-DD)
                - domain: Filter by URL domain
            
        Returns:
            List[Dict]: List of matching posts
        """
        try:
            # Prepare search parameters
            search_params = {
                "q": query,
                "limit": min(100, limit)  # API limit is 100 per request
            }
            
            # Add optional filters
            if 'from_user' in kwargs and kwargs['from_user']:
                search_params["from"] = kwargs['from_user'].strip('@')
            if 'mention' in kwargs and kwargs['mention']:
                search_params["mention"] = kwargs['mention'].strip('@')
            if 'language' in kwargs and kwargs['language']:
                search_params["lang"] = kwargs['language']
            
            # Add date filters
            if 'since' in kwargs and kwargs['since']:
                search_params["since"] = kwargs['since']
            if 'until' in kwargs and kwargs['until']:
                search_params["until"] = kwargs['until']
                
            # Initialize variables for pagination
            posts = []
            cursor = None
            posts_collected = 0
            original_limit = limit
            
            # Calculate number of API calls needed
            api_calls_needed = max(1, (original_limit + 99) // 100)  # Round up
            
            # Iterate until we reach the limit or run out of results
            for call_num in range(api_calls_needed):
                # Calculate limit for this call (max 100)
                current_call_limit = min(100, original_limit - posts_collected)
                
                if current_call_limit <= 0:
                    break
                
                # Update limit for this request
                search_params['limit'] = current_call_limit
                
                # Add cursor if this isn't the first call
                if cursor:
                    search_params['cursor'] = cursor
                
                # Make the search request
                search_response = self.client.app.bsky.feed.search_posts(search_params)
                
                # Get cursor for next page if it exists
                cursor = getattr(search_response, 'cursor', None)
                
                # Process the posts from this page
                page_posts = []
                
                if not hasattr(search_response, 'posts') or len(search_response.posts) == 0:
                    # No more results
                    break
                
                
                # Process each post
                for post in search_response.posts:
                    # Extract post data
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
                    
                    # Add language information if available
                    if hasattr(post.record, 'langs') and post.record.langs:
                        # Use the first language in the list if it's a list
                        if isinstance(post.record.langs, list) and len(post.record.langs) > 0:
                            post_data['lang'] = post.record.langs[0]
                        else:
                            post_data['lang'] = str(post.record.langs)
                    else:
                        post_data['lang'] = ''
                    
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
                        
                        # Initialize reply fields with default empty values
                        post_data['replied_to_handle'] = ''
                        post_data['replied_to_id'] = ''
                        
                        # When a post is a reply, we need to fetch the parent post data to get replied-to info
                        if hasattr(post.record, 'reply'):
                            reply_info = post.record.reply
                            
                            # Get the parent post reference from the reply structure
                            if hasattr(reply_info, 'parent') and hasattr(reply_info.parent, 'uri'):
                                parent_uri = reply_info.parent.uri
                                
                                # Extract the DID from the parent URI
                                # URI format: at://did:plc:XXXX/app.bsky.feed.post/YYYY
                                import re
                                did_match = re.search(r'at://([^/]+)', parent_uri)
                                if did_match:
                                    parent_did = did_match.group(1)
                                    post_data['replied_to_id'] = parent_did
                                    
                                    # Since we now have the DID, attempt to get the handle too
                                    # First, try to get it from the original post's text
                                    if post_data['text'] and post_data['text'].startswith('@'):
                                        handle_match = re.match(r'^@([\w.-]+\.\w+(?:\.\w+)?)', post_data['text'])
                                        if handle_match:
                                            post_data['replied_to_handle'] = handle_match.group(1)
                                    
                                    # If we couldn't get it from the text, we need to make an API call
                                    # This is a more expensive operation but ensures we get accurate data
                                    if not post_data['replied_to_handle']:
                                        try:
                                            # Try different API methods to resolve the DID to a handle
                                            try:
                                                # Method 1: Direct getProfile call (may work with some client implementations)
                                                profile = self.client.get_profile({'actor': parent_did})
                                                if hasattr(profile, 'handle'):
                                                    post_data['replied_to_handle'] = profile.handle
                                                elif isinstance(profile, dict) and 'handle' in profile:
                                                    post_data['replied_to_handle'] = profile['handle']
                                            except Exception as e1:
                                                # Method 2: Try the Bluesky XRPC API with explicit actor address
                                                try:
                                                    # This requires the client to support app.bsky.actor namespace
                                                    # Different client implementations may have different APIs
                                                    # First, try typical bsky.social clients
                                                    if hasattr(self.client, 'app') and hasattr(self.client.app, 'bsky') and hasattr(self.client.app.bsky, 'actor'):
                                                        profile_data = self.client.app.bsky.actor.getProfile({'actor': parent_did})
                                                        if hasattr(profile_data, 'handle'):
                                                            post_data['replied_to_handle'] = profile_data.handle
                                                        elif isinstance(profile_data, dict) and 'handle' in profile_data:
                                                            post_data['replied_to_handle'] = profile_data['handle']
                                                except Exception as e2:
                                                    # Final fallback - try to get the handle from the full parent post
                                                    try:
                                                        # Get the full URI of the parent post
                                                        parent_uri = reply_info.parent.uri
                                                        post_view = self.client.get_post_thread({'uri': parent_uri})
                                                        if hasattr(post_view, 'thread') and hasattr(post_view.thread, 'post') and hasattr(post_view.thread.post, 'author'):
                                                            post_data['replied_to_handle'] = post_view.thread.post.author.handle
                                                    except Exception as e3:
                                                        # If all methods fail, we'll resort to text-based extraction later
                                                        pass
                                        except Exception as e:
                                            # If all API calls fail, fall back to other methods
                                            # We'll continue with text-based extraction below
                                            pass
                        
                        # Fallback method: Extract from mentions in text
                        if (not post_data['replied_to_handle'] or not post_data['replied_to_id']) and post_data['text']:
                            raw_mentions = post_data.get('mentions', [])
                            
                            # Method 1: Check text using regex (common in replies) if it starts with @username
                            if post_data['text'].startswith('@') and not post_data['replied_to_handle']:
                                import re
                                patterns = [
                                    r'^@([\w.-]+\.\w+\.\w+)',  # user.domain.tld
                                    r'^@([\w.-]+\.\w+)',       # user.domain
                                ]
                                
                                for pattern in patterns:
                                    match = re.match(pattern, post_data['text'])
                                    if match:
                                        post_data['replied_to_handle'] = match.group(1)
                                        break
                            
                            # Method 2: Use mentions array data if available
                            if not post_data['replied_to_handle'] and raw_mentions:
                                if isinstance(raw_mentions, list) and len(raw_mentions) > 0:
                                    # First mention in a reply is usually who was replied to
                                    first_mention = raw_mentions[0]
                                    if isinstance(first_mention, str):
                                        post_data['replied_to_handle'] = first_mention.replace('@', '')
                                    elif isinstance(first_mention, dict):
                                        if 'handle' in first_mention:
                                            post_data['replied_to_handle'] = first_mention['handle']
                                        if 'did' in first_mention and not post_data['replied_to_id']:
                                            post_data['replied_to_id'] = first_mention['did']
                        
                        # Ensure no @ symbol in the handle
                        if post_data['replied_to_handle'] and post_data['replied_to_handle'].startswith('@'):
                            post_data['replied_to_handle'] = post_data['replied_to_handle'][1:]
                    else:
                        # For non-reply posts, check if they're reposts
                        
                        # Extract the users of interest from the parameters
                        from_user = kwargs.get('from_user')
                        users_of_interest = []
                        if from_user:
                            # If we have a from_user specified, that's our user of interest
                            users_of_interest.append(from_user)
                            
                        # If the post author is in our list of interest, it's an original
                        # Otherwise, it might be a repost
                        author_handle = post.author.handle
                        
                        if users_of_interest and any(user.lower() in author_handle.lower() for user in users_of_interest):
                            # The author is in our list of interest
                            post_data['post_type'] = 'original'
                        else:
                            # It might be a repost or just a post from another user
                            # Check other repost indicators
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
                    
                    # Domain filtering if specified
                    if 'domain' in kwargs and kwargs['domain'] and urls:
                        domain = kwargs['domain'].lower()
                        # Filter posts to only include those with URLs containing the specified domain
                        if not any(domain in url.lower() for url in urls):
                            # Skip this post if it doesn't contain the domain
                            continue
                    
                    # Always include arrays in a consistent format, empty list if no items
                    post_data['urls'] = urls if urls else []
                    post_data['mentions'] = mentions if mentions else []
                    post_data['images'] = post_data.get('images', [])
                    
                    page_posts.append(post_data)
                
                # Add the posts from this page to the complete list
                posts.extend(page_posts)
                posts_collected += len(page_posts)
                
                # Show progress
                if api_calls_needed > 1:
                    print(f"ℹ️ Retrieved {posts_collected} of {original_limit} requested posts")
                
                # If no cursor or we've reached the limit, end the loop
                if not cursor or posts_collected >= original_limit:
                    break
                    
                time.sleep(0.5)  # Half-second pause between calls
            
            print(f"✅ Found a total of {len(posts)} posts matching the search")
            return posts
            
        except Exception as e:
            print(f"❌ Error searching posts: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
