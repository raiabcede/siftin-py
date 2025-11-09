// Bookmarklet installer script - inline version
(function() {
  'use strict';
  
  // Remove any existing popup
  const existing = document.getElementById('siftin-status-popup');
  if (existing) existing.remove();
  
  // Check if we're on LinkedIn
  if (!window.location.hostname.includes('linkedin.com')) {
    alert('Please navigate to LinkedIn first, then click this bookmarklet.\n\nRedirecting to LinkedIn...');
    window.location.href = 'https://www.linkedin.com';
    return;
  }
  
  // Create popup to show status
  const popup = document.createElement('div');
  popup.id = 'siftin-status-popup';
  popup.style.cssText = `
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    background: white !important;
    border: 2px solid #0077b5 !important;
    border-radius: 8px !important;
    padding: 20px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    z-index: 999999 !important;
    max-width: 300px !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  `;
  
  popup.innerHTML = `
    <div style="text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #0077b5;">LinkedIn Status Checker</h3>
      <div id="siftin-status" style="padding: 10px; border-radius: 4px; margin: 10px 0;">
        <div style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #1976d2; margin-right: 8px; animation: siftin-pulse 1.5s infinite;"></div>
        <span>Checking status...</span>
      </div>
      <button id="siftin-close-btn" style="margin-top: 10px; padding: 8px 16px; background: #0077b5; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
    </div>
    <style>
      @keyframes siftin-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
    </style>
  `;
  
  document.body.appendChild(popup);
  
  // Check login status
  async function checkStatus() {
    const statusEl = document.getElementById('siftin-status');
    if (!statusEl) return;
    
    try {
      // Improved LinkedIn login detection with multiple selectors
      let isLoggedIn = false;
      let userName = '';
      
      try {
        const bodyText = document.body.textContent || '';
        
        // First check: If "Sign in" or "Join now" text exists, definitely not logged in
        const hasSignIn = /Sign\s+in/i.test(bodyText);
        const hasJoinNow = /Join\s+now/i.test(bodyText);
        
        if (hasSignIn || hasJoinNow) {
          isLoggedIn = false;
        } else {
          // Only check for logged-in indicators if no sign-in/join buttons
          const nav = document.querySelector('nav');
          const hasNav = !!nav;
          
          if (!hasNav) {
            isLoggedIn = false;
          } else {
            // Check for navigation items that only appear when logged in (with full path)
            const hasMessaging = !!document.querySelector('a[href*="/messaging/"]');
            const hasNotifications = !!document.querySelector('a[href*="/notifications/"]');
            const hasJobs = !!document.querySelector('a[href*="/jobs/"]');
            const hasMyNetwork = !!document.querySelector('a[href*="/mynetwork/"]');
            
            // Check for "Start a post" section (only visible when logged in)
            const hasStartPost = !!(
              document.querySelector('[placeholder*="Start a post"], textarea[placeholder*="Start a post"]') ||
              bodyText.includes('Start a post')
            );
            
            // Check for profile card (only visible when logged in)
            const hasProfileCard = !!document.querySelector('.profile-card, .pv-profile-card');
            
            // Check for feed content
            const hasFeed = !!document.querySelector('.feed-container, .scaffold-finite-scroll__content');
            
            // Check for "Me" menu (but not if sign-in is present)
            const hasMeMenu = !!(bodyText.includes('Me') && !hasSignIn);
            
            // Count indicators - need at least 3 to be confident (more strict)
            let indicators = 0;
            if (hasMessaging) indicators++;
            if (hasNotifications) indicators++;
            if (hasJobs) indicators++;
            if (hasMyNetwork) indicators++;
            if (hasStartPost) indicators++;
            if (hasProfileCard) indicators++;
            if (hasFeed) indicators++;
            if (hasMeMenu) indicators++;
            
            // User is logged in if has at least 3 indicators (more strict requirement)
            isLoggedIn = indicators >= 3;
          }
        }
        
        // Get user name from various possible locations
        if (isLoggedIn) {
          const allLinks = document.querySelectorAll(
            'a[href*="/me/"], a[href*="/in/"], button[aria-label*="Me"], a[aria-label*="Me"], .global-nav__me-photo, [data-control-name="nav.settings"]'
          );
          
          for (const link of allLinks) {
            const parent = link.closest('div, li, span, button, a');
            if (parent) {
              const spans = parent.querySelectorAll('span');
              for (const span of spans) {
                const txt = span.textContent.trim();
                // Valid name: not "Me", reasonable length, doesn't contain common UI text
                if (txt && txt !== 'Me' && txt.length > 2 && txt.length < 50 && 
                    !txt.includes('View') && !txt.includes('profile') && 
                    !txt.includes('Settings') && !txt.includes('Sign')) {
                  userName = txt;
                  break;
                }
              }
              if (userName) break;
            }
          }
        }
      } catch (e) {
        console.log('Error detecting login status:', e);
      }
      
      // Try to send to API (but don't fail if API is not available)
      let apiResult = null;
      try {
        const response = await fetch('http://localhost:8000/api/linkedin-login-status', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          mode: 'cors'
        });
        if (response.ok) {
          apiResult = await response.json();
        }
      } catch (apiError) {
        console.log('API check failed (server may not be running):', apiError);
      }
      
      // Determine final status
      const loggedIn = apiResult?.logged_in === true || isLoggedIn;
      const finalUserName = apiResult?.user_name || userName;
      
      if (loggedIn) {
        statusEl.innerHTML = `
          <div style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #388e3c; margin-right: 8px;"></div>
          <span style="color: #388e3c; font-weight: bold;">Logged In</span>
          ${finalUserName ? `<div style="margin-top: 5px; font-size: 12px; color: #666;">as ${finalUserName}</div>` : ''}
        `;
        statusEl.style.background = '#e8f5e9';
      } else {
        statusEl.innerHTML = `
          <div style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #d32f2f; margin-right: 8px;"></div>
          <span style="color: #d32f2f; font-weight: bold;">Not Logged In</span>
          <div style="margin-top: 5px; font-size: 12px; color: #666;">Please log in to LinkedIn</div>
        `;
        statusEl.style.background = '#ffebee';
      }
    } catch (error) {
      statusEl.innerHTML = `
        <div style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #d32f2f; margin-right: 8px;"></div>
        <span style="color: #d32f2f;">Check Failed</span>
        <div style="margin-top: 5px; font-size: 12px; color: #666;">Error: ${error.message || 'Unknown error'}</div>
      `;
      statusEl.style.background = '#ffebee';
      console.error('Error checking status:', error);
    }
  }
  
  // Close button - use onclick for better compatibility
  const closeBtn = document.getElementById('siftin-close-btn');
  if (closeBtn) {
    closeBtn.onclick = function() {
      popup.remove();
    };
  }
  
  // Check status
  checkStatus();
})();

