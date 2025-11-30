/**
 * Index Page JavaScript - Accessibility Scan Form
 * Used by: index.html
 */

// Get all DOM elements globally so they're accessible everywhere
const scanForm = document.getElementById('scanForm');
const scanButton = document.getElementById('scanButton');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const pagesScanned = document.getElementById('pagesScanned');
const issuesFound = document.getElementById('issuesFound');
const estimatedTime = document.getElementById('estimatedTime');

// Check for URL parameter and pre-fill the form
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlParam = urlParams.get('url');

    if (urlParam) {
        document.getElementById('url').value = urlParam;
        // Optionally focus the URL field or scroll to form
        document.getElementById('url').focus();
    }
});

// Handle scan form submission
scanForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        url: document.getElementById('url').value,
        max_pages: parseInt(document.getElementById('maxPages').value),
        max_depth: parseInt(document.getElementById('maxDepth').value),
        same_domain_only: true,
        restrict_to_path: document.getElementById('restrictPath').checked,
        enable_screenshots: document.getElementById('enableScreenshots').checked
    };

    // Disable form
    scanButton.disabled = true;
    progressSection.style.display = 'block';
    progressText.innerHTML = '<strong>Starting scan...</strong>';
    progressBar.style.width = '10%';
    progressPercent.textContent = '10%';
    pagesScanned.textContent = '0';
    issuesFound.textContent = '0';
    estimatedTime.textContent = 'Calculating...';

    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.scan_id) {
            progressText.innerHTML = '<strong>Scan started successfully!</strong> Analyzing pages...';
            progressBar.style.width = '30%';
            progressPercent.textContent = '30%';
            pollScanStatus(data.scan_id);
        } else {
            throw new Error('No scan ID received');
        }
    } catch (error) {
        console.error('Error starting scan:', error);
        alert('Failed to start scan. Please try again.');
        scanButton.disabled = false;
        progressSection.style.display = 'none';
    }
});

// Poll scan status until completion
async function pollScanStatus(scanId) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/scan/${scanId}`);
            const data = await response.json();

            console.log('Poll update:', {
                status: data.status,
                pages_scanned: data.pages_scanned,
                total_violations: data.total_violations
            });

            // Update stat blocks
            pagesScanned.textContent = data.pages_scanned || 0;
            issuesFound.textContent = data.total_violations || 0;

            // Update progress bar
            const progress = Math.min(30 + (data.pages_scanned * 3), 90);
            progressBar.style.width = `${progress}%`;
            progressPercent.textContent = `${progress}%`;

            // Update estimated time remaining
            if (data.estimated_time_remaining_formatted) {
                estimatedTime.textContent = `Estimated time remaining: ${data.estimated_time_remaining_formatted}`;
            } else if (data.pages_scanned === 0) {
                estimatedTime.textContent = 'Calculating...';
            } else {
                estimatedTime.textContent = 'Completing...';
            }

            // Update status text
            progressText.innerHTML = `<strong>Scanning:</strong> ${data.pages_scanned} pages analyzed, ${data.total_violations} issues found`;

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                progressBar.style.width = '100%';
                progressPercent.textContent = '100%';
                progressText.innerHTML = '<strong class="text-success">✓ Scan complete!</strong> Redirecting to results...';
                setTimeout(() => {
                    window.location.href = `/results/${scanId}`;
                }, 1500);
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                alert('Scan failed: ' + (data.error_message || 'Unknown error'));
                scanButton.disabled = false;
                progressSection.style.display = 'none';
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 2000);
}

// Check if page loaded with a resumed scan
document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const scanId = urlParams.get('scan_id');
    const resumed = urlParams.get('resumed');

    if (scanId && resumed === 'true') {
        try {
            // Fetch scan details from API
            const response = await fetch(`/api/scan/${scanId}`);
            const scanData = await response.json();

            // Get form elements
            const urlInput = document.getElementById('url');
            const maxPagesInput = document.getElementById('maxPages');
            const maxDepthInput = document.getElementById('maxDepth');
            const progressSection = document.getElementById('progressSection');
            const progressText = document.getElementById('progressText');
            const scanButton = document.getElementById('scanButton');
            const pagesScanned = document.getElementById('pagesScanned');
            const issuesFound = document.getElementById('issuesFound');
            const progressBar = document.getElementById('progressBar');
            const progressPercent = document.getElementById('progressPercent');

            // Pre-fill form fields with resumed scan configuration
            if (urlInput) urlInput.value = scanData.start_url || '';
            if (maxPagesInput) maxPagesInput.value = scanData.max_pages || 25;
            if (maxDepthInput) maxDepthInput.value = scanData.max_depth || 3;

            // Initialize progress stats with current values
            pagesScanned.textContent = scanData.pages_scanned || 0;
            issuesFound.textContent = scanData.total_violations || 0;

            // Calculate initial progress
            const initialProgress = Math.min(30 + ((scanData.pages_scanned || 0) * 3), 90);
            progressBar.style.width = `${initialProgress}%`;
            progressPercent.textContent = `${initialProgress}%`;

            // Set initial estimated time
            if (scanData.estimated_time_remaining_formatted) {
                estimatedTime.textContent = `Estimated time remaining: ${scanData.estimated_time_remaining_formatted}`;
            } else {
                estimatedTime.textContent = 'Calculating...';
            }

            // Show progress section
            progressSection.style.display = 'block';
            progressText.innerHTML = `<strong>Scan resumed successfully!</strong> Continuing from checkpoint (${scanData.pages_scanned || 0} pages already scanned)...`;
            scanButton.disabled = true;

            // Start polling the resumed scan
            pollScanStatus(scanId);
        } catch (error) {
            console.error('Error loading resumed scan:', error);
            alert('Failed to load scan details. Redirecting to history...');
            window.location.href = '/history';
        }
    }
});

