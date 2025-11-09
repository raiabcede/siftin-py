// Content script to detect LinkedIn login status
(function() {
  'use strict';
  
  // Check if user is logged in by looking for login indicators
  function checkLoginStatus() {
    // Check for logged-in indicators
    const loggedInIndicators = [
      document.querySelector('[data-control-name="nav.settings"]'),
      document.querySelector('[data-control-name="nav.messaging"]'),
      document.querySelector('.global-nav__me'),
      document.querySelector('[data-test-id="nav-settings"]')
    ];
    
    const isLoggedIn = loggedInIndicators.some(el => el !== null);
    
    // Get user name if available
    let userName = null;
    const profileLink = document.querySelector('.global-nav__me-photo, [data-control-name="nav.settings"]');
    if (profileLink) {
      const nameEl = profileLink.closest('div')?.querySelector('span');
      if (nameEl) {
        userName = nameEl.textContent.trim();
      }
    }
    
    // Send message to background script
    chrome.runtime.sendMessage({
      type: 'LINKEDIN_STATUS',
      loggedIn: isLoggedIn,
      userName: userName,
      url: window.location.href
    });
  }
  
  // Check on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkLoginStatus);
  } else {
    checkLoginStatus();
  }
  
  // Check when navigating (SPA)
  let lastUrl = location.href;
  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      setTimeout(checkLoginStatus, 1000);
    }
  }).observe(document, { subtree: true, childList: true });
})();

