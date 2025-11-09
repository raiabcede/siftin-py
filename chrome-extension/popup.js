const API_BASE_URL = 'http://localhost:8000';

async function checkStatus() {
  const statusEl = document.getElementById('status');
  const statusText = document.getElementById('status-text');
  const statusIcon = statusEl.querySelector('.status-icon');
  const userInfo = document.getElementById('user-info');
  
  statusEl.className = 'status checking';
  statusIcon.className = 'status-icon checking';
  statusText.textContent = 'Checking...';
  userInfo.style.display = 'none';
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/linkedin-login-status`);
    const result = await response.json();
    
    if (result.logged_in === true) {
      statusEl.className = 'status logged-in';
      statusIcon.className = 'status-icon logged-in';
      statusText.textContent = 'Logged In';
      
      if (result.user_name) {
        userInfo.textContent = `Logged in as: ${result.user_name}`;
        userInfo.style.display = 'block';
      }
    } else {
      statusEl.className = 'status not-logged-in';
      statusIcon.className = 'status-icon not-logged-in';
      statusText.textContent = 'Not Logged In';
    }
  } catch (error) {
    statusEl.className = 'status not-logged-in';
    statusIcon.className = 'status-icon not-logged-in';
    statusText.textContent = 'Check Failed';
    console.error('Error checking status:', error);
  }
}

document.getElementById('check-btn').addEventListener('click', checkStatus);

// Check on load
checkStatus();

