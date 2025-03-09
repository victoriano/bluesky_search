#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Client Module

This module contains the core client functionality for interacting with
the Bluesky social network via the AT Protocol.
"""

import time
from typing import Dict, Any, Optional

from atproto import Client

class BlueskyClient:
    """Base client for interacting with Bluesky via AT Protocol."""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize the Bluesky client.
        
        Args:
            username: Username or email for authentication
            password: Password for authentication
        """
        self.client = Client()
        self._authenticated = False
        
        if username and password:
            self.login(username, password)
    
    def login(self, username: str, password: str) -> bool:
        """
        Log in to Bluesky.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            self.client.login(username, password)
            self._authenticated = True
            print(f"✅ Authentication successful as {username}")
            return True
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            self._authenticated = False
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # Start with the simple check (set by the login method)
        if self._authenticated:
            return True
            
        # If not explicitly authenticated, try to check if the client session seems valid
        try:
            # Check for session data that would indicate authentication
            if hasattr(self.client, 'session') and self.client.session:
                self._authenticated = True
                return True
                
            # Attempt to see if me data is available
            if hasattr(self.client, '_me') and self.client._me is not None:
                self._authenticated = True
                return True
                
            # No evidence of valid authentication
            return False
        except Exception:
            return False
    
    def get_profile(self, actor: str) -> Dict[str, Any]:
        """
        Get a user's profile.
        
        Args:
            actor: Username (handle) of the profile to get
            
        Returns:
            Dict: Profile information
        """
        try:
            # Remove @ if present at the beginning of the handle
            if actor.startswith('@'):
                actor = actor[1:]
                
            profile = self.client.get_profile(actor=actor)
            return profile
        except Exception as e:
            print(f"❌ Error getting profile for {actor}: {str(e)}")
            return {}
    
    def _check_rate_limit_info(self, exception: Exception) -> Optional[Dict[str, Any]]:
        """
        Check for rate limit information in an exception.
        
        Args:
            exception: Exception that might contain rate limit information
            
        Returns:
            Optional[Dict]: Rate limit information if available, None otherwise
        """
        rate_limit_info = {}
        
        try:
            # Check for rate limit in response headers
            if hasattr(exception, 'response') and hasattr(exception.response, 'headers'):
                headers = exception.response.headers
                
                # Check for rate limit headers
                if 'ratelimit-limit' in headers:
                    rate_limit_info['limit'] = headers['ratelimit-limit']
                if 'ratelimit-remaining' in headers:
                    rate_limit_info['remaining'] = headers['ratelimit-remaining']
                if 'ratelimit-reset' in headers:
                    rate_limit_info['reset'] = headers['ratelimit-reset']
                    
                if rate_limit_info:
                    print(f"⚠️ Rate limit info: {rate_limit_info}")
                    
                    # If we're close to hitting the rate limit, pause briefly
                    if 'remaining' in rate_limit_info and int(rate_limit_info['remaining']) < 5:
                        reset_time = int(rate_limit_info['reset']) if 'reset' in rate_limit_info else 60
                        print(f"⏱️ Rate limit nearly exhausted, pausing for {reset_time} seconds...")
                        time.sleep(reset_time)
                        
                    return rate_limit_info
        except Exception as e:
            print(f"⚠️ Error checking rate limit info: {str(e)}")
            
        return None
