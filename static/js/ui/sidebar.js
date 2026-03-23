function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const icon = document.getElementById('toggle-icon');
  const newChatText = document.getElementById('newChatText');

  sidebar.classList.toggle('collapsed');

  if (sidebar.classList.contains('collapsed')) {
    icon.className = 'fas fa-chevron-right';
    newChatText.textContent = '+';
  } else {
    icon.className = 'fas fa-chevron-left';
    newChatText.textContent = 'New Chat';
  }
}

function loadChatList() {
  ApiClient.listChats().then(data => {
    AppState.allChats = data;
    renderChatList(data);
  });
}

function renderChatList(data) {
  const favoritesList = document.getElementById('favoritesList');
  const recentList = document.getElementById('recentList');
  const allChatsList = document.getElementById('allChatsList');

  favoritesList.innerHTML = '';
  recentList.innerHTML = '';
  allChatsList.innerHTML = '';

  if (data.favorites && data.favorites.length > 0) {
    data.favorites.forEach(chat => {
      favoritesList.innerHTML += createChatItem(chat, true);
    });
  }

  const allChatsArray = [];
  if (data.no_project) {
    allChatsArray.push(...data.no_project);
  }

  Object.values(data.projects || {}).forEach(project => {
    allChatsArray.push(...project.chats);
  });

  allChatsArray.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

  allChatsArray.slice(0, 5).forEach(chat => {
    recentList.innerHTML += createChatItem(chat);
  });

  allChatsArray.forEach(chat => {
    allChatsList.innerHTML += createChatItem(chat);
  });
}

function createChatItem(chat, isFavorite = false) {
  const isActive = chat.session_id === AppState.sessionId ? 'active' : '';
  const starClass = chat.is_favorite ? 'fas' : 'far';

  return `
    <div class="chat-item ${isActive}" onclick="loadChat('${chat.session_id}')">
      <div class="chat-item-text">${chat.name}</div>
      <div class="chat-item-actions" onclick="event.stopPropagation()">
        ${!isFavorite ? `<button class="chat-action-btn" onclick="toggleFavorite('${chat.session_id}')" title="Favorite">
          <i class="${starClass} fa-star"></i>
        </button>` : ''}
      </div>
    </div>
  `;
}

function findChatInfo(sessionId) {
  if (AppState.allChats.favorites) {
    for (const chat of AppState.allChats.favorites) {
      if (chat.session_id === sessionId) return chat;
    }
  }
  if (AppState.allChats.no_project) {
    for (const chat of AppState.allChats.no_project) {
      if (chat.session_id === sessionId) return chat;
    }
  }
  for (const projectData of Object.values(AppState.allChats.projects || {})) {
    for (const chat of projectData.chats) {
      if (chat.session_id === sessionId) return chat;
    }
  }
  return null;
}
