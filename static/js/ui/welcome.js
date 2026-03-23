function updateWelcomeScreen(cfg) {
  const titleEl = document.getElementById('welcomeTitle');
  const descEl = document.getElementById('welcomeDescription');

  if (titleEl) titleEl.textContent = cfg.welcomeTitle;
  if (descEl) descEl.textContent = cfg.welcomeDescription;

  updatePromptCards(cfg.prompts);
}

function updatePromptCards(prompts) {
  const grid = document.getElementById('promptsGrid');
  if (grid && prompts) {
    grid.innerHTML = prompts.map(p => `
      <div class="prompt-card" onclick="addPromptToInput('${p.prompt.replace(/'/g, "\\'")}')">
        <div class="prompt-label">${p.label}</div>
        <div class="prompt-text">${p.text}</div>
      </div>
    `).join('');
  }
}

function addPromptToInput(prompt) {
  const input = document.getElementById('inputField');
  input.value = prompt;
  input.focus();
}
