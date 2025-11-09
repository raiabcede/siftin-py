/**
 * Routes Configuration
 * Centralized configuration for all application routes
 * 
 * This file contains all route definitions for the application.
 * Update routes here to keep navigation consistent across the app.
 * 
 * Usage Examples:
 * 
 * // Get all navigation routes
 * const navRoutes = Routes.utils.getNavigationRoutes();
 * 
 * // Get a specific route by ID
 * const newCaptureRoute = Routes.utils.getRouteById('new-capture');
 * 
 * // Get a route by page name
 * const runsRoute = Routes.utils.getRouteByPage('runs');
 * 
 * // Get full URL for a route
 * const url = Routes.utils.getFullUrl('/new-capture/');
 * 
 * // Set active route
 * Routes.utils.setActiveRoute('sample page 1');
 * 
 * // Access routes directly
 * Routes.navigation.forEach(route => {
 *   console.log(route.title, route.path);
 * });
 */

const Routes = {
  // Base web root path (used for building absolute URLs)
  webRoot: '',

  // Main navigation routes (sidebar menu)
  navigation: [
    {
      id: 'new-capture',
      page: 'sample page 1',
      path: '/new-capture/',
      title: 'New Capture',
      icon: 'ti-circle-plus',
      active: false
    },
    {
      id: 'runs',
      page: 'runs',
      path: '/runs/',
      title: 'Runs',
      icon: 'ti-player-play',
      active: false
    },
    {
      id: 'results',
      page: 'results',
      path: '/index.html',
      title: 'Results',
      icon: 'ti-chart-bar',
      active: false
    },
    {
      id: 'leads',
      page: 'leads',
      path: '/index.html',
      title: 'Leads',
      icon: 'ti-users',
      active: false
    },
    {
      id: 'exports',
      page: 'exports',
      path: '/index.html',
      title: 'Exports',
      icon: 'ti-download',
      active: false
    },
    {
      id: 'integrations',
      page: 'integrations',
      path: '/index.html',
      title: 'Integrations',
      icon: 'ti-plug',
      active: false
    },
    {
      id: 'firefox-setup',
      page: 'firefox-setup',
      path: '/firefox-setup/',
      title: 'Firefox Setup',
      icon: 'ti-brand-firefox',
      active: false
    },
    {
      id: 'settings',
      page: 'settings',
      path: '/index.html',
      title: 'Settings',
      icon: 'ti-settings',
      active: false
    },
    {
      id: 'help',
      page: 'help',
      path: '/index.html',
      title: 'Help',
      icon: 'ti-help-circle',
      active: false
    }
  ],

  // Horizontal navigation routes
  horizontalNav: [
    {
      id: 'sample-page-1',
      page: 'sample page 1',
      path: '/new-capture/',
      title: 'Sample Page 1',
      icon: 'ti-brand-chrome'
    },
    {
      id: 'sample-page-2',
      page: 'sample page 2',
      path: '/index2.html',
      title: 'Sample Page 2',
      icon: 'ti-dashboard'
    }
  ],

  // Utility functions
  utils: {
    /**
     * Get route by ID
     * @param {string} id - Route ID
     * @returns {Object|null} Route object or null if not found
     */
    getRouteById(id) {
      return Routes.navigation.find(route => route.id === id) || 
             Routes.horizontalNav.find(route => route.id === id) || 
             null;
    },

    /**
     * Get route by page name
     * @param {string} pageName - Page name
     * @returns {Object|null} Route object or null if not found
     */
    getRouteByPage(pageName) {
      return Routes.navigation.find(route => route.page === pageName) || 
             Routes.horizontalNav.find(route => route.page === pageName) || 
             null;
    },

    /**
     * Get full URL for a route
     * @param {string} path - Route path
     * @returns {string} Full URL
     */
    getFullUrl(path) {
      const webRoot = Routes.webRoot || '';
      return `${webRoot}${path}`;
    },

    /**
     * Get all navigation routes
     * @returns {Array} Array of navigation routes
     */
    getNavigationRoutes() {
      return Routes.navigation;
    },

    /**
     * Get all horizontal navigation routes
     * @returns {Array} Array of horizontal navigation routes
     */
    getHorizontalNavRoutes() {
      return Routes.horizontalNav;
    },

    /**
     * Set active route by page name
     * @param {string} pageName - Page name to set as active
     */
    setActiveRoute(pageName) {
      Routes.navigation.forEach(route => {
        route.active = route.page === pageName;
      });
      Routes.horizontalNav.forEach(route => {
        route.active = route.page === pageName;
      });
    }
  }
};

// Make Routes available globally
if (typeof window !== 'undefined') {
  window.Routes = Routes;
}

// Export for use in modules (if using ES6 modules)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Routes;
}

