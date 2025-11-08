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
    max_pages: int = 1,
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


def extract_profile_links(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 1,
    headless: bool = False,
    return_by_page: bool = False
):
    """
    Extract profile links/URLs from LinkedIn search results.
    This is more reliable than extracting names since links are always present.
    
    Args:
        search_url: LinkedIn search results URL
        firefox_profile_path: Path to Firefox profile (for logged-in session)
        max_results: Maximum number of results to extract
        max_pages: Maximum number of pages to extract
        headless: Run browser in headless mode
        return_by_page: If True, returns dict with 'links' and 'by_page' keys
    
    Returns:
        List of profile URLs (strings) or dict with 'links' and 'by_page' if return_by_page=True
    """
    profile_links = []
    
    print(f"[Link Extractor] Starting profile link extraction for URL: {search_url}")
    print(f"[Link Extractor] Max results: {max_results}, Max pages: {max_pages}")
    
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
        print(f"[Link Extractor] Using Firefox profile: {profile_path}")
        print(f"[Link Extractor] Note: Make sure Firefox is closed before running to avoid profile lock issues")
    
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
        print(f"[Link Extractor] Navigating to: {search_url_full}")
        driver.get(search_url_full)
        wait(5)  # Wait longer for page to load
        
        # Verify we're on the right page
        current_url = driver.current_url
        print(f"[Link Extractor] Current URL after navigation: {current_url}")
        
        # Check if we need to login or if there's a redirect
        if "challenge" in current_url.lower() or "login" in current_url.lower():
            print("[Link Extractor] ⚠️ Detected login/challenge page. You may need to log in manually.")
        
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
            print(f"[Link Extractor] Found {last_page_number} pages, will extract up to {total_pages} pages")
        except Exception as e:
            print(f"[Link Extractor] Could not find pagination list: {e}")
            print("[Link Extractor] Assuming only one page of results...")
            total_pages = 1
        
        # Extract links from each page
        current_page = 1
        page_links = []  # Store links per page
        
        for _ in range(total_pages):
            if len(profile_links) >= max_results:
                print(f"[Link Extractor] Reached max results ({max_results}), stopping...")
                break
            
            print(f"\n[Link Extractor] Extracting links from page {current_page}/{total_pages}...")
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
                    print(f"[Link Extractor] ⚠️ Detected login/challenge page on page {current_page}")
            
            # Wait a bit and scroll to ensure content loads
            wait(3)
            scroll_to_bottom(driver)
            wait(2)
            driver.execute_script("window.scrollTo(0, 0);")  # Scroll back to top
            wait(1)
            
            # Find all profile links on the page
            try:
                all_profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                print(f"[Link Extractor] Found {len(all_profile_links)} profile links on page {current_page}")
                
                # Extract unique profile URLs
                seen_profile_ids = set()
                page_links_list = []
                
                for link in all_profile_links:
                    if len(profile_links) >= max_results:
                        break
                    
                    try:
                        href = link.get_attribute("href")
                        if not href or "/in/" not in href:
                            continue
                        
                        # Clean and extract profile URL
                        clean_href = href.split("?")[0].split("#")[0]  # Remove query params and fragments
                        if "/in/" in clean_href:
                            try:
                                profile_id = clean_href.split("/in/")[1].strip("/")
                                if profile_id and len(profile_id) > 2 and profile_id not in seen_profile_ids:
                                    seen_profile_ids.add(profile_id)
                                    profile_links.append(clean_href)
                                    page_links_list.append(clean_href)
                                    print(f"  {len(page_links_list)}. {clean_href}")
                            except:
                                # Fallback: use full URL if profile ID extraction fails
                                if clean_href not in seen_profile_ids:
                                    seen_profile_ids.add(clean_href)
                                    profile_links.append(clean_href)
                                    page_links_list.append(clean_href)
                                    print(f"  {len(page_links_list)}. {clean_href}")
                    except:
                        continue
                
                # Store links for this page
                page_links.append({
                    'page': current_page,
                    'links': page_links_list,
                    'count': len(page_links_list)
                })
                
                print(f"[Link Extractor] Page {current_page}: Found {len(page_links_list)} unique profile links")
                
            except Exception as e:
                print(f"[Link Extractor] Error extracting links from page {current_page}: {e}")
                import traceback
                traceback.print_exc()
            
            # Increment current page
            current_page += 1
        
        print(f"\n[Link Extractor] ✓ Extracted {len(profile_links)} profile links total from {len(page_links)} pages")
        print("\n" + "="*60)
        print("ALL PROFILE LINKS BY PAGE:")
        print("="*60)
        
        for page_data in page_links:
            print(f"\nPAGE {page_data['page']} ({page_data['count']} links):")
            print("-" * 60)
            for i, link in enumerate(page_data['links'], 1):
                print(f"  {i}. {link}")
        
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        for page_data in page_links:
            print(f"Page {page_data['page']}: {page_data['count']} links")
        print(f"Total: {len(profile_links)} profile links from {len(page_links)} pages")
        print("="*60)
        
        if return_by_page:
            return {
                'links': profile_links,
                'by_page': page_links
            }
        return profile_links
        
    except Exception as e:
        print(f"[Link Extractor] ✗ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return profile_links
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def extract_names_only(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 1,
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
                    # Fallback: Find all profile links directly and extract ALL names
                    try:
                        all_profile_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                        print(f"[Name Extractor] Fallback: Found {len(all_profile_links)} profile links on page")
                        
                        # Remove duplicates by profile ID
                        seen_profile_ids = set()
                        unique_links = []
                        
                        for link in all_profile_links:
                            try:
                                href = link.get_attribute("href")
                                if not href or "/in/" not in href:
                                    continue
                                
                                # Extract profile ID
                                try:
                                    # Clean URL
                                    clean_href = href.split("?")[0].split("#")[0]
                                    if "/in/" in clean_href:
                                        profile_id = clean_href.split("/in/")[1].strip("/")
                                        if profile_id and len(profile_id) > 2 and profile_id not in seen_profile_ids:
                                            seen_profile_ids.add(profile_id)
                                            unique_links.append(link)
                                except:
                                    # Fallback: use full URL
                                    if href not in seen_profile_ids:
                                        seen_profile_ids.add(href)
                                        unique_links.append(link)
                            except:
                                continue
                        
                        print(f"[Name Extractor] Found {len(unique_links)} unique profile links")
                        print(f"[Name Extractor] Attempting to extract names from all {len(unique_links)} links...")
                        
                        # Extract names from each link - try multiple methods
                        for link_idx, link in enumerate(unique_links):
                            if link_idx < 5:  # Debug first 5
                                try:
                                    href = link.get_attribute("href")
                                    print(f"  [Debug] Processing link {link_idx+1}/{len(unique_links)}: {href[:50]}...")
                                except:
                                    pass
                            if len(names) >= max_results:
                                break
                            
                            name_found = False
                            name_text = None
                            
                            try:
                                # Scroll link into view to ensure it's loaded
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                                wait(0.3)  # Small wait for content to load
                                
                                # Debug: Show what text is available from the link
                                if link_idx < 5:
                                    try:
                                        link_text_debug = link.text.strip()
                                        link_inner_html = link.get_attribute("innerHTML")[:100] if link.get_attribute("innerHTML") else ""
                                        print(f"    [Debug] Link text: '{link_text_debug[:50]}' | HTML preview: {link_inner_html}")
                                    except:
                                        pass
                                
                                # Method 1: Direct link text
                                link_text = link.text.strip()
                                if link_text and len(link_text) > 0:
                                    # Check if it looks like a name (has space or is reasonable length)
                                    if (" " in link_text and 3 <= len(link_text) <= 50) or (len(link_text) >= 2 and len(link_text) <= 30):
                                        # Check if it's NOT navigation text
                                        skip_words = ["view", "profile", "connect", "message", "more", "linkedin", "see", "all"]
                                        if not any(skip in link_text.lower() for skip in skip_words):
                                            name_text = link_text
                                            name_found = True
                                
                                # Method 2: Try aria-label
                                if not name_found:
                                    try:
                                        aria_label = link.get_attribute("aria-label")
                                        if aria_label:
                                            # Clean aria-label (remove "View profile of" etc)
                                            clean_label = aria_label.replace("View profile of", "").replace("View", "").replace("profile", "").strip()
                                            if clean_label and len(clean_label) >= 2:
                                                if " " in clean_label or len(clean_label) <= 30:
                                                    skip_words = ["connect", "message", "more"]
                                                    if not any(skip in clean_label.lower() for skip in skip_words):
                                                        name_text = clean_label
                                                        name_found = True
                                    except:
                                        pass
                                
                                # Method 3: Find name in parent container - try multiple parent levels
                                if not name_found:
                                    try:
                                        # Try multiple parent levels
                                        for level in range(1, 6):
                                            try:
                                                parent_xpath = "./" + ("../" * level) + "*[contains(@class, 'entity-result') or contains(@class, 'search-result') or contains(@class, 'reusable-search') or contains(@class, 'artdeco-entity-lockup')][1]"
                                                parent = link.find_element(By.XPATH, parent_xpath)
                                                
                                                # Try multiple selectors in parent - prioritize name-specific selectors
                                                name_selectors = [
                                                    "span[dir='ltr']",  # User found this works!
                                                    "span[data-anonymize='person-name']",
                                                    "[data-anonymize='person-name']",
                                                    ".entity-result__title-text span[dir='ltr']",
                                                    ".entity-result__title-text span[aria-hidden='true']",
                                                    ".entity-result__title-text span:not([class*='subtitle']):not([class*='secondary'])",
                                                    ".entity-result__title-text",
                                                    "h3 span[dir='ltr']",
                                                    "h3 span[aria-hidden='true']",
                                                    "h3 span",
                                                    "h3",
                                                    "a[href*='/in/'] span[dir='ltr']",
                                                    "a[href*='/in/'] span[aria-hidden='true']",
                                                    "a[href*='/in/'] span:not([class*='subtitle'])",
                                                    ".search-result__title",
                                                    "span[aria-hidden='true']:not([class*='subtitle'])",
                                                ]
                                                
                                                for name_sel in name_selectors:
                                                    try:
                                                        name_elem = parent.find_element(By.CSS_SELECTOR, name_sel)
                                                        candidate_name = name_elem.text.strip()
                                                        if candidate_name and len(candidate_name) >= 2:
                                                            # Check it's not navigation text, location, or job title
                                                            skip_words = ["view", "profile", "connect", "message", "more", "linkedin", "see", "all", "at", "company"]
                                                            if not any(skip in candidate_name.lower() for skip in skip_words):
                                                                # Check if it looks like a name (has space, reasonable length)
                                                                if " " in candidate_name and 3 <= len(candidate_name) <= 50:
                                                                    # Additional check: not a location pattern
                                                                    if not ("," in candidate_name and len(candidate_name.split(",")) == 2):
                                                                        name_text = candidate_name
                                                                        name_found = True
                                                                        break
                                                    except:
                                                        continue
                                                
                                                if name_found:
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                # Method 4: Try to get text from the entire parent element and extract name
                                if not name_found:
                                    try:
                                        # Get parent and extract all text, then find the name-like part
                                        parent = link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'entity-result') or contains(@class, 'search-result')][1]")
                                        all_text = parent.text
                                        if all_text:
                                            # Debug first few
                                            if link_idx < 3:
                                                print(f"    [Debug] Parent text preview: {all_text[:150]}")
                                            
                                            # Split by newlines and look for name-like strings
                                            lines = [line.strip() for line in all_text.split("\n") if line.strip()]
                                            # Try first few lines (name is usually at the top)
                                            for line in lines[:5]:  # Check first 5 lines only
                                                if len(line) >= 3 and len(line) <= 50:
                                                    skip_words = ["view", "profile", "connect", "message", "more", "linkedin", "see", "all", "at", "company", "benefit", "might"]
                                                    if not any(skip in line.lower() for skip in skip_words):
                                                        # Must have a space (first and last name)
                                                        if " " in line:
                                                            # Check it's not a location
                                                            if "," in line:
                                                                parts = line.split(",")
                                                                if len(parts) == 2 and len(parts[1].strip()) <= 3:
                                                                    continue  # Likely location
                                                            # Check it's not a URL or email
                                                            if "@" not in line and "http" not in line.lower():
                                                                # Check it looks like a name (2-4 words)
                                                                words = line.split()
                                                                if 2 <= len(words) <= 4 and all(2 <= len(w) <= 20 for w in words):
                                                                    name_text = line
                                                                    name_found = True
                                                                    break
                                    except:
                                        pass
                                
                                # Method 5: Try to find span[dir='ltr'] directly from link's ancestors
                                if not name_found:
                                    try:
                                        # Try to find span[dir='ltr'] in parent containers
                                        for level in range(1, 6):
                                            try:
                                                parent_xpath = "./" + ("../" * level) + "*[contains(@class, 'entity-result') or contains(@class, 'search-result')][1]"
                                                parent = link.find_element(By.XPATH, parent_xpath)
                                                
                                                # Find all span[dir='ltr'] in parent
                                                name_spans = parent.find_elements(By.CSS_SELECTOR, "span[dir='ltr']")
                                                for span in name_spans:
                                                    candidate = span.text.strip()
                                                    if candidate and " " in candidate and 3 <= len(candidate) <= 50:
                                                        # Validate it's a name
                                                        skip_words = ["view", "profile", "connect", "message", "benefit", "might", "premium", "upgrade", "try", "boost"]
                                                        if not any(skip in candidate.lower() for skip in skip_words):
                                                            # Check not location
                                                            if "," in candidate:
                                                                parts = candidate.split(",")
                                                                if len(parts) == 2 and len(parts[1].strip()) <= 3:
                                                                    continue
                                                            # Check not job title
                                                            words = candidate.split()
                                                            job_titles_check = ["manager", "director", "sdr", "bdr", "sales"]
                                                            if not any(title in candidate.lower() for title in job_titles_check):
                                                                if 2 <= len(words) <= 4:
                                                                    name_text = candidate
                                                                    name_found = True
                                                                    if link_idx < 5:
                                                                        print(f"    [Debug] Found name via span[dir='ltr']: {name_text}")
                                                                    break
                                                if name_found:
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                # Method 6: Try sibling and nearby elements more aggressively
                                if not name_found:
                                    try:
                                        # Try multiple XPath patterns for nearby elements
                                        nearby_xpaths = [
                                            "./following-sibling::*[1]//span[dir='ltr']",
                                            "./preceding-sibling::*[1]//span[dir='ltr']",
                                            "./parent::*/span[dir='ltr']",
                                            "./parent::*/div[1]//span[dir='ltr']",
                                            "./following-sibling::*[1]//span[1]",
                                            "./preceding-sibling::*[1]//span[1]",
                                            "./parent::*/span[1]",
                                            "./ancestor::div[1]//span[contains(@class, 'title')]",
                                            "./ancestor::div[1]//h3",
                                        ]
                                        for xpath in nearby_xpaths:
                                            try:
                                                nearby_elems = link.find_elements(By.XPATH, xpath)
                                                for elem in nearby_elems:
                                                    candidate = elem.text.strip()
                                                    if candidate and len(candidate) >= 2 and len(candidate) <= 50:
                                                        skip_words = ["view", "profile", "connect", "message"]
                                                        if not any(skip in candidate.lower() for skip in skip_words):
                                                            if " " in candidate and 3 <= len(candidate) <= 50:
                                                                # Check not location or job title
                                                                if "," not in candidate or ("," in candidate and len(candidate.split(",")[1].strip()) > 3):
                                                                    words = candidate.split()
                                                                    if 2 <= len(words) <= 4:
                                                                        name_text = candidate
                                                                        name_found = True
                                                                        break
                                                if name_found:
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                # Add name if found and not duplicate
                                if name_found and name_text:
                                    # Clean the name
                                    name_text = " ".join(name_text.split())  # Normalize whitespace
                                    # Remove extra characters
                                    name_text = name_text.strip(".,;:!?")
                                    
                                    # Validate it's actually a name (not promotional text, job titles, etc.)
                                    if name_text and len(name_text) >= 2:
                                        text_lower = name_text.lower()
                                        
                                        # Filter out promotional/non-name text
                                        invalid_patterns = [
                                            "you might benefit",
                                            "unlimited search",
                                            "premium",
                                            "upgrade",
                                            "try",
                                            "get",
                                            "free",
                                            "trial",
                                            "benefit from",
                                            "recommended",
                                            "suggested",
                                            "see all",
                                            "view all",
                                            "show more",
                                            "load more",
                                        ]
                                        
                                        # Common job titles and roles (not names)
                                        job_titles = [
                                            "manager", "director", "executive", "president", "ceo", "cto", "cfo",
                                            "vp", "vice president", "head of", "lead", "senior", "junior",
                                            "associate", "analyst", "specialist", "coordinator", "administrator",
                                            "engineer", "developer", "designer", "consultant", "advisor",
                                            "representative", "officer", "supervisor", "superintendent",
                                            "sdr", "bdr", "ae", "account executive", "sales", "marketing",
                                            "hr", "recruiter", "talent", "operations", "finance", "accounting",
                                            "founder", "co-founder", "owner", "partner", "principal",
                                            "professor", "teacher", "instructor", "researcher", "scientist",
                                            "doctor", "physician", "nurse", "therapist", "counselor",
                                            "attorney", "lawyer", "judge", "paralegal",
                                            "architect", "contractor", "builder",
                                        ]
                                        
                                        # Common location patterns (not names)
                                        location_patterns = [
                                            ", il", ", ca", ", ny", ", tx", ", fl", ", pa", ", oh", ", ga",
                                            ", ma", ", nc", ", mi", ", nj", ", va", ", wa", ", az", ", md",
                                            ", co", ", tn", ", in", ", mo", ", wi", ", mn", ", sc", ", al",
                                            ", la", ", ky", ", or", ", ok", ", ct", ", ia", ", ut", ", ar",
                                            ", ms", ", ks", ", nm", ", ne", ", wv", ", id", ", hi", ", nh",
                                            ", me", ", mt", ", ri", ", de", ", sd", ", nd", ", ak", ", vt",
                                            ", wy", ", dc", "united states", "usa", "uk", "united kingdom",
                                            "canada", "australia", "germany", "france", "spain", "italy",
                                        ]
                                        
                                        # Check if text contains invalid patterns
                                        is_invalid = any(pattern in text_lower for pattern in invalid_patterns)
                                        
                                        # Check if it's a job title
                                        words = name_text.split()
                                        for word in words:
                                            if word.lower() in job_titles:
                                                is_invalid = True
                                                break
                                        
                                        # Check if entire text is a job title (e.g., "SDR Manager")
                                        if any(title in text_lower for title in job_titles):
                                            is_invalid = True
                                        
                                        # Check if it's a location (e.g., "Chicago, IL")
                                        if any(loc in text_lower for loc in location_patterns):
                                            is_invalid = True
                                        
                                        # Check if it matches location pattern (City, State or City, Country)
                                        if "," in name_text and len(name_text.split(",")) == 2:
                                            parts = [p.strip() for p in name_text.split(",")]
                                            # If second part is 2-3 letters (likely state code) or common location word
                                            if len(parts) == 2:
                                                second_part = parts[1].lower()
                                                if (len(second_part) == 2 or 
                                                    second_part in ["il", "ca", "ny", "tx", "fl", "uk", "us", "usa"] or
                                                    any(loc_word in second_part for loc_word in ["states", "kingdom", "province", "region"])):
                                                    is_invalid = True
                                        
                                        # Check if it looks like a real name (has proper name structure)
                                        # Names typically: have 2-4 words, each word 2-20 chars, start with capital
                                        looks_like_name = (
                                            len(words) >= 2 and len(words) <= 4 and  # Must have at least 2 words (first + last name)
                                            all(2 <= len(word) <= 20 for word in words) and
                                            not any(word.isdigit() for word in words) and
                                            not "@" in name_text and
                                            not "http" in text_lower and
                                            # First word should start with capital (proper name)
                                            (words[0][0].isupper() if words else False)
                                        )
                                        
                                        # Additional check: if it has a comma followed by text, it's likely not a name
                                        if "," in name_text:
                                            parts = name_text.split(",")
                                            if len(parts) > 1:
                                                after_comma = parts[1].strip()
                                                # If there's substantial text after comma, it's likely a description
                                                if len(after_comma) > 5:
                                                    # Check if it contains promotional words
                                                    promo_words = ["benefit", "might", "try", "get", "upgrade", "premium", "unlimited"]
                                                    if any(word in after_comma.lower() for word in promo_words):
                                                        is_invalid = True
                                                    # Or if it's just too long (likely description)
                                                    elif len(after_comma) > 15:
                                                        is_invalid = True
                                        
                                        if not is_invalid and looks_like_name:
                                            if name_text not in names:
                                                names.append(name_text)
                                                page_names_list.append(name_text)
                                                print(f"  {len(page_names_list)}. {name_text}")
                                        else:
                                            if link_idx < 5:  # Debug first 5
                                                reason = "job title" if is_invalid and any(title in text_lower for title in job_titles) else "invalid pattern or doesn't look like name"
                                                print(f"  [Debug] Filtered out: '{name_text}' ({reason})")
                                        
                            except Exception as e:
                                # Continue to next link if this one fails
                                if link_idx < 5:  # Debug first 5 failures
                                    print(f"  [Debug] Link {link_idx+1} extraction failed: {str(e)[:80]}")
                                
                                # Last resort: try to get ANY visible text near the link
                                if link_idx < 5:
                                    try:
                                        # Get the link's href to find it again
                                        href = link.get_attribute("href")
                                        # Find all elements that contain this link
                                        containing_elements = driver.find_elements(By.XPATH, f"//a[@href='{href}']/ancestor::*")
                                        for elem in containing_elements[:3]:  # Check first 3 ancestors
                                            try:
                                                all_text = elem.text
                                                if all_text:
                                                    # Look for name-like patterns in the text
                                                    lines = [l.strip() for l in all_text.split("\n") if l.strip()]
                                                    for line in lines:
                                                        if len(line) >= 3 and len(line) <= 40 and " " in line:
                                                            skip_words = ["view", "profile", "connect", "message", "at", "company", "benefit", "might"]
                                                            if not any(skip in line.lower() for skip in skip_words):
                                                                if "," not in line or ("," in line and len(line.split(",")[1].strip()) < 5):
                                                                    # This might be a name
                                                                    if line not in names:
                                                                        names.append(line)
                                                                        page_names_list.append(line)
                                                                        print(f"  {len(page_names_list)}. {line} (last resort method)")
                                                                        break
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                continue
                        
                        # If we still don't have enough names, try a different approach
                        # Find all result containers and extract names from them
                        if len(page_names_list) < len(unique_links):
                            print(f"[Name Extractor] Only extracted {len(page_names_list)}/{len(unique_links)} names, trying alternative method...")
                            try:
                                # Find all result containers on the page
                                result_containers = driver.find_elements(By.CSS_SELECTOR, 
                                    "li[class*='entity-result'], div[class*='entity-result'], div[class*='search-result']")
                                
                                print(f"[Name Extractor] Found {len(result_containers)} result containers")
                                
                                for container_idx, container in enumerate(result_containers):
                                    if len(names) >= max_results:
                                        break
                                    
                                    try:
                                        # Scroll container into view
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
                                        wait(0.1)
                                        
                                        # Check if container has a profile link
                                        has_profile_link = container.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                                        if not has_profile_link:
                                            continue
                                        
                                        # First try to find name using span[dir='ltr'] selector (user found this works!)
                                        name_found_in_container = False
                                        try:
                                            name_spans = container.find_elements(By.CSS_SELECTOR, "span[dir='ltr']")
                                            for span in name_spans:
                                                candidate = span.text.strip()
                                                if candidate and " " in candidate and 3 <= len(candidate) <= 50:
                                                    # Validate it's a name
                                                    skip_words = ["view", "profile", "connect", "message", "benefit", "might", "premium", "upgrade", "try", "boost"]
                                                    if not any(skip in candidate.lower() for skip in skip_words):
                                                        # Check not location
                                                        if "," in candidate:
                                                            parts = candidate.split(",")
                                                            if len(parts) == 2 and len(parts[1].strip()) <= 3:
                                                                continue
                                                        # Check not job title
                                                        words = candidate.split()
                                                        job_titles_check = ["manager", "director", "sdr", "bdr", "sales"]
                                                        if not any(title in candidate.lower() for title in job_titles_check):
                                                            if 2 <= len(words) <= 4 and candidate not in names:
                                                                names.append(candidate)
                                                                page_names_list.append(candidate)
                                                                print(f"  {len(page_names_list)}. {candidate} (from span[dir='ltr'])")
                                                                name_found_in_container = True
                                                                break
                                        except:
                                            pass
                                        
                                        # If span[dir='ltr'] didn't work, try other methods
                                        if not name_found_in_container:
                                            # Get all text from container
                                            container_text = container.text
                                            if not container_text:
                                                continue
                                            
                                            # Extract all lines from container
                                            lines = [l.strip() for l in container_text.split("\n") if l.strip()]
                                            
                                            # Look for name-like patterns (first line that looks like a name)
                                            for line in lines:
                                                # Skip if too short or too long
                                                if len(line) < 3 or len(line) > 50:
                                                    continue
                                                
                                                # Must have a space (first and last name)
                                                if " " not in line:
                                                    continue
                                                
                                                # Skip promotional/navigation text
                                                skip_words = ["view", "profile", "connect", "message", "more", "linkedin", 
                                                             "see", "all", "at", "company", "benefit", "might", "try", 
                                                             "get", "upgrade", "premium", "unlimited", "search"]
                                                if any(skip in line.lower() for skip in skip_words):
                                                    continue
                                                
                                                # Skip locations (City, State or City, Country)
                                                if "," in line:
                                                    parts = [p.strip() for p in line.split(",")]
                                                    if len(parts) == 2:
                                                        second_part = parts[1].lower()
                                                        # Check if second part looks like a state/country code or location
                                                        location_indicators = ["il", "ca", "ny", "tx", "fl", "uk", "us", "usa", 
                                                                              "states", "kingdom", "province", "region", "area"]
                                                        if (len(second_part) <= 3 or 
                                                            any(indicator in second_part for indicator in location_indicators) or
                                                            len(parts[1].strip()) > 10):  # Long text after comma is likely description
                                                            continue
                                                
                                                # Check if it looks like a name (2-4 words, reasonable length)
                                                words = line.split()
                                                
                                                # Filter out job titles
                                                line_lower = line.lower()
                                                job_titles = [
                                                    "manager", "director", "executive", "sdr", "bdr", "sales", "marketing",
                                                    "engineer", "developer", "designer", "consultant", "analyst",
                                                    "representative", "officer", "supervisor", "coordinator",
                                                    "founder", "co-founder", "owner", "partner", "ceo", "cto", "cfo",
                                                ]
                                                is_job_title = any(title in line_lower for title in job_titles)
                                                
                                                # Filter out locations
                                                location_patterns = [", il", ", ca", ", ny", ", tx", ", uk", ", us"]
                                                is_location = any(pattern in line_lower for pattern in location_patterns)
                                                
                                                if (not is_job_title and not is_location and
                                                    2 <= len(words) <= 4 and  # Must have at least 2 words
                                                    all(2 <= len(w) <= 20 for w in words) and
                                                    words[0][0].isupper()):  # First word starts with capital
                                                    # Check it's not a URL or email
                                                    if "@" not in line and "http" not in line.lower():
                                                        # This looks like a name!
                                                        if line not in names:
                                                            names.append(line)
                                                            page_names_list.append(line)
                                                            print(f"  {len(page_names_list)}. {line} (from container)")
                                                            break  # Found name for this container, move to next
                                        
                                    except Exception as e:
                                        if container_idx < 3:
                                            print(f"  [Debug] Container {container_idx+1} error: {str(e)[:50]}")
                                        continue
                                
                            except Exception as e:
                                print(f"[Name Extractor] Alternative method error: {e}")
                        
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
                            print("[Name Extractor] Try running the debug script to see page structure")
                    except Exception as fallback_error:
                        print(f"[Name Extractor] Fallback method error: {fallback_error}")
                        import traceback
                        traceback.print_exc()
                    
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
    max_pages: int = 1,
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
    max_pages: int = 1,
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


async def extract_profile_links_async(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 1,
    headless: bool = False,
    return_by_page: bool = False
):
    """
    Async wrapper for extract_profile_links.
    This runs the blocking Selenium code in a thread pool.
    """
    import asyncio
    import concurrent.futures
    
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            extract_profile_links,
            search_url,
            firefox_profile_path,
            max_results,
            max_pages,
            headless,
            return_by_page
        )
        return result


async def extract_names_only_async(
    search_url: str,
    firefox_profile_path: Optional[str] = None,
    max_results: int = 50,
    max_pages: int = 1,
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
    max_pages: int = 1,
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

