function checkSession() {
  var sessionId = sessionStorage.getItem('oskar_session_id');
  var userName = sessionStorage.getItem('oskar_userName');
  if (!sessionId || !userName) {
    window.location.href = 'home.html';
    return false;
  }
  AppState.sessionId = sessionId;
  AppState.userName = userName;
  AppState.userRole = sessionStorage.getItem('oskar_userRole') || '';
  return true;
}
