import os
import sys
import json
from atproto import Client

# Add the parent directory to path to import BlueskyPostsFetcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bluesky_posts import BlueskyPostsFetcher

def debug_post_type(post, prefix=""):
    """
    Print detailed information about a post's type attributes
    """
    print(f"\n{prefix}===== POST TYPE DEBUG =====")
    print(f"{prefix}Post URI: {post.uri}")
    print(f"{prefix}Author: {post.author.handle}")
    
    # Check record attributes
    if hasattr(post, "record"):
        # Check for reply structure
        if hasattr(post.record, "reply"):
            print(f"{prefix}Has 'reply' attribute: YES")
            print(f"{prefix}Reply value: {post.record.reply}")
        else:
            print(f"{prefix}Has 'reply' attribute: NO")
            
        # Check for reason (repost indicator)
        if hasattr(post, "reason"):
            print(f"{prefix}Has 'reason' attribute: YES")
            print(f"{prefix}Reason value: {post.reason}")
            if hasattr(post.reason, "py_type"):
                print(f"{prefix}Reason py_type: {post.reason.py_type}")
        else:
            print(f"{prefix}Has 'reason' attribute: NO")
    
    # Look for other attributes that might indicate post type
    print(f"\n{prefix}All top-level attributes:")
    for attr in dir(post):
        if not attr.startswith("_") and not callable(getattr(post, attr)):
            try:
                value = getattr(post, attr)
                print(f"{prefix}- {attr}: {type(value).__name__}")
            except:
                print(f"{prefix}- {attr}: <error accessing>")
    
    print(f"{prefix}===== END DEBUG =====\n")

def main():
    """
    Get various post types and debug them
    """
    # Create client and fetcher
    print("Creating Bluesky client...")
    client = Client()
    try:
        # Try to load credentials from file
        creds_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.txt")
        with open(creds_file, "r") as f:
            lines = f.readlines()
            username = lines[0].strip()
            password = lines[1].strip()
            
        print(f"Logging in as {username}...")
        client.login(username, password)
    except Exception as e:
        print(f"Error logging in: {e}")
        return

    # Initialize fetcher
    fetcher = BlueskyPostsFetcher(client)
    
    # Get feed posts to analyze
    print("Getting feed posts...")
    feed = client.app.bsky.feed.get_author_feed({"actor": username, "limit": 5})
    
    if hasattr(feed, "feed") and feed.feed:
        for i, feed_item in enumerate(feed.feed):
            print(f"\nExamining feed item {i+1}:")
            debug_post_type(feed_item.post)
            
            # Check if it's a repost
            if hasattr(feed_item, "reason"):
                print("THIS APPEARS TO BE A REPOST in the feed!")
            
            # Get raw post structure for the record
            raw_data = {}
            try:
                for attr in dir(feed_item):
                    if not attr.startswith("_") and not callable(getattr(feed_item, attr)):
                        raw_data[attr] = str(getattr(feed_item, attr))
                print(f"Feed item raw structure:\n{json.dumps(raw_data, indent=2)}")
            except:
                print("Could not get raw structure")
    else:
        print("No feed items found")
    
    # Try to get some replies
    print("\nSearching for reply posts...")
    search_results = client.app.bsky.feed.search_posts({"q": "replying to", "limit": 3})
    
    if hasattr(search_results, "posts"):
        for i, post in enumerate(search_results.posts):
            print(f"\nExamining potential reply post {i+1}:")
            debug_post_type(post)
    else:
        print("No reply posts found")

if __name__ == "__main__":
    main()
