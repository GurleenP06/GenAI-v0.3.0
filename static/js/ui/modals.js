function viewDocument(docInfo, passages) {
  const filename = docInfo.filename;

  ApiClient.viewDocument(filename, docInfo.original_extension || '', passages)
    .then(blob => {
      const fileURL = window.URL.createObjectURL(blob);
      AppState.currentDocumentUrl = fileURL;

      document.getElementById('documentTitle').textContent = docInfo.display_filename || docInfo.filename;
      document.getElementById('documentFrame').src = fileURL;
      document.getElementById('documentModal').classList.add('show');
    })
    .catch(error => {
      console.error('Error viewing document:', error);
      alert('Unable to open document.');
    });
}

function closeDocumentModal() {
  document.getElementById('documentModal').classList.remove('show');

  if (AppState.currentDocumentUrl) {
    window.URL.revokeObjectURL(AppState.currentDocumentUrl);
    AppState.currentDocumentUrl = null;
  }

  document.getElementById('documentFrame').src = '';
}

function downloadDocument() {
  if (AppState.currentDocumentUrl) {
    const a = document.createElement('a');
    a.href = AppState.currentDocumentUrl;
    a.download = document.getElementById('documentTitle').textContent;
    a.click();
  }
}

function showRenameModal() {
  document.getElementById('newChatName').value = AppState.currentChatMetadata.name || '';
  document.getElementById('renameModal').classList.add('show');
}

function closeRenameModal() {
  document.getElementById('renameModal').classList.remove('show');
}

function saveNewName() {
  const newName = document.getElementById('newChatName').value.trim();
  if (newName) {
    ApiClient.renameChat(AppState.sessionId, newName).then(() => {
      document.getElementById('chatTitle').textContent = newName;
      closeRenameModal();
      loadChatList();
    });
  }
}
