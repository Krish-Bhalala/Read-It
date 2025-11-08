const API_BASE = 'http://localhost:8888/api';

// State management
let currentUser = null;

// DOM Elements
const authSection = document.getElementById('authSection');
const appSection = document.getElementById('appSection');
const authMessage = document.getElementById('authMessage');
const appMessage = document.getElementById('appMessage');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const createMessageForm = document.getElementById('createMessageForm');
const logoutBtn = document.getElementById('headerLogoutBtn');
const currentUserSpan = document.getElementById('headerUserName');
const messagesContainer = document.getElementById('messagesContainer');
const headerUser = document.getElementById('headerUser');

// Modal elements
const createPostTrigger = document.getElementById('createPostTrigger');
const createPostModal = document.getElementById('createPostModal');
const closeModal = document.getElementById('closeModal');
const cancelPost = document.getElementById('cancelPost');

// Auth tabs
const tabBtns = document.querySelectorAll('.tab-btn');
const authForms = document.querySelectorAll('.auth-form');

// Tab switching
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    authForms.forEach(form => form.classList.remove('active'));
    if (tab === 'login') {
      loginForm.classList.add('active');
    } else {
      registerForm.classList.add('active');
    }
  });
});

// Modal controls
createPostTrigger.addEventListener('click', () => {
  createPostModal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
});

closeModal.addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

cancelPost.addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

createPostModal.querySelector('.modal-overlay').addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

// Utility Functions
function showMessage(container, message, type) {
  container.innerHTML = `<div class="message-alert ${type}">${message}</div>`;
  setTimeout(() => {
    container.innerHTML = '';
  }, 5000);
}

function showAuthView() {
  authSection.classList.remove('hidden');
  appSection.classList.add('hidden');
  headerUser.classList.add('hidden');
}

function showAppView() {
  authSection.classList.add('hidden');
  appSection.classList.remove('hidden');
  headerUser.classList.remove('hidden');
}

function parseStringToJSON(str) {
  const regex = /('(.*?)')|("(.*?)")/g;
  const result = str.replace(regex, (match, g1, g2, g3, g4) => {
    if (g1) {
      return `"${g2.replace(/"/g, '\\"')}"`;
    }
    return match;
  });
  return JSON.parse(result);
}

function parseMessagesToJSON(jsonString) {
    let trimmed = jsonString.trim();
    if (trimmed.startsWith('[')) trimmed = trimmed.slice(1);
    if (trimmed.endsWith(']')) trimmed = trimmed.slice(0, -1);

    let parts = trimmed.split('}, {');
    let result = parts.map((part, index) => {
        if (index === 0) part += '}';
        else if (index === parts.length - 1) part = '{' + part;
        else part = '{' + part + '}';
        return parseStringToJSON(part);
    });

    return result;
}

// API Functions using XHR
function checkCurrentUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', `${API_BASE}/user`);
    
  xhr.onload = function() {
    const data = xhr.responseText;
    if (xhr.status >= 200 && xhr.status < 300) {
      currentUser = data.username || data.user || data;
      currentUserSpan.textContent = currentUser;
      showAppView();
      loadMessages();
    } else {
      console.log('[DEBUG] No current user found due to {data}');
      showAuthView();
    }
  };
  
  xhr.onerror = function() {
    console.error('Error checking user');
    showAuthView();
  };
  
  xhr.send();
}

function loginUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/login`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    
  xhr.onload = function() {
    const data = xhr.responseText;
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(authMessage, `Login successful! - ${data}`, 'success');
      currentUser = username;
      currentUserSpan.textContent = currentUser;
      loginForm.reset();
      setTimeout(() => {
        console.log('[DEBUG] Showing app view after login');
        showAppView();
        loadMessages();
      }, 1000);
    } else {
      console.log(`[DEBUG] Login failed with response: ${data}`);  
      try {
        showMessage(authMessage, data || 'Login failed', 'error');
      } catch (e) {
        showMessage(authMessage, `Login failed due to ${e}`, 'error');
      }
    }
  };
  
  xhr.onerror = function() {
    showMessage(authMessage, 'Network error occurred', 'error');
  };
  
  xhr.send(`username=${username}&password=${password}`);
}

function registerUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/register`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

  xhr.onload = function() {
    const data = xhr.responseText;
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(authMessage, `Registration successful! You can now login. ${data}`, 'success');
      registerForm.reset();
      // Switch to login tab
      tabBtns[0].click();
    } else {
      console.log(`[DEBUG] Registration failed with response: ${data}`);
      try {
        showMessage(authMessage, data || `Registration failed ${data}`, 'error');
      } catch (e) {
        showMessage(authMessage, `Registration failed due to exception ${data}`, 'error');
      }
    }
  };
  
  xhr.onerror = function() {
    showMessage(authMessage, 'Network error occurred', 'error');
  };
  
  xhr.send(`username=${username}&password=${password}`);
}

function logoutUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('DELETE', `${API_BASE}/login`);
    
  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, 'Logged out successfully!', 'info');
      currentUser = null;
      setTimeout(() => {
        showAuthView();
      }, 1000);
    } else {
      showMessage(appMessage, 'Logout failed', 'error');
    }
  };
  
  xhr.onerror = function() {
    showMessage(appMessage, 'Network error occurred', 'error');
  };
  
  xhr.send();
}

function loadMessages() {
  messagesContainer.innerHTML = `
    <div class="loading-spinner">
      <div class="spinner"></div>
      <p>Loading posts...</p>
    </div>
  `;
  
  const xhr = new XMLHttpRequest();
  xhr.open('GET', `${API_BASE}/messages`);
    
  xhr.onload = function() {
    const data = xhr.responseText;
    if (xhr.status >= 200 && xhr.status < 300) {
      displayMessages(parseMessagesToJSON(data));
    } else {
      messagesContainer.innerHTML = `<div class="error">Failed to load messages due to ${data}</div>`;
    }
  };
  
  xhr.onerror = function() {
    messagesContainer.innerHTML = '<div class="error">Network error loading messages</div>';
  };
  
  xhr.send();
}

function createMessage(message) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/messages`);
  xhr.setRequestHeader('Content-Type', 'application/json');

  const data = xhr.responseText;
  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message posted successfully! ${data}`, 'success');
      createMessageForm.reset();
      createPostModal.classList.add('hidden');
      document.body.style.overflow = 'auto';
      loadMessages();
    } else {
      console.log(`[DEBUG] Create message failed with response: ${data}`);
      try {
        showMessage(appMessage, data || 'Failed to post message', 'error');
      } catch (e) {
        showMessage(appMessage, `Failed to post message due to exception ${e}`, 'error');
      }
    }
  };
  
  xhr.onerror = function() {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  const author = currentUser.username || currentUser;
  console.log(`[DEBUG] Creating message as user: ${author}`);
  console.log(`[DEBUG] Message content: ${message}`);
  xhr.send(`author=${author}&msg=${message}`);
}

function deleteMessage(messageId) {
  const xhr = new XMLHttpRequest();
  xhr.open('DELETE', `${API_BASE}/messages`);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('id', messageId)

  xhr.onload = function() {
    const data = xhr.responseText;
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message deleted successfully! ${data}`, 'success');
      loadMessages();
    } else {
      console.log(`[DEBUG] Delete message failed with error ${data}`);
      try {
        showMessage(appMessage, data || 'Failed to delete message', 'error');
      } catch (e) {
        showMessage(appMessage, `Failed to delete message ${e}`, 'error');
      }
    }
  };

  xhr.onerror = function() {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  xhr.send();
}

function displayMessages(messages) {
  if (!messages || messages.length === 0) {
    messagesContainer.innerHTML = `
      <div class="empty-state">
        <p>No messages yet</p>
        <small>Be the first to post!</small>
      </div>
    `;
    return;
  }

  messagesContainer.innerHTML = messages.map(msg => {
    const timestamp = msg.time ? new Date(msg.time / 1000000) : null;
    const formattedDate = timestamp ? timestamp.toLocaleDateString() : 'Unknown date';
    const formattedTime = timestamp ? timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
    
    const author = msg.author || msg.username || 'Anonymous';
    const authorInitial = author.charAt(0).toUpperCase();
    const timeAgo = timestamp ? getTimeAgo(timestamp) : 'some time ago';

    return `
      <div class="message-item">
        <div class="message-header">
          <div class="message-author">
            <div class="author-avatar">${authorInitial}</div>
            <span class="author-name">u/${escapeHtml(author)}</span>
            <span class="message-timestamp">• ${timeAgo}</span>
          </div>
        </div>
        <div class="message-body">
          <div class="message-text">${escapeHtml(msg.msg || msg.message || msg.text || msg.content)}</div>
        </div>
        <div class="message-footer">
          <div class="message-meta">
            ID: ${msg.id} • ${formattedDate} ${formattedTime}
          </div>
          ${msg.author === currentUser ? 
            `<button class="delete-btn" onclick="deleteMessage(${msg.id})">Delete</button>` : 
            ''}
        </div>
      </div>
    `;
  }).join('');
}

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  
  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60
  };
  
  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval !== 1 ? 's' : ''} ago`;
    }
  }
  
  return 'just now';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Event Listeners
loginForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(loginForm);
  loginUser(formData.get('username'), formData.get('password'));
});

registerForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(registerForm);
  registerUser(formData.get('username'), formData.get('password'));
});

createMessageForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(createMessageForm);
  createMessage(formData.get('message'));
});

logoutBtn.addEventListener('click', () => {
  logoutUser();
});

// Initial check for current user
checkCurrentUser();