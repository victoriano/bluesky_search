import sys
import os
import json
from atproto import Client, models
from datetime import datetime

# Authenticate with Bluesky
def authenticate(username, password):
    print(f"⏳ Intentando autenticar como {username}")
    client = Client()
    try:
        client.login(username, password)
        print(f"✅ Autenticación exitosa como {username}")
        return client
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        sys.exit(1)

# Main function
def main():
    if len(sys.argv) < 3:
        print("Uso: python debug_image_urls.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    client = authenticate(username, password)
    
    # Search for posts with images
    print("⏳ Buscando posts con imágenes...")
    response = client.app.bsky.feed.search_posts(q="image", limit=3)
    
    debug_info = []
    
    for post in response.posts:
        if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
            for i, img in enumerate(post.record.embed.images):
                print(f"\n🔍 Analizando imagen {i+1} en post de {post.author.handle}")
                
                # Inspect the entire image object
                img_info = {
                    "post_author": post.author.handle,
                    "post_text": post.record.text[:50] + "..." if len(post.record.text) > 50 else post.record.text,
                    "image_index": i,
                    "alt_text": img.alt if hasattr(img, 'alt') else None,
                }
                
                # Debug all properties of the image object
                if hasattr(img, 'image'):
                    print("  • Tiene propiedad 'image'")
                    img_info["has_image_property"] = True
                    
                    img_obj = img.image
                    if hasattr(img_obj, '__dict__'):
                        img_info["image_dict"] = str(img_obj.__dict__)
                    
                    # Check for common image properties
                    for prop in ["ref", "cid", "mimeType", "size", "width", "height"]:
                        if hasattr(img_obj, prop):
                            value = getattr(img_obj, prop)
                            print(f"  • {prop}: {value}")
                            img_info[f"image_{prop}"] = str(value)
                    
                    # Check deeper for ref object
                    if hasattr(img_obj, 'ref'):
                        ref_obj = img_obj.ref
                        img_info["ref_info"] = {}
                        
                        print("  • Propiedades de ref:")
                        for ref_prop in dir(ref_obj):
                            if not ref_prop.startswith('_') and not callable(getattr(ref_obj, ref_prop)):
                                ref_value = getattr(ref_obj, ref_prop)
                                print(f"    - {ref_prop}: {ref_value}")
                                img_info["ref_info"][ref_prop] = str(ref_value)
                
                debug_info.append(img_info)
    
    # Save debug info to file
    with open('temp_debug/image_debug_info.json', 'w') as f:
        json.dump(debug_info, f, indent=2)
    
    print(f"\n✅ Información de depuración guardada en temp_debug/image_debug_info.json")

if __name__ == "__main__":
    main()
