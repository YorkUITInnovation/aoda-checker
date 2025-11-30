/**
 * Admin Check Configuration Page JavaScript
 * Used by: admin_checks.html
 */

let allChecks = [];
let editModal;

document.addEventListener('DOMContentLoaded', function() {
    editModal = new bootstrap.Modal(document.getElementById('editModal'));
    loadChecks();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('initializeBtn').addEventListener('click', initializeChecks);
    document.getElementById('saveBtn').addEventListener('click', saveCheck);
    document.getElementById('filterStatus').addEventListener('change', filterChecks);
    document.getElementById('filterSeverity').addEventListener('change', filterChecks);
    document.getElementById('filterWCAG').addEventListener('change', filterChecks);
    document.getElementById('searchInput').addEventListener('input', filterChecks);
}

async function loadChecks() {
    try {
        console.log('Fetching checks from API...');
        const response = await fetch('/api/admin/checks/');
        if (!response.ok) throw new Error('Failed to load checks');

        allChecks = await response.json();
        console.log(`Loaded ${allChecks.length} checks from API:`, allChecks.map(c => c.check_id));
        renderChecks(allChecks);
    } catch (error) {
        console.error('Error loading checks:', error);
        showAlert('Failed to load checks', 'danger');
    }
}

// Escape HTML to prevent XSS and template literal breaks
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderChecks(checks) {
    const tbody = document.getElementById('checksTableBody');

    console.log(`Rendering ${checks.length} checks`);

    if (checks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
                    No checks found. Click "Initialize Default Checks" to load default configuration.
                </td>
            </tr>
        `;
        return;
    }

    try {
        tbody.innerHTML = checks.map((check, index) => {
            try {
                // Escape all text values to prevent template literal breaks
                const safeCheckId = escapeHtml(check.check_id);
                const safeName = escapeHtml(check.check_name);
                const safeDesc = escapeHtml(check.description || 'No description');
                const safeSeverity = escapeHtml(check.severity);
                const safeType = escapeHtml(check.check_type);
                const safeWcagCrit = escapeHtml(check.wcag_criterion);
                const safeWcagLevel = escapeHtml(check.wcag_level);
                const safeHelpUrl = check.help_url || '';

                return `
            <tr class="check-row" data-check-id="${safeCheckId}">
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input enabled-switch" type="checkbox"
                               ${check.enabled ? 'checked' : ''}
                               onchange="toggleCheck('${safeCheckId}', this.checked)">
                    </div>
                </td>
                <td>
                    <strong>${safeName}</strong>
                    <br>
                    <small class="text-muted">${safeCheckId}</small>
                </td>
                <td>
                    <small>${safeDesc}</small>
                </td>
                <td>
                    <span class="badge severity-badge ${getSeverityClass(check.severity)}">
                        ${safeSeverity.toUpperCase()}
                    </span>
                </td>
                <td>
                    ${check.wcag_criterion ? `
                        <span class="badge bg-info wcag-badge">
                            ${safeWcagCrit} (${safeWcagLevel})
                        </span>
                        ${check.aoda_required ? '<br><span class="badge bg-success wcag-badge mt-1">AODA Required</span>' : ''}
                    ` : '<span class="text-muted">N/A</span>'}
                </td>
                <td>
                    <span class="badge bg-secondary">${safeType}</span>
                </td>
                <td class="table-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="editCheck('${safeCheckId}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                    ${safeHelpUrl ? `
                        <a href="${safeHelpUrl}" target="_blank" class="btn btn-sm btn-outline-info">
                            <i class="bi bi-info-circle"></i>
                        </a>
                    ` : ''}
                </td>
            </tr>
        `;
            } catch (err) {
                console.error(`Error rendering check ${index}:`, check, err);
                const safeCheckId = escapeHtml(check.check_id || 'unknown');
                const safeErrMsg = escapeHtml(err.message);
                return `
                    <tr>
                        <td colspan="7" class="text-danger">
                            Error rendering check: ${safeCheckId} - ${safeErrMsg}
                        </td>
                    </tr>
                `;
            }
        }).join('');
        console.log(`Successfully rendered ${checks.length} check rows`);
    } catch (err) {
        console.error('Error in renderChecks:', err);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-danger">
                    Error rendering checks: ${err.message}
                </td>
            </tr>
        `;
    }
}

function getSeverityClass(severity) {
    const classes = {
        'error': 'bg-danger',
        'warning': 'bg-warning text-dark',
        'alert': 'bg-info',
        'disabled': 'bg-secondary'
    };
    return classes[severity] || 'bg-secondary';
}

function filterChecks() {
    const status = document.getElementById('filterStatus').value;
    const severity = document.getElementById('filterSeverity').value;
    const wcag = document.getElementById('filterWCAG').value;
    const search = document.getElementById('searchInput').value.toLowerCase();

    const filtered = allChecks.filter(check => {
        if (status !== 'all' && ((status === 'enabled') !== check.enabled)) return false;
        if (severity !== 'all' && check.severity !== severity) return false;
        if (wcag !== 'all' && check.wcag_level !== wcag) return false;
        if (search && !check.check_name.toLowerCase().includes(search) &&
            !check.check_id.toLowerCase().includes(search)) return false;
        return true;
    });

    renderChecks(filtered);
}

async function toggleCheck(checkId, enabled) {
    const check = allChecks.find(c => c.check_id === checkId);
    if (!check) return;

    try {
        const response = await fetch(`/api/admin/checks/${checkId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enabled: enabled,
                severity: check.severity
            })
        });

        if (!response.ok) throw new Error('Failed to update check');

        check.enabled = enabled;
        showAlert(`Check ${enabled ? 'enabled' : 'disabled'} successfully`, 'success');
    } catch (error) {
        console.error('Error updating check:', error);
        showAlert('Failed to update check', 'danger');
        loadChecks(); // Reload to reset state
    }
}

function editCheck(checkId) {
    const check = allChecks.find(c => c.check_id === checkId);
    if (!check) return;

    document.getElementById('editCheckId').value = check.check_id;
    document.getElementById('editCheckName').value = check.check_name;
    document.getElementById('editEnabled').checked = check.enabled;
    document.getElementById('editSeverity').value = check.severity;

    editModal.show();
}

async function saveCheck() {
    const checkId = document.getElementById('editCheckId').value;
    const enabled = document.getElementById('editEnabled').checked;
    const severity = document.getElementById('editSeverity').value;

    try {
        const response = await fetch(`/api/admin/checks/${checkId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled, severity })
        });

        if (!response.ok) throw new Error('Failed to save check');

        const check = allChecks.find(c => c.check_id === checkId);
        if (check) {
            check.enabled = enabled;
            check.severity = severity;
        }

        editModal.hide();
        renderChecks(allChecks);
        showAlert('Check configuration saved successfully', 'success');
    } catch (error) {
        console.error('Error saving check:', error);
        showAlert('Failed to save check configuration', 'danger');
    }
}

async function initializeChecks() {
    if (!confirm('This will initialize default check configurations. Continue?')) return;

    try {
        const response = await fetch('/api/admin/checks/initialize', {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to initialize checks');

        showAlert('Default checks initialized successfully', 'success');
        loadChecks();
    } catch (error) {
        console.error('Error initializing checks:', error);
        showAlert('Failed to initialize checks', 'danger');
    }
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

