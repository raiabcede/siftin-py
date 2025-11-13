/**
 * Authentication helper functions
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Get the authentication token from localStorage
 */
function getAuthToken() {
    return localStorage.getItem('auth_token');
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!getAuthToken();
}

/**
 * Get auth headers for API requests
 */
function getAuthHeaders() {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}

/**
 * Enhanced API call function with authentication
 */
async function apiCall(endpoint, method = 'GET', data = null, timeout = 300000) {
    try {
        const options = {
            method,
            headers: getAuthHeaders(),
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        console.log(`[API] Calling ${method} ${API_BASE_URL}${endpoint}`, data);
        
        // Create a timeout promise
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error(`Request timeout after ${timeout / 1000} seconds.`));
            }, timeout);
        });
        
        // Race between fetch and timeout
        const response = await Promise.race([
            fetch(`${API_BASE_URL}${endpoint}`, options),
            timeoutPromise
        ]);
        
        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_email');
            window.location.href = '/login';
            throw new Error('Authentication required. Please log in.');
        }
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            console.error(`[API] Error response:`, error);
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log(`[API] Success:`, result);
        return result;
    } catch (error) {
        console.error('[API] Request failed:', error);
        
        // Check if it's a network error (API not running)
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            throw new Error('Cannot connect to API. Make sure the FastAPI server is running on http://localhost:8000');
        }
        
        throw error;
    }
}

/**
 * Logout function
 */
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_email');
    window.location.href = '/login';
}

// Make logout available globally
window.logout = logout;

/**
 * Check authentication and redirect if not authenticated
 */
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

