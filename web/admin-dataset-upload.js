// Admin dataset upload script
// API Configuration - Auto-detect based on environment
function getApiBaseUrl() {
    // Check if we have an environment variable
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    
    // Check meta tag for API URL
    const metaApiUrl = document.querySelector('meta[name="api-base-url"]');
    if (metaApiUrl && metaApiUrl.content) {
        return metaApiUrl.content;
    }
    
    // Auto-detect: if we're on localhost, use localhost API
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
        return 'http://127.0.0.1:8000';
    }
    
    // Production: use same origin (if API is on same domain)
    return window.location.origin;
}

const API_BASE_URL = getApiBaseUrl();

(function () {
    const form = document.getElementById('datasetUploadForm');
    const messageEl = document.getElementById('uploadMessage');

    if (!form) {
        console.error('datasetUploadForm not found on page.');
        return;
    }

    function setMessage(text, type = 'info') {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = `admin-message admin-message-${type}`;
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const fileInput = document.getElementById('imageFile');
        const trustSelect = document.getElementById('trustLabel');

        if (!fileInput || !trustSelect) {
            setMessage('Form elements not found.', 'error');
            return;
        }

        const file = fileInput.files[0];
        const uiLabel = trustSelect.value;

        if (!file) {
            setMessage('Please select an image file to upload.', 'error');
            return;
        }
        if (!uiLabel) {
            setMessage('Please select a trust level.', 'error');
            return;
        }

        // Map UI labels to API labels ("high_trust" -> "high", etc.)
        const labelMap = {
            high_trust: 'high',
            medium_trust: 'medium',
            low_trust: 'low',
        };

        const apiLabel = labelMap[uiLabel];
        if (!apiLabel) {
            setMessage('Invalid trust label selected.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('trust_label', apiLabel);

        setMessage('Uploading image...', 'info');

        try {
            const response = await fetch(`${API_BASE_URL}/api/dataset/upload-image`, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || !data.success) {
                const errorDetail = data.detail || data.error || response.statusText;
                setMessage(`Upload failed: ${errorDetail}`, 'error');
                return;
            }

            setMessage(`Upload successful! Saved as: ${data.path} (label: ${data.label})`, 'success');
            form.reset();
        } catch (err) {
            console.error('Upload error:', err);
            setMessage('Network or server error during upload. Check console for details.', 'error');
        }
    });
})();


