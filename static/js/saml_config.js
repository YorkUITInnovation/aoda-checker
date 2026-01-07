// SAML Configuration Page JavaScript

// Show alert message
function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}-fill"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.appendChild(alert);

    // Scroll to alert
    alertContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

// Toggle between URL and XML metadata import
document.querySelectorAll('input[name="metadata_source"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const urlSection = document.getElementById('metadata-url-section');
        const xmlSection = document.getElementById('metadata-xml-section');

        if (this.value === 'url') {
            urlSection.classList.remove('d-none');
            xmlSection.classList.add('d-none');
        } else {
            urlSection.classList.add('d-none');
            xmlSection.classList.remove('d-none');
        }
    });
});

// Generate Certificates
document.getElementById('generate-cert-btn').addEventListener('click', async function() {
    const btn = this;
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';

    const certData = {
        cn: document.getElementById('cert_cn').value,
        org: document.getElementById('cert_org').value,
        country: document.getElementById('cert_country').value,
        state: document.getElementById('cert_state').value,
        city: document.getElementById('cert_city').value,
        email: document.getElementById('cert_email').value,
        ou: document.getElementById('cert_ou').value
    };

    try {
        const response = await fetch('/api/admin/saml-generate-certificates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(certData)
        });

        const result = await response.json();

        if (response.ok) {
            showAlert('Certificates generated successfully!', 'success');
        } else {
            showAlert(`Error: ${result.detail || 'Failed to generate certificates'}`, 'danger');
        }
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// Import IdP Metadata
document.getElementById('import-metadata-btn').addEventListener('click', async function() {
    const btn = this;
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Importing...';

    const metadataSource = document.querySelector('input[name="metadata_source"]:checked').value;
    const requestData = {
        metadata_source: metadataSource,
        idp_metadata_xml: metadataSource === 'xml' ? document.getElementById('idp_metadata_xml').value : '',
        idp_metadata_url: metadataSource === 'url' ? document.getElementById('idp_metadata_url').value : ''
    };

    try {
        const response = await fetch('/api/admin/saml-parse-metadata', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Populate form fields with parsed data
            const data = result.data;
            document.getElementById('idp_entity_id').value = data.idp_entity_id || '';
            document.getElementById('idp_sso_url').value = data.idp_sso_url || '';
            document.getElementById('idp_sls_url').value = data.idp_sls_url || '';
            document.getElementById('idp_x509_cert').value = data.idp_x509_cert || '';

            showAlert('IdP metadata imported successfully! Please review the populated fields.', 'success');
        } else {
            showAlert(`Error: ${result.detail || result.message || 'Failed to import metadata'}`, 'danger');
        }
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// Save Configuration
document.getElementById('saml-config-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    // Build form data
    const formData = new FormData();
    formData.append('enabled', document.getElementById('enabled').checked);
    formData.append('sp_entity_id', document.getElementById('sp_entity_id').value);
    formData.append('sp_acs_url', document.getElementById('sp_acs_url').value);
    formData.append('sp_sls_url', document.getElementById('sp_sls_url').value);

    // Convert datetime-local to ISO format for sp_valid_until
    const validUntilInput = document.getElementById('sp_valid_until').value;
    if (validUntilInput) {
        const validUntilDate = new Date(validUntilInput);
        formData.append('sp_valid_until', validUntilDate.toISOString());
    } else {
        formData.append('sp_valid_until', '');
    }

    formData.append('idp_entity_id', document.getElementById('idp_entity_id').value);
    formData.append('idp_sso_url', document.getElementById('idp_sso_url').value);
    formData.append('idp_sls_url', document.getElementById('idp_sls_url').value);
    formData.append('idp_x509_cert', document.getElementById('idp_x509_cert').value);
    formData.append('org_name', document.getElementById('org_name').value);
    formData.append('org_display_name', document.getElementById('org_display_name').value);
    formData.append('org_url', document.getElementById('org_url').value);
    formData.append('technical_contact_email', document.getElementById('technical_contact_email').value);
    formData.append('attribute_mapping', document.getElementById('attribute_mapping').value);
    formData.append('auto_provision_users', document.getElementById('auto_provision_users').checked);
    formData.append('default_user_role_is_admin', document.getElementById('default_user_role_is_admin').checked);

    try {
        const response = await fetch('/api/admin/saml-config', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showAlert('SAML configuration saved successfully!', 'success');
        } else {
            showAlert(`Error: ${result.detail || 'Failed to save configuration'}`, 'danger');
        }
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'danger');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
});

