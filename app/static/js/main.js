/**
 * CivicShield AI — Interactive Frontend Controller
 * Features:
 * - Guided 4-Step Complaint Submission Wizard
 * - Real-time AI Category Suggestion with debouncing
 * - Multi-file Evidence Upload & Live Previews
 * - Duplicate Click / Form Re-submission Prevention
 * - Bilingual Citizen Assistance Drawer (English & Tamil)
 * - Auto-dismissing Alerts & Toast Notifications
 */

document.addEventListener('DOMContentLoaded', function() {
    initAlerts();
    initGuidedWizard();
    initEvidenceUpload();
    initAssistantDrawer();
    initNotificationPoller();
});

/* ==========================================================================
   1. Flash Alerts & Feedback
   ========================================================================== */
function initAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {}
        });
    }, 6000);
}

/* ==========================================================================
   2. Guided 4-Step Complaint Wizard
   ========================================================================== */
let currentStep = 1;
const totalSteps = 4;

function initGuidedWizard() {
    const wizardForm = document.getElementById('complaintWizardForm');
    if (!wizardForm) return;

    // Step navigation buttons
    const btnNext = document.getElementById('btnWizardNext');
    const btnPrev = document.getElementById('btnWizardPrev');
    const btnSubmit = document.getElementById('btnWizardSubmit');

    if (btnNext) {
        btnNext.addEventListener('click', function() {
            if (validateCurrentStep(currentStep)) {
                if (currentStep < totalSteps) {
                    currentStep++;
                    updateWizardUI();
                    if (currentStep === 4) {
                        populateReviewStep();
                    }
                }
            }
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener('click', function() {
            if (currentStep > 1) {
                currentStep--;
                updateWizardUI();
            }
        });
    }

    // Duplicate submission prevention
    wizardForm.addEventListener('submit', function(e) {
        if (!validateCurrentStep(4)) {
            e.preventDefault();
            return false;
        }
        if (btnSubmit) {
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Submitting Complaint...';
        }
    });

    // Real-time AI Category Classification
    initRealtimeCategoryClassification();
}

function updateWizardUI() {
    // Hide all step panes
    document.querySelectorAll('.wizard-pane').forEach(function(pane) {
        pane.classList.add('d-none');
    });

    // Show current pane
    const activePane = document.getElementById('wizardStep' + currentStep);
    if (activePane) {
        activePane.classList.remove('d-none');
    }

    // Update progress circles
    for (let i = 1; i <= totalSteps; i++) {
        const stepCircle = document.getElementById('stepIndicator' + i);
        if (stepCircle) {
            stepCircle.classList.remove('active', 'completed');
            if (i === currentStep) {
                stepCircle.classList.add('active');
            } else if (i < currentStep) {
                stepCircle.classList.add('completed');
            }
        }
    }

    // Update button states
    const btnPrev = document.getElementById('btnWizardPrev');
    const btnNext = document.getElementById('btnWizardNext');
    const btnSubmit = document.getElementById('btnWizardSubmit');

    if (btnPrev) {
        btnPrev.style.display = currentStep > 1 ? 'inline-block' : 'none';
    }
    if (btnNext) {
        btnNext.style.display = currentStep < totalSteps ? 'inline-block' : 'none';
    }
    if (btnSubmit) {
        btnSubmit.style.display = currentStep === totalSteps ? 'inline-block' : 'none';
    }

    window.scrollTo({ top: 120, behavior: 'smooth' });
}

function validateCurrentStep(step) {
    let isValid = true;
    const currentPane = document.getElementById('wizardStep' + step);
    if (!currentPane) return true;

    // Validate required fields in the step
    const inputs = currentPane.querySelectorAll('input[required], select[required], textarea[required]');
    inputs.forEach(function(input) {
        if (!input.value || !input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });

    if (step === 1) {
        const desc = document.getElementById('description');
        if (desc && desc.value.trim().length < 20) {
            desc.classList.add('is-invalid');
            isValid = false;
            showToast('Please describe the incident in at least 20 characters for proper investigation.', 'warning');
        }
    }

    if (step === 4) {
        const decl = document.getElementById('declaration');
        if (decl && !decl.checked) {
            decl.classList.add('is-invalid');
            isValid = false;
            showToast('You must confirm the truthfulness of the complaint before submission.', 'warning');
        }
    }

    return isValid;
}

function populateReviewStep() {
    const titleVal = document.getElementById('title') ? document.getElementById('title').value : '';
    const catVal = document.getElementById('crime_category') ? document.getElementById('crime_category').value : '';
    const dateVal = document.getElementById('incident_date') ? document.getElementById('incident_date').value : '';
    const descVal = document.getElementById('description') ? document.getElementById('description').value : '';
    const distVal = document.getElementById('district') ? document.getElementById('district').value : '';
    const locVal = document.getElementById('incident_location') ? document.getElementById('incident_location').value : '';
    const psVal = document.getElementById('police_station') ? document.getElementById('police_station').value : '';

    const reviewTitle = document.getElementById('reviewTitle');
    const reviewCategory = document.getElementById('reviewCategory');
    const reviewDate = document.getElementById('reviewDate');
    const reviewLocation = document.getElementById('reviewLocation');
    const reviewStation = document.getElementById('reviewStation');
    const reviewDescription = document.getElementById('reviewDescription');
    const reviewEvidenceCount = document.getElementById('reviewEvidenceCount');

    if (reviewTitle) reviewTitle.textContent = titleVal;
    if (reviewCategory) reviewCategory.textContent = catVal;
    if (reviewDate) reviewDate.textContent = dateVal ? dateVal.replace('T', ' ') : 'N/A';
    if (reviewLocation) reviewLocation.textContent = `${locVal}, ${distVal}`;
    if (reviewStation) reviewStation.textContent = psVal;
    if (reviewDescription) reviewDescription.textContent = descVal;

    const fileInput = document.getElementById('evidence_files');
    const count = fileInput && fileInput.files ? fileInput.files.length : 0;
    if (reviewEvidenceCount) reviewEvidenceCount.textContent = count > 0 ? `${count} file(s) attached` : 'None';
}

function jumpToWizardStep(stepNum) {
    if (stepNum >= 1 && stepNum <= totalSteps) {
        currentStep = stepNum;
        updateWizardUI();
        if (currentStep === 4) {
            populateReviewStep();
        }
    }
}

/* ==========================================================================
   3. AI Real-time Complaint Classification (Debounced)
   ========================================================================== */
function initRealtimeCategoryClassification() {
    const descInput = document.getElementById('description');
    const categorySelect = document.getElementById('crime_category');
    const suggestionBox = document.getElementById('aiSuggestionBox');
    const suggestionText = document.getElementById('aiSuggestionText');
    const btnApplySuggestion = document.getElementById('btnApplySuggestion');

    if (!descInput || !categorySelect || !suggestionBox) return;

    let debounceTimer = null;

    descInput.addEventListener('input', function() {
        const text = descInput.value.trim();
        clearTimeout(debounceTimer);

        if (text.length < 15) {
            suggestionBox.classList.add('d-none');
            return;
        }

        debounceTimer = setTimeout(function() {
            fetch('/api/ai/classify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ text: text })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.category && data.category !== 'Other') {
                    suggestionBox.classList.remove('d-none');
                    if (suggestionText) {
                        suggestionText.innerHTML = `Suggested: <strong>${data.category}</strong> <span class="badge-ml ms-1">${data.confidence}% match</span>`;
                    }
                    if (btnApplySuggestion) {
                        btnApplySuggestion.onclick = function() {
                            categorySelect.value = data.category;
                            suggestionBox.classList.add('d-none');
                            showToast(`Category set to ${data.category}`, 'info');
                        };
                    }
                } else {
                    suggestionBox.classList.add('d-none');
                }
            })
            .catch(() => {
                suggestionBox.classList.add('d-none');
            });
        }, 550);
    });
}

/* ==========================================================================
   4. Multi-File Evidence Upload with Live Preview
   ========================================================================== */
function initEvidenceUpload() {
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('evidence_files');
    const previewGrid = document.getElementById('evidencePreviewGrid');

    if (!dropzone || !fileInput || !previewGrid) return;

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            renderEvidencePreviews(fileInput.files);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files) {
            renderEvidencePreviews(fileInput.files);
        }
    });
}

function renderEvidencePreviews(files) {
    const previewGrid = document.getElementById('evidencePreviewGrid');
    if (!previewGrid) return;
    previewGrid.innerHTML = '';

    Array.from(files).forEach((file, index) => {
        const card = document.createElement('div');
        card.className = 'preview-card';

        const sizeKb = Math.round(file.size / 1024);
        const nameShort = file.name.length > 18 ? file.name.substring(0, 15) + '...' : file.name;

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                card.innerHTML = `
                    <img src="${e.target.result}" alt="Preview">
                    <div class="small text-truncate" title="${file.name}">${nameShort}</div>
                    <div class="text-muted" style="font-size: 0.75rem;">${sizeKb} KB</div>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            card.innerHTML = `
                <div class="file-icon"><i class="fas fa-file-pdf text-danger"></i></div>
                <div class="small text-truncate" title="${file.name}">${nameShort}</div>
                <div class="text-muted" style="font-size: 0.75rem;">${sizeKb} KB</div>
            `;
        }

        previewGrid.appendChild(card);
    });
}

/* ==========================================================================
   5. Bilingual Citizen Assistance Drawer (English & Tamil)
   ========================================================================== */
let currentAssistantLang = 'en';

function initAssistantDrawer() {
    const btnOpen = document.querySelectorAll('.btn-open-assistant');
    const btnClose = document.getElementById('btnCloseAssistant');
    const drawer = document.getElementById('assistantDrawer');
    const backdrop = document.getElementById('assistantBackdrop');
    const langBtnEn = document.getElementById('btnLangEn');
    const langBtnTa = document.getElementById('btnLangTa');
    const queryInput = document.getElementById('assistantQueryInput');
    const btnSend = document.getElementById('btnSendAssistantQuery');

    if (!drawer) return;

    btnOpen.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            openAssistantDrawer();
        });
    });

    if (btnClose) btnClose.addEventListener('click', closeAssistantDrawer);
    if (backdrop) backdrop.addEventListener('click', closeAssistantDrawer);

    if (langBtnEn) {
        langBtnEn.addEventListener('click', () => {
            setAssistantLanguage('en');
        });
    }

    if (langBtnTa) {
        langBtnTa.addEventListener('click', () => {
            setAssistantLanguage('ta');
        });
    }

    if (btnSend && queryInput) {
        btnSend.addEventListener('click', () => {
            submitAssistantQuery(queryInput.value);
        });
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitAssistantQuery(queryInput.value);
            }
        });
    }

    // Load suggested questions initially
    loadSuggestedQuestions('en');
}

function openAssistantDrawer() {
    const drawer = document.getElementById('assistantDrawer');
    const backdrop = document.getElementById('assistantBackdrop');
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('show');
}

function closeAssistantDrawer() {
    const drawer = document.getElementById('assistantDrawer');
    const backdrop = document.getElementById('assistantBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
}

function setAssistantLanguage(lang) {
    currentAssistantLang = lang;
    const btnEn = document.getElementById('btnLangEn');
    const btnTa = document.getElementById('btnLangTa');
    const queryInput = document.getElementById('assistantQueryInput');

    if (btnEn && btnTa) {
        if (lang === 'ta') {
            btnTa.classList.add('active');
            btnEn.classList.remove('active');
            if (queryInput) queryInput.placeholder = "உங்கள் கேள்வியை இங்கு தட்டச்சு செய்யவும்...";
        } else {
            btnEn.classList.add('active');
            btnTa.classList.remove('active');
            if (queryInput) queryInput.placeholder = "Type your question here...";
        }
    }
    loadSuggestedQuestions(lang);
}

function loadSuggestedQuestions(lang) {
    const container = document.getElementById('assistantSuggestions');
    if (!container) return;

    fetch(`/api/ai/suggested-questions?lang=${lang}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.questions) {
                container.innerHTML = '';
                data.questions.slice(0, 5).forEach(item => {
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = 'btn btn-sm btn-outline-secondary text-start me-1 mb-2 text-truncate';
                    chip.style.maxWidth = '100%';
                    chip.style.fontSize = '0.785rem';
                    chip.style.borderRadius = '9999px';
                    chip.textContent = item.question;
                    chip.onclick = () => submitAssistantQuery(item.question);
                    container.appendChild(chip);
                });
            }
        })
        .catch(() => {});
}

function submitAssistantQuery(query) {
    if (!query || !query.trim()) return;

    const queryInput = document.getElementById('assistantQueryInput');
    const answerContainer = document.getElementById('assistantAnswerArea');
    if (!answerContainer) return;

    if (queryInput) queryInput.value = '';

    answerContainer.innerHTML = `
        <div class="text-center py-4 text-muted">
            <div class="spinner-border spinner-border-sm text-primary mb-2" role="status"></div>
            <div>Consulting CivicShield Knowledge Engine...</div>
        </div>
    `;

    fetch('/api/ai/help', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ query: query, lang: currentAssistantLang })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            let stepsHtml = '';
            if (data.steps && data.steps.length > 0) {
                stepsHtml = '<ol class="mt-2 mb-2 ps-3" style="font-size: 0.85rem;">' +
                    data.steps.map(s => `<li class="mb-1">${s}</li>`).join('') +
                    '</ol>';
            }

            answerContainer.innerHTML = `
                <div class="card card-civic mb-3 border-0 bg-light p-3">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="badge bg-primary text-white" style="font-size: 0.7rem;">${data.category || 'Help Topic'}</span>
                        <span class="text-muted" style="font-size: 0.7rem;">CivicShield Assistant</span>
                    </div>
                    <h6 class="fw-bold mb-2" style="font-size: 0.9rem;">${data.question || query}</h6>
                    <p class="mb-2" style="font-size: 0.875rem; line-height: 1.5;">${data.answer}</p>
                    ${stepsHtml}
                    <div class="mt-2 pt-2 border-top text-muted" style="font-size: 0.725rem;">
                        <i class="fas fa-info-circle me-1"></i> Demo assistance system. For immediate police emergency, dial 112.
                    </div>
                </div>
            `;
        }
    })
    .catch(() => {
        answerContainer.innerHTML = `
            <div class="alert alert-warning" style="font-size: 0.85rem;">
                Unable to reach assistance service. Please browse our FAQ page or try again.
            </div>
        `;
    });
}

/* ==========================================================================
   6. Notification Poller & CSRF Utility
   ========================================================================== */
function initNotificationPoller() {
    const badge = document.getElementById('navbarNotificationBadge');
    if (!badge) return;

    setInterval(function() {
        fetch('/api/notifications/unread-count')
            .then(res => res.json())
            .then(data => {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.classList.remove('d-none');
                } else {
                    badge.classList.add('d-none');
                }
            })
            .catch(() => {});
    }, 45000);
}

function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) return metaTag.getAttribute('content');
    const inputTag = document.querySelector('input[name="csrf_token"]');
    if (inputTag) return inputTag.value;
    return '';
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.bottom = '24px';
        container.style.right = '24px';
        container.style.zIndex = '99999';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} shadow-lg py-2 px-3 mb-2 d-flex align-items-center justify-content-between`;
    toast.style.minWidth = '280px';
    toast.style.borderRadius = '8px';
    toast.innerHTML = `
        <span>${message}</span>
        <button type="button" class="btn-close ms-2" style="font-size: 0.75rem;"></button>
    `;

    toast.querySelector('.btn-close').onclick = () => toast.remove();
    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4000);
}
