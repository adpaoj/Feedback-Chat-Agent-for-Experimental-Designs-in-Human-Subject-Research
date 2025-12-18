/**
 * ChatAI Main JavaScript
 * Handles chat interactions, conversation management, and UI updates
 */

// ============================================================================
// Global State Variables
// ============================================================================
let currentConversationId = null;
let isStreaming = false;
let streamReader = null; // Store the reader to allow cancellation
let currentAbortController = null; // For aborting fetch requests
let modelChoicesInstance = null; // Store Choices.js instance

// ============================================================================
// Initialization
// ============================================================================
window.onload = function() {
    // Only initialize if we are on the chat page
    if (!document.getElementById('chat-window')) {
        return;
    }

    loadModels();
    loadConversations();
    loadSettings();
    initializeEventListeners();
    autoResizeTextarea();
};

/**
 * Initialize all event listeners for the chat interface
 */
function initializeEventListeners() {
    // Chat form submission
    document.getElementById('chat-form').addEventListener('submit', handleChatSubmit);
    
    // New conversation buttons (desktop and mobile)
    document.getElementById('new-conversation').addEventListener('click', startNewConversation);
    const newConvoMobile = document.getElementById('new-conversation-mobile');
    if (newConvoMobile) {
        newConvoMobile.addEventListener('click', startNewConversation);
    }
    
    // Stop generation button
    document.getElementById('stop-button').addEventListener('click', stopGeneration);
    
    // Settings save buttons
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    const saveSettingsMobile = document.getElementById('save-settings-mobile');
    if (saveSettingsMobile) {
        saveSettingsMobile.addEventListener('click', saveSettings);
    }
    
    // Model selector change
    document.getElementById('model-select').addEventListener('change', handleModelChange);
    const modelSelectMobile = document.getElementById('model-select-mobile');
    if (modelSelectMobile) {
        modelSelectMobile.addEventListener('change', () => {
            // Sync with desktop selector
            document.getElementById('model-select').value = modelSelectMobile.value;
            handleModelChange();
        });
    }
    
    // Message input auto-resize
    const messageInput = document.getElementById('message-input');
    messageInput.addEventListener('input', autoResizeTextarea);
    messageInput.addEventListener('keydown', handleMessageInputKeydown);
    
    // File upload
    const uploadBtn = document.getElementById('upload-btn');
    const fileUpload = document.getElementById('file-upload');
    if (uploadBtn && fileUpload) {
        uploadBtn.addEventListener('click', () => fileUpload.click());
        fileUpload.addEventListener('change', handleFileUpload);
    }
    
    const removeFileBtn = document.getElementById('remove-file');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', clearFilePreview);
    }
}

// ============================================================================
// Conversation Management
// ============================================================================

/**
 * Load all conversations for the current user
 */
function loadConversations() {
    fetch('/get_conversations')
        .then(response => response.json())
        .then(data => {
            const conversationList = document.getElementById('conversation-list');
            const conversationListMobile = document.getElementById('conversation-list-mobile');
            
            conversationList.innerHTML = '';
            if (conversationListMobile) {
                conversationListMobile.innerHTML = '';
            }
            
            data.conversations.forEach(convo => {
                appendConversation(convo, conversationList);
                if (conversationListMobile) {
                    appendConversation(convo, conversationListMobile, true);
                }
            });
        })
        .catch(error => {
            console.error('Error loading conversations:', error);
            showErrorMessage('Failed to load conversations');
        });
}

/**
 * Create and append a conversation item to the list
 */
function appendConversation(convo, container, isMobile = false) {
    // Check if conversation already exists
    if (container.querySelector(`[data-id="${convo.id}"]`)) return;

    const button = document.createElement('button');
    button.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3 border-0 border-bottom';
    button.dataset.id = convo.id;
    
    // Content Container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'd-flex align-items-center text-truncate';
    contentDiv.style.maxWidth = '85%';

    // Icon
    const icon = document.createElement('i');
    icon.className = 'bi bi-chat-left-text me-3 text-secondary';
    contentDiv.appendChild(icon);

    // Text Info
    const textDiv = document.createElement('div');
    textDiv.className = 'd-flex flex-column text-truncate';

    const titleSpan = document.createElement('span');
    titleSpan.className = 'fw-medium text-truncate';
    titleSpan.textContent = convo.title || `Conversation ${convo.id}`;
    textDiv.appendChild(titleSpan);

    if (convo.created_at) {
        const dateSmall = document.createElement('small');
        dateSmall.className = 'text-muted';
        dateSmall.style.fontSize = '0.75rem';
        dateSmall.textContent = convo.created_at;
        textDiv.appendChild(dateSmall);
    }

    contentDiv.appendChild(textDiv);
    button.appendChild(contentDiv);

    // Load conversation on click
    button.addEventListener('click', () => {
        // Highlight active conversation
        container.querySelectorAll('.list-group-item').forEach(item => {
            item.classList.remove('active', 'bg-light');
        });
        button.classList.add('active');
        
        // Also sync highlighting in other container if mobile
        if (isMobile) {
            const desktopList = document.getElementById('conversation-list');
            desktopList.querySelectorAll('.list-group-item').forEach(item => {
                if (item.dataset.id === convo.id) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active', 'bg-light');
                }
            });
            // Close offcanvas on mobile
            const offcanvas = bootstrap.Offcanvas.getInstance(document.getElementById('sidebarOffcanvas'));
            if (offcanvas) offcanvas.hide();
        } else {
            const mobileList = document.getElementById('conversation-list-mobile');
            if (mobileList) {
                mobileList.querySelectorAll('.list-group-item').forEach(item => {
                    if (item.dataset.id === convo.id) {
                        item.classList.add('active');
                    } else {
                        item.classList.remove('active', 'bg-light');
                    }
                });
            }
        }
        
        loadConversation(convo.id);
    });

    // Delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-link text-danger p-0 delete-btn opacity-50';
    deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
    deleteBtn.style.textDecoration = 'none';
    deleteBtn.title = 'Delete Conversation';
    
    // Hover effect for delete button
    deleteBtn.addEventListener('mouseenter', () => deleteBtn.classList.remove('opacity-50'));
    deleteBtn.addEventListener('mouseleave', () => deleteBtn.classList.add('opacity-50'));

    deleteBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        if(confirm('Are you sure you want to delete this conversation?')) {
            deleteConversation(convo.id);
        }
    });

    button.appendChild(deleteBtn);
    container.prepend(button);
}

/**
 * Load a specific conversation by ID
 */
function loadConversation(conversationId) {
    fetch(`/conversation/${conversationId}`)
        .then(response => {
            if (!response.ok) throw new Error('Conversation not found');
            return response.json();
        })
        .then(data => {
            currentConversationId = data.conversation_id;
            const chatWindow = document.getElementById('chat-window');
            chatWindow.innerHTML = '';
            
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content, msg.id);
            });
            
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error loading conversation:', error);
            showErrorMessage('Failed to load conversation');
        });
}

/**
 * Delete a conversation by ID
 */
function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    fetch(`/delete_conversation/${conversationId}`, {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (conversationId == currentConversationId) {
                startNewConversation();
            }
            loadConversations();
        } else {
            showErrorMessage('Failed to delete conversation');
        }
    })
    .catch(error => {
        console.error('Error deleting conversation:', error);
        showErrorMessage('Failed to delete conversation');
    });
}

/**
 * Start a new conversation
 */
function startNewConversation() {
    currentConversationId = null;
    document.getElementById('message-input').value = '';
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
        <div class="text-center text-muted mt-5">
            <i class="bi bi-chat-square-text display-1"></i>
            <p class="mt-3 lead">Start a new conversation.</p>
        </div>
    `;
    
    // Remove active class from all conversations
    document.querySelectorAll('#conversation-list .list-group-item, #conversation-list-mobile .list-group-item').forEach(item => {
        item.classList.remove('active');
    });
}

// ============================================================================
// Message Handling
// ============================================================================

/**
 * Handle chat form submission
 */
function handleChatSubmit(event) {
    event.preventDefault();
    if (isStreaming) return;

    const messageInput = document.getElementById('message-input');
    const userMessage = messageInput.value.trim();

    if (!userMessage) {
        showErrorMessage('Please enter a message');
        return;
    }

    // Display user message
    appendMessage('user', userMessage);
    messageInput.value = '';
    autoResizeTextarea();

    // Create placeholder for assistant response
    const assistantMessageElement = appendMessage('assistant', '');
    const messageContent = assistantMessageElement.querySelector('.message-content');
    messageContent.innerHTML = '<div class="spinner-border spinner-border-sm text-secondary" role="status"><span class="visually-hidden">Loading...</span></div>';
    
    // Show stop button, hide send button
    document.getElementById('send-button').style.display = 'none';
    document.getElementById('stop-button').style.display = 'inline-block';
    isStreaming = true;

    // Get settings
    const temperature = parseFloat(document.getElementById('temperature').value) || 0.5;
    const maxTokens = parseInt(document.getElementById('max_tokens').value) || 1500;
    const systemPrompt = document.getElementById('system_prompt').value.trim();
    const model = document.getElementById('model-select').value;

    const params = {
        message: userMessage,
        conversation_id: currentConversationId,
        model: model,
        temperature: temperature,
        max_tokens: maxTokens,
        system_prompt: systemPrompt
    };

    // Create abort controller for this request
    currentAbortController = new AbortController();

    // Send request with streaming
    fetch('/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: currentAbortController.signal
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Check for new conversation ID
        const newConversationId = response.headers.get('X-New-Conversation-Id');
        if (newConversationId && (!currentConversationId || currentConversationId != newConversationId)) {
            currentConversationId = parseInt(newConversationId);
            loadConversations();
        }
        
        streamReader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantContent = '';
        
        // Remove spinner
        messageContent.innerHTML = '';

        function readStream() {
            streamReader.read().then(({ done, value }) => {
                if (done) {
                    finishStreaming();
                    return;
                }

                const chunk = decoder.decode(value, { stream: true });
                assistantContent += chunk;
                messageContent.innerHTML = formatMarkdown(assistantContent);
                scrollToBottom();
                readStream();
            }).catch(error => {
                if (error.name === 'AbortError') {
                    messageContent.innerHTML += '<br><span class="text-warning"><i class="bi bi-exclamation-triangle"></i> Generation stopped by user</span>';
                } else {
                    console.error('Error reading stream:', error);
                    messageContent.innerHTML += '<br><span class="text-danger"><i class="bi bi-x-circle"></i> Error reading stream</span>';
                }
                finishStreaming();
            });
        }

        readStream();
    })
    .catch(error => {
        if (error.name === 'AbortError') {
            messageContent.innerHTML = '<span class="text-warning"><i class="bi bi-exclamation-triangle"></i> Generation stopped by user</span>';
        } else {
            console.error('Streaming error:', error);
            messageContent.innerHTML = `<span class="text-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</span>`;
        }
        finishStreaming();
    });
}

/**
 * Stop the current generation
 */
function stopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
    }
    if (streamReader) {
        streamReader.cancel();
    }
    finishStreaming();
}

/**
 * Clean up after streaming finishes
 */
function finishStreaming() {
    isStreaming = false;
    streamReader = null;
    currentAbortController = null;
    document.getElementById('send-button').style.display = 'inline-block';
    document.getElementById('stop-button').style.display = 'none';
    loadConversations(); // Refresh conversation list
}

/**
 * Append a message to the chat window
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message content
 * @param {number} messageId - Optional message ID for edit/regenerate
 * @returns {HTMLElement} The message element
 */
function appendMessage(role, content = '', messageId = null) {
    const chatWindow = document.getElementById('chat-window');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role} mb-3`;
    if (messageId) {
        messageDiv.dataset.messageId = messageId;
    }

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = formatMarkdown(content);

    messageDiv.appendChild(messageContent);
    
    // Add action buttons for user messages (Edit) and assistant messages (Regenerate)
    if (role === 'user') {
        const actions = createMessageActions('user', messageId);
        messageDiv.appendChild(actions);
    } else if (role === 'assistant' && content) {
        const actions = createMessageActions('assistant', messageId);
        messageDiv.appendChild(actions);
    }

    chatWindow.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

/**
 * Create action buttons for messages
 */
function createMessageActions(role, messageId) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    
    if (role === 'user') {
        // Edit button for user messages
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i> Edit';
        editBtn.title = 'Edit message';
        editBtn.addEventListener('click', () => editMessage(messageId, actionsDiv.closest('.chat-message')));
        actionsDiv.appendChild(editBtn);
    } else if (role === 'assistant') {
        // Regenerate button for assistant messages
        const regenerateBtn = document.createElement('button');
        regenerateBtn.className = 'btn btn-sm';
        regenerateBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Regenerate';
        regenerateBtn.title = 'Regenerate response';
        regenerateBtn.addEventListener('click', () => regenerateResponse());
        actionsDiv.appendChild(regenerateBtn);
        
        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm';
        copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
        copyBtn.title = 'Copy to clipboard';
        copyBtn.addEventListener('click', (e) => {
            const content = actionsDiv.previousElementSibling.textContent;
            navigator.clipboard.writeText(content).then(() => {
                copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
                }, 2000);
            });
        });
        actionsDiv.appendChild(copyBtn);
    }
    
    return actionsDiv;
}

/**
 * Edit a user message
 */
function editMessage(messageId, messageElement) {
    const messageContent = messageElement.querySelector('.message-content');
    const originalText = messageContent.textContent;
    
    // Replace content with textarea
    messageContent.innerHTML = `
        <textarea class="form-control" rows="3">${originalText}</textarea>
        <div class="mt-2">
            <button class="btn btn-sm btn-primary" id="save-edit-btn">Save</button>
            <button class="btn btn-sm btn-secondary" id="cancel-edit-btn">Cancel</button>
        </div>
    `;
    
    const textarea = messageContent.querySelector('textarea');
    const saveBtn = messageContent.querySelector('#save-edit-btn');
    const cancelBtn = messageContent.querySelector('#cancel-edit-btn');
    
    saveBtn.addEventListener('click', () => {
        const newText = textarea.value.trim();
        if (newText) {
            messageContent.innerHTML = formatMarkdown(newText);
            // Trigger regeneration with new message
            document.getElementById('message-input').value = newText;
            regenerateResponse();
        }
    });
    
    cancelBtn.addEventListener('click', () => {
        messageContent.innerHTML = formatMarkdown(originalText);
    });
    
    textarea.focus();
}

/**
 * Regenerate the last assistant response
 */
function regenerateResponse() {
    if (isStreaming) return;
    
    // Get the last user message
    const chatWindow = document.getElementById('chat-window');
    const messages = chatWindow.querySelectorAll('.chat-message');
    
    let lastUserMessage = '';
    for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].classList.contains('user')) {
            lastUserMessage = messages[i].querySelector('.message-content').textContent.trim();
            break;
        }
    }
    
    if (!lastUserMessage) {
        showErrorMessage('No previous message to regenerate');
        return;
    }
    
    // Remove last assistant message if present
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.classList.contains('assistant')) {
        lastMessage.remove();
    }
    
    // Re-submit the last user message
    document.getElementById('message-input').value = lastUserMessage;
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

// ============================================================================
// Models and Settings
// ============================================================================

/**
 * Format model ID into a readable name
 */
function formatModelName(modelId) {
    if (!modelId) return '';
    
    // Remove organization prefix (e.g., "meta-llama/")
    let name = modelId.split('/').pop();
    
    // Replace hyphens and underscores with spaces
    name = name.replace(/[-_]/g, ' ');
    
    // Add spaces between numbers and letters if needed (e.g. "Llama3" -> "Llama 3")
    // This is a bit aggressive, let's stick to simple replacement first.
    
    return name;
}

/**
 * Load available models from the API
 */
function loadModels() {
    fetch('/get_models')
        .then(response => response.json())
        .then(models => {
            const modelSelect = document.getElementById('model-select');
            const modelSelectMobile = document.getElementById('model-select-mobile');
            
            // Destroy existing instance if it exists
            if (modelChoicesInstance) {
                modelChoicesInstance.destroy();
                modelChoicesInstance = null;
            }
            
            modelSelect.innerHTML = '';
            if (modelSelectMobile) {
                modelSelectMobile.innerHTML = '';
            }

            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id; // Keep ID as value
                
                // Use formatted name for display
                option.textContent = formatModelName(model.id);
                
                // Ensure input is a valid JSON string
                let inputTypes = ['text'];
                try {
                    if (Array.isArray(model.input)) {
                        inputTypes = model.input;
                    } else if (typeof model.input === 'string') {
                        // Try to parse if it's a string representation of an array
                        try {
                            inputTypes = JSON.parse(model.input);
                        } catch (e) {
                            inputTypes = [model.input];
                        }
                    }
                } catch (e) {
                    console.warn('Error parsing model input types:', e);
                }
                
                option.dataset.input = JSON.stringify(inputTypes);
                modelSelect.appendChild(option);
                
                if (modelSelectMobile) {
                    const optionMobile = option.cloneNode(true);
                    modelSelectMobile.appendChild(optionMobile);
                }
            });

            // Initialize Choices.js
            if (typeof Choices !== 'undefined') {
                modelChoicesInstance = new Choices(modelSelect, {
                    searchEnabled: true,
                    itemSelectText: '',
                    shouldSort: false,
                    searchResultLimit: 20,
                    position: 'bottom',
                });
            }

            handleModelChange();
        })
        .catch(error => {
            console.error('Error loading models:', error);
            showErrorMessage('Failed to load models');
        });
}

/**
 * Handle model selection change
 */
function handleModelChange() {
    const modelSelect = document.getElementById('model-select');
    const uploadBtn = document.getElementById('upload-btn');
    const selectedOption = modelSelect.options[modelSelect.selectedIndex];
    
    if (!selectedOption) return;
    
    const inputTypes = JSON.parse(selectedOption.dataset.input || '["text"]');
    const supportsImages = inputTypes.includes('image');

    if (uploadBtn) {
        uploadBtn.style.display = supportsImages ? 'inline-block' : 'none';
    }
}

/**
 * Load user settings from server
 */
function loadSettings() {
    fetch('/get_settings')
        .then(response => response.json())
        .then(settings => {
            if (settings.default_temperature !== undefined) {
                document.getElementById('temperature').value = settings.default_temperature;
                const tempMobile = document.getElementById('temperature-mobile');
                if (tempMobile) tempMobile.value = settings.default_temperature;
            }
            if (settings.default_max_tokens !== undefined) {
                document.getElementById('max_tokens').value = settings.default_max_tokens;
                const tokensMobile = document.getElementById('max_tokens-mobile');
                if (tokensMobile) tokensMobile.value = settings.default_max_tokens;
            }
            if (settings.system_prompt !== undefined) {
                document.getElementById('system_prompt').value = settings.system_prompt;
                const promptMobile = document.getElementById('system_prompt-mobile');
                if (promptMobile) promptMobile.value = settings.system_prompt;
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
        });
}

/**
 * Save user settings to server
 */
function saveSettings() {
    // Get values from either desktop or mobile (they should be synced)
    const temperature = parseFloat(document.getElementById('temperature').value);
    const maxTokens = parseInt(document.getElementById('max_tokens').value);
    const systemPrompt = document.getElementById('system_prompt').value;
    
    const settings = {
        default_temperature: temperature,
        default_max_tokens: maxTokens,
        system_prompt: systemPrompt
    };
    
    fetch('/update_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Settings saved successfully');
            
            // Sync mobile and desktop inputs
            document.getElementById('temperature-mobile').value = temperature;
            document.getElementById('max_tokens-mobile').value = maxTokens;
            document.getElementById('system_prompt-mobile').value = systemPrompt;
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showErrorMessage('Failed to save settings');
    });
}

// ============================================================================
// File Upload Handling
// ============================================================================

let base64Image = null;

/**
 * Handle file upload
 */
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
        showErrorMessage('Invalid file type. Only JPEG and PNG are allowed.');
        event.target.value = '';
        return;
    }
    
    if (file.size > 2 * 1024 * 1024) {
        showErrorMessage('File size exceeds 2MB. Please upload a smaller image.');
        event.target.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        base64Image = e.target.result.split(',')[1];
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-preview-container').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

/**
 * Clear file preview
 */
function clearFilePreview() {
    base64Image = null;
    document.getElementById('file-upload').value = '';
    document.getElementById('file-preview-container').style.display = 'none';
}

// ============================================================================
// UI Utilities
// ============================================================================

/**
 * Auto-resize textarea as user types
 */
function autoResizeTextarea() {
    const textarea = document.getElementById('message-input');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

/**
 * Handle special keys in message input
 */
function handleMessageInputKeydown(event) {
    // Submit on Enter (without Shift)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
    }
}

/**
 * Scroll chat window to bottom
 */
function scrollToBottom() {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

/**
 * Format markdown content
 */
function formatMarkdown(content) {
    if (!content) return '';
    
    // Use marked.js if available
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(content);
        } catch (e) {
            console.error('Markdown parsing error:', e);
        }
    }
    
    // Fallback: basic formatting
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
    content = content.replace(/\n/g, '<br>');
    
    return content;
}

/**
 * Show error message
 */
function showErrorMessage(message) {
    // Simple alert for now; could be replaced with toast notification
    alert('Error: ' + message);
}

/**
 * Show success message
 */
function showSuccessMessage(message) {
    // Simple alert for now; could be replaced with toast notification
    alert(message);
}
