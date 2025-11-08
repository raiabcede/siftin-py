"""
Debug script to see what's actually on the LinkedIn page
"""
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import time

# Get Firefox profile path from environment variable
FIREFOX_PROFILE_PATH = os.getenv('FIREFOX_PROFILE_PATH')

def debug_linkedin_page(url):
    """Debug what's on a LinkedIn search results page"""
    
    print("="*60)
    print("LINKEDIN PAGE DEBUGGER")
    print("="*60)
    print(f"URL: {url}")
    print(f"Firefox Profile: {FIREFOX_PROFILE_PATH or 'Not set'}")
    print("="*60 + "\n")
    
    # Setup Firefox
    options = Options()
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    
    if FIREFOX_PROFILE_PATH:
        profile_path = os.path.abspath(FIREFOX_PROFILE_PATH)
        profile = FirefoxProfile(profile_path)
        profile.set_preference("profile.default_directory", profile_path)
        options.profile = profile
        print(f"Using Firefox profile: {profile_path}\n")
    
    service = Service(GeckoDriverManager().install())
    driver = None
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        
        print("Navigating to URL...")
        driver.get(url)
        time.sleep(5)
        
        print(f"\nCurrent URL: {driver.current_url}")
        print(f"Page Title: {driver.title}\n")
        
        # Check for login/challenge
        if "challenge" in driver.current_url.lower() or "login" in driver.current_url.lower():
            print("⚠️ WARNING: Detected login/challenge page!")
            print("You need to log in first.\n")
        
        # Try to find results list with various selectors
        print("="*60)
        print("SEARCHING FOR RESULTS LIST...")
        print("="*60)
        
        selectors_to_try = [
            ("Class: reusable-search__entity-result-list", By.CLASS_NAME, "reusable-search__entity-result-list"),
            ("CSS: ul.reusable-search__entity-result-list", By.CSS_SELECTOR, "ul.reusable-search__entity-result-list"),
            ("CSS: ul[class*='entity-result']", By.CSS_SELECTOR, "ul[class*='entity-result']"),
            ("CSS: ul.search-results__list", By.CSS_SELECTOR, "ul.search-results__list"),
            ("CSS: div.search-results", By.CSS_SELECTOR, "div.search-results"),
            ("CSS: main[role='main']", By.CSS_SELECTOR, "main[role='main']"),
        ]
        
        results_list = None
        for name, by, selector in selectors_to_try:
            try:
                element = driver.find_element(by, selector)
                print(f"✓ Found: {name}")
                results_list = element
                break
            except:
                print(f"✗ Not found: {name}")
        
        if not results_list:
            print("\n⚠️ Could not find results list with any selector!")
            print("\nTrying to find ANY list elements...")
            all_lists = driver.find_elements(By.TAG_NAME, "ul")
            print(f"Found {len(all_lists)} <ul> elements on the page")
            for i, ul in enumerate(all_lists[:5]):  # Show first 5
                try:
                    classes = ul.get_attribute("class")
                    print(f"  UL {i+1}: class='{classes}'")
                except:
                    pass
        
        # If we found results list, check for items
        if results_list:
            print("\n" + "="*60)
            print("SEARCHING FOR RESULT ITEMS...")
            print("="*60)
            
            # Try to find list items
            li_elements = results_list.find_elements(By.TAG_NAME, "li")
            print(f"Found {len(li_elements)} <li> elements in results list")
            
            if len(li_elements) == 0:
                print("\n⚠️ No <li> elements found!")
                print("Checking for other elements...")
                all_divs = results_list.find_elements(By.TAG_NAME, "div")
                print(f"Found {len(all_divs)} <div> elements in results list")
            else:
                print(f"\nAnalyzing first 3 result items...")
                for i, li in enumerate(li_elements[:3]):
                    print(f"\n--- Result Item {i+1} ---")
                    try:
                        # Try to find name
                        name_selectors = [
                            ("Class: entity-result__title-text", By.CLASS_NAME, "entity-result__title-text"),
                            ("CSS: .entity-result__title-text", By.CSS_SELECTOR, ".entity-result__title-text"),
                            ("CSS: a[href*='/in/']", By.CSS_SELECTOR, "a[href*='/in/']"),
                        ]
                        
                        name_found = False
                        for name_sel, by, selector in name_selectors:
                            try:
                                elem = li.find_element(by, selector)
                                text = elem.text.strip()
                                if text:
                                    print(f"  Name ({name_sel}): {text}")
                                    name_found = True
                                    break
                            except:
                                pass
                        
                        if not name_found:
                            print("  Name: NOT FOUND")
                        
                        # Try to find any links
                        links = li.find_elements(By.TAG_NAME, "a")
                        linkedin_links = [l for l in links if l.get_attribute("href") and "/in/" in l.get_attribute("href")]
                        print(f"  LinkedIn profile links: {len(linkedin_links)}")
                        if linkedin_links:
                            print(f"  First link: {linkedin_links[0].get_attribute('href')}")
                        
                    except Exception as e:
                        print(f"  Error analyzing item: {e}")
        
        # Take a screenshot for debugging
        screenshot_path = "linkedin_debug_screenshot.png"
        try:
            driver.save_screenshot(screenshot_path)
            print(f"\n✓ Screenshot saved to: {screenshot_path}")
        except:
            pass
        
        # Save page source
        page_source_path = "linkedin_debug_page_source.html"
        try:
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"✓ Page source saved to: {page_source_path}")
        except:
            pass
        
        print("\n" + "="*60)
        print("DEBUG COMPLETE")
        print("="*60)
        print("\nPress Enter to close browser...")
        input()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_linkedin.py <linkedin_search_url>")
        print("\nExample:")
        print('  python debug_linkedin.py "https://www.linkedin.com/search/results/people/?keywords=sales"')
        sys.exit(1)
    
    url = sys.argv[1]
    debug_linkedin_page(url)

