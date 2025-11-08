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


def get_geckodriver_service():
    """
    Get geckodriver service, handling GitHub API rate limits by using cached versions.
    """
    import shutil
    import os
    from pathlib import Path
    
    # Try to use geckodriver from PATH first
    geckodriver_path = shutil.which("geckodriver")
    if geckodriver_path:
        print(f"[Driver] Using geckodriver from PATH: {geckodriver_path}")
        return Service(geckodriver_path)
    
    # Try to find geckodriver in api folder
    try:
        api_dir = Path(__file__).parent
        geckodriver_exe = api_dir / ("geckodriver.exe" if os.name == 'nt' else "geckodriver")
        if geckodriver_exe.exists():
            print(f"[Driver] Using geckodriver from api folder: {geckodriver_exe}")
            return Service(str(geckodriver_exe))
    except:
        pass
    
    # Try to use cached version from webdriver-manager
    try:
        cache_dir = Path.home() / ".wdm" / "drivers" / "geckodriver"
        if cache_dir.exists():
            # Find the latest version
            versions = [d for d in cache_dir.iterdir() if d.is_dir()]
            if versions:
                latest = max(versions, key=lambda x: x.name)
                geckodriver_exe = latest / ("geckodriver.exe" if os.name == 'nt' else "geckodriver")
                if geckodriver_exe.exists():
                    print(f"[Driver] Using cached geckodriver: {geckodriver_exe}")
                    return Service(str(geckodriver_exe))
    except:
        pass
    
    # Fallback: Try to download (may hit rate limit)
    try:
        return Service(GeckoDriverManager().install())
    except Exception as e:
        if "rate limit" in str(e).lower() or "429" in str(e) or "rate limit exceeded" in str(e).lower():
            print("\n" + "="*60)
            print("⚠️ GITHUB API RATE LIMIT HIT")
            print("="*60)
            print("Geckodriver download failed due to GitHub rate limiting.")
            print("\nSolutions:")
            print("1. Wait a few minutes and try again")
            print("2. Install geckodriver manually:")
            print("   - Download from: https://github.com/mozilla/geckodriver/releases")
            print("   - Extract and add to your PATH")
            print("   - Or place geckodriver.exe in the api/ folder")
            print("="*60)
        raise


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
    
    # Important: Prevent Firefox from detecting automation
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    
    # Use Firefox profile if provided (for logged-in session)
    # Proper method for Selenium 4.x using FirefoxProfile class
    if firefox_profile_path:
        # Convert path to absolute path to avoid issues
        profile_path = os.path.abspath(firefox_profile_path)
        profile = FirefoxProfile(profile_path)
        
        # IMPORTANT: Prevent profile copying to maintain session
        # This ensures the profile is used directly, not copied
        profile.set_preference("profile.default_directory", profile_path)
        
        # Set profile on options (Selenium 4.x method)
        options.profile = profile
        print(f"[Scraper] Using Firefox profile: {profile_path}")
        print(f"[Scraper] Note: Make sure Firefox is closed before running to avoid profile lock issues")
    
    # Setup Firefox service
    service = get_geckodriver_service()
    
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


def filter_profiles_with_ai(profiles: List[Dict], ai_criteria: str) -> List[Dict]:
    """
    Filter profiles using AI criteria.
    Uses OpenAI API if available, otherwise falls back to keyword matching.
    
    Args:
        profiles: List of profile dictionaries
        ai_criteria: Natural language criteria for filtering
    
    Returns:
        Filtered list of profiles with match scores
    """
    if not profiles or not ai_criteria:
        return profiles
    
    print(f"[AI Filter] Filtering {len(profiles)} profiles using AI criteria...")
    print(f"[AI Filter] Criteria: {ai_criteria}")
    
    # Try to use OpenAI API if available
    try:
        import os
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if openai_api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_api_key)
                
                # Create a prompt for filtering
                profile_texts = []
                for i, profile in enumerate(profiles):
                    profile_text = f"Profile {i+1}:\n"
                    profile_text += f"Name: {profile.get('name', 'N/A')}\n"
                    profile_text += f"Title: {profile.get('title', 'N/A')}\n"
                    profile_text += f"Company: {profile.get('company', 'N/A')}\n"
                    profile_text += f"Description: {profile.get('description', 'N/A')}\n"
                    profile_texts.append(profile_text)
                
                all_profiles_text = "\n\n".join(profile_texts)
                
                prompt = f"""You are a lead qualification assistant. Given the following criteria and profiles, determine which profiles match the criteria and assign a match score (0-100).

Criteria: {ai_criteria}

Profiles:
{all_profiles_text}

For each profile, respond with:
- Profile number
- Match score (0-100, where 100 is a perfect match)
- Brief reason for the score

Format your response as JSON array with objects containing: profile_number, match_score, reason
"""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a lead qualification assistant. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                import json
                result_text = response.choices[0].message.content
                
                # Try to parse JSON response
                try:
                    # Extract JSON from markdown code blocks if present
                    if "```json" in result_text:
                        result_text = result_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in result_text:
                        result_text = result_text.split("```")[1].split("```")[0].strip()
                    
                    matches = json.loads(result_text)
                    
                    # Update profiles with match scores
                    for match in matches:
                        profile_idx = match.get('profile_number', 0) - 1
                        if 0 <= profile_idx < len(profiles):
                            profiles[profile_idx]['match_score'] = match.get('match_score', 0)
                            profiles[profile_idx]['match_reason'] = match.get('reason', '')
                    
                    # Filter profiles with score >= 50 and sort by score
                    filtered = [p for p in profiles if p.get('match_score', 0) >= 50]
                    filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
                    
                    print(f"[AI Filter] ✓ Filtered to {len(filtered)} matching profiles using OpenAI")
                    return filtered
                    
                except json.JSONDecodeError:
                    print(f"[AI Filter] ⚠️ Could not parse OpenAI response, falling back to keyword matching")
                    pass
                    
            except ImportError:
                print("[AI Filter] ⚠️ OpenAI library not installed, falling back to keyword matching")
                pass
            except Exception as e:
                print(f"[AI Filter] ⚠️ OpenAI API error: {e}, falling back to keyword matching")
                pass
    except Exception as e:
        print(f"[AI Filter] ⚠️ Error with AI filtering: {e}, falling back to keyword matching")
        pass
    
    # Fallback: Simple keyword matching
    print("[AI Filter] Using keyword-based matching (fallback)")
    criteria_lower = ai_criteria.lower()
    keywords = [w for w in criteria_lower.split() if len(w) > 3]  # Filter out short words
    
    filtered = []
    for profile in profiles:
        score = 0
        profile_text = f"{profile.get('name', '')} {profile.get('title', '')} {profile.get('company', '')} {profile.get('description', '')}".lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in profile_text)
        if matches > 0:
            score = min(80, matches * 20)  # Cap at 80 for keyword matching
            profile['match_score'] = score
            profile['match_reason'] = f"Matched {matches} keywords from criteria"
            filtered.append(profile)
    
    filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    print(f"[AI Filter] ✓ Filtered to {len(filtered)} profiles using keyword matching")
    return filtered


def extract_names_only(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False,
    return_by_page: bool = False
):
    """
    Fast extraction of names only from LinkedIn search results.
    This is optimized to save time by only extracting names, skipping other data.
    
    Args:
        search_url: LinkedIn search results URL
        firefox_profile_path: Path to Firefox profile (for logged-in session)
        max_results: Maximum number of results to extract
        max_pages: Maximum number of pages to extract
        headless: Run browser in headless mode
        return_by_page: If True, returns dict with 'names' and 'by_page' keys
    
    Returns:
        List of names (strings) or dict with 'names' and 'by_page' if return_by_page=True
    """
    names = []
    
    print(f"[Name Extractor] Starting name extraction for URL: {search_url}")
    print(f"[Name Extractor] Max results: {max_results}, Max pages: {max_pages}")
    
    # Parse URL to extract parameters
    url_params = parse_linkedin_url(search_url)
    keywords = url_params.get('keywords', '')
    geo_urn = url_params.get('geo_urn', '')
    
    # Setup Firefox options
    options = Options()
    
    if headless:
        options.add_argument("--headless")
    
    # Important: Prevent Firefox from detecting automation
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    
    # Use Firefox profile if provided (for logged-in session)
    if firefox_profile_path:
        profile_path = os.path.abspath(firefox_profile_path)
        profile = FirefoxProfile(profile_path)
        
        # IMPORTANT: Prevent profile copying to maintain session
        profile.set_preference("profile.default_directory", profile_path)
        
        options.profile = profile
        print(f"[Name Extractor] Using Firefox profile: {profile_path}")
        print(f"[Name Extractor] Note: Make sure Firefox is closed before running to avoid profile lock issues")
    
    # Setup Firefox service
    service = get_geckodriver_service()
    
    # Create driver
    driver = None
    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        
        # Build search URL
        if geo_urn:
            search_url_full = f"{BASE_LINKEDIN_URL}/search/results/people/?geoUrn={geo_urn}&keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR"
        else:
            search_url_full = f"{BASE_LINKEDIN_URL}/search/results/people/?keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR"
        
        # Navigate to search URL
        print(f"[Name Extractor] Navigating to: {search_url_full}")
        driver.get(search_url_full)
        wait(5)  # Wait longer for page to load
        
        # Verify we're on the right page
        current_url = driver.current_url
        print(f"[Name Extractor] Current URL after navigation: {current_url}")
        
        # Check if we need to login or if there's a redirect
        if "challenge" in current_url.lower() or "login" in current_url.lower():
            print("[Name Extractor] ⚠️ Detected login/challenge page. You may need to log in manually.")
        
        # Scroll to bottom to load pagination
        scroll_to_bottom(driver)
        wait(3)  # Wait longer after scrolling
        
        # Get total number of pages
        total_pages = max_pages
        try:
            pagination_list = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, PAGINATION_LIST_CLASS))
            )
            last_page_number = int(pagination_list.find_elements(By.TAG_NAME, "li")[-1].find_element(By.TAG_NAME, "span").text)
            total_pages = min(last_page_number, max_pages)
            print(f"[Name Extractor] Found {last_page_number} pages, will extract up to {total_pages} pages")
        except Exception as e:
            print(f"[Name Extractor] Could not find pagination list: {e}")
            print("[Name Extractor] Assuming only one page of results...")
            total_pages = 1
        
        # Extract names from each page
        current_page = 1
        page_names = []  # Store names per page
        
        for _ in range(total_pages):
            if len(names) >= max_results:
                print(f"[Name Extractor] Reached max results ({max_results}), stopping...")
                break
            
            print(f"\n[Name Extractor] Extracting names from page {current_page}/{total_pages}...")
            print("-" * 60)
            
            # Navigate to page (if not first page)
            if current_page > 1:
                if geo_urn:
                    page_url = f"{BASE_LINKEDIN_URL}/search/results/people/?geoUrn={geo_urn}&keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR&page={current_page}"
                else:
                    page_url = f"{BASE_LINKEDIN_URL}/search/results/people/?keywords={keywords}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR&page={current_page}"
                driver.get(page_url)
                wait(4)  # Wait longer for page to load
                
                # Verify we're on the right page
                if "challenge" in driver.current_url.lower() or "login" in driver.current_url.lower():
                    print(f"[Name Extractor] ⚠️ Detected login/challenge page on page {current_page}")
            
            # Wait a bit more and scroll to ensure content loads
            wait(3)
            scroll_to_bottom(driver)
            wait(2)
            driver.execute_script("window.scrollTo(0, 0);")  # Scroll back to top
            wait(1)
            
            # Initialize page_names_list before extraction
            page_names_list = []
            
            # Try to find results list, but if it fails, use fallback immediately
            results_list = None
            try:
                results_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, RESULTS_LIST_CLASS))
                )
                print(f"[Name Extractor] Found results list on page {current_page}")
            except Exception as e:
                print(f"[Name Extractor] Could not find results list on page {current_page}: {e}")
                print(f"[Name Extractor] Current URL: {driver.current_url}")
                print(f"[Name Extractor] Page title: {driver.title}")
                # Try alternative selectors
                alt_selectors = [
                    (By.CSS_SELECTOR, "ul.reusable-search__entity-result-list"),
                    (By.CSS_SELECTOR, "ul[class*='entity-result']"),
                    (By.CSS_SELECTOR, "ul.search-results__list"),
                    (By.CSS_SELECTOR, "div.search-results"),
                    (By.CSS_SELECTOR, "main[role='main']"),
                ]
                for selector_type, selector_value in alt_selectors:
                    try:
                        results_list = driver.find_element(selector_type, selector_value)
                        print(f"[Name Extractor] Found results using alternative selector: {selector_value}")
                        break
                    except:
                        continue
                
                # If still no results list, use fallback method immediately
                if not results_list:
                    print("[Name Extractor] No results list found, using fallback method...")
                    # Fallback: Find all profile links directly
                    try:
                        all_profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                        print(f"[Name Extractor] Fallback: Found {len(all_profile_links)} profile links on page")
                        
                        # Remove duplicates and extract names
                        seen_hrefs = set()
                        for link in all_profile_links:
                            try:
                                href = link.get_attribute("href")
                                if href and "/in/" in href and href not in seen_hrefs:
                                    # Extract clean profile URL
                                    if "?" in href:
                                        href = href.split("?")[0]
                                    if href not in seen_hrefs:
                                        seen_hrefs.add(href)
                                        
                                        # Try to get name from link text or nearby elements
                                        link_text = link.text.strip()
                                        if link_text and " " in link_text and 3 <= len(link_text) <= 50:
                                            # Looks like a name
                                            if link_text not in [n for n in names]:
                                                names.append(link_text)
                                                page_names_list.append(link_text)
                                                print(f"  {len(page_names_list)}. {link_text}")
                                                if len(names) >= max_results:
                                                    break
                                        else:
                                            # Try to find name in parent or nearby span/div
                                            try:
                                                parent = link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'entity-result') or contains(@class, 'search-result')][1]")
                                                # Look for name in various places
                                                name_selectors = [
                                                    ".entity-result__title-text",
                                                    "span[aria-hidden='true']",
                                                    "h3",
                                                    ".search-result__title",
                                                ]
                                                for name_sel in name_selectors:
                                                    try:
                                                        name_elem = parent.find_element(By.CSS_SELECTOR, name_sel)
                                                        name_text = name_elem.text.strip()
                                                        if name_text and " " in name_text and 3 <= len(name_text) <= 50:
                                                            if name_text not in [n for n in names]:
                                                                names.append(name_text)
                                                                page_names_list.append(name_text)
                                                                print(f"  {len(page_names_list)}. {name_text}")
                                                                if len(names) >= max_results:
                                                                    break
                                                                break
                                                    except:
                                                        continue
                                            except:
                                                pass
                            except:
                                continue
                        
                        if len(page_names_list) > 0:
                            print(f"[Name Extractor] Fallback method extracted {len(page_names_list)} names")
                            page_names.append({
                                'page': current_page,
                                'names': page_names_list,
                                'count': len(page_names_list)
                            })
                            print(f"[Name Extractor] Page {current_page}: Found {len(page_names_list)} names")
                            current_page += 1
                            continue
                        else:
                            print("[Name Extractor] Fallback method found links but couldn't extract names")
                    except Exception as fallback_error:
                        print(f"[Name Extractor] Fallback method error: {fallback_error}")
                    
                    print("[Name Extractor] Skipping this page...")
                    current_page += 1
                    continue
            
            # Get all `li` elements inside of the results list
            results = results_list.find_elements(By.TAG_NAME, "li")
            print(f"[Name Extractor] Found {len(results)} result items on page {current_page}")
            
            # If no li elements, try finding div elements (LinkedIn might use divs)
            if len(results) == 0:
                print(f"[Name Extractor] No <li> elements found, trying <div> elements...")
                results = results_list.find_elements(By.TAG_NAME, "div")
                # Filter divs that might be result items (have links to profiles)
                results = [r for r in results if r.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")]
                print(f"[Name Extractor] Found {len(results)} potential result divs")
            
            if len(results) == 0:
                print(f"[Name Extractor] ⚠️ No result items found. Trying fallback method...")
                # Fallback: Find all profile links on the page directly
                try:
                    all_profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                    # Remove duplicates
                    seen_hrefs = set()
                    unique_links = []
                    for link in all_profile_links:
                        href = link.get_attribute("href")
                        if href and href not in seen_hrefs and "/in/" in href:
                            # Extract profile ID from URL to check uniqueness
                            try:
                                profile_id = href.split("/in/")[1].split("?")[0].split("/")[0]
                                if profile_id and len(profile_id) > 2:
                                    seen_hrefs.add(href)
                                    unique_links.append(link)
                            except:
                                if href not in seen_hrefs:
                                    seen_hrefs.add(href)
                                    unique_links.append(link)
                    
                    print(f"[Name Extractor] Fallback: Found {len(unique_links)} profile links on page")
                    
                    # Try to extract names from these links
                    for link in unique_links[:50]:  # Limit to 50
                        try:
                            # Try to get text from link
                            link_text = link.text.strip()
                            if link_text and len(link_text) > 1:
                                # Check if it looks like a name (has space, reasonable length)
                                if " " in link_text and 3 <= len(link_text) <= 50:
                                    names.append(link_text)
                                    page_names_list.append(link_text)
                                    print(f"  {len(page_names_list)}. {link_text} (from link)")
                                    if len(names) >= max_results:
                                        break
                        except:
                            continue
                    
                    if len(page_names_list) > 0:
                        print(f"[Name Extractor] Fallback method extracted {len(page_names_list)} names")
                        # Store and continue to next page
                        page_names.append({
                            'page': current_page,
                            'names': page_names_list,
                            'count': len(page_names_list)
                        })
                        print(f"[Name Extractor] Page {current_page}: Found {len(page_names_list)} names")
                        current_page += 1
                        continue
                except Exception as e:
                    print(f"[Name Extractor] Fallback method also failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Debug: Print some HTML to see what's on the page
                try:
                    page_text = driver.page_source[:500]  # First 500 chars
                    print(f"[Name Extractor] Page source preview: {page_text}...")
                except:
                    pass
            
            # Extract names from this page (if we have results)
            for idx, result in enumerate(results):
                if len(names) >= max_results:
                    break
                
                try:
                    # Try multiple methods to get the name
                    name = None
                    
                    # Method 1: Original method
                    try:
                        name_elem = result.find_element(By.CLASS_NAME, PERSON_NAME_CLASS)
                        spans = name_elem.find_elements(By.TAG_NAME, "span")
                        if len(spans) > 1:
                            name = spans[1].text
                    except Exception as e1:
                        # Method 2: Try direct span search
                        try:
                            name_elem = result.find_element(By.CLASS_NAME, PERSON_NAME_CLASS)
                            name = name_elem.text
                        except Exception as e2:
                            # Method 3: Try CSS selector
                            try:
                                name_elem = result.find_element(By.CSS_SELECTOR, f".{PERSON_NAME_CLASS} span")
                                name = name_elem.text
                            except Exception as e3:
                                # Method 4: Try any link with /in/ in href
                                try:
                                    links = result.find_elements(By.TAG_NAME, "a")
                                    for link in links:
                                        href = link.get_attribute("href")
                                        if href and "/in/" in href:
                                            # Try to get text from this link or nearby
                                            name = link.text.strip()
                                            if not name:
                                                # Try parent element
                                                try:
                                                    parent = link.find_element(By.XPATH, "..")
                                                    name = parent.text.strip()
                                                except:
                                                    pass
                                            if name:
                                                break
                                except:
                                    pass
                    
                    if name and name.strip():
                        name_clean = name.strip()
                        names.append(name_clean)
                        page_names_list.append(name_clean)
                        print(f"  {len(page_names_list)}. {name_clean}")
                    else:
                        if idx < 3:  # Only print first 3 failures to avoid spam
                            print(f"  [Debug] Result {idx+1}: Could not extract name")
                        
                except Exception as e:
                    if idx < 3:  # Only print first 3 errors to avoid spam
                        print(f"  [Debug] Result {idx+1}: Error - {str(e)[:100]}")
                    continue
            
            # Store names for this page
            page_names.append({
                'page': current_page,
                'names': page_names_list,
                'count': len(page_names_list)
            })
            
            print(f"[Name Extractor] Page {current_page}: Found {len(page_names_list)} names")
            
            # Increment current page
            current_page += 1
        
        print(f"\n[Name Extractor] ✓ Extracted {len(names)} names total from {len(page_names)} pages")
        print("\n" + "="*60)
        print("ALL NAMES BY PAGE:")
        print("="*60)
        
        for page_data in page_names:
            print(f"\nPAGE {page_data['page']} ({page_data['count']} names):")
            print("-" * 60)
            for i, name in enumerate(page_data['names'], 1):
                print(f"  {i}. {name}")
        
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        for page_data in page_names:
            print(f"Page {page_data['page']}: {page_data['count']} names")
        print(f"Total: {len(names)} names from {len(page_names)} pages")
        print("="*60)
        
        if return_by_page:
            return {
                'names': names,
                'by_page': page_names
            }
        return names
        
    except Exception as e:
        print(f"[Name Extractor] ✗ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return names
        
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


def extract_and_filter_names(
    search_url: str,
    ai_criteria: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False
) -> List[Dict]:
    """
    Extract all profiles from LinkedIn search, then filter using AI criteria.
    This is a two-step process: extract all results first, then filter.
    
    Args:
        search_url: LinkedIn search results URL
        ai_criteria: Natural language criteria for filtering
        firefox_profile_path: Path to Firefox profile (for logged-in session)
        max_results: Maximum number of results to extract before filtering
        max_pages: Maximum number of pages to extract
        headless: Run browser in headless mode
    
    Returns:
        List of filtered profile dictionaries with match scores
    """
    print(f"[Extract & Filter] Starting extraction and filtering...")
    print(f"[Extract & Filter] Will extract all results first, then filter using AI criteria")
    
    # Step 1: Extract all profiles (using the full scraper)
    print("\n" + "="*60)
    print("STEP 1: Extracting all profiles from LinkedIn...")
    print("="*60)
    all_profiles = scrape_linkedin_search(
        search_url=search_url,
        firefox_profile_path=firefox_profile_path,
        max_results=max_results,
        max_pages=max_pages,
        headless=headless
    )
    
    print(f"\n[Extract & Filter] ✓ Extracted {len(all_profiles)} profiles total")
    
    # Step 2: Filter using AI criteria
    if not ai_criteria or not ai_criteria.strip():
        print("\n[Extract & Filter] ⚠️ No AI criteria provided, returning all profiles")
        return all_profiles
    
    print("\n" + "="*60)
    print("STEP 2: Filtering profiles using AI criteria...")
    print("="*60)
    filtered_profiles = filter_profiles_with_ai(all_profiles, ai_criteria.strip())
    
    print(f"\n[Extract & Filter] ✓ Filtered to {len(filtered_profiles)} matching profiles")
    print("\n" + "="*60)
    print("FILTERED RESULTS (sorted by match score):")
    print("="*60)
    for i, profile in enumerate(filtered_profiles, 1):
        score = profile.get('match_score', 0)
        name = profile.get('name', 'N/A')
        title = profile.get('title', 'N/A')
        company = profile.get('company', 'N/A')
        print(f"{i}. [{score}%] {name} - {title} at {company}")
    print("="*60)
    
    return filtered_profiles


async def extract_names_only_async(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False,
    return_by_page: bool = False
):
    """
    Async wrapper for extract_names_only.
    This runs the blocking Selenium code in a thread pool.
    """
    import asyncio
    import concurrent.futures
    
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            extract_names_only,
            search_url,
            firefox_profile_path,
            max_results,
            max_pages,
            headless,
            return_by_page
        )
        return result


async def extract_and_filter_names_async(
    search_url: str,
    ai_criteria: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 10,
    headless: bool = False
) -> List[Dict]:
    """
    Async wrapper for extract_and_filter_names.
    This runs the blocking Selenium code in a thread pool.
    """
    import asyncio
    import concurrent.futures
    
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            extract_and_filter_names,
            search_url,
            ai_criteria,
            firefox_profile_path,
            max_results,
            max_pages,
            headless
        )
        return result

