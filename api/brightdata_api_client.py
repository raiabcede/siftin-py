"""
BrightData API Integration
Uses BrightData's API for LinkedIn data extraction
"""

import os
import requests
from typing import Optional, List, Dict
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Rate limiting: Track last request time to avoid hitting limits
_last_request_time = None
_min_request_interval = 2.0  # Minimum 2 seconds between requests (30 requests/min max)


class BrightDataAPI:
    """
    BrightData API client for fetching LinkedIn profile data
    Requires BrightData API token and Collector ID
    """
    
    def __init__(self, api_token: Optional[str] = None, collector_id: Optional[str] = None):
        self.api_token = api_token or os.getenv('BRIGHTDATA_API_TOKEN')
        self.collector_id = collector_id or os.getenv('BRIGHTDATA_COLLECTOR_ID')
        
        # Clean API token (remove newlines and spaces)
        if self.api_token:
            self.api_token = self.api_token.replace('\n', '').replace('\r', '').strip()
        
        self.api_base = "https://api.brightdata.com"
        
        # Debug logging
        if self.api_token:
            print(f"[BrightData API] API Token loaded: {self.api_token[:10]}...")
        else:
            print("[BrightData API] ⚠️ No API token found")
        
        if self.collector_id:
            print(f"[BrightData API] Collector ID loaded: {self.collector_id}")
        else:
            print("[BrightData API] ⚠️ No Collector ID found")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for BrightData API requests"""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def _rate_limit_delay(self):
        """Add delay between requests to avoid hitting rate limits"""
        global _last_request_time, _min_request_interval
        
        if _last_request_time is not None:
            elapsed = time.time() - _last_request_time
            if elapsed < _min_request_interval:
                wait_time = _min_request_interval - elapsed
                print(f"[BrightData API] Rate limiting: waiting {wait_time:.2f}s before next request...")
                time.sleep(wait_time)
        
        _last_request_time = time.time()
    
    def trigger_collector(self, linkedin_url: str) -> Optional[Dict]:
        """
        Trigger the BrightData collector for a LinkedIn URL
        
        Args:
            linkedin_url: LinkedIn search URL to scrape
            
        Returns:
            Collection response with collection_id or None if failed
        """
        if not self.api_token or not self.collector_id:
            print("[BrightData API] Missing API token or Collector ID")
            return None
        
        # Apply rate limiting
        self._rate_limit_delay()
        
        # BrightData DCA trigger endpoint
        trigger_url = f"{self.api_base}/dca/trigger?collector={self.collector_id}&queue_next=1"
        
        # Payload format: array of objects with url field
        payload = [{"url": linkedin_url}]
        
        try:
            print(f"[BrightData API] Triggering collector for URL: {linkedin_url}")
            response = requests.post(trigger_url, headers=self._get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            print(f"[BrightData API] Collector triggered successfully")
            return data
        except requests.exceptions.HTTPError as e:
            print(f"[BrightData API] HTTP error triggering collector: {e}")
            if e.response:
                error_text = e.response.text[:200]
                print(f"[BrightData API] Response: {error_text}")
                # If rate limit error, increase delay for next request
                if 'rate' in error_text.lower() or 'limit' in error_text.lower():
                    global _min_request_interval
                    _min_request_interval = min(_min_request_interval * 2, 10.0)  # Max 10 seconds
                    print(f"[BrightData API] Rate limit detected, increased delay to {_min_request_interval}s")
            return None
        except Exception as e:
            print(f"[BrightData API] Error triggering collector: {e}")
            return None
    
    def initiate_collection(self, start_urls: List[str], params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Legacy method - use trigger_collector instead
        Maintained for backward compatibility
        """
        if start_urls and len(start_urls) > 0:
            return self.trigger_collector(start_urls[0])
        return None
    
    def get_collection_data(self, collection_id: str) -> Optional[List[Dict]]:
        """
        Retrieve data from a completed collection
        
        Args:
            collection_id: The ID of the collection job
            
        Returns:
            List of collected data items or None if failed
        """
        if not self.api_token:
            return None
        
        # Apply rate limiting
        self._rate_limit_delay()
        
        # BrightData DCA dataset endpoint
        result_url = f"{self.api_base}/dca/dataset?id={collection_id}"
        
        try:
            print(f"[BrightData API] Fetching results for collection: {collection_id}")
            response = requests.get(result_url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for errors in the response FIRST - before any processing
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                if isinstance(first_item, dict) and 'error' in first_item:
                    error_msg = first_item.get('error', 'Unknown error')
                    print(f"[BrightData API] ⚠️ Error detected in collection response: {error_msg}")
                    print(f"[BrightData API] Full error item: {first_item}")
                    
                    # Check for authentication/login related errors
                    error_lower = error_msg.lower()
                    auth_keywords = ['login', 'auth', 'authentication', 'unauthorized', 'forbidden', '401', '403', 'redirected to login', 'authentication required']
                    if any(keyword in error_lower for keyword in auth_keywords):
                        auth_error = f"BrightData Authentication Error: {error_msg}. Your BrightData collector needs LinkedIn authentication configured. Go to your BrightData dashboard → Collector Settings → LinkedIn Authentication, and add your LinkedIn session cookies or credentials."
                        print(f"[BrightData API] 🔴 Raising authentication error: {auth_error}")
                        raise Exception(auth_error)
                    # Check for rate limit error
                    elif 'rate' in error_lower or 'limit' in error_lower:
                        rate_error = f"BrightData Rate Limit Error: {error_msg}. Please wait a moment and try again, or contact your BrightData Account Manager to increase your rate limit."
                        print(f"[BrightData API] 🔴 Raising rate limit error: {rate_error}")
                        raise Exception(rate_error)
                    else:
                        other_error = f"BrightData Collection Error: {error_msg}"
                        print(f"[BrightData API] 🔴 Raising collection error: {other_error}")
                        raise Exception(other_error)
            
            # BrightData may return data in different formats
            if isinstance(data, dict):
                # Check for common data fields
                if 'data' in data:
                    return data['data']
                elif 'items' in data:
                    return data['items']
                elif 'results' in data:
                    return data['results']
                else:
                    # Return the whole dict if it's a single item
                    return [data]
            elif isinstance(data, list):
                # Check if all items are errors first
                error_items = [item for item in data if isinstance(item, dict) and 'error' in item]
                valid_items = [item for item in data if isinstance(item, dict) and 'error' not in item]
                
                # If we have only error items (no valid data), check the errors
                if error_items and not valid_items:
                    first_error = error_items[0].get('error', '')
                    error_lower = first_error.lower()
                    # Check for authentication errors
                    auth_keywords = ['login', 'auth', 'authentication', 'unauthorized', 'forbidden', '401', '403', 'redirected to login', 'authentication required']
                    if any(keyword in error_lower for keyword in auth_keywords):
                        raise Exception(f"BrightData Authentication Error: {first_error}. Your BrightData collector needs LinkedIn authentication configured. Go to your BrightData dashboard → Collector Settings → LinkedIn Authentication, and add your LinkedIn session cookies or credentials.")
                    # Check for rate limit errors
                    elif 'rate' in error_lower or 'limit' in error_lower:
                        raise Exception(f"BrightData Rate Limit Error: {first_error}. Please wait a moment and try again, or contact your BrightData Account Manager to increase your rate limit.")
                    # Other errors - still raise so they can be handled
                    else:
                        raise Exception(f"BrightData Collection Error: {first_error}")
                
                # If we have valid items, return them (errors are filtered out)
                if valid_items:
                    return valid_items
                # If no valid items and no errors (shouldn't happen), return empty
                return []
            else:
                return []
        except requests.exceptions.HTTPError as e:
            print(f"[BrightData API] HTTP error getting data: {e}")
            if e.response:
                error_text = e.response.text[:500]
                print(f"[BrightData API] Response: {error_text}")
                # Check for rate limit in error response
                if 'rate' in error_text.lower() or 'limit' in error_text.lower():
                    raise Exception(f"BrightData Rate Limit Error. Please wait a moment and try again, or contact your BrightData Account Manager to increase your rate limit.")
            return None
        except Exception as e:
            # Re-raise if it's already a formatted error message
            if "BrightData" in str(e):
                raise
            print(f"[BrightData API] Error getting data: {e}")
            return None
    
    def search_linkedin_profiles(self, search_url: str, max_results: int = 10) -> List[Dict]:
        """
        Search for LinkedIn profiles using BrightData collector
        
        Args:
            search_url: LinkedIn search URL
            max_results: Maximum number of results to return
            
        Returns:
            List of lead dictionaries
        """
        if not self.api_token or not self.collector_id:
            print("[BrightData API] Missing API token or Collector ID")
            return []
        
        print(f"[BrightData API] Triggering collector for search URL: {search_url}")
        
        # Step 1: Trigger the collector
        collection_response = self.trigger_collector(search_url)
        
        if not collection_response:
            print("[BrightData API] Failed to trigger collector")
            return []
        
        # Extract collection_id from response (can be in different formats)
        collection_id = None
        if isinstance(collection_response, dict):
            collection_id = collection_response.get('collection_id') or collection_response.get('_id')
        elif isinstance(collection_response, list) and len(collection_response) > 0:
            collection_id = collection_response[0].get('collection_id') or collection_response[0].get('_id')
        
        if not collection_id:
            print("[BrightData API] No collection ID in response")
            print(f"[BrightData API] Response: {collection_response}")
            return []
        
        print(f"[BrightData API] Collection triggered with ID: {collection_id}")
        print("[BrightData API] Waiting for collection to complete...")
        
        # Step 2: Wait for the data to be ready (polling with exponential backoff)
        max_wait_time = 300  # 5 minutes max
        initial_wait = 20  # Initial wait time (as per example)
        check_interval = 10  # Check every 10 seconds (increased to reduce API calls)
        elapsed_time = 0
        retry_count = 0
        max_retries = 3
        
        # Initial wait before first check
        print(f"[BrightData API] Waiting {initial_wait} seconds before checking results...")
        time.sleep(initial_wait)
        elapsed_time += initial_wait
        
        # Poll for completion
        while elapsed_time < max_wait_time:
            print(f"[BrightData API] Checking results... ({elapsed_time}s elapsed)")
            try:
                data = self.get_collection_data(collection_id)
                
                if data and len(data) > 0:
                    print(f"[BrightData API] Collection completed! Retrieved {len(data)} items")
                    break
                
                # If no data yet, wait and try again
                # Use exponential backoff: increase wait time with each check
                wait_time = check_interval + (retry_count * 2)
                print(f"[BrightData API] No data yet, waiting {wait_time}s before next check...")
                time.sleep(wait_time)
                elapsed_time += wait_time
                retry_count += 1
            except Exception as e:
                # If we get a rate limit or other error, handle it
                error_msg = str(e)
                # Authentication errors should be raised immediately (don't retry)
                if "Authentication" in error_msg or "login" in error_msg.lower() or "auth" in error_msg.lower() or "redirected to login" in error_msg.lower():
                    print(f"[BrightData API] Authentication error detected: {error_msg}")
                    raise  # Re-raise authentication errors immediately
                elif "Rate Limit" in error_msg or "rate" in error_msg.lower():
                    print(f"[BrightData API] Rate limit error detected: {error_msg}")
                    # Increase delay significantly and wait before retrying
                    global _min_request_interval
                    _min_request_interval = min(_min_request_interval * 3, 30.0)  # Max 30 seconds
                    print(f"[BrightData API] Increased delay to {_min_request_interval}s, waiting before retry...")
                    time.sleep(30)  # Wait 30 seconds before retrying
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"[BrightData API] Max retries reached, giving up")
                        raise
                    continue
                # For other errors, log and continue trying
                print(f"[BrightData API] Error checking results: {error_msg}")
                time.sleep(check_interval)
                elapsed_time += check_interval
                retry_count += 1
        
        if elapsed_time >= max_wait_time:
            print("[BrightData API] Collection timeout - trying to retrieve partial results")
            try:
                data = self.get_collection_data(collection_id)
            except Exception as e:
                # Re-raise authentication and rate limit errors
                error_msg = str(e)
                if "Authentication" in error_msg or "login" in error_msg.lower() or "auth" in error_msg.lower() or "redirected to login" in error_msg.lower():
                    raise
                if "Rate Limit" in error_msg or "rate" in error_msg.lower():
                    raise
                data = None
        
        if not data:
            print("[BrightData API] ⚠️ No data retrieved from collection")
            # If we got no data, it might be because of an error that was filtered
            # Try one more time to check for errors explicitly
            try:
                print("[BrightData API] Re-checking for errors in collection response...")
                error_check = self.get_collection_data(collection_id)
                if not error_check:
                    print("[BrightData API] Still no data after re-check - returning empty list")
                    return []
            except Exception as e:
                # If we get an exception on re-check, it's likely an auth/rate limit error
                error_msg = str(e)
                print(f"[BrightData API] Error detected on re-check: {error_msg}")
                if "Authentication" in error_msg or "login" in error_msg.lower() or "auth" in error_msg.lower() or "redirected to login" in error_msg.lower():
                    print("[BrightData API] 🔴 Re-raising authentication error")
                    raise
                if "Rate Limit" in error_msg or "rate" in error_msg.lower():
                    print("[BrightData API] 🔴 Re-raising rate limit error")
                    raise
                # For other errors, log but don't raise (might be transient)
                print(f"[BrightData API] Other error on re-check, returning empty: {error_msg}")
            return []
        
        # Parse the data into lead format
        leads = self._parse_collection_results(data, max_results)
        
        return leads
    
    def _parse_collection_results(self, data: List[Dict], max_results: int) -> List[Dict]:
        """
        Parse BrightData collection results into lead format
        
        Args:
            data: Raw data from BrightData collection
            max_results: Maximum number of leads to return
            
        Returns:
            List of lead dictionaries
        """
        leads = []
        
        # Debug: Print first item structure to understand the format
        if data and len(data) > 0:
            import json
            print(f"[BrightData API] Sample data structure (first item):")
            print(json.dumps(data[0], indent=2)[:500])  # Print first 500 chars
        
        for item in data[:max_results]:
            try:
                if not isinstance(item, dict):
                    print(f"[BrightData API] Skipping non-dict item: {type(item)}")
                    continue
                
                # BrightData may return data in different formats
                # Try multiple extraction strategies
                
                # Strategy 1: Check if data is nested under 'profile' or similar keys
                profile_data = item.get('profile') or item.get('data') or item.get('result') or item
                
                # Strategy 2: Check top-level fields first, then nested
                def get_nested_value(key_variations, default=''):
                    """Try multiple key variations to find a value"""
                    for key in key_variations:
                        # Try top level
                        if key in item:
                            value = item[key]
                            if value:
                                return str(value).strip()
                        # Try in profile_data
                        if key in profile_data:
                            value = profile_data[key]
                            if value:
                                return str(value).strip()
                        # Try nested structures
                        if isinstance(profile_data, dict):
                            for nested_key in profile_data.keys():
                                if key.lower() in nested_key.lower():
                                    value = profile_data[nested_key]
                                    if value:
                                        return str(value).strip()
                    return default
                
                # Extract name - try many variations
                name = get_nested_value([
                    'name', 'full_name', 'fullName', 'displayName', 'display_name',
                    'first_name', 'firstName', 'last_name', 'lastName',
                    'title', 'headline'
                ], 'Unknown')
                
                # If name is still Unknown, try combining first and last
                if name == 'Unknown':
                    first = get_nested_value(['first_name', 'firstName', 'first'], '')
                    last = get_nested_value(['last_name', 'lastName', 'last'], '')
                    if first or last:
                        name = f"{first} {last}".strip()
                
                # Extract LinkedIn URL
                linkedin_url = get_nested_value([
                    'linkedin_url', 'linkedinUrl', 'linkedin', 'url', 'profile_url',
                    'profileUrl', 'profile_link', 'profileLink', 'href'
                ], '')
                
                # Extract title/headline
                title = get_nested_value([
                    'headline', 'title', 'position', 'job_title', 'jobTitle',
                    'current_position', 'currentPosition', 'role', 'occupation'
                ], '')
                
                # Extract company
                company = get_nested_value([
                    'company', 'current_company', 'currentCompany', 'organization',
                    'employer', 'workplace', 'company_name', 'companyName'
                ], '')
                
                # Extract location
                location = get_nested_value([
                    'location', 'geo_location', 'geoLocation', 'city', 'address',
                    'region', 'country', 'location_name', 'locationName'
                ], '')
                
                # Extract description
                description = get_nested_value([
                    'summary', 'description', 'about', 'bio', 'overview',
                    'profile_summary', 'profileSummary'
                ], '')
                
                # Extract profile image
                profile_image = get_nested_value([
                    'profile_image', 'profileImage', 'image_url', 'imageUrl',
                    'photo', 'avatar', 'picture', 'img'
                ], None)
                if not profile_image or profile_image == 'None':
                    profile_image = None
                
                # Debug output for first item
                if len(leads) == 0:
                    print(f"[BrightData API] Parsed first lead:")
                    print(f"  Name: {name}")
                    print(f"  Title: {title}")
                    print(f"  Company: {company}")
                    print(f"  Location: {location}")
                    print(f"  LinkedIn URL: {linkedin_url}")
                
                # Only create lead if we have at least a LinkedIn URL or name
                if linkedin_url or (name and name != 'Unknown'):
                    lead = {
                        "id": str(uuid.uuid4()),
                        "name": name if name != 'Unknown' else (get_nested_value(['url'], '').split('/in/')[-1].split('/')[0] if linkedin_url else 'Unknown'),
                        "title": title,
                        "company": company,
                        "location": location,
                        "match_score": 85,  # Default score
                        "description": description,
                        "linkedin_url": linkedin_url or "",
                        "email": get_nested_value(['email', 'email_address', 'emailAddress'], None),
                        "profile_image": profile_image,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    leads.append(lead)
                else:
                    print(f"[BrightData API] Skipping item - no name or URL found")
                    print(f"[BrightData API] Item keys: {list(item.keys()) if isinstance(item, dict) else 'N/A'}")
            except Exception as e:
                print(f"[BrightData API] Error parsing result: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[BrightData API] Successfully parsed {len(leads)} leads from {len(data)} items")
        return leads


async def fetch_leads_via_brightdata(search_url: str, max_results: int = 10) -> List[Dict]:
    """
    Fetch leads using BrightData API
    """
    api = BrightDataAPI()
    
    # Check if we have API credentials
    if not api.api_token or not api.collector_id:
        print("[BrightData API] No BrightData API credentials found")
        print("[BrightData API] To use BrightData API:")
        print("[BrightData API]   1. Sign up for BrightData at https://brightdata.com")
        print("[BrightData API]   2. Get your API token from the dashboard")
        print("[BrightData API]   3. Set up a LinkedIn collector and get the Collector ID")
        print("[BrightData API]   4. Set BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID environment variables")
        return []
    
    print("[BrightData API] Using BrightData API to fetch leads...")
    try:
        leads = api.search_linkedin_profiles(search_url, max_results)
        
        if leads:
            print(f"[BrightData API] ✓ Found {len(leads)} leads via API")
        else:
            print("[BrightData API] No results from API")
        
        return leads
    except Exception as e:
        # Re-raise authentication and rate limit errors so they can be handled by main.py
        error_msg = str(e)
        if "Authentication" in error_msg or "Rate Limit" in error_msg:
            print(f"[BrightData API] 🔴 Propagating error to main handler: {error_msg}")
            raise
        # For other errors, log and return empty
        print(f"[BrightData API] Error fetching leads: {error_msg}")
        return []

