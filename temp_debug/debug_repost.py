import os
import sys
import json
from atproto import Client

# Add the parent directory to path to import BlueskyPostsFetcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bluesky_posts import BlueskyPostsFetcher

def debug_post_structure(post, prefix="", feed_item=None):
    """
    Print detailed post structure focusing on repost detection
    """
    print(f"\n{prefix}===== POST STRUCTURE =====")
    print(f"{prefix}Post URI: {post.uri}")
    print(f"{prefix}Author: {post.author.handle}")
    
    # Inspect top-level feed item if provided (may contain repost info)
    if feed_item:
        print(f"\n{prefix}--- FEED ITEM INSPECTION ---")
        
        if hasattr(feed_item, "post") and feed_item.post.uri == post.uri:
            print(f"{prefix}Feed item contains this post")
            # Check if this is a repost via the 'reason' attribute
            if hasattr(feed_item, "reason"):
                print(f"{prefix}REPOST INDICATOR - Has reason attribute: {feed_item.reason}")
                if hasattr(feed_item.reason, "py_type"):
                    print(f"{prefix}Reason py_type: {feed_item.reason.py_type}")
                if hasattr(feed_item.reason, "by"):
                    print(f"{prefix}Reposted by: {feed_item.reason.by.handle}")
                    print(f"{prefix}Original author: {post.author.handle}")
                    if feed_item.reason.by.handle != post.author.handle:
                        print(f"{prefix}*** THIS IS A REPOST - different authors ***")
            
            # Check if this post's author is different from the viewing user
            if hasattr(feed_item, "user_handle"):
                user_handle = feed_item.user_handle
                print(f"{prefix}User handle: {user_handle}")
                print(f"{prefix}Post author: {post.author.handle}")
                if user_handle != post.author.handle:
                    print(f"{prefix}*** POTENTIAL REPOST - Author mismatch ***")
    
    # Check for custom fields in the record that might indicate a repost
    if hasattr(post, "record"):
        print(f"\n{prefix}--- RECORD INSPECTION ---")
        # Try to access all attributes
        record_dict = {}
        for attr in dir(post.record):
            if not attr.startswith("_") and not callable(getattr(post.record, attr)):
                try:
                    record_dict[attr] = str(getattr(post.record, attr))
                except:
                    record_dict[attr] = "<error accessing>"
        
        print(f"{prefix}Record attributes: {json.dumps(record_dict, indent=2)}")
        
        # Special check for $type indicators
        if hasattr(post.record, "py_type"):
            print(f"{prefix}Record py_type: {post.record.py_type}")
            if "repost" in str(post.record.py_type).lower():
                print(f"{prefix}*** REPOST INDICATOR in record type ***")

    # Try to find any other attributes that might help identify reposts
    print(f"\n{prefix}--- OTHER POTENTIAL INDICATORS ---")
    repost_related_attrs = []
    for attr in dir(post):
        attr_lower = attr.lower()
        if not attr.startswith("_") and not callable(getattr(post, attr)):
            if "repost" in attr_lower or "share" in attr_lower or "reason" in attr_lower:
                try:
                    value = getattr(post, attr)
                    repost_related_attrs.append(f"{attr}: {value}")
                except:
                    repost_related_attrs.append(f"{attr}: <error accessing>")
    
    if repost_related_attrs:
        print(f"{prefix}Repost-related attributes:")
        for attr in repost_related_attrs:
            print(f"{prefix}- {attr}")
    else:
        print(f"{prefix}No obvious repost-related attributes found")
    
    print(f"{prefix}===== END DEBUG =====\n")

def main():
    """
    Debug repost structure in Bluesky posts
    """
    # Create client
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
    
    # Try to get a timeline which often contains reposts
    print("\nGetting timeline posts (likely to contain reposts)...")
    timeline = client.app.bsky.feed.get_timeline({"limit": 15})
    
    found_reposts = 0
    if hasattr(timeline, "feed") and timeline.feed:
        for i, feed_item in enumerate(timeline.feed):
            post = feed_item.post
            
            # Look for indicators that this might be a repost
            is_potential_repost = False
            if hasattr(feed_item, "reason"):
                is_potential_repost = True
                found_reposts += 1
                print(f"\n🔄 FOUND POTENTIAL REPOST #{found_reposts} in feed item {i+1}:")
                debug_post_structure(post, prefix="  ", feed_item=feed_item)
            
            if found_reposts >= 3:
                break
    
    if found_reposts == 0:
        print("No reposts found in the timeline. Let's check for specific users who might repost content...")
        
        # Try to search for terms that might find reposts
        print("\nSearching for posts containing 'reposted' or related terms...")
        search_results = client.app.bsky.feed.search_posts({"q": "reposted", "limit": 5})
        
        if hasattr(search_results, "posts"):
            for i, post in enumerate(search_results.posts):
                print(f"\nExamining search result {i+1}:")
                debug_post_structure(post)

if __name__ == "__main__":
    main()
