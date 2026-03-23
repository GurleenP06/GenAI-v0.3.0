function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showThinking() {
  document.getElementById('thinking').classList.add('active');
}

function hideThinking() {
  document.getElementById('thinking').classList.remove('active');
}

function getAssistantName(type) {
  const names = {
    rlpm: 'RLPM Analyst',
    opo: 'OPO Search',
    writing: 'Writing Assistant',
    document: 'Document Assistant'
  };
  return names[type] || 'Assistant';
}
