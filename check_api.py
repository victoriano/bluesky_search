#!/usr/bin/env python3
from atproto import Client

def main():
    client = Client()
    
    # Print available methods in client.app.bsky.graph
    print("Methods in client.app.bsky.graph:")
    print(dir(client.app.bsky.graph))
    
    # Print feed methods
    print("\nMethods in client.app.bsky.feed:")
    print(dir(client.app.bsky.feed))
    
    # Check search_posts method
    print("\nSearch Posts Method:")
    if hasattr(client.app.bsky.feed, 'search_posts'):
        print("Method exists!")
        print("Parameters that can be passed to search_posts:")
        try:
            # Try to get information about the search_posts method
            params = client.app.bsky.feed.search_posts({})
        except Exception as e:
            print(f"Error info: {str(e)}")
    else:
        print("Method does not exist")

if __name__ == "__main__":
    main()
