// NullForge Chrome Extension - Background Service Worker
// State of the Art AI-powered code synthesis

const API_ENDPOINT = 'http://localhost:8000';

// Context menu setup
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'nullforge-synthesize',
    title: 'Synthesize with NullForge',
    contexts: ['selection']
  });
  
  chrome.contextMenus.create({
    id: 'nullforge-explain',
    title: 'Explain Code with NullForge',
    contexts: ['selection']
  });
  
  chrome.contextMenus.create({
    id: 'nullforge-optimize',
    title: 'Optimize with NullForge',
    contexts: ['selection']
  });
  
  chrome.contextMenus.create({
    id: 'nullforge-audit',
    title: 'Security Audit with NullForge',
    contexts: ['selection']
  });
  
  console.log('NullForge extension installed');
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const selectedText = info.selectionText;
  
  if (!selectedText) return;
  
  let prompt = '';
  
  switch (info.menuItemId) {
    case 'nullforge-synthesize':
      prompt = `Build: ${selectedText}`;
      break;
    case 'nullforge-explain':
      prompt = `Explain this code in detail:\n\n${selectedText}`;
      break;
    case 'nullforge-optimize':
      prompt = `Optimize this code for performance and readability:\n\n${selectedText}`;
      break;
    case 'nullforge-audit':
      prompt = `Security audit this code and identify vulnerabilities:\n\n${selectedText}`;
      break;
  }
  
  // Send to API
  try {
    const response = await synthesize(prompt);
    
    // Notify user
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'NullForge',
      message: 'Code synthesis complete! Click to view.'
    });
    
    // Store result for popup
    await chrome.storage.local.set({
      lastResult: response,
      lastPrompt: prompt,
      timestamp: Date.now()
    });
    
  } catch (error) {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'NullForge Error',
      message: error.message
    });
  }
});

// Handle keyboard shortcuts
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'synthesize') {
    // Get selected text from active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: () => window.getSelection().toString()
    }, async (results) => {
      if (results && results[0] && results[0].result) {
        const selectedText = results[0].result;
        const response = await synthesize(`Build: ${selectedText}`);
        
        // Store and notify
        await chrome.storage.local.set({
          lastResult: response,
          lastPrompt: selectedText,
          timestamp: Date.now()
        });
        
        chrome.action.openPopup();
      }
    });
  }
});

// API communication
async function synthesize(prompt, provider = 'venice') {
  const settings = await chrome.storage.sync.get(['apiEndpoint', 'apiKey']);
  const endpoint = settings.apiEndpoint || API_ENDPOINT;
  
  const response = await fetch(`${endpoint}/v1/synthesize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(settings.apiKey && { 'Authorization': `Bearer ${settings.apiKey}` })
    },
    body: JSON.stringify({
      prompt,
      provider,
      config: {
        enable_shell: true,
        enable_files: true,
        enable_web_search: false
      }
    })
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return await response.json();
}

// WebSocket connection for real-time updates
let ws = null;
let wsReconnectInterval = null;

function connectWebSocket() {
  chrome.storage.sync.get(['apiEndpoint'], (settings) => {
    const endpoint = settings.apiEndpoint || API_ENDPOINT;
    const wsUrl = endpoint.replace('http', 'ws') + '/v1/ws/extension';
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      chrome.runtime.sendMessage({ type: 'ws-connected' });
      
      if (wsReconnectInterval) {
        clearInterval(wsReconnectInterval);
        wsReconnectInterval = null;
      }
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      chrome.runtime.sendMessage({ type: 'ws-message', data });
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      chrome.runtime.sendMessage({ type: 'ws-disconnected' });
      
      // Reconnect after 5 seconds
      if (!wsReconnectInterval) {
        wsReconnectInterval = setInterval(connectWebSocket, 5000);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  });
}

// Initial connection
connectWebSocket();

// Handle messages from popup/content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'synthesize') {
    synthesize(message.prompt, message.provider)
      .then(response => sendResponse({ success: true, data: response }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (message.type === 'check-connection') {
    fetch(`${API_ENDPOINT}/health`)
      .then(response => response.json())
      .then(data => sendResponse({ connected: true, data }))
      .catch(() => sendResponse({ connected: false }));
    return true;
  }
  
  if (message.type === 'ws-send') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message.data));
      sendResponse({ success: true });
    } else {
      sendResponse({ success: false, error: 'WebSocket not connected' });
    }
    return true;
  }
});

// Badge updates
function updateBadge(status) {
  if (status === 'processing') {
    chrome.action.setBadgeText({ text: '...' });
    chrome.action.setBadgeBackgroundColor({ color: '#667eea' });
  } else if (status === 'complete') {
    chrome.action.setBadgeText({ text: '✓' });
    chrome.action.setBadgeBackgroundColor({ color: '#22c55e' });
    setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
  } else if (status === 'error') {
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
    setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

console.log('NullForge background service worker initialized');
