// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
// For production, change to: const API_BASE_URL = 'https://api.nimasaraeian.com';

// Module configurations
const MODULE_CONFIGS = {
    deepscan: {
        title: 'Behavioral DeepScan',
        fields: [
            { name: 'industry', label: 'Industry', type: 'select', options: ['Beauty Clinic', 'Restaurant', 'SaaS', 'Education', 'Real Estate', 'Other'] },
            { name: 'city', label: 'City', type: 'text', placeholder: 'e.g., Istanbul' },
            { name: 'target_audience', label: 'Target Audience', type: 'text', placeholder: 'e.g., Tourists, Locals, Young Professionals' },
            { name: 'query', label: 'What do you want to analyze?', type: 'textarea', placeholder: 'Describe your current marketing situation, challenges, or what you want to understand about your audience...' }
        ]
    },
    market: {
        title: 'Market & Trend Intelligence',
        fields: [
            { name: 'industry', label: 'Industry', type: 'select', options: ['Beauty Clinic', 'Restaurant', 'SaaS', 'Education', 'Real Estate', 'Other'] },
            { name: 'city', label: 'City', type: 'text', placeholder: 'e.g., Istanbul' },
            { name: 'channel', label: 'Primary Channel', type: 'select', options: ['Instagram Ads', 'Google Ads', 'Facebook Ads', 'TikTok Ads', 'LinkedIn Ads', 'Email', 'Other'] },
            { name: 'query', label: 'What market intelligence do you need?', type: 'textarea', placeholder: 'Describe competitors, trends, positioning gaps, or audience reactions you want to analyze...' }
        ]
    },
    content: {
        title: 'AI Content Engine',
        fields: [
            { name: 'industry', label: 'Industry', type: 'select', options: ['Beauty Clinic', 'Restaurant', 'SaaS', 'Education', 'Real Estate', 'Other'] },
            { name: 'city', label: 'City', type: 'text', placeholder: 'e.g., Istanbul' },
            { name: 'channel', label: 'Content Format', type: 'select', options: ['Instagram', 'YouTube', 'LinkedIn', 'Blog', 'Email', 'All'] },
            { name: 'query', label: 'What content do you need?', type: 'textarea', placeholder: 'Describe the type of content, topics, voice, tone, or specific campaign you want to create...' }
        ]
    },
    conversion: {
        title: 'Conversion & Funnel Architecture',
        fields: [
            { name: 'industry', label: 'Industry', type: 'select', options: ['Beauty Clinic', 'Restaurant', 'SaaS', 'Education', 'Real Estate', 'Other'] },
            { name: 'city', label: 'City', type: 'text', placeholder: 'e.g., Istanbul' },
            { name: 'channel', label: 'Channel', type: 'select', options: ['Instagram Ads', 'Google Ads', 'Facebook Ads', 'Website', 'Email', 'Other'] },
            { name: 'query', label: 'What funnel or conversion challenge do you have?', type: 'textarea', placeholder: 'Describe your current funnel, conversion issues, trust points, or decision journey challenges...' }
        ]
    },
    automation: {
        title: 'AI Automation System',
        fields: [
            { name: 'industry', label: 'Industry', type: 'select', options: ['Beauty Clinic', 'Restaurant', 'SaaS', 'Education', 'Real Estate', 'Other'] },
            { name: 'city', label: 'City', type: 'text', placeholder: 'e.g., Istanbul' },
            { name: 'channel', label: 'Automation Channel', type: 'select', options: ['DM/WhatsApp', 'Email', 'SMS', 'All'] },
            { name: 'query', label: 'What automation do you need?', type: 'textarea', placeholder: 'Describe your lead qualification, routing, follow-up, or appointment automation needs...' }
        ]
    }
};

// Utility Functions
function scrollToModules() {
    document.getElementById('modules').scrollIntoView({ behavior: 'smooth' });
}

function openConsultation() {
    alert('Consultation booking will be integrated here.');
    // You can integrate with a booking system or contact form
}

// Module Functions
function openModule(moduleId) {
    const config = MODULE_CONFIGS[moduleId];
    if (!config) return;

    const modal = document.getElementById('moduleModal');
    const container = document.getElementById('moduleFormContainer');
    
    container.innerHTML = `
        <h2 style="margin-bottom: 2rem; color: var(--text-primary);">${config.title}</h2>
        <form id="moduleForm" onsubmit="submitModule('${moduleId}', event)">
            ${config.fields.map(field => {
                if (field.type === 'select') {
                    return `
                        <div class="form-group">
                            <label class="form-label">${field.label}</label>
                            <select class="form-select" name="${field.name}" required>
                                <option value="">Select...</option>
                                ${field.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
                            </select>
                        </div>
                    `;
                } else if (field.type === 'textarea') {
                    return `
                        <div class="form-group">
                            <label class="form-label">${field.label}</label>
                            <textarea class="form-textarea" name="${field.name}" placeholder="${field.placeholder || ''}" required></textarea>
                        </div>
                    `;
                } else {
                    return `
                        <div class="form-group">
                            <label class="form-label">${field.label}</label>
                            <input class="form-input" type="${field.type}" name="${field.name}" placeholder="${field.placeholder || ''}" required>
                        </div>
                    `;
                }
            }).join('')}
            <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                <button type="submit" class="btn btn-primary" style="flex: 1;">Analyze with AI</button>
                <button type="button" class="btn btn-secondary" onclick="closeModule()" style="flex: 1;">Cancel</button>
            </div>
        </form>
    `;
    
    modal.style.display = 'block';
}

function closeModule() {
    document.getElementById('moduleModal').style.display = 'none';
}

function closeResults() {
    document.getElementById('resultsModal').style.display = 'none';
}

// Submit Module Form
async function submitModule(moduleId, event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    // Build query based on module
    let query = data.query;
    if (moduleId === 'deepscan') {
        query = `I need a behavioral DeepScan analysis for my ${data.industry} in ${data.city}. Target audience: ${data.target_audience}. ${data.query}`;
    } else if (moduleId === 'market') {
        query = `I need market intelligence for my ${data.industry} in ${data.city} using ${data.channel}. ${data.query}`;
    } else if (moduleId === 'content') {
        query = `I need AI-generated content for my ${data.industry} in ${data.city} for ${data.channel}. ${data.query}`;
    } else if (moduleId === 'conversion') {
        query = `I need conversion and funnel architecture help for my ${data.industry} in ${data.city} on ${data.channel}. ${data.query}`;
    } else if (moduleId === 'automation') {
        query = `I need automation setup for my ${data.industry} in ${data.city} using ${data.channel}. ${data.query}`;
    }
    
    // Prepare API request
    const requestData = {
        role: 'ai_marketing_strategist',
        locale: 'tr-TR',
        city: data.city || 'Istanbul',
        industry: data.industry || 'Other',
        channel: data.channel || 'Instagram Ads',
        query: query
    };
    
    // Show loading
    document.getElementById('loadingOverlay').classList.add('active');
    closeModule();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/brain`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const result = await response.json();
        showResults(result, MODULE_CONFIGS[moduleId].title);
        
    } catch (error) {
        console.error('Error:', error);
        alert('خطا در ارتباط با سرور. لطفاً مطمئن شوید سرور در حال اجرا است.');
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// Show Results
function showResults(result, moduleTitle) {
    const modal = document.getElementById('resultsModal');
    const container = document.getElementById('resultsContainer');
    
    const qualityBadge = result.quality_score >= 4 
        ? `<span class="quality-score">Quality Score: ${result.quality_score}/5 ✅</span>`
        : `<span class="quality-score" style="background: var(--warning-color);">Quality Score: ${result.quality_score}/5</span>`;
    
    container.innerHTML = `
        <div class="results-header">
            <h2>${moduleTitle} - Results</h2>
            ${qualityBadge}
            ${result.quality_checks ? `
                <div style="margin-top: 1rem;">
                    <strong>Quality Checks:</strong>
                    <ul style="margin-top: 0.5rem;">
                        ${Object.entries(result.quality_checks).map(([key, value]) => 
                            `<li>${key}: ${value ? '✅' : '❌'}</li>`
                        ).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
        <div class="results-content">
            ${formatMarkdown(result.response)}
        </div>
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">
            <button class="btn btn-primary" onclick="downloadResults('${moduleTitle}', \`${escapeHtml(result.response)}\`)">Download Results</button>
            <button class="btn btn-secondary" onclick="closeResults()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Visual Psychology + Image (Pro) submission
async function submitVisualPsychologyWithImage(event) {
    event.preventDefault();

    const form = event.target;
    const textEl = document.getElementById('visualProText');
    const imageEl = document.getElementById('visualProImage');

    if (!textEl || !textEl.value.trim()) {
        alert('لطفاً متن تبلیغ یا لندینگ را وارد کنید.');
        return;
    }

    const formData = new FormData();
    formData.append('text', textEl.value.trim());
    if (imageEl && imageEl.files && imageEl.files[0]) {
        formData.append('image', imageEl.files[0]);
    }

    // Show loading overlay
    document.getElementById('loadingOverlay').classList.add('active');

    try {
        const response = await fetch(`${API_BASE_URL}/api/brain/analyze-with-image`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`API Error ${response.status}: ${errText}`);
        }

        const result = await response.json();
        showVisualProResults(result);
    } catch (error) {
        console.error('Visual Pro error:', error);
        alert('خطا در تحلیل متن + تصویر. لطفاً مطمئن شوید سرور و مدل بصری فعال هستند.');
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// Render combined psychology + visual trust results
function showVisualProResults(result) {
    const modal = document.getElementById('resultsModal');
    const container = document.getElementById('resultsContainer');

    const visual = result.visual_layer || {};
    const vtLabel = visual.visual_trust_label || (result.visual_trust && result.visual_trust.label) || 'N/A';
    const vtScore = visual.visual_trust_score ?? (result.visual_trust && result.visual_trust.score_numeric);
    const vtComment = visual.visual_comment || 'No visual layer available (no image provided or model not configured).';

    const breakdown = visual.visual_trust_scores
        || visual.visual_trust_breakdown
        || (result.visual_trust && result.visual_trust.scores)
        || {};

    const overall = result.overall || {};
    const human = result.human_readable_report || '';

    const breakdownHtml = Object.keys(breakdown).length
        ? `<ul>${Object.entries(breakdown)
              .map(([k, v]) => `<li><strong>${k}:</strong> ${(v * 100).toFixed(1)}%</li>`)
              .join('')}</ul>`
        : '<p>No visual scores available.</p>';

    container.innerHTML = `
        <div class="results-header">
            <h2>Decision Psychology + Visual Trust (Pro)</h2>
        </div>

        <div class="results-section">
            <h3>Core Psychology Engine (Text)</h3>
            <pre class="results-pre">${human}</pre>
        </div>

        <div class="results-section">
            <h3>Visual Layer</h3>
            <p><strong>Visual trust label:</strong> ${vtLabel}</p>
            <p><strong>Visual trust score:</strong> ${vtScore != null ? vtScore.toFixed(1) : 'N/A'}</p>
            <p><strong>Comment:</strong> ${vtComment}</p>
            <h4>Score breakdown</h4>
            ${breakdownHtml}
        </div>
    `;

    modal.style.display = 'block';
}

// Format Markdown to HTML (simple version)
function formatMarkdown(text) {
    // Headers
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Lists
    text = text.replace(/^\- (.*$)/gim, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Line breaks
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';
    
    return text;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function downloadResults(title, content) {
    const blob = new Blob([`# ${title}\n\n${content}`], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '-')}-results.md`;
    a.click();
    URL.revokeObjectURL(url);
}

// Close modals when clicking outside
window.onclick = function(event) {
    const moduleModal = document.getElementById('moduleModal');
    const resultsModal = document.getElementById('resultsModal');
    
    if (event.target === moduleModal) {
        closeModule();
    }
    if (event.target === resultsModal) {
        closeResults();
    }
}



