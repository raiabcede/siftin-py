// Background service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'LINKEDIN_STATUS') {
    // Store status in chrome.storage
    chrome.storage.local.set({
      linkedinStatus: {
        loggedIn: message.loggedIn,
        userName: message.userName,
        url: message.url,
        timestamp: Date.now()
      }
    });
  }
});

// Listen for tab updates on LinkedIn
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.includes('linkedin.com')) {
    // Status will be updated by content script
  }
});

