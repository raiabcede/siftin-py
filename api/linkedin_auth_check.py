"""
LinkedIn Authentication Checker
Checks if user is logged into LinkedIn using Firefox profile
"""
import os
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


def check_linkedin_auth(firefox_profile_path: str, headless: bool = False) -> Dict:
    """
    Check if user is logged into LinkedIn using Firefox profile.
    
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
    
    # Setup Firefox options
    options = Options()
    
    if headless:
        options.add_argument("--headless")
    
    # Use Firefox profile - proper method for Selenium 4.x
    # Convert path to absolute path to avoid issues
    profile_path = os.path.abspath(firefox_profile_path)
    profile = FirefoxProfile(profile_path)
    # Set profile on options (Selenium 4.x method)
    options.profile = profile
    
    print(f"[Auth Check] Using Firefox profile: {profile_path}")
    
    # Setup Firefox service
    service = Service(GeckoDriverManager().install())
    
    driver = None
    try:
        # Create driver with profile set via options
        driver = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        
        # Navigate to LinkedIn feed (requires login)
        driver.get("https://www.linkedin.com/feed/")
        wait(3)
        
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
        
        # Check for login indicators on the page
        try:
            # Try to find elements that only appear when logged in
            # Check for feed container or navigation bar
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "scaffold-finite-scroll__content")),
                    EC.presence_of_element_located((By.CLASS_NAME, "global-nav")),
                    EC.presence_of_element_located((By.ID, "main"))
                )
            )
            
            # Try to get user's name from navigation (if logged in)
            user_name = None
            try:
                # Look for user menu or profile link
                nav_elements = driver.find_elements(By.CSS_SELECTOR, "[data-control-name='nav.settings']")
                if nav_elements:
                    user_name = "Logged in"  # We know they're logged in
            except:
                pass
            
            return {
                "logged_in": True,
                "status": "success",
                "message": "Successfully logged into LinkedIn",
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

