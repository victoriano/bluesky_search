#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text processing utilities for Bluesky Search.

This module contains functions for processing and manipulating text data.
"""

import re

def sanitize_uri_component(input_str: str) -> str:
    """
    Sanitize a URI component by removing quotes, extra spaces, and other problematic characters.
    
    Args:
        input_str: String to sanitize
        
    Returns:
        str: Sanitized string
    """
    if not input_str:
        return ""
    
    # Convert to string if not already
    input_str = str(input_str)
    
    # Strip quotes and whitespace
    sanitized = input_str.strip().strip('"').strip("'").strip()
    
    # Remove any duplicate quotes inside the string
    sanitized = re.sub(r'["\']+', '', sanitized)
    
    # Remove any control characters
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    
    return sanitized

def extract_urls_from_text(text: str) -> list:
    """
    Extract URLs from text using regular expressions.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        list: List of extracted URLs
    """
    if not text:
        return []
    
    url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./%?&=+#]*)?'
    urls = re.findall(url_pattern, text)
    
    return urls
