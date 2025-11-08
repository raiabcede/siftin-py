"""
FastAPI server for LinkedIn Lead Capture
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import urllib.parse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


app = FastAPI(title="LinkedIn Lead Capture API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ProcessLinkedInRequest(BaseModel):
    linkedin_url: str


class ProcessLinkedInResponse(BaseModel):
    success: bool
    keywords: Optional[str] = None
    message: Optional[str] = None


class FindLeadsRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str


class Lead(BaseModel):
    id: str
    name: str
    title: str
    company: str
    location: str
    match_score: int
    description: str
    linkedin_url: str
    email: Optional[str] = None
    profile_image: Optional[str] = None
    created_at: str
    is_mock: Optional[bool] = False


class FindLeadsResponse(BaseModel):
    leads: List[Lead]
    total: int
    requires_login: Optional[bool] = False
    login_url: Optional[str] = None
    collector_id: Optional[str] = None
    errors: Optional[List[str]] = None


class ExtractNamesRequest(BaseModel):
    linkedin_url: str
    ai_criteria: Optional[str] = None
    max_results: Optional[int] = 50
    max_pages: Optional[int] = 10


class PageNames(BaseModel):
    page: int
    names: List[str]
    count: int


class ExtractNamesResponse(BaseModel):
    success: bool
    names: Optional[List[str]] = None
    names_by_page: Optional[List[PageNames]] = None
    leads: Optional[List[Lead]] = None
    total: int
    filtered: bool = False
    errors: Optional[List[str]] = None


class ExtractLinksRequest(BaseModel):
    linkedin_url: str
    max_results: Optional[int] = 50
    max_pages: Optional[int] = 10


class PageLinks(BaseModel):
    page: int
    links: List[str]
    count: int


class ExtractLinksResponse(BaseModel):
    success: bool
    links: Optional[List[str]] = None
    links_by_page: Optional[List[PageLinks]] = None
    total: int
    errors: Optional[List[str]] = None


class SaveToLibraryRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str
    run_label: str
    selected_lead_ids: List[str]


class SaveResponse(BaseModel):
    success: bool
    message: str


class ExportRequest(BaseModel):
    linkedin_url: str
    ai_criteria: str
    run_label: str
    selected_lead_ids: List[str]


class ExportResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None


def extract_keywords_from_url(linkedin_url: str) -> str:
    """Extract keywords from LinkedIn search URL"""
    try:
        parsed = urllib.parse.urlparse(linkedin_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        keywords = params.get('keywords', [''])[0] if params.get('keywords') else ''
        
        # Also try to extract from URL path
        if not keywords:
            # Look for keywords in the URL path
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and part != 'search' and part != 'results' and part != 'people':
                    # Decode URL encoding
                    decoded = urllib.parse.unquote(part)
                    if decoded and len(decoded) > 2:
                        keywords = decoded.replace('-', ' ').replace('_', ' ')
                        break
        
        return keywords if keywords else 'LinkedIn Search'
    except Exception as e:
        print(f"[API] Error extracting keywords: {e}")
        return 'LinkedIn Search'




















@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "LinkedIn Lead Capture API is running"}


# Cache for LinkedIn auth status (to avoid repeated browser launches)
_linkedin_auth_cache = {
    "result": None,
    "timestamp": 0,
    "ttl": 300  # Cache for 5 minutes (300 seconds)
}

@app.get("/api/linkedin-auth-status")
async def check_linkedin_auth_status():
    """Check LinkedIn authentication status using Firefox profile (with caching)"""
    import time
    
    firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH')
    
    if not firefox_profile_path:
        return {
            "logged_in": None,
            "status": "not_configured",
            "message": "Firefox profile path not configured",
            "note": "Set FIREFOX_PROFILE_PATH environment variable with your Firefox profile path"
        }
    
    # Check cache first
    current_time = time.time()
    if (_linkedin_auth_cache["result"] is not None and 
        current_time - _linkedin_auth_cache["timestamp"] < _linkedin_auth_cache["ttl"]):
        cached_result = _linkedin_auth_cache["result"].copy()
        cached_result["cached"] = True
        return cached_result
    
    try:
        from linkedin_auth_check import check_linkedin_auth_async
        
        # Use headless mode for faster checks
        result = await check_linkedin_auth_async(
            firefox_profile_path=firefox_profile_path,
            headless=True  # Use headless for speed
        )
        
        # Update cache
        _linkedin_auth_cache["result"] = result
        _linkedin_auth_cache["timestamp"] = current_time
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error checking LinkedIn auth: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            "logged_in": None,
            "status": "error",
            "message": "Error checking authentication",
            "error": error_msg
        }


@app.get("/api/linkedin-login-status")
async def check_linkedin_login_status():
    """Check LinkedIn login status (alias for linkedin-auth-status)"""
    # Use the same function as linkedin-auth-status
    return await check_linkedin_auth_status()


@app.post("/api/linkedin-auth-status/clear-cache")
async def clear_linkedin_auth_cache():
    """Clear the LinkedIn auth status cache (force fresh check on next request)"""
    _linkedin_auth_cache["result"] = None
    _linkedin_auth_cache["timestamp"] = 0
    return {
        "status": "success",
        "message": "Cache cleared. Next status check will be fresh."
    }


@app.get("/api/firefox-profile")
async def get_firefox_profile():
    """Get current Firefox profile path configuration"""
    firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH')
    
    return {
        "profile_path": firefox_profile_path,
        "configured": bool(firefox_profile_path),
        "exists": os.path.exists(firefox_profile_path) if firefox_profile_path else False,
        "is_directory": os.path.isdir(firefox_profile_path) if firefox_profile_path else False
    }


class FirefoxProfileRequest(BaseModel):
    profile_path: str


@app.post("/api/firefox-profile")
async def set_firefox_profile(request: FirefoxProfileRequest):
    """Set Firefox profile path (for documentation - actual setting should be done via environment variable)"""
    profile_path = request.profile_path
    
    if not profile_path:
        return {
            "success": False,
            "message": "Profile path is required"
        }
    
    if not os.path.exists(profile_path):
        return {
            "success": False,
            "message": "Profile path does not exist",
            "profile_path": profile_path
        }
    
    if not os.path.isdir(profile_path):
        return {
            "success": False,
            "message": "Profile path is not a directory",
            "profile_path": profile_path
        }
    
    # Note: In production, you'd want to save this to a config file or database
    # For now, we just validate it
    return {
        "success": True,
        "message": "Profile path is valid. Please set FIREFOX_PROFILE_PATH environment variable with this path.",
        "profile_path": profile_path,
        "note": "Set this in your .env file: FIREFOX_PROFILE_PATH=" + profile_path
    }


@app.post("/api/capture/process-linkedin", response_model=ProcessLinkedInResponse)
async def process_linkedin(request: ProcessLinkedInRequest):
    """Process LinkedIn URL and extract keywords"""
    try:
        keywords = extract_keywords_from_url(request.linkedin_url)
        
        return ProcessLinkedInResponse(
            success=True,
            keywords=keywords,
            message=f"Extracted keywords: {keywords}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing LinkedIn URL: {str(e)}")


def generate_mock_leads(linkedin_url: str, ai_criteria: str, count: int = 8) -> List[dict]:
    """Generate mock leads for testing/development"""
    import uuid
    from datetime import datetime
    
    keywords = extract_keywords_from_url(linkedin_url)
    
    mock_leads = [
        {
            "id": str(uuid.uuid4()),
            "name": "John Smith",
            "title": "Senior Sales Manager",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "match_score": 92,
            "description": f"Experienced {keywords} professional with strong sales background",
            "linkedin_url": "https://www.linkedin.com/in/johnsmith",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sarah Johnson",
            "title": "Sales Director",
            "company": "Global Solutions Inc",
            "location": "New York, NY",
            "match_score": 88,
            "description": f"Expert in {keywords} with proven track record",
            "linkedin_url": "https://www.linkedin.com/in/sarahjohnson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Michael Chen",
            "title": "VP of Sales",
            "company": "Innovation Labs",
            "location": "Austin, TX",
            "match_score": 85,
            "description": f"Strategic {keywords} leader driving growth",
            "linkedin_url": "https://www.linkedin.com/in/michaelchen",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Emily Rodriguez",
            "title": "Account Executive",
            "company": "SalesForce Pro",
            "location": "Chicago, IL",
            "match_score": 82,
            "description": f"Results-driven {keywords} professional",
            "linkedin_url": "https://www.linkedin.com/in/emilyrodriguez",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "David Wilson",
            "title": "Regional Sales Manager",
            "company": "Enterprise Solutions",
            "location": "Seattle, WA",
            "match_score": 80,
            "description": f"Seasoned {keywords} expert",
            "linkedin_url": "https://www.linkedin.com/in/davidwilson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lisa Anderson",
            "title": "Business Development Manager",
            "company": "Growth Partners",
            "location": "Boston, MA",
            "match_score": 78,
            "description": f"Dynamic {keywords} specialist",
            "linkedin_url": "https://www.linkedin.com/in/lisaanderson",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Robert Martinez",
            "title": "Sales Team Lead",
            "company": "Premium Services",
            "location": "Denver, CO",
            "match_score": 75,
            "description": f"Focused {keywords} professional",
            "linkedin_url": "https://www.linkedin.com/in/robertmartinez",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Jennifer Taylor",
            "title": "Senior Account Manager",
            "company": "Client Success Co",
            "location": "Los Angeles, CA",
            "match_score": 73,
            "description": f"Client-focused {keywords} expert",
            "linkedin_url": "https://www.linkedin.com/in/jennifertaylor",
            "email": None,
            "profile_image": None,
            "created_at": datetime.now().isoformat()
        },
    ]
    
    return mock_leads[:count]


@app.post("/api/capture/find-leads", response_model=FindLeadsResponse)
async def find_leads(request: FindLeadsRequest):
    """Find leads based on LinkedIn URL and AI criteria"""
    leads = []
    errors = []
    
    print("=" * 60)
    print("[API] ===== FIND LEADS REQUEST ======")
    print(f"[API] LinkedIn URL: {request.linkedin_url}")
    print(f"[API] AI Criteria: {request.ai_criteria}")
    print("=" * 60)
    
    # Validate that the URL is a LinkedIn search results URL (not a profile URL)
    if not request.linkedin_url or "/search/results/people" not in request.linkedin_url:
        error_msg = f"Invalid LinkedIn URL. Please provide a LinkedIn search results URL like: https://www.linkedin.com/search/results/people/?keywords=..."
        print(f"[API] ✗ {error_msg}")
        print(f"[API] Received URL: {request.linkedin_url}")
        return FindLeadsResponse(
            leads=[],
            total=0,
            requires_login=False,
            login_url=None,
            errors=[error_msg] if error_msg else None
        )
    
    try:
        # Use Selenium-based LinkedIn scraper
        print("[API] Using Selenium-based LinkedIn scraper...")
        
        # Get Firefox profile path from environment variable (optional)
        firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH')
        if firefox_profile_path:
            print(f"[API] Using Firefox profile: {firefox_profile_path}")
        
        # Run scraper in async executor (Selenium is blocking)
        from linkedin_scraper import scrape_linkedin_search_async
        
        try:
            leads = await scrape_linkedin_search_async(
                search_url=request.linkedin_url,
                firefox_profile_path=firefox_profile_path,
                max_results=50,
                max_pages=1,
                headless=False  # Set to True for headless mode
            )
            
            if leads:
                print(f"[API] ✓ Found {len(leads)} leads via Selenium scraper")
            else:
                print("[API] ⚠️ No leads found from scraper")
                errors.append("No leads found. Make sure you're logged into LinkedIn in your Firefox profile, or provide a valid Firefox profile path via FIREFOX_PROFILE_PATH environment variable.")
        except Exception as scrape_error:
            error_msg = str(scrape_error)
            print(f"[API] ✗ Scraper error: {error_msg}")
            import traceback
            traceback.print_exc()
            errors.append(f"Scraper error: {error_msg}")
            leads = []
        
        # Convert to Lead models
        lead_models = []
        for lead in leads:
            try:
                lead_models.append(Lead(**lead))
            except Exception as e:
                print(f"[API] Error converting lead: {e}, Lead data: {lead}")
                continue
        
        print(f"[API] Returning {len(lead_models)} leads")
        print("=" * 60)
        
        return FindLeadsResponse(
            leads=lead_models,
            total=len(lead_models),
            requires_login=False,
            login_url=None,
            errors=errors if errors else None
        )
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error finding leads: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Return empty results on error instead of mock data
        print("[API] Returning empty results due to error.")
        return FindLeadsResponse(
            leads=[],
            total=0,
            requires_login=False,
            login_url=None,
            errors=[error_msg] if error_msg else None
        )


@app.post("/api/capture/save-to-library", response_model=SaveResponse)
async def save_to_library(request: SaveToLibraryRequest):
    """Save selected leads to library"""
    try:
        # TODO: Implement actual database storage
        # For now, just return success
        
        return SaveResponse(
            success=True,
            message=f"Successfully saved {len(request.selected_lead_ids)} leads to library"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to library: {str(e)}")


@app.post("/api/capture/save-run", response_model=SaveResponse)
async def save_run(request: SaveToLibraryRequest):
    """Save a capture run"""
    try:
        # TODO: Implement actual database storage
        # For now, just return success
        
        return SaveResponse(
            success=True,
            message=f"Successfully saved run '{request.run_label}' with {len(request.selected_lead_ids)} leads"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving run: {str(e)}")


@app.post("/api/capture/export", response_model=ExportResponse)
async def export_leads(request: ExportRequest):
    """Export selected leads"""
    try:
        # TODO: Implement actual export functionality (CSV, Excel, etc.)
        # For now, just return success
        
        return ExportResponse(
            success=True,
            message=f"Successfully exported {len(request.selected_lead_ids)} leads",
            download_url=None  # TODO: Generate actual download URL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting leads: {str(e)}")


@app.post("/api/capture/extract-names", response_model=ExtractNamesResponse)
async def extract_names(request: ExtractNamesRequest):
    """
    Extract names from LinkedIn search results, grouped by page.
    Returns all names from each page of search results.
    AI criteria is optional - if not provided, returns all names from all pages.
    """
    names = []
    names_by_page_data = []
    leads = []
    errors = []
    is_filtered = False
    
    print("=" * 60)
    print("[API] ===== EXTRACT NAMES REQUEST ======")
    print(f"[API] LinkedIn URL: {request.linkedin_url}")
    print(f"[API] AI Criteria: {request.ai_criteria or 'None (names only mode)'}")
    print(f"[API] Max results: {request.max_results}, Max pages: {request.max_pages}")
    print("=" * 60)
    
    # Validate that the URL is a LinkedIn search results URL
    if not request.linkedin_url or "/search/results/people" not in request.linkedin_url:
        error_msg = f"Invalid LinkedIn URL. Please provide a LinkedIn search results URL like: https://www.linkedin.com/search/results/people/?keywords=..."
        print(f"[API] ✗ {error_msg}")
        return ExtractNamesResponse(
            success=False,
            names=[],
            leads=[],
            total=0,
            filtered=False,
            errors=[error_msg]
        )
    
    try:
        # Get Firefox profile path from environment variable (optional)
        firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH')
        if firefox_profile_path:
            print(f"[API] Using Firefox profile: {firefox_profile_path}")
        
        # Skip AI filtering for now - just extract names
        # If AI criteria is provided in the future, use extract_and_filter_names
        if False and request.ai_criteria and request.ai_criteria.strip():
            print("[API] Using extract-and-filter mode (extract all, then filter with AI)...")
            from linkedin_scraper import extract_and_filter_names_async
            
            try:
                filtered_profiles = await extract_and_filter_names_async(
                    search_url=request.linkedin_url,
                    ai_criteria=request.ai_criteria.strip(),
                    firefox_profile_path=firefox_profile_path,
                    max_results=request.max_results or 50,
                    max_pages=request.max_pages or 1,
                    headless=False  # Set to True for headless mode
                )
                
                # Convert to Lead models
                for profile in filtered_profiles:
                    try:
                        leads.append(Lead(**profile))
                    except Exception as e:
                        print(f"[API] Error converting profile to Lead: {e}")
                        continue
                
                if leads:
                    print(f"[API] ✓ Extracted and filtered to {len(leads)} matching profiles")
                    is_filtered = True
                else:
                    print("[API] ⚠️ No matching profiles found after filtering")
                    errors.append("No profiles matched the AI criteria. Try adjusting your criteria or extracting without filtering first.")
            except Exception as extract_error:
                error_msg = str(extract_error)
                print(f"[API] ✗ Extraction/filtering error: {error_msg}")
                import traceback
                traceback.print_exc()
                errors.append(f"Extraction/filtering error: {error_msg}")
                leads = []
        else:
            # Fast mode: names only
            print("[API] Using fast name extraction (names only mode)...")
            from linkedin_scraper import extract_names_only_async
            
            try:
                result = await extract_names_only_async(
                    search_url=request.linkedin_url,
                    firefox_profile_path=firefox_profile_path,
                    max_results=request.max_results or 50,
                    max_pages=request.max_pages or 1,
                    headless=False,  # Set to True for headless mode
                    return_by_page=True  # Get names grouped by page
                )
                
                # Handle both dict (with by_page) and list (legacy list responses
                if isinstance(result, dict):
                    names = result.get('names', [])
                    names_by_page_data = result.get('by_page', [])
                else:
                    # Legacy: just a list of names
                    names = result if isinstance(result, list) else []
                    names_by_page_data = []
                
                if names:
                    print(f"[API] ✓ Extracted {len(names)} names from {len(names_by_page_data)} pages")
                else:
                    print("[API] ⚠️ No names found")
                    errors.append("No names found. Make sure you're logged into LinkedIn in your Firefox profile, or provide a valid Firefox profile path via FIREFOX_PROFILE_PATH environment variable.")
            except Exception as extract_error:
                error_msg = str(extract_error)
                print(f"[API] ✗ Extraction error: {error_msg}")
                import traceback
                traceback.print_exc()
                errors.append(f"Extraction error: {error_msg}")
                names = []
                names_by_page_data = []
        
        total = len(leads) if leads else len(names)
        print(f"[API] Returning {total} results")
        print("=" * 60)
        
        # Convert names_by_page_data to PageNames models
        names_by_page = None
        if names_by_page_data:
            names_by_page = [PageNames(page=d['page'], names=d['names'], count=d['count']) for d in names_by_page_data]
        
        return ExtractNamesResponse(
            success=total > 0,
            names=names if names else None,
            names_by_page=names_by_page,
            leads=leads if leads else None,
            total=total,
            filtered=is_filtered,
            errors=errors if errors else None
        )
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error extracting names: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return ExtractNamesResponse(
            success=False,
            names=[],
            leads=[],
            total=0,
            filtered=False,
            errors=[error_msg]
        )


@app.post("/api/capture/extract-links", response_model=ExtractLinksResponse)
async def extract_links(request: ExtractLinksRequest):
    """
    Extract profile links/URLs from LinkedIn search results.
    This is more reliable than extracting names since links are always present in the HTML.
    """
    links = []
    links_by_page_data = []
    errors = []
    
    print("=" * 60)
    print("[API] ===== EXTRACT PROFILE LINKS REQUEST ======")
    print(f"[API] LinkedIn URL: {request.linkedin_url}")
    print(f"[API] Max results: {request.max_results}, Max pages: {request.max_pages}")
    print("=" * 60)
    
    # Validate that the URL is a LinkedIn search results URL
    if not request.linkedin_url or "/search/results/people" not in request.linkedin_url:
        error_msg = f"Invalid LinkedIn URL. Please provide a LinkedIn search results URL like: https://www.linkedin.com/search/results/people/?keywords=..."
        print(f"[API] ✗ {error_msg}")
        return ExtractLinksResponse(
            success=False,
            links=[],
            links_by_page=[],
            total=0,
            errors=[error_msg]
        )
    
    try:
        # Get Firefox profile path from environment variable (optional)
        firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH')
        if firefox_profile_path:
            print(f"[API] Using Firefox profile: {firefox_profile_path}")
        
        print("[API] Extracting profile links...")
        from linkedin_scraper import extract_profile_links_async
        
        try:
            result = await extract_profile_links_async(
                search_url=request.linkedin_url,
                firefox_profile_path=firefox_profile_path,
                max_results=request.max_results or 50,
                max_pages=request.max_pages or 1,
                headless=False,  # Set to True for headless mode
                return_by_page=True  # Get links grouped by page
            )
            
            # Handle both dict (with by_page) and list (legacy list responses)
            if isinstance(result, dict):
                links = result.get('links', [])
                links_by_page_data = result.get('by_page', [])
            else:
                # Legacy: just a list of links
                links = result if isinstance(result, list) else []
                links_by_page_data = []
            
            # Convert to PageLinks models
            links_by_page = []
            for page_data in links_by_page_data:
                if isinstance(page_data, dict):
                    links_by_page.append(PageLinks(
                        page=page_data.get('page', 0),
                        links=page_data.get('links', []),
                        count=page_data.get('count', 0)
                    ))
            
            total = len(links)
            
            if total > 0:
                print(f"[API] ✓ Successfully extracted {total} profile links")
            else:
                print("[API] ⚠️ No profile links were extracted")
                errors.append("No profile links were extracted. Check your LinkedIn URL and Firefox profile.")
            
        except Exception as extract_error:
            error_msg = str(extract_error)
            print(f"[API] ✗ Extraction error: {error_msg}")
            import traceback
            traceback.print_exc()
            errors.append(f"Extraction error: {error_msg}")
            links = []
            links_by_page = []
        
        return ExtractLinksResponse(
            success=len(links) > 0,
            links=links if links else None,
            links_by_page=links_by_page if links_by_page else None,
            total=len(links),
            errors=errors if errors else None
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error extracting links: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return ExtractLinksResponse(
            success=False,
            links=[],
            links_by_page=[],
            total=0,
            errors=[error_msg]
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

