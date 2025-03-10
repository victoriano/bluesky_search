#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Search CLI

This module provides command-line functionality for the bluesky_search package.
"""

import os
import sys
import argparse
import datetime
from typing import List, Dict, Any, Optional

from .fetcher import BlueskyPostsFetcher

def generate_output_filename(base_name: str, export_format: str) -> str:
    """
    Generate an output filename with timestamp.
    
    Args:
        base_name: Base name for the file
        export_format: Export format extension
        
    Returns:
        str: Timestamped filename
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{export_format}"

def main():
    """Main function to run the CLI."""
    parser = argparse.ArgumentParser(description="Fetch posts from Bluesky users")
    
    # Authentication arguments
    parser.add_argument("-u", "--username", help="Bluesky username or email")
    parser.add_argument("-p", "--password", help="Bluesky password")
    
    # Target specification (one of these is required)
    target_group = parser.add_argument_group("target", "Specify the target to fetch posts from")
    target_group.add_argument("-a", "--handle", help="Fetch posts from a single Bluesky user by handle")
    target_group.add_argument("-f", "--file", help="File with a list of Bluesky handles (one per line)")
    target_group.add_argument("-l", "--list", help="Use a Bluesky list URL to fetch posts")
    target_group.add_argument("-s", "--search", help="Search for posts containing a specific query")
    
    # Options
    parser.add_argument("-n", "--limit", type=int, default=20, help="Maximum number of posts to retrieve per user")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    parser.add_argument("-e", "--export", choices=["json", "csv", "parquet"], default="csv", help="Export format")
    parser.add_argument("-x", "--format", dest="export", choices=["json", "csv", "parquet"], help="Export format (legacy option, use -e instead)")
    
    # Additional search filters
    search_group = parser.add_argument_group("search filters", "Additional filters for search queries")
    search_group.add_argument("--from", dest="from_user", help="Filter search results by author")
    search_group.add_argument("--mention", help="Filter search results by mentioned user")
    search_group.add_argument("--language", help="Filter search results by language code")
    search_group.add_argument("--since", help="Filter search results by start date (YYYY-MM-DD)")
    search_group.add_argument("--until", help="Filter search results by end date (YYYY-MM-DD)")
    search_group.add_argument("--domain", help="Filter search results by URL domain")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check for required arguments
    if not (args.handle or args.file or args.list or args.search):
        parser.error("You must specify a target: --handle, --file, --list, or --search")
    
    # Initialize the fetcher
    fetcher = BlueskyPostsFetcher(args.username, args.password)
    
    # Validate authentication
    if not fetcher.is_authenticated():
        print("❌ Authentication failed. Please provide valid Bluesky credentials.")
        return 1
    
    print(f"✅ Authenticated and ready to fetch posts")
    
    # Process the request based on the provided target
    posts = []
    
    try:
        if args.handle:
            # Fetch posts from a single user
            print(f"📥 Fetching posts from @{args.handle}...")
            posts = fetcher.get_user_posts(args.handle, args.limit)
            output_base = f"bluesky_posts_{args.handle}"
            
        elif args.file:
            # Fetch posts from multiple users listed in a file
            if not os.path.exists(args.file):
                print(f"❌ File not found: {args.file}")
                return 1
                
            print(f"📂 Reading handles from file: {args.file}")
            with open(args.file, 'r') as f:
                handles = [line.strip() for line in f if line.strip()]
            
            print(f"👥 Found {len(handles)} handles in the file")
            
            all_posts = []
            for handle in handles:
                print(f"📥 Fetching posts from @{handle}...")
                user_posts = fetcher.get_user_posts(handle, args.limit)
                all_posts.extend(user_posts)
                print(f"    ✅ Retrieved {len(user_posts)} posts")
            
            posts = all_posts
            output_base = "bluesky_posts_multiple_users"
            
        elif args.list:
            # Fetch posts from a Bluesky list
            print(f"📋 Fetching posts from list: {args.list}")
            list_posts = fetcher.get_list_posts(args.list, args.limit)
            posts = list_posts
            
            # Get list name for the output file
            list_info = fetcher.get_list_info(args.list)
            list_name = list_info.get('name', 'unknown_list').replace(' ', '_').lower()
            output_base = f"bluesky_list_{list_name}"
            
        elif args.search:
            # Search for posts
            print(f"🔍 Searching for posts with query: {args.search}")
            
            # Prepare search filters
            search_filters = {}
            if args.from_user:
                search_filters['from_user'] = args.from_user
            if args.mention:
                search_filters['mention'] = args.mention
            if args.language:
                search_filters['language'] = args.language
            if args.since:
                search_filters['since'] = args.since
            if args.until:
                search_filters['until'] = args.until
            if args.domain:
                search_filters['domain'] = args.domain
            
            search_results = fetcher.search_posts(args.search, args.limit, **search_filters)
            posts = search_results
            output_base = f"bluesky_search_{args.search.replace(' ', '_')}"
        
        # Export the results
        if not posts:
            print("❌ No posts found.")
            return 0
        
        print(f"✅ Retrieved {len(posts)} posts in total")
        
        # Determine the output file path
        if args.output:
            output_path = args.output
        else:
            output_path = generate_output_filename(output_base, args.export)
        
        # Export the results
        print(f"💾 Exporting results to {output_path}")
        
        if args.export == "json":
            fetcher.export_to_json(posts, output_path)
        elif args.export == "csv":
            fetcher.export_to_csv(posts, output_path)
        elif args.export == "parquet":
            fetcher.export_to_parquet(posts, output_path)
        
        print(f"✅ Export complete! File saved to: {output_path}")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
