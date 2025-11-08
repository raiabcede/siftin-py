/**
 * Icon Cache & Preload Script
 * Preloads and caches Tabler Icons font for faster rendering
 * Caches unique icon classes without duplicates
 */

(function() {
  'use strict';

  var ICON_FONT_URL = 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/fonts/tabler-icons.woff2';
  var CACHE_KEY = 'tabler_icons_cached';

  // Extract all unique icon classes from the page (no duplicates)
  function extractUniqueIconClasses() {
    var iconClasses = new Set();
    var allElements = document.querySelectorAll('[class*="ti-"]');
    
    allElements.forEach(function(el) {
      var classes = el.className.split(/\s+/);
      classes.forEach(function(cls) {
        // Match ti-* classes but exclude base 'ti' class
        if (cls.startsWith('ti-') && cls !== 'ti') {
          iconClasses.add(cls);
        }
      });
    });
    
    return Array.from(iconClasses).sort(); // Sort for consistent caching
  }

  // Use Font Loading API to preload and cache font
  function preloadIconFont() {
    if (!document.fonts || !window.FontFace) {
      return; // Font Loading API not supported
    }

    try {
      // Check if font is already loaded
      if (document.fonts.check('1em tabler-icons')) {
        return; // Already loaded
      }

      // Load font using Font Loading API
      var iconFont = new FontFace('tabler-icons', 'url(' + ICON_FONT_URL + ')', {
        display: 'swap', // Show fallback immediately, swap when loaded
        weight: '400',
        style: 'normal'
      });

      iconFont.load().then(function(loadedFont) {
        document.fonts.add(loadedFont);
        
        // Cache successful load
        try {
          localStorage.setItem(CACHE_KEY, 'loaded');
          localStorage.setItem(CACHE_KEY + '_time', Date.now().toString());
        } catch (e) {
          // localStorage not available
        }
      }).catch(function(error) {
        console.warn('Icon font preload failed:', error);
      });
    } catch (e) {
      console.warn('Font Loading API error:', e);
    }
  }

  // Cache icon classes list in localStorage
  function cacheIconClasses() {
    try {
      var iconClasses = extractUniqueIconClasses();
      var cachedData = {
        classes: iconClasses,
        count: iconClasses.length,
        timestamp: Date.now()
      };
      
      localStorage.setItem(CACHE_KEY + '_classes', JSON.stringify(cachedData));
    } catch (e) {
      // localStorage not available or quota exceeded
    }
  }

  // Ensure icons render properly
  function ensureIconsRendered() {
    // Add CSS to ensure font-display: swap for better performance
    if (!document.getElementById('icon-cache-style')) {
      var style = document.createElement('style');
      style.id = 'icon-cache-style';
      style.textContent = '@font-face{font-family:"tabler-icons";font-display:swap;}';
      document.head.appendChild(style);
    }

    // Force reflow on icons after font loads
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function() {
        var icons = document.querySelectorAll('.ti');
        icons.forEach(function(icon) {
          // Trigger reflow to ensure proper rendering
          icon.style.fontDisplay = 'swap';
        });
      });
    }
  }

  // Initialize immediately (runs in head)
  preloadIconFont();

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      cacheIconClasses();
      ensureIconsRendered();
    });
  } else {
    cacheIconClasses();
    ensureIconsRendered();
  }

  // Also cache on page visibility change (in case icons are added dynamically)
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      cacheIconClasses();
    }
  });
})();

