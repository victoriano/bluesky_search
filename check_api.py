#!/usr/bin/env python3
from atproto import Client

def main():
    client = Client()
    
    # Print available methods in client.app.bsky.graph
    print("Methods in client.app.bsky.graph:")
    print(dir(client.app.bsky.graph))
    
    # Print other relevant namespace methods
    print("\nMethods in client.app.bsky.feed:")
    print(dir(client.app.bsky.feed))

if __name__ == "__main__":
    main()
