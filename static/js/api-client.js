const ApiClient = {
  async healthCheck() {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },

  async loadModels() {
    const response = await fetch(`${API_BASE}/models/`);
    return response.json();
  },

  async changeModel(modelName) {
    const response = await fetch(`${API_BASE}/models/change/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    return response.json();
  },

  async newChat() {
    const response = await fetch(`${API_BASE}/new_chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    return response.json();
  },

  async listChats() {
    const response = await fetch(`${API_BASE}/list_chats/`);
    return response.json();
  },

  async getChatHistory(sessionId) {
    const response = await fetch(`${API_BASE}/get_chat_history/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    return response.json();
  },

  async generate(sessionId, query, assistantType, model) {
    const response = await fetch(`${API_BASE}/generate/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        query: query,
        assistant_type: assistantType,
        model: model
      })
    });
    return response.json();
  },

  async renameChat(sessionId, newName) {
    const response = await fetch(`${API_BASE}/rename_chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, new_name: newName })
    });
    return response.json();
  },

  async toggleFavorite(sessionId) {
    const response = await fetch(`${API_BASE}/toggle_favorite/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    return response.json();
  },

  async exportChat(sessionId, format) {
    const response = await fetch(`${API_BASE}/export_chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, format: format })
    });
    return response.blob();
  },

  async saveRating(question, responseText, rating) {
    const response = await fetch(`${API_BASE}/save_rating/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        response: responseText,
        rating: rating
      })
    });
    return response.json();
  },

  async registerSession(name, role) {
    const response = await fetch(`${API_BASE}/register_session/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, role: role })
    });
    return response.json();
  },

  async logInteraction(sessionId, question, responseText, responseTimeMs, assistantType, model) {
    const response = await fetch(`${API_BASE}/log_interaction/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question: question,
        response: responseText,
        response_time_ms: responseTimeMs,
        assistant_type: assistantType,
        model: model
      })
    });
    return response.json();
  },

  async viewDocument(filename, originalExtension, highlights) {
    const response = await fetch(`${API_BASE}/view_document/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: filename,
        original_extension: originalExtension || '',
        highlights: highlights
      })
    });
    if (!response.ok) throw new Error('Document not found');
    return response.blob();
  }
};
