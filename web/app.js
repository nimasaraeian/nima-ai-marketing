// API Configuration - Auto-detect based on environment
function getApiBaseUrl() {
    // Check if we have an environment variable (set via meta tag or window config)
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
    const protocol = window.location.protocol;
    
    // If opened from file:// protocol, use localhost API
    if (protocol === 'file:' || hostname === '' || hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000';
    }
    
    // Production: use same origin (if API is on same domain) or relative URLs
    // If API is on different subdomain, you can set it via meta tag or window.API_BASE_URL
    return window.location.origin;
}

const API_BASE_URL = getApiBaseUrl();

// Helper function to check if server is running
async function checkServerHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            mode: 'cors'  // Explicitly allow CORS
        });
        return response.ok;
    } catch (error) {
        console.error('Health check failed:', error);
        console.error('API_BASE_URL:', API_BASE_URL);
        return false;
    }
}

// Helper function to parse error response
async function parseErrorResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    
    // If response is HTML (not JSON), it's likely a hosting service error
    if (contentType.includes('text/html')) {
        const htmlText = await response.text();
        
        if (htmlText.includes('Service Suspended') || htmlText.includes('service has been suspended')) {
            return {
                type: 'service_suspended',
                message: 'سرور در حال حاضر غیرفعال است. لطفاً سرور محلی را اجرا کنید یا با پشتیبانی تماس بگیرید.'
            };
        }
        
        if (htmlText.includes('404') || htmlText.includes('Not Found')) {
            return {
                type: 'not_found',
                message: 'آدرس API یافت نشد. لطفاً مطمئن شوید سرور در حال اجرا است.'
            };
        }
        
        return {
            type: 'html_response',
            message: `سرور پاسخ HTML برگردانده است (احتمالاً سرور در حال اجرا نیست): ${response.status}`
        };
    }
    
    // Try to parse as JSON
    try {
        const json = await response.json();
        return {
            type: 'json_error',
            message: json.detail || json.message || json.error || `خطای ${response.status}`,
            data: json
        };
    } catch (e) {
        const text = await response.text();
        return {
            type: 'unknown',
            message: text || `خطای غیرمنتظره: ${response.status}`
        };
    }
}

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
        // First check if server is running
        const serverHealthy = await checkServerHealth();
        if (!serverHealthy) {
            throw new Error('SERVER_NOT_RUNNING');
        }
        
        const response = await fetch(`${API_BASE_URL}/api/brain`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || `خطای ${response.status}`);
        }
        
        // Check if response is actually JSON
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || 'پاسخ سرور فرمت JSON ندارد');
        }
        
        const result = await response.json();
        showResults(result, MODULE_CONFIGS[moduleId].title);
        
    } catch (error) {
        console.error('Error:', error);
        
        let errorMessage = 'خطا در ارتباط با سرور. ';
        
        if (error.message === 'SERVER_NOT_RUNNING') {
            errorMessage += 'سرور در حال اجرا نیست. لطفاً سرور را با دستور زیر اجرا کنید:\n\n';
            errorMessage += 'python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage += 'نمی‌توان به سرور متصل شد. لطفاً:\n';
            errorMessage += '1. مطمئن شوید سرور در حال اجرا است\n';
            errorMessage += '2. آدرس API درست است: ' + API_BASE_URL;
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
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
    
    // Check if we have screenshots from capture_info (old format) or screenshots (new format from /analyze-url)
    let screenshotsHtml = '';
    const apiBaseUrl = API_BASE_URL;
    
    // Check for new format: result.screenshots (from /analyze-url endpoint)
    if (result.screenshots) {
        const screenshots = result.screenshots;
        screenshotsHtml = '<div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">';
        screenshotsHtml += '<h3 style="margin-bottom: 1rem;">Screenshots</h3>';
        screenshotsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">';
        
        // Desktop screenshot
        if (screenshots.desktop && screenshots.desktop.url) {
            const desktopUrl = screenshots.desktop.url.startsWith('http') 
                ? screenshots.desktop.url 
                : `${apiBaseUrl}${screenshots.desktop.url}`;
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Desktop View</h4>
                    <img src="${desktopUrl}" 
                         alt="Desktop screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" 
                         onerror="this.parentElement.innerHTML='<p style=\\'color: red;\\'>Failed to load desktop screenshot</p>'" />
                    ${screenshots.desktop.error ? `<p style="color: #f59e0b; font-size: 0.875rem; margin-top: 0.5rem;">⚠️ ${screenshots.desktop.error}</p>` : ''}
                </div>
            `;
        }
        
        // Mobile screenshot
        if (screenshots.mobile && screenshots.mobile.url) {
            const mobileUrl = screenshots.mobile.url.startsWith('http') 
                ? screenshots.mobile.url 
                : `${apiBaseUrl}${screenshots.mobile.url}`;
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Mobile View</h4>
                    <img src="${mobileUrl}" 
                         alt="Mobile screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" 
                         onerror="this.parentElement.innerHTML='<p style=\\'color: red;\\'>Failed to load mobile screenshot</p>'" />
                    ${screenshots.mobile.error ? `<p style="color: #f59e0b; font-size: 0.875rem; margin-top: 0.5rem;">⚠️ ${screenshots.mobile.error}</p>` : ''}
                </div>
            `;
        }
        
        screenshotsHtml += '</div></div>';
    }
    // Check for old format: result.capture_info.screenshots
    else if (result.capture_info && result.capture_info.screenshots) {
        const screenshots = result.capture_info.screenshots;
        
        screenshotsHtml = '<div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">';
        screenshotsHtml += '<h3 style="margin-bottom: 1rem;">Screenshots</h3>';
        screenshotsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">';
        
        if (screenshots.above_the_fold) {
            const atfPath = screenshots.above_the_fold.split(/[/\\]/).pop();
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Above the Fold</h4>
                    <img src="${apiBaseUrl}/api/artifacts/${atfPath}" 
                         alt="Above the fold screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" />
                </div>
            `;
        }
        
        if (screenshots.full_page) {
            const fullPath = screenshots.full_page.split(/[/\\]/).pop();
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Full Page</h4>
                    <img src="${apiBaseUrl}/api/artifacts/${fullPath}" 
                         alt="Full page screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" />
                </div>
            `;
        }
        
        screenshotsHtml += '</div></div>';
    }
    
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
        ${screenshotsHtml}
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">
            <button class="btn btn-primary" onclick="downloadResults('${moduleTitle}', \`${escapeHtml(result.response)}\`)">Download Results</button>
            <button class="btn btn-secondary" onclick="closeResults()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Test endpoint for debugging image upload
async function testImageUpload(event) {
    if (event) {
        event.preventDefault();
    }
    
    const textEl = document.getElementById('visualProText');
    const imageEl = document.getElementById('visualProImage');
    
    const formData = new FormData();
    formData.append('content', textEl ? textEl.value.trim() : '');
    
    if (imageEl && imageEl.files && imageEl.files[0]) {
        const imageFile = imageEl.files[0];
        console.log('🧪 TEST: Image file selected:', {
            name: imageFile.name,
            size: imageFile.size,
            type: imageFile.type
        });
        formData.append('image', imageFile);
    } else {
        console.log('🧪 TEST: No image file selected');
    }
    
    try {
        console.log('🧪 TEST: Sending to /api/brain/test');
        const response = await fetch(`${API_BASE_URL}/api/brain/test`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('🧪 TEST RESULT:', result);
        alert('Test Result:\n' + JSON.stringify(result, null, 2));
    } catch (error) {
        console.error('🧪 TEST ERROR:', error);
        alert('Test Error: ' + error.message);
    }
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
    
    let hasImage = false;
    if (imageEl && imageEl.files && imageEl.files[0]) {
        const imageFile = imageEl.files[0];
        console.log('Image file selected:', {
            name: imageFile.name,
            size: imageFile.size,
            type: imageFile.type
        });
        
        if (imageFile.size === 0) {
            alert('فایل تصویر خالی است. لطفاً یک تصویر معتبر انتخاب کنید.');
            return;
        }
        
        formData.append('image', imageFile);
        hasImage = true;
    } else {
        console.log('No image file selected');
    }

    // Show loading overlay
    document.getElementById('loadingOverlay').classList.add('active');

    try {
        console.log(`Sending request to ${API_BASE_URL}/api/brain/analyze-with-image`, {
            hasText: textEl.value.trim().length > 0,
            hasImage: hasImage
        });
        
        const response = await fetch(`${API_BASE_URL}/api/brain/analyze-with-image`, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it automatically with boundary for FormData
        });

        if (!response.ok) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || `خطای ${response.status}`);
        }

        // Check if response is actually JSON
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || 'پاسخ سرور فرمت JSON ندارد');
        }

        const result = await response.json();
        showVisualProResults(result);
    } catch (error) {
        console.error('Visual Pro error:', error);
        
        let errorMessage = 'خطا در تحلیل متن + تصویر. ';
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage += 'نمی‌توان به سرور متصل شد. لطفاً مطمئن شوید سرور در حال اجرا است.';
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// Render combined psychology + visual trust results
function showVisualProResults(result) {
    const modal = document.getElementById('resultsModal');
    const container = document.getElementById('resultsContainer');

    // Extract analysis data
    const analysis = result.analysis || {};
    const overall = result.overall || {};
    const visual = result.visual_layer || {};
    
    // Extract pillar scores
    const cognitiveFriction = analysis.cognitive_friction || {};
    const emotionalResonance = analysis.emotional_resonance || {};
    const trustClarity = analysis.trust_clarity || {};
    
    // Calculate main friction score (average of key pillars or use global score)
    // Friction is inverse of quality: high global score = low friction
    const frictionScore = overall.global_score != null 
        ? Math.max(0, Math.min(100, 100 - overall.global_score)) // Invert: higher global score = lower friction
        : cognitiveFriction.score != null 
            ? cognitiveFriction.score 
            : 50;
    
    // Get sub-scores with fallbacks
    const cfScore = cognitiveFriction.score ?? cognitiveFriction.friction_score ?? 50;
    const erScore = emotionalResonance.score ?? emotionalResonance.emotional_resonance_score ?? 50;
    const tcScore = trustClarity.score ?? trustClarity.trust_score ?? 50;
    
    // Decision Likelihood - try multiple possible locations
    let decisionLikelihood = overall.decision_likelihood_percentage ?? 
                             overall.decision_likelihood ?? 
                             overall.decisionProbability ? (overall.decisionProbability * 100) : null;
    
    // Conversion Impact - calculate if not provided
    // Formula: Based on how much improvement is possible if issues are fixed
    // If decision likelihood is low, there's high potential for improvement
    let conversionImpact = overall.conversion_lift_estimate ?? 
                          overall.conversionLiftEstimate ?? null;
    
    if (conversionImpact == null && decisionLikelihood != null) {
        // Estimate conversion impact based on decision likelihood
        // If likelihood is below 50%, there's potential for positive impact
        // If likelihood is above 70%, impact is lower (already good)
        if (decisionLikelihood < 50) {
            conversionImpact = (50 - decisionLikelihood) * 1.5; // Potential improvement
        } else if (decisionLikelihood < 70) {
            conversionImpact = (70 - decisionLikelihood) * 0.8; // Moderate improvement
        } else {
            conversionImpact = Math.max(0, (100 - decisionLikelihood) * 0.3); // Small improvement
        }
    } else if (conversionImpact == null) {
        // Fallback: estimate based on friction and trust scores
        const avgScore = (cfScore + erScore + tcScore) / 3;
        if (avgScore < 50) {
            conversionImpact = (50 - avgScore) * 1.2; // High potential
        } else {
            conversionImpact = Math.max(0, (100 - avgScore) * 0.5); // Lower potential
        }
    }
    
    // Get blockers and factors - handle different data structures
    const keyBlockers = cognitiveFriction.reasons || 
                       cognitiveFriction.issues || 
                       cognitiveFriction.keyDecisionBlockers ||
                       (Array.isArray(cognitiveFriction.blockers) ? cognitiveFriction.blockers : []) ||
                       [];
    
    const emotionalResistance = emotionalResonance.resistance_factors || 
                               emotionalResonance.emotionalResistanceFactors ||
                               emotionalResonance.issues ||
                               [];
    
    const cognitiveOverload = cognitiveFriction.overload_factors || 
                              cognitiveFriction.cognitiveOverloadFactors ||
                              cognitiveFriction.overload ||
                              [];
    
    const trustBreakpoints = trustClarity.breakpoints || 
                            trustClarity.trustBreakpoints ||
                            trustClarity.issues ||
                            [];
    
    // Get motivation misalignments
    const motivationProfile = analysis.motivation_profile || {};
    const motivationMisalignments = motivationProfile.misalignment_signals ||
                                   analysis.motivationMisalignments ||
                                   (result.motivationMisalignments ? result.motivationMisalignments : []) ||
                                   [];
    
    // Get recommendations - handle different structures
    let quickWins = [];
    if (overall.recommendedQuickWins && Array.isArray(overall.recommendedQuickWins)) {
        quickWins = overall.recommendedQuickWins;
    } else if (overall.quick_wins && Array.isArray(overall.quick_wins)) {
        quickWins = overall.quick_wins;
    } else if (overall.priority_fixes && Array.isArray(overall.priority_fixes)) {
        quickWins = overall.priority_fixes.slice(0, 3).map(f => 
            typeof f === 'string' ? f : (f.issue || f.explanation || f)
        ).filter(Boolean);
    }
    
    let deepChanges = [];
    if (overall.recommendedDeepChanges && Array.isArray(overall.recommendedDeepChanges)) {
        deepChanges = overall.recommendedDeepChanges;
    } else if (overall.final_recommendations && Array.isArray(overall.final_recommendations)) {
        deepChanges = overall.final_recommendations;
    } else if (overall.priority_fixes && Array.isArray(overall.priority_fixes)) {
        deepChanges = overall.priority_fixes.slice(3).map(f => 
            typeof f === 'string' ? f : (f.issue || f.explanation || f)
        ).filter(Boolean);
    }
    
    // Visual trust data
    const vtLabel = visual.visual_trust_label || (result.visual_trust && result.visual_trust.label) || 'N/A';
    const vtScore = visual.visual_trust_score ?? (result.visual_trust && result.visual_trust.score_numeric);
    const vtComment = visual.visual_comment || 'No visual layer available (no image provided or model not configured).';

    // Helper function to get status badge
    // For positive metrics (higher is better): emotional resonance, trust & clarity
    function getStatusBadge(score, isPositive = true) {
        if (!isPositive) {
            // For negative metrics (lower is better): friction
            if (score <= 30) return '<span class="status-badge status-good">Excellent</span>';
            if (score <= 50) return '<span class="status-badge status-medium">Moderate</span>';
            if (score <= 70) return '<span class="status-badge status-warning">Warning</span>';
            return '<span class="status-badge status-critical">Critical</span>';
        } else {
            // For positive metrics (higher is better)
            if (score >= 70) return '<span class="status-badge status-good">Excellent</span>';
            if (score >= 50) return '<span class="status-badge status-medium">Moderate</span>';
            if (score >= 30) return '<span class="status-badge status-warning">Warning</span>';
            return '<span class="status-badge status-critical">Critical</span>';
        }
    }
    
    // Helper function to format percentage
    function formatPercent(value) {
        if (value == null || isNaN(value)) return 'NaN';
        return value.toFixed(1) + '%';
    }
    
    // Helper function to format score
    function formatScore(value) {
        if (value == null || isNaN(value)) return 'NaN';
        return Math.round(value);
    }

    container.innerHTML = `
        <div class="results-header">
            <h2>Decision Psychology Report</h2>
            <span class="ai-analysis-badge">AI Analysis</span>
        </div>

        <!-- Decision Friction Score Section -->
        <div class="dashboard-section">
            <div class="friction-score-card">
                <div class="score-header">
                    <span class="score-icon">🎯</span>
                    <h3>Decision Friction Score</h3>
                </div>
                <div class="score-value">${formatScore(frictionScore)} / 100</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${Math.min(100, frictionScore)}%; background: ${frictionScore > 60 ? '#ef4444' : frictionScore > 40 ? '#f59e0b' : '#10b981'};"></div>
                </div>
                ${getStatusBadge(frictionScore, false)}
            </div>
        </div>

        <!-- Sub-Scores Section -->
        <div class="dashboard-section">
            <div class="sub-scores-grid">
                <div class="sub-score-card">
                    <span class="sub-score-icon">⚡</span>
                    <h4>Cognitive Friction</h4>
                    <div class="sub-score-value">${formatScore(cfScore)} / 100</div>
                    ${getStatusBadge(cfScore, false)}
                    <div class="mini-progress-bar" style="width: ${Math.min(100, cfScore)}%; background: ${cfScore > 60 ? '#ef4444' : '#f59e0b'};"></div>
                </div>
                <div class="sub-score-card">
                    <span class="sub-score-icon">✨</span>
                    <h4>Emotional Resonance</h4>
                    <div class="sub-score-value">${formatScore(erScore)} / 100</div>
                    ${getStatusBadge(erScore, true)}
                    <div class="mini-progress-bar" style="width: ${Math.min(100, erScore)}%; background: ${erScore > 60 ? '#10b981' : erScore > 40 ? '#f59e0b' : '#ef4444'};"></div>
                </div>
                <div class="sub-score-card">
                    <span class="sub-score-icon">🛡️</span>
                    <h4>Trust & Clarity</h4>
                    <div class="sub-score-value">${formatScore(tcScore)} / 100</div>
                    ${getStatusBadge(tcScore, true)}
                    <div class="mini-progress-bar" style="width: ${Math.min(100, tcScore)}%; background: ${tcScore > 60 ? '#10b981' : tcScore > 40 ? '#f59e0b' : '#ef4444'};"></div>
                </div>
                <div class="sub-score-card">
                    <span class="sub-score-icon">📈</span>
                    <h4>Action Triggers</h4>
                    <div class="action-metrics">
                        <div>Decision Likelihood ${formatPercent(decisionLikelihood)}</div>
                        <div>Conversion Impact ${formatPercent(conversionImpact)}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Decision Blockers Section -->
        <div class="dashboard-section">
            <h3 class="section-title">Decision Blockers & Psychological Factors</h3>
            <div class="blockers-grid">
                <div class="blocker-card">
                    <span class="blocker-icon">⚡</span>
                    <h4>Key Decision Blockers</h4>
                    ${keyBlockers.length > 0 
                        ? `<ul class="blocker-list">${keyBlockers.slice(0, 3).map(b => `<li>${b}</li>`).join('')}</ul>`
                        : '<p>No major blockers detected.</p>'}
                </div>
                <div class="blocker-card">
                    <span class="blocker-icon">✨</span>
                    <h4>Emotional Resistance</h4>
                    ${emotionalResistance.length > 0 
                        ? `<ul class="blocker-list">${emotionalResistance.slice(0, 3).map(r => `<li>${r}</li>`).join('')}</ul>`
                        : '<p>No major emotional resistance detected.</p>'}
                </div>
                <div class="blocker-card">
                    <span class="blocker-icon">🧠</span>
                    <h4>Cognitive Overload</h4>
                    ${cognitiveOverload.length > 0 
                        ? `<ul class="blocker-list">${cognitiveOverload.slice(0, 3).map(o => `<li>${o}</li>`).join('')}</ul>`
                        : '<p>No cognitive overload detected.</p>'}
                </div>
                <div class="blocker-card">
                    <span class="blocker-icon">🛡️</span>
                    <h4>Trust Breakpoints</h4>
                    ${trustBreakpoints.length > 0 
                        ? `<ul class="blocker-list">${trustBreakpoints.slice(0, 3).map(t => `<li>${t}</li>`).join('')}</ul>`
                        : '<p>No trust breakpoints detected.</p>'}
                </div>
                <div class="blocker-card">
                    <span class="blocker-icon">🎯</span>
                    <h4>Motivation Misalignments</h4>
                    ${motivationMisalignments.length > 0 
                        ? `<ul class="blocker-list">${motivationMisalignments.slice(0, 3).map(m => `<li>${m}</li>`).join('')}</ul>`
                        : '<p>No alignment with user needs or desires.</p>'}
                </div>
            </div>
        </div>

        <!-- AI Recommendations Section -->
        <div class="dashboard-section">
            <h3 class="section-title">AI Recommendations</h3>
            <div class="recommendations-grid">
                <div class="recommendation-card">
                    <span class="recommendation-icon">⚡</span>
                    <h4>Quick Wins</h4>
                    <p>Immediate changes to reduce friction fast.</p>
                    <div class="recommendation-content">
                        ${quickWins.length > 0 ? `<ul>${quickWins.map(w => `<li>${w}</li>`).join('')}</ul>` : '<p>No quick wins available.</p>'}
                    </div>
                </div>
                <div class="recommendation-card">
                    <span class="recommendation-icon">🎯</span>
                    <h4>Deep Changes</h4>
                    <p>Structural and strategic improvements for long-term impact.</p>
                    <div class="recommendation-content">
                        ${deepChanges.length > 0 ? `<ul>${deepChanges.map(c => `<li>${c}</li>`).join('')}</ul>` : '<p>No deep changes available.</p>'}
                    </div>
                </div>
            </div>
        </div>

        <!-- Decision Psychology Summary -->
        <div class="dashboard-section">
            <h3 class="section-title">Decision Psychology Summary</h3>
            <div class="summary-content">
                ${overall.summary || 
                   overall.explanationSummary || 
                   (result.explanationSummary ? result.explanationSummary : '') ||
                   (result.human_readable_report ? result.human_readable_report : '') ||
                   'Analysis completed. Review the scores and recommendations above.'}
            </div>
        </div>

        <!-- Visual Layer (if available) -->
        ${vtScore != null ? `
        <div class="dashboard-section">
            <h3 class="section-title">Visual Trust Layer</h3>
            <div class="visual-trust-info">
                <p><strong>Visual trust label:</strong> ${vtLabel}</p>
                <p><strong>Visual trust score:</strong> ${vtScore.toFixed(1)}</p>
                <p><strong>Comment:</strong> ${vtComment}</p>
            </div>
        </div>
        ` : ''}
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

// Check server health when page loads
document.addEventListener('DOMContentLoaded', async function() {
    // Wait a bit to avoid blocking page render
    setTimeout(async () => {
        try {
            const isHealthy = await checkServerHealth();
            if (!isHealthy) {
                console.warn('⚠️ سرور در حال اجرا نیست. لطفاً سرور را با دستور زیر اجرا کنید:');
                console.warn('python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload');
                
                // Show a non-intrusive notification
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #ff9800;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                    z-index: 10000;
                    max-width: 400px;
                    font-family: Arial, sans-serif;
                    direction: rtl;
                `;
                notification.innerHTML = `
                    <strong>⚠️ هشدار:</strong><br>
                    سرور در حال اجرا نیست. لطفاً سرور را اجرا کنید.<br>
                    <small style="opacity: 0.9;">برای بستن کلیک کنید</small>
                `;
                notification.onclick = () => notification.remove();
                document.body.appendChild(notification);
                
                // Auto-remove after 10 seconds
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 10000);
            } else {
                console.log('✅ سرور در حال اجرا است');
            }
        } catch (error) {
            console.warn('⚠️ خطا در بررسی وضعیت سرور:', error);
        }
    }, 500);
});

// URL Analysis submission
async function submitUrlAnalysis(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const url = formData.get('url');
    
    if (!url) {
        alert('Please enter a URL');
        return;
    }
    
    // Show loading overlay
    document.getElementById('loadingOverlay').classList.add('active');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze-url`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url
            })
        });
        
        if (!response.ok) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || `خطای ${response.status}`);
        }
        
        const result = await response.json();
        
        // Show results with screenshots
        showUrlAnalysisResults(result);
        
    } catch (error) {
        console.error('URL Analysis error:', error);
        
        let errorMessage = 'خطا در تحلیل URL. ';
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage += 'نمی‌توان به سرور متصل شد. لطفاً مطمئن شوید سرور در حال اجرا است.';
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// Show URL Analysis Results
function showUrlAnalysisResults(result) {
    const modal = document.getElementById('resultsModal');
    const container = document.getElementById('resultsContainer');
    
    // Extract analysis data
    const visualTrust = result.visualTrust || {};
    const brain = result.brain || {};
    const features = result.features || {};
    
    // Build screenshots HTML
    let screenshotsHtml = '';
    if (result.screenshots) {
        const screenshots = result.screenshots;
        const apiBaseUrl = API_BASE_URL;
        
        screenshotsHtml = '<div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">';
        screenshotsHtml += '<h3 style="margin-bottom: 1rem;">Screenshots</h3>';
        screenshotsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">';
        
        // Desktop screenshot
        if (screenshots.desktop && screenshots.desktop.url) {
            const desktopUrl = screenshots.desktop.url.startsWith('http') 
                ? screenshots.desktop.url 
                : `${apiBaseUrl}${screenshots.desktop.url}`;
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Desktop View</h4>
                    <img src="${desktopUrl}" 
                         alt="Desktop screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" 
                         onerror="this.parentElement.innerHTML='<p style=\\'color: red;\\'>Failed to load desktop screenshot</p>'" />
                    ${screenshots.desktop.error ? `<p style="color: #f59e0b; font-size: 0.875rem; margin-top: 0.5rem;">⚠️ ${screenshots.desktop.error}</p>` : ''}
                </div>
            `;
        }
        
        // Mobile screenshot
        if (screenshots.mobile && screenshots.mobile.url) {
            const mobileUrl = screenshots.mobile.url.startsWith('http') 
                ? screenshots.mobile.url 
                : `${apiBaseUrl}${screenshots.mobile.url}`;
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Mobile View</h4>
                    <img src="${mobileUrl}" 
                         alt="Mobile screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" 
                         onerror="this.parentElement.innerHTML='<p style=\\'color: red;\\'>Failed to load mobile screenshot</p>'" />
                    ${screenshots.mobile.error ? `<p style="color: #f59e0b; font-size: 0.875rem; margin-top: 0.5rem;">⚠️ ${screenshots.mobile.error}</p>` : ''}
                </div>
            `;
        }
        
        screenshotsHtml += '</div></div>';
    }
    
    // Build analysis summary
    let analysisSummary = '';
    if (visualTrust && visualTrust.label) {
        analysisSummary += `<p><strong>Visual Trust:</strong> ${visualTrust.label} (${(visualTrust.confidence * 100).toFixed(1)}%)</p>`;
    }
    if (brain && brain.decision) {
        analysisSummary += `<p><strong>Decision:</strong> ${brain.decision}</p>`;
    }
    if (brain && brain.confidence !== undefined) {
        analysisSummary += `<p><strong>Confidence:</strong> ${(brain.confidence * 100).toFixed(1)}%</p>`;
    }
    
    container.innerHTML = `
        <div class="results-header">
            <h2>URL Analysis Results</h2>
            <p><strong>URL:</strong> ${result.url || 'N/A'}</p>
            ${analysisSummary}
        </div>
        <div class="results-content">
            ${result.extractedText ? `<div style="margin-bottom: 1rem;"><h3>Extracted Text</h3><p>${result.extractedText.substring(0, 500)}${result.extractedText.length > 500 ? '...' : ''}</p></div>` : ''}
            ${result.brain && result.brain.explanation ? `<div style="margin-bottom: 1rem;"><h3>Analysis</h3>${formatMarkdown(result.brain.explanation)}</div>` : ''}
        </div>
        ${screenshotsHtml}
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">
            <button class="btn btn-secondary" onclick="closeResults()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Human Decision Review submission
async function submitHumanDecisionReview(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const url = formData.get('url');
    const goal = formData.get('goal') || 'other';
    const locale = formData.get('locale') || 'en';
    
    if (!url) {
        alert('Please enter a URL');
        return;
    }
    
    // Show loading overlay
    document.getElementById('loadingOverlay').classList.add('active');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/url-human`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                goal: goal,
                locale: locale
            })
        });
        
        if (!response.ok) {
            const errorInfo = await parseErrorResponse(response);
            throw new Error(errorInfo.message || `خطای ${response.status}`);
        }
        
        const result = await response.json();
        
        // Show results with screenshots
        showHumanDecisionResults(result);
        
    } catch (error) {
        console.error('Human Decision Review error:', error);
        
        let errorMessage = 'خطا در تحلیل URL. ';
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage += 'نمی‌توان به سرور متصل شد. لطفاً مطمئن شوید سرور در حال اجرا است.';
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// Show Human Decision Review Results
function showHumanDecisionResults(result) {
    const modal = document.getElementById('resultsModal');
    const container = document.getElementById('resultsContainer');
    
    // Extract screenshots if available
    let screenshotsHtml = '';
    if (result.capture_info && result.capture_info.screenshots) {
        const screenshots = result.capture_info.screenshots;
        const apiBaseUrl = API_BASE_URL;
        
        screenshotsHtml = '<div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">';
        screenshotsHtml += '<h3 style="margin-bottom: 1rem;">Screenshots</h3>';
        screenshotsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">';
        
        if (screenshots.above_the_fold) {
            const atfPath = screenshots.above_the_fold.split(/[/\\]/).pop();
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Above the Fold</h4>
                    <img src="${apiBaseUrl}/api/artifacts/${atfPath}" 
                         alt="Above the fold screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" />
                </div>
            `;
        }
        
        if (screenshots.full_page) {
            const fullPath = screenshots.full_page.split(/[/\\]/).pop();
            screenshotsHtml += `
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-size: 1rem;">Full Page</h4>
                    <img src="${apiBaseUrl}/api/artifacts/${fullPath}" 
                         alt="Full page screenshot" 
                         style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                         onclick="window.open(this.src, '_blank')" />
                </div>
            `;
        }
        
        screenshotsHtml += '</div></div>';
    }
    
    container.innerHTML = `
        <div class="results-header">
            <h2>Human Decision Review - Results</h2>
        </div>
        <div class="results-content">
            ${result.report ? formatMarkdown(result.report) : '<p>No report available.</p>'}
        </div>
        ${screenshotsHtml}
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--border-color);">
            <button class="btn btn-primary" onclick="downloadResults('Human Decision Review', \`${escapeHtml(result.report || 'No report available.')}\`)">Copy report</button>
            <button class="btn btn-secondary" onclick="closeResults()">Close</button>
        </div>
    `;
    
    modal.style.display = 'block';
}

