"""
FastAPI server for LinkedIn Lead Capture
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import urllib.parse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from brightdata_api_client import fetch_leads_via_brightdata

app = FastAPI(title="LinkedIn Lead Capture API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ProcessLinkedInRequest(BaseModel):
    linkedin_url: str


class ProcessLinkedInResponse(BaseModel):
    success: bool
    keywords: Optional[str] = None
    message: Optional[str] = None


class FindLeadsRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str


class Lead(BaseModel):
    id: str
    name: str
    title: str
    company: str
    location: str
    match_score: int
    description: str
    linkedin_url: str
    email: Optional[str] = None
    profile_image: Optional[str] = None
    created_at: str
    is_mock: Optional[bool] = False


class FindLeadsResponse(BaseModel):
    leads: List[Lead]
    total: int
    requires_login: Optional[bool] = False
    login_url: Optional[str] = None
    collector_id: Optional[str] = None


class SaveToLibraryRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str
    run_label: str
    selected_lead_ids: List[str]


class SaveResponse(BaseModel):
    success: bool
    message: str


class ExportRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str
    run_label: str
    selected_lead_ids: List[str]


class ExportResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None


def extract_keywords_from_url(linkedin_url: str) -> str:
    """Extract keywords from LinkedIn search URL"""
    try:
        parsed = urllib.parse.urlparse(linkedin_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        keywords = params.get('keywords', [''])[0] if params.get('keywords') else ''
        
        # Also try to extract from URL path
        if not keywords:
            # Look for keywords in the URL path
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and part != 'search' and part != 'results' and part != 'people':
                    # Decode URL encoding
                    decoded = urllib.parse.unquote(part)
                    if decoded and len(decoded) > 2:
                        keywords = decoded.replace('-', ' ').replace('_', ' ')
                        break
        
        return keywords if keywords else 'LinkedIn Search'
    except Exception as e:
        print(f"[API] Error extracting keywords: {e}")
        return 'LinkedIn Search'


@app.get("/api/test-credentials")
async def test_credentials():
    """Test endpoint to verify BrightData API credentials are loaded"""
    from brightdata_api_client import BrightDataAPI
    
    api = BrightDataAPI()
    
    return {
        "api_token": api.api_token[:10] + "..." if api.api_token else None,
        "collector_id": api.collector_id if api.collector_id else None,
        "credentials_loaded": bool(api.api_token and api.collector_id),
        "has_api_token": bool(api.api_token),
        "has_collector_id": bool(api.collector_id),
        "env_file_location": "Check api/.env file for BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID",
        "note": "BrightData API provides LinkedIn data extraction via their collector service."
    }




@app.get("/api/linkedin-login-status")
async def check_linkedin_login_status():
    """Check LinkedIn authentication status using local Playwright and browser-cookie3
    
    This checks if the user is logged in to LinkedIn by extracting cookies from their local browser
    and using Playwright to verify authentication. This is faster than BrightData API checks.
    """
    from linkedin_local_check import check_linkedin_login_status_local
    import asyncio
    import concurrent.futures
    
    print("[API] Checking LinkedIn login status using local Playwright and browser-cookie3...")
    
    # Run the blocking Playwright call in an executor to avoid blocking the event loop
    # Add a timeout to prevent hanging
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Add timeout wrapper
            async def check_with_timeout():
                try:
                    result = await loop.run_in_executor(executor, check_linkedin_login_status_local)
                    return result
                except Exception as inner_e:
                    import traceback
                    print(f"[API] Inner exception in executor: {inner_e}")
                    print(f"[API] Inner exception type: {type(inner_e).__name__}")
                    print(f"[API] Inner traceback:\n{traceback.format_exc()}")
                    # Re-raise to be caught by outer handler
                    raise
            
            # Wait for result with 30 second timeout
            result = await asyncio.wait_for(check_with_timeout(), timeout=30.0)
        
        print(f"[API] Local check result: {result}")
        return result
        
    except asyncio.TimeoutError:
        print("[API] ⚠️ Status check timed out after 30 seconds")
        return {
            "logged_in": None,
            "status": "error",
            "message": "LinkedIn: Check Timeout",
            "note": "Status check timed out. Please try clicking the status indicator to open a login window, or ensure your browser is closed and try again.",
            "method": "local_playwright"
        }
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else type(e).__name__
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        
        print(f"[API] Error checking LinkedIn login status: {error_msg}")
        print(f"[API] Error type: {error_type}")
        print(f"[API] Full traceback:\n{full_traceback}")
        
        # Provide more detailed error message
        if not error_msg or error_msg.strip() == "":
            error_msg = f"{error_type}: An error occurred during LinkedIn login check. See server logs for details."
        
        return {
            "logged_in": None,
            "status": "error",
            "message": "LinkedIn: Check Failed",
            "note": f"Error checking LinkedIn login status: {error_msg}. Please try clicking the status indicator to open a login window.",
            "method": "local_playwright",
            "error": error_msg,
            "error_type": error_type
        }


class LinkedInLoginRequest(BaseModel):
    email: str
    password: str


class SetCookieRequest(BaseModel):
    cookie_value: str


@app.get("/api/linkedin-open-login")
async def open_linkedin_login():
    """Open a browser window for LinkedIn login and wait for user to authenticate
    
    This opens a visible browser window where the user can log in to LinkedIn.
    After successful login, cookies are extracted and saved for future use.
    """
    from linkedin_local_check import PLAYWRIGHT_AVAILABLE, sync_playwright
    import asyncio
    import concurrent.futures
    import threading
    
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "success": False,
            "error": "Playwright not installed",
            "note": "Install with: pip install playwright && playwright install chromium"
        }
    
    print("[API] Opening LinkedIn login window...")
    
    def open_login_window():
        try:
            print("[API] Starting browser launch process...")
            with sync_playwright() as p:
                # Open browser in visible mode (not headless) - make sure it's visible
                print("[API] Launching browser in visible mode (headless=False)...")
                try:
                    browser = p.chromium.launch(
                        headless=False,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--start-maximized',  # Start maximized so user can see it
                            '--disable-web-security'  # Sometimes helps with popups
                        ]
                    )
                    print("[API] ✓ Browser launched successfully!")
                except Exception as launch_error:
                    print(f"[API] ❌ Error launching browser: {launch_error}")
                    import traceback
                    print(f"[API] Traceback: {traceback.format_exc()}")
                    raise
                
                context = browser.new_context(viewport={'width': 1280, 'height': 720})
                page = context.new_page()
                
                # Navigate to LinkedIn login
                print("[API] Navigating to LinkedIn login page...")
                try:
                    page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded', timeout=30000)
                    print("[API] ✓ Browser window opened and navigated to LinkedIn login!")
                    print("[API] ✓ Browser window should be visible now. If not, check your taskbar.")
                    print("[API] Waiting for user to log in...")
                except Exception as nav_error:
                    print(f"[API] ❌ Error navigating to LinkedIn: {nav_error}")
                    import traceback
                    print(f"[API] Traceback: {traceback.format_exc()}")
                    try:
                        browser.close()
                    except:
                        pass
                    raise
                
                # Wait for user to log in - check every 2 seconds
                max_wait_time = 300  # 5 minutes max
                check_interval = 2  # Check every 2 seconds
                waited = 0
                
                while waited < max_wait_time:
                    try:
                        current_url = page.url
                        page_title = page.title().lower()
                        
                        # Check if we're logged in (on feed or profile page)
                        if "/feed" in current_url or "/in/" in current_url or "/me" in current_url:
                            # Check for login indicators to make sure we're not on a login page
                            if "sign in" not in page_title and "login" not in current_url:
                                print("[API] ✓ Login detected! Extracting cookies...")
                                
                                # Extract cookies
                                cookies = context.cookies()
                                linkedin_cookies = [
                                    c for c in cookies 
                                    if 'linkedin.com' in c.get('domain', '') or c.get('domain', '').startswith('.linkedin.com')
                                ]
                                
                                if linkedin_cookies:
                                    # Save cookies
                                    from linkedin_local_check import save_cookies
                                    save_cookies(linkedin_cookies)
                                    print(f"[API] ✓ Saved {len(linkedin_cookies)} LinkedIn cookies")
                                    
                                    # Close browser after a short delay
                                    page.wait_for_timeout(2000)
                                    browser.close()
                                    
                                    return {
                                        "success": True,
                                        "message": "Login successful! Cookies saved.",
                                        "cookies_saved": len(linkedin_cookies),
                                        "note": "Login successful! The browser window has been closed. Your login status will be checked automatically."
                                    }
                        
                        page.wait_for_timeout(check_interval * 1000)
                        waited += check_interval
                        
                    except Exception as e:
                        print(f"[API] Error checking login status: {e}")
                        page.wait_for_timeout(check_interval * 1000)
                        waited += check_interval
                
                # Timeout - user didn't log in
                print("[API] ⚠️ Timeout waiting for login")
                browser.close()
                return {
                    "success": False,
                    "error": "Timeout",
                    "note": "Login timeout. Please try again and log in within 5 minutes."
                }
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            print(f"[API] Error opening login window: {error_msg}")
            print(f"[API] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
                "note": f"Error opening login window: {error_msg}"
            }
    
    # Run in executor to avoid blocking - but start it immediately
    # The browser window should open in a separate process
    try:
        # Start the browser opening in a non-daemon thread so it doesn't block
        # and the browser stays open
        import threading
        thread = threading.Thread(target=open_login_window, daemon=False, name="LinkedInLoginWindow")
        thread.start()
        
        # Give it a moment to start and verify it's running
        import time
        time.sleep(2)  # Give more time for browser to launch
        
        # Check if thread is still alive (browser should be running)
        if thread.is_alive():
            print("[API] ✓ Browser launch thread is running")
        else:
            print("[API] ⚠️ Browser launch thread may have exited early")
        
        # Return immediately - the browser window should be opening now
        return {
            "success": True,
            "message": "Browser window opening...",
            "note": "A browser window is opening for LinkedIn login. Please log in there. The window will close automatically after successful login. If you don't see it, check your taskbar or try again. Check the server console for launch messages."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "note": f"Error: {str(e)}"
        }


@app.post("/api/linkedin-login")
async def linkedin_login(request: LinkedInLoginRequest):
    """
    Log in to LinkedIn using Playwright and automatically save cookies.
    This allows the local login check to work without manual cookie extraction.
    """
    from linkedin_local_check import login_and_save_cookies
    
    print(f"[API] LinkedIn login request for: {request.email}")
    
    result = login_and_save_cookies(request.email, request.password)
    
    if result.get("success"):
        return {
            "success": True,
            "message": result.get("message", "Login successful"),
            "cookies_saved": result.get("cookies_count", 0)
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "Login failed")
        }


@app.post("/api/linkedin-set-cookie")
async def set_linkedin_cookie(request: SetCookieRequest):
    """Manually set the LinkedIn li_at cookie
    
    Args:
        request: Contains cookie_value (the li_at cookie value)
    """
    from linkedin_local_check import save_cookies
    
    cookie_value = request.cookie_value
    
    try:
        # Create a cookie dict in Playwright format
        cookie = {
            "name": "li_at",
            "value": cookie_value,
            "domain": ".linkedin.com",
            "path": "/",
            "expires": -1,  # Session cookie
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        }
        
        # Save the cookie
        saved = save_cookies([cookie])
        
        if saved:
            print(f"[API] ✓ Saved li_at cookie manually")
            return {
                "success": True,
                "message": "Cookie saved successfully",
                "note": "LinkedIn authentication cookie has been saved. Your login status will be checked automatically."
            }
        else:
            return {
                "success": False,
                "error": "Failed to save cookie",
                "note": "Could not save the cookie. Please check server logs."
            }
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error setting cookie: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "note": f"Error setting cookie: {error_msg}"
        }


@app.get("/api/linkedin-user-name")
async def get_linkedin_user_name():
    """Get the name of the logged-in LinkedIn user using Playwright persistent context"""
    from linkedin_local_check import get_linkedin_user_name as get_name_local
    
    print("[API] Attempting to get LinkedIn user name from browser...")
    
    # Try local method first (extracts cookies from browser)
    result = get_name_local()
    
    if result and result.get("success"):
        print(f"[API] ✓ Got user name from browser: {result.get('name')}")
        return result
    
    # If local method failed, fall back to BrightData (slower but works if browser method fails)
    print("[API] Local method failed, falling back to BrightData...")
    from brightdata_api_client import BrightDataAPI
    import asyncio
    
    api = BrightDataAPI()
    brightdata_configured = bool(api.api_token and api.collector_id)
    
    if not brightdata_configured:
        return {
            "success": False,
            "error": "Browser method failed and BrightData API not configured",
            "message": "Please log in to LinkedIn in your browser, or configure BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID"
        }
    
    # Try to get user's own profile - navigate to feed and extract profile URL
    # Note: LinkedIn doesn't have a /me endpoint, so we'll use the feed page
    profile_url = "https://www.linkedin.com/feed/"
    
    try:
        print("[API] Fetching logged-in user's profile via BrightData...")
        collection_response = api.trigger_collector(profile_url)
        
        if not collection_response:
            return {
                "success": False,
                "error": "Failed to trigger collection"
            }
        
        # Extract collection_id
        collection_id = None
        if isinstance(collection_response, dict):
            collection_id = collection_response.get('collection_id') or collection_response.get('_id')
        elif isinstance(collection_response, list) and len(collection_response) > 0:
            collection_id = collection_response[0].get('collection_id') or collection_response[0].get('_id')
        
        if not collection_id:
            return {
                "success": False,
                "error": "Failed to get collection ID"
            }
        
        # Wait for collection to process
        print("[API] Waiting for profile data...")
        await asyncio.sleep(15)
        
        # Get collection data
        data = api.get_collection_data(collection_id)
        
        if not data or not isinstance(data, list) or len(data) == 0:
            return {
                "success": False,
                "error": "No profile data returned"
            }
        
        # Check for errors
        first_item = data[0]
        if isinstance(first_item, dict) and 'error' in first_item:
            error_msg = first_item.get('error', '')
            return {
                "success": False,
                "error": error_msg,
                "message": "Failed to fetch profile. Authentication may be required."
            }
        
        # Extract name from profile data
        def get_nested_value(item, key_variations, default=''):
            """Try multiple key variations to find a value"""
            for key in key_variations:
                if key in item:
                    value = item[key]
                    if value:
                        return str(value).strip()
                # Check nested structures
                if 'profile' in item and isinstance(item['profile'], dict):
                    if key in item['profile']:
                        value = item['profile'][key]
                        if value:
                            return str(value).strip()
                if 'data' in item and isinstance(item['data'], dict):
                    if key in item['data']:
                        value = item['data'][key]
                        if value:
                            return str(value).strip()
            return default
        
        # Try to extract name
        name = get_nested_value(first_item, [
            'name', 'full_name', 'fullName', 'display_name', 'displayName',
            'firstName', 'first_name', 'lastName', 'last_name'
        ], '')
        
        # If we have first and last separately, combine them
        if not name:
            first = get_nested_value(first_item, ['firstName', 'first_name', 'first'], '')
            last = get_nested_value(first_item, ['lastName', 'last_name', 'last'], '')
            if first or last:
                name = f"{first} {last}".strip()
        
        # Also try headline/title
        headline = get_nested_value(first_item, ['headline', 'title', 'position'], '')
        
        if name:
            print(f"[API] ✓ Found user name via BrightData: {name}")
            return {
                "success": True,
                "name": name,
                "headline": headline if headline else None,
                "method": "brightdata"
            }
        else:
            print(f"[API] ⚠️ Could not extract name from profile data")
            return {
                "success": False,
                "error": "Could not extract name from profile",
                "profile_data": first_item  # Include for debugging
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error fetching user name: {error_msg}")
        return {
            "success": False,
            "error": error_msg
    }


@app.get("/api/test-linkedin-search")
async def test_linkedin_search(keywords: str = "SDR manager"):
    """Test endpoint to see what BrightData API returns"""
    from brightdata_api_client import BrightDataAPI
    
    api = BrightDataAPI()
    
    if not api.api_token or not api.collector_id:
        return {
            "error": "Missing API token or Collector ID",
            "credentials_loaded": False,
            "note": "Set BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID in api/.env file"
        }
    
    # Create a test search URL
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}"
    
    try:
        # Test triggering the collector
        result = api.trigger_collector(search_url)
        if result:
            # Extract collection_id from response
            collection_id = None
            if isinstance(result, dict):
                collection_id = result.get('collection_id') or result.get('_id')
            elif isinstance(result, list) and len(result) > 0:
                collection_id = result[0].get('collection_id') or result[0].get('_id')
            
            return {
                "status": "success",
                "collection_response": result,
                "collection_id": collection_id,
                "note": "BrightData collector triggered. Results will be available after processing (typically 20-60 seconds)."
            }
        else:
            return {
                "status": "error",
                "error": "Failed to trigger collector",
                "note": "Check your API token and Collector ID"
            }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "LinkedIn Lead Capture API is running"}


@app.post("/api/capture/process-linkedin", response_model=ProcessLinkedInResponse)
async def process_linkedin(request: ProcessLinkedInRequest):
    """Process LinkedIn URL and extract keywords"""
    try:
        keywords = extract_keywords_from_url(request.linkedin_url)
        
        return ProcessLinkedInResponse(
            success=True,
            keywords=keywords,
            message=f"Extracted keywords: {keywords}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing LinkedIn URL: {str(e)}")


def generate_mock_leads(linkedin_url: str, ai_criteria: str, count: int = 8) -> List[dict]:
    """Generate mock leads for testing/development"""
    import uuid
    from datetime import datetime
    
    keywords = extract_keywords_from_url(linkedin_url)
    
    mock_leads = [
        {
            "id": str(uuid.uuid4()),
            "name": "John Smith",
            "title": "Senior Sales Manager",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "match_score": 92,
            "description": f"Experienced {keywords} professional with strong sales background",
            "linkedin_url": "https://www.linkedin.com/in/johnsmith",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sarah Johnson",
            "title": "Sales Director",
            "company": "Global Solutions Inc",
            "location": "New York, NY",
            "match_score": 88,
            "description": f"Expert in {keywords} with proven track record",
            "linkedin_url": "https://www.linkedin.com/in/sarahjohnson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Michael Chen",
            "title": "VP of Sales",
            "company": "Innovation Labs",
            "location": "Austin, TX",
            "match_score": 85,
            "description": f"Strategic {keywords} leader driving growth",
            "linkedin_url": "https://www.linkedin.com/in/michaelchen",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Emily Rodriguez",
            "title": "Account Executive",
            "company": "SalesForce Pro",
            "location": "Chicago, IL",
            "match_score": 82,
            "description": f"Results-driven {keywords} professional",
            "linkedin_url": "https://www.linkedin.com/in/emilyrodriguez",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "David Wilson",
            "title": "Regional Sales Manager",
            "company": "Enterprise Solutions",
            "location": "Seattle, WA",
            "match_score": 80,
            "description": f"Seasoned {keywords} expert",
            "linkedin_url": "https://www.linkedin.com/in/davidwilson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lisa Anderson",
            "title": "Business Development Manager",
            "company": "Growth Partners",
            "location": "Boston, MA",
            "match_score": 78,
            "description": f"Dynamic {keywords} specialist",
            "linkedin_url": "https://www.linkedin.com/in/lisaanderson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Robert Martinez",
            "title": "Sales Team Lead",
            "company": "Premium Services",
            "location": "Denver, CO",
            "match_score": 75,
            "description": f"Focused {keywords} professional",
            "linkedin_url": "https://www.linkedin.com/in/robertmartinez",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Jennifer Taylor",
            "title": "Senior Account Manager",
            "company": "Client Success Co",
            "location": "Los Angeles, CA",
            "match_score": 73,
            "description": f"Client-focused {keywords} expert",
            "linkedin_url": "https://www.linkedin.com/in/jennifertaylor",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
    ]
    
    return mock_leads[:count]


@app.post("/api/capture/find-leads", response_model=FindLeadsResponse)
async def find_leads(request: FindLeadsRequest):
    """Find leads based on LinkedIn URL and AI criteria"""
    leads = []
    errors = []
    
    print("=" * 60)
    print("[API] ===== FIND LEADS REQUEST ======")
    print(f"[API] LinkedIn URL: {request.linkedin_url}")
    print(f"[API] AI Criteria: {request.ai_criteria}")
    print("=" * 60)
    
    # Validate that the URL is a LinkedIn search results URL (not a profile URL)
    if not request.linkedin_url or "/search/results/people" not in request.linkedin_url:
        error_msg = f"Invalid LinkedIn URL. Please provide a LinkedIn search results URL like: https://www.linkedin.com/search/results/people/?keywords=..."
        print(f"[API] ✗ {error_msg}")
        print(f"[API] Received URL: {request.linkedin_url}")
        return FindLeadsResponse(
            leads=[],
            total=0,
            requires_login=False,
            login_url=None,
            errors=[error_msg]
        )
    
    try:
        # Check BrightData API status first
        brightdata_configured = False
        try:
            from brightdata_api_client import BrightDataAPI
            api = BrightDataAPI()
            if api.api_token and api.collector_id:
                brightdata_configured = True
                print("[API] ✓ BrightData API is configured")
        except:
            pass
        
        # Use BrightData API only
        print("[API] Attempting to fetch leads via BrightData API...")
        try:
            api_leads = await fetch_leads_via_brightdata(request.linkedin_url, max_results=50)
            if api_leads:
                leads = api_leads
                print(f"[API] ✓ Found {len(leads)} leads via BrightData API")
            else:
                print("[API] ✗ BrightData API returned 0 leads")
                if not brightdata_configured:
                    errors.append("BrightData API not configured. Please set BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID in api/.env file")
        except Exception as e:
            error_msg = str(e)
            errors.append(error_msg)
            print(f"[API] ✗ Exception caught: {error_msg}")
            print(f"[API] Exception type: {type(e).__name__}")
            import traceback
            print(f"[API] Traceback: {traceback.format_exc()}")
            
            # Check if it's an authentication/login error
            error_lower = error_msg.lower()
            auth_keywords = ['authentication', 'login', 'auth', 'redirected to login', 'authentication required', 'unauthorized', 'forbidden']
            is_auth_error = any(keyword in error_lower for keyword in auth_keywords) or "Authentication" in error_msg
            
            print(f"[API] Checking if auth error - keywords found: {is_auth_error}")
            print(f"[API] Error message (lowercase): {error_lower}")
            
            if is_auth_error:
                print("[API] ⚠️ BrightData authentication/login required - setting requires_login=True")
                # Try to get collector ID for better error message
                collector_id = None
                try:
                    from brightdata_api_client import BrightDataAPI
                    api = BrightDataAPI()
                    collector_id = api.collector_id
                    print(f"[API] Collector ID: {collector_id}")
                except Exception as ex:
                    print(f"[API] Could not get collector ID: {ex}")
                
                return FindLeadsResponse(
                    leads=[],
                    total=0,
                    requires_login=True,
                    login_url="https://brightdata.com/cp/dashboard",
                    collector_id=collector_id
                )
            
            # Check if it's a rate limit error
            if "Rate Limit" in error_msg or "rate" in error_msg.lower():
                print("[API] ⚠️ BrightData rate limit exceeded")
                return FindLeadsResponse(
                    leads=[],
                    total=0,
                    requires_login=False,
                    login_url=None
                )
            
            if not brightdata_configured:
                errors.append("BrightData API credentials missing. Please configure BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID")
        
        # If still no leads, return empty results
        if not leads:
            print("[API] ⚠️ No leads found from BrightData API.")
            print("[API] Errors encountered:", errors)
            if not brightdata_configured:
                print("[API] Please configure BrightData API credentials (BRIGHTDATA_API_TOKEN and BRIGHTDATA_COLLECTOR_ID) in api/.env file")
            print("[API] Returning empty results.")
        
        # Convert to Lead models
        lead_models = []
        for lead in leads:
            try:
                lead_models.append(Lead(**lead))
            except Exception as e:
                print(f"[API] Error converting lead: {e}, Lead data: {lead}")
                continue
        
        print(f"[API] Returning {len(lead_models)} leads")
        print("=" * 60)
        
        return FindLeadsResponse(
            leads=lead_models,
            total=len(lead_models),
            requires_login=False,
            login_url=None
        )
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error finding leads: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Return empty results on error instead of mock data
        print("[API] Returning empty results due to error.")
        return FindLeadsResponse(
            leads=[],
            total=0,
            requires_login=False,
            login_url=None
        )


@app.post("/api/capture/save-to-library", response_model=SaveResponse)
async def save_to_library(request: SaveToLibraryRequest):
    """Save selected leads to library"""
    try:
        # TODO: Implement actual database storage
        # For now, just return success
        
        return SaveResponse(
            success=True,
            message=f"Successfully saved {len(request.selected_lead_ids)} leads to library"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to library: {str(e)}")


@app.post("/api/capture/save-run", response_model=SaveResponse)
async def save_run(request: SaveToLibraryRequest):
    """Save a capture run"""
    try:
        # TODO: Implement actual database storage
        # For now, just return success
        
        return SaveResponse(
            success=True,
            message=f"Successfully saved run '{request.run_label}' with {len(request.selected_lead_ids)} leads"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving run: {str(e)}")


@app.post("/api/capture/export", response_model=ExportResponse)
async def export_leads(request: ExportRequest):
    """Export selected leads"""
    try:
        # TODO: Implement actual export functionality (CSV, Excel, etc.)
        # For now, just return success
        
        return ExportResponse(
            success=True,
            message=f"Successfully exported {len(request.selected_lead_ids)} leads",
            download_url=None  # TODO: Generate actual download URL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting leads: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

