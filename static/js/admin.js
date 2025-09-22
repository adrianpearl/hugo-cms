// Hugo CMS Admin JavaScript
// Configuration will be provided via window.hugoCmsConfig object

let currentSourceFile = '';

// Initialize configuration from global config object
let filePathPattern = '';
let filePathPatternHint = '';

if (window.hugoCmsConfig) {
    currentSourceFile = window.hugoCmsConfig.currentSourceFile || '';
    filePathPattern = window.hugoCmsConfig.filePathPattern || '';
    filePathPatternHint = window.hugoCmsConfig.filePathPatternHint || '';
}

// Toggle admin panel visibility
function toggleAdminPanel() {
    const panel = document.getElementById('hugo-cms-panel');
    if (panel) {
        panel.classList.toggle('open');
    }
}

// Loading state management
function setButtonLoading(buttonElement, isLoading, originalText) {
    if (isLoading) {
        buttonElement.disabled = true;
        buttonElement.classList.add('hugo-cms-loading');
        buttonElement.innerHTML = originalText + '<span class="hugo-cms-spinner"></span>';
    } else {
        buttonElement.disabled = false;
        buttonElement.classList.remove('hugo-cms-loading');
        buttonElement.innerHTML = originalText;
    }
}

function setAllButtonsLoading(isLoading) {
    const buttons = document.querySelectorAll('.hugo-cms-actions button');
    buttons.forEach(button => {
        button.disabled = isLoading;
        if (isLoading) {
            button.classList.add('hugo-cms-loading');
        } else {
            button.classList.remove('hugo-cms-loading');
        }
    });
}

function validateFilePath(filePath) {
    if (!filePathPattern) {
        return { valid: true, message: '' };
    }
    
    try {
        const regex = new RegExp(filePathPattern);
        if (regex.test(filePath)) {
            return { valid: true, message: '' };
        } else {
            const hint = filePathPatternHint || filePathPattern;
            return { valid: false, message: `File path must match pattern: ${hint}` };
        }
    } catch (e) {
        return { valid: false, message: 'Invalid file path pattern configured' };
    }
}

function updateFilenamePreview(input) {
    const preview = document.getElementById('filename-preview');
    if (preview) {
        const value = input.value.trim();
        if (value) {
            const finalFilename = value.endsWith('.md') ? value : value + '.md';
            const validation = validateFilePath(value);
            
            if (validation.valid) {
                preview.textContent = `Will create: ${finalFilename}`;
                preview.style.color = '#007cba';
                preview.classList.remove('error');
            } else {
                preview.textContent = validation.message;
                preview.style.color = '#dc3545';
                preview.classList.add('error');
            }
            preview.style.display = 'block';
        } else {
            preview.style.display = 'none';
        }
    }
}

function showNotification(message, isSuccess = true) {
    // Create a temporary notification instead of using alert
    const notification = document.createElement('div');
    notification.style.cssText = 
        'position: fixed;' +
        'top: 80px;' +
        'right: 10px;' +
        'background: ' + (isSuccess ? '#4CAF50' : '#f44336') + ';' +
        'color: white;' +
        'padding: 15px;' +
        'border-radius: 5px;' +
        'z-index: 10001;' +
        'font-family: Arial, sans-serif;' +
        'max-width: 300px;' +
        'word-wrap: break-word;';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 4000);
}

function editCurrentPage() {
    if (!currentSourceFile) {
        alert('No source file found for this page');
        return;
    }
    
    fetch(`/admin/api/get-content/${encodeURIComponent(currentSourceFile)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showEditModal(data.frontmatter, data.content, currentSourceFile);
            } else {
                alert('Error loading content: ' + data.message);
            }
        });
}

function createNewPage() {
    showEditModal({}, '', null);
}

function showEditModal(frontmatter, content, filePath) {
    const modal = document.getElementById('hugo-cms-modal') || createModal();
    
    let frontmatterFields = '';
    const commonFields = ['title', 'date', 'draft', 'tags', 'categories'];
    
    // Add existing frontmatter fields
    for (const [key, value] of Object.entries(frontmatter)) {
        frontmatterFields += 
            '<div>' +
            '<label>' + key + ':</label>' +
            '<input type="text" name="fm_' + key + '" value="' + value + '" />' +
            '</div>';
    }
    
    // Add common fields if not present
    for (const field of commonFields) {
        if (!frontmatter.hasOwnProperty(field)) {
            const inputType = field === 'date' ? 'date' : 'text';
            frontmatterFields += 
                '<div>' +
                '<label>' + field + ':</label>' +
                '<input type="' + inputType + '" name="fm_' + field + '" value="" />' +
                '</div>';
        }
    }
    
    modal.innerHTML = 
        '<div class="hugo-cms-modal-content">' +
        '<span class="hugo-cms-close" onclick="closeModal()">&times;</span>' +
        '<h2>' + (filePath ? 'Edit Page' : 'Create New Page') + '</h2>' +
        '<form class="hugo-cms-form" onsubmit="savePage(event, \'' + (filePath || '') + '\')">' +
        (!filePath ? 
            '<div>' +
            '<label>File Path: <small style="color: #666;">(will auto-add .md if not included)</small></label>' +
            (filePathPatternHint ? '<div style="color: #666; font-size: 12px; margin-bottom: 5px;">📝 ' + filePathPatternHint + '</div>' : '') +
            '<input type="text" name="filename" placeholder="news/recent-news-item" required ' +
            'oninput="updateFilenamePreview(this)" />' +
            '<small id="filename-preview" style="color: #007cba; display: block; margin-top: 5px;"></small>' +
            '</div>' 
        : '') +
        '<h3>Frontmatter</h3>' +
        frontmatterFields +
        '<h3>Content</h3>' +
        '<textarea name="content" placeholder="Write your content here...">' + content + '</textarea>' +
        '<button type="submit">' + (filePath ? 'Save Changes' : 'Create Page') + '</button>' +
        '</form>' +
        '</div>';
    
    modal.style.display = 'block';
}

function createModal() {
    const modal = document.createElement('div');
    modal.id = 'hugo-cms-modal';
    modal.className = 'hugo-cms-modal';
    document.body.appendChild(modal);
    return modal;
}

function closeModal() {
    const modal = document.getElementById('hugo-cms-modal');
    if (modal) modal.style.display = 'none';
}

function savePage(event, filePath) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    
    // For new pages, validate file path before submitting
    if (!filePath) {
        const filename = formData.get('filename');
        if (filename) {
            const validation = validateFilePath(filename);
            if (!validation.valid) {
                showNotification(validation.message, false);
                return;
            }
        }
    }
    
    // Show loading state
    setButtonLoading(submitButton, true, filePath ? 'Saving...' : 'Creating...');
    setAllButtonsLoading(true);
    
    const url = filePath ? 
        `/admin/api/save/${encodeURIComponent(filePath)}` : 
        '/admin/api/create';
    
    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // Reset loading state
        setButtonLoading(submitButton, false, originalButtonText);
        setAllButtonsLoading(false);
        
        if (data.success) {
            showNotification(data.message);
            closeModal();
            
            // If this is a new page creation, navigate to the new page
            if (!filePath && data.url) {
                setTimeout(() => window.location.href = data.url, 1000);
            } else {
                // For edits, reload the current page
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            showNotification('Error: ' + data.message, false);
        }
    })
    .catch(error => {
        // Reset loading state
        setButtonLoading(submitButton, false, originalButtonText);
        setAllButtonsLoading(false);
        showNotification('Error: ' + error.message, false);
    });
}

function rebuildSite() {
    const buildButton = document.querySelector('button[onclick="rebuildSite()"]');
    const originalText = '🔄 Build';
    
    // Show loading state
    setButtonLoading(buildButton, true, '🔄 Building...');
    setAllButtonsLoading(true);
    
    fetch('/admin/api/build')
        .then(response => {
            if (response.status === 401) {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Skip if redirected
            // Reset loading state
            setButtonLoading(buildButton, false, originalText);
            setAllButtonsLoading(false);
            
            showNotification(data.message, data.success);
            if (data.success) {
                setTimeout(() => location.reload(), 1000);
            }
        })
        .catch(error => {
            // Reset loading state
            setButtonLoading(buildButton, false, originalText);
            setAllButtonsLoading(false);
            showNotification('Error: ' + error.message, false);
        });
}

function publishChanges() {
    if (!confirm('Are you sure you want to publish all changes to the Git repository?')) {
        return;
    }
    
    const publishButton = document.querySelector('button[onclick="publishChanges()"]');
    const originalText = '🚀 Stage for Publishing';
    
    // Show loading state
    setButtonLoading(publishButton, true, '🚀 Staging for Publishing...');
    setAllButtonsLoading(true);
    
    fetch('/admin/api/publish', {
        method: 'POST'
    })
    .then(response => {
        if (response.status === 401) {
            window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            return;
        }
        return response.json();
    })
    .then(data => {
        if (!data) return; // Skip if redirected
        // Reset loading state
        setButtonLoading(publishButton, false, originalText);
        setAllButtonsLoading(false);
        
        showNotification(data.message, data.success);
    })
    .catch(error => {
        // Reset loading state
        setButtonLoading(publishButton, false, originalText);
        setAllButtonsLoading(false);
        showNotification('Error: ' + error.message, false);
    });
}

function clearCache() {
    if (!confirm('Are you sure you want to clear the repository cache and re-clone? This will discard any uncommitted local changes.')) {
        return;
    }
    
    const clearButton = document.querySelector('button[onclick="clearCache()"]');
    const originalText = '🗑️ Clear Cache';
    
    // Show loading state
    setButtonLoading(clearButton, true, '🗑️ Clearing...');
    setAllButtonsLoading(true);
    
    fetch('/admin/api/clear-cache', {
        method: 'POST'
    })
    .then(response => {
        if (response.status === 401) {
            window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            return;
        }
        return response.json();
    })
    .then(data => {
        if (!data) return; // Skip if redirected
        // Reset loading state
        setButtonLoading(clearButton, false, originalText);
        setAllButtonsLoading(false);
        
        showNotification(data.message, data.success);
        if (data.success) {
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(error => {
        // Reset loading state
        setButtonLoading(clearButton, false, originalText);
        setAllButtonsLoading(false);
        showNotification('Error: ' + error.message, false);
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('hugo-cms-modal');
    if (event.target == modal) {
        closeModal();
    }
}
