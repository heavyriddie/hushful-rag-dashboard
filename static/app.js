// Global state
let allDocuments = [];
let currentEditId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDocuments();
    setupTabs();
    setupForms();
    initUploadWorkflow();
});

// Tab switching
function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });
}

// Load stats
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        if (data.success) {
            const stats = data.stats;
            const statsEl = document.getElementById('stats');
            statsEl.innerHTML = `
                <span>${stats.total_documents} documents</span>
                <span>${Object.keys(stats.categories).length} categories</span>
            `;

            // Update category filter
            const filter = document.getElementById('category-filter');
            filter.innerHTML = '<option value="">All Categories</option>';
            Object.keys(stats.categories).sort().forEach(cat => {
                filter.innerHTML += `<option value="${cat}">${cat} (${stats.categories[cat]})</option>`;
            });
        }
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

// Load documents
async function loadDocuments() {
    const list = document.getElementById('documents-list');
    list.innerHTML = '<div class="loading">Loading documents...</div>';

    try {
        const res = await fetch('/api/documents');
        const data = await res.json();

        if (data.success) {
            allDocuments = data.documents;
            renderDocuments(allDocuments);
        } else {
            list.innerHTML = `<div class="empty">Error: ${data.error}</div>`;
        }
    } catch (err) {
        list.innerHTML = `<div class="empty">Error loading documents</div>`;
        console.error('Error:', err);
    }
}

// Render documents
function renderDocuments(docs) {
    const list = document.getElementById('documents-list');

    if (docs.length === 0) {
        list.innerHTML = '<div class="empty">No documents found</div>';
        return;
    }

    list.innerHTML = docs.map(doc => `
        <div class="document-card" onclick="editDocument('${doc.id}')">
            <span class="category">${doc.metadata?.category || 'uncategorized'}</span>
            <div class="content">${escapeHtml(doc.content?.substring(0, 200) || '')}...</div>
            <div class="meta">
                ID: ${doc.id}
                ${doc.metadata?.source ? ` | Source: ${doc.metadata.source}` : ''}
            </div>
        </div>
    `).join('');
}

// Filter documents
document.getElementById('search-filter')?.addEventListener('input', filterDocuments);
document.getElementById('category-filter')?.addEventListener('change', filterDocuments);

function filterDocuments() {
    const search = document.getElementById('search-filter').value.toLowerCase();
    const category = document.getElementById('category-filter').value;

    const filtered = allDocuments.filter(doc => {
        const matchesSearch = !search ||
            doc.content?.toLowerCase().includes(search) ||
            doc.metadata?.source?.toLowerCase().includes(search);
        const matchesCategory = !category || doc.metadata?.category === category;
        return matchesSearch && matchesCategory;
    });

    renderDocuments(filtered);
}

// Setup forms
function setupForms() {
    // Add document form
    document.getElementById('add-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const content = document.getElementById('doc-content').value;
        const metadata = {
            category: document.getElementById('doc-category').value,
            source: document.getElementById('doc-source').value || undefined,
            source_link: document.getElementById('doc-source-link').value || undefined
        };

        try {
            const res = await fetch('/api/documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, metadata })
            });

            const data = await res.json();
            if (data.success) {
                alert('Document added successfully!');
                e.target.reset();
                loadStats();
                loadDocuments();
                // Switch to documents tab
                document.querySelector('[data-tab="documents"]').click();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (err) {
            alert('Error adding document');
            console.error(err);
        }
    });

    // Query form
    document.getElementById('query-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const query = document.getElementById('query-text').value;
        const n_results = parseInt(document.getElementById('query-results').value);

        const resultsList = document.getElementById('query-results-list');
        resultsList.innerHTML = '<div class="loading">Searching...</div>';

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, n_results })
            });

            const data = await res.json();
            if (data.success) {
                renderQueryResults(data.results);
            } else {
                resultsList.innerHTML = `<div class="empty">Error: ${data.error}</div>`;
            }
        } catch (err) {
            resultsList.innerHTML = '<div class="empty">Error searching</div>';
            console.error(err);
        }
    });

    // Edit form
    document.getElementById('edit-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const id = document.getElementById('edit-id').value;
        const content = document.getElementById('edit-content').value;
        const metadata = {
            category: document.getElementById('edit-category').value,
            source: document.getElementById('edit-source').value || undefined,
            source_link: document.getElementById('edit-source-link').value || undefined
        };

        try {
            const res = await fetch(`/api/documents/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, metadata })
            });

            const data = await res.json();
            if (data.success) {
                alert('Document updated!');
                closeModal();
                loadStats();
                loadDocuments();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (err) {
            alert('Error updating document');
            console.error(err);
        }
    });
}

// Render query results
function renderQueryResults(results) {
    const list = document.getElementById('query-results-list');

    if (results.length === 0) {
        list.innerHTML = '<div class="empty">No results found</div>';
        return;
    }

    list.innerHTML = results.map((r, i) => `
        <div class="result-card">
            <span class="similarity">${(r.similarity * 100).toFixed(1)}% match</span>
            <span class="category">${r.metadata?.category || 'uncategorized'}</span>
            <div class="content">${escapeHtml(r.content)}</div>
            <div class="meta">
                ID: ${r.id}
                ${r.metadata?.source ? ` | Source: ${r.metadata.source}` : ''}
            </div>
        </div>
    `).join('');
}

// Edit document
function editDocument(id) {
    const doc = allDocuments.find(d => d.id === id);
    if (!doc) return;

    currentEditId = id;
    document.getElementById('edit-id').value = id;
    document.getElementById('edit-content').value = doc.content || '';
    document.getElementById('edit-category').value = doc.metadata?.category || 'other';
    document.getElementById('edit-source').value = doc.metadata?.source || '';
    document.getElementById('edit-source-link').value = doc.metadata?.source_link || '';

    document.getElementById('edit-modal').classList.add('show');
}

// Delete document
async function deleteDocument() {
    if (!currentEditId) return;

    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
        const res = await fetch(`/api/documents/${currentEditId}`, {
            method: 'DELETE'
        });

        const data = await res.json();
        if (data.success) {
            alert('Document deleted!');
            closeModal();
            loadStats();
            loadDocuments();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error deleting document');
        console.error(err);
    }
}

// Close modal
function closeModal() {
    document.getElementById('edit-modal').classList.remove('show');
    currentEditId = null;
}

// Close modal on outside click
document.getElementById('edit-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'edit-modal') {
        closeModal();
    }
});

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// Upload Workflow
// =============================================================================

// Upload workflow state
let uploadState = {
    step: 1,
    extractedText: '',
    sourceName: '',
    sourceUrl: ''
};

// Initialize upload functionality
function initUploadWorkflow() {
    setupDragDrop();
    setupFileInput();
    setupUrlFetch();
    setupSummarize();
    setupApprove();
}

// Step navigation
function goToStep(stepNum) {
    document.querySelectorAll('.workflow-step').forEach(step => {
        step.classList.remove('active');
    });
    const stepEl = document.getElementById(`upload-step-${stepNum}`);
    if (stepEl) {
        stepEl.classList.add('active');
    }
    uploadState.step = stepNum;
}

// Reset workflow
function resetUploadWorkflow() {
    uploadState = {
        step: 1,
        extractedText: '',
        sourceName: '',
        sourceUrl: ''
    };

    const fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';

    const urlInput = document.getElementById('url-input');
    if (urlInput) urlInput.value = '';

    const extractedText = document.getElementById('extracted-text');
    if (extractedText) extractedText.value = '';

    const summaryContent = document.getElementById('summary-content');
    if (summaryContent) summaryContent.value = '';

    const uploadSource = document.getElementById('upload-source');
    if (uploadSource) uploadSource.value = '';

    const uploadSourceLink = document.getElementById('upload-source-link');
    if (uploadSourceLink) uploadSourceLink.value = '';

    clearStatus('upload-status');
    clearStatus('summarize-status');
    clearStatus('approve-status');
    goToStep(1);
}

// Switch to documents tab
function viewDocuments() {
    document.querySelector('[data-tab="documents"]').click();
    loadDocuments();
}

// Drag and drop setup
function setupDragDrop() {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
}

// File input setup
function setupFileInput() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput) return;

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

// Handle file upload
async function handleFileUpload(file) {
    const statusEl = document.getElementById('upload-status');
    showStatus(statusEl, 'loading', `Extracting text from ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            uploadState.extractedText = data.text;
            uploadState.sourceName = data.filename;
            uploadState.sourceUrl = '';

            showExtractionResults(data);
            clearStatus(statusEl);
            goToStep(2);
        } else {
            showStatus(statusEl, 'error', data.error);
        }
    } catch (err) {
        showStatus(statusEl, 'error', 'Failed to upload file');
        console.error(err);
    }
}

// URL fetch setup
function setupUrlFetch() {
    const fetchBtn = document.getElementById('fetch-url-btn');
    if (!fetchBtn) return;

    fetchBtn.addEventListener('click', handleUrlFetch);

    // Also allow Enter key in URL input
    const urlInput = document.getElementById('url-input');
    if (urlInput) {
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleUrlFetch();
            }
        });
    }
}

// Handle URL fetch
async function handleUrlFetch() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput ? urlInput.value.trim() : '';

    if (!url) {
        showStatus(document.getElementById('upload-status'), 'error',
                   'Please enter a URL');
        return;
    }

    const statusEl = document.getElementById('upload-status');
    showStatus(statusEl, 'loading', 'Fetching content from URL...');

    try {
        const response = await fetch('/api/extract-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (data.success) {
            uploadState.extractedText = data.text;
            uploadState.sourceName = data.title || url;
            uploadState.sourceUrl = data.url;

            showExtractionResults(data);
            clearStatus(statusEl);
            goToStep(2);
        } else {
            showStatus(statusEl, 'error', data.error);
        }
    } catch (err) {
        showStatus(statusEl, 'error', 'Failed to fetch URL');
        console.error(err);
    }
}

// Show extraction results
function showExtractionResults(data) {
    const sourceEl = document.getElementById('extraction-source');
    if (sourceEl) {
        sourceEl.textContent = `Source: ${data.filename || data.title || data.url}`;
    }

    const statsEl = document.getElementById('extraction-stats');
    if (statsEl) {
        statsEl.textContent = `${data.word_count.toLocaleString()} words | ${data.char_count.toLocaleString()} characters`;
    }

    // Show preview (first 5000 chars)
    const preview = data.text.length > 5000
        ? data.text.substring(0, 5000) + '\n\n... [truncated for preview]'
        : data.text;

    const extractedTextEl = document.getElementById('extracted-text');
    if (extractedTextEl) {
        extractedTextEl.value = preview;
    }

    // Pre-fill source fields
    const uploadSourceEl = document.getElementById('upload-source');
    if (uploadSourceEl) {
        uploadSourceEl.value = uploadState.sourceName;
    }

    const uploadSourceLinkEl = document.getElementById('upload-source-link');
    if (uploadSourceLinkEl) {
        uploadSourceLinkEl.value = uploadState.sourceUrl;
    }
}

// Summarize setup
function setupSummarize() {
    const summarizeBtn = document.getElementById('summarize-btn');
    if (!summarizeBtn) return;

    summarizeBtn.addEventListener('click', handleSummarize);
}

// Handle summarization
async function handleSummarize() {
    const statusEl = document.getElementById('summarize-status');
    showStatus(statusEl, 'loading',
               'Generating summary with Claude... This may take a moment.');

    try {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: uploadState.extractedText,
                source_name: uploadState.sourceName
            })
        });

        const data = await response.json();

        if (data.success) {
            const summaryContent = document.getElementById('summary-content');
            if (summaryContent) {
                summaryContent.value = data.summary;
            }
            clearStatus(statusEl);
            goToStep(3);
        } else {
            showStatus(statusEl, 'error', data.error);
        }
    } catch (err) {
        showStatus(statusEl, 'error', 'Failed to generate summary');
        console.error(err);
    }
}

// Approve setup
function setupApprove() {
    const approveBtn = document.getElementById('approve-btn');
    if (!approveBtn) return;

    approveBtn.addEventListener('click', handleApprove);
}

// Handle approval - add to knowledge base
async function handleApprove() {
    const summaryContentEl = document.getElementById('summary-content');
    const content = summaryContentEl ? summaryContentEl.value.trim() : '';

    if (!content) {
        showStatus(document.getElementById('approve-status'), 'error',
                   'Summary content is required');
        return;
    }

    const statusEl = document.getElementById('approve-status');
    showStatus(statusEl, 'loading', 'Adding to knowledge base...');

    const categoryEl = document.getElementById('upload-category');
    const sourceEl = document.getElementById('upload-source');
    const sourceLinkEl = document.getElementById('upload-source-link');

    const metadata = {
        category: categoryEl ? categoryEl.value : 'other',
        source: sourceEl && sourceEl.value ? sourceEl.value : undefined,
        source_link: sourceLinkEl && sourceLinkEl.value ? sourceLinkEl.value : undefined
    };

    try {
        const response = await fetch('/api/documents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, metadata })
        });

        const data = await response.json();

        if (data.success) {
            const docIdEl = document.getElementById('added-doc-id');
            if (docIdEl) {
                docIdEl.textContent = `Document ID: ${data.id}`;
            }
            loadStats();
            clearStatus(statusEl);
            goToStep(4);
        } else {
            showStatus(statusEl, 'error', data.error);
        }
    } catch (err) {
        showStatus(statusEl, 'error', 'Failed to add document');
        console.error(err);
    }
}

// Status helpers
function showStatus(element, type, message) {
    if (!element) return;
    element.className = `status-message ${type}`;
    element.textContent = message;
}

function clearStatus(elementId) {
    const element = typeof elementId === 'string'
        ? document.getElementById(elementId)
        : elementId;
    if (!element) return;
    element.className = 'status-message';
    element.textContent = '';
}
