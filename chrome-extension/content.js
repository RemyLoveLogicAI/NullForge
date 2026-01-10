// NullForge Chrome Extension - Content Script
// Injects NullForge functionality into GitHub/GitLab/Bitbucket

(function() {
  'use strict';

  // Configuration
  const BUTTON_ID = 'nullforge-btn';
  const PANEL_ID = 'nullforge-panel';

  // Create floating action button
  function createFloatingButton() {
    if (document.getElementById(BUTTON_ID)) return;

    const btn = document.createElement('div');
    btn.id = BUTTON_ID;
    btn.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="nf-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea"/>
            <stop offset="100%" style="stop-color:#764ba2"/>
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="45" fill="url(#nf-grad)"/>
        <text x="50" y="65" text-anchor="middle" fill="white" font-size="40" font-weight="bold">N</text>
      </svg>
    `;
    btn.title = 'NullForge AI';
    btn.onclick = togglePanel;
    document.body.appendChild(btn);
  }

  // Create slide-in panel
  function createPanel() {
    if (document.getElementById(PANEL_ID)) return;

    const panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <div class="nf-panel-header">
        <h3>NullForge AI</h3>
        <button class="nf-close-btn">&times;</button>
      </div>
      <div class="nf-panel-content">
        <div class="nf-actions">
          <button class="nf-action-btn" data-action="explain">
            <span class="nf-icon">📖</span>
            <span>Explain Code</span>
          </button>
          <button class="nf-action-btn" data-action="optimize">
            <span class="nf-icon">⚡</span>
            <span>Optimize</span>
          </button>
          <button class="nf-action-btn" data-action="audit">
            <span class="nf-icon">🔒</span>
            <span>Security Audit</span>
          </button>
          <button class="nf-action-btn" data-action="test">
            <span class="nf-icon">🧪</span>
            <span>Generate Tests</span>
          </button>
          <button class="nf-action-btn" data-action="docs">
            <span class="nf-icon">📝</span>
            <span>Generate Docs</span>
          </button>
          <button class="nf-action-btn" data-action="refactor">
            <span class="nf-icon">🔄</span>
            <span>Refactor</span>
          </button>
        </div>
        <div class="nf-custom-prompt">
          <textarea placeholder="Or enter a custom prompt..."></textarea>
          <button class="nf-submit-btn">Synthesize</button>
        </div>
        <div class="nf-output" style="display: none;">
          <div class="nf-output-header">
            <span>Result</span>
            <button class="nf-copy-btn">Copy</button>
          </div>
          <pre class="nf-output-content"></pre>
        </div>
        <div class="nf-loading" style="display: none;">
          <div class="nf-spinner"></div>
          <span>Processing...</span>
        </div>
      </div>
    `;
    document.body.appendChild(panel);

    // Event listeners
    panel.querySelector('.nf-close-btn').onclick = togglePanel;
    panel.querySelectorAll('.nf-action-btn').forEach(btn => {
      btn.onclick = () => handleAction(btn.dataset.action);
    });
    panel.querySelector('.nf-submit-btn').onclick = handleCustomPrompt;
    panel.querySelector('.nf-copy-btn').onclick = copyResult;
  }

  // Toggle panel visibility
  function togglePanel() {
    const panel = document.getElementById(PANEL_ID);
    if (panel) {
      panel.classList.toggle('visible');
    }
  }

  // Get selected code
  function getSelectedCode() {
    const selection = window.getSelection().toString();
    if (selection) return selection;

    // Try to get code from GitHub code view
    const codeBlock = document.querySelector('.blob-code-content, .highlight');
    if (codeBlock) {
      return codeBlock.textContent;
    }

    return '';
  }

  // Handle action buttons
  async function handleAction(action) {
    const code = getSelectedCode();
    if (!code) {
      alert('Please select some code first');
      return;
    }

    const prompts = {
      explain: `Explain this code in detail:\n\n${code}`,
      optimize: `Optimize this code for performance and readability:\n\n${code}`,
      audit: `Security audit this code and identify vulnerabilities:\n\n${code}`,
      test: `Generate comprehensive unit tests for this code:\n\n${code}`,
      docs: `Generate documentation for this code:\n\n${code}`,
      refactor: `Refactor this code following best practices:\n\n${code}`
    };

    await sendToAPI(prompts[action]);
  }

  // Handle custom prompt
  async function handleCustomPrompt() {
    const panel = document.getElementById(PANEL_ID);
    const textarea = panel.querySelector('.nf-custom-prompt textarea');
    const prompt = textarea.value.trim();
    
    if (!prompt) {
      alert('Please enter a prompt');
      return;
    }

    const code = getSelectedCode();
    const fullPrompt = code ? `${prompt}\n\nCode:\n${code}` : prompt;

    await sendToAPI(fullPrompt);
  }

  // Send request to NullForge API
  async function sendToAPI(prompt) {
    const panel = document.getElementById(PANEL_ID);
    const loading = panel.querySelector('.nf-loading');
    const output = panel.querySelector('.nf-output');
    const outputContent = panel.querySelector('.nf-output-content');

    loading.style.display = 'flex';
    output.style.display = 'none';

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'synthesize',
        prompt,
        provider: 'venice'
      });

      if (response.success) {
        outputContent.textContent = formatResult(response.data);
        output.style.display = 'block';
      } else {
        outputContent.textContent = `Error: ${response.error}`;
        output.style.display = 'block';
      }
    } catch (error) {
      outputContent.textContent = `Error: ${error.message}`;
      output.style.display = 'block';
    } finally {
      loading.style.display = 'none';
    }
  }

  // Format API result
  function formatResult(data) {
    if (typeof data === 'string') return data;
    if (data.result) return data.result;
    if (data.files) {
      return Object.entries(data.files)
        .map(([name, content]) => `// ${name}\n${content}`)
        .join('\n\n');
    }
    return JSON.stringify(data, null, 2);
  }

  // Copy result to clipboard
  function copyResult() {
    const panel = document.getElementById(PANEL_ID);
    const content = panel.querySelector('.nf-output-content').textContent;
    navigator.clipboard.writeText(content).then(() => {
      const btn = panel.querySelector('.nf-copy-btn');
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = 'Copy', 2000);
    });
  }

  // Add inline buttons to code blocks
  function addInlineButtons() {
    document.querySelectorAll('.blob-code-content, .highlight, pre code').forEach(codeBlock => {
      if (codeBlock.dataset.nfProcessed) return;
      codeBlock.dataset.nfProcessed = 'true';

      const wrapper = codeBlock.closest('.blob-wrapper, .highlight');
      if (!wrapper) return;

      const toolbar = document.createElement('div');
      toolbar.className = 'nf-inline-toolbar';
      toolbar.innerHTML = `
        <button class="nf-inline-btn" data-action="explain" title="Explain">📖</button>
        <button class="nf-inline-btn" data-action="optimize" title="Optimize">⚡</button>
        <button class="nf-inline-btn" data-action="audit" title="Audit">🔒</button>
      `;

      toolbar.querySelectorAll('.nf-inline-btn').forEach(btn => {
        btn.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          
          // Select the code block content
          const range = document.createRange();
          range.selectNodeContents(codeBlock);
          window.getSelection().removeAllRanges();
          window.getSelection().addRange(range);
          
          handleAction(btn.dataset.action);
        };
      });

      wrapper.style.position = 'relative';
      wrapper.appendChild(toolbar);
    });
  }

  // Initialize
  function init() {
    createFloatingButton();
    createPanel();
    addInlineButtons();

    // Watch for dynamic content
    const observer = new MutationObserver(() => {
      addInlineButtons();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
