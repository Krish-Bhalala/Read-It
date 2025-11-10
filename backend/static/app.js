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

// Filter elements
const orderByFilter = document.getElementById('orderByFilter');
const authorFilter = document.getElementById('authorFilter');
const timeFilter = document.getElementById('timeFilter');
const clearFiltersBtn = document.getElementById('clearFilters');

// Filter state
let currentFilters = {
  orderBy: 'newest',
  author: '',
  time: ''
};

// Auth tabs
const tabBtns = document.querySelectorAll('.tab-btn');
const authForms = document.querySelectorAll('.auth-form');

// Tab switching
tabBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
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
  console.log(container)
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

function parseMessagesToJSON(jsonString) {
    return JSON.parse(jsonString);
}

const apiMessages = {
  "/api/user": {
    200: "User info retrieved successfully.",
    400: "Invalid request for user information.",
    401: "You must be logged in to view user information.",
    403: "Access to user information is forbidden.",
    404: "User not found.",
    405: "Method not allowed for user information.",
    500: "Server error while retrieving user information.",
    429: "Too many requests to user info. Please slow down."
  },
  "/api/register": {
    201: "User registered successfully.",
    400: "Registration request invalid. Check input.",
    405: "Registration failed",
    409: "User already exists.",
    500: "Server error during registration.",
    429: "Too many registration attempts. Please wait."
  },
  "/api/login": {
    200: "Login successful.",
    400: "Invalid login request.",
    401: "Incorrect username or password.",
    403: "Account is locked or forbidden.",
    404: "User not found.",
    405: "Login failed.",
    429: "Too many login attempts. Please wait.",
    500: "Server error during login."
  },
  "DELETE /api/login": {
    200: "Logout successful.",
    401: "You must be logged in to logout.",
    405: "Method not allowed for user information.",
    429: "Too many logout attempts. Please wait.",
    500: "Server error during logout."
  },
  "/api/messages": {
    200: "Messages retrieved successfully.",
    400: "Invalid request for messages.",
    401: "You must be logged in to view messages.",
    405: "Method not allowed for user information.",
    403: "Access to messages is forbidden.",
    500: "Server error while retrieving messages.",
    429: "Too many requests. Slow down please."
  },
  "POST /api/messages": {
    201: "Message created successfully.",
    400: "Invalid message data.",
    401: "You must be logged in to create messages.",
    405: "Not allowed to retrieve messages",
    403: "You do not have permission to create messages.",
    429: "You are creating messages too fast, Please slow down.",
    500: "Server error while creating message."
  },
  "DELETE /api/messages": {
    200: "Message deleted successfully.",
    400: "Invalid delete message request.",
    401: "You must be logged in to delete messages.",
    405: "Not allowed to delete message",
    403: "You do not have permission to delete this message.",
    404: "Message not found.",
    429: "You are deleting too fast, Please slow down.",
    500: "Server error while deleting message."
  }
};

function getAPIMessage(endpoint, code, additionalInfo = "") {
  const messages = apiMessages[endpoint];
  if (!messages) return "Unknown API endpoint.";
  let message = messages[code] || `An unexpected error occurred (code: ${code})`;
  if (code >= 400 && messages[code] && additionalInfo) {
    return `${message} ${additionalInfo}`;
  }
  return message;
}


// API Functions using XHR
function checkCurrentUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', `${API_BASE}/user`);

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/user', status);
    let type = 'success'
    if (status >= 200 && status < 300) {
      currentUser = data.username || data.user || data;
      currentUserSpan.textContent = currentUser;
      showAppView();
      loadMessages();
    } else {
      type = 'error';
      showAuthView();
    }
    console.log(message);
  };
  
  xhr.onerror = function() {
    console.error('Error checking user');
    showAuthView();
    showMessage(authMessage, 'Network error occurred', 'error');
  };
  
  xhr.send();
}

function loginUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/login`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/login', status, data);
    let type = 'success';
    if (xhr.status >= 200 && xhr.status < 300) {
      currentUser = username;
      currentUserSpan.textContent = currentUser;
      loginForm.reset();
      setTimeout(() => {
        showAppView();
        loadMessages();
      }, 1000);
    } else { 
      type = 'error';
    }
    showMessage(authMessage, message, type);
  };
  
  xhr.onerror = function() {
    showMessage(authMessage, 'Network error occurred', 'error');
  };
  
  xhr.send(`username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
}

function registerUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/register`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/register', status, data);
    let type = 'success';
    if (status >= 200 && status < 300) {
      registerForm.reset();
      // Switch to login tab
      tabBtns[0].click();
    } else {
      type = 'error';
    }
    showMessage(authMessage, message, type);
  };
  
  xhr.onerror = function() {
    showMessage(authMessage, 'Network error occurred', 'error');
  };
  
  xhr.send(`username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
}

function logoutUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('DELETE', `${API_BASE}/login`);

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('DELETE /api/login', status, data);
    let type = 'success';
    if (status >= 200 && status < 300) {
      currentUser = null;
      setTimeout(() => {
        showAuthView();
      }, 1000);
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
  };

  xhr.onerror = function() {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  xhr.send();
}

function getFilterSettings() {
  // Build settings headers based on current filters
  const settings = {};
  
  // Order-by filter
  if (currentFilters.orderBy === 'oldest') {
    settings['order-by'] = 'oldest';
  }else {
    settings['order-by'] = 'newest';
  }
  
  // Author filter
  if (currentFilters.author) {
    settings['group-author'] = currentFilters.author;
  }
  
  // Time filter (calculate timestamp for "last" parameter)
  if (currentFilters.time) {
    const now = Date.now() * 1000000; // Convert to nanoseconds
    let timeAgo = 0;
    
    switch(currentFilters.time) {
      case '1h':
        timeAgo = 60 * 60 * 1000 * 1000000; // 1 hour in nanoseconds
        break;
      case '24h':
        timeAgo = 24 * 60 * 60 * 1000 * 1000000; // 24 hours
        break;
      case '7d':
        timeAgo = 7 * 24 * 60 * 60 * 1000 * 1000000; // 7 days
        break;
      case '30d':
        timeAgo = 30 * 24 * 60 * 60 * 1000 * 1000000; // 30 days
        break;
    }
    
    if (timeAgo > 0) {
      settings['last'] = String(now - timeAgo);
    }
  }
  return settings;
}

function loadMessages() {
  messagesContainer.innerHTML = `
    <div class="loading-spinner">
      <div class="spinner"></div>
      <p>Loading posts...</p>
    </div>
  `;
  
  const xhr = new XMLHttpRequest();
  let URI = `${API_BASE}/messages`;

  const settings = getFilterSettings();

  // Set settings in URI query parameters
  for (const [key, value] of Object.entries(settings)) {
    URI += (URI.includes('?') ? '&' : '?') + `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
  }

  xhr.open('GET', URI);
  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/messages', status, data);
    if (xhr.status >= 200 && xhr.status < 300) {
      const messages = parseMessagesToJSON(data);
      displayMessages(messages);
      updateAuthorFilter(messages);
    } else {
      messagesContainer.innerHTML = `<div class="error">Failed to load messages due to ${message}</div>`;
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

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('POST /api/messages', status, data);
    let type = 'success';
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message posted successfully! ${data}`, 'success');
      createMessageForm.reset();
      createPostModal.classList.add('hidden');
      document.body.style.overflow = 'auto';
      loadMessages();
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
  };

  xhr.onerror = function() {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  const author = currentUser.username || currentUser;
  console.log(`[DEBUG] Creating message as user: ${author}`);
  console.log(`[DEBUG] Message content: ${message}`);
  xhr.send(`author=${encodeURIComponent(author)}&msg=${message}`);
}

function deleteMessage(messageId) {
  const xhr = new XMLHttpRequest();
  let URI = `${API_BASE}/messages`;
  URI += (URI.includes('?') ? '&' : '?') + `id=${encodeURIComponent(messageId)}`;
  xhr.open('DELETE', URI);
  xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onload = function() {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('DELETE /api/messages', status, data);
    let type = 'success';
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message deleted successfully! ${data}`, 'success');
      loadMessages();
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
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

// Filter functions
function updateAuthorFilter(messages) {
  const authors = new Set();
  messages.forEach(msg => {
    const author = msg.author || msg.username;
    if (author) authors.add(author);
  });
  
  const currentSelection = authorFilter.value;
  authorFilter.innerHTML = '<option value="">All Authors</option>';
  
  Array.from(authors).sort().forEach(author => {
    const option = document.createElement('option');
    option.value = author;
    option.textContent = `u/${author}`;
    authorFilter.appendChild(option);
  });
  
  // Restore selection if it still exists
  if (currentSelection && authors.has(currentSelection)) {
    authorFilter.value = currentSelection;
  }
}

function resetFilters() {
  currentFilters = {
    orderBy: 'newest',
    author: '',
    time: ''
  };

  orderByFilter.value = 'newest';
  authorFilter.value = '';
  timeFilter.value = '';

  loadMessages();
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

logoutBtn.addEventListener('click', (e) => {
  e.preventDefault();
  logoutUser();
});

// Filter event listeners
orderByFilter.addEventListener('change', (e) => {
  currentFilters.orderBy = e.target.value;
  loadMessages();
});

authorFilter.addEventListener('change', (e) => {
  currentFilters.author = e.target.value;
  loadMessages();
});

timeFilter.addEventListener('change', (e) => {
  currentFilters.time = e.target.value;
  loadMessages();
});

clearFiltersBtn.addEventListener('click', () => {
  resetFilters();
});

// Initial check for current user
checkCurrentUser();