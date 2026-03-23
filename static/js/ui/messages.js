function appendUserMessage(message, animate = true) {
  const messagesInner = document.getElementById('messagesInner');

  const messageDiv = document.createElement('div');
  messageDiv.className = 'message user';

  messageDiv.innerHTML = `
    <div class="message-header">You</div>
    <div class="message-content">${escapeHtml(message)}</div>
  `;

  messagesInner.appendChild(messageDiv);
  document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
}

function appendAssistantMessage(message, citations, highlightedPassages, modelUsed, animate = true) {
  const messagesInner = document.getElementById('messagesInner');

  let htmlContent = marked.parse(message);

  if (Object.keys(citations).length > 0) {
    htmlContent = htmlContent.replace(/\[(\d+)\]/g, (match, num) => {
      if (citations[num]) {
        return `<span class="citation" data-citation="${num}">[${num}]</span>`;
      }
      return match;
    });
  }

  const cleanHtml = DOMPurify.sanitize(htmlContent, {
    ADD_TAGS: ['span'],
    ADD_ATTR: ['class', 'data-citation', 'style'],
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                   'blockquote', 'code', 'pre', 'ol', 'ul', 'li', 'a', 'span', 'div',
                   'table', 'thead', 'tbody', 'tr', 'td', 'th', 'hr'],
    ALLOWED_ATTR: ['href', 'title', 'target', 'class', 'data-citation', 'style']
  });

  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant';

  const assistantName = getAssistantName(AppState.currentAssistant);
  const messageId = 'msg_' + Date.now();
  const modelTag = modelUsed ? `<span class="model-tag">${modelUsed}</span>` : '';

  messageDiv.innerHTML = `
    <div class="message-header">${assistantName}</div>
    <div class="message-content">${cleanHtml}</div>
    <div class="message-actions">
      ${Object.keys(citations).length > 0 ? '<button class="message-action" onclick="toggleSources(this)">Sources</button>' : ''}
      <button class="message-action" onclick="copyMessage(this)">Copy</button>
      <div class="rating-stars" id="rating_${messageId}">
        <span class="star" onclick="rateMessage('${messageId}', 1)">&#9733;</span>
        <span class="star" onclick="rateMessage('${messageId}', 2)">&#9733;</span>
        <span class="star" onclick="rateMessage('${messageId}', 3)">&#9733;</span>
        <span class="star" onclick="rateMessage('${messageId}', 4)">&#9733;</span>
        <span class="star" onclick="rateMessage('${messageId}', 5)">&#9733;</span>
      </div>
      ${modelTag}
    </div>
    ${Object.keys(citations).length > 0 ? createSourcesSection(citations, highlightedPassages) : ''}
  `;

  messagesInner.appendChild(messageDiv);

  messageDiv.querySelectorAll('.citation').forEach(citation => {
    citation.addEventListener('click', function() {
      const citationNum = this.dataset.citation;
      if (citations[citationNum]) {
        viewDocument(citations[citationNum], highlightedPassages[citationNum] || []);
      }
    });
  });

  document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
}

function createSourcesSection(citations, highlightedPassages) {
  let html = '<div class="sources">';

  Object.entries(citations).forEach(([num, info]) => {
    html += `
      <div class="source-item">
        <span class="source-num">[${num}]</span>
        <span class="source-name">${info.display_filename || info.filename}</span>
        <button class="source-view" onclick='viewDocument(${JSON.stringify(info)}, ${JSON.stringify(highlightedPassages[num] || [])})'>View</button>
      </div>
    `;
  });

  html += '</div>';
  return html;
}

function toggleSources(button) {
  const sources = button.parentElement.nextElementSibling;
  if (sources && sources.classList.contains('sources')) {
    sources.classList.toggle('visible');
    button.textContent = sources.classList.contains('visible') ? 'Hide Sources' : 'Sources';
  }
}

function renderChatHistory() {
  const messagesInner = document.getElementById('messagesInner');
  const welcome = document.getElementById('welcome');
  const messages = document.getElementById('messages');

  messagesInner.innerHTML = '';
  welcome.style.display = 'none';
  messages.style.display = 'block';

  AppState.chatHistory.forEach(msg => {
    if (msg.role === 'user') {
      appendUserMessage(msg.message, false);
    } else {
      appendAssistantMessage(msg.message, msg.citations || {}, msg.highlighted_passages || {}, msg.model_used || '', false);
    }
  });

  messages.scrollTop = messages.scrollHeight;
}

function copyMessage(button) {
  const content = button.closest('.message').querySelector('.message-content');
  const text = content.innerText;

  navigator.clipboard.writeText(text).then(() => {
    const original = button.textContent;
    button.textContent = 'Copied';
    setTimeout(() => {
      button.textContent = original;
    }, 2000);
  });
}

function rateMessage(messageId, rating) {
  const stars = document.querySelectorAll(`#rating_${messageId} .star`);
  stars.forEach((star, index) => {
    if (index < rating) {
      star.classList.add('active');
    } else {
      star.classList.remove('active');
    }
  });

  const messageContent = document.querySelector(`#rating_${messageId}`).closest('.message').querySelector('.message-content').innerText;
  const previousMessage = document.querySelector(`#rating_${messageId}`).closest('.message').previousElementSibling;
  const question = previousMessage ? previousMessage.querySelector('.message-content').innerText : '';

  ApiClient.saveRating(question, messageContent, rating);
}
