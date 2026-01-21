// Global state
let allDocuments = [];
let currentEditId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDocuments();
    setupTabs();
    setupForms();
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
