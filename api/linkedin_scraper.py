import uuid
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import urllib.parse

async def scrape_linkedin_profiles_no_login(search_url: str, max_results: int = 10) -> list:
    """
    Attempt to scrape LinkedIn profiles without login (limited success)
    LinkedIn requires authentication for search results, but we can try to extract public profile URLs
    """
    leads = []
    
    try:
        # Parse the search URL to extract parameters
        parsed = urllib.parse.urlparse(search_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        # Try to extract keywords
        keywords = params.get('keywords', [''])[0] if params.get('keywords') else ''
        
        print(f"[Scraper] Attempting to scrape without login (keywords: {keywords})")
        print("[Scraper] ⚠️ Note: LinkedIn requires authentication for search results")
        print("[Scraper] This method has limited success - LinkedIn blocks most automated access")
        
        # Try using requests (will likely fail due to auth wall)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for profile links
                profile_links = soup.find_all('a', href=lambda x: x and '/in/' in x)
                
                for link in profile_links[:max_results]:
                    try:
                        href = link.get('href', '')
                        if '/in/' in href:
                            # Clean URL
                            if href.startswith('/'):
                                profile_url = f"https://www.linkedin.com{href}"
                            elif href.startswith('http'):
                                profile_url = href.split('?')[0].split('/#')[0]
                            else:
                                continue
                            
                            name = link.get_text(strip=True)
                            if name and len(name) < 100:  # Reasonable name length
                                lead = {
                                    "id": str(uuid.uuid4()),
                                    "name": name,
                                    "title": "",
                                    "company": "",
                                    "location": "",
                                    "match_score": 75,
                                    "description": "Public LinkedIn profile",
                                    "linkedin_url": profile_url,
                                    "email": None,
                                    "profile_image": None,
                                    "created_at": datetime.now().isoformat()
                                }
                                leads.append(lead)
                                print(f"[Scraper] Found profile: {name} - {profile_url}")
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"[Scraper] Request failed: {e}")
        
        if not leads:
            print("[Scraper] No profiles found without login")
            print("[Scraper] LinkedIn requires authentication for search results")
        
        return leads
        
    except Exception as e:
        print(f"[Scraper] Error: {e}")
        return []

async def scrape_linkedin_profiles(search_url: str, max_results: int = 10) -> list:
    """
    Scrape LinkedIn search results to get actual profile data
    Requires LinkedIn credentials (user will need to login)
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        import time
    except ImportError:
        print("[Scraper] Selenium not installed. Install with: pip install selenium")
        return []
    
    leads = []
    
    try:
        import os
        import platform
        
        # Setup Chrome options for headless mode (invisible browser)
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Use new headless mode (invisible)
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')  # Set window size for headless
        
        # NO REMOTE DEBUGGING - Always use Chrome profile approach
        # Check if Chrome is running (if it is, we can't use the profile)
        chrome_running = False
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        chrome_running = True
                        break
                except:
                    pass
        except ImportError:
            # psutil not available, assume Chrome might be running
            chrome_running = True
        except:
            # Error checking, assume Chrome might be running
            chrome_running = True
        
        # Get Chrome profile path
        system = platform.system()
        if system == "Windows":
            chrome_user_data = os.path.expanduser(f"~\\AppData\\Local\\Google\\Chrome\\User Data")
        elif system == "Darwin":  # macOS
            chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        else:  # Linux
            chrome_user_data = os.path.expanduser("~/.config/google-chrome")
        
        chrome_profile = os.path.join(chrome_user_data, "Default")
        use_existing_profile = False
        connected_via_remote_debugging = False  # Never use remote debugging
        
        # If Chrome is NOT running, use the profile directly (no remote debugging needed)
        if not chrome_running and os.path.exists(chrome_profile):
            print("[Scraper] ✓ Chrome is not running - using your Chrome profile directly")
            print("[Scraper] This will use your existing LinkedIn session from Chrome cookies.")
            
            chrome_options = Options()
            chrome_options.add_argument(f"--user-data-dir={chrome_user_data}")
            chrome_options.add_argument(f"--profile-directory=Default")
            # Add headless mode and other options
            chrome_options.add_argument('--headless=new')  # Invisible browser
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            use_existing_profile = True
            print("[Scraper] ✓ Will use Chrome profile with LinkedIn session")
        elif chrome_running:
            # Chrome is running - try to detect if LinkedIn cookies exist
            print("[Scraper] Chrome is running - checking if LinkedIn cookies exist...")
            linkedin_logged_in = False
            try:
                # Try to read Chrome cookies database to check for LinkedIn session
                import sqlite3
                import shutil
                import tempfile
                
                cookies_db = os.path.join(chrome_user_data, "Default", "Cookies")
                if os.path.exists(cookies_db):
                    # Copy the database to temp location (Chrome locks it when running)
                    temp_cookies_db = os.path.join(tempfile.gettempdir(), "chrome_cookies_temp.db")
                    try:
                        shutil.copy2(cookies_db, temp_cookies_db)
                        
                        conn = sqlite3.connect(temp_cookies_db)
                        cursor = conn.cursor()
                        
                        # Check for LinkedIn cookies (especially session cookies)
                        cursor.execute("""
                            SELECT name, value, host_key, expires_utc 
                            FROM cookies 
                            WHERE host_key LIKE '%linkedin.com%' 
                            AND (name LIKE '%session%' OR name LIKE '%auth%' OR name LIKE '%li_at%' OR name LIKE '%JSESSIONID%')
                            LIMIT 1
                        """)
                        
                        result = cursor.fetchone()
                        conn.close()
                        
                        if result:
                            print("[Scraper] ✓ Found LinkedIn cookies in Chrome - you are logged in!")
                            print("[Scraper] However, Chrome profile is locked while Chrome is running.")
                            print("[Scraper] To use your LinkedIn session for scraping:")
                            print("[Scraper]   1. Close Chrome (this unlocks the profile)")
                            print("[Scraper]   2. Try scraping again - it will use your Chrome profile automatically")
                            linkedin_logged_in = True
                        else:
                            print("[Scraper] ⚠️ No LinkedIn session cookies found in Chrome")
                        
                        # Clean up temp file
                        try:
                            os.remove(temp_cookies_db)
                        except:
                            pass
                    except Exception as e:
                        print(f"[Scraper] Could not read Chrome cookies: {e}")
                        print("[Scraper] (Chrome may be locking the database)")
            
            except Exception as e:
                print(f"[Scraper] Error checking cookies: {e}")
            
            if linkedin_logged_in:
                print("[Scraper] ⚠️ Chrome is running - please close Chrome to use your LinkedIn session for scraping")
                print("[Scraper] You ARE logged into LinkedIn, but Chrome needs to be closed to use the profile")
            else:
                print("[Scraper] ⚠️ Chrome is currently running - please close all Chrome windows")
                print("[Scraper] Then log into LinkedIn in Chrome, close Chrome again, and try scraping")
            
            print("[Scraper] The scraper will automatically use your Chrome profile with LinkedIn session")
            # Return login required indicator
            return ["__REQUIRES_LOGIN__"]
        
        if not use_existing_profile:
            # Chrome profile not available - use temp profile (will need login)
            print("[Scraper] ⚠️ Chrome profile not found or Chrome is running")
            print("[Scraper] Using temporary profile (no LinkedIn session)")
            
            chrome_options = Options()
            # Use temp profile (no LinkedIn session - will need login)
            import tempfile
            temp_profile_dir = os.path.join(tempfile.gettempdir(), "chrome_siftin_headless")
            os.makedirs(temp_profile_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
            print(f"[Scraper] 💡 Tip: Close Chrome, log into LinkedIn in Chrome, close Chrome again, then try scraping")
            
            connected_via_remote_debugging = False
            
            # Chrome options - use headless mode (invisible) with stealth options
            chrome_options.add_argument('--headless=new')  # Invisible browser
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            # Don't disable images - LinkedIn needs them to render properly
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            # Add stealth options to avoid detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
        try:
            if connected_via_remote_debugging:
                print("[Scraper] Connecting to existing Chrome instance via remote debugging...")
            else:
                print("[Scraper] Starting Chrome browser in headless mode (invisible)...")
                print("[Scraper] Browser will run in the background - you won't see it.")
            
            # Try to initialize ChromeDriver
            try:
                driver = webdriver.Chrome(options=chrome_options)
                if connected_via_remote_debugging:
                    print("[Scraper] ✓ Connected to Chrome via remote debugging (using your LinkedIn session)")
                else:
                    print("[Scraper] ✓ Chrome browser started in headless mode (invisible)")
                
                # Execute stealth script to avoid detection
                try:
                    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                        '''
                    })
                except:
                    pass  # CDP command might not be available
                
            except Exception as driver_error:
                error_msg = str(driver_error)
                print(f"[Scraper] ✗ Failed to start Chrome browser: {error_msg}")
                
                if "chromedriver" in error_msg.lower() or "webdriver" in error_msg.lower():
                    print("[Scraper]")
                    print("[Scraper] ChromeDriver not found or not compatible!")
                    print("[Scraper] Solutions:")
                    print("[Scraper]   1. Install webdriver-manager: pip install webdriver-manager")
                    print("[Scraper]   2. Download ChromeDriver from: https://chromedriver.chromium.org/")
                raise
            
            # Navigate directly to search URL (no login check needed - will return login required if needed)
            print("[Scraper] Navigating directly to search URL...")
            print(f"[Scraper] Search URL: {search_url}")
            
            try:
                driver.get(search_url)
                print("[Scraper] Waiting for page to load in headless mode...")
                time.sleep(8)  # Increased wait for headless mode - LinkedIn needs time
                current_url = driver.current_url.lower()
                print(f"[Scraper] Current URL after navigation: {current_url}")
                
                # Check if redirected to login page
                url_path = current_url.split('?')[0].split('#')[0]
                is_on_login_page = (
                    url_path.endswith('/login') or 
                    url_path.endswith('/signin') or
                    '/login' in url_path.split('/')[-2:] or
                    '/signin' in url_path.split('/')[-2:] or
                    'authwall' in url_path or
                    ('challenge' in url_path and 'login' in url_path)
                )
                
                has_login_form = False
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                    if password_input:
                        try:
                            form = password_input.find_element(By.XPATH, "./ancestor::form[1]")
                            form_action = form.get_attribute('action') or ''
                            if 'login' in form_action.lower() or 'signin' in form_action.lower():
                                has_login_form = True
                        except:
                            has_login_form = True
                except:
                    pass
                
                if is_on_login_page or has_login_form:
                    print("[Scraper] ⚠️ Detected login page - not logged into LinkedIn!")
                    print("[Scraper] Returning login required status...")
                    try:
                        if connected_via_remote_debugging:
                            # Don't close - keep user's Chrome open
                            pass
                        else:
                            driver.quit()
                    except:
                        pass
                    return ["__REQUIRES_LOGIN__"]
                else:
                    print("[Scraper] ✓ On search results page - logged in!")
                    already_on_search_page = True
                    
            except Exception as nav_error:
                print(f"[Scraper] Error navigating to search URL: {nav_error}")
                already_on_search_page = False
                
        except Exception as e:
            print(f"[Scraper] ChromeDriver error: {e}")
            print("[Scraper] Please install ChromeDriver from https://chromedriver.chromium.org/")
            print("[Scraper] Or install webdriver-manager: pip install webdriver-manager")
            return []
        
        if not driver:
            return []
        
        # Rest of the scraping code continues below...
        try:
            # Only navigate if we haven't already
            if not already_on_search_page:
                # Navigate to LinkedIn search page
                print(f"[Scraper] Navigating to LinkedIn search URL...")
                print(f"[Scraper] URL: {search_url}")
                
                # Navigate directly to the search URL
                driver.get(search_url)
                print("[Scraper] Waiting for page to load (headless mode needs more time)...")
                time.sleep(5)  # Increased for headless mode - LinkedIn needs time to render
            else:
                print("[Scraper] ✓ Already on search page - skipping navigation!")
                print("[Scraper] Waiting for LinkedIn to render search results...")
                time.sleep(8)  # Still need to wait for LinkedIn to render results even if already on page
            
            # Print current URL for debugging
            current_url = driver.current_url
            print(f"[Scraper] Current page URL: {current_url}")
            print(f"[Scraper] Page title: {driver.title}")
            print(f"[Scraper] ===== PROCEEDING TO SCRAPE LEADS =====")
            
            # Quick login check - check URL first (fastest)
            is_on_login_page = any([
                "login" in current_url.lower(),
                "challenge" in current_url.lower(),
                "authwall" in current_url.lower(),
                "signin" in current_url.lower()
            ])
            
            # If we're on login page, something went wrong - return login required indicator
            if is_on_login_page:
                print("[Scraper] ⚠️ Redirected to login page! Session may have expired.")
                print("[Scraper] Browser session is not logged into LinkedIn.")
                print("[Scraper] 💡 Tip: Close Chrome, log into LinkedIn in Chrome, close Chrome again, then try scraping")
                try:
                    if connected_via_remote_debugging:
                        # Don't close - keep user's Chrome open
                        pass
                    else:
                        driver.quit()
                except:
                    pass
                return ["__REQUIRES_LOGIN__"]
            
            print("[Scraper] ✓ Not on login page - proceeding with scraping...")
            print("[Scraper] ===== STARTING TO EXTRACT PROFILE DATA =====")
            
            # Page check (headless mode needs more time)
            try:
                WebDriverWait(driver, 5).until(  # Increased to 5 seconds for headless
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print("[Scraper] ✓ Page loaded")
            except:
                print("[Scraper] Page ready check timed out, continuing anyway...")
            
            # Wait for LinkedIn's JavaScript to fully render (headless needs more time)
            print("[Scraper] Waiting for LinkedIn content to render...")
            time.sleep(5)  # Increased for headless mode - LinkedIn needs time to render search results
            
            # Try to wait for profile cards to appear (more reliable than fixed wait)
            print("[Scraper] Waiting for profile cards to appear...")
            profile_cards_appeared = False
            selectors_to_try = [
                ".reusable-search__result-container",
                "li.reusable-search__result-container",
                ".entity-result",
                "div[data-chameleon-result-urn]",
            ]
            
            for wait_attempt in range(10):  # Try for up to 10 seconds
                for selector in selectors_to_try:
                    try:
                        cards = driver.find_elements(By.CSS_SELECTOR, selector)
                        if cards:
                            # Check if any card contains a profile link
                            for card in cards[:3]:  # Check first 3 cards
                                try:
                                    links = card.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                                    if links:
                                        profile_cards_appeared = True
                                        print(f"[Scraper] ✓ Profile cards appeared! Found {len(cards)} cards")
                                        break
                                except:
                                    pass
                            if profile_cards_appeared:
                                break
                    except:
                        pass
                if profile_cards_appeared:
                    break
                time.sleep(1)  # Wait 1 second before next attempt
            
            if not profile_cards_appeared:
                print("[Scraper] ⚠️ Profile cards not detected yet, but proceeding anyway...")
            
            # Scroll to trigger lazy loading (headless needs more time)
            print("[Scraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)  # Wait for content in headless mode
            
            # Scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Wait longer for lazy-loaded content in headless
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)  # Wait before searching
            
            # Suppress console errors (LinkedIn has many harmless JavaScript errors)
            try:
                driver.execute_script("""
                    if (window.console) {
                        window.console.error = function() {};
                        window.console.warn = function() {};
                    }
                """)
            except:
                pass
            
            # Check what's actually on the page
            print("[Scraper] Checking page content...")
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:200]
                print(f"[Scraper] Page content preview: {body_text[:100]}...")
            except:
                pass
            
            # Try multiple selectors for LinkedIn's search results (prioritize most common ones)
            # LinkedIn frequently changes their HTML structure, so we try many variations
            selectors = [
                ".reusable-search__result-container",  # Most common - try first
                "li.reusable-search__result-container",  # More specific
                ".entity-result",  # Common alternative
                "div[data-chameleon-result-urn]",  # LinkedIn uses data attributes
                ".search-result",
                "[data-test-id='search-result']",
            ]
            
            profile_cards = []
            print("[Scraper] Looking for search results...")
            print("[Scraper] Trying selectors (will stop at first match)...")
            
            # First, try to find ANY elements that might be profile cards (with shorter timeout)
            # Stop at first successful match to speed things up
            selector_found = False
            for selector in selectors:
                try:
                    print(f"[Scraper] Trying selector: {selector}")
                    try:
                        WebDriverWait(driver, 8).until(  # Increased to 8 seconds for headless mode
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    except:
                        continue  # Skip logging - just try next selector
                    
                    profile_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if profile_cards:
                        print(f"[Scraper] ✓ Found {len(profile_cards)} elements using selector: {selector}")
                        # Filter to only include elements that look like profile cards
                        # Check if they contain links to LinkedIn profiles
                        filtered_cards = []
                        for card in profile_cards[:20]:  # Only check first 20 to speed up
                            try:
                                # Check if card contains a LinkedIn profile link
                                links = card.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                                if links:
                                    filtered_cards.append(card)
                            except:
                                pass
                        
                        if filtered_cards:
                            profile_cards = filtered_cards
                            print(f"[Scraper] ✓ Filtered to {len(profile_cards)} profile cards with LinkedIn links")
                            selector_found = True
                            break
                        else:
                            print(f"[Scraper] Elements found but none contain profile links - trying next selector")
                    else:
                        print(f"[Scraper] Selector {selector} found 0 elements")
                except Exception as e:
                    print(f"[Scraper] Selector {selector} failed: {str(e)[:100]}")
                    continue
            
            if not selector_found:
                print("[Scraper] ⚠️ None of the selectors found profile cards!")
                print("[Scraper] LinkedIn may have changed their HTML structure.")
                print("[Scraper] Will try fallback method to find profile links...")
            
            # If still no results, try finding ANY links to LinkedIn profiles
            if not profile_cards:
                print("[Scraper] No results with standard selectors, trying to find profile links directly...")
                try:
                    # Wait a bit more for page to fully load (headless needs more time)
                    print("[Scraper] Waiting longer for fallback method...")
                    time.sleep(5)  # Increased for headless mode
                    
                    # Look for all links to LinkedIn profiles
                    profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                    print(f"[Scraper] Found {len(profile_links)} total links to LinkedIn profiles on page")
                    
                    # Filter out navigation links and other non-profile links
                    filtered_links = []
                    for link in profile_links:
                        try:
                            href = link.get_attribute('href') or ''
                            # Skip navigation links, company pages, etc.
                            if '/in/' in href and '/feed' not in href and '/company/' not in href and '/my-items' not in href:
                                # Extract profile ID from URL
                                profile_id = href.split('/in/')[-1].split('/')[0].split('?')[0]
                                if len(profile_id) > 2:  # Valid profile ID
                                    filtered_links.append(link)
                        except:
                            pass
                    
                    if filtered_links:
                        print(f"[Scraper] ✓ Found {len(filtered_links)} valid profile links")
                        # Create pseudo-cards from links
                        profile_cards = filtered_links[:max_results]
                    else:
                        print("[Scraper] ⚠️ No valid profile links found!")
                except Exception as e:
                    print(f"[Scraper] Error finding profile links: {e}")
            
            # Scroll to load more results if needed (headless needs explicit scrolling)
            if len(profile_cards) >= max_results:
                print(f"[Scraper] Found {len(profile_cards)} cards - enough to proceed")
            elif len(profile_cards) > 0:
                # Scroll multiple times to trigger lazy loading in headless mode
                print(f"[Scraper] Found {len(profile_cards)} cards, scrolling to load more...")
                for scroll_iteration in range(3):  # Scroll 3 times
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)  # Wait for content to load
                    
                    # Check for new cards
                    try:
                        new_cards = driver.find_elements(By.CSS_SELECTOR, selectors[0])
                        if new_cards and len(new_cards) > len(profile_cards):
                            profile_cards = new_cards
                            print(f"[Scraper] Found {len(profile_cards)} cards after scroll {scroll_iteration + 1}")
                        else:
                            break  # No new cards, stop scrolling
                    except:
                        break
            else:
                # No cards found - try scrolling anyway to trigger lazy loading
                print("[Scraper] No cards found initially, trying to scroll to trigger loading...")
                for scroll_iteration in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait longer for initial load
                    
                    # Try selectors again
                    for selector in selectors[:2]:  # Try first 2 selectors
                        try:
                            new_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                            if new_cards:
                                profile_cards = new_cards
                                print(f"[Scraper] Found {len(profile_cards)} cards after scrolling!")
                                break
                        except:
                            continue
                    if profile_cards:
                        break
            
            # Limit to max_results to avoid processing too many
            cards_to_process = profile_cards[:max_results] if profile_cards else []
            print(f"[Scraper] ===== FOUND {len(profile_cards)} TOTAL CARDS =====")
            print(f"[Scraper] Processing {len(cards_to_process)} cards...")
            
            if not cards_to_process:
                print("[Scraper] ⚠️ No profile cards found to process!")
                print("[Scraper] LinkedIn may have changed their HTML structure, or you may need to log in.")
                try:
                    if connected_via_remote_debugging:
                        # Don't close - keep user's Chrome open
                        pass
                    else:
                        driver.quit()
                except:
                    pass
                return []
            
            # Extract data from each profile card
            leads = []
            for i, card in enumerate(cards_to_process, 1):
                try:
                    lead_data = {}
                    
                    # Try multiple selectors for name and LinkedIn URL
                    # LinkedIn uses various structures, so we try many variations
                    name_selectors = [
                        ".entity-result__title-text a",  # Most common
                        ".entity-result__title a",  # Alternative
                        "a[href*='/in/'][aria-label]",  # LinkedIn uses aria-label for names
                        ".base-search-card__title a",
                        ".search-result__result-link",
                        "a[href*='/in/']",
                        ".search-result__info a",
                        "h3 a[href*='/in/']",
                        "h4 a[href*='/in/']",
                        "span.entity-result__title-text a",
                        "div.entity-result__title-text a",
                    ]
                    
                    # First, try to find the name link element
                    for ns in name_selectors:
                        try:
                            name_elem = card.find_element(By.CSS_SELECTOR, ns)
                            if name_elem:
                                # Get href first
                                linkedin_url_raw = name_elem.get_attribute('href')
                                
                                # Try to get name text
                                name_text = name_elem.text.strip()
                                
                                # If no text, try aria-label (LinkedIn often uses this)
                                if not name_text:
                                    name_text = name_elem.get_attribute('aria-label') or ''
                                
                                # If still no text, try innerText or textContent via JavaScript
                                if not name_text:
                                    try:
                                        name_text = driver.execute_script("return arguments[0].innerText || arguments[0].textContent", name_elem)
                                        name_text = name_text.strip() if name_text else ''
                                    except:
                                        pass
                                
                                # If still no text, try parent or sibling elements
                                if not name_text:
                                    try:
                                        parent = name_elem.find_element(By.XPATH, "./..")
                                        name_text = parent.text.strip()[:100]  # Limit length
                                    except:
                                        pass
                                
                                if linkedin_url_raw and name_text:
                                    lead_data['name'] = name_text
                                    lead_data['linkedin_url'] = linkedin_url_raw.split('?')[0]  # Remove query params
                                    print(f"[Scraper] Profile {i}: Found name '{name_text[:50]}' via selector {ns}")
                                    break
                        except:
                            continue
                    
                    # If we didn't find name via selectors, try to extract from link href
                    if not lead_data.get('name') or not lead_data.get('linkedin_url'):
                        try:
                            # Try to find any link to LinkedIn profile
                            link_elem = card.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                            if link_elem:
                                linkedin_url_raw = link_elem.get_attribute('href') or ''
                                if linkedin_url_raw:
                                    lead_data['linkedin_url'] = linkedin_url_raw.split('?')[0]
                                    
                                    # Try to get name from link
                                    name_text = link_elem.text.strip()
                                    if not name_text:
                                        name_text = link_elem.get_attribute('aria-label') or ''
                                    if not name_text:
                                        try:
                                            name_text = driver.execute_script("return arguments[0].innerText || arguments[0].textContent", link_elem)
                                            name_text = name_text.strip() if name_text else ''
                                        except:
                                            pass
                                    
                                    if name_text:
                                        lead_data['name'] = name_text
                                        print(f"[Scraper] Profile {i}: Found name '{name_text[:50]}' from link")
                        except:
                            pass
                    
                    # Extract title/headline
                    title_selectors = [
                        ".entity-result__primary-subtitle",
                        ".entity-result__summary",
                        ".search-result__snippets",
                        ".base-search-card__subtitle",
                        "div[class*='subtitle']",
                        "span[class*='subtitle']",
                    ]
                    
                    for ts in title_selectors:
                        try:
                            title_elem = card.find_element(By.CSS_SELECTOR, ts)
                            if title_elem:
                                title_text = title_elem.text.strip()
                                if title_text:
                                    lead_data['title'] = title_text
                                    break
                        except:
                            continue
                    
                    # Extract location
                    location_selectors = [
                        ".entity-result__secondary-subtitle",
                        ".search-result__location",
                        "span[class*='location']",
                    ]
                    
                    for ls in location_selectors:
                        try:
                            loc_elem = card.find_element(By.CSS_SELECTOR, ls)
                            if loc_elem:
                                loc_text = loc_elem.text.strip()
                                if loc_text:
                                    lead_data['location'] = loc_text
                                    break
                        except:
                            continue
                    
                    # Only add if we have at least a LinkedIn URL
                    if lead_data.get('linkedin_url'):
                        # Ensure name exists (use LinkedIn URL if name not found)
                        if not lead_data.get('name'):
                            # Try to extract name from LinkedIn URL
                            profile_id = lead_data['linkedin_url'].split('/in/')[-1].split('/')[0].split('?')[0]
                            lead_data['name'] = profile_id.replace('-', ' ').title()  # Fallback name
                        
                        leads.append(lead_data)
                        print(f"[Scraper] ✓ Extracted profile {i}/{len(cards_to_process)}: {lead_data.get('name', 'Unknown')[:50]}")
                    else:
                        print(f"[Scraper] ⚠️ Profile {i}: No LinkedIn URL found, skipping")
                        
                except Exception as e:
                    print(f"[Scraper] Error extracting profile {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Always close browser after scraping (browser runs in headless mode, invisible to user)
            if len(leads) > 0:
                print(f"[Scraper] ✓ Successfully extracted {len(leads)} leads!")
            else:
                print("[Scraper] ⚠️ No leads extracted")
            
            # Close browser (it's headless/invisible, runs in background)
            if connected_via_remote_debugging:
                print("[Scraper] Keeping Chrome open (using remote debugging)...")
                print("[Scraper] ✓ Scraping complete - your Chrome window remains open")
                # Don't close when using remote debugging - it would close the user's Chrome
                # Just disconnect by letting the driver go out of scope
                try:
                    # Try to switch to a new tab or keep the current one
                    # But don't close - user's Chrome should stay open
                    pass
                except:
                    pass
            else:
                print("[Scraper] Closing browser (background operation complete)...")
                try:
                    driver.quit()
                    print("[Scraper] ✓ Browser closed - no tabs left open")
                except:
                    pass
            
            # Always return results, even if empty
            print(f"[Scraper] ===== SCRAPING COMPLETE: {len(leads)} leads found =====")
            print(f"[Scraper] Returning {len(leads)} leads to API...")
            print(f"[Scraper] ✓ API should receive results now - check frontend!")
            
            # Force return - ensure we always return results
            return leads
            
        except Exception as e:
            print(f"[Scraper] Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            # Close browser on error
            try:
                if connected_via_remote_debugging:
                    # Don't close when using remote debugging - keep user's Chrome open
                    print("[Scraper] Error occurred but keeping Chrome open (remote debugging)")
                else:
                    driver.quit()  # Close entire browser when using headless
            except:
                pass
            return []
        
    except Exception as e:
        print(f"[Scraper] Error: {e}")
        import traceback
        traceback.print_exc()
        return []

