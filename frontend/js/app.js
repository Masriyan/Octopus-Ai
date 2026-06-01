/**
 * Octopus AI — Main Application 🐙 v2.0
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
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
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
    stopBtn: $('#stop-btn'),
    newChatBtn: $('#new-chat-btn'),
    conversationList: $('#conversation-list'),
    settingsBtn: $('#settings-btn'),
    settingsModal: $('#settings-modal'),
    closeSettings: $('#close-settings'),
    modelSelect: $('#model-select'),
    headerProvider: $('#header-provider'),
    headerModel: $('#header-model'),
    refreshModels: $('#refresh-models'),
    activityPanel: $('#activity-panel'),
    activityToggle: $('#activity-toggle'),
    activityClose: $('#activity-close'),
    activityPlan: $('#activity-plan'),
    activityTimeline: $('#activity-timeline'),
    toolModeSelect: $('#tool-mode-select'),
    ollamaBaseUrl: $('#ollama-base-url'),
    localBaseUrl: $('#local-base-url'),
    localApiKey: $('#local-api-key'),
    localModel: $('#local-model'),
    searchConversations: $('#search-conversations'),
    toggleSidebar: $('#toggle-sidebar'),
    sidebar: $('#sidebar'),
    temperature: $('#temperature'),
    tempValue: $('#temp-value'),
    exportBtn: $('#export-btn'),
    fileUploadInput: $('#file-upload-input'),
    themeToggleBtn: $('#theme-toggle-btn'),
    themeIcon: $('#theme-icon'),
    themeLabel: $('#theme-label'),
    systemPromptInput: $('#system-prompt-input'),
    saveSystemPrompt: $('#save-system-prompt'),
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
    initTheme();
    await loadConfig();
    await loadConversations();
    await checkGoogleAuthStatus();
    await loadSystemPrompt();
    setupEventListeners();
    setupTextareaAutoResize();
    setupKeyboardShortcuts();
    initGoogleSignIn();
});

// ─── Toast Notification System ───────────────────────────────────────
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => toast.classList.add('show'));

    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, duration);
}

// ─── Theme Management ────────────────────────────────────────────────
function initTheme() {
    const saved = localStorage.getItem('octopus-theme') || 'dark';
    applyTheme(saved);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('octopus-theme', theme);

    // Toggle highlight.js stylesheets
    const darkSheet = document.getElementById('hljs-theme-dark');
    const lightSheet = document.getElementById('hljs-theme-light');
    if (darkSheet && lightSheet) {
        darkSheet.disabled = theme === 'light';
        lightSheet.disabled = theme === 'dark';
    }

    if (els.themeIcon) els.themeIcon.textContent = theme === 'dark' ? '🌙' : '☀️';
    if (els.themeLabel) els.themeLabel.textContent = theme === 'dark' ? 'Dark Mode' : 'Light Mode';
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

// ─── Config ──────────────────────────────────────────────────────────
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/api/config`);
        state.config = await res.json();
        await applyConfig();
    } catch (e) {
        console.error('Failed to load config:', e);
        state.config = { llm_provider: 'openai', model: 'gpt-4o-mini', temperature: 0.7 };
        showToast('Failed to connect to backend', 'error');
    }
}

async function applyConfig() {
    const { llm_provider, model, temperature, tools_enabled, tool_mode } = state.config;

    // Provider (settings radio + header switcher)
    const radio = $(`input[name="provider"][value="${llm_provider}"]`);
    if (radio) radio.checked = true;
    if (els.headerProvider) els.headerProvider.value = llm_provider || 'openai';

    // Models — populates both the header switcher and the settings select
    await populateModelSelects(llm_provider, model);

    // Tool-calling mode
    if (els.toolModeSelect) els.toolModeSelect.value = tool_mode || 'auto';

    // Local runtime fields
    if (els.ollamaBaseUrl) els.ollamaBaseUrl.value = state.config.ollama_base_url || '';
    if (els.localBaseUrl) els.localBaseUrl.value = state.config.local_openai_base_url || '';
    if (els.localApiKey) els.localApiKey.value = state.config.local_openai_api_key || '';
    if (els.localModel) els.localModel.value = state.config.local_openai_model || '';

    // Temperature
    if (els.temperature) {
        els.temperature.value = temperature ?? 0.7;
        els.tempValue.textContent = temperature ?? 0.7;
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
        showToast('Failed to save setting', 'error');
    }
}

const STATIC_MODELS = {
    openai: [
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
        { value: 'gpt-4o', label: 'GPT-4o' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    ],
    anthropic: [
        { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
        { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
        { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    ],
    gemini: [
        { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
        { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro' },
        { value: 'gemini-3.1-flash-lite-preview', label: 'Gemini 3.1 Flash Lite' },
        { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
        { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    ],
};

// Discover models for a provider. Local runtimes (ollama/local) are queried
// live so you always see what's actually installed/loaded.
async function getModelsFor(provider) {
    if (provider === 'ollama' || provider === 'local') {
        try {
            const res = await fetch(`${API_BASE}/api/models/${provider}`);
            const data = await res.json();
            const models = (data.models || []).map(m => ({ value: m, label: m }));
            if (models.length) return models;
        } catch (e) { /* endpoint offline */ }
        if (provider === 'ollama') {
            return [{ value: 'llama3.2', label: 'llama3.2 (Ollama offline?)' }];
        }
        const lm = state.config.local_openai_model || 'local-model';
        return [{ value: lm, label: `${lm} (server offline?)` }];
    }
    return STATIC_MODELS[provider] || STATIC_MODELS.openai;
}

// Populate both the header switcher and the settings model <select>.
async function populateModelSelects(provider, selected) {
    const models = await getModelsFor(provider);
    const opts = models
        .map(m => `<option value="${escapeHtml(m.value)}">${escapeHtml(m.label)}</option>`)
        .join('');
    if (els.modelSelect) els.modelSelect.innerHTML = opts;
    if (els.headerModel) els.headerModel.innerHTML = opts;
    const valid = selected && models.some(m => m.value === selected);
    const value = valid ? selected : (models[0]?.value || '');
    if (els.modelSelect) els.modelSelect.value = value;
    if (els.headerModel) els.headerModel.value = value;
    return value;
}

// Switch provider everywhere (header + settings radio) and persist.
async function setProvider(provider) {
    if (els.headerProvider) els.headerProvider.value = provider;
    const radio = $(`input[name="provider"][value="${provider}"]`);
    if (radio) radio.checked = true;
    const model = await populateModelSelects(provider, state.config.model);
    state.config.llm_provider = provider;
    state.config.model = model;
    await saveConfigValue('llm_provider', provider);
    await saveConfigValue('model', model);
}

async function setModel(model) {
    if (els.headerModel) els.headerModel.value = model;
    if (els.modelSelect) els.modelSelect.value = model;
    state.config.model = model;
    await saveConfigValue('model', model);
}

// ─── System Prompt ───────────────────────────────────────────────────
async function loadSystemPrompt() {
    try {
        const res = await fetch(`${API_BASE}/api/config/system-prompt`);
        const data = await res.json();
        if (els.systemPromptInput && data.system_prompt) {
            els.systemPromptInput.value = data.system_prompt;
        }
    } catch (e) {
        console.error('Failed to load system prompt:', e);
    }
}

async function saveSystemPrompt() {
    const prompt = els.systemPromptInput?.value || '';
    try {
        await fetch(`${API_BASE}/api/config/system-prompt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ system_prompt: prompt }),
        });
        showToast('System prompt saved', 'success');
    } catch (e) {
        showToast('Failed to save system prompt', 'error');
    }
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
            <span class="conv-title" data-id="${conv.id}">${escapeHtml(conv.title)}</span>
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

    // Double-click to rename
    list.querySelectorAll('.conv-title').forEach(titleEl => {
        titleEl.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            startInlineRename(titleEl);
        });
    });
}

function startInlineRename(titleEl) {
    const convId = titleEl.dataset.id;
    const oldTitle = titleEl.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldTitle;
    input.className = 'conv-rename-input';
    input.style.cssText = 'width:100%;background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--accent);border-radius:4px;padding:2px 6px;font-size:13px;';

    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = async () => {
        const newTitle = input.value.trim() || oldTitle;
        if (newTitle !== oldTitle) {
            try {
                await fetch(`${API_BASE}/api/conversations/${convId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: newTitle }),
                });
                // Update local state
                const conv = state.conversations.find(c => c.id === convId);
                if (conv) conv.title = newTitle;
                if (state.currentConvId === convId) {
                    els.chatTitle.textContent = newTitle;
                }
                showToast('Conversation renamed', 'success');
            } catch (e) {
                showToast('Failed to rename', 'error');
            }
        }
        renderConversationList();
    };

    input.addEventListener('blur', finish);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
        if (e.key === 'Escape') { input.value = oldTitle; input.blur(); }
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
        showToast('Failed to create conversation', 'error');
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
                appendMessage('user', msg.content, false, msg.timestamp);
            } else if (msg.role === 'assistant') {
                appendMessage('assistant', msg.content, false, msg.timestamp);
            } else if (msg.role === 'tool') {
                const toolCalls = msg.tool_calls || [];
                if (toolCalls.length > 0) {
                    try {
                        appendToolResult(toolCalls[0].name, JSON.parse(msg.content));
                    } catch (e) {
                        // Skip malformed tool results
                    }
                }
            }
        }

        scrollToBottom();
    } catch (e) {
        console.error('Failed to load conversation:', e);
        showToast('Failed to load conversation', 'error');
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
        showToast('Conversation deleted', 'info');
    } catch (e) {
        console.error('Failed to delete conversation:', e);
        showToast('Failed to delete', 'error');
    }
}

// ─── Export ──────────────────────────────────────────────────────────
async function exportConversation(format = 'json') {
    if (!state.currentConvId) return;
    try {
        const res = await fetch(`${API_BASE}/api/conversations/${state.currentConvId}/export?format=${format}`);
        const blob = await res.blob();
        const ext = format === 'markdown' ? 'md' : 'json';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation_${state.currentConvId}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
        showToast(`Exported as ${format.toUpperCase()}`, 'success');
    } catch (e) {
        showToast('Export failed', 'error');
    }
}

// ─── File Upload ─────────────────────────────────────────────────────
async function handleFileUpload(file) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
        showToast('File too large (max 10MB)', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (data.status === 'uploaded') {
            showToast(`Uploaded: ${data.filename}`, 'success');
            // Auto-insert a reference to the uploaded file in the message input
            const current = els.messageInput.value;
            const prefix = current ? current + '\n' : '';
            els.messageInput.value = prefix + `I've uploaded a file: ${data.path} (${formatBytes(data.size)}). Please analyze it.`;
            els.messageInput.focus();
            els.messageInput.dispatchEvent(new Event('input'));
        }
    } catch (e) {
        showToast('Upload failed', 'error');
    }
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ─── WebSocket ───────────────────────────────────────────────────────
function connectWebSocket(convId) {
    const ws = new WebSocket(`${WS_BASE}/ws/chat/${convId}`);

    ws.onopen = () => {
        console.log('🐙 WebSocket connected');
        state.reconnectAttempts = 0;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleStreamEvent(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = (event) => {
        console.log('WebSocket disconnected');
        // Auto-reconnect with exponential backoff
        if (state.currentConvId === convId && state.reconnectAttempts < state.maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 30000);
            state.reconnectAttempts++;
            console.log(`Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts})...`);
            setTimeout(() => {
                if (state.currentConvId === convId) {
                    connectWebSocket(convId);
                }
            }, delay);
        }
    };

    state.ws = ws;
}

function stopStreaming() {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: 'stop' }));
    }
    state.isStreaming = false;
    els.sendBtn.classList.remove('hidden');
    els.stopBtn.classList.add('hidden');
    els.messageInput.disabled = false;
    els.messageInput.focus();
}

// ─── Stream Event Handler ────────────────────────────────────────────
let currentAssistantEl = null;
let currentAssistantText = '';

let renderScheduled = false;
function scheduleRender() {
    if (renderScheduled) return;
    renderScheduled = true;
    requestAnimationFrame(() => {
        renderScheduled = false;
        if (currentAssistantEl) updateMessageContent(currentAssistantEl, currentAssistantText);
    });
}

function handleStreamEvent(event) {
    switch (event.type) {
        case 'text':
            if (!currentAssistantEl) {
                currentAssistantEl = appendMessage('assistant', '', true);
                currentAssistantText = '';
            }
            currentAssistantText += event.content;
            scheduleRender();              // coalesce re-renders (avoids O(n²) reparsing)
            scrollToBottom();
            break;

        case 'tool_start':
            appendToolCall(event.tool, event.arguments, event.id);
            addTimelineItem(event.tool, event.id);
            scrollToBottom();
            break;

        case 'tool_result':
            updateToolResult(event.id, event.result);
            updateTimelineItem(event.id, event.result && event.result.status);
            scrollToBottom();
            break;

        case 'plan':
            renderPlan(event.steps);
            break;

        case 'error':
            if (!currentAssistantEl) {
                currentAssistantEl = appendMessage('assistant', '', true);
                currentAssistantText = '';
            }
            currentAssistantText += `\n\n⚠️ **Error:** ${event.content}`;
            updateMessageContent(currentAssistantEl, currentAssistantText);
            showToast(event.content, 'error');
            scrollToBottom();
            break;

        case 'done':
            if (currentAssistantEl) {
                updateMessageContent(currentAssistantEl, currentAssistantText);
                finalizeMessage(currentAssistantEl);
            }
            state.isStreaming = false;
            currentAssistantEl = null;
            currentAssistantText = '';
            els.sendBtn.classList.remove('hidden');
            els.stopBtn.classList.add('hidden');
            els.sendBtn.disabled = false;
            els.messageInput.disabled = false;
            els.messageInput.focus();

            const typing = els.messagesContainer.querySelector('.typing-indicator-wrapper');
            if (typing) typing.remove();

            loadConversations();
            break;
    }
}

// ─── Agent Activity Panel ────────────────────────────────────────────────
const TOOL_ICONS = {
    shell_execute: '🐚', file_operations: '📁', web_browse: '🌐',
    code_execute: '💻', search_web: '🔍', image_generate: '🎨',
    update_plan: '🗺️', delegate_task: '🤝',
};

function openActivityPanel() {
    if (els.activityPanel) els.activityPanel.classList.add('open');
}

function renderPlan(steps) {
    if (!els.activityPlan || !Array.isArray(steps)) return;
    openActivityPanel();
    if (!steps.length) {
        els.activityPlan.innerHTML = '<li class="activity-empty">No active plan yet.</li>';
        return;
    }
    const marker = { pending: '○', in_progress: '◐', done: '●' };
    els.activityPlan.innerHTML = steps.map(s => `
        <li class="plan-item plan-${s.status || 'pending'}">
            <span class="plan-marker">${marker[s.status] || '○'}</span>
            <span class="plan-text">${escapeHtml(s.title || '')}</span>
        </li>`).join('');
}

function clearActivity() {
    if (els.activityTimeline)
        els.activityTimeline.innerHTML = '<div class="activity-empty">Tool activity will appear here.</div>';
}

function addTimelineItem(tool, id) {
    if (!els.activityTimeline) return;
    const empty = els.activityTimeline.querySelector('.activity-empty');
    if (empty) empty.remove();
    const item = document.createElement('div');
    item.className = 'timeline-item running';
    item.id = `tl-${id}`;
    item.innerHTML =
        `<span class="tl-icon">${TOOL_ICONS[tool] || '🦑'}</span>` +
        `<span class="tl-name">${escapeHtml((tool || '').replace(/_/g, ' '))}</span>` +
        `<span class="tl-status">running</span>`;
    els.activityTimeline.appendChild(item);
    openActivityPanel();
}

function updateTimelineItem(id, status) {
    const item = document.getElementById(`tl-${id}`);
    if (!item) return;
    const ok = status === 'success';
    item.className = `timeline-item ${ok ? 'done' : 'failed'}`;
    const st = item.querySelector('.tl-status');
    if (st) st.textContent = ok ? 'done' : (status || 'error');
}

// ─── Message Rendering ──────────────────────────────────────────────
function appendMessage(role, content, isStreaming = false, timestamp = null) {
    const avatar = role === 'user' ? '👤' : '🐙';
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const timeStr = timestamp ? formatTimestamp(timestamp) : '';
    const timeHtml = timeStr ? `<span class="message-time">${timeStr}</span>` : '';

    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-body">
            <div class="message-content">${
                isStreaming ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' :
                renderMarkdown(content)
            }</div>
            ${timeHtml}
        </div>
    `;
    els.messagesContainer.appendChild(div);
    if (!isStreaming && content) finalizeMessage(div);
    return div;
}

function formatTimestamp(ts) {
    const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
    if (isNaN(date.getTime())) return '';
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return date.toLocaleDateString();
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
        image_generate: '🎨',
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
    let raw;
    try {
        raw = window.marked
            ? marked.parse(text, { breaks: true, gfm: true })
            : '<p>' + escapeHtml(text).replace(/\n/g, '<br>') + '</p>';
    } catch (e) {
        raw = '<p>' + escapeHtml(text).replace(/\n/g, '<br>') + '</p>';
    }
    return window.DOMPurify
        ? DOMPurify.sanitize(raw, { ADD_ATTR: ['target', 'rel'] })
        : raw;
}

// Decorate code blocks (language header + copy button) and syntax-highlight.
// Run once a message is complete, not on every streamed token.
function enhanceCodeBlocks(container) {
    if (!container) return;
    container.querySelectorAll('pre > code').forEach(code => {
        const pre = code.parentElement;
        const alreadyWrapped = pre.parentElement &&
            pre.parentElement.classList.contains('code-block-wrapper');
        if (!alreadyWrapped) {
            const langMatch = (code.className || '').match(/language-([\w-]+)/);
            const lang = langMatch ? langMatch[1] : 'code';
            const id = 'code-' + Math.random().toString(36).slice(2, 11);
            code.id = id;
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            const header = document.createElement('div');
            header.className = 'code-block-header';
            header.innerHTML =
                `<span class="code-lang">${escapeHtml(lang)}</span>` +
                `<button class="btn-copy-code" data-code-id="${id}" onclick="copyCodeBlock('${id}')" title="Copy">` +
                `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">` +
                `<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>` +
                `<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy</button>`;
            pre.parentElement.insertBefore(wrapper, pre);
            wrapper.appendChild(header);
            wrapper.appendChild(pre);
        }
        if (typeof hljs !== 'undefined' && !code.dataset.highlighted) {
            try { hljs.highlightElement(code); code.dataset.highlighted = 'true'; } catch (e) {}
        }
    });
    container.querySelectorAll('a[href]').forEach(a => {
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener noreferrer');
    });
}

function finalizeMessage(el) {
    const contentEl = el && el.querySelector('.message-content');
    if (contentEl) enhanceCodeBlocks(contentEl);
}

// Global function for copy code button onclick
window.copyCodeBlock = function(id) {
    const codeEl = document.getElementById(id);
    if (!codeEl) return;
    const text = codeEl.textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(`[data-code-id="${id}"]`);
        if (btn) {
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg> Copied!`;
            setTimeout(() => {
                btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg> Copy`;
            }, 2000);
        }
        showToast('Copied to clipboard', 'success', 1500);
    });
};

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
    appendMessage('user', text, false, Date.now() / 1000);
    els.messageInput.value = '';
    els.messageInput.style.height = 'auto';
    clearActivity();              // fresh tentacle timeline for this turn
    scrollToBottom();

    // Send via WebSocket
    state.isStreaming = true;
    els.sendBtn.classList.add('hidden');
    els.stopBtn.classList.remove('hidden');
    els.messageInput.disabled = true;

    state.ws.send(JSON.stringify({ content: text }));
}

// ─── Keyboard Shortcuts ──────────────────────────────────────────────
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+N / Cmd+N — New chat
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            createConversation();
        }
        // Ctrl+K / Cmd+K — Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            els.searchConversations.focus();
        }
        // Escape — Close modals
        if (e.key === 'Escape') {
            if (!els.settingsModal.classList.contains('hidden')) {
                els.settingsModal.classList.add('hidden');
            }
            if (els.sidebar.classList.contains('open')) {
                els.sidebar.classList.remove('open');
            }
        }
    });
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

    // Stop streaming
    if (els.stopBtn) {
        els.stopBtn.addEventListener('click', stopStreaming);
    }

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

    // Provider change (settings radio + header switcher kept in sync)
    $$('input[name="provider"]').forEach(radio => {
        radio.addEventListener('change', (e) => setProvider(e.target.value));
    });
    els.modelSelect.addEventListener('change', (e) => setModel(e.target.value));

    if (els.headerProvider) {
        els.headerProvider.addEventListener('change', (e) => setProvider(e.target.value));
    }
    if (els.headerModel) {
        els.headerModel.addEventListener('change', (e) => setModel(e.target.value));
    }
    if (els.refreshModels) {
        els.refreshModels.addEventListener('click', async () => {
            const provider = els.headerProvider ? els.headerProvider.value : state.config.llm_provider;
            await populateModelSelects(provider, state.config.model);
            showToast('Models refreshed', 'info', 1500);
        });
    }

    // Agent Activity panel toggle/close
    if (els.activityToggle) {
        els.activityToggle.addEventListener('click', () =>
            els.activityPanel && els.activityPanel.classList.toggle('open'));
    }
    if (els.activityClose) {
        els.activityClose.addEventListener('click', () =>
            els.activityPanel && els.activityPanel.classList.remove('open'));
    }

    // Tool-calling mode
    if (els.toolModeSelect) {
        els.toolModeSelect.addEventListener('change', async (e) => {
            await saveConfigValue('tool_mode', e.target.value);
            state.config.tool_mode = e.target.value;
        });
    }

    // Generic config-key save buttons (local runtime endpoints, etc.)
    $$('[data-config-key]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const key = btn.dataset.configKey;
            const input = $(`#${btn.dataset.configInput}`);
            if (!input) return;
            const value = input.value.trim();
            await saveConfigValue(key, value);
            state.config[key] = value;
            const orig = btn.textContent;
            btn.textContent = '✓ Saved';
            showToast('Saved', 'success', 1200);
            setTimeout(() => { btn.textContent = orig; }, 1500);
        });
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
            if (!provider) return; // Skip non-API-key save buttons
            const input = $(`#${provider}-key`);
            if (!input) return;
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
                showToast(`${provider} API key saved`, 'success');
                setTimeout(() => {
                    btn.textContent = 'Save';
                    btn.style.background = '';
                }, 2000);
            } catch (e) {
                btn.textContent = '✗ Error';
                showToast('Failed to save API key', 'error');
                setTimeout(() => { btn.textContent = 'Save'; }, 2000);
            }
        });
    });

    // System prompt save
    if (els.saveSystemPrompt) {
        els.saveSystemPrompt.addEventListener('click', saveSystemPrompt);
    }

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

    // Export button
    if (els.exportBtn) {
        els.exportBtn.addEventListener('click', () => {
            exportConversation('markdown');
        });
    }

    // File upload
    if (els.fileUploadInput) {
        els.fileUploadInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
                e.target.value = ''; // Reset
            }
        });
    }

    // Theme toggle
    if (els.themeToggleBtn) {
        els.themeToggleBtn.addEventListener('click', toggleTheme);
    }

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
        showToast('Google sign-in failed', 'error');
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

            // Auto-switch to Gemini provider (syncs header + settings + persists)
            await setProvider('gemini');

            // Update auth status in settings
            updateAuthStatus(true, userInfo.name || userInfo.email);
            showToast('Signed in with Google ✅', 'success');
        }
    })
    .catch(err => {
        console.error('Failed to get user info:', err);
        showToast('Google sign-in failed', 'error');
    });
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

// Google Sign-In event listeners
function setupGoogleEventListeners() {
    // Sign-In button
    if (els.googleSigninBtn) {
        els.googleSigninBtn.addEventListener('click', () => {
            if (!googleTokenClient) {
                const clientId = state.config.google_client_id || localStorage.getItem('google_client_id') || '';
                if (!clientId) {
                    showToast('Please set your Google OAuth Client ID in Settings first.', 'warning');
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
                showToast('Signed out from Google', 'info');
            } catch (e) {
                console.error('Sign out failed:', e);
                showToast('Sign out failed', 'error');
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
                showToast('Client ID saved', 'success');
                setTimeout(() => {
                    els.saveClientId.textContent = 'Save';
                    els.saveClientId.style.background = '';
                }, 2000);
            } catch (e) {
                els.saveClientId.textContent = '✗ Error';
                showToast('Failed to save Client ID', 'error');
                setTimeout(() => { els.saveClientId.textContent = 'Save'; }, 2000);
            }
        });
    }
}
