/**
 * URL Discovery Page JavaScript
 * Used by: discover.html
 */

let discoveredUrls = [];
let discoveryMetadata = {};
let selectedUrls = new Set();
let activeBatchScan = null;
let batchStatusInterval = null;

// Load saved scan parameters
function loadSavedParameters() {
    const savedMaxPages = localStorage.getItem('lastMaxPages');
    const savedMaxDepth = localStorage.getItem('lastMaxDepth');

    if (savedMaxPages) {
        const maxPagesInput = document.getElementById('batchMaxPages');
        if (maxPagesInput) maxPagesInput.value = savedMaxPages;
    }
    if (savedMaxDepth) {
        const maxDepthInput = document.getElementById('batchMaxDepth');
        if (maxDepthInput) maxDepthInput.value = savedMaxDepth;
    }
}

// Save scan parameters
function saveScanParameters(maxPages, maxDepth) {
    localStorage.setItem('lastMaxPages', maxPages);
    localStorage.setItem('lastMaxDepth', maxDepth);
}

// Check for active batch scans on page load
async function checkActiveBatchScans() {
    try {
        const response = await fetch('/api/batch/active');
        if (response.ok) {
            const activeBatches = await response.json();
            if (activeBatches && activeBatches.length > 0) {
                activeBatchScan = activeBatches[0].batch_id;
                startBatchStatusPolling();
                showBatchProgress();
                disableScanControls();
            }
        }
    } catch (error) {
        console.error('Error checking active batch scans:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSavedParameters();
    checkActiveBatchScans();
});

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

        // Log the response for debugging
        console.log('Discovery response:', data);

        // Check if we got valid data
        if (!data) {
            throw new Error('No data received from server');
        }

        discoveredUrls = data.discovered_urls || [];
        discoveryMetadata = data;

        // Check if discovery had errors
        if (data.status === 'failed' || data.status === 'error') {
            throw new Error(data.error_message || 'Discovery failed on server');
        }

        // Check if we got any URLs
        if (discoveredUrls.length === 0) {
            alert('No URLs discovered. The site may have timed out or no links were found matching your criteria.');
        }

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
    const resultsSection = document.getElementById('resultsSection');
    const urlCountEl = document.getElementById('urlCount');
    const metadataEl = document.getElementById('metadata');

    // Safety check - ensure elements exist
    if (!resultsSection || !urlCountEl || !metadataEl) {
        console.error('Required DOM elements not found');
        return;
    }

    resultsSection.style.display = 'block';
    urlCountEl.textContent = discoveredUrls.length;

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
    metadataEl.innerHTML = metadataHtml;

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
            <button class="btn btn-sm btn-outline-primary scan-url-btn" data-url="${url}" title="Scan this URL">
                <i class="bi bi-search"></i> Scan
            </button>
        `;
        urlList.appendChild(div);
    });

    // Add event listeners to all scan buttons
    document.querySelectorAll('.scan-url-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const url = e.currentTarget.dataset.url;
            // Navigate to scan page with URL as query parameter
            window.location.href = `/?url=${encodeURIComponent(url)}`;
        });
    });
}

// Search URLs
document.getElementById('searchUrls').addEventListener('input', (e) => {
    renderUrlList(e.target.value);
});

// Select All/None
document.getElementById('selectAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.url-checkbox').forEach(cb => cb.checked = true);
});

document.getElementById('selectNoneBtn').addEventListener('click', () => {
    document.querySelectorAll('.url-checkbox').forEach(cb => cb.checked = false);
});

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

// ===== BATCH SCANNING FUNCTIONS =====

// Start Batch Scan
document.getElementById('batchScanBtn')?.addEventListener('click', async () => {
    const selectedCheckboxes = Array.from(document.querySelectorAll('.url-checkbox:checked'));
    selectedUrls = new Set(selectedCheckboxes.map(cb => cb.dataset.url));

    if (selectedUrls.size === 0) {
        alert('Please select at least one URL to scan');
        return;
    }

    if (selectedUrls.size > 500) {
        alert('Maximum 500 URLs can be scanned in a batch');
        return;
    }

    const maxPages = parseInt(document.getElementById('batchMaxPages').value);
    const maxDepth = parseInt(document.getElementById('batchMaxDepth').value);

    if (maxPages < 1 || maxPages > 10000) {
        alert('Max pages must be between 1 and 10,000');
        return;
    }

    if (maxDepth < 1 || maxDepth > 10) {
        alert('Max depth must be between 1 and 10');
        return;
    }

    // Save parameters for next time
    saveScanParameters(maxPages, maxDepth);

    // Confirm
    if (!confirm(`Start batch scan of ${selectedUrls.size} URLs?\n\nThis will create ${selectedUrls.size} individual scans.`)) {
        return;
    }

    try {
        const response = await fetch('/api/batch/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                urls: Array.from(selectedUrls),
                max_pages: maxPages,
                max_depth: maxDepth,
                same_domain_only: true,
                scan_mode: 'aoda'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start batch scan');
        }

        const data = await response.json();
        activeBatchScan = data.batch_id;

        // Show progress section
        showBatchProgress();

        // Start polling for status
        startBatchStatusPolling();

        // Disable scan controls
        disableScanControls();

    } catch (error) {
        alert(`Failed to start batch scan: ${error.message}`);
    }
});

// Cancel Batch Scan
document.getElementById('cancelBatchBtn')?.addEventListener('click', async () => {
    if (!activeBatchScan) return;

    if (!confirm('Are you sure you want to cancel this batch scan?\n\nCompleted scans will be saved, but remaining URLs will not be scanned.')) {
        return;
    }

    try {
        const response = await fetch(`/api/batch/cancel/${activeBatchScan}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to cancel batch scan');
        }

        alert('Batch scan cancelled successfully');
        stopBatchStatusPolling();
        hideBatchProgress();
        enableScanControls();
        activeBatchScan = null;

    } catch (error) {
        alert(`Failed to cancel batch scan: ${error.message}`);
    }
});

// Show batch progress section
function showBatchProgress() {
    const progressSection = document.getElementById('batchProgressSection');
    if (progressSection) {
        progressSection.style.display = 'block';
    }
}

// Hide batch progress section
function hideBatchProgress() {
    const progressSection = document.getElementById('batchProgressSection');
    if (progressSection) {
        progressSection.style.display = 'none';
    }
}

// Disable scan controls during batch scanning
function disableScanControls() {
    const batchScanBtn = document.getElementById('batchScanBtn');
    const discoverBtn = document.querySelector('#discoverForm button[type="submit"]');

    if (batchScanBtn) {
        batchScanBtn.disabled = true;
        batchScanBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Batch Scan in Progress...';
    }

    if (discoverBtn) {
        discoverBtn.disabled = true;
    }

    // Disable individual scan buttons
    document.querySelectorAll('.scan-url-btn').forEach(btn => {
        btn.disabled = true;
    });

    // Show warning message
    const warningEl = document.getElementById('scanningWarning');
    if (warningEl) {
        warningEl.style.display = 'block';
    }
}

// Enable scan controls after batch completes
function enableScanControls() {
    const batchScanBtn = document.getElementById('batchScanBtn');
    const discoverBtn = document.querySelector('#discoverForm button[type="submit"]');

    if (batchScanBtn) {
        batchScanBtn.disabled = false;
        batchScanBtn.innerHTML = '<i class="bi bi-play-circle-fill"></i> Scan All Selected';
    }

    if (discoverBtn) {
        discoverBtn.disabled = false;
    }

    // Enable individual scan buttons
    document.querySelectorAll('.scan-url-btn').forEach(btn => {
        btn.disabled = false;
    });

    // Hide warning message
    const warningEl = document.getElementById('scanningWarning');
    if (warningEl) {
        warningEl.style.display = 'none';
    }
}

// Start polling for batch status
function startBatchStatusPolling() {
    if (batchStatusInterval) {
        clearInterval(batchStatusInterval);
    }

    updateBatchStatus(); // Immediate update
    batchStatusInterval = setInterval(updateBatchStatus, 2000); // Poll every 2 seconds
}

// Stop polling for batch status
function stopBatchStatusPolling() {
    if (batchStatusInterval) {
        clearInterval(batchStatusInterval);
        batchStatusInterval = null;
    }
}

// Update batch status display
async function updateBatchStatus() {
    if (!activeBatchScan) {
        stopBatchStatusPolling();
        return;
    }

    try {
        const response = await fetch(`/api/batch/status/${activeBatchScan}`);

        if (!response.ok) {
            console.error('Failed to fetch batch status');
            return;
        }

        const status = await response.json();

        // Update progress text
        const progressText = document.getElementById('batchProgressText');
        if (progressText) {
            const completed = status.completed + status.failed;
            progressText.textContent = `Scanning ${completed} of ${status.total_urls} URLs`;
        }

        // Update current URL
        const currentUrlEl = document.getElementById('currentBatchUrl');
        if (currentUrlEl) {
            if (status.current_url) {
                currentUrlEl.textContent = `Current: ${status.current_url}`;
                currentUrlEl.style.display = 'block';
            } else {
                currentUrlEl.style.display = 'none';
            }
        }

        // Update progress bar
        const progressBar = document.getElementById('batchProgressBar');
        if (progressBar) {
            const completed = status.completed + status.failed;
            const percentage = (completed / status.total_urls) * 100;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            progressBar.textContent = `${Math.round(percentage)}%`;
        }

        // Update stats
        const statsEl = document.getElementById('batchStats');
        if (statsEl) {
            statsEl.innerHTML = `
                <span class="badge bg-success me-2">Completed: ${status.completed}</span>
                <span class="badge bg-danger me-2">Failed: ${status.failed}</span>
                <span class="badge bg-primary">In Progress: ${status.in_progress}</span>
            `;
        }

        // Check if completed or cancelled
        if (status.status === 'completed' || status.status === 'cancelled') {
            stopBatchStatusPolling();
            enableScanControls();

            setTimeout(() => {
                hideBatchProgress();
                activeBatchScan = null;

                if (status.status === 'completed') {
                    alert(`Batch scan completed!\n\n${status.completed} URLs scanned successfully\n${status.failed} URLs failed\n\nYou can view the results in the History page.`);
                }
            }, 3000);
        }

    } catch (error) {
        console.error('Error updating batch status:', error);
    }
}
