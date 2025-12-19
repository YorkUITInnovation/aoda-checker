/* Scheduled Logs Page JavaScript */

let allLogs = [];
let deleteTargetId = null;
let deleteModal = null;
let bulkDeleteModal = null;

const LOGS_PER_PAGE = 50;
let currentPage = 1;
let totalLogs = 0;

// Selection management
function getSelectedLogIds() {
    const checkboxes = document.querySelectorAll('.log-checkbox:checked');
    return Array.from(checkboxes).map(cb => parseInt(cb.value));
}

function updateSelection() {
    const selectedIds = getSelectedLogIds();
    const bulkActionBar = document.getElementById('bulkActionBar');
    const selectedCount = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const allCheckboxes = document.querySelectorAll('.log-checkbox');

    selectedCount.textContent = selectedIds.length;

    if (selectedIds.length > 0) {
        bulkActionBar.classList.add('show');
    } else {
        bulkActionBar.classList.remove('show');
    }

    if (allCheckboxes.length > 0) {
        selectAllCheckbox.checked = selectedIds.length === allCheckboxes.length;
        selectAllCheckbox.indeterminate = selectedIds.length > 0 && selectedIds.length < allCheckboxes.length;
    }
}

function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.log-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
    updateSelection();
}

function clearSelection() {
    const checkboxes = document.querySelectorAll('.log-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = false;
    });
    updateSelection();
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/scheduled-logs/statistics');
        const stats = await response.json();

        const statsHtml = `
            <div class="col-md-3">
                <div class="stat-box">
                    <div class="stat-number">${stats.total}</div>
                    <div class="stat-label">Total Executions</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box success">
                    <div class="stat-number">${stats.success}</div>
                    <div class="stat-label">Successful</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box failed">
                    <div class="stat-number">${stats.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box">
                    <div class="stat-number">${stats.success_rate}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>
        `;

        document.getElementById('statistics').innerHTML = statsHtml;
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load logs
async function loadLogs() {
    const logsList = document.getElementById('logsList');

    logsList.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading logs...</span>
            </div>
            <p class="mt-3 text-muted">Loading scheduled task logs...</p>
        </div>
    `;

    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const sortBy = document.getElementById('sortBy').value;
        const sortOrder = document.getElementById('sortOrder').value;

        let url = `/api/scheduled-logs?limit=${LOGS_PER_PAGE}&offset=${(currentPage - 1) * LOGS_PER_PAGE}`;
        url += `&sort_by=${sortBy}&sort_order=${sortOrder}`;

        if (statusFilter) url += `&status=${statusFilter}`;
        if (startDate) url += `&start_date=${startDate}T00:00:00`;
        if (endDate) url += `&end_date=${endDate}T23:59:59`;

        const response = await fetch(url);
        const data = await response.json();

        allLogs = data.logs;
        totalLogs = data.total;

        displayLogs(data.logs);
        renderPagination();
    } catch (error) {
        console.error('Failed to load logs:', error);
        logsList.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load logs. Please try refreshing the page.
            </div>
        `;
    }
}

// Display logs
function displayLogs(logs) {
    const logsList = document.getElementById('logsList');
    const selectAllContainer = document.getElementById('selectAllContainer');
    const displayedCount = document.getElementById('displayedCount');
    const totalCount = document.getElementById('totalCount');

    if (logs.length === 0) {
        logsList.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox display-1 text-muted"></i>
                <h3 class="mt-3">No logs found</h3>
                <p class="text-muted">Scheduled scan logs will appear here once your scheduled scans run.</p>
            </div>
        `;
        selectAllContainer.style.display = 'none';
        document.getElementById('paginationContainer').style.display = 'none';
        return;
    }

    selectAllContainer.style.display = 'block';
    displayedCount.textContent = logs.length;
    totalCount.textContent = totalLogs;

    let html = '';
    logs.forEach((log, index) => {
        const statusColor = log.status === 'success' ? 'success' : 'danger';
        const statusIcon = log.status === 'success' ? 'check-circle-fill' : 'x-circle-fill';
        const executedDate = new Date(log.executed_at);
        const formattedDate = executedDate.toLocaleString();
        const logNumber = (currentPage - 1) * LOGS_PER_PAGE + index + 1;

        html += `
            <div class="card log-card mb-3">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <div class="log-card-number">#${logNumber}</div>
                        </div>
                        <div class="col-auto">
                            <div class="form-check">
                                <input
                                    class="form-check-input log-checkbox"
                                    type="checkbox"
                                    id="log_${log.id}"
                                    value="${log.id}"
                                    onchange="updateSelection()">
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h6 class="mb-2">
                                <i class="bi bi-link-45deg"></i>
                                ${truncateUrl(log.start_url, 60)}
                            </h6>
                            <p class="text-muted small mb-0">
                                <i class="bi bi-clock"></i> ${formattedDate}
                            </p>
                        </div>
                        <div class="col-md-3">
                            ${log.status === 'success' ? `
                                <div class="mb-1">
                                    <i class="bi bi-file-earmark-text"></i>
                                    <strong>Pages:</strong> ${log.pages_scanned}
                                </div>
                                <div class="mb-1">
                                    <i class="bi bi-exclamation-triangle"></i>
                                    <strong>Violations:</strong> ${log.total_violations}
                                </div>
                                ${log.email_sent ? '<div class="text-success small"><i class="bi bi-envelope-check"></i> Email sent</div>' : ''}
                            ` : `
                                <div class="text-danger small">
                                    <i class="bi bi-exclamation-circle"></i>
                                    ${log.error_message || 'Scan failed'}
                                </div>
                            `}
                            ${log.duration_seconds ? `
                                <div class="text-muted small mt-1">
                                    <i class="bi bi-stopwatch"></i> ${formatDuration(log.duration_seconds)}
                                </div>
                            ` : ''}
                        </div>
                        <div class="col-md-2 text-end">
                            <span class="badge bg-${statusColor} mb-2 d-inline-block">
                                <i class="bi bi-${statusIcon}"></i>
                                ${log.status.toUpperCase()}
                            </span>
                            <br>
                            ${log.scan_id ? `
                                <a href="/results/${log.scan_id}" class="btn btn-sm btn-outline-primary mb-1">
                                    <i class="bi bi-eye"></i> View Scan
                                </a>
                                <br>
                            ` : ''}
                            <button
                                class="btn btn-sm btn-outline-danger"
                                onclick="confirmDelete(${log.id})">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    logsList.innerHTML = html;
    updateSelection();
}

// Pagination
function renderPagination() {
    const container = document.getElementById('paginationContainer');
    const totalPages = Math.ceil(totalLogs / LOGS_PER_PAGE);

    if (totalPages <= 1) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    let html = '<nav aria-label="Log pagination"><ul class="pagination justify-content-center">';

    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;">Previous</a>
        </li>
    `;

    // Page numbers
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(1); return false;">1</a></li>`;
        if (startPage > 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
            </li>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages}); return false;">${totalPages}</a></li>`;
    }

    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;">Next</a>
        </li>
    `;

    html += '</ul></nav>';
    container.innerHTML = html;
}

function changePage(newPage) {
    const totalPages = Math.ceil(totalLogs / LOGS_PER_PAGE);
    if (newPage < 1 || newPage > totalPages) return;

    currentPage = newPage;
    loadLogs();
    document.getElementById('logsList').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Filters
function clearFilters() {
    document.getElementById('statusFilter').value = '';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    currentPage = 1;
    loadLogs();
}

// Delete functions
function confirmDelete(logId) {
    deleteTargetId = logId;

    if (!deleteModal) {
        deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    }
    deleteModal.show();
}

async function deleteLog() {
    if (!deleteTargetId) return;

    const deleteBtn = document.getElementById('confirmDeleteBtn');
    const originalText = deleteBtn.innerHTML;

    try {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';

        const response = await fetch(`/api/scheduled-logs/${deleteTargetId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete log');
        }

        deleteModal.hide();
        deleteTargetId = null;

        await loadLogs();
        await loadStatistics();

    } catch (error) {
        console.error('Error deleting log:', error);
        alert(`Failed to delete log: ${error.message}`);
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
    }
}

function confirmBulkDelete() {
    const selectedIds = getSelectedLogIds();
    if (selectedIds.length === 0) return;

    document.getElementById('bulkDeleteCount').textContent = selectedIds.length;

    if (!bulkDeleteModal) {
        bulkDeleteModal = new bootstrap.Modal(document.getElementById('bulkDeleteModal'));
    }
    bulkDeleteModal.show();
}

async function bulkDeleteLogs() {
    const selectedIds = getSelectedLogIds();
    if (selectedIds.length === 0) return;

    const deleteBtn = document.getElementById('confirmBulkDeleteBtn');
    const originalText = deleteBtn.innerHTML;

    try {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';

        const response = await fetch('/api/scheduled-logs/bulk-delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(selectedIds)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete logs');
        }

        const result = await response.json();

        bulkDeleteModal.hide();
        clearSelection();

        alert(result.message);

        await loadLogs();
        await loadStatistics();

    } catch (error) {
        console.error('Error deleting logs:', error);
        alert(`Failed to delete logs: ${error.message}`);
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
    }
}

// Utility functions
function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength - 3) + '...';
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadLogs();

    const statusFilter = document.getElementById('statusFilter');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const sortBy = document.getElementById('sortBy');
    const sortOrder = document.getElementById('sortOrder');

    if (statusFilter) statusFilter.addEventListener('change', () => { currentPage = 1; loadLogs(); });
    if (startDate) startDate.addEventListener('change', () => { currentPage = 1; loadLogs(); });
    if (endDate) endDate.addEventListener('change', () => { currentPage = 1; loadLogs(); });
    if (sortBy) sortBy.addEventListener('change', () => { currentPage = 1; loadLogs(); });
    if (sortOrder) sortOrder.addEventListener('change', () => { currentPage = 1; loadLogs(); });
});

