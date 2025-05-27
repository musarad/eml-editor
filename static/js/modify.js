// Handle form submission
document.getElementById('modifyForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Show loading modal
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();
    
    // Get form data
    const formData = new FormData(this);
    
    // Add authentication mode to form data
    const authMode = document.querySelector('input[name="auth_mode"]:checked').value;
    if (authMode === 'realistic') {
        formData.append('realistic_mode', 'on');
    } else if (authMode === 'legacy') {
        formData.append('legacy_mode', 'on');
    }
    
    // Add X-header mode to form data
    const xHeaderMode = document.querySelector('input[name="x_header_mode"]:checked');
    if (xHeaderMode) {
        formData.append('x_header_mode', xHeaderMode.value);
    }
    
    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Hide loading modal
        loadingModal.hide();
        
        if (result.success) {
            // Set download link
            document.getElementById('downloadLink').href = result.download_url;
            
            // Update success modal with validation info
            updateSuccessModal(result);
            
            // Show success modal
            const successModal = new bootstrap.Modal(document.getElementById('successModal'));
            successModal.show();
        } else {
            // Show error
            document.getElementById('errorMessage').textContent = result.error || 'An error occurred while processing your email.';
            const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
            errorModal.show();
        }
    } catch (error) {
        // Hide loading modal
        loadingModal.hide();
        
        // Show error
        document.getElementById('errorMessage').textContent = 'Network error: ' + error.message;
        const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        errorModal.show();
    }
});

// Update success modal with validation information
function updateSuccessModal(result) {
    const modalBody = document.querySelector('#successModal .modal-body');
    
    // Create status message
    let statusHtml = '<p>Your email has been successfully modified.</p>';
    
    // Add mode information
    if (result.realistic_mode) {
        statusHtml += '<div class="alert alert-success alert-sm mb-3">';
        statusHtml += '<i class="bi bi-shield-check"></i> <strong>Realistic Mode:</strong> Authentication headers are consistent and detection-resistant.';
        statusHtml += '</div>';
    } else {
        statusHtml += '<div class="alert alert-warning alert-sm mb-3">';
        statusHtml += '<i class="bi bi-exclamation-triangle"></i> <strong>Legacy Mode:</strong> May contain authentication inconsistencies.';
        statusHtml += '</div>';
    }
    
    // Add crypto information
    if (result.crypto_used) {
        statusHtml += '<div class="alert alert-info alert-sm mb-3">';
        statusHtml += '<i class="bi bi-lock"></i> <strong>Cryptographic Signatures:</strong> Real DKIM/ARC signatures applied.';
        statusHtml += '</div>';
    }
    
    // Add validation warnings if any
    if (result.validation_warnings && result.validation_warnings.length > 0) {
        statusHtml += '<div class="alert alert-warning alert-sm mb-3">';
        statusHtml += '<i class="bi bi-exclamation-triangle"></i> <strong>Validation Warnings:</strong><ul class="mb-0 mt-2">';
        result.validation_warnings.forEach(warning => {
            statusHtml += `<li>${warning}</li>`;
        });
        statusHtml += '</ul></div>';
    }
    
    // Add download button
    statusHtml += '<a id="downloadLink" href="' + result.download_url + '" class="btn btn-primary btn-lg">';
    statusHtml += '<i class="bi bi-download"></i> Download Modified Email</a>';
    
    modalBody.innerHTML = statusHtml;
}

// Handle authentication mode changes
document.addEventListener('DOMContentLoaded', function() {
    const realisticMode = document.getElementById('realistic_mode');
    const legacyMode = document.getElementById('legacy_mode');
    
    function updateModeDescription() {
        // You can add dynamic descriptions here if needed
        if (legacyMode.checked) {
            console.log('Legacy mode selected - warning user about detection risks');
        }
    }
    
    if (realisticMode) realisticMode.addEventListener('change', updateModeDescription);
    if (legacyMode) legacyMode.addEventListener('change', updateModeDescription);
});

// Auto-resize textarea
const textarea = document.getElementById('new_body');
if (textarea) {
    function autoResize() {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    }
    
    textarea.addEventListener('input', autoResize);
    
    // Initial resize
    setTimeout(autoResize, 100);
}

// File input preview
document.getElementById('new_attachments').addEventListener('change', function(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        const fileNames = files.map(f => f.name).join(', ');
        const label = e.target.nextElementSibling;
        if (label) {
            label.textContent = `Selected: ${fileNames}`;
        }
    }
});

// Date helper
document.getElementById('new_date').addEventListener('change', function(e) {
    // The datetime-local input will be converted server-side
    console.log('Date selected:', e.target.value);
}); 