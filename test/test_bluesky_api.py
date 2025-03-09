#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky API Test Script

This script tests the various ways of querying the Bluesky API using the BlueskyPostsFetcher class.
It provides examples of each query method and verifies that they work correctly.

IMPORTANT: Authentication with Bluesky is REQUIRED for ALL API operations, even for public content.
You MUST provide your Bluesky username/email and password to run these tests.

Usage:
    uv run test_bluesky_api.py -u "your_username" -p "your_password"
    
    # To run a specific test only:
    uv run test_bluesky_api.py -u "your_username" -p "your_password" --test user

Note: Your credentials are only used locally for API authentication and are never stored.
"""

import os
import sys
import time
import json
import argparse
from typing import Dict, List, Any, Optional

# Add parent directory to path to import the BlueskyPostsFetcher class
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bluesky_posts import BlueskyPostsFetcher

# Default test parameters (modify these as needed)
DEFAULT_TEST_PARAMS = {
    "username": "",  # Your Bluesky username or email (REQUIRED)
    "password": "",  # Your Bluesky password (REQUIRED)
    "test_user": "victoriano.bsky.social",  # A public user to test with
    "test_users": ["victoriano.bsky.social", "martasvm.bsky.social", "bsky.app"],  # List of test users
    "test_list_url": "https://bsky.app/profile/victoriano.bsky.social/lists/3ldzsbqd4ky2p",  # A public list to test with
    "test_search_query": "granada",  # A query to test search functionality
    "post_limit": 5,  # Limit posts for testing to avoid long run times
    "output_dir": os.path.join(os.path.dirname(__file__), "results"),  # Directory to store test results inside test folder
    "default_export_format": "csv",  # Default format for exporting test results (csv, json, or parquet)
}


class BlueskyAPITester:
    """Class to test the BlueskyPostsFetcher functionality."""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize the tester with test parameters.
        
        Args:
            params: Dictionary of test parameters (uses defaults if not provided)
        """
        self.params = params or DEFAULT_TEST_PARAMS
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.params["output_dir"]):
            os.makedirs(self.params["output_dir"])
        
        # Initialize the fetcher without logging in
        self.fetcher = BlueskyPostsFetcher()
        self.is_authenticated = False
        
        print(f"🧪 Bluesky API Test initialized")
    
    def print_section(self, title: str) -> None:
        """Print a formatted section header."""
        print("\n" + "=" * 80)
        print(f"🔍 TEST: {title}")
        print("=" * 80)
    
    def test_authentication(self) -> bool:
        """Test authentication to the Bluesky API."""
        self.print_section("Authentication")
        
        username = self.params["username"]
        password = self.params["password"]
        
        if not username or not password:
            print("❌ ERROR: Authentication credentials are REQUIRED for ALL Bluesky API operations.")
            print("❌ Please provide your Bluesky username/email and password.")
            print("❌ Run the script with: uv run test_bluesky_api.py -u \"your_username\" -p \"your_password\"")
            return False
        
        print(f"📝 Attempting to authenticate as {username}...")
        self.is_authenticated = self.fetcher.login(username, password)
        
        if self.is_authenticated:
            print("✅ Authentication test passed!")
        else:
            print("❌ Authentication test failed! Please check your credentials.")
        
        return self.is_authenticated
    
    def test_get_user_posts(self) -> bool:
        """Test retrieving posts from a single user."""
        self.print_section("Get User Posts")
        
        test_user = self.params["test_user"]
        post_limit = self.params["post_limit"]
        
        print(f"📝 Retrieving {post_limit} posts from @{test_user}...")
        posts = self.fetcher.get_user_posts(test_user, limit=post_limit)
        
        success = len(posts) > 0
        if success:
            print(f"✅ Successfully retrieved {len(posts)} posts from @{test_user}")
            print(f"📊 First post: \"{posts[0]['text'][:50]}...\"")
            
            # Save example to file
            self._save_example("user_posts", posts, format='csv')
        else:
            print(f"❌ Failed to retrieve posts from @{test_user}")
        
        return success
    
    def test_get_posts_from_users(self) -> bool:
        """Test retrieving posts from multiple users."""
        self.print_section("Get Posts from Multiple Users")
        
        test_users = self.params["test_users"]
        post_limit = self.params["post_limit"]
        
        print(f"📝 Retrieving {post_limit} posts from each of {len(test_users)} users...")
        results = self.fetcher.get_posts_from_users(test_users, limit_per_user=post_limit)
        
        total_posts = sum(len(posts) for posts in results.values())
        success = total_posts > 0
        
        if success:
            print(f"✅ Successfully retrieved {total_posts} posts from {len(results)} users")
            for user, posts in results.items():
                print(f"  - @{user}: {len(posts)} posts")
            
            # Save example to file
            self._save_example("multiple_users_posts", results, format='csv')
        else:
            print(f"❌ Failed to retrieve posts from users")
        
        return success
    
    def test_get_posts_from_list(self) -> bool:
        """Test retrieving posts from a Bluesky list."""
        self.print_section("Get Posts from Bluesky List")
        
        if not self.is_authenticated:
            print("⚠️  Authentication required for this test. Skipping.")
            return False
        
        list_url = self.params["test_list_url"]
        post_limit = self.params["post_limit"]
        
        print(f"📝 Retrieving posts from list: {list_url}...")
        results = self.fetcher.get_posts_from_bluesky_list_url(list_url, limit=post_limit)
        
        success = isinstance(results, dict) and len(results) > 0
        
        if success:
            total_posts = sum(len(posts) for posts in results.values())
            print(f"✅ Successfully retrieved {total_posts} posts from {len(results)} users in the list")
            
            # Save example to file
            self._save_example("list_posts", results, format='csv')
        else:
            print(f"❌ Failed to retrieve posts from list")
        
        return success
    
    def test_search_posts(self) -> bool:
        """Test searching for posts with various criteria."""
        self.print_section("Search Posts")
        
        query = self.params["test_search_query"]
        post_limit = self.params["post_limit"]
        
        print(f"📝 Searching for '{query}' with limit {post_limit}...")
        posts = self.fetcher.search_posts(query, limit=post_limit)
        
        success = len(posts) > 0
        if success:
            print(f"✅ Successfully found {len(posts)} posts matching '{query}'")
            print(f"📊 First match: \"{posts[0]['text'][:50]}...\"")
            
            # Save example to file
            self._save_example("search_posts", posts, format='csv')
        else:
            print(f"❌ Failed to find posts matching '{query}'")
        
        return success
    
    def test_advanced_search(self) -> bool:
        """Test advanced search with multiple criteria."""
        self.print_section("Advanced Search with Multiple Criteria")
        
        query = self.params["test_search_query"]
        post_limit = self.params["post_limit"]
        
        # Define advanced search criteria
        search_params = {
            "query": query,
            "limit": post_limit,
            "language": "en",  # English language posts
            "since": "2023-01-01",  # Posts since 2023
        }
        
        print(f"📝 Advanced search for '{query}' in English since 2023...")
        posts = self.fetcher.search_posts(**search_params)
        
        success = len(posts) > 0
        if success:
            print(f"✅ Successfully found {len(posts)} posts with advanced criteria")
            print(f"📊 First match: \"{posts[0]['text'][:50]}...\"")
            
            # Save example to file
            self._save_example("advanced_search_posts", posts, format='csv')
        else:
            print(f"❌ Failed to find posts with advanced criteria")
        
        return success
    
    def test_large_search(self) -> bool:
        """Test retrieving a large number of search results (500 posts)."""
        self.print_section("Large Search (500 Results)")
        
        query = self.params["test_search_query"]
        large_limit = 500  # Set a large limit for this test
        
        print(f"📝 Performing large search for '{query}' with limit {large_limit}...")
        # This might take some time as it will paginate through results
        start_time = time.time()
        posts = self.fetcher.search_posts(query, limit=large_limit)
        end_time = time.time()
        
        success = len(posts) > 0
        if success:
            elapsed_time = end_time - start_time
            print(f"✅ Successfully retrieved {len(posts)} posts matching '{query}'")
            print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")
            print(f"📊 Retrieved {len(posts) / elapsed_time:.2f} posts per second on average")
            
            # Save all posts to CSV file
            self._save_example("large_search_posts", posts, format='csv')  # Save all posts to CSV
            print(f"📄 Saved all {len(posts)} posts to CSV file")
            
            # Print some statistics about the results
            if len(posts) > 0:
                dates = [post['created_at'] for post in posts if 'created_at' in post]
                if dates:
                    earliest = min(dates)
                    latest = max(dates)
                    print(f"📅 Date range: {earliest} to {latest}")
        else:
            print(f"❌ Failed to find posts matching '{query}' in large search")
        
        return success
        
    def test_search_sort_options(self) -> bool:
        """Test searching for posts with different sort options."""
        self.print_section("Search with Sort Options")
        
        query = self.params["test_search_query"]
        post_limit = self.params["post_limit"]
        
        # Test with 'latest' sort (default)
        print(f"📝 Searching for '{query}' with 'latest' sort (default)...")
        latest_posts = self.fetcher.search_posts(query, limit=post_limit, sort='latest')
        
        # Test with 'top' sort
        print(f"📝 Searching for '{query}' with 'top' sort...")
        top_posts = self.fetcher.search_posts(query, limit=post_limit, sort='top')
        
        success_latest = len(latest_posts) > 0
        success_top = len(top_posts) > 0
        
        if success_latest and success_top:
            print(f"✅ Successfully found posts with both sort options:")
            print(f"  - Latest sort: {len(latest_posts)} posts")
            print(f"  - Top sort: {len(top_posts)} posts")
            
            # Compare results
            if latest_posts and top_posts:
                # Check if the first posts are different
                if latest_posts[0]['uri'] != top_posts[0]['uri']:
                    print(f"📊 Different posts at top position - sort is working as expected")
                    print(f"  - Latest first post: \"{latest_posts[0]['text'][:50]}...\"")
                    print(f"  - Top first post: \"{top_posts[0]['text'][:50]}...\"")
                    
                    # Check date difference if available
                    if 'created_at' in latest_posts[0] and 'created_at' in top_posts[0]:
                        latest_date = latest_posts[0]['created_at']
                        top_date = top_posts[0]['created_at']
                        print(f"  - Latest first post date: {latest_date}")
                        print(f"  - Top first post date: {top_date}")
                else:
                    print(f"⚠️ Same post at top position in both sort options")
            
            # Save examples to file
            self._save_example("latest_sort_posts", latest_posts, format='csv')
            self._save_example("top_sort_posts", top_posts, format='csv')
        else:
            if not success_latest:
                print(f"❌ Failed to find posts with 'latest' sort")
            if not success_top:
                print(f"❌ Failed to find posts with 'top' sort")
        
        return success_latest and success_top

    def test_export_formats(self) -> bool:
        """Test exporting results in different formats."""
        self.print_section("Export Formats")
        
        # First get some data to export
        test_user = self.params["test_user"]
        post_limit = self.params["post_limit"]
        
        print(f"📝 Getting posts from @{test_user} for export testing...")
        posts = self.fetcher.get_user_posts(test_user, limit=post_limit)
        
        if not posts:
            print("❌ Failed to get posts for export testing")
            return False
        
        # Format results as expected by export methods
        results = {test_user: posts}
        
        # Test JSON export
        json_file = os.path.join(self.params["output_dir"], "test_export.json")
        print(f"📝 Exporting to JSON: {json_file}")
        json_result = self.fetcher.export_results(results, format='json', filename=json_file)
        
        # Test CSV export
        csv_file = os.path.join(self.params["output_dir"], "test_export.csv")
        print(f"📝 Exporting to CSV: {csv_file}")
        csv_result = self.fetcher.export_results(results, format='csv', filename=csv_file)
        
        # Test Parquet export
        parquet_file = os.path.join(self.params["output_dir"], "test_export.parquet")
        print(f"📝 Exporting to Parquet: {parquet_file}")
        parquet_result = self.fetcher.export_results(results, format='parquet', filename=parquet_file)
        
        # Check results
        success = all([
            json_result and os.path.exists(json_file),
            csv_result and os.path.exists(csv_file),
            parquet_result and os.path.exists(parquet_file)
        ])
        
        if success:
            print("✅ Successfully exported results in all formats")
            print(f"  - JSON: {json_file}")
            print(f"  - CSV: {csv_file}")
            print(f"  - Parquet: {parquet_file}")
        else:
            print("⚠️ Some export formats failed:")
            print(f"  - JSON: {'✅' if json_result else '❌'}")
            print(f"  - CSV: {'✅' if csv_result else '❌'}")
            print(f"  - Parquet: {'✅' if parquet_result else '❌'}")
        
        return success
    
    def _save_example(self, name: str, data: Any, format: str = 'csv') -> None:
        """Save example data to a file using the specified format (csv by default)."""
        if format == 'json':
            filename = os.path.join(self.params["output_dir"], f"{name}_example.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"📄 Example saved to {filename}")
        elif format == 'csv':
            # For CSV export, we need to format the data appropriately
            # If data is a list of posts
            if isinstance(data, list):
                result_dict = {"posts": data}
            else:
                # If data is already a dictionary (e.g., for multiple users)
                result_dict = data
            
            filename = os.path.join(self.params["output_dir"], f"{name}_example.csv")
            success = self.fetcher.export_results(result_dict, format='csv', filename=filename)
            if success:
                print(f"📄 Example saved to {filename}")
            else:
                # Fallback to JSON if CSV export fails
                fallback_filename = os.path.join(self.params["output_dir"], f"{name}_example.json")
                with open(fallback_filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"⚠️ CSV export failed, saved as JSON to {fallback_filename}")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all the test methods."""
        self.print_section("RUNNING ALL TESTS")
        
        # Initialize authentication (required for all tests)
        auth_result = self.test_authentication()
        
        # If authentication fails, we can't run any tests
        if not auth_result:
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return {"authentication": False}
        
        # Run all tests
        results = {
            "authentication": auth_result,
            "get_user_posts": self.test_get_user_posts(),
            "get_posts_from_users": self.test_get_posts_from_users(),
            "search_posts": self.test_search_posts(),
            "advanced_search": self.test_advanced_search(),
            "search_sort_options": self.test_search_sort_options(),
            "large_search": self.test_large_search(),
            "export_formats": self.test_export_formats(),
            "get_posts_from_list": self.test_get_posts_from_list(),
        }
        
        return results
    
    def print_results_summary(self, results: Dict[str, bool]) -> None:
        """Print a summary of test results."""
        self.print_section("TEST RESULTS SUMMARY")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        print(f"Passed: {passed}/{total} tests ({passed/total*100:.1f}%)")
        print("\nDetailed Results:")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  - {test_name}: {status}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Bluesky API functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests with your Bluesky credentials:
  uv run test_bluesky_api.py -u "your_username" -p "your_password"
  
  # Run only the user posts test:
  uv run test_bluesky_api.py -u "your_username" -p "your_password" --test user
  
  # Run tests with a custom user and post limit:
  uv run test_bluesky_api.py -u "your_username" -p "your_password" --test-user "bsky.app" --limit 10
  
  # Run tests with credentials from credentials.txt file:
  uv run test_bluesky_api.py --creds-file "credentials.txt"
"""
    )
    
    # Required authentication parameters
    auth_group = parser.add_argument_group("Authentication (REQUIRED)")
    auth_group.add_argument('-u', '--username', help="Bluesky username or email", required=False)
    auth_group.add_argument('-p', '--password', help="Bluesky password", required=False)
    auth_group.add_argument('--creds-file', help="Path to file containing credentials", default="credentials.txt")
    
    # Test configuration parameters
    config_group = parser.add_argument_group("Test Configuration (Optional)")
    config_group.add_argument('--test-user', help="User handle to test with")
    config_group.add_argument('--test-list', help="Bluesky list URL to test with")
    config_group.add_argument('--search-query', help="Search query for testing")
    config_group.add_argument('--limit', type=int, help="Limit of posts to retrieve")
    config_group.add_argument('--output-dir', help="Directory to store test results")
    
    # Test selection arguments
    test_group = parser.add_argument_group("Test Selection")
    test_group.add_argument('--test', choices=[
        'all', 'auth', 'user', 'users', 'list', 'search', 'advanced-search', 'search-sort', 'large-search', 'export'
    ], default='all', help="Run specific test(s)")
    
    args = parser.parse_args()
    
    # If creds-file is specified, read username and password from it
    if args.creds_file:
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
                elif args.username and not args.password:
                    print(f"Warning: No password found in {args.creds_file}. The file should contain the username on the first line and password on the second line.")
        except Exception as e:
            print(f"Error reading credentials file: {e}")
    
    return args


def main() -> None:
    """Main function to run the API tests."""
    args = parse_arguments()
    
    # Debug output to verify credentials are loaded
    print(f"\nDEBUG - Username: {args.username}")
    print(f"DEBUG - Password available: {'Yes' if args.password else 'No'}")
    
    # Update test parameters from command-line arguments
    test_params = DEFAULT_TEST_PARAMS.copy()
    if args.username:
        test_params["username"] = args.username
    if args.password:
        test_params["password"] = args.password
    if args.test_user:
        test_params["test_user"] = args.test_user
    if args.test_list:
        test_params["test_list_url"] = args.test_list
    if args.search_query:
        test_params["test_search_query"] = args.search_query
    if args.limit:
        test_params["post_limit"] = args.limit
    if args.output_dir:
        test_params["output_dir"] = args.output_dir
    
    print("\n🧪🧪🧪 BLUESKY API TEST SUITE 🧪🧪🧪")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check for credentials before proceeding
    if not test_params["username"] or not test_params["password"]:
        print("\n❌ ERROR: Authentication credentials are REQUIRED for ALL Bluesky API operations.")
        print("❌ Please provide your Bluesky username/email and password.")
        print("❌ Run the script with: uv run test_bluesky_api.py -u \"your_username\" -p \"your_password\"")
        print("\nOr create a credentials.txt file with username on first line and password on second line.")
        return
    
    # Initialize the tester
    tester = BlueskyAPITester(test_params)
    
    # Run selected test(s)
    results = {}
    
    if args.test == 'all':
        results = tester.run_all_tests()
    else:
        # Initialize authentication for all tests
        auth_result = tester.test_authentication()
        results["authentication"] = auth_result
        
        if not auth_result:
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            tester.print_results_summary(results)
            return
        
        # Run specific test
        if args.test == 'auth':
            pass  # Already ran above
        elif args.test == 'user':
            results["get_user_posts"] = tester.test_get_user_posts()
        elif args.test == 'users':
            results["get_posts_from_users"] = tester.test_get_posts_from_users()
        elif args.test == 'list':
            results["get_posts_from_list"] = tester.test_get_posts_from_list()
        elif args.test == 'search':
            results["search_posts"] = tester.test_search_posts()
        elif args.test == 'advanced-search':
            results["advanced_search"] = tester.test_advanced_search()
        elif args.test == 'search-sort':
            results["search_sort_options"] = tester.test_search_sort_options()
        elif args.test == 'large-search':
            results["large_search"] = tester.test_large_search()
        elif args.test == 'export':
            results["export_formats"] = tester.test_export_formats()
    
    # Print summary
    tester.print_results_summary(results)
    print(f"\nFinished at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not any(results.values()):
        print("\n⚠️  All tests failed. Make sure your Bluesky credentials are correct.")
        print("⚠️  If you're sure your credentials are correct, Bluesky's API might be experiencing issues.")
    elif all(results.values()):
        print("\n🎉 All tests passed successfully! Your Bluesky API integration is working properly.")
    else:
        print("\n⚠️  Some tests failed. Check the results above for details.")


if __name__ == "__main__":
    main()
