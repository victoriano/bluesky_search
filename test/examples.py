#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky API Examples

This script provides simple examples of how to use the BlueskyPostsFetcher class
to interact with the Bluesky API in different ways.

Usage:
    uv run examples.py -u "your_username" -p "your_password"
"""

import argparse
import os
import json
import sys

# Add parent directory to path to import the BlueskyPostsFetcher class
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bluesky_posts import BlueskyPostsFetcher

def setup_fetcher(username, password):
    """Set up and authenticate the BlueskyPostsFetcher."""
    print("\n==== Setting up Bluesky Posts Fetcher ====")
    fetcher = BlueskyPostsFetcher()
    
    # Authenticate
    print(f"Authenticating as {username}...")
    success = fetcher.login(username, password)
    
    if not success:
        print("Authentication failed. Exiting.")
        exit(1)
    
    print("Authentication successful!")
    return fetcher

def example_user_posts(fetcher):
    """Example: Get posts from a single user."""
    print("\n==== Example: Get Posts from a User ====")
    user = "victoriano.bsky.social"
    limit = 3
    
    print(f"Fetching {limit} posts from @{user}...")
    posts = fetcher.get_user_posts(user, limit=limit)
    
    print(f"Found {len(posts)} posts")
    if posts:
        for i, post in enumerate(posts, 1):
            print(f"\n{i}. Post by @{post['author']['handle']} ({post['created_at']}):")
            print(f"   {post['text']}")
            print(f"   Likes: {post['likes']} | Reposts: {post['reposts']} | Replies: {post['replies']}")
            print(f"   URL: {post['web_url']}")

def example_multiple_users(fetcher):
    """Example: Get posts from multiple users."""
    print("\n==== Example: Get Posts from Multiple Users ====")
    users = ["victoriano.bsky.social", "martasvm.bsky.social"]
    limit = 2
    
    print(f"Fetching {limit} posts from each user: {', '.join(users)}...")
    results = fetcher.get_posts_from_users(users, limit_per_user=limit)
    
    for user, posts in results.items():
        print(f"\nPosts from @{user}: {len(posts)}")
        if posts:
            post = posts[0]  # Show just the first post as an example
            print(f"Latest post ({post['created_at']}): {post['text'][:100]}...")

def example_bluesky_list(fetcher):
    """Example: Get posts from a Bluesky list."""
    print("\n==== Example: Get Posts from a Bluesky List ====")
    list_url = "https://bsky.app/profile/victoriano.bsky.social/lists/3ldzsbqd4ky2p"
    limit = 5
    
    print(f"Fetching posts from list: {list_url}...")
    results = fetcher.get_posts_from_bluesky_list_url(list_url, limit=limit)
    
    total_posts = sum(len(posts) for posts in results.values())
    print(f"Found {total_posts} posts from {len(results)} users in the list")
    
    # Show first post from each user
    for user, posts in results.items():
        if posts:
            post = posts[0]
            print(f"\n@{user}: {post['text'][:100]}...")

def example_search(fetcher):
    """Example: Search for posts."""
    print("\n==== Example: Search for Posts ====")
    query = "bluesky"
    limit = 5
    
    print(f"Searching for '{query}' (limit: {limit})...")
    posts = fetcher.search_posts(query, limit=limit)
    
    print(f"Found {len(posts)} posts")
    if posts:
        for i, post in enumerate(posts[:3], 1):  # Show first 3 results
            print(f"\n{i}. Post by @{post['author']['handle']} ({post['created_at']}):")
            print(f"   {post['text'][:100]}...")

def example_advanced_search(fetcher):
    """Example: Advanced search with filters."""
    print("\n==== Example: Advanced Search with Filters ====")
    
    # Define search parameters
    params = {
        "query": "api",
        "limit": 5,
        "language": "en",
        "since": "2023-01-01"
    }
    
    print(f"Advanced search for '{params['query']}' in English since 2023...")
    posts = fetcher.search_posts(**params)
    
    print(f"Found {len(posts)} posts")
    if posts:
        for i, post in enumerate(posts[:3], 1):  # Show first 3 results
            print(f"\n{i}. Post by @{post['author']['handle']} ({post['created_at']}):")
            print(f"   {post['text'][:100]}...")

def example_export_formats(fetcher):
    """Example: Export data in different formats."""
    print("\n==== Example: Export Formats ====")
    
    # Get some data to export
    user = "bsky.app"
    posts = fetcher.get_user_posts(user, limit=3)
    
    if not posts:
        print("No posts to export.")
        return
    
    results = {user: posts}
    print(f"Got {len(posts)} posts from @{user} for export")
    
    # Create output directory inside test folder
    output_dir = os.path.join(os.path.dirname(__file__), "examples_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to different formats
    formats = ["json", "csv", "parquet"]
    for format in formats:
        filename = os.path.join(output_dir, f"example_export.{format}")
        print(f"Exporting to {format.upper()}: {filename}")
        
        result = fetcher.export_results(results, format=format, filename=filename)
        if result:
            print(f"✅ Successfully exported to {format.upper()}")
        else:
            print(f"❌ Failed to export to {format.upper()}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Bluesky API examples")
    parser.add_argument("-u", "--username", required=False, help="Bluesky username or email")
    parser.add_argument("-p", "--password", required=False, help="Bluesky password")
    parser.add_argument("--creds-file", default="../usuarios.txt", help="Path to file containing credentials")
    
    args = parser.parse_args()
    
    # If username or password not provided, try to read from credentials file
    if not args.username or not args.password:
        try:
            # Adjust path to look for the file in the project root directory
            creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', os.path.basename(args.creds_file)))
            with open(creds_path, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 1:
                    args.username = lines[0].strip()
                    print(f"Username loaded from {args.creds_file}: {args.username}")
                
                if len(lines) >= 2:
                    args.password = lines[1].strip()
                    print(f"Password loaded from {args.creds_file}")
                elif not args.password:
                    print(f"Warning: No password found in {args.creds_file}. The file should contain the username on the first line and password on the second line.")
                    exit(1)
        except Exception as e:
            print(f"Error reading credentials file: {e}")
            exit(1)
    
    # Ensure we have both username and password
    if not args.username or not args.password:
        print("Error: Both username and password are required.")
        exit(1)
        
    return args

def main():
    """Run all examples."""
    args = parse_args()
    
    # Set up the fetcher
    fetcher = setup_fetcher(args.username, args.password)
    
    # Run examples
    example_user_posts(fetcher)
    example_multiple_users(fetcher)
    example_bluesky_list(fetcher)
    example_search(fetcher)
    example_advanced_search(fetcher)
    example_export_formats(fetcher)
    
    print("\n==== All Examples Completed ====")
    print("Check the 'examples_output' directory for exported files.")

if __name__ == "__main__":
    main()
