"""
Quick script to extract names from LinkedIn search results
Usage: 
  python extract_names_quick.py "https://www.linkedin.com/search/results/people/?keywords=..."
  python extract_names_quick.py "https://..." 100 5
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from linkedin_scraper import extract_names_only

# Load environment variables from .env file
# Look for .env in the api directory (where this script is located)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[Config] Loaded .env from: {env_path}")
else:
    # Fallback to default location
    load_dotenv()

# Get Firefox profile path from environment variable
FIREFOX_PROFILE_PATH = os.getenv('FIREFOX_PROFILE_PATH')

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_names_quick.py <linkedin_search_url> [max_results] [max_pages]")
        print("\nExamples:")
        print('  python extract_names_quick.py "https://www.linkedin.com/search/results/people/?keywords=sales"')
        print('  python extract_names_quick.py "https://..." 100 5')
        sys.exit(1)
    
    linkedin_url = sys.argv[1]
    max_results = 50
    max_pages = 1
    
    # Parse arguments
    if len(sys.argv) > 2:
        try:
            max_results = int(sys.argv[2])
        except ValueError:
            pass
    
    if len(sys.argv) > 3:
        try:
            max_pages = int(sys.argv[3])
        except ValueError:
            pass
    
    print("\n" + "="*60)
    print("LINKEDIN NAME EXTRACTION")
    print("="*60)
    print(f"URL: {linkedin_url}")
    print(f"Max Results: {max_results}")
    print(f"Max Pages: {max_pages}")
    if FIREFOX_PROFILE_PATH:
        print(f"Firefox Profile: {FIREFOX_PROFILE_PATH}")
    else:
        print("Firefox Profile: Not set (using default)")
    print("="*60 + "\n")
    
    try:
        # Extract names only - no AI filtering
        names = extract_names_only(
            search_url=linkedin_url,
            firefox_profile_path=FIREFOX_PROFILE_PATH,
            max_results=max_results,
            max_pages=max_pages,
            headless=False,  # Set to True for headless mode
            return_by_page=False  # Just return list of names
        )
        
        if names:
            print(f"\n✓ Successfully extracted {len(names)} names!")
        else:
            print("\n⚠️ No names were extracted. Check your LinkedIn URL and Firefox profile.")
            print("Make sure:")
            print("  1. You're logged into LinkedIn in your Firefox profile")
            print("  2. The URL is a valid LinkedIn search results URL")
            print("  3. The search has results")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Extraction interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

