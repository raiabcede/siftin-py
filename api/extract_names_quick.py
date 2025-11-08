"""
Quick script to extract profile links from LinkedIn search results
Usage: 
  python extract_names_quick.py "https://www.linkedin.com/search/results/people/?keywords=..."
  python extract_names_quick.py "https://..." 100 5
  python extract_names_quick.py "https://..." 100 5 --save  # Save results to files
"""
import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from linkedin_scraper import extract_names_only, extract_profile_links
from utilities import save_to_json

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
        print("Usage: python extract_names_quick.py <linkedin_search_url> [max_results] [max_pages] [--save]")
        print("\nExamples:")
        print('  python extract_names_quick.py "https://www.linkedin.com/search/results/people/?keywords=sales"')
        print('  python extract_names_quick.py "https://..." 100 5')
        print('  python extract_names_quick.py "https://..." 100 5 --save  # Save results to files')
        print("\nNote: Files are only saved when --save flag is used. Use --save or --export to generate output files.")
        sys.exit(1)
    
    linkedin_url = sys.argv[1]
    max_results = 50
    max_pages = 1
    save_files = False
    
    # Parse arguments
    for arg in sys.argv[2:]:
        if arg in ['--save', '--export']:
            save_files = True
        else:
            try:
                # Try to parse as integer
                num = int(arg)
                if max_results == 50:  # First number is max_results
                    max_results = num
                elif max_pages == 1:  # Second number is max_pages
                    max_pages = num
            except ValueError:
                pass
    
    print("\n" + "="*60)
    print("LINKEDIN PROFILE LINK EXTRACTION")
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
        # Extract profile links - more reliable than names
        links = extract_profile_links(
            search_url=linkedin_url,
            firefox_profile_path=FIREFOX_PROFILE_PATH,
            max_results=max_results,
            max_pages=max_pages,
            headless=False,  # Set to True for headless mode
            return_by_page=False  # Just return list of links
        )
        
        if links:
            print(f"\n✓ Successfully extracted {len(links)} profile links!")
            
            # Only save results to files if --save or --export flag is used
            if save_files:
                # Save results to files
                try:
                    # Prepare output directory (in api folder)
                    output_dir = Path(__file__).parent / "output"
                    if not output_dir.exists():
                        output_dir.mkdir()
                    
                    # Create timestamp for filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save as JSON
                    json_data = {
                        "extraction_date": datetime.now().isoformat(),
                        "linkedin_url": linkedin_url,
                        "max_results": max_results,
                        "max_pages": max_pages,
                        "total_links": len(links),
                        "profile_links": links
                    }
                    json_file = output_dir / f"profile_links_{timestamp}.json"
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    print(f"\n✓ Saved JSON to: {json_file}")
                    
                    # Save as CSV
                    csv_file = output_dir / f"profile_links_{timestamp}.csv"
                    with open(csv_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["#", "Profile URL", "Extraction Date", "Search URL"])
                        for idx, link in enumerate(links, 1):
                            writer.writerow([idx, link, datetime.now().isoformat(), linkedin_url])
                    print(f"✓ Saved CSV to: {csv_file}")
                    
                    # Save as simple text file
                    txt_file = output_dir / f"profile_links_{timestamp}.txt"
                    with open(txt_file, "w", encoding="utf-8") as f:
                        f.write(f"LinkedIn Profile Link Extraction Results\n")
                        f.write(f"Date: {datetime.now().isoformat()}\n")
                        f.write(f"Search URL: {linkedin_url}\n")
                        f.write(f"Total Links: {len(links)}\n")
                        f.write(f"\n{'='*60}\n")
                        f.write(f"PROFILE LINKS:\n")
                        f.write(f"{'='*60}\n\n")
                        for idx, link in enumerate(links, 1):
                            f.write(f"{idx}. {link}\n")
                    print(f"✓ Saved TXT to: {txt_file}")
                    
                    print(f"\n📁 All files saved in: {output_dir.absolute()}")
                    
                except Exception as save_error:
                    print(f"\n⚠️ Warning: Could not save results to file: {save_error}")
            else:
                print("\n💡 Tip: Use --save or --export flag to save results to files")
        else:
            print("\n⚠️ No profile links were extracted. Check your LinkedIn URL and Firefox profile.")
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

