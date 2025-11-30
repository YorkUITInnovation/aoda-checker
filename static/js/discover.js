/**
 * URL Discovery Page JavaScript
 * Used by: discover.html
 */

let discoveredUrls = [];
let discoveryMetadata = {};

// Discover URLs Form
document.getElementById('discoverForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('discoverUrl').value;
    const maxDepth = parseInt(document.getElementById('maxDepth').value);
    const maxPages = parseInt(document.getElementById('maxPages').value);
    const sameDomain = document.getElementById('sameDomain').checked;
    const restrictPath = document.getElementById('restrictPath').checked;

    // Validate max pages
    if (maxPages < 1 || maxPages > 10000) {
        alert('Max pages must be between 1 and 10,000');
        return;
    }

    // Show spinner
    document.getElementById('spinnerContainer').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';

    try {
        const apiUrl = `/api/discover-urls?url=${encodeURIComponent(url)}&max_depth=${maxDepth}&max_pages=${maxPages}&same_domain_only=${sameDomain}&restrict_to_path=${restrictPath}`;
        
        const response = await fetch(apiUrl);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Discovery failed');
        }

        const data = await response.json();
        discoveredUrls = data.discovered_urls || [];
        discoveryMetadata = data;

        displayResults();
    } catch (error) {
        console.error('Discovery error:', error);
        alert(`Discovery failed: ${error.message}`);
    } finally {
        document.getElementById('spinnerContainer').style.display = 'none';
    }
});

// File Upload Handler
document.getElementById('fileUpload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const text = await file.text();
    const extension = file.name.split('.').pop().toLowerCase();

    try {
        if (extension === 'csv') {
            discoveredUrls = parseCSV(text);
        } else if (extension === 'json') {
            discoveredUrls = parseJSON(text);
        } else if (extension === 'txt') {
            discoveredUrls = parseTXT(text);
        }

        discoveryMetadata = {
            start_url: 'Imported from file',
            total_discovered: discoveredUrls.length,
            status: 'imported'
        };

        displayResults();
    } catch (error) {
        alert(`Failed to parse file: ${error.message}`);
    }
});

// Paste URLs Handler
document.getElementById('loadUrlsBtn').addEventListener('click', () => {
    const pastedText = document.getElementById('pasteUrls').value;
    if (!pastedText.trim()) {
        alert('Please paste some URLs first');
        return;
    }

    discoveredUrls = parseTXT(pastedText);
    discoveryMetadata = {
        start_url: 'Imported from paste',
        total_discovered: discoveredUrls.length,
        status: 'imported'
    };

    displayResults();

    // Switch to discover tab to show results
    document.getElementById('discover-tab').click();
});

// Parse Functions
function parseCSV(csvText) {
    const lines = csvText.split('\n').filter(line => line.trim());
    const urls = [];

    for (let i = 1; i < lines.length; i++) { // Skip header
        const line = lines[i].trim();
        if (line.includes('http')) {
            const url = line.split(',')[0].trim().replace(/['"]/g, '');
            if (url.startsWith('http')) {
                urls.push(url);
            }
        }
    }

    // If no header was found, try all lines
    if (urls.length === 0) {
        return lines.filter(line => line.trim().startsWith('http'))
                   .map(line => line.split(',')[0].trim().replace(/['"]/g, ''));
    }

    return urls;
}

function parseJSON(jsonText) {
    const data = JSON.parse(jsonText);
    if (Array.isArray(data)) {
        return data.filter(item => typeof item === 'string' && item.startsWith('http'));
    }
    if (data.urls && Array.isArray(data.urls)) {
        return data.urls;
    }
    if (data.discovered_urls && Array.isArray(data.discovered_urls)) {
        return data.discovered_urls;
    }
    throw new Error('JSON format not recognized. Expected {urls: [...]} or array of URLs');
}

function parseTXT(txtText) {
    return txtText.split('\n')
                 .map(line => line.trim())
                 .filter(line => line.startsWith('http'));
}

// Display Results
function displayResults() {
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('urlCount').textContent = discoveredUrls.length;

    // Show metadata
    let metadataHtml = '';
    if (discoveryMetadata.start_url) {
        metadataHtml += `<strong>Start URL:</strong> ${discoveryMetadata.start_url}<br>`;
    }
    if (discoveryMetadata.duration_seconds) {
        metadataHtml += `<strong>Duration:</strong> ${discoveryMetadata.duration_seconds}s<br>`;
    }
    if (discoveryMetadata.depth_crawled) {
        metadataHtml += `<strong>Depth:</strong> ${discoveryMetadata.depth_crawled} levels<br>`;
    }
    document.getElementById('metadata').innerHTML = metadataHtml;

    renderUrlList();
}

// Render URL List
function renderUrlList(filter = '') {
    const urlList = document.getElementById('urlList');
    urlList.innerHTML = '';

    const filteredUrls = discoveredUrls.filter(url =>
        url.toLowerCase().includes(filter.toLowerCase())
    );

    filteredUrls.forEach((url, index) => {
        const div = document.createElement('div');
        div.className = 'url-item';
        div.innerHTML = `
            <input type="checkbox" class="form-check-input url-checkbox"
                   data-url="${url}" checked>
            <span class="url-text">${url}</span>
        `;
        urlList.appendChild(div);
    });

    updateSelectedCount();
}

// Search URLs
document.getElementById('searchUrls').addEventListener('input', (e) => {
    renderUrlList(e.target.value);
});

// Select All/None
document.getElementById('selectAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.url-checkbox').forEach(cb => cb.checked = true);
    updateSelectedCount();
});

document.getElementById('selectNoneBtn').addEventListener('click', () => {
    document.querySelectorAll('.url-checkbox').forEach(cb => cb.checked = false);
    updateSelectedCount();
});

// Update selected count when checkboxes change
document.getElementById('urlList').addEventListener('change', updateSelectedCount);

function updateSelectedCount() {
    const count = document.querySelectorAll('.url-checkbox:checked').length;
    document.getElementById('selectedCount').textContent = count;
}

// Export Functions
document.getElementById('exportCsvBtn').addEventListener('click', () => {
    // Properly quote URLs to prevent colon from being treated as separator
    const csvRows = ['url'];
    discoveredUrls.forEach(url => {
        // Wrap each URL in quotes and escape any quotes in the URL
        csvRows.push(`"${url.replace(/"/g, '""')}"`);
    });
    const csv = csvRows.join('\n');
    downloadFile(csv, 'discovered_urls.csv', 'text/csv');
});

document.getElementById('exportJsonBtn').addEventListener('click', () => {
    const json = JSON.stringify({
        ...discoveryMetadata,
        discovered_urls: discoveredUrls
    }, null, 2);
    downloadFile(json, 'discovered_urls.json', 'application/json');
});

document.getElementById('exportTxtBtn').addEventListener('click', () => {
    const txt = discoveredUrls.join('\n');
    downloadFile(txt, 'discovered_urls.txt', 'text/plain');
});

document.getElementById('copyBtn').addEventListener('click', () => {
    const selectedUrls = Array.from(document.querySelectorAll('.url-checkbox:checked'))
                             .map(cb => cb.dataset.url);
    navigator.clipboard.writeText(selectedUrls.join('\n'))
        .then(() => alert(`Copied ${selectedUrls.length} URLs to clipboard!`))
        .catch(err => alert('Failed to copy: ' + err));
});

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

