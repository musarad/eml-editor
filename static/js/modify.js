// Handle form submission
document.getElementById('modifyForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Show loading modal
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();
    
    // Get form data
    const formData = new FormData(this);
    
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