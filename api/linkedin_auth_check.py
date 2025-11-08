"""
LinkedIn Authentication Checker
Checks if user is logged into LinkedIn using Firefox profile
"""
import os
import sqlite3
import time
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

from utilities import wait, close_all_firefox_instances, check_profile_location


def get_user_name_quick(firefox_profile_path: str, headless: bool = True) -> Optional[str]:
    """
    Quick browser check to get user name only. Used when cookies are already verified.
    """
    try:
        # Setup Firefox options - minimal for speed
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # Performance optimizations
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("permissions.default.image", 2)  # Block images
        
        # Use Firefox profile
        profile_path = os.path.abspath(firefox_profile_path)
        profile = FirefoxProfile(profile_path)
        options.profile = profile
        
        # Setup Firefox service
        service = Service(GeckoDriverManager().install())
        
        driver = None
        try:
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(10)  # Shorter timeout for name extraction
            
            # Navigate directly to /me page for fastest name extraction
            driver.get("https://www.linkedin.com/me")
            wait(1)  # Just enough time for page to load
            
            # Try multiple selectors to get the name
            user_name = None
            
            # Method 1: Profile header h1
            try:
                name_element = driver.find_element(By.CSS_SELECTOR, "h1.text-heading-xlarge, h1.pv-text-details__left-panel h1, h1[data-anonymize='person-name']")
                if name_element:
                    user_name = name_element.text.strip()
            except:
                pass
            
            # Method 2: Navigation aria-label
            if not user_name:
                try:
                    profile_link = driver.find_element(By.CSS_SELECTOR, "a[data-control-name='nav.settings']")
                    aria_label = profile_link.get_attribute("aria-label")
                    if aria_label and "View profile of" in aria_label:
                        user_name = aria_label.replace("View profile of", "").strip()
                except:
                    pass
            
            # Method 3: Try feed page navigation
            if not user_name:
                try:
                    driver.get("https://www.linkedin.com/feed/")
                    wait(0.5)
                    name_elements = driver.find_elements(By.CSS_SELECTOR, "a[data-control-name='nav.settings']")
                    if name_elements:
                        aria_label = name_elements[0].get_attribute("aria-label")
                        if aria_label and "View profile of" in aria_label:
                            user_name = aria_label.replace("View profile of", "").strip()
                except:
                    pass
            
            return user_name
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                    
    except Exception as e:
        print(f"[Auth Check] Quick name extraction failed: {e}")
        return None


def check_linkedin_cookies_fast(firefox_profile_path: str) -> Optional[Dict]:
    """
    Fast cookie-based check - reads cookies from Firefox profile without launching browser.
    Returns None if cookies can't be read, otherwise returns auth status.
    """
    try:
        # Firefox stores cookies in cookies.sqlite
        cookies_db = os.path.join(firefox_profile_path, "cookies.sqlite")
        
        if not os.path.exists(cookies_db):
            return None
        
        # Connect to SQLite database
        conn = sqlite3.connect(cookies_db)
        cursor = conn.cursor()
        
        # Check for LinkedIn session cookies
        # li_at is the main LinkedIn authentication cookie
        cursor.execute("""
            SELECT name, value, expiry 
            FROM moz_cookies 
            WHERE host LIKE '%linkedin.com%' 
            AND (name = 'li_at' OR name = 'JSESSIONID')
            ORDER BY expiry DESC
        """)
        
        cookies = cursor.fetchall()
        conn.close()
        
        if not cookies:
            return {
                "logged_in": False,
                "status": "not_logged_in",
                "message": "No LinkedIn cookies found",
                "note": "Please log in to LinkedIn in your Firefox profile",
                "method": "cookie_check"
            }
        
        # Check if li_at cookie exists
        li_at_found = False
        current_time = int(time.time() * 1000000)  # microseconds since epoch
        
        for cookie in cookies:
            if cookie[0] == 'li_at':
                li_at_found = True
                # Check expiry (expiry is in seconds since epoch, stored as microseconds in some cases)
                expiry = cookie[2]
                if expiry:
                    # Convert to seconds if in microseconds
                    if expiry > 1000000000000000:  # Likely in microseconds
                        expiry = expiry / 1000000
                    # Check if cookie is not expired (with 1 day buffer)
                    if expiry > (time.time() - 86400):
                        return {
                            "logged_in": True,
                            "status": "success",
                            "message": "LinkedIn cookies found (fast check)",
                            "method": "cookie_check"
                        }
                else:
                    # No expiry means session cookie - assume valid
                    return {
                        "logged_in": True,
                        "status": "success",
                        "message": "LinkedIn cookies found (fast check)",
                        "method": "cookie_check"
                    }
        
        if li_at_found:
            # Cookie exists but might be expired - need browser check
            return None
        
        return {
            "logged_in": False,
            "status": "not_logged_in",
            "message": "LinkedIn cookies not found or expired",
            "note": "Please log in to LinkedIn in your Firefox profile",
            "method": "cookie_check"
        }
        
    except Exception as e:
        # If cookie check fails, return None to fall back to browser check
        print(f"[Auth Check] Cookie check failed: {e}")
        return None


def check_linkedin_auth(firefox_profile_path: str, headless: bool = False) -> Dict:
    """
    Check if user is logged into LinkedIn using Firefox profile.
    First tries fast cookie check, then falls back to browser check if needed.
    
    Args:
        firefox_profile_path: Path to Firefox profile directory
        headless: Run browser in headless mode
    
    Returns:
        Dictionary with authentication status and details
    """
    # Check if profile path exists
    if not os.path.exists(firefox_profile_path):
        return {
            "logged_in": False,
            "status": "error",
            "message": "Firefox profile not found",
            "error": f"Profile path does not exist: {firefox_profile_path}"
        }
    
    if not os.path.isdir(firefox_profile_path):
        return {
            "logged_in": False,
            "status": "error",
            "message": "Invalid Firefox profile path",
            "error": f"Path is not a directory: {firefox_profile_path}"
        }
    
    # Try fast cookie check first (much faster than launching browser)
    cookie_result = check_linkedin_cookies_fast(firefox_profile_path)
    if cookie_result is not None and cookie_result.get("logged_in") == True:
        # Cookie check succeeded - try to get user name quickly
        # Do a minimal browser check just to extract the name
        user_name = get_user_name_quick(firefox_profile_path, headless)
        if user_name:
            cookie_result["user_name"] = user_name
            cookie_result["message"] = f"LinkedIn cookies found (fast check) - {user_name}"
        cookie_result["profile_path"] = firefox_profile_path
        return cookie_result
    elif cookie_result is not None:
        # Cookie check found no login - return immediately
        cookie_result["profile_path"] = firefox_profile_path
        return cookie_result
    
    # Cookie check inconclusive or failed - fall back to browser check
    print("[Auth Check] Cookie check inconclusive, using browser check...")
    
    # Setup Firefox options - optimize for speed
    options = Options()
    
    # Always use headless for faster checks (can be overridden if needed)
    if headless:
        options.add_argument("--headless")
    
    # Performance optimizations
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0")
    
    # Disable images and other resources for faster loading
    options.set_preference("permissions.default.image", 2)  # Block images
    options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)
    
    # Use Firefox profile - proper method for Selenium 4.x
    # Convert path to absolute path to avoid issues
    profile_path = os.path.abspath(firefox_profile_path)
    profile = FirefoxProfile(profile_path)
    # Set profile on options (Selenium 4.x method)
    options.profile = profile
    
    print(f"[Auth Check] Using Firefox profile: {profile_path}")
    
    # Setup Firefox service with timeout
    service = Service(GeckoDriverManager().install())
    
    driver = None
    try:
        # Create driver with profile set via options
        driver = webdriver.Firefox(service=service, options=options)
        # Set page load timeout to avoid hanging
        driver.set_page_load_timeout(15)  # 15 seconds max for page load
        if not headless:
            driver.maximize_window()
        
        # Navigate to LinkedIn feed (requires login)
        driver.get("https://www.linkedin.com/feed/")
        
        # Check URL immediately - no need to wait for full page load
        # LinkedIn redirects quickly if not logged in
        wait(0.5)  # Reduced to 0.5 seconds - just enough for redirect
        
        # Check current URL - if redirected to login, not authenticated
        current_url = driver.current_url
        
        if "login" in current_url.lower() or "challenge" in current_url.lower():
            return {
                "logged_in": False,
                "status": "not_logged_in",
                "message": "Not logged into LinkedIn",
                "current_url": current_url,
                "note": "Please log in to LinkedIn in your Firefox profile"
            }
        
        # Quick check: if URL contains feed, we're likely logged in
        # Try to get user name before returning
        user_name = None
        if "feed" in current_url or "/in/" in current_url or "/mynetwork" in current_url:
            # Try to quickly get user name from the current page
            try:
                # Try to get name from navigation
                name_elements = driver.find_elements(By.CSS_SELECTOR, "a[data-control-name='nav.settings']")
                if name_elements:
                    aria_label = name_elements[0].get_attribute("aria-label")
                    if aria_label and "View profile of" in aria_label:
                        user_name = aria_label.replace("View profile of", "").strip()
            except:
                pass
            
            return {
                "logged_in": True,
                "status": "success",
                "message": "Logged into LinkedIn (detected via URL)" + (f" as {user_name}" if user_name else ""),
                "current_url": current_url,
                "user_name": user_name,
                "profile_path": firefox_profile_path
            }
        
        # Check for login indicators on the page (with shorter timeout)
        try:
            # Try to find elements that only appear when logged in
            # Reduced timeout from 5 to 2 seconds for faster response
            WebDriverWait(driver, 2).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "scaffold-finite-scroll__content")),
                    EC.presence_of_element_located((By.CLASS_NAME, "global-nav")),
                    EC.presence_of_element_located((By.ID, "main"))
                )
            )
            
            # Try to get user's name from navigation or profile
            user_name = None
            try:
                # Method 1: Try to get name from the navigation profile menu
                try:
                    # Look for the profile link in the nav
                    profile_link = driver.find_element(By.CSS_SELECTOR, "a[data-control-name='nav.settings']")
                    if profile_link:
                        # Try to get name from aria-label or title
                        aria_label = profile_link.get_attribute("aria-label")
                        if aria_label:
                            # Extract name from aria-label (format: "View profile of [Name]")
                            if "View profile of" in aria_label:
                                user_name = aria_label.replace("View profile of", "").strip()
                except:
                    pass
                
                # Method 2: Try to get name from the "Me" menu button
                if not user_name:
                    try:
                        me_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Me menu'], button[aria-label*='View profile']")
                        aria_label = me_button.get_attribute("aria-label")
                        if aria_label:
                            # Extract name from various formats
                            if "View profile of" in aria_label:
                                user_name = aria_label.replace("View profile of", "").strip()
                            elif "Me menu" in aria_label:
                                # Try to find the name in a nearby element
                                pass
                    except:
                        pass
                
                # Method 3: Navigate to /me to get the name
                if not user_name:
                    try:
                        driver.get("https://www.linkedin.com/me")
                        wait(1)
                        # Look for the name in the profile header
                        name_element = driver.find_element(By.CSS_SELECTOR, "h1.text-heading-xlarge, h1.pv-text-details__left-panel h1")
                        if name_element:
                            user_name = name_element.text.strip()
                    except:
                        pass
                
                # Method 4: Try to get from the feed page directly
                if not user_name:
                    try:
                        # Look for name in the "Who's viewed your profile" section or similar
                        name_elements = driver.find_elements(By.CSS_SELECTOR, "span[data-test-id='nav-settings__user-name'], a[data-control-name='nav.settings'] span")
                        if name_elements:
                            user_name = name_elements[0].text.strip()
                    except:
                        pass
                        
            except Exception as e:
                print(f"[Auth Check] Could not extract user name: {e}")
                pass
            
            return {
                "logged_in": True,
                "status": "success",
                "message": "Successfully logged into LinkedIn" + (f" as {user_name}" if user_name else ""),
                "current_url": current_url,
                "user_name": user_name,
                "profile_path": firefox_profile_path
            }
            
        except Exception as e:
            # If we can't find logged-in elements, check URL again
            current_url = driver.current_url
            if "feed" in current_url or "/in/" in current_url or "/mynetwork" in current_url:
                return {
                    "logged_in": True,
                    "status": "success",
                    "message": "Logged into LinkedIn (detected via URL)",
                    "current_url": current_url,
                    "profile_path": firefox_profile_path
                }
            else:
                return {
                    "logged_in": False,
                    "status": "uncertain",
                    "message": "Could not determine login status",
                    "current_url": current_url,
                    "error": str(e),
                    "note": "Please verify you are logged into LinkedIn"
                }
        
    except Exception as e:
        return {
            "logged_in": False,
            "status": "error",
            "message": "Error checking authentication",
            "error": str(e),
            "profile_path": firefox_profile_path
        }
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


async def check_linkedin_auth_async(firefox_profile_path: str, headless: bool = False) -> Dict:
    """
    Async wrapper for check_linkedin_auth.
    """
    import asyncio
    import concurrent.futures
    
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            check_linkedin_auth,
            firefox_profile_path,
            headless
        )
        return result

