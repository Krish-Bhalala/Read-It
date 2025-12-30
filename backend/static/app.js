const API_BASE = '{{API_BASE}}'; // Base URL for all API requests (injected by server)

// State management
let currentUser = null; // Stores the currently logged-in user's identifier

// DOM Elements
const authSection = document.getElementById('authSection'); // Section for login/register forms
const appSection = document.getElementById('appSection'); // Main application content section
const authMessage = document.getElementById('authMessage'); // Area to display messages on auth page
const appMessage = document.getElementById('appMessage'); // Area to display messages on app page
const loginForm = document.getElementById('loginForm'); // Login form element
const registerForm = document.getElementById('registerForm'); // Registration form element
const createMessageForm = document.getElementById('createMessageForm'); // Form for creating a new post
const logoutBtn = document.getElementById('headerLogoutBtn'); // Logout button
const currentUserSpan = document.getElementById('headerUserName'); // Display current username in header
const messagesContainer = document.getElementById('messagesContainer'); // Container for displaying posts
const headerUser = document.getElementById('headerUser'); // Header element showing user info

// Modal elements
const createPostTrigger = document.getElementById('createPostTrigger'); // Button to open the create post modal
const createPostModal = document.getElementById('createPostModal'); // The modal container
const closeModal = document.getElementById('closeModal'); // Button to close the modal
const cancelPost = document.getElementById('cancelPost'); // Button to cancel and close the modal

// Filter elements
const orderByFilter = document.getElementById('orderByFilter'); // Dropdown for message order
const authorFilter = document.getElementById('authorFilter'); // Dropdown for filtering by author
const timeFilter = document.getElementById('timeFilter'); // Dropdown for filtering by time
const clearFiltersBtn = document.getElementById('clearFilters'); // Button to reset all filters

// Filter state
let currentFilters = {
  orderBy: 'newest', // Default sort order
  author: '', // Default no author filter
  time: '' // Default no time filter
};

// Auth tabs
const tabBtns = document.querySelectorAll('.tab-btn'); // Buttons for switching between Login/Register
const authForms = document.querySelectorAll('.auth-form'); // The login and register form elements

// Tab switching logic for authentication forms
tabBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const tab = btn.dataset.tab; // Gets 'login' or 'register'

    tabBtns.forEach(b => b.classList.remove('active')); // Deactivate all tab buttons
    btn.classList.add('active'); // Activate the clicked button

    authForms.forEach(form => form.classList.remove('active')); // Hide all auth forms
    if (tab === 'login') {
      loginForm.classList.add('active'); // Show login form
    } else {
      registerForm.classList.add('active'); // Show register form
    }
  });
});

// Modal controls: show modal and disable background scrolling
createPostTrigger.addEventListener('click', () => {
  createPostModal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
});

// Modal controls: hide modal and enable background scrolling
closeModal.addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

cancelPost.addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

// Closes modal when clicking on the overlay outside the content
createPostModal.querySelector('.modal-overlay').addEventListener('click', () => {
  createPostModal.classList.add('hidden');
  document.body.style.overflow = 'auto';
});

// Utility Functions
// Displays a transient alert message in a specified container
function showMessage(container, message, type) {
  console.log(container)
  container.innerHTML = `<div class="message-alert ${type}">${message}</div>`;
  // Message disappears after 5 seconds
  setTimeout(() => {
    container.innerHTML = '';
  }, 5000);
}

// Switches view to the authentication section (hides app content)
function showAuthView() {
  authSection.classList.remove('hidden');
  appSection.classList.add('hidden');
  headerUser.classList.add('hidden');
}

// Switches view to the main application section (hides auth forms)
function showAppView() {
  authSection.classList.add('hidden');
  appSection.classList.remove('hidden');
  headerUser.classList.remove('hidden');
}

// Helper to safely parse JSON response text
function parseMessagesToJSON(jsonString) {
  return JSON.parse(jsonString);
}

// Predefined API response messages mapped by endpoint and HTTP status code
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

// Looks up a human-readable message based on endpoint and HTTP code
function getAPIMessage(endpoint, code, additionalInfo = "") {
  const messages = apiMessages[endpoint];
  if (!messages) return "Unknown API endpoint.";
  let message = messages[code] || `An unexpected error occurred (code: ${code})`;
  // Appends additional info (like server-side error body) for errors
  if (code >= 400 && messages[code] && additionalInfo) {
    return `${message} ${additionalInfo}`;
  }
  return message;
}


// API Functions using XHR
// Checks if a user is currently authenticated on the server
function checkCurrentUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', `${API_BASE}/user`);

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/user', status);
    if (status >= 200 && status < 300) {
      currentUser = data.username || data.user || data; // Extract username
      currentUserSpan.textContent = currentUser;
      showAppView(); // Show the main application
      loadMessages(); // Load messages for the logged-in user
    } else {
      type = 'error';
      showAuthView(); // Show login/register view
    }
    console.log(message);
  };

  xhr.onerror = function () {
    console.error('Error checking user');
    showAuthView();
    showMessage(authMessage, 'Network error occurred', 'error');
  };

  xhr.send();
}

// Sends user credentials to the server for login
function loginUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/login`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded'); // Set required content type

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/login', status, data);
    let type = 'success';
    // Successful login
    if (xhr.status >= 200 && xhr.status < 300) {
      currentUser = username;
      currentUserSpan.textContent = currentUser;
      loginForm.reset();
      // Wait a moment then transition to app view and load data
      setTimeout(() => {
        showAppView();
        loadMessages();
      }, 1000);
    } else {
      type = 'error';
    }
    showMessage(authMessage, message, type);
  };

  xhr.onerror = function () {
    showMessage(authMessage, 'Network error occurred', 'error');
  };

  // Send credentials in x-www-form-urlencoded format
  xhr.send(`username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
}

// Sends user credentials to the server for registration
function registerUser(username, password) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/register`);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/register', status, data);
    let type = 'success';
    // Successful registration
    if (status >= 200 && status < 300) {
      registerForm.reset();
      // Automatically switch to the login tab after successful registration
      tabBtns[0].click();
    } else {
      type = 'error';
    }
    showMessage(authMessage, message, type);
  };

  xhr.onerror = function () {
    showMessage(authMessage, 'Network error occurred', 'error');
  };

  xhr.send(`username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
}

// Sends a request to log the user out
function logoutUser() {
  const xhr = new XMLHttpRequest();
  xhr.open('DELETE', `${API_BASE}/login`);

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('DELETE /api/login', status, data);
    let type = 'success';
    // Successful logout
    if (status >= 200 && status < 300) {
      currentUser = null;
      // Wait a moment then transition to auth view
      setTimeout(() => {
        showAuthView();
      }, 1000);
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
  };

  xhr.onerror = function () {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  xhr.send();
}

// Builds the API request headers based on the current filter state
function getFilterSettings() {
  const settings = {};

  // Order-by filter logic
  if (currentFilters.orderBy === 'oldest') {
    settings['order-by'] = 'oldest';
  } else {
    settings['order-by'] = 'newest';
  }

  // Author filter logic
  if (currentFilters.author) {
    settings['group-author'] = currentFilters.author;
  }

  // Time filter logic (calculates a 'last' timestamp)
  if (currentFilters.time) {
    const now = Date.now() * 1000000; // Convert current time to nanoseconds (assumes server expects nanoseconds)
    let timeAgo = 0;

    // Calculates the duration in nanoseconds based on filter selection
    switch (currentFilters.time) {
      case '1h':
        timeAgo = 60 * 60 * 1000 * 1000000; // 1 hour
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

    // Sets the 'last' parameter to the calculated past timestamp
    if (timeAgo > 0) {
      settings['last'] = String(now - timeAgo);
    }
  }
  return settings;
}

// Fetches messages from the API, applying current filters
function loadMessages() {
  // Show a loading spinner while fetching
  messagesContainer.innerHTML = `
    <div class="loading-spinner">
      <div class="spinner"></div>
      <p>Loading posts...</p>
    </div>
  `;

  const xhr = new XMLHttpRequest();
  let URI = `${API_BASE}/messages`;

  const settings = getFilterSettings(); // Get current filters as URI parameters

  // Append filter settings to the URI as query parameters
  for (const [key, value] of Object.entries(settings)) {
    URI += (URI.includes('?') ? '&' : '?') + `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
  }

  xhr.open('GET', URI);
  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('/api/messages', status, data);
    // Successful fetch
    if (xhr.status >= 200 && xhr.status < 300) {
      const messages = parseMessagesToJSON(data);
      displayMessages(messages); // Render messages
      updateAuthorFilter(messages); // Populate the author filter options
    } else {
      messagesContainer.innerHTML = `<div class="error">Failed to load messages due to ${message}</div>`;
    }
  };

  xhr.onerror = function () {
    messagesContainer.innerHTML = '<div class="error">Network error loading messages</div>';
  };

  xhr.send();
}

// Submits a new message (post) to the server
function createMessage(message) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/messages`);
  xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('POST /api/messages', status, data);
    let type = 'success';
    // Successful post
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message posted successfully! ${data}`, 'success');
      createMessageForm.reset();
      createPostModal.classList.add('hidden'); // Close modal
      document.body.style.overflow = 'auto';
      loadMessages(); // Refresh message list
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
  };

  xhr.onerror = function () {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  const author = currentUser.username || currentUser;
  console.log(`[DEBUG] Creating message as user: ${author}`);
  console.log(`[DEBUG] Message content: ${message}`);
  // Send data in x-www-form-urlencoded format (though Content-Type is set to application/json, this sends form data)
  xhr.send(`author=${encodeURIComponent(author)}&msg=${message}`);
}

// Sends a request to delete a specific message
function deleteMessage(messageId) {
  const xhr = new XMLHttpRequest();
  let URI = `${API_BASE}/messages`;
  // Append message ID as a query parameter
  URI += (URI.includes('?') ? '&' : '?') + `id=${encodeURIComponent(messageId)}`;
  xhr.open('DELETE', URI);
  xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onload = function () {
    const data = xhr.responseText;
    const status = xhr.status;
    const message = getAPIMessage('DELETE /api/messages', status, data);
    let type = 'success';
    // Successful deletion
    if (xhr.status >= 200 && xhr.status < 300) {
      showMessage(appMessage, `Message deleted successfully! ${data}`, 'success');
      loadMessages(); // Refresh message list
    } else {
      type = 'error';
    }
    showMessage(appMessage, message, type);
  };

  xhr.onerror = function () {
    showMessage(appMessage, 'Network error occurred', 'error');
  };

  xhr.send();
}

// Renders the list of messages into the messages container
function displayMessages(messages) {
  // Show an empty state message if no messages are returned
  if (!messages || messages.length === 0) {
    messagesContainer.innerHTML = `
      <div class="empty-state">
        <p>No messages yet</p>
        <small>Be the first to post!</small>
      </div>
    `;
    return;
  }

  // Map messages array to HTML string and join
  messagesContainer.innerHTML = messages.map(msg => {
    // Convert nanosecond timestamp to Date object (dividing by 1000000)
    const timestamp = msg.time ? new Date(msg.time / 1000000) : null;
    const formattedDate = timestamp ? timestamp.toLocaleDateString() : 'Unknown date';
    const formattedTime = timestamp ? timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

    const author = msg.author || msg.username || 'Anonymous';
    const authorInitial = author.charAt(0).toUpperCase();
    const timeAgo = timestamp ? getTimeAgo(timestamp) : 'some time ago'; // Calculate time elapsed

    // Template for a single message item
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
          ${msg.author === currentUser ? // Only show delete button for current user's messages
        `<button class="delete-btn" onclick="deleteMessage(${msg.id})">Delete</button>` :
        ''}
        </div>
      </div>
    `;
  }).join('');
}

// Calculates a human-readable "time ago" string
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

  // Find the largest interval unit
  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval !== 1 ? 's' : ''} ago`;
    }
  }

  return 'just now';
}

// Utility function to safely escape HTML content
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Filter functions
// Updates the options in the author filter dropdown based on loaded messages
function updateAuthorFilter(messages) {
  const authors = new Set(); // Use a Set to get unique authors
  messages.forEach(msg => {
    const author = msg.author || msg.username;
    if (author) authors.add(author);
  });

  const currentSelection = authorFilter.value; // Store current selection
  authorFilter.innerHTML = '<option value="">All Authors</option>'; // Reset options

  // Add unique authors as options
  Array.from(authors).sort().forEach(author => {
    const option = document.createElement('option');
    option.value = author;
    option.textContent = `u/${author}`;
    authorFilter.appendChild(option);
  });

  // Restore the user's previous selection if it's still available
  if (currentSelection && authors.has(currentSelection)) {
    authorFilter.value = currentSelection;
  }
}

// Resets all filter settings to their default values
function resetFilters() {
  currentFilters = {
    orderBy: 'newest',
    author: '',
    time: ''
  };

  orderByFilter.value = 'newest';
  authorFilter.value = '';
  timeFilter.value = '';

  loadMessages(); // Reload messages with default filters
}

// Event Listeners
// Handle login form submission
loginForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(loginForm);
  loginUser(formData.get('username'), formData.get('password'));
});

// Handle registration form submission
registerForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(registerForm);
  registerUser(formData.get('username'), formData.get('password'));
});

// Handle new message creation form submission
createMessageForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(createMessageForm);
  createMessage(formData.get('message'));
});

// Handle logout button click
logoutBtn.addEventListener('click', (e) => {
  e.preventDefault();
  logoutUser();
});

// Filter event listeners: update filter state and reload messages on change
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

// Handle clear filters button click
clearFiltersBtn.addEventListener('click', () => {
  resetFilters();
});

// Initial check for current user state when the application loads
checkCurrentUser();