"""
Local LinkedIn login check using Playwright with saved cookies.
Automatically extracts and saves cookies from browser sessions.
Also supports extracting cookies from browser using browser-cookie3.
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict

# Try to import Playwright - make it optional
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    Browser = None
    BrowserContext = None
    Page = None

# Try to import browser_cookie3 - make it optional
try:
    import browser_cookie3
    from http.cookiejar import Cookie
    BROWSER_COOKIE3_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE3_AVAILABLE = False
    browser_cookie3 = None
    Cookie = None

# Cookie file path
COOKIE_FILE = Path(__file__).parent / "linkedin_cookies.json"


def load_cookies() -> Optional[List[Dict]]:
    """Load saved LinkedIn cookies from file"""
    if not COOKIE_FILE.exists():
        return None
    
    try:
        with open(COOKIE_FILE, 'r') as f:
            cookies = json.load(f)
            if isinstance(cookies, list):
                return cookies
            return None
    except Exception as e:
        print(f"[LinkedIn Local Check] Error loading cookies: {e}")
        return None


def save_cookies(cookies: List[Dict]) -> bool:
    """Save LinkedIn cookies to file"""
    try:
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"[LinkedIn Local Check] Saved {len(cookies)} cookies to {COOKIE_FILE}")
        return True
    except Exception as e:
        print(f"[LinkedIn Local Check] Error saving cookies: {e}")
        return False


def extract_cookies_from_browser(context: BrowserContext) -> List[Dict]:
    """Extract cookies from browser context"""
    try:
        cookies = context.cookies()
        # Filter for LinkedIn cookies only
        linkedin_cookies = [
            cookie for cookie in cookies 
            if 'linkedin.com' in cookie.get('domain', '') or cookie.get('domain', '').startswith('.linkedin.com')
        ]
        return linkedin_cookies
    except Exception as e:
        print(f"[LinkedIn Local Check] Error extracting cookies: {e}")
        return []


def check_linkedin_login_status_local() -> Dict:
    """
    Check LinkedIn login status using Playwright and browser-cookie3.
    Extracts cookies from local browsers and uses Playwright to verify login.
    
    Returns:
        Dict with 'logged_in' (bool), 'status', 'message', 'note', etc.
    """
    import signal
    
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "logged_in": None,
            "status": "error",
            "message": "Playwright: Not Installed",
            "note": "Playwright is not installed. Install with: pip install playwright && playwright install chromium",
            "method": "local_playwright"
        }
    
    if not BROWSER_COOKIE3_AVAILABLE:
        return {
            "logged_in": None,
            "status": "error",
            "message": "browser-cookie3: Not Installed",
            "note": "browser-cookie3 is not installed. Install with: pip install browser-cookie3",
            "method": "local_playwright"
        }
    
    # First, try to load saved cookies from file
    print("[LinkedIn Local Check] Checking for saved cookies...")
    saved_cookies = load_cookies()
    
    # Get LinkedIn cookies from browser (with timeout)
    print("[LinkedIn Local Check] Attempting to extract LinkedIn cookies from local browsers...")
    try:
        browser_cookies = get_linkedin_cookies_for_playwright()
    except Exception as e:
        print(f"[LinkedIn Local Check] Error extracting cookies: {e}")
        browser_cookies = []
    
    # Combine saved cookies and browser cookies (prefer browser cookies if available)
    cookies = browser_cookies if browser_cookies else (saved_cookies if saved_cookies else [])
    
    if not cookies:
        print("[LinkedIn Local Check] [WARNING] No cookies found via browser-cookie3 or saved file.")
        # Return immediately - don't try Playwright fallback as it's slow and unreliable
        # User should use the login button to open a browser window
        return {
            "logged_in": False,
            "status": "error",
            "message": "LinkedIn: Not Logged In",
            "note": "No LinkedIn cookies found. Please click this status indicator to open a browser window and log in to LinkedIn.",
            "method": "local_playwright",
            "linkedin_url": "https://www.linkedin.com/login"
        }
    
    if saved_cookies and not browser_cookies:
        print(f"[LinkedIn Local Check] Using {len(saved_cookies)} saved cookies from file")
    elif browser_cookies:
        print(f"[LinkedIn Local Check] Using {len(browser_cookies)} cookies from browser")
    
    print(f"[LinkedIn Local Check] Found {len(cookies)} LinkedIn cookies from browser")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=10000)
            context = browser.new_context()
            
            # Add all LinkedIn cookies to context
            try:
                print(f"[LinkedIn Local Check] Adding {len(cookies)} cookies to browser context...")
                # Validate cookie format before adding
                for cookie in cookies:
                    if not isinstance(cookie, dict):
                        raise ValueError(f"Cookie is not a dict: {type(cookie)}")
                    if 'name' not in cookie or 'value' not in cookie:
                        raise ValueError(f"Cookie missing required fields: {cookie.keys()}")
                    if 'domain' not in cookie:
                        cookie['domain'] = '.linkedin.com'
                    if 'path' not in cookie:
                        cookie['path'] = '/'
                
                context.add_cookies(cookies)
                print(f"[LinkedIn Local Check] Successfully added {len(cookies)} cookies")
            except Exception as e:
                import traceback
                error_msg = str(e) if str(e) else type(e).__name__
                print(f"[LinkedIn Local Check] Error adding cookies: {error_msg}")
                print(f"[LinkedIn Local Check] Cookie data: {cookies[:1] if cookies else 'No cookies'}")
                print(f"[LinkedIn Local Check] Traceback: {traceback.format_exc()}")
                try:
                    browser.close()
                except:
                    pass
                return {
                    "logged_in": False,
                    "status": "error",
                    "message": "LinkedIn: Cookie Error",
                    "note": f"Error adding cookies: {error_msg}. Please check the cookie format. See server logs for details.",
                    "method": "local_playwright",
                    "linkedin_url": "https://www.linkedin.com/login",
                    "error": error_msg
                }
            
            page = context.new_page()
            
            # Navigate to LinkedIn feed (requires authentication)
            print("[LinkedIn Local Check] Navigating to LinkedIn feed...")
            try:
                # Use shorter timeout to avoid hanging
                page.goto("https://www.linkedin.com/feed/", wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(2000)  # Wait for JS to finish
            except Exception as e:
                print(f"[LinkedIn Local Check] Error navigating to feed: {e}")
                try:
                    browser.close()
                except:
                    pass
                return {
                    "logged_in": None,
                    "status": "error",
                    "message": "LinkedIn: Check Failed",
                    "note": f"Error navigating to LinkedIn: {str(e)}. Please try again or use the login button to open a browser window.",
                    "method": "local_playwright"
                }
            
            # Check current URL
            current_url = page.url
            print(f"[LinkedIn Local Check] Current URL: {current_url}")
            
            # Check if redirected to login page
            if "/login" in current_url or "challenge" in current_url.lower():
                print("[LinkedIn Local Check] [FAIL] Redirected to login page - not logged in")
                browser.close()
                return {
                    "logged_in": False,
                    "status": "error",
                    "message": "LinkedIn: Not Logged In",
                    "note": "Cookies may be expired. Please log in to LinkedIn in your browser again.",
                    "method": "local_playwright",
                    "linkedin_url": "https://www.linkedin.com/login"
                }
            
            # Check page content for login indicators
            try:
                page_content = page.content().lower()
                page_title = page.title().lower()
                
                # Check for login page indicators
                login_indicators = ["sign in", "join linkedin", "welcome back", "forgot password"]
                has_login_indicators = any(indicator in page_content or indicator in page_title for indicator in login_indicators)
                
                # Check for feed page indicators (logged in)
                feed_indicators = ["feed", "start a post", "linkedin news", "view profile"]
                has_feed_indicators = any(indicator in page_content or indicator in page_title for indicator in feed_indicators)
                
                # If we have login indicators and no feed indicators, not logged in
                if has_login_indicators and not has_feed_indicators:
                    print("[LinkedIn Local Check] [FAIL] Login page content detected - not logged in")
                    browser.close()
                    return {
                        "logged_in": False,
                        "status": "error",
                        "message": "LinkedIn: Not Logged In",
                        "note": "Login page detected. Please log in to LinkedIn in your browser.",
                        "method": "local_playwright",
                        "linkedin_url": "https://www.linkedin.com/login"
                    }
                
                # If we're on feed URL and have feed indicators, logged in
                if "linkedin.com/feed" in current_url and has_feed_indicators:
                    is_logged_in = True
                elif "linkedin.com/feed" in current_url:
                    # On feed URL but check more carefully
                    try:
                        feed_element = page.query_selector('div[data-test-id="feed-container"]') or \
                                     page.query_selector('div.feed-container') or \
                                     page.query_selector('main[role="main"]')
                        is_logged_in = feed_element is not None
                    except:
                        is_logged_in = False
                else:
                    # Not on feed URL - might be redirected
                    is_logged_in = False
                    
            except Exception as e:
                print(f"[LinkedIn Local Check] Error checking page content: {e}")
                # Fallback to URL check only
                is_logged_in = "/login" not in current_url and "linkedin.com/feed" in current_url
            
            # Additional verification: Try to access feed page (protected endpoint)
            if is_logged_in:
                try:
                    page.goto("https://www.linkedin.com/feed/", wait_until='domcontentloaded', timeout=10000)
                    page.wait_for_timeout(1000)
                    feed_url = page.url
                    
                    # If redirected to login, cookies are invalid
                    if "/login" in feed_url:
                        print("[LinkedIn Local Check] [FAIL] Cookies invalid - redirected to login on feed page")
                        browser.close()
                        return {
                            "logged_in": False,
                            "status": "error",
                            "message": "LinkedIn: Not Logged In",
                            "note": "Cookies are invalid or expired. Please log in to LinkedIn in your browser again.",
                            "method": "local_playwright",
                            "linkedin_url": "https://www.linkedin.com/login"
                        }
                    
                    print("[LinkedIn Local Check] [OK] Feed page accessible - logged in")
                except Exception as e:
                    print(f"[LinkedIn Local Check] Warning: Could not verify profile page: {e}")
            
            browser.close()
            
            if is_logged_in:
                print("[LinkedIn Local Check] [OK] Logged in successfully")
                return {
                    "logged_in": True,
                    "status": "success",
                    "message": "LinkedIn: Logged In",
                    "note": "LinkedIn authentication verified using local browser cookies.",
                    "method": "local_playwright"
                }
            else:
                print("[LinkedIn Local Check] [FAIL] Not logged in")
                return {
                    "logged_in": False,
                    "status": "error",
                    "message": "LinkedIn: Not Logged In",
                    "note": "Not logged in. Please log in to LinkedIn in your browser (Chrome/Edge/Firefox).",
                    "method": "local_playwright",
                    "linkedin_url": "https://www.linkedin.com/login"
                }
                
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else type(e).__name__
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        
        print(f"[LinkedIn Local Check] Error checking login status: {error_msg}")
        print(f"[LinkedIn Local Check] Error type: {error_type}")
        print(f"[LinkedIn Local Check] Full traceback:\n{full_traceback}")
        
        # Provide more detailed error message
        if not error_msg or error_msg.strip() == "":
            error_msg = f"{error_type}: An error occurred during LinkedIn login check. See server logs for details."
        
        return {
            "logged_in": None,
            "status": "error",
            "message": "LinkedIn: Check Failed",
            "note": f"Error checking LinkedIn login status: {error_msg}. Please check server logs for more details.",
            "method": "local_playwright",
            "error": error_msg,
            "error_type": error_type
        }


def check_linkedin_login_local() -> Optional[bool]:
    """
    Check LinkedIn login status using Playwright and saved cookies.
    
    Returns:
        True if logged in
        False if not logged in
        None if check unavailable (no cookies, Playwright error, etc.)
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("[LinkedIn Local Check] Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return None
    
    cookies = load_cookies()
    
    if not cookies:
        print("[LinkedIn Local Check] No saved cookies found")
        return None
    
    print(f"[LinkedIn Local Check] Checking login status with {len(cookies)} saved cookies...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            # Add saved cookies
            try:
                context.add_cookies(cookies)
            except Exception as e:
                print(f"[LinkedIn Local Check] Error adding cookies: {e}")
                browser.close()
                return None
            
            page = context.new_page()
            
            # Navigate to LinkedIn feed (requires authentication)
            try:
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                # Wait a bit for any redirects
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"[LinkedIn Local Check] Error navigating to LinkedIn: {e}")
                browser.close()
                return None
            
            # Check current URL after navigation
            current_url = page.url
            print(f"[LinkedIn Local Check] Current URL after navigation: {current_url}")
            
            # Check for login page indicators
            is_on_login_page = "/login" in current_url or "challenge" in current_url.lower()
            
            # If we're on login page, definitely not logged in
            if is_on_login_page:
                print("[LinkedIn Local Check] [FAIL] Redirected to login page - not logged in")
                browser.close()
                return False
            
            # Check page content for login indicators
            try:
                page_content = page.content().lower()
                page_title = page.title().lower()
                
                # Check for login page indicators in content
                login_indicators = [
                    "sign in",
                    "join linkedin",
                    "welcome back",
                    "forgot password",
                    "new to linkedin"
                ]
                
                has_login_indicators = any(indicator in page_content or indicator in page_title for indicator in login_indicators)
                
                # Check for feed page indicators (logged in)
                feed_indicators = [
                    "feed",
                    "start a post",
                    "linkedin news",
                    "view profile"
                ]
                
                has_feed_indicators = any(indicator in page_content or indicator in page_title for indicator in feed_indicators)
                
                print(f"[LinkedIn Local Check] Login indicators found: {has_login_indicators}")
                print(f"[LinkedIn Local Check] Feed indicators found: {has_feed_indicators}")
                
                # If we have login indicators and no feed indicators, not logged in
                if has_login_indicators and not has_feed_indicators:
                    print("[LinkedIn Local Check] [FAIL] Login page content detected - not logged in")
                    browser.close()
                    return False
                
                # If we're on feed URL and have feed indicators, logged in
                if "linkedin.com/feed" in current_url and has_feed_indicators:
                    is_logged_in = True
                elif "linkedin.com/feed" in current_url:
                    # On feed URL but check more carefully
                    # Try to find a logged-in element
                    try:
                        # Look for elements that only exist when logged in
                        feed_element = page.query_selector('div[data-test-id="feed-container"]') or \
                                     page.query_selector('div.feed-container') or \
                                     page.query_selector('main[role="main"]')
                        is_logged_in = feed_element is not None
                        print(f"[LinkedIn Local Check] Feed element found: {is_logged_in}")
                    except:
                        is_logged_in = False
                else:
                    # Not on feed URL - might be redirected
                    is_logged_in = False
                    
            except Exception as e:
                print(f"[LinkedIn Local Check] Error checking page content: {e}")
                # Fallback to URL check only
                is_logged_in = "/login" not in current_url and "linkedin.com/feed" in current_url
            
            # Additional verification: Try to access a protected endpoint
            if is_logged_in:
                # Double-check by trying to access feed page (protected endpoint)
                try:
                    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(1000)
                    feed_url = page.url
                    
                    # If redirected to login, cookies are invalid
                    if "/login" in feed_url:
                        print("[LinkedIn Local Check] [FAIL] Cookies invalid - redirected to login on feed page")
                        browser.close()
                        return False
                    
                    print("[LinkedIn Local Check] [OK] Profile page accessible - cookies are valid")
                except Exception as e:
                    print(f"[LinkedIn Local Check] Warning: Could not verify profile page: {e}")
            
            # If logged in, try to extract and save fresh cookies
            if is_logged_in:
                print("[LinkedIn Local Check] [OK] Logged in - extracting fresh cookies...")
                fresh_cookies = extract_cookies_from_browser(context)
                if fresh_cookies:
                    save_cookies(fresh_cookies)
            else:
                print("[LinkedIn Local Check] [FAIL] Not logged in - cookies may be expired or invalid")
                # Optionally delete invalid cookies
                # if COOKIE_FILE.exists():
                #     COOKIE_FILE.unlink()
                #     print("[LinkedIn Local Check] Deleted invalid cookies file")
            
            browser.close()
            return is_logged_in
            
    except ImportError:
        print("[LinkedIn Local Check] Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        print(f"[LinkedIn Local Check] Error during check: {e}")
        return None


def login_and_save_cookies(email: str, password: str) -> Dict[str, any]:
    """
    Log in to LinkedIn using Playwright and save cookies automatically.
    
    Args:
        email: LinkedIn email
        password: LinkedIn password
        
    Returns:
        Dict with success status and message
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "success": False,
            "message": "Playwright not installed. Install with: pip install playwright && playwright install chromium"
        }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Show browser for login
            context = browser.new_context()
            page = context.new_page()
            
            print("[LinkedIn Local Check] Navigating to LinkedIn login...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            
            # Fill in login form
            print("[LinkedIn Local Check] Filling login form...")
            page.fill('input[name="session_key"]', email)
            page.fill('input[name="session_password"]', password)
            
            # Click login button
            page.click('button[type="submit"]')
            
            # Wait for navigation (either to feed or back to login if failed)
            try:
                page.wait_for_url("**/feed/**", timeout=10000)
            except:
                # Check if still on login page (login failed)
                if "/login" in page.url:
                    browser.close()
                    return {
                        "success": False,
                        "message": "Login failed. Please check your email and password."
                    }
            
            # If we get here, login was successful
            print("[LinkedIn Local Check] [OK] Login successful - extracting cookies...")
            cookies = extract_cookies_from_browser(context)
            
            if cookies:
                save_cookies(cookies)
                browser.close()
                return {
                    "success": True,
                    "message": f"Login successful. Saved {len(cookies)} cookies.",
                    "cookies_count": len(cookies)
                }
            else:
                browser.close()
                return {
                    "success": False,
                    "message": "Login successful but failed to extract cookies."
                }
                
    except ImportError:
        return {
            "success": False,
            "message": "Playwright not installed. Install with: pip install playwright && playwright install chromium"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during login: {str(e)}"
        }


def load_all_browser_cookies():
    """
    Try to load cookies from common browsers. browser_cookie3.load() automatically
    tries available browsers, but we'll also call chrome/firefox/edge explicitly as fallback.
    Returns a http.cookiejar.CookieJar (iterable of Cookie objects).
    """
    if not BROWSER_COOKIE3_AVAILABLE:
        return None
    
    cj = None
    loaders = [
        browser_cookie3.load,      # generic loader (tries many)
        getattr(browser_cookie3, "chrome", None),
        getattr(browser_cookie3, "firefox", None),
        getattr(browser_cookie3, "edge", None)
    ]
    
    for loader in loaders:
        if not loader:
            continue
        try:
            maybe = loader()
            if maybe:
                # merge into one CookieJar
                if cj is None:
                    cj = maybe
                else:
                    for c in maybe:
                        cj.set_cookie(c)
        except Exception:
            # ignore errors for loaders that fail (e.g., browser not installed)
            continue
    
    return cj


def cookie_to_playwright_dict(cookie: Cookie) -> Dict:
    """
    Convert http.cookiejar.Cookie to Playwright cookie dict.
    Playwright expects: name, value, domain, path, expires, httpOnly, secure, sameSite
    - expires: integer seconds since epoch, or -1 for session cookies
    - sameSite: 'Strict' | 'Lax' | 'None' (Playwright accepts capitalized strings)
    """
    # domain: Playwright is okay with leading dot, but normalize for safety
    domain = cookie.domain or ""
    if domain.startswith("."):
        domain = domain  # keep leading dot - Playwright accepts it
    
    path = cookie.path or "/"
    
    # expires: cookie.expires is already in seconds since epoch or None
    expires = int(cookie.expires) if cookie.expires else -1
    
    # httpOnly detection: cookie._rest may contain 'HttpOnly' or 'httponly' flags
    http_only = False
    try:
        rest = getattr(cookie, "_rest", {}) or {}
        # some cookie objects store HttpOnly as a key; check common casings
        http_only = bool(rest.get("HttpOnly") or rest.get("httponly") or rest.get("HttpOnly".lower()))
    except Exception:
        http_only = False
    
    # sameSite detection: cookie._rest may contain 'SameSite' or 'samesite'
    same_site = "Lax"  # default
    try:
        rest = getattr(cookie, "_rest", {}) or {}
        s = rest.get("SameSite") or rest.get("samesite") or None
        if s:
            s_up = s.capitalize()
            if s_up in ("Lax", "Strict", "None"):
                same_site = s_up
    except Exception:
        same_site = "Lax"
    
    return {
        "name": cookie.name,
        "value": cookie.value,
        "domain": domain,
        "path": path,
        "expires": expires,
        "httpOnly": bool(cookie.has_nonstandard_attr("HttpOnly")) if hasattr(cookie, "has_nonstandard_attr") else http_only,
        "secure": bool(cookie.secure),
        "sameSite": same_site
    }


def get_linkedin_cookies_for_playwright() -> List[Dict]:
    """
    Returns a list of Playwright-compatible cookie dictionaries for domain linkedin.com
    """
    print("[LinkedIn Local Check] Loading cookies from all browsers...")
    cj = load_all_browser_cookies()
    if not cj:
        print("[LinkedIn Local Check] [WARNING] No cookies loaded from any browser")
        print("[LinkedIn Local Check] Note: If your browser is open, close it and try again. browser-cookie3 needs the browser to be closed to access the cookie database.")
        return []
    
    print(f"[LinkedIn Local Check] Loaded cookie jar with cookies from browser")
    
    linkedin_cookies = []
    total_cookies = 0
    for c in cj:
        total_cookies += 1
        # c is http.cookiejar.Cookie
        try:
            domain = (c.domain or "").lower()
            if "linkedin.com" in domain:
                linkedin_cookies.append(cookie_to_playwright_dict(c))
        except Exception as e:
            print(f"[LinkedIn Local Check] Error processing cookie: {e}")
            continue
    
    print(f"[LinkedIn Local Check] Found {len(linkedin_cookies)} LinkedIn cookies out of {total_cookies} total cookies")
    
    # deduplicate by (name, domain, path)
    seen = set()
    unique = []
    for c in linkedin_cookies:
        key = (c["name"], c["domain"], c["path"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    
    print(f"[LinkedIn Local Check] After deduplication: {len(unique)} unique LinkedIn cookies")
    
    return unique


def get_linkedin_user_name() -> Optional[Dict]:
    """
    Get the logged-in LinkedIn user's name by extracting cookies from browser
    using browser-cookie3 and using Playwright to access the profile page.
    
    Returns:
        Dict with 'name', 'headline', 'success', or None if unavailable
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("[LinkedIn Local Check] Playwright not installed")
        return None
    
    # Get LinkedIn cookies from browser
    cookies = get_linkedin_cookies_for_playwright()
    if not cookies:
        print("[LinkedIn Local Check] No LinkedIn cookies found in local browsers")
        return {
            "success": False,
            "error": "LinkedIn cookies not found. Please log in to LinkedIn in your browser (Chrome/Edge/Firefox) first."
        }
    
    print(f"[LinkedIn Local Check] Found {len(cookies)} LinkedIn cookies from browser")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            # Add all LinkedIn cookies to context
            context.add_cookies(cookies)
            
            page = context.new_page()
            
            # Navigate to feed first to verify login and get profile URL
            print("[LinkedIn Local Check] Navigating to LinkedIn feed...")
            page.goto("https://www.linkedin.com/feed/", wait_until='networkidle', timeout=30000)
            
            # Check if we're redirected to login page
            current_url = page.url
            if "/login" in current_url:
                browser.close()
                return {
                    "success": False,
                    "error": "Not logged in. Cookies may be expired. Please log in to LinkedIn in your browser again."
                }
            
            # Wait a bit for JS to finish rendering
            page.wait_for_timeout(2000)
            
            # Try to extract profile URL from feed page navigation
            profile_url = None
            try:
                # Look for profile link in navigation - common selectors
                profile_link_selectors = [
                    "a[href*='/in/']",  # Profile link in nav
                    "a[data-control-name='nav.settings_profile']",  # Settings profile link
                    "a[href*='/me']",  # Me link (though /me doesn't work, the href might point to actual profile)
                    ".global-nav__me-photo",  # Profile photo in nav
                    "a.global-nav__primary-link-me"  # Me menu link
                ]
                
                for selector in profile_link_selectors:
                    try:
                        link_element = page.locator(selector).first
                        if link_element.count() > 0:
                            href = link_element.get_attribute('href')
                            if href and '/in/' in href:
                                profile_url = href if href.startswith('http') else f"https://www.linkedin.com{href}"
                                print(f"[LinkedIn Local Check] Found profile URL: {profile_url}")
                                break
                    except:
                        continue
                
                # If we found a profile URL, navigate to it
                if profile_url:
                    print(f"[LinkedIn Local Check] Navigating to profile: {profile_url}")
                    page.goto(profile_url, wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(2000)
                else:
                    # Fallback: try to extract name from feed page directly
                    print("[LinkedIn Local Check] Could not find profile URL, trying to extract name from feed...")
            except Exception as e:
                print(f"[LinkedIn Local Check] Error extracting profile URL: {e}")
            
            # Extract name from page
            name = None
            headline = None
            
            try:
                # Try different selectors for name
                name_selectors = [
                    "h1.text-heading-xlarge",
                    "h1[data-anonymize='person-name']",
                    "h1.break-words",
                    "h1.text-heading-xlarge.inline",
                    ".pv-text-details__left-panel h1",
                    "h1.break-words.text-heading-xlarge"
                ]
                
                for selector in name_selectors:
                    try:
                        name_element = page.locator(selector).first
                        if name_element.count() > 0:
                            name = name_element.inner_text(timeout=3000).strip()
                            if name:
                                print(f"[LinkedIn Local Check] Found name using selector: {selector}")
                                break
                    except:
                        continue
                
                # Try to get headline
                headline_selectors = [
                    ".text-body-medium.break-words",
                    ".pv-text-details__left-panel .text-body-medium",
                    "[data-anonymize='headline']",
                    ".text-body-medium"
                ]
                
                for selector in headline_selectors:
                    try:
                        headline_element = page.locator(selector).first
                        if headline_element.count() > 0:
                            headline = headline_element.inner_text(timeout=3000).strip()
                            if headline:
                                print(f"[LinkedIn Local Check] Found headline using selector: {selector}")
                                break
                    except:
                        continue
                
            except Exception as e:
                print(f"[LinkedIn Local Check] Error extracting name: {e}")
            
            browser.close()
            
            if name:
                print(f"[LinkedIn Local Check] [OK] Found user name: {name}")
                return {
                    "success": True,
                    "name": name,
                    "headline": headline if headline else None
                }
            else:
                print("[LinkedIn Local Check] Could not extract name from profile page")
                # Try to get page title as fallback
                try:
                    page_title = page.title()
                    if page_title and "LinkedIn" in page_title:
                        # Sometimes name is in title
                        name_from_title = page_title.replace(" | LinkedIn", "").strip()
                        if name_from_title:
                            return {
                                "success": True,
                                "name": name_from_title,
                                "headline": headline if headline else None
                            }
                except:
                    pass
                
                return {
                    "success": False,
                    "error": "Could not extract name from profile page. May need to log in to LinkedIn in browser."
                }
                
    except Exception as e:
        error_msg = str(e)
        print(f"[LinkedIn Local Check] Error getting user name: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

