import os
import sys
import json
from atproto import Client

# Add the parent directory to path to import BlueskyPostsFetcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bluesky_posts import BlueskyPostsFetcher

def debug_post_structure(post, prefix=""):
    """
    Print a detailed structure of a post for debugging
    """
    print(f"{prefix}URI: {post.uri}")
    print(f"{prefix}Author: {post.author.handle}")
    
    # Check for post type indicators
    print(f"{prefix}== POST TYPE INFORMATION ==")
    if hasattr(post, "reason"):
        print(f"{prefix}Reason attribute found: {post.reason}")
        # This could indicate a repost
        
    if hasattr(post.record, "reply"):
        print(f"{prefix}Reply attribute found: This is a REPLY")
        print(f"{prefix}Reply details: {post.record.reply}")
    elif hasattr(post, "reason") and hasattr(post.reason, "py_type") and "repost" in post.reason.py_type:
        print(f"{prefix}This is a REPOST")
    else:
        print(f"{prefix}This appears to be an ORIGINAL post")
    
    if hasattr(post, "record"):
        print(f"{prefix}\nText: {post.record.text}")
        
        # Check if post has facets
        if hasattr(post.record, "facets") and post.record.facets:
            print(f"{prefix}\n== FACETS INFORMATION ==")
            print(f"{prefix}FACETS FOUND: {len(post.record.facets)}")
            
            for i, facet in enumerate(post.record.facets):
                print(f"{prefix}  Facet {i}:")
                
                # Check for index
                if hasattr(facet, "index"):
                    print(f"{prefix}    Index: {facet.index}")
                
                # Check features
                if hasattr(facet, "features"):
                    print(f"{prefix}    Features: {len(facet.features)} found")
                    
                    for j, feature in enumerate(facet.features):
                        print(f"{prefix}      Feature {j}:")
                        # Check if this is a mention
                        if hasattr(feature, "py_type") and "mention" in feature.py_type:
                            print(f"{prefix}      ** MENTION FOUND **")
                        
                        # Print all attributes
                        for attr in dir(feature):
                            if not attr.startswith("_"):
                                try:
                                    value = getattr(feature, attr)
                                    print(f"{prefix}        {attr}: {value}")
                                except:
                                    print(f"{prefix}        {attr}: <error accessing>")
        else:
            print(f"{prefix}NO FACETS FOUND")
            
        # Look for other interesting fields
        print(f"\n{prefix}== OTHER POST FIELDS ==")
        interesting_fields = ["embed", "entities", "langs", "tags", "createdAt"]
        for field in interesting_fields:
            if hasattr(post.record, field):
                print(f"{prefix}{field}: {getattr(post.record, field)}")
    else:
        print(f"{prefix}NO RECORD FOUND")

    print(f"{prefix}-----------------------------------")

def get_post_with_link():
    """
    Get the specific post mentioned by the user and analyze its structure
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

    # Initialize fetcher with client
    fetcher = BlueskyPostsFetcher(client)
    
    # First, get the specific post
    # URL: https://bsky.app/profile/robysinatra.bsky.social/post/3ljkav62fkk24
    handle = "robysinatra.bsky.social"
    post_id = "3ljkav62fkk24"
    
    print(f"Getting post {post_id} from {handle}...")
    try:
        # Construct the URI for the post
        post_uri = f"at://did:plc:{client.get_profile(handle).did.replace('did:plc:', '')}/app.bsky.feed.post/{post_id}"
        thread = client.get_post_thread(post_uri)
        
        if hasattr(thread, "thread") and hasattr(thread.thread, "post"):
            print("\n===== ANALYSIS OF SPECIFIC POST =====")
            debug_post_structure(thread.thread.post)
        else:
            print("Could not find post thread structure")
    except Exception as e:
        print(f"Error getting specific post: {e}")
    
    # Get some recent posts with links to compare
    print("\n===== SEARCHING FOR POSTS WITH LINKS =====")
    search_results = client.app.bsky.feed.search_posts({"q": "https://", "limit": 5})
    
    if hasattr(search_results, "posts"):
        for i, post in enumerate(search_results.posts):
            print(f"\nPOST {i+1} WITH LINK:")
            debug_post_structure(post)
    else:
        print("No search results found")

if __name__ == "__main__":
    print("Starting link debugging...")
    get_post_with_link()
