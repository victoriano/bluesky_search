# Bluesky Posts Fetcher Tests

This directory contains test scripts and examples for testing the various ways of querying the Bluesky API using the `BlueskyPostsFetcher` class.

## Important Note

**Authentication with Bluesky is REQUIRED for ALL API operations, even for public content.**

All tests and examples in this directory require you to provide your Bluesky username/email and password. Your credentials are only used locally for API authentication and are never stored.

## Test Files

1. **test_bluesky_api.py** - A comprehensive test suite that systematically tests all API query methods and provides detailed results
2. **examples.py** - A simpler, more practical script that demonstrates each query method with clear examples

### Understanding the Difference

While both files use the same underlying `BlueskyPostsFetcher` class, they serve different purposes:

- **test_bluesky_api.py** is designed for **automated testing** to verify that all functionality works correctly. It runs systematic checks with assertions and provides pass/fail results.

- **examples.py** serves as **educational documentation** showing how to use the library in real-world scenarios. It provides clear, focused examples that are easier to follow than test code.

You don't strictly need both files for the application to work, but maintaining both is a software best practice:
- Tests ensure reliability and prevent regressions
- Examples help new users understand how to use your library

## Running the Tests

### Using Credentials File

Both scripts can use a `credentials.txt` file in the root directory of the project containing your Bluesky username on the first line and password on the second line:

```bash
# Run without manually specifying credentials (using credentials.txt):
uv run test/test_bluesky_api.py
uv run test/examples.py
```

### Comprehensive Test Suite

The `test_bluesky_api.py` script provides a comprehensive test suite for all Bluesky API functionality:

```bash
# Run all tests
uv run test/test_bluesky_api.py -u "your_username" -p "your_password"

# Run only a specific test
uv run test/test_bluesky_api.py -u "your_username" -p "your_password" --test user
```

Available test options:
- `auth` - Test authentication only
- `user` - Test fetching posts from a single user
- `users` - Test fetching posts from multiple users
- `list` - Test fetching posts from a Bluesky list
- `search` - Test basic search functionality
- `advanced-search` - Test advanced search with filters
- `export` - Test exporting data in different formats

Additional configuration options:
```bash
# Customize test parameters
uv run test/test_bluesky_api.py -u "your_username" -p "your_password" \
  --test-user "different.user" \
  --limit 10 \
  --search-query "custom query" \
  --output-dir "custom_results"
```

### Example Usage Script

The `examples.py` script provides practical examples of each API method with clear, readable output:

```bash
uv run test/examples.py -u "your_username" -p "your_password"
```

This will run all examples sequentially and generate sample exports in the `test/examples_output` directory.

## Test Output

- The test suite generates detailed results in the terminal showing which tests passed or failed
- Examples of retrieved data are saved in the `test/results` directory (or custom directory if specified)
- The examples script saves sample exports in the `test/examples_output` directory

## Troubleshooting

If tests fail, check the following:

1. **Authentication Issues**: Make sure your Bluesky credentials are correct
2. **API Availability**: The Bluesky API might be experiencing issues or rate limiting
3. **Network Connectivity**: Ensure you have a stable internet connection
4. **Python Environment**: Make sure all required dependencies are installed

## Dependencies

These tests require the same dependencies as the main script:
- Python 3.8 or higher
- `atproto` library for API interactions
- `polars` library for CSV and Parquet exports

## Updating Tests

If you modify the `BlueskyPostsFetcher` class with new functionality, consider:

1. Adding corresponding tests to `test_bluesky_api.py` to ensure your changes work correctly and don't break existing functionality
2. Updating `examples.py` to demonstrate how to use the new features

This dual approach ensures both quality assurance and good documentation for your library.
