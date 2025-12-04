/* History Page JavaScript */

let allScans = [];
let deleteTargetId = null;
let deleteModal = null;
let bulkDeleteModal = null;
const isAdmin = document.querySelector('body').dataset.isAdmin === 'true';

// Bulk selection functions
function getSelectedScanIds() {
    const checkboxes = document.querySelectorAll('.scan-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function updateSelection() {
    const selectedIds = getSelectedScanIds();
    const bulkActionBar = document.getElementById('bulkActionBar');
    const selectedCount = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const allCheckboxes = document.querySelectorAll('.scan-checkbox');

    selectedCount.textContent = selectedIds.length;

    if (selectedIds.length > 0) {
        bulkActionBar.classList.add('show');
    } else {
        bulkActionBar.classList.remove('show');
    }

    // Update select all checkbox state
    if (allCheckboxes.length > 0) {
        selectAllCheckbox.checked = selectedIds.length === allCheckboxes.length;
        selectAllCheckbox.indeterminate = selectedIds.length > 0 && selectedIds.length < allCheckboxes.length;
    }
}

function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.scan-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
    updateSelection();
}

function clearSelection() {
    const checkboxes = document.querySelectorAll('.scan-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = false;
    });
    updateSelection();
}

function confirmBulkDelete() {
    const selectedIds = getSelectedScanIds();
    if (selectedIds.length === 0) return;

    const bulkDeleteCount = document.getElementById('bulkDeleteCount');
    const bulkDeleteList = document.getElementById('bulkDeleteList');

    bulkDeleteCount.textContent = selectedIds.length;

    // Build list of scans to delete
    let listHtml = '<ul class="list-group">';
    selectedIds.forEach(scanId => {
        const scan = allScans.find(s => s.scan_id === scanId);
        if (scan) {
            listHtml += `
                <li class="list-group-item">
                    <i class="bi bi-link-45deg"></i>
                    <small class="text-break">${scan.start_url}</small>
                </li>
            `;
        }
    });
    listHtml += '</ul>';
    bulkDeleteList.innerHTML = listHtml;

    if (!bulkDeleteModal) {
        bulkDeleteModal = new bootstrap.Modal(document.getElementById('bulkDeleteModal'));
    }
    bulkDeleteModal.show();
}

async function bulkDeleteScans() {
    const selectedIds = getSelectedScanIds();
    if (selectedIds.length === 0) return;

    const deleteBtn = document.getElementById('confirmBulkDeleteBtn');
    const originalText = deleteBtn.innerHTML;

    try {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';

        // Delete scans one by one
        let successCount = 0;
        let failCount = 0;

        for (const scanId of selectedIds) {
            try {
                const response = await fetch(`/api/history/scans/${scanId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                console.error(`Failed to delete scan ${scanId}:`, error);
                failCount++;
            }
        }

        bulkDeleteModal.hide();
        clearSelection();
        await loadScans();
        await loadStatistics();

        // Show result message
        if (failCount > 0) {
            alert(`Deleted ${successCount} scan(s). Failed to delete ${failCount} scan(s).`);
        }

    } catch (error) {
        console.error('Error during bulk delete:', error);
        alert('Failed to delete scans. Please try again.');
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
    }
}

// Load users for admin filter
async function loadUsers() {
    if (!isAdmin) return;

    try {
        const response = await fetch('/api/history/users');
        const users = await response.json();

        const userSelect = document.getElementById('specificUserSelect');
        userSelect.innerHTML = '<option value="">Select a user...</option>';
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.full_name ? `${user.username} (${user.full_name})` : user.username;
            userSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

// Handle user filter change
if (isAdmin) {
    document.addEventListener('DOMContentLoaded', () => {
        const userFilter = document.getElementById('userFilter');
        const specificUserFilter = document.getElementById('specificUserFilter');
        const specificUserSelect = document.getElementById('specificUserSelect');

        if (userFilter) {
            userFilter.addEventListener('change', function() {
                if (this.value === 'by-user') {
                    specificUserFilter.style.display = 'block';
                } else {
                    specificUserFilter.style.display = 'none';
                    loadScans();
                }
            });
        }

        if (specificUserSelect) {
            specificUserSelect.addEventListener('change', function() {
                if (this.value) {
                    loadScans();
                }
            });
        }
    });
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/history/statistics');
        const stats = await response.json();

        const statsHtml = `
            <div class="col-md-4">
                <div class="stat-box">
                    <div class="stat-number">${stats.total_scans}</div>
                    <div class="stat-label">Total Scans${stats.is_user_specific ? ' (Your Scans)' : ''}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-box">
                    <div class="stat-number">${stats.scans_by_status.completed || 0}</div>
                    <div class="stat-label">Completed${stats.is_user_specific ? ' (Your Scans)' : ''}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-box">
                    <div class="stat-number">${stats.total_violations.toLocaleString()}</div>
                    <div class="stat-label">Total Violations${stats.is_user_specific ? ' (Your Scans)' : ''}</div>
                </div>
            </div>
        `;

        document.getElementById('statistics').innerHTML = statsHtml;
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load scan history
async function loadScans() {
    try {
        let url = '/api/history/scans?limit=100';

        if (isAdmin) {
            const userFilter = document.getElementById('userFilter');
            if (userFilter) {
                const userFilterValue = userFilter.value;
                if (userFilterValue === 'all') {
                    url += '&all_scans=true';
                } else if (userFilterValue === 'by-user') {
                    const userId = document.getElementById('specificUserSelect').value;
                    if (userId) {
                        url += `&user_id=${userId}`;
                    }
                }
            }
        }

        const response = await fetch(url);
        allScans = await response.json();
        displayScans(allScans);
    } catch (error) {
        console.error('Failed to load scans:', error);
        document.getElementById('scanList').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load scan history. Please try refreshing the page.
            </div>
        `;
    }
}

// Display scans
function displayScans(scans) {
    const scanList = document.getElementById('scanList');
    const selectAllContainer = document.getElementById('selectAllContainer');

    if (scans.length === 0) {
        scanList.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox display-1 text-muted"></i>
                <h3 class="mt-3">No scans found</h3>
                <p class="text-muted">Start your first accessibility scan to see results here.</p>
                <a href="/" class="btn btn-outline-primary mt-3">
                    <i class="bi bi-plus-circle"></i> Create New Scan
                </a>
            </div>
        `;
        selectAllContainer.style.display = 'none';
        return;
    }

    // Show select all container when there are scans
    selectAllContainer.style.display = 'block';

    let html = '';
    scans.forEach(scan => {
        const statusColors = {
            'completed': 'success',
            'running': 'primary',
            'in_progress': 'primary',
            'failed': 'danger'
        };
        const statusColor = statusColors[scan.status] || 'secondary';

        const startDate = new Date(scan.start_time);
        const formattedDate = startDate.toLocaleString();

        html += `
            <div class="card scan-card mb-3">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <div class="form-check">
                                <input
                                    class="form-check-input scan-checkbox"
                                    type="checkbox"
                                    id="scan_${scan.scan_id}"
                                    value="${scan.scan_id}"
                                    onchange="updateSelection()"
                                    aria-label="Select scan for ${scan.start_url}">
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h5 class="card-title mb-2">
                                <i class="bi bi-link-45deg"></i>
                                <a href="${scan.start_url}" target="_blank" class="text-decoration-none">
                                    ${truncateUrl(scan.start_url, 50)}
                                </a>
                            </h5>
                            <p class="text-muted small mb-1">
                                <i class="bi bi-clock"></i> ${formattedDate}
                            </p>
                            <p class="text-muted small mb-1">
                                <i class="bi bi-shield-check"></i>
                                ${scan.scan_mode === 'aoda' ? 'Ontario AODA' : 'WCAG 2.1'}
                            </p>
                            <p class="text-muted small mb-0">
                                <i class="bi bi-gear"></i>
                                Max Pages: ${scan.max_pages || 'N/A'} | Max Depth: ${scan.max_depth || 'N/A'}
                            </p>
                        </div>
                        <div class="col-md-3">
                            <div class="d-flex gap-4 justify-content-center mt-2 mt-md-0">
                                <div class="text-center">
                                    <div class="fw-bold fs-5">${scan.pages_scanned}</div>
                                    <div class="small text-muted">Pages</div>
                                </div>
                                <div class="text-center">
                                    <div class="fw-bold fs-5 text-${scan.total_violations > 0 ? 'danger' : 'success'}">
                                        ${scan.total_violations}
                                    </div>
                                    <div class="small text-muted">Issues</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3 text-md-end mt-3 mt-md-0">
                            <span class="badge bg-${statusColor} mb-2 d-inline-block">
                                ${scan.status.toUpperCase()}
                            </span>
                            <br>
                            <div class="btn-group" role="group">
                                ${scan.status === 'completed' ? `
                                    <a href="/results/${scan.scan_id}" class="btn btn-sm btn-outline-primary">
                                        <i class="bi bi-eye"></i> View
                                    </a>
                                ` : ''}
                                ${scan.status === 'failed' || scan.status === 'in_progress' ? `
                                    <button
                                        class="btn btn-sm btn-outline-primary"
                                        onclick="confirmResume('${scan.scan_id}', '${scan.start_url.replace(/'/g, "\\'")}', ${scan.pages_scanned})">
                                        <i class="bi bi-arrow-clockwise"></i> Resume
                                    </button>
                                ` : ''}
                                <button
                                    class="btn btn-sm btn-outline-danger"
                                    onclick="confirmDelete('${scan.scan_id}', '${scan.start_url.replace(/'/g, "\\'")}')">
                                    <i class="bi bi-trash"></i> Delete
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    scanList.innerHTML = html;
    updateSelection(); // Update selection state
}

function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// Filter scans
function filterScans() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;

    const filteredScans = allScans.filter(scan => {
        const matchesSearch = scan.start_url.toLowerCase().includes(searchTerm);
        const matchesStatus = !statusFilter || scan.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    displayScans(filteredScans);
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');

    if (searchInput) {
        searchInput.addEventListener('input', filterScans);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterScans);
    }
});

// Delete confirmation
function confirmDelete(scanId, scanUrl) {
    deleteTargetId = scanId;
    document.getElementById('deleteUrl').textContent = scanUrl;

    if (!deleteModal) {
        deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    }
    deleteModal.show();
}

// Delete scan
async function deleteScan() {
    if (!deleteTargetId) return;

    const deleteBtn = document.getElementById('confirmDeleteBtn');
    const originalText = deleteBtn.innerHTML;

    try {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';

        const response = await fetch(`/api/history/scans/${deleteTargetId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete scan');
        }

        deleteModal.hide();
        await loadScans();
        await loadStatistics();

    } catch (error) {
        console.error('Error deleting scan:', error);
        alert('Failed to delete scan. Please try again.');
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
        deleteTargetId = null;
    }
}

// Resume confirmation
let resumeTargetId = null;
let resumeModal = null;

function confirmResume(scanId, scanUrl, pagesScanned) {
    resumeTargetId = scanId;
    document.getElementById('resumeUrl').textContent = scanUrl;
    document.getElementById('resumeProgress').textContent = pagesScanned.toLocaleString();

    if (!resumeModal) {
        resumeModal = new bootstrap.Modal(document.getElementById('resumeModal'));
    }
    resumeModal.show();
}

// Resume scan
async function resumeScan() {
    if (!resumeTargetId) return;

    const resumeBtn = document.getElementById('confirmResumeBtn');
    const originalText = resumeBtn.innerHTML;

    try {
        resumeBtn.disabled = true;
        resumeBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Resuming...';

        const response = await fetch(`/api/scan/resume/${resumeTargetId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to resume scan');
        }

        const result = await response.json();
        resumeModal.hide();

        // Redirect to home page to show scan progress
        window.location.href = `/?scan_id=${result.scan_id}&resumed=true`;

    } catch (error) {
        console.error('Error resuming scan:', error);
        alert(`Failed to resume scan: ${error.message}`);
        resumeBtn.disabled = false;
        resumeBtn.innerHTML = originalText;
        resumeTargetId = null;
    }
}

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadScans();
    if (isAdmin) {
        loadUsers();
    }

    // Auto-refresh every 30 seconds if there are running scans
    setInterval(() => {
        if (allScans.some(scan => scan.status === 'running')) {
            loadScans();
            loadStatistics();
        }
    }, 30000);
});

