import polars as pl
import sys

# Get the file path from command line argument
file_path = sys.argv[1] if len(sys.argv) > 1 else 'data/bluesky_posts_20250309_174919.parquet'

# Read the parquet file
df = pl.read_parquet(file_path)

# Print columns
print('Columns in the dataframe:', df.columns)

# Check for posts with images
images_posts = df.filter(pl.col('images').is_not_null())
print(f'\nFound {len(images_posts)} posts with images')

# Print sample if available
if len(images_posts) > 0:
    sample = images_posts.head(1).to_dicts()[0]
    print('\nSample post with images:')
    print(f"Author: {sample['author_handle']}")
    print(f"Text: {sample['text']}")
    print(f"Images: {sample['images']}")
else:
    print('No posts with images found in this sample')

# Check for posts with urls
urls_posts = df.filter(pl.col('urls').is_not_null())
print(f'\nFound {len(urls_posts)} posts with URLs')

# Print sample if available
if len(urls_posts) > 0:
    sample = urls_posts.head(1).to_dicts()[0]
    print('\nSample post with URLs:')
    print(f"Author: {sample['author_handle']}")
    print(f"Text: {sample['text']}")
    print(f"URLs: {sample['urls']}")
else:
    print('No posts with URLs found in this sample')

# Check for posts with mentions
mentions_posts = df.filter(pl.col('mentions').is_not_null())
print(f'\nFound {len(mentions_posts)} posts with mentions')

# Print sample if available
if len(mentions_posts) > 0:
    sample = mentions_posts.head(1).to_dicts()[0]
    print('\nSample post with mentions:')
    print(f"Author: {sample['author_handle']}")
    print(f"Text: {sample['text']}")
    print(f"Mentions: {sample['mentions']}")
else:
    print('No posts with mentions found in this sample')
