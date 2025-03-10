#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the BlueskyList implementation.

This script tests the updated get_posts_from_bluesky_list and get_posts_from_bluesky_list_url methods.

Usage:
    uv run test_list.py -u "your_username" -p "your_password"
"""

import argparse
import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import the necessary modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bluesky_search.list import BlueskyList
from src.bluesky_search.client import BlueskyClient

def setup_client(username, password):
    """Set up and authenticate the Bluesky client."""
    print("\n==== Setting up Bluesky Client ====")
    client = BlueskyClient()
    
    # Authenticate
    print(f"Authenticating as {username}...")
    success = client.login(username, password)
    
    if not success:
        print("Authentication failed. Exiting.")
        exit(1)
    
    print("Authentication successful!")
    return client

def test_get_posts_from_bluesky_list(list_handler, handle, list_id, limit=5):
    """Test the get_posts_from_bluesky_list method."""
    print(f"\n==== Testing get_posts_from_bluesky_list ====")
    print(f"Getting posts from list: @{handle}/lists/{list_id}")
    
    start_time = datetime.now()
    results = list_handler.get_posts_from_bluesky_list(handle, list_id, limit=limit)
    end_time = datetime.now()
    
    total_posts = sum(len(posts) for posts in results.values())
    print(f"Found {total_posts} posts from {len(results)} users in {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Show first post from each user
    for user, posts in results.items():
        if posts:
            post = posts[0]
            print(f"\n@{user}: {post['text'][:100]}...")
            
            # Print post details
            print(f"  - Post type: {post.get('post_type', 'unknown')}")
            print(f"  - Created at: {post.get('created_at', 'unknown')}")
            print(f"  - Web URL: {post.get('web_url', 'unknown')}")
            
            # Print image URLs if available
            if 'images' in post and post['images']:
                print(f"  - Images: {len(post['images'])} image(s)")
                
            # Print URLs if available
            if 'urls' in post and post['urls']:
                print(f"  - URLs: {len(post['urls'])} URL(s)")
                for url in post['urls'][:2]:  # Show first 2 URLs
                    print(f"    - {url}")
                    
            # Print mentions if available
            if 'mentions' in post and post['mentions']:
                print(f"  - Mentions: {', '.join('@' + m for m in post['mentions'][:3])}")
    
    return results

def test_get_posts_from_bluesky_list_url(list_handler, list_url, limit=5):
    """Test the get_posts_from_bluesky_list_url method."""
    print(f"\n==== Testing get_posts_from_bluesky_list_url ====")
    print(f"Getting posts from list URL: {list_url}")
    
    start_time = datetime.now()
    results = list_handler.get_posts_from_bluesky_list_url(list_url, limit=limit)
    end_time = datetime.now()
    
    total_posts = sum(len(posts) for posts in results.values())
    print(f"Found {total_posts} posts from {len(results)} users in {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Show first post from each user
    for user, posts in results.items():
        if posts:
            post = posts[0]
            print(f"\n@{user}: {post['text'][:100]}...")
    
    return results

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test the BlueskyList implementation")
    parser.add_argument("-u", "--username", required=True, help="Bluesky username or email")
    parser.add_argument("-p", "--password", required=True, help="Bluesky password")
    parser.add_argument("-l", "--list-url", default="https://bsky.app/profile/victoriano.bsky.social/lists/3ldzsbqd4ky2p", 
                        help="URL of a Bluesky list to test")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of posts to retrieve per user")
    return parser.parse_args()

def main():
    """Run the tests."""
    args = parse_args()
    
    # Set up the client
    client = setup_client(args.username, args.password)
    
    # Create a BlueskyList instance
    list_handler = BlueskyList(client)
    
    # Test get_posts_from_bluesky_list_url
    results_from_url = test_get_posts_from_bluesky_list_url(list_handler, args.list_url, args.limit)
    
    # Extract handle and list_id from the URL to test get_posts_from_bluesky_list directly
    # URL format: https://bsky.app/profile/handle/lists/list_id
    parts = args.list_url.split('/')
    if len(parts) >= 6 and 'profile' in parts and 'lists' in parts:
        handle_index = parts.index('profile') + 1
        list_id_index = parts.index('lists') + 1
        
        if handle_index < len(parts) and list_id_index < len(parts):
            handle = parts[handle_index]
            list_id = parts[list_id_index]
            
            # Test get_posts_from_bluesky_list
            results_direct = test_get_posts_from_bluesky_list(list_handler, handle, list_id, args.limit)
            
            # Compare results
            url_users = set(results_from_url.keys())
            direct_users = set(results_direct.keys())
            
            print("\n==== Comparison of Results ====")
            print(f"Users from URL method: {len(url_users)}")
            print(f"Users from direct method: {len(direct_users)}")
            
            if url_users == direct_users:
                print("✅ Both methods returned the same set of users")
            else:
                print("⚠️ The methods returned different sets of users")
                print(f"Users only in URL method: {url_users - direct_users}")
                print(f"Users only in direct method: {direct_users - url_users}")
    
    print("\n==== All Tests Completed ====")

if __name__ == "__main__":
    main() 