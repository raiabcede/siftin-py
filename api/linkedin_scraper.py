"""
LinkedIn Scraper using Selenium with Firefox
Based on linkedin-bot functionality
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

from utilities import wait, scroll_to_bottom, parse_linkedin_url

# LinkedIn class names (may need to be updated if LinkedIn changes their UI)
RESULTS_LIST_CLASS = "reusable-search__entity-result-list"
PAGINATION_LIST_CLASS = "artdeco-pagination__pages"
PERSON_NAME_CLASS = "entity-result__title-text"
PERSON_SUBTITLE_CLASS = "entity-result__primary-subtitle"
PERSON_SECONDARY_SUBTITLE_CLASS = "entity-result__secondary-subtitle"
PERSON_SUMMARY_CLASS = "entity-result__summary"
BASE_LINKEDIN_URL = "https://www.linkedin.com"


def scrape_linkedin_search(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False
) -> List[Dict]:
    """
    Scrape LinkedIn search results using Selenium with Firefox.
    Only extracts profile information - no connection requests or messages.
    
    Args:
        search_url: LinkedIn search results URL
        firefox_profile_path: Path to Firefox profile (for logged-in session)
        max_results: Maximum number of results to scrape
        max_pages: Maximum number of pages to scrape
        headless: Run browser in headless mode
    
    Returns:
        List of lead dictionaries
    """
    people = []
    
    print(f"[Scraper] Starting LinkedIn scrape for URL: {search_url}")
    print(f"[Scraper] Max results: {max_results}, Max pages: {max_pages}")
    
    # Parse URL to extract parameters
    url_params = parse_linkedin_url(search_url)
    keywords = url_params.get('keywords', '')
    geo_urn = url_params.get('geo_urn', '')
    
    # Setup Firefox options
    options = Options()
    
    if headless:
        options.add_argument("--headless")
    
    # Use Firefox profile if provided (for logged-in session)
    # Proper method for Selenium 4.x using FirefoxProfile class
    if firefox_profile_path:
        # Convert path to absolute path to avoid issues
        profile_path = os.path.abspath(firefox_profile_path)
        profile = FirefoxProfile(profile_path)
        # Set profile on options (Selenium 4.x method)
        options.profile = profile
        print(f"[Scraper] Using Firefox profile: {profile_path}")
    
    # Setup Firefox service
    service = Service(GeckoDriverManager().install())
    
    # Create driver
    driver = None
    try:
        # Create driver with profile set via options
        driver = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        
        # Build search URL (matching original bot format)
        if geo_urn:
            search_url_full = f"{BASE_LINKEDIN_URL}/search/results/people/?geoUrn={geo_urn}&keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR"
        else:
            search_url_full = f"{BASE_LINKEDIN_URL}/search/results/people/?keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR"
        
        # Navigate to search URL
        driver.get(search_url_full)
        wait(4)
        
        # Scroll to bottom to load pagination
        scroll_to_bottom(driver)
        wait(2)
        
        # Get total number of pages
        total_pages = max_pages
        try:
            pagination_list = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, PAGINATION_LIST_CLASS))
            )
            # Get last `li` element's text (inside of `span`) - matching original bot
            last_page_number = int(pagination_list.find_elements(By.TAG_NAME, "li")[-1].find_element(By.TAG_NAME, "span").text)
            total_pages = min(last_page_number, max_pages)
            print(f"[Scraper] Found {last_page_number} pages, will scrape up to {total_pages} pages")
        except Exception as e:
            print(f"[Scraper] Could not find pagination list: {e}")
            print("[Scraper] Assuming only one page of results...")
            total_pages = 1
        
        # Scrape each page
        current_page = 1
        for _ in range(total_pages):
            if len(people) >= max_results:
                print(f"[Scraper] Reached max results ({max_results}), stopping...")
                break
            
            print(f"[Scraper] Scraping page {current_page}/{total_pages}...")
            
            # Navigate to page (if not first page)
            if current_page > 1:
                if geo_urn:
                    page_url = f"{BASE_LINKEDIN_URL}/search/results/people/?geoUrn={geo_urn}&keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR&page={current_page}"
                else:
                    page_url = f"{BASE_LINKEDIN_URL}/search/results/people/?keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR&page={current_page}"
                driver.get(page_url)
                wait(2)
            
            # Wait for results list to be present
            try:
                results_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, RESULTS_LIST_CLASS))
                )
            except Exception as e:
                print(f"[Scraper] Could not find results list on page {current_page}: {e}")
                print("[Scraper] Skipping this page...")
                current_page += 1
                continue
            
            # Get all `li` elements inside of the results list
            results = results_list.find_elements(By.TAG_NAME, "li")
            
            # Iterate over results, get their information (matching original bot logic)
            for result in results:
                if len(people) >= max_results:
                    break
                
                try:
                    # Get profile image (PFP URL)
                    try:
                        pfp = result.find_element(By.TAG_NAME, "img").get_attribute("src")
                    except:
                        pfp = None
                    
                    # Get Profile URL (matching original bot logic)
                    profile_url = ""
                    try:
                        profile_links = result.find_elements(By.TAG_NAME, "a")
                        for url in profile_links:
                            href = url.get_attribute("href")
                            if href and "/in/" in href:
                                profile_url = href
                                break
                        else:
                            profile_url = ""
                    except:
                        profile_url = ""
                    
                    # Skip if no profile URL
                    if not profile_url:
                        continue
                    
                    # Get Name (matching original bot logic exactly)
                    try:
                        name = result.find_element(By.CLASS_NAME, PERSON_NAME_CLASS).find_elements(By.TAG_NAME, "span")[1].text
                    except:
                        continue  # Skip if no name
                    
                    # Get Subtitle (title/position)
                    try:
                        subtitle = result.find_element(By.CLASS_NAME, PERSON_SUBTITLE_CLASS).text
                    except:
                        subtitle = ""
                    
                    # Get Secondary Subtitle (company)
                    try:
                        secondary_subtitle = result.find_element(By.CLASS_NAME, PERSON_SECONDARY_SUBTITLE_CLASS).text
                    except:
                        secondary_subtitle = ""
                    
                    # Get Summary (description)
                    try:
                        summary = result.find_element(By.CLASS_NAME, PERSON_SUMMARY_CLASS).text
                    except:
                        summary = ""
                    
                    # Create lead dictionary
                    person = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "title": subtitle,
                        "company": secondary_subtitle,
                        "location": "",  # Not available in search results
                        "match_score": 85,  # Default score
                        "description": summary,
                        "linkedin_url": profile_url,
                        "email": None,
                        "profile_image": pfp,
                        "created_at": datetime.now().isoformat(),
                        "is_mock": False
                    }
                    
                    people.append(person)
                    print(f"[Scraper] ✓ Scraped: {name} - {subtitle}")
                    
                except Exception as e:
                    print(f"[Scraper] Error extracting data from result: {e}")
                    continue
            
            # Increment current page
            current_page += 1
        
        # Remove every person without profile_url (matching original bot)
        people = [person for person in people if person["linkedin_url"]]
        
        print(f"[Scraper] ✓ Scraped {len(people)} people total")
        return people
        
    except Exception as e:
        print(f"[Scraper] ✗ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return people
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


async def scrape_linkedin_search_async(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False
) -> List[Dict]:
    """
    Async wrapper for scrape_linkedin_search.
    This runs the blocking Selenium code in a thread pool.
    """
    import asyncio
    import concurrent.futures
    
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            scrape_linkedin_search,
            search_url,
            firefox_profile_path,
            max_results,
            max_pages,
            headless
        )
        return result

