// LinkedIn Status Checker - Shared across all pages
// This file handles checking and displaying LinkedIn login status in the navbar

// Get API base URL (use page's definition if available, otherwise default)
function getApiBaseUrl() {
	return (typeof API_BASE_URL !== 'undefined' && API_BASE_URL) 
		? API_BASE_URL 
		: 'http://localhost:8000';
}

// Helper function for API calls (use page's if available, otherwise define our own)
async function linkedinStatusApiCall(endpoint, method = 'GET', data = null, timeout = 30000) {
	// Use page's apiCall if available
	if (typeof apiCall !== 'undefined') {
		return await apiCall(endpoint, method, data, timeout);
	}
	
	// Otherwise, use our own implementation
	try {
		const apiBaseUrl = getApiBaseUrl();
		const options = {
			method,
			headers: {
				'Content-Type': 'application/json',
			}
		};
		
		if (data) {
			options.body = JSON.stringify(data);
		}
		
		console.log(`[LinkedIn Status API] Calling ${method} ${apiBaseUrl}${endpoint}`, data);
		
		// Create a timeout promise
		const timeoutPromise = new Promise((_, reject) => {
			setTimeout(() => {
				reject(new Error(`Request timeout after ${timeout / 1000} seconds.`));
			}, timeout);
		});
		
		// Race between fetch and timeout
		const response = await Promise.race([
			fetch(`${apiBaseUrl}${endpoint}`, options),
			timeoutPromise
		]);
		
		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
			console.error(`[LinkedIn Status API] Error response:`, error);
			throw new Error(error.detail || `HTTP error! status: ${response.status}`);
		}
		
		const result = await response.json();
		console.log(`[LinkedIn Status API] Success:`, result);
		return result;
	} catch (error) {
		console.error('[LinkedIn Status API] Request failed:', error);
		
		// Check if it's a network error (API not running)
		if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
			throw new Error('Cannot connect to API. Make sure the FastAPI server is running on http://localhost:8000');
		}
		
		throw error;
	}
}

// Bookmarklet status - no polling needed, status persists until user logs out
let lastValidStatus = null;
// Declare linkedinLoginStatus globally so it can be accessed by page scripts
if (typeof linkedinLoginStatus === 'undefined') {
	var linkedinLoginStatus = null;
}

// Helper function to capitalize first letter of each word
function capitalizeWords(str) {
	if (!str) return str;
	return str.split(' ').map(word => {
		if (word.length === 0) return word;
		return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
	}).join(' ');
}

// Update UI with bookmarklet status (badge on Chrome icon only)
function updateBookmarkletStatusUI(status) {
	const extensionBadge = document.getElementById('extension-installer-badge');
	const extensionInstaller = document.getElementById('extension-installer');
	
	if (status.loggedIn) {
		// Update extension badge - green for logged in
		if (extensionBadge) {
			extensionBadge.className = 'absolute inline-flex items-center justify-center  text-white text-[11px] font-medium  bg-success p-[5px] rounded-full -top-[-5px] -right-[0px]';
			extensionBadge.classList.remove('hidden');
		}
		// Update extension installer title with user name
		if (extensionInstaller) {
			const capitalizedUserName = status.userName ? capitalizeWords(status.userName) : null;
			extensionInstaller.title = capitalizedUserName 
				? `LinkedIn: ${capitalizedUserName} - Drag to Install Extension` 
				: 'LinkedIn: Logged In - Drag to Install Extension';
		}
	} else {
		// Update extension badge - red for logged out
		if (extensionBadge) {
			extensionBadge.className = 'absolute inline-flex items-center justify-center  text-white text-[11px] font-medium  bg-danger p-[5px] rounded-full -top-[-5px] -right-[0px]';
			extensionBadge.classList.remove('hidden');
		}
		// Update extension installer title
		if (extensionInstaller) {
			extensionInstaller.title = 'LinkedIn: Not Logged In - Drag to Install Extension';
		}
	}
}

// Sync status to API (called from main page, not blocked by CSP)
async function syncStatusToAPI(loggedIn, userName) {
	try {
		await linkedinStatusApiCall('/api/bookmarklet-status', 'POST', {
			logged_in: loggedIn,
			user_name: userName
		}, 5000);
		console.log('Status synced to API successfully');
	} catch (error) {
		console.log('Failed to sync status to API:', error);
		// Non-critical error - localStorage still works
	}
}

// Check for bookmarklet status from localStorage first, then sync to API
async function checkBookmarkletStatus() {
	// First, check localStorage (set by bookmarklet on LinkedIn)
	try {
		const storedStatus = localStorage.getItem('siftin_linkedin_status');
		if (storedStatus) {
			const statusData = JSON.parse(storedStatus);
			// Check if data is recent (within last 24 hours)
			const age = Date.now() - (statusData.timestamp || 0);
			const maxAge = 24 * 60 * 60 * 1000; // 24 hours
			
			if (age < maxAge && statusData.logged_in !== null) {
				// Only use localStorage if it says logged_in is true
				// If logged_in is false, we should verify with API
				if (statusData.logged_in === true) {
					linkedinLoginStatus = statusData.logged_in;
					lastValidStatus = {
						logged_in: statusData.logged_in,
						user_name: statusData.user_name,
						status: 'success'
					};
					updateBookmarkletStatusUI({
						loggedIn: statusData.logged_in,
						userName: statusData.user_name
					});
					
					// Sync to API in the background (from main page, not blocked by CSP)
					syncStatusToAPI(statusData.logged_in, statusData.user_name).catch(err => {
						console.log('Background API sync failed (non-critical):', err);
					});
					
					return true;
				} else {
					// localStorage says logged out - clear it and check API
					localStorage.removeItem('siftin_linkedin_status');
				}
			} else {
				// Data is too old, remove it
				localStorage.removeItem('siftin_linkedin_status');
			}
		}
	} catch (e) {
		console.log('Error reading from localStorage:', e);
		// On error, clear potentially corrupted localStorage
		try {
			localStorage.removeItem('siftin_linkedin_status');
		} catch (err) {
			console.log('Error clearing localStorage:', err);
		}
	}
	
	// Fallback: Check API
	try {
		const result = await linkedinStatusApiCall('/api/bookmarklet-status', 'GET', null, 5000);
		if (result && result.status === 'success' && result.logged_in !== null) {
			linkedinLoginStatus = result.logged_in;
			lastValidStatus = result;
			updateBookmarkletStatusUI({
				loggedIn: result.logged_in,
				userName: result.user_name
			});
			return true;
		} else if (result && (result.status === 'expired' || result.status === 'not_set')) {
			// Status expired (user logged out) or not set
			linkedinLoginStatus = false;
			lastValidStatus = null;
			updateBookmarkletStatusUI({
				loggedIn: false,
				userName: null
			});
			// Clear localStorage if status is expired/not set
			try {
				localStorage.removeItem('siftin_linkedin_status');
			} catch (e) {
				console.log('Error clearing localStorage:', e);
			}
			return false;
		} else {
			// No result or unexpected response - assume not logged in
			linkedinLoginStatus = false;
			lastValidStatus = null;
			updateBookmarkletStatusUI({
				loggedIn: false,
				userName: null
			});
			return false;
		}
	} catch (e) {
		console.log('Error reading bookmarklet status from API:', e);
		// On error, assume not logged in and clear any stale localStorage
		linkedinLoginStatus = false;
		lastValidStatus = null;
		try {
			localStorage.removeItem('siftin_linkedin_status');
		} catch (err) {
			console.log('Error clearing localStorage:', err);
		}
		updateBookmarkletStatusUI({
			loggedIn: false,
			userName: null
		});
		return false;
	}
}

// Setup Chrome Extension Installer (Temporarily Disabled)
function setupExtensionInstaller() {
	const installer = document.getElementById('extension-installer');
	if (!installer) return;
	// Temporarily disabled - do nothing
	return;
	
	// Create inline bookmarklet code (no external script loading needed)
	// This avoids CORS issues and works immediately
	// Improved LinkedIn login detection with multiple selectors
	// Accurate LinkedIn detection - checks for sign-in button first, then requires multiple logged-in indicators
	// Enhanced username extraction with multiple methods
	// Prioritizes h3.profile-card-name as the primary selector for username
	const bookmarkletCode = `javascript:(function(){var d=document;var e=d.getElementById('siftin-status-popup');if(e)e.remove();if(!d.location.hostname.includes('linkedin.com')){alert('Please navigate to LinkedIn first');d.location.href='https://www.linkedin.com';return;}var p=d.createElement('div');p.id='siftin-status-popup';p.style.cssText='position:fixed!important;top:20px!important;right:20px!important;background:white!important;border:2px solid #0077b5!important;border-radius:8px!important;padding:20px!important;box-shadow:0 4px 12px rgba(0,0,0,0.15)!important;z-index:999999!important;max-width:300px!important;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif!important;';var loggedIn=false;var name='';var bodyText=d.body.textContent||'';var hasSignIn=!!(/Sign\s+in/i.test(bodyText));var hasJoinNow=!!(/Join\s+now/i.test(bodyText));if(hasSignIn||hasJoinNow){loggedIn=false;}else{var nav=d.querySelector('nav');var hasNav=!!nav;if(!hasNav){loggedIn=false;}else{var hasMessaging=!!d.querySelector('a[href*="/messaging/"]');var hasNotifications=!!d.querySelector('a[href*="/notifications/"]');var hasJobs=!!d.querySelector('a[href*="/jobs/"]');var hasMyNetwork=!!d.querySelector('a[href*="/mynetwork/"]');var hasStartPost=!!(d.querySelector('[placeholder*="Start a post"],textarea[placeholder*="Start a post"]')||bodyText.includes('Start a post'));var hasProfileCard=!!d.querySelector('.profile-card,.pv-profile-card');var hasFeed=!!d.querySelector('.feed-container,.scaffold-finite-scroll__content');var hasMeMenu=!!(bodyText.includes('Me')&&!hasSignIn);var indicators=0;if(hasMessaging)indicators++;if(hasNotifications)indicators++;if(hasJobs)indicators++;if(hasMyNetwork)indicators++;if(hasStartPost)indicators++;if(hasProfileCard)indicators++;if(hasFeed)indicators++;if(hasMeMenu)indicators++;loggedIn=indicators>=3;}}if(loggedIn){function isValidName(txt){if(!txt||txt.length<2||txt.length>50)return false;var invalidWords=['Me','View','profile','Settings','Sign','LinkedIn','Mentions','Notifications','Messages','Jobs','My Network','Home','Search','Work','Learning','People','Posts','Articles','Companies','Groups','Events','Newsletters','Hashtags','Follow','Following','Followers','Connections','Invitations','Try Premium','Upgrade','Help','Privacy','Terms','About','Accessibility','Business Services','Talent Solutions','Marketing Solutions','Sales Solutions','Small Business','Community Guidelines','Cookie Policy','Copyright Policy','Brand Policy','Guest Controls','Language'];for(var w=0;w<invalidWords.length;w++){if(txt===invalidWords[w]||txt.includes(invalidWords[w]))return false;}return true;}var nameSelectors=['h3.profile-card-name','h1.text-heading-xlarge','h1.pv-text-details__left-panel h1','h1[data-anonymize="person-name"]','.profile-card h1','.pv-profile-card h1','[data-control-name="nav.settings"]'];for(var i=0;i<nameSelectors.length;i++){var el=d.querySelector(nameSelectors[i]);if(el){var txt=el.textContent.trim();if(isValidName(txt)){name=txt;break;}var aria=el.getAttribute('aria-label');if(aria&&aria.includes('View profile of')){txt=aria.replace('View profile of','').trim();if(isValidName(txt)){name=txt;break;}}}}if(!name){var meButton=d.querySelector('button[aria-label*="Me menu"],button[aria-label*="View profile"],a[aria-label*="Me"]');if(meButton){var aria=meButton.getAttribute('aria-label');if(aria&&aria.includes('View profile of')){var txt=aria.replace('View profile of','').trim();if(isValidName(txt)){name=txt;}}}if(!name){var profileLinks=d.querySelectorAll('a[href*="/me/"],a[href*="/in/"]');for(var j=0;j<profileLinks.length&&j<5;j++){var link=profileLinks[j];var href=link.getAttribute('href');if(href&&(href.includes('/me/')||href.includes('/in/'))){var txt=link.textContent.trim();if(isValidName(txt)){name=txt;break;}var parent=link.closest('.profile-card,.pv-profile-card,.global-nav__me-photo-container');if(parent){var spans=parent.querySelectorAll('span,h1,h2,h3');for(var k=0;k<spans.length;k++){txt=spans[k].textContent.trim();if(isValidName(txt)){name=txt;break;}}if(name)break;}}}}}}var statusData={logged_in:loggedIn,user_name:name,timestamp:Date.now()};try{localStorage.setItem('siftin_linkedin_status',JSON.stringify(statusData));console.log('Status saved to localStorage:',statusData);}catch(err){console.log('Error saving to localStorage:',err);}var s=loggedIn?'Logged In':'Not Logged In';var c=loggedIn?'#388e3c':'#d32f2f';var b=loggedIn?'#e8f5e9':'#ffebee';p.innerHTML='<div style="text-align:center"><h3 style="margin:0 0 10px 0;color:#0077b5">LinkedIn Status</h3><div style="padding:10px;border-radius:4px;background:'+b+'"><div style="display:inline-block;width:12px;height:12px;border-radius:50%;background:'+c+';margin-right:8px"></div><span style="color:'+c+';font-weight:bold">'+s+'</span>'+(name?'<div style="margin-top:5px;font-size:12px;color:#666">as '+name+'</div>':'')+'</div><div style="margin-top:8px;font-size:11px;color:#666">Status saved. Return to New Capture page to sync.</div><button id="siftin-close-btn" style="margin-top:10px;padding:8px 16px;background:#0077b5;color:white;border:none;border-radius:4px;cursor:pointer">Close</button></div>';d.body.appendChild(p);var closeBtn=d.getElementById('siftin-close-btn');if(closeBtn){closeBtn.onclick=function(){p.remove();};}})();`;
	
	// Set href for dragging
	installer.href = bookmarkletCode;
	
	// Handle drag start
	installer.addEventListener('dragstart', function(e) {
		// Temporarily add text content for bookmark name (browsers use link text as bookmark name)
		const originalHTML = installer.innerHTML;
		installer.textContent = 'Siftin Ext';
		
		// Set bookmark code
		e.dataTransfer.setData('text/plain', bookmarkletCode);
		e.dataTransfer.setData('text/uri-list', bookmarkletCode);
		e.dataTransfer.effectAllowed = 'copy';
		
		// Restore original HTML after a short delay (allows drag to complete)
		setTimeout(() => {
			installer.innerHTML = originalHTML;
		}, 0);
		
		// Visual feedback
		installer.style.opacity = '0.5';
	});
	
	installer.addEventListener('dragend', function() {
		installer.style.opacity = '1';
	});
	
	// Handle click - show instructions
	installer.addEventListener('click', function(e) {
		e.preventDefault();
		const apiBaseUrl = getApiBaseUrl();
		alert('To install:\n\n1. Drag this button to your browser\'s bookmarks bar\n2. Go to LinkedIn (linkedin.com)\n3. Click the bookmark to check your login status\n\nOr visit: ' + apiBaseUrl + '/chrome-extension/install.html');
	});
}

// Initialize LinkedIn status checking on page load
function initLinkedInStatus() {
	// Setup extension installer
	setupExtensionInstaller();
	
	// Check for bookmarklet status on page load
	checkBookmarkletStatus();
	
	// Check status when page becomes visible (user switches back to tab)
	document.addEventListener('visibilitychange', () => {
		if (!document.hidden) {
			// Page is now visible - check status once
			checkBookmarkletStatus();
		}
	});
}

// Auto-initialize when DOM is ready
// Use a small delay to ensure page scripts (like API_BASE_URL) have loaded
function delayedInit() {
	// Small delay to ensure page scripts have run
	setTimeout(() => {
		initLinkedInStatus();
	}, 100);
}

if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', delayedInit);
} else {
	// DOM already ready, but still delay slightly to ensure page scripts have run
	delayedInit();
}

