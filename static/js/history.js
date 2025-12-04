/* History Page JavaScript */

let allScans = [];
let deleteTargetId = null;
let deleteModal = null;
let bulkDeleteModal = null;
const isAdmin = document.querySelector('body').dataset.isAdmin === 'true';

// Pagination configuration
const SCANS_PER_PAGE = 100;
let currentPage = 1;
let filteredScans = [];  // Scans after search/filter, before pagination

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

function selectAllScansAcrossAllPages() {
    // Get all scan IDs from filtered scans
    const allScanIds = filteredScans.map(scan => scan.scan_id);

    // Check all checkboxes on current page
    const checkboxes = document.querySelectorAll('.scan-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = true;
    });

    // Note: This only selects visible scans on current page
    // To select across all pages would require different UX
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

// Export selected scans to Excel
async function exportToExcel(mode = 'selected') {
    let scanIdsToExport = [];

    if (mode === 'all') {
        // Export all filtered scans (respects search/filter)
        scanIdsToExport = filteredScans.map(scan => scan.scan_id);

        if (scanIdsToExport.length === 0) {
            alert('No scans available to export.');
            return;
        }

        // Confirm for very large exports
        if (scanIdsToExport.length > 100) {
            const confirmed = confirm(
                `You are about to export ALL ${scanIdsToExport.length} scans. ` +
                `This may take several minutes to complete. ` +
                `\n\nDo you want to continue?`
            );
            if (!confirmed) return;
        } else {
            // Confirm export all
            const confirmed = confirm(
                `Export all ${scanIdsToExport.length} scans to Excel?`
            );
            if (!confirmed) return;
        }
    } else {
        // Export only selected scans on current page
        scanIdsToExport = getSelectedScanIds();

        if (scanIdsToExport.length === 0) {
            alert('Please select at least one scan to export.');
            return;
        }

        // Warn for very large exports
        if (scanIdsToExport.length > 100) {
            const confirmed = confirm(
                `You are about to export ${scanIdsToExport.length} selected scans. ` +
                `This may take several minutes to complete. ` +
                `\n\nDo you want to continue?`
            );
            if (!confirmed) return;
        }
    }

    const exportOverlay = document.getElementById('exportOverlay');
    const spinnerText = document.querySelector('.export-spinner-text');
    const spinnerSubtext = document.querySelector('.export-spinner-subtext');

    try {
        // Show spinner with appropriate message
        if (mode === 'all') {
            spinnerText.textContent = `Generating Excel Report for ${scanIdsToExport.length} Scans...`;
        } else {
            spinnerText.textContent = `Generating Excel Report for ${scanIdsToExport.length} Selected Scan${scanIdsToExport.length > 1 ? 's' : ''}...`;
        }
        spinnerSubtext.textContent = scanIdsToExport.length > 50
            ? 'This may take several minutes for large exports'
            : 'This may take a moment for large scans';

        exportOverlay.classList.add('show');

        const response = await fetch('/api/history/scans/export/bulk-excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(scanIdsToExport)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate Excel report');
        }

        // Get the blob from response
        const blob = await response.blob();

        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'accessibility_report_bulk.xlsx';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Clear selection after successful export (only for 'selected' mode)
        if (mode === 'selected') {
            clearSelection();
        }

    } catch (error) {
        console.error('Error exporting to Excel:', error);
        alert(`Failed to export scans: ${error.message}`);
    } finally {
        // Hide spinner
        exportOverlay.classList.remove('show');
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
    const scanList = document.getElementById('scanList');

    // Show loading indicator
    scanList.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading scan history...</span>
            </div>
            <p class="mt-3 text-muted">Loading scan history...</p>
        </div>
    `;

    try {
        let url = '/api/history/scans?limit=10000';

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

        console.log(`Loaded ${allScans.length} scans from server`);
        displayScans(allScans);
    } catch (error) {
        console.error('Failed to load scans:', error);
        scanList.innerHTML = `
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
    const displayedCount = document.getElementById('displayedCount');
    const totalCount = document.getElementById('totalCount');

    // Store filtered scans for pagination
    filteredScans = scans;

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
        document.getElementById('paginationContainer').style.display = 'none';
        return;
    }

    // Calculate pagination
    const totalPages = Math.ceil(scans.length / SCANS_PER_PAGE);

    // Ensure current page is valid
    if (currentPage > totalPages) {
        currentPage = totalPages;
    }
    if (currentPage < 1) {
        currentPage = 1;
    }

    const startIndex = (currentPage - 1) * SCANS_PER_PAGE;
    const endIndex = Math.min(startIndex + SCANS_PER_PAGE, scans.length);
    const paginatedScans = scans.slice(startIndex, endIndex);

    // Show select all container when there are scans
    selectAllContainer.style.display = 'block';

    // Update counts - show range for current page
    const displayStart = startIndex + 1;
    const displayEnd = endIndex;
    displayedCount.textContent = `${displayStart}-${displayEnd}`;
    totalCount.textContent = scans.length;

    let html = '';
    paginatedScans.forEach((scan, index) => {
        const statusColors = {
            'completed': 'success',
            'running': 'primary',
            'in_progress': 'primary',
            'failed': 'danger'
        };
        const statusColor = statusColors[scan.status] || 'secondary';

        const startDate = new Date(scan.start_time);
        const formattedDate = startDate.toLocaleString();
        const cardNumber = startIndex + index + 1;  // Absolute number across all pages

        html += `
            <div class="card scan-card mb-3">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <div class="scan-card-number">
                                #${cardNumber}
                            </div>
                        </div>
                        <div class="col-auto">
                            <div class="form-check">
                                <input
                                    class="form-check-input scan-checkbox"
                                    type="checkbox"
                                    id="scan_${scan.scan_id}"
                                    value="${scan.scan_id}"
                                    onchange="updateSelection()"
                                    aria-label="Select scan number ${cardNumber} for ${scan.start_url}">
                            </div>
                        </div>
                        <div class="col-md-4">
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

    // Render pagination controls
    renderPagination(totalPages, scans.length);

    updateSelection(); // Update selection state
}

function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// Render pagination controls
function renderPagination(totalPages, totalScans) {
    const paginationContainer = document.getElementById('paginationContainer');

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'block';

    let html = '<nav aria-label="Scan history pagination"><ul class="pagination justify-content-center mb-0">';

    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;" aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
    `;

    // Page numbers with smart truncation
    const maxVisiblePages = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    // Adjust start if we're near the end
    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    // First page + ellipsis
    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(1); return false;">1</a></li>`;
        if (startPage > 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
            </li>
        `;
    }

    // Ellipsis + last page
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages}); return false;">${totalPages}</a></li>`;
    }

    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;

    html += '</ul></nav>';

    // Add page info text
    html += `<div class="text-center mt-2 text-muted small">Page ${currentPage} of ${totalPages}</div>`;

    paginationContainer.innerHTML = html;
}

// Change page function
function changePage(newPage) {
    const totalPages = Math.ceil(filteredScans.length / SCANS_PER_PAGE);

    if (newPage < 1 || newPage > totalPages) {
        return;
    }

    currentPage = newPage;
    displayScans(filteredScans);

    // Scroll to top of scan list
    document.getElementById('scanList').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Filter scans
function filterScans() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;

    const filtered = allScans.filter(scan => {
        const matchesSearch = scan.start_url.toLowerCase().includes(searchTerm);
        const matchesStatus = !statusFilter || scan.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Reset to page 1 when filtering
    currentPage = 1;
    displayScans(filtered);
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

