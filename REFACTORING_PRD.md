# Bluesky Search Refactoring PRD

## Project Overview
Refactor the `bluesky_posts.py` file (1400+ lines) into a well-structured Python package that can be published to PyPI. The goal is to improve maintainability, readability, and make the code more accessible for future development.

## Key Objectives
- [x] Create a proper package structure
- [x] Separate concerns into logical modules
- [x] Maintain all existing functionality
- [x] Prepare for PyPI publication
- [x] Make the codebase easier to navigate and maintain

## Implementation Plan

### 1. Create Package Structure
- [x] Create new git branch `refactor-package-structure`
- [x] Set up directory structure
- [x] Create placeholder files
- [x] Create package configuration files

### 2. Core Client Component
- [x] Extract authentication and base client functionality
- [x] Create BlueskyClient class
- [x] Move core methods from original file

### 3. Fetcher Component
- [x] Create BlueskyPostsFetcher class
- [x] Move post retrieval methods
- [x] Ensure compatibility with client component

### 4. Search Component
- [x] Extract search-related functionality
- [x] Create dedicated search methods
- [x] Integrate with fetcher component

### 5. List Component
- [x] Extract list-related functionality
- [x] Create dedicated list handling methods
- [x] Integrate with fetcher component

### 6. Utils Components
- [x] Create URL handling utilities
- [x] Extract text processing functions
- [x] Move authentication helpers

### 7. Export Components
- [x] Extract export functionality for different formats
- [x] Create dedicated exporters for JSON, CSV, and Parquet
- [x] Ensure compatibility with data structures

### 8. CLI Component
- [x] Extract command-line interface
- [x] Update to use the refactored components
- [x] Maintain existing CLI functionality

### 9. Package Configuration
- [x] Create pyproject.toml
- [x] Set up proper dependencies
- [x] Configure for PyPI publication

### 10. Documentation
- [ ] Update README with usage examples
- [ ] Add proper docstrings throughout the code
- [ ] Create a LICENSE file

### 11. Testing
- [x] Verify existing tests work with the refactored code
- [x] Ensure all features work as expected

## Dependencies
- Python 3.7+
- atproto client
- polars (optional for data export)
- uv (for package management)

## Timeline
- Start Date: March 9, 2025
- Target Completion: TBD

## Testing Strategy
- Manual testing to ensure feature parity
- Basic unit tests for core functionality

## Risks & Mitigations
- **Risk**: Breaking existing functionality during refactoring
  - **Mitigation**: Regular testing throughout the process
- **Risk**: Missing edge cases in the original implementation
  - **Mitigation**: Careful code review during extraction

## Success Criteria
- All existing functionality is preserved
- Code is well-organized into logical modules
- Package can be installed via pip/uv
- Documentation is clear and comprehensive
