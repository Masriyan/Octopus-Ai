/**
 * Octopus AI — Main Application 🐙
 * App initialization, WebSocket management, and panel routing.
 */

// ─── Configuration ───────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

// ─── State ───────────────────────────────────────────────────────────
const state = {
    currentConvId: null,
    ws: null,
    isStreaming: false,
    config: {},
    conversations: [],
};

// ─── DOM Elements ────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    welcomeScreen: $('#welcome-screen'),
    chatScreen: $('#chat-screen'),
    chatTitle: $('#chat-title'),
    messagesContainer: $('#messages-container'),
    messageInput: $('#message-input'),
    sendBtn: $('#send-btn'),
    newChatBtn: $('#new-chat-btn'),
    conversationList: $('#conversation-list'),
    settingsBtn: $('#settings-btn'),
    settingsModal: $('#settings-modal'),
    closeSettings: $('#close-settings'),
    modelSelect: $('#model-select'),
    modelBadge: $('#model-badge'),
    searchConversations: $('#search-conversations'),
    toggleSidebar: $('#toggle-sidebar'),
    sidebar: $('#sidebar'),
    temperature: $('#temperature'),
    tempValue: $('#temp-value'),
    // Google Sign-In
    googleSigninBtn: $('#google-signin-btn'),
    googleSigninArea: $('#google-signin-area'),
    googleUserArea: $('#google-user-area'),
    googleUserAvatar: $('#google-user-avatar'),
    googleUserName: $('#google-user-name'),
    googleSignoutBtn: $('#google-signout-btn'),
    googleClientId: $('#google-client-id'),
    saveClientId: $('#save-client-id'),
    authStatusText: $('#auth-status-text'),
    googleAuthStatus: $('#google-auth-status'),
};

// ─── Initialization ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await loadConversations();
    await checkGoogleAuthStatus();
    setupEventListeners();
    setupTextareaAutoResize();
    initGoogleSignIn();
});

// ─── Config ──────────────────────────────────────────────────────────
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/api/config`);
        state.config = await res.json();
        applyConfig();
    } catch (e) {
        console.error('Failed to load config:', e);
        state.config = { llm_provider: 'openai', model: 'gpt-4o-mini', temperature: 0.7 };
    }
}

function applyConfig() {
    const { llm_provider, model, temperature, tools_enabled } = state.config;

    // Provider radio
    const radio = $(`input[name="provider"][value="${llm_provider}"]`);
    if (radio) radio.checked = true;

    // Model
    updateModelOptions(llm_provider);
    if (els.modelSelect) els.modelSelect.value = model;
    els.modelBadge.textContent = model;

    // Temperature
    if (els.temperature) {
        els.temperature.value = temperature || 0.7;
        els.tempValue.textContent = temperature || 0.7;
    }

    // Tool toggles
    if (tools_enabled) {
        for (const [tool, enabled] of Object.entries(tools_enabled)) {
            const toggle = $(`#tool-${tool}`);
            if (toggle) toggle.checked = enabled;
        }
    }
}

async function saveConfigValue(key, value) {
    try {
        await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: value }),
        });
    } catch (e) {
        console.error('Failed to save config:', e);
    }
}

function updateModelOptions(provider) {
    const models = {
        openai: [
            { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
            { value: 'gpt-4o', label: 'GPT-4o' },
            { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
        ],
        anthropic: [
            { value: 'claude-sonnet-4-20250514', label: 'Claude 3.5 Sonnet' },
            { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
            { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
        ],
        ollama: [
            { value: 'llama3.2', label: 'Llama 3.2' },
            { value: 'mistral', label: 'Mistral' },
            { value: 'codellama', label: 'Code Llama' },
        ],
        gemini: [
            { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
            { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro' },
            { value: 'gemini-3.1-flash-lite-preview', label: 'Gemini 3.1 Flash Lite' },
            { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
            { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
        ],
    };

    const options = models[provider] || models.openai;
    els.modelSelect.innerHTML = options
        .map(m => `<option value="${m.value}">${m.label}</option>`)
        .join('');
}

// ─── Conversations ───────────────────────────────────────────────────
async function loadConversations() {
    try {
        const res = await fetch(`${API_BASE}/api/conversations`);
        const data = await res.json();
        state.conversations = data.conversations || [];
        renderConversationList();
    } catch (e) {
        console.error('Failed to load conversations:', e);
    }
}

function renderConversationList(filter = '') {
    const list = els.conversationList;
    const filtered = filter
        ? state.conversations.filter(c =>
            c.title.toLowerCase().includes(filter.toLowerCase()))
        : state.conversations;

    if (filtered.length === 0) {
        list.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 13px;">
            ${filter ? 'No matching conversations' : 'No conversations yet'}
        </div>`;
        return;
    }

    list.innerHTML = filtered.map(conv => `
        <div class="conversation-item ${conv.id === state.currentConvId ? 'active' : ''}"
             data-id="${conv.id}">
            <span class="conv-icon">💬</span>
            <span class="conv-title">${escapeHtml(conv.title)}</span>
            <button class="conv-delete" data-id="${conv.id}" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        </div>
    `).join('');

    // Click handlers
    list.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.closest('.conv-delete')) return;
            openConversation(item.dataset.id);
        });
    });

    list.querySelectorAll('.conv-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            await deleteConversation(btn.dataset.id);
        });
    });
}

async function createConversation() {
    try {
        const res = await fetch(`${API_BASE}/api/conversations`, { method: 'POST' });
        const conv = await res.json();
        state.conversations.unshift({
            id: conv.id,
            title: conv.title,
            message_count: 0,
        });
        renderConversationList();
        openConversation(conv.id);
        return conv.id;
    } catch (e) {
        console.error('Failed to create conversation:', e);
        return null;
    }
}

async function openConversation(convId) {
    state.currentConvId = convId;

    // Close WebSocket if open
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }

    // Show chat screen
    els.welcomeScreen.classList.add('hidden');
    els.chatScreen.classList.remove('hidden');

    // Load messages
    try {
        const res = await fetch(`${API_BASE}/api/conversations/${convId}`);
        const conv = await res.json();
        els.chatTitle.textContent = conv.title || 'New Chat';

        // Render existing messages
        els.messagesContainer.innerHTML = '';
        for (const msg of conv.messages || []) {
            if (msg.role === 'user') {
                appendMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                appendMessage('assistant', msg.content);
            } else if (msg.role === 'tool') {
                const toolCalls = msg.tool_calls || [];
                if (toolCalls.length > 0) {
                    appendToolResult(toolCalls[0].name, JSON.parse(msg.content));
                }
            }
        }

        scrollToBottom();
    } catch (e) {
        console.error('Failed to load conversation:', e);
    }

    // Connect WebSocket
    connectWebSocket(convId);

    // Update active state
    renderConversationList();

    // Close mobile sidebar
    els.sidebar.classList.remove('open');
}

async function deleteConversation(convId) {
    try {
        await fetch(`${API_BASE}/api/conversations/${convId}`, { method: 'DELETE' });
        state.conversations = state.conversations.filter(c => c.id !== convId);

        if (state.currentConvId === convId) {
            state.currentConvId = null;
            els.welcomeScreen.classList.remove('hidden');
            els.chatScreen.classList.add('hidden');
        }

        renderConversationList();
    } catch (e) {
        console.error('Failed to delete conversation:', e);
    }
}

// ─── WebSocket ───────────────────────────────────────────────────────
function connectWebSocket(convId) {
    const ws = new WebSocket(`${WS_BASE}/ws/chat/${convId}`);

    ws.onopen = () => {
        console.log('🐙 WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleStreamEvent(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };

    state.ws = ws;
}

// ─── Stream Event Handler ────────────────────────────────────────────
let currentAssistantEl = null;
let currentAssistantText = '';

function handleStreamEvent(event) {
    switch (event.type) {
        case 'text':
            if (!currentAssistantEl) {
                currentAssistantEl = appendMessage('assistant', '', true);
                currentAssistantText = '';
            }
            currentAssistantText += event.content;
            updateMessageContent(currentAssistantEl, currentAssistantText);
            scrollToBottom();
            break;

        case 'tool_start':
            appendToolCall(event.tool, event.arguments, event.id);
            scrollToBottom();
            break;

        case 'tool_result':
            updateToolResult(event.id, event.result);
            scrollToBottom();
            break;

        case 'error':
            if (!currentAssistantEl) {
                currentAssistantEl = appendMessage('assistant', '', true);
                currentAssistantText = '';
            }
            currentAssistantText += `\n\n⚠️ **Error:** ${event.content}`;
            updateMessageContent(currentAssistantEl, currentAssistantText);
            scrollToBottom();
            break;

        case 'done':
            state.isStreaming = false;
            currentAssistantEl = null;
            currentAssistantText = '';
            els.sendBtn.disabled = false;
            els.messageInput.disabled = false;
            els.messageInput.focus();

            // Remove typing indicator
            const typing = els.messagesContainer.querySelector('.typing-indicator-wrapper');
            if (typing) typing.remove();

            // Reload conversation list (titles may have changed)
            loadConversations();
            break;
    }
}

// ─── Message Rendering ──────────────────────────────────────────────
function appendMessage(role, content, isStreaming = false) {
    const avatar = role === 'user' ? '👤' : '🐙';
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${
            isStreaming ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' :
            renderMarkdown(content)
        }</div>
    `;
    els.messagesContainer.appendChild(div);
    return div;
}

function updateMessageContent(el, text) {
    const contentEl = el.querySelector('.message-content');
    if (contentEl) {
        contentEl.innerHTML = renderMarkdown(text);
    }
}

function appendToolCall(toolName, args, id) {
    const toolIcons = {
        shell_execute: '🐚',
        file_operations: '📁',
        web_browse: '🌐',
        code_execute: '💻',
        search_web: '🔍',
    };

    const icon = toolIcons[toolName] || '🦑';
    const argsStr = JSON.stringify(args, null, 2);

    const div = document.createElement('div');
    div.className = 'tool-call';
    div.id = `tool-${id}`;
    div.innerHTML = `
        <div class="tool-call-header" onclick="this.nextElementSibling.classList.toggle('expanded')">
            <span class="tool-icon">${icon}</span>
            <span class="tool-name">${toolName.replace('_', ' ')}</span>
            <span class="tool-status running">Running...</span>
        </div>
        <div class="tool-call-body">
            <strong>Arguments:</strong>\n${argsStr}\n\n<strong>Result:</strong>\nWaiting...
        </div>
    `;
    els.messagesContainer.appendChild(div);
}

function updateToolResult(id, result) {
    const toolEl = document.getElementById(`tool-${id}`);
    if (!toolEl) return;

    const status = toolEl.querySelector('.tool-status');
    const body = toolEl.querySelector('.tool-call-body');
    const icon = toolEl.querySelector('.tool-icon');

    const isSuccess = result.status === 'success';
    status.className = `tool-status ${isSuccess ? 'success' : 'error'}`;
    status.textContent = isSuccess ? 'Complete' : 'Error';
    icon.classList.add('done');

    // Update body with result
    const resultStr = JSON.stringify(result, null, 2);
    const existingContent = body.innerHTML.split('<strong>Result:</strong>')[0];
    body.innerHTML = existingContent + `<strong>Result:</strong>\n${escapeHtml(resultStr)}`;
    body.classList.add('expanded');
}

// ─── Markdown Rendering ─────────────────────────────────────────────
function renderMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Links
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Unordered lists
    html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph if not already wrapped
    if (!html.startsWith('<')) {
        html = `<p>${html}</p>`;
    }

    return html;
}

// ─── Send Message ────────────────────────────────────────────────────
async function sendMessage() {
    const text = els.messageInput.value.trim();
    if (!text || state.isStreaming) return;

    // Create conversation if needed
    if (!state.currentConvId) {
        const convId = await createConversation();
        if (!convId) return;
    }

    // If WebSocket isn't connected, reconnect
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        connectWebSocket(state.currentConvId);
        await new Promise(resolve => {
            const check = () => {
                if (state.ws.readyState === WebSocket.OPEN) resolve();
                else setTimeout(check, 100);
            };
            check();
        });
    }

    // Add user message to UI
    appendMessage('user', text);
    els.messageInput.value = '';
    els.messageInput.style.height = 'auto';
    scrollToBottom();

    // Send via WebSocket
    state.isStreaming = true;
    els.sendBtn.disabled = true;
    els.messageInput.disabled = true;

    state.ws.send(JSON.stringify({ content: text }));
}

// ─── Event Listeners ─────────────────────────────────────────────────
function setupEventListeners() {
    // Send message
    els.sendBtn.addEventListener('click', sendMessage);
    els.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // New chat
    els.newChatBtn.addEventListener('click', async () => {
        await createConversation();
    });

    // Settings
    els.settingsBtn.addEventListener('click', () => {
        els.settingsModal.classList.remove('hidden');
    });

    els.closeSettings.addEventListener('click', () => {
        els.settingsModal.classList.add('hidden');
    });

    // Close modal on overlay click
    els.settingsModal.querySelector('.modal-overlay').addEventListener('click', () => {
        els.settingsModal.classList.add('hidden');
    });

    // Provider change
    $$('input[name="provider"]').forEach(radio => {
        radio.addEventListener('change', async (e) => {
            const provider = e.target.value;
            updateModelOptions(provider);
            const model = els.modelSelect.value;
            await saveConfigValue('llm_provider', provider);
            await saveConfigValue('model', model);
            state.config.llm_provider = provider;
            state.config.model = model;
            els.modelBadge.textContent = model;
        });
    });

    // Model change
    els.modelSelect.addEventListener('change', async (e) => {
        const model = e.target.value;
        await saveConfigValue('model', model);
        state.config.model = model;
        els.modelBadge.textContent = model;
    });

    // Temperature
    els.temperature.addEventListener('input', (e) => {
        els.tempValue.textContent = e.target.value;
    });

    els.temperature.addEventListener('change', async (e) => {
        await saveConfigValue('temperature', parseFloat(e.target.value));
    });

    // API key save buttons
    $$('.btn-save-key').forEach(btn => {
        btn.addEventListener('click', async () => {
            const provider = btn.dataset.provider;
            const input = $(`#${provider}-key`);
            const key = input.value.trim();

            if (!key) return;

            try {
                await fetch(`${API_BASE}/api/config/apikey`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider, key }),
                });
                btn.textContent = '✓ Saved';
                btn.style.background = 'var(--tentacle-green)';
                setTimeout(() => {
                    btn.textContent = 'Save';
                    btn.style.background = '';
                }, 2000);
            } catch (e) {
                btn.textContent = '✗ Error';
                setTimeout(() => { btn.textContent = 'Save'; }, 2000);
            }
        });
    });

    // Tool toggles
    $$('.tool-toggle input').forEach(toggle => {
        toggle.addEventListener('change', async () => {
            const tools = {};
            $$('.tool-toggle input').forEach(t => {
                const name = t.id.replace('tool-', '');
                tools[name] = t.checked;
            });
            await saveConfigValue('tools_enabled', tools);
        });
    });

    // Search conversations
    els.searchConversations.addEventListener('input', (e) => {
        renderConversationList(e.target.value);
    });

    // Mobile sidebar toggle
    if (els.toggleSidebar) {
        els.toggleSidebar.addEventListener('click', () => {
            els.sidebar.classList.toggle('open');
        });
    }

    // Capability cards (quick prompts)
    $$('.capability-card').forEach(card => {
        card.addEventListener('click', async () => {
            const prompt = card.dataset.prompt;
            if (!state.currentConvId) {
                await createConversation();
            }
            els.messageInput.value = prompt;
            sendMessage();
        });
    });

    // Initialize Google Auth Listeners
    setupGoogleEventListeners();
}

// ─── Textarea Auto-resize ────────────────────────────────────────────
function setupTextareaAutoResize() {
    els.messageInput.addEventListener('input', () => {
        els.messageInput.style.height = 'auto';
        els.messageInput.style.height = Math.min(els.messageInput.scrollHeight, 200) + 'px';
    });
}

// ─── Utilities ───────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        els.messagesContainer.scrollTop = els.messagesContainer.scrollHeight;
    });
}

// ─── Google Sign-In ──────────────────────────────────────────────────
let googleTokenClient = null;

function initGoogleSignIn() {
    const clientId = state.config.google_client_id || localStorage.getItem('google_client_id') || '';
    if (els.googleClientId) {
        els.googleClientId.value = clientId;
    }

    if (!clientId) return;

    // Wait for Google Identity Services to load
    const initInterval = setInterval(() => {
        if (typeof google !== 'undefined' && google.accounts && google.accounts.oauth2) {
            clearInterval(initInterval);
            setupGoogleTokenClient(clientId);
        }
    }, 200);

    // Give up after 10s
    setTimeout(() => clearInterval(initInterval), 10000);
}

function setupGoogleTokenClient(clientId) {
    try {
        googleTokenClient = google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: 'https://www.googleapis.com/auth/generative-language openid profile email',
            callback: handleGoogleTokenResponse,
        });
        console.log('🔑 Google token client initialized');
    } catch (e) {
        console.error('Failed to init Google token client:', e);
    }
}

function handleGoogleTokenResponse(tokenResponse) {
    if (tokenResponse.error) {
        console.error('Google auth error:', tokenResponse.error);
        return;
    }

    const accessToken = tokenResponse.access_token;

    // Fetch user info from Google
    fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
        headers: { Authorization: `Bearer ${accessToken}` },
    })
    .then(res => res.json())
    .then(async (userInfo) => {
        // Send token to backend
        const res = await fetch(`${API_BASE}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                access_token: accessToken,
                name: userInfo.name || userInfo.email || 'Google User',
                email: userInfo.email || '',
            }),
        });
        const result = await res.json();

        if (result.status === 'authenticated') {
            // Update UI to show signed-in state
            showGoogleSignedIn(userInfo.name || userInfo.email, userInfo.picture || '');

            // Auto-switch to Gemini provider
            const geminiRadio = $('input[name="provider"][value="gemini"]');
            if (geminiRadio) geminiRadio.checked = true;
            updateModelOptions('gemini');
            const model = els.modelSelect.value;
            state.config.llm_provider = 'gemini';
            state.config.model = model;
            els.modelBadge.textContent = model;

            // Update auth status in settings
            updateAuthStatus(true, userInfo.name || userInfo.email);
        }
    })
    .catch(err => console.error('Failed to get user info:', err));
}

function showGoogleSignedIn(name, avatarUrl) {
    els.googleSigninArea.classList.add('hidden');
    els.googleUserArea.classList.remove('hidden');
    els.googleUserName.textContent = name;
    if (avatarUrl) {
        els.googleUserAvatar.src = avatarUrl;
        els.googleUserAvatar.style.display = '';
    } else {
        els.googleUserAvatar.style.display = 'none';
    }
}

function showGoogleSignedOut() {
    els.googleSigninArea.classList.remove('hidden');
    els.googleUserArea.classList.add('hidden');
    els.googleUserName.textContent = '';
    els.googleUserAvatar.src = '';
    updateAuthStatus(false);
}

function updateAuthStatus(connected, userName = '') {
    if (els.authStatusText) {
        els.authStatusText.textContent = connected
            ? `✅ Signed in as ${userName}`
            : 'Not signed in';
    }
    if (els.googleAuthStatus) {
        els.googleAuthStatus.classList.toggle('connected', connected);
    }
}

async function checkGoogleAuthStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/google/status`);
        const data = await res.json();
        if (data.authenticated) {
            showGoogleSignedIn(data.user_name, '');
            updateAuthStatus(true, data.user_name);
        }
    } catch (e) {
        console.error('Failed to check Google auth status:', e);
    }
}

// Google Sign-In event listeners (appended in setupEventListeners)
function setupGoogleEventListeners() {
    // Sign-In button
    if (els.googleSigninBtn) {
        els.googleSigninBtn.addEventListener('click', () => {
            if (!googleTokenClient) {
                const clientId = state.config.google_client_id || localStorage.getItem('google_client_id') || '';
                if (!clientId) {
                    alert('Please set your Google OAuth Client ID in Settings first.');
                    els.settingsModal.classList.remove('hidden');
                    return;
                }
                setupGoogleTokenClient(clientId);
            }
            if (googleTokenClient) {
                googleTokenClient.requestAccessToken();
            }
        });
    }

    // Sign-Out button
    if (els.googleSignoutBtn) {
        els.googleSignoutBtn.addEventListener('click', async () => {
            try {
                await fetch(`${API_BASE}/api/auth/google/signout`, { method: 'POST' });
                // Revoke Google token
                if (typeof google !== 'undefined' && google.accounts && google.accounts.oauth2) {
                    google.accounts.oauth2.revoke(state.config.google_oauth?.access_token);
                }
                showGoogleSignedOut();
            } catch (e) {
                console.error('Sign out failed:', e);
            }
        });
    }

    // Save Client ID button
    if (els.saveClientId) {
        els.saveClientId.addEventListener('click', async () => {
            const clientId = els.googleClientId.value.trim();
            if (!clientId) return;

            try {
                await fetch(`${API_BASE}/api/config/google-client-id`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id: clientId }),
                });
                localStorage.setItem('google_client_id', clientId);
                state.config.google_client_id = clientId;

                // Re-init Google Sign-In with new client ID
                setupGoogleTokenClient(clientId);

                els.saveClientId.textContent = '✓ Saved';
                els.saveClientId.style.background = 'var(--tentacle-green)';
                setTimeout(() => {
                    els.saveClientId.textContent = 'Save';
                    els.saveClientId.style.background = '';
                }, 2000);
            } catch (e) {
                els.saveClientId.textContent = '✗ Error';
                setTimeout(() => { els.saveClientId.textContent = 'Save'; }, 2000);
            }
        });
    }
}
