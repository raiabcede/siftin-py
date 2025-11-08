"""
Utility functions for LinkedIn scraping
"""
import os
import time
import json
from datetime import datetime
from pathlib import Path


def wait(seconds: float):
    """
    Waits for specified seconds.
    """
    time.sleep(seconds)


def scroll_to_bottom(driver):
    """
    Scrolls to the bottom of the page.
    """
    print("[Scraper] Scrolling to bottom of page...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


def prepare_output_structure():
    """
    Prepares the output directory for saving scraped data.
    """
    output_dir = Path("output")
    if not output_dir.exists():
        output_dir.mkdir()
    return output_dir


def save_to_json(data, output_dir: Path = None):
    """
    Saves the data to a JSON file.
    """
    if output_dir is None:
        output_dir = prepare_output_structure()
    
    now = datetime.now()
    timestamp = now.strftime("%d-%m-%Y_%H-%M-%S")
    filename = output_dir / f"{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"[Scraper] Saved data to {filename}")
    return filename


def close_all_firefox_instances():
    """
    Closes all Firefox instances.
    """
    print("[Scraper] Closing all Firefox instances...")

    if os.name == "nt":
        os.system("taskkill /im firefox.exe /f")
    elif os.name == "posix":
        os.system("killall firefox")
    else:
        print("[Scraper] ⚠️ Unsupported OS for closing Firefox instances.")


def parse_linkedin_url(url: str):
    """
    Parse LinkedIn search URL to extract parameters.
    Returns dict with keywords, geo_urn, page, etc.
    """
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    return {
        'keywords': params.get('keywords', [''])[0],
        'geo_urn': params.get('geoUrn', [''])[0],
        'page': params.get('page', ['1'])[0],
        'base_url': f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    }


def check_profile_location(path: str) -> bool:
    """
    Checks if the specified path is a valid Firefox profile directory.
    
    Args:
        path: Path to Firefox profile
    
    Returns:
        True if valid, raises error if not
    """
    # Check if Firefox profile exists
    if not os.path.exists(path):
        raise ValueError(f"Firefox profile not found: {path}")
    
    # Check if Firefox profile is a directory
    if not os.path.isdir(path):
        raise ValueError(f"Firefox profile is not a directory: {path}")
    
    return True

