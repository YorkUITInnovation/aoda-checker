// User Check Configuration JavaScript

let allChecks = [];
let currentFilter = 'all';
let currentSearchTerm = '';

// Load checks on page load
document.addEventListener('DOMContentLoaded', () => {
    loadChecks();

    // Set up event listeners
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    document.getElementById('filterAll').addEventListener('click', () => setFilter('all'));
    document.getElementById('filterEnabled').addEventListener('click', () => setFilter('enabled'));
    document.getElementById('filterDisabled').addEventListener('click', () => setFilter('disabled'));
    document.getElementById('resetAllBtn').addEventListener('click', resetAllChecks);
    document.getElementById('saveBtn').addEventListener('click', saveCheck);
});

async function loadChecks() {
    try {
        const response = await fetch('/api/checks/');
        if (!response.ok) throw new Error('Failed to load checks');

        allChecks = await response.json();
        console.log(`Loaded ${allChecks.length} checks`);

        renderChecks();
        updateCounts();
    } catch (error) {
        console.error('Error loading checks:', error);
        showAlert('Failed to load check configurations', 'danger');
    }
}

function renderChecks() {
    const tbody = document.getElementById('checksTableBody');
    tbody.innerHTML = '';

    const filteredChecks = filterChecks();
    const noResults = document.getElementById('noResults');

    if (filteredChecks.length === 0) {
        noResults.style.display = 'block';
        return;
    }

    noResults.style.display = 'none';

    filteredChecks.forEach(check => {
        const row = createCheckRow(check);
        tbody.appendChild(row);
    });

    console.log(`Rendered ${filteredChecks.length} checks`);
}

function createCheckRow(check) {
    const row = document.createElement('tr');

    // Enabled toggle
    const enabledCell = document.createElement('td');
    enabledCell.className = 'text-center';
    const enabledSwitch = `
        <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" ${check.enabled ? 'checked' : ''} 
                   onchange="quickToggle('${check.check_id}', this.checked)"
                   aria-label="Toggle ${check.check_name}">
        </div>
    `;
    enabledCell.innerHTML = enabledSwitch;
    row.appendChild(enabledCell);

    // Check name and description
    const nameCell = document.createElement('td');
    nameCell.innerHTML = `
        <div>
            <strong>${escapeHtml(check.check_name)}</strong>
            ${check.description ? `<br><small class="text-muted">${escapeHtml(check.description)}</small>` : ''}
        </div>
    `;
    row.appendChild(nameCell);

    // Severity
    const severityCell = document.createElement('td');
    const severityBadge = getSeverityBadge(check.severity);
    severityCell.innerHTML = severityBadge;
    row.appendChild(severityCell);

    // WCAG
    const wcagCell = document.createElement('td');
    if (check.wcag_criterion && check.wcag_level) {
        wcagCell.innerHTML = `
            <span class="badge bg-info">${check.wcag_criterion}</span>
            <span class="badge bg-secondary">${check.wcag_level}</span>
        `;
    } else {
        wcagCell.innerHTML = '<span class="text-muted">N/A</span>';
    }
    row.appendChild(wcagCell);

    // Type
    const typeCell = document.createElement('td');
    typeCell.innerHTML = `<span class="badge bg-light text-dark">${check.check_type}</span>`;
    row.appendChild(typeCell);

    // Actions
    const actionsCell = document.createElement('td');
    actionsCell.innerHTML = `
        <button class="btn btn-sm btn-outline-primary" onclick="editCheck('${check.check_id}')" 
                title="Edit check configuration">
            <i class="bi bi-pencil"></i>
        </button>
    `;
    row.appendChild(actionsCell);

    return row;
}

function getSeverityBadge(severity) {
    const badges = {
        'error': '<span class="badge bg-danger">Error</span>',
        'warning': '<span class="badge bg-warning text-dark">Warning</span>',
        'alert': '<span class="badge bg-info">Alert</span>',
        'disabled': '<span class="badge bg-secondary">Disabled</span>'
    };
    return badges[severity] || '<span class="badge bg-secondary">Unknown</span>';
}

function filterChecks() {
    let filtered = allChecks;

    // Apply status filter
    if (currentFilter === 'enabled') {
        filtered = filtered.filter(c => c.enabled);
    } else if (currentFilter === 'disabled') {
        filtered = filtered.filter(c => !c.enabled);
    }

    // Apply search filter
    if (currentSearchTerm) {
        const term = currentSearchTerm.toLowerCase();
        filtered = filtered.filter(c =>
            c.check_name.toLowerCase().includes(term) ||
            (c.description && c.description.toLowerCase().includes(term)) ||
            c.check_id.toLowerCase().includes(term)
        );
    }

    return filtered;
}

function handleSearch(e) {
    currentSearchTerm = e.target.value;
    renderChecks();
}

function setFilter(filter) {
    currentFilter = filter;

    // Update button states
    document.querySelectorAll('#filterAll, #filterEnabled, #filterDisabled').forEach(btn => {
        btn.classList.remove('active');
    });

    if (filter === 'all') {
        document.getElementById('filterAll').classList.add('active');
    } else if (filter === 'enabled') {
        document.getElementById('filterEnabled').classList.add('active');
    } else if (filter === 'disabled') {
        document.getElementById('filterDisabled').classList.add('active');
    }

    renderChecks();
}

function updateCounts() {
    const total = allChecks.length;
    const enabled = allChecks.filter(c => c.enabled).length;
    const disabled = total - enabled;

    document.getElementById('countAll').textContent = total;
    document.getElementById('countEnabled').textContent = enabled;
    document.getElementById('countDisabled').textContent = disabled;
}

async function quickToggle(checkId, enabled) {
    const check = allChecks.find(c => c.check_id === checkId);
    if (!check) return;

    try {
        const response = await fetch(`/api/checks/${checkId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                enabled: enabled,
                severity: check.severity
            })
        });

        if (!response.ok) throw new Error('Failed to update check');

        // Update local data
        check.enabled = enabled;
        updateCounts();

        showAlert(`Check "${check.check_name}" ${enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
        console.error('Error updating check:', error);
        showAlert('Failed to update check configuration', 'danger');
        // Revert the toggle
        await loadChecks();
    }
}

function editCheck(checkId) {
    const check = allChecks.find(c => c.check_id === checkId);
    if (!check) return;

    // Populate modal
    document.getElementById('editCheckId').value = check.check_id;
    document.getElementById('editCheckName').textContent = check.check_name;
    document.getElementById('editCheckDescription').textContent = check.description || 'No description available';
    document.getElementById('editEnabled').checked = check.enabled;
    document.getElementById('editSeverity').value = check.severity;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
}

async function saveCheck() {
    const checkId = document.getElementById('editCheckId').value;
    const enabled = document.getElementById('editEnabled').checked;
    const severity = document.getElementById('editSeverity').value;

    try {
        const response = await fetch(`/api/checks/${checkId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                enabled: enabled,
                severity: severity
            })
        });

        if (!response.ok) throw new Error('Failed to save check');

        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
        modal.hide();

        // Reload checks
        await loadChecks();

        showAlert('Check configuration saved successfully', 'success');
    } catch (error) {
        console.error('Error saving check:', error);
        showAlert('Failed to save check configuration', 'danger');
    }
}

async function resetAllChecks() {
    if (!confirm('Are you sure you want to reset ALL check configurations to system defaults? This will remove all your custom settings.')) {
        return;
    }

    try {
        const response = await fetch('/api/checks/reset-all', {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to reset checks');

        const result = await response.json();

        // Reload checks
        await loadChecks();

        showAlert(result.message, 'success');
    } catch (error) {
        console.error('Error resetting checks:', error);
        showAlert('Failed to reset check configurations', 'danger');
    }
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

