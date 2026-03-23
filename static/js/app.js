marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false,
  sanitize: false
});


document.addEventListener('DOMContentLoaded', function() {
  if (checkSession()) {
    initializeApp();
  }

  document.getElementById('inputField').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});

async function initializeApp() {
  // Display user name in sidebar
  var logoEl = document.querySelector('.logo');
  if (logoEl && AppState.userName) {
    logoEl.textContent = 'OSKAR';
    logoEl.insertAdjacentHTML('afterend',
      '<div style="font-size:11px;color:#999;padding:4px 20px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
      'Welcome, ' + AppState.userName + '</div>');
  }

  await checkOllamaStatus();
  await loadModels();
  selectSection('rlpm');
  // Session already created via /register_session/ — just load it
  AppState.chatHistory = [];
  document.getElementById('messagesInner').innerHTML = '';
  document.getElementById('welcome').style.display = 'flex';
  document.getElementById('messages').style.display = 'none';
  document.getElementById('chatTitle').textContent = 'New Chat';
  var cfg = SECTION_CONFIG[AppState.currentSection];
  updateWelcomeScreen(cfg);
  loadChatList();
}


function selectSection(section) {
  AppState.currentSection = section;

  document.querySelectorAll('.section-tab').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelector(`[data-section="${section}"]`).classList.add('active');

  const cfg = SECTION_CONFIG[section];
  renderAssistantTabs(cfg.assistants);
  selectAssistant(cfg.defaultAssistant);
  updateWelcomeScreen(cfg);
}

function renderAssistantTabs(assistants) {
  const container = document.getElementById('assistantTabs');
  container.innerHTML = assistants.map(a =>
    `<button class="assistant-tab" data-type="${a.type}" onclick="selectAssistant('${a.type}')">${a.label}</button>`
  ).join('');
}

function selectAssistant(type) {
  AppState.currentAssistant = type;
  document.querySelectorAll('.assistant-tab').forEach(tab => {
    tab.classList.remove('active');
  });
  const activeTab = document.querySelector(`.assistant-tab[data-type="${type}"]`);
  if (activeTab) activeTab.classList.add('active');

  const cfg = SECTION_CONFIG[AppState.currentSection];
  updatePromptCards(cfg.prompts);
}


async function checkOllamaStatus() {
  try {
    const data = await ApiClient.healthCheck();
    const statusIndicator = document.getElementById('ollamaStatus');
    if (data.ollama && data.ollama.status === 'connected') {
      statusIndicator.className = 'status-indicator connected';
      statusIndicator.title = 'Ollama connected';
    } else {
      statusIndicator.className = 'status-indicator disconnected';
      statusIndicator.title = 'Ollama disconnected';
    }
  } catch (error) {
    console.error('Health check failed:', error);
    document.getElementById('ollamaStatus').className = 'status-indicator disconnected';
  }
}

async function loadModels() {
  try {
    const data = await ApiClient.loadModels();
    AppState.currentModel = data.current_model;

    const select = document.getElementById('modelSelect');
    for (let option of select.options) {
      if (option.value === AppState.currentModel || AppState.currentModel.includes(option.value)) {
        option.selected = true;
        break;
      }
    }

    const available = data.locally_available || [];
    for (let option of select.options) {
      const isAvailable = available.some(m => m.includes(option.value) || option.value.includes(m.split(':')[0]));
      if (!isAvailable && available.length > 0) {
        option.text = option.text.replace(' (not installed)', '') + ' (not installed)';
      }
    }
  } catch (error) {
    console.error('Failed to load models:', error);
  }
}

async function changeModel(modelName) {
  try {
    const data = await ApiClient.changeModel(modelName);
    AppState.currentModel = data.current_model;
    console.log(`Model changed to: ${AppState.currentModel}`);
  } catch (error) {
    console.error('Model change failed:', error);
    alert(`Failed to change model: ${error.message}`);
    loadModels();
  }
}


function startNewChat() {
  ApiClient.newChat().then(data => {
    AppState.sessionId = data.session_id;
    AppState.currentChatMetadata = data.metadata;
    AppState.chatHistory = [];
    document.getElementById('messagesInner').innerHTML = '';
    document.getElementById('welcome').style.display = 'flex';
    document.getElementById('messages').style.display = 'none';
    document.getElementById('chatTitle').textContent = 'New Chat';

    const cfg = SECTION_CONFIG[AppState.currentSection];
    updateWelcomeScreen(cfg);

    loadChatList();
  });
}

function loadChat(chatId) {
  AppState.sessionId = chatId;

  ApiClient.getChatHistory(AppState.sessionId).then(data => {
    AppState.chatHistory = data.history;

    const chatInfo = findChatInfo(AppState.sessionId);
    if (chatInfo) {
      AppState.currentChatMetadata = chatInfo;
      document.getElementById('chatTitle').textContent = chatInfo.name;
    }

    renderChatHistory();
    loadChatList();
  });
}


function sendMessage() {
  const input = document.getElementById('inputField');
  const message = input.value.trim();

  if (!message) return;

  const welcome = document.getElementById('welcome');
  const messages = document.getElementById('messages');

  if (welcome.style.display !== 'none') {
    welcome.style.display = 'none';
    messages.style.display = 'block';
  }

  appendUserMessage(message);
  input.value = '';

  showThinking();

  const selectedModel = document.getElementById('modelSelect').value;
  const startTime = Date.now();

  ApiClient.generate(AppState.sessionId, message, AppState.currentAssistant, selectedModel)
    .then(data => {
      const responseTimeMs = Date.now() - startTime;
      hideThinking();
      appendAssistantMessage(data.answer, data.citations || {}, data.highlighted_passages || {}, data.model_used || selectedModel);
      loadChatList();

      // Log interaction with timing
      ApiClient.logInteraction(
        AppState.sessionId, message, data.answer || '',
        responseTimeMs, data.assistant_type || AppState.currentAssistant,
        data.model_used || selectedModel
      ).catch(function(err) { console.error('Log interaction failed:', err); });
    })
    .catch(error => {
      hideThinking();
      console.error('Error:', error);
      appendAssistantMessage('Sorry, I encountered an error. Is Ollama running?', {}, {}, '');
    });
}

function toggleFavorite(chatId) {
  ApiClient.toggleFavorite(chatId).then(() => loadChatList());
}

function exportChat(format) {
  ApiClient.exportChat(AppState.sessionId, format).then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_export_${new Date().toISOString().slice(0,10)}.${format}`;
    a.click();
    window.URL.revokeObjectURL(url);
  });
}
