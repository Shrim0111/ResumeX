/**
 * Live Preview & Studio Real-time Sync Engine
 * Handles character-by-character live preview, AJAX form submissions,
 * template switching, zoom scaling, and asynchronous entry management.
 */

(function () {
  'use strict';

  // State
  let currentResume = window.INITIAL_RESUME || {};
  let currentTemplate = currentResume.selected_template || 'classic';
  let currentZoom = 0.85; // Default comfortable fit on desktop split-screen
  let activeSectionKey = 'contact';

  // Section mapping
  const SECTION_MAP = {
    contactForm: 'contacts',
    summaryForm: 'summary',
    educationForm: 'education',
    experienceForm: 'experience',
    projectForm: 'projects',
    skillsForm: 'skills',
    involvementForm: 'innovations',
    certificationForm: 'certifications',
    courseworkForm: 'coursework'
  };

  // DOM Elements
  const resumePageEl = document.getElementById('liveResumePage');
  const templateCssLink = document.getElementById('liveTemplateCss');
  const zoomLevelDisplay = document.getElementById('zoomLevelDisplay');
  const previewCanvasWrap = document.getElementById('previewCanvasWrap');
  const pdfDownloadBtn = document.getElementById('pdfDownloadBtn');

  // Section steps for walk-in wizard flow
  const STEPS = [
    { target: 'contactForm', name: 'Contact Details' },
    { target: 'summaryForm', name: 'Professional Summary' },
    { target: 'experienceForm', name: 'Work Experience' },
    { target: 'projectForm', name: 'Projects & Portfolio' },
    { target: 'educationForm', name: 'Education' },
    { target: 'skillsForm', name: 'Skills & Proficiencies' },
    { target: 'involvementForm', name: 'Involvement & Activities' },
    { target: 'courseworkForm', name: 'Relevant Coursework' },
    { target: 'certificationForm', name: 'Certifications' }
  ];

  let currentStepIndex = 0;

  const ICONS = {
    contactForm: 'fa-phone',
    summaryForm: 'fa-book-open',
    educationForm: 'fa-graduation-cap',
    experienceForm: 'fa-briefcase',
    projectForm: 'fa-diagram-project',
    skillsForm: 'fa-layer-group',
    involvementForm: 'fa-lightbulb',
    certificationForm: 'fa-certificate',
    courseworkForm: 'fa-laptop-code'
  };

  const TITLES = {
    contactForm: 'Personal & Contact Information',
    summaryForm: 'Professional Summary',
    educationForm: 'Education History',
    experienceForm: 'Work Experience',
    projectForm: 'Projects & Portfolio',
    skillsForm: 'Skills & Proficiencies',
    involvementForm: 'Innovations & Extra-Curricular',
    certificationForm: 'Licenses & Certifications',
    courseworkForm: 'Relevant Coursework'
  };

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', function () {
    initTabNavigation();
    initWalkinNavigation();
    initLiveInputSync();
    initAjaxForms();
    initTemplateSwitcher();
    initZoomControls();
    initSavedItemsLists();
    
    // Auto-fit initial zoom based on available width
    autoFitZoom();
    window.addEventListener('resize', debounce(autoFitZoom, 200));

    // Render initial state
    if (window.INITIAL_RESUME) {
      renderLiveResume(window.INITIAL_RESUME);
    }
  });

  // ==================== 1. TAB & WALK-IN NAVIGATION ====================
  function updateWalkinBar() {
    const stepNumEl = document.getElementById('walkinStepNumber');
    const stepNameEl = document.getElementById('walkinStepName');
    const prevBtn = document.getElementById('walkinPrevBtn');
    const nextBtn = document.getElementById('walkinNextBtn');

    if (!prevBtn || !nextBtn) return;

    if (stepNumEl) stepNumEl.textContent = `Step ${currentStepIndex + 1} of ${STEPS.length}`;
    if (stepNameEl) stepNameEl.textContent = STEPS[currentStepIndex]?.name || '';

    prevBtn.disabled = (currentStepIndex === 0);

    if (currentStepIndex === STEPS.length - 1) {
      nextBtn.innerHTML = 'Finish & Preview <i class="fa-solid fa-flag-checkered"></i>';
      nextBtn.classList.add('btn-walkin-finish');
    } else {
      nextBtn.innerHTML = 'Next Step <i class="fa-solid fa-arrow-right"></i>';
      nextBtn.classList.remove('btn-walkin-finish');
    }
  }

  function activateSection(target) {
    if (!target) return;
    if (target === 'previewForm') {
      window.location.href = '/previewForm';
      return;
    }

    const tabButtons = document.querySelectorAll('.tab-button');
    const forms = document.querySelectorAll('.form-section');
    const sectionTitleEl = document.getElementById('activeSectionTitle');
    const sectionIconEl = document.getElementById('activeSectionIcon');

    // Toggle active menu item
    tabButtons.forEach(b => {
      const parentItem = b.closest('.menu-item');
      if (parentItem) parentItem.classList.remove('active-nav-item');
    });
    const currentTabBtn = document.querySelector(`.tab-button[data-target="${target}"]`);
    if (currentTabBtn) {
      const currentParent = currentTabBtn.closest('.menu-item');
      if (currentParent) currentParent.classList.add('active-nav-item');
    }

    // Toggle active form
    forms.forEach(f => f.classList.remove('active'));
    const activeForm = document.getElementById(target);
    if (activeForm) {
      activeForm.classList.add('active');
      activeSectionKey = SECTION_MAP[target] || 'contact';

      if (sectionTitleEl && TITLES[target]) sectionTitleEl.textContent = TITLES[target];
      if (sectionIconEl && ICONS[target]) {
        sectionIconEl.className = 'fa-solid ' + ICONS[target];
      }

      renderSectionSavedItems(target);

      const formPane = document.querySelector('.studio-form-pane');
      if (formPane) {
        formPane.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }

    // Update step index
    const sIndex = STEPS.findIndex(s => s.target === target);
    if (sIndex !== -1) {
      currentStepIndex = sIndex;
      updateWalkinBar();
    }
  }

  function initTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        const target = this.getAttribute('data-target');
        activateSection(target);
      });
    });

    // Support clicking anywhere on sidebar item row
    document.querySelectorAll('.sidebar .menu-item > a').forEach(a => {
      a.addEventListener('click', function (e) {
        const btn = this.querySelector('.tab-button');
        if (btn && e.target !== btn) {
          e.preventDefault();
          btn.click();
        }
      });
    });

    // Initialize first tab active nav state
    activateSection('contactForm');
  }

  function initWalkinNavigation() {
    const prevBtn = document.getElementById('walkinPrevBtn');
    const nextBtn = document.getElementById('walkinNextBtn');

    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (currentStepIndex > 0) {
          activateSection(STEPS[currentStepIndex - 1].target);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (currentStepIndex < STEPS.length - 1) {
          activateSection(STEPS[currentStepIndex + 1].target);
        } else {
          window.location.href = '/previewForm';
        }
      });
    }

    updateWalkinBar();
  }

  // ==================== 2. REAL-TIME KEYSTROKE SYNC ====================
  function initLiveInputSync() {
    // Listen to all inputs across all forms
    document.addEventListener('input', handleInputChange);
    document.addEventListener('change', handleInputChange);
  }

  function handleInputChange(e) {
    const target = e.target;
    const form = target.closest('form');
    if (!form) return;

    const formSection = target.closest('.form-section');
    const formId = formSection ? formSection.id : '';

    // A. Contact form fields
    if (formId === 'contactForm') {
      const fullName = form.querySelector('#fullName')?.value.trim() || currentResume.user?.name || 'Your Name';
      const email = form.querySelector('#email')?.value.trim() || '';
      const phone = form.querySelector('#phone')?.value.trim() || '';
      const pWeb = form.querySelector('[name="p_web"]')?.value.trim() || '';
      const lWeb = form.querySelector('[name="l_web"]')?.value.trim() || '';
      const country = form.querySelector('#Country')?.value.trim() || '';
      const state = form.querySelector('#State')?.value.trim() || '';
      const city = form.querySelector('#City')?.value.trim() || '';

      const nameEl = document.getElementById('liveHeaderName');
      if (nameEl) nameEl.textContent = fullName;

      const contactLineEl = document.getElementById('liveHeaderContact');
      if (contactLineEl) {
        let parts = [];
        if (phone) parts.push(`+91 ${phone}`);
        if (email) parts.push(email);
        if (pWeb) parts.push(`<a href="https://${pWeb.replace(/^https?:\/\//, '')}" target="_blank">${pWeb}</a>`);
        if (lWeb) parts.push(`<a href="https://${lWeb.replace(/^https?:\/\//, '')}" target="_blank">LinkedIn</a>`);
        if (city || state) {
          const loc = [city, state, country].filter(Boolean).map(capitalize).join(', ');
          if (loc) parts.push(loc);
        }
        contactLineEl.innerHTML = parts.join(' | ');
      }
    }

    // B. Summary form
    if (formId === 'summaryForm') {
      const summaryText = form.querySelector('textarea[name="summary"]')?.value.trim() || '';
      const summaryEl = document.getElementById('liveSummaryContent');
      if (summaryEl) {
        if (summaryText) {
          summaryEl.textContent = summaryText;
          document.getElementById('liveSummarySection')?.classList.remove('hidden-section');
        } else if (!currentResume.summary?.summary_text) {
          document.getElementById('liveSummarySection')?.classList.add('hidden-section');
        }
      }
    }

    // C. Live drafting row for entries (Experience, Education, Projects, etc.)
    handleDraftingRow(formId, form);
  }

  function handleDraftingRow(formId, form) {
    if (formId === 'experienceForm') {
      const jobTitle = form.querySelector('[name="jobTitle"]')?.value.trim();
      const company = form.querySelector('[name="company"]')?.value.trim();
      const location = form.querySelector('[name="location"]')?.value.trim();
      const desc = form.querySelector('[name="description"]')?.value.trim();
      const draftContainer = document.getElementById('liveExpDraft');

      if (draftContainer) {
        if (jobTitle || company) {
          draftContainer.style.display = 'block';
          draftContainer.innerHTML = `
            <div class="draft-badge"><i class="fa-solid fa-pen-nib"></i> Typing New Entry...</div>
            <div class="item-header-row">
              <h3>${escapeHtml(jobTitle || 'Job Title')}</h3>
              <span>${escapeHtml(company || 'Company')}</span>
            </div>
            ${location ? `<p style="font-size: 11.5px; color: #64748b; margin: 2px 0;">${escapeHtml(location)}</p>` : ''}
            ${desc ? `<p style="font-size: 12px; margin-top: 4px;">${escapeHtml(desc)}</p>` : ''}
          `;
        } else {
          draftContainer.style.display = 'none';
        }
      }
    } else if (formId === 'educationForm') {
      const degree = form.querySelector('[name="degree"]')?.value.trim();
      const institution = form.querySelector('[name="institution"]')?.value.trim();
      const fieldOfStudy = form.querySelector('[name="fieldOfStudy"]')?.value.trim();
      const draftContainer = document.getElementById('liveEduDraft');

      if (draftContainer) {
        if (degree || institution) {
          draftContainer.style.display = 'block';
          draftContainer.innerHTML = `
            <div class="draft-badge"><i class="fa-solid fa-pen-nib"></i> Typing New Entry...</div>
            <div class="item-header-row">
              <h3>${escapeHtml(degree || 'Degree')} ${fieldOfStudy ? 'in ' + escapeHtml(fieldOfStudy) : ''}</h3>
            </div>
            <p style="font-size: 12px; color: #475569;">${escapeHtml(institution || 'Institution')}</p>
          `;
        } else {
          draftContainer.style.display = 'none';
        }
      }
    } else if (formId === 'projectForm') {
      const projName = form.querySelector('[name="projectName"]')?.value.trim();
      const role = form.querySelector('[name="role"]')?.value.trim();
      const draftContainer = document.getElementById('liveProjDraft');

      if (draftContainer) {
        if (projName) {
          draftContainer.style.display = 'block';
          draftContainer.innerHTML = `
            <div class="draft-badge"><i class="fa-solid fa-pen-nib"></i> Typing New Project...</div>
            <div class="item-header-row">
              <h3>${escapeHtml(projName)}</h3>
              ${role ? `<span style="font-size: 12px; color: #64748b;">${escapeHtml(role)}</span>` : ''}
            </div>
          `;
        } else {
          draftContainer.style.display = 'none';
        }
      }
    }
  }

  // ==================== 3. AJAX FORM INTERCEPTION ====================
  function initAjaxForms() {
    const allForms = document.querySelectorAll('.form-section form');

    allForms.forEach(form => {
      form.addEventListener('submit', function (e) {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const origBtnHtml = submitBtn ? submitBtn.innerHTML : 'Submit';

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        }

        const formData = new FormData(form);

        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        })
          .then(res => {
            return res.json().then(data => ({ status: res.status, data }));
          })
          .then(({ status, data }) => {
            if (status >= 200 && status < 300 && data.success) {
              // Update state
              currentResume = data.resume || currentResume;
              
              // Re-render live preview
              renderLiveResume(currentResume);

              // Show success toast
              showStudioToast(data.message || 'Saved successfully!', 'success');

              // Button checkmark
              if (submitBtn) {
                submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
                setTimeout(() => {
                  submitBtn.disabled = false;
                  submitBtn.innerHTML = origBtnHtml;
                }, 1500);
              }

              // Reset form if it's an additive entry form
              const formSection = form.closest('.form-section');
              const formId = formSection ? formSection.id : '';
              if (formId !== 'contactForm' && formId !== 'summaryForm') {
                form.reset();
                // Clear any drafting preview row
                clearDraftRows();
              }

              // Update the saved items list in the editor
              if (formId) {
                renderSectionSavedItems(formId);
              }

            } else {
              const errMsg = data.error || data.message || 'Failed to save entry. Please check your inputs.';
              showStudioToast(errMsg, 'danger');
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origBtnHtml;
              }
            }
          })
          .catch(err => {
            console.error('AJAX Form Error:', err);
            showStudioToast('Connection error while saving. Please try again.', 'danger');
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = origBtnHtml;
            }
          });
      });
    });
  }

  function clearDraftRows() {
    ['liveExpDraft', 'liveEduDraft', 'liveProjDraft'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.style.display = 'none';
        el.innerHTML = '';
      }
    });
  }

  // ==================== 4. LIVE TEMPLATE SWITCHER ====================
  function initTemplateSwitcher() {
    const pills = document.querySelectorAll('.studio-template-pill');

    pills.forEach(pill => {
      pill.addEventListener('click', function (e) {
        e.preventDefault();
        const templateId = this.getAttribute('data-template');
        if (!templateId || templateId === currentTemplate) return;

        switchTemplate(templateId);
      });
    });
  }

  function switchTemplate(templateId) {
    currentTemplate = templateId;

    // Update active pill UI
    document.querySelectorAll('.studio-template-pill').forEach(p => {
      if (p.getAttribute('data-template') === templateId) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });

    // Update stylesheet href
    if (templateCssLink) {
      templateCssLink.href = `/static/templates/${templateId}.css`;
    }

    // Update container classes
    if (resumePageEl) {
      resumePageEl.className = `page template-${templateId}`;
    }

    // Update PDF link
    const userId = currentResume.user?.user_id || 1;
    if (pdfDownloadBtn) {
      pdfDownloadBtn.href = `/dpw/${userId}?template=${templateId}`;
    }

    // Re-render layout (switch between 1-column and 2-column structure)
    renderLiveResume(currentResume);

    // Save preference via AJAX in background
    fetch(`/select_template/${templateId}`, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      }
    })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          showStudioToast(`Switched layout to ${res.template_info?.name || templateId}`, 'info');
        }
      })
      .catch(err => console.warn('Template sync failed:', err));
  }

  // ==================== 5. ZOOM & SCALE CONTROLS ====================
  function initZoomControls() {
    document.getElementById('zoomInBtn')?.addEventListener('click', () => adjustZoom(0.08));
    document.getElementById('zoomOutBtn')?.addEventListener('click', () => adjustZoom(-0.08));
    document.getElementById('zoomFitBtn')?.addEventListener('click', autoFitZoom);
    document.getElementById('zoomResetBtn')?.addEventListener('click', () => setZoom(1.0));
  }

  function adjustZoom(delta) {
    setZoom(Math.min(1.3, Math.max(0.45, currentZoom + delta)));
  }

  function setZoom(val) {
    currentZoom = Math.round(val * 100) / 100;
    if (resumePageEl) {
      resumePageEl.style.transform = `scale(${currentZoom})`;
      resumePageEl.style.transformOrigin = 'top center';
    }
    if (zoomLevelDisplay) {
      zoomLevelDisplay.textContent = `${Math.round(currentZoom * 100)}%`;
    }
  }

  function autoFitZoom() {
    if (!previewCanvasWrap || !resumePageEl) return;
    const availableWidth = previewCanvasWrap.clientWidth - 40; // 20px padding each side
    const paperWidth = 794; // approx A4 width in px (210mm @ 96dpi)
    if (availableWidth > 0) {
      const fitScale = Math.min(1.0, Math.max(0.5, availableWidth / paperWidth));
      setZoom(fitScale);
    }
  }

  // ==================== 6. DYNAMIC RESUME RENDERER ====================
  function renderLiveResume(data) {
    if (!data) return;

    const user = data.user || {};
    const contacts = data.contacts;
    const summary = data.summary;
    const education = data.education || [];
    const experience = data.experience || [];
    const projects = data.projects || [];
    const skills = data.skills || [];
    const certs = data.certifications || [];
    const innovations = data.innovations || [];
    const coursework = data.coursework || [];

    // Header
    const nameEl = document.getElementById('liveHeaderName');
    if (nameEl) nameEl.textContent = contacts?.fullname || user.name || 'Your Full Name';

    const contactLineEl = document.getElementById('liveHeaderContact');
    if (contactLineEl) {
      let parts = [];
      if (contacts?.phone) parts.push(`+91 ${contacts.phone}`);
      if (contacts?.email) parts.push(contacts.email);
      if (contacts?.p_web) parts.push(`<a href="https://${contacts.p_web.replace(/^https?:\/\//, '')}" target="_blank">${contacts.p_web}</a>`);
      if (contacts?.l_web) parts.push(`<a href="https://${contacts.l_web.replace(/^https?:\/\//, '')}" target="_blank">LinkedIn</a>`);
      if (contacts?.City || contacts?.State) {
        const loc = [contacts.City, contacts.State, contacts.Country].filter(Boolean).map(capitalize).join(', ');
        if (loc) parts.push(loc);
      }
      contactLineEl.innerHTML = parts.join(' | ') || 'Phone | Email | LinkedIn | Location';
    }

    // Summary
    const summarySec = document.getElementById('liveSummarySection');
    const summaryContent = document.getElementById('liveSummaryContent');
    if (summarySec && summaryContent) {
      if (summary && summary.summary_text) {
        summaryContent.textContent = summary.summary_text;
        summarySec.classList.remove('hidden-section');
      } else {
        summarySec.classList.add('hidden-section');
      }
    }

    // Layout splitting: Two-column vs One-column
    const isTwoColumn = currentTemplate === 'two_column';
    const bodyContainer = document.getElementById('liveResumeBody');

    if (isTwoColumn) {
      renderTwoColumnBody(bodyContainer, { skills, certs, coursework, education, experience, projects, innovations });
    } else {
      renderOneColumnBody(bodyContainer, { education, experience, projects, skills, certs, innovations, coursework });
    }
  }

  function renderOneColumnBody(container, sections) {
    if (!container) return;

    let html = `
      <!-- Experience -->
      <div class="section section-experience" id="liveExpSection">
        <h2>Experience</h2>
        <div id="liveExpDraft" class="draft-preview-item" style="display: none;"></div>
        <div id="liveExpList">
          ${sections.experience.length ? sections.experience.map(renderExperienceItem).join('') : '<p class="empty-hint">No experience added yet.</p>'}
        </div>
      </div>

      <!-- Education -->
      <div class="section section-education" id="liveEduSection">
        <h2>Education</h2>
        <div id="liveEduDraft" class="draft-preview-item" style="display: none;"></div>
        <div id="liveEduList">
          ${sections.education.length ? sections.education.map(renderEducationItem).join('') : '<p class="empty-hint">No education records added yet.</p>'}
        </div>
      </div>

      <!-- Projects -->
      <div class="section section-projects" id="liveProjSection">
        <h2>Projects</h2>
        <div id="liveProjDraft" class="draft-preview-item" style="display: none;"></div>
        <div id="liveProjList">
          ${sections.projects.length ? sections.projects.map(renderProjectItem).join('') : '<p class="empty-hint">No projects added yet.</p>'}
        </div>
      </div>

      <!-- Skills -->
      <div class="section section-skills" id="liveSkillsSection">
        <h2>Skills</h2>
        <div id="liveSkillsList">
          ${sections.skills.length ? sections.skills.map(renderSkillItem).join('') : '<p class="empty-hint">No skills added yet.</p>'}
        </div>
      </div>

      <!-- Certifications -->
      ${sections.certs.length ? `
      <div class="section section-certifications">
        <h2>Certifications</h2>
        <ul>${sections.certs.map(renderCertItem).join('')}</ul>
      </div>` : ''}

      <!-- Innovations -->
      ${sections.innovations.length ? `
      <div class="section section-innovations">
        <h2>Innovations & Achievements</h2>
        <ul>${sections.innovations.map(renderInnovationItem).join('')}</ul>
      </div>` : ''}

      <!-- Coursework -->
      ${sections.coursework.length ? `
      <div class="section section-coursework">
        <h2>Relevant Coursework</h2>
        <ul>${sections.coursework.map(renderCourseworkItem).join('')}</ul>
      </div>` : ''}
    `;

    container.innerHTML = html;
  }

  function renderTwoColumnBody(container, sections) {
    if (!container) return;

    let html = `
      <!-- Left Column (Sidebar) -->
      <div class="resume-sidebar-col">
        <!-- Skills -->
        <div class="section section-skills">
          <h2>Skills</h2>
          ${sections.skills.length ? sections.skills.map(renderSkillItem).join('') : '<p class="empty-hint">No skills added.</p>'}
        </div>

        <!-- Certifications -->
        ${sections.certs.length ? `
        <div class="section section-certifications">
          <h2>Certifications</h2>
          <ul style="list-style: none; padding-left: 0;">${sections.certs.map(renderCertItem).join('')}</ul>
        </div>` : ''}

        <!-- Coursework -->
        ${sections.coursework.length ? `
        <div class="section section-coursework">
          <h2>Coursework</h2>
          <ul style="list-style: none; padding-left: 0;">${sections.coursework.map(renderCourseworkItem).join('')}</ul>
        </div>` : ''}
      </div>

      <!-- Right Column (Main) -->
      <div class="resume-main-col">
        <!-- Experience -->
        <div class="section section-experience">
          <h2>Experience</h2>
          <div id="liveExpDraft" class="draft-preview-item" style="display: none;"></div>
          ${sections.experience.length ? sections.experience.map(renderExperienceItem).join('') : '<p class="empty-hint">No experience added.</p>'}
        </div>

        <!-- Education -->
        <div class="section section-education">
          <h2>Education</h2>
          <div id="liveEduDraft" class="draft-preview-item" style="display: none;"></div>
          ${sections.education.length ? sections.education.map(renderEducationItem).join('') : '<p class="empty-hint">No education added.</p>'}
        </div>

        <!-- Projects -->
        <div class="section section-projects">
          <h2>Projects</h2>
          <div id="liveProjDraft" class="draft-preview-item" style="display: none;"></div>
          ${sections.projects.length ? sections.projects.map(renderProjectItem).join('') : '<p class="empty-hint">No projects added.</p>'}
        </div>

        <!-- Innovations -->
        ${sections.innovations.length ? `
        <div class="section section-innovations">
          <h2>Innovations</h2>
          <ul>${sections.innovations.map(renderInnovationItem).join('')}</ul>
        </div>` : ''}
      </div>
    `;

    container.innerHTML = html;
  }

  // ==================== 7. ITEM TEMPLATES ====================
  function renderExperienceItem(exp) {
    return `
      <div class="item exp-item">
        <div class="item-header-row">
          <h3>${escapeHtml(exp.jobTitle)}</h3>
          <span>${escapeHtml(exp.company)}</span>
        </div>
        <p style="font-size: 11.5px; color: #64748b; margin: 2px 0;">
          ${[exp.location, [exp.startDate, exp.endDate || 'Present'].filter(Boolean).join(' - '), exp.employmentType].filter(Boolean).map(escapeHtml).join(' • ')}
        </p>
        ${exp.description ? `<p style="font-size: 12px; margin-top: 3px;">${escapeHtml(exp.description)}</p>` : ''}
      </div>
    `;
  }

  function renderEducationItem(edu) {
    return `
      <div class="item edu-item">
        <div class="item-header-row">
          <h3>${escapeHtml(edu.degree)} ${edu.fieldOfStudy ? 'in ' + escapeHtml(edu.fieldOfStudy) : ''}</h3>
          <span>${[edu.startDate, edu.endDate].filter(Boolean).join(' - ')}</span>
        </div>
        <p style="font-size: 12px; color: #475569; margin: 2px 0;">
          ${escapeHtml(edu.institution)} ${edu.gpa ? `• GPA: ${escapeHtml(edu.gpa)}` : ''}
        </p>
        ${edu.description ? `<p style="font-size: 11.5px; margin-top: 2px;">${escapeHtml(edu.description)}</p>` : ''}
      </div>
    `;
  }

  function renderProjectItem(proj) {
    return `
      <div class="item proj-item">
        <div class="item-header-row">
          <h3>${escapeHtml(proj.projectName)}</h3>
          ${proj.role ? `<span style="font-size: 12px; color: #64748b;">${escapeHtml(proj.role)}</span>` : ''}
        </div>
        ${proj.skills ? `<p style="font-size: 11.5px; color: #2563eb; margin: 2px 0;"><strong>Technologies:</strong> ${escapeHtml(proj.skills)}</p>` : ''}
        ${proj.description ? `<p style="font-size: 12px; margin-top: 2px;">${escapeHtml(proj.description)}</p>` : ''}
        ${proj.url ? `<p style="font-size: 11px;"><a href="${escapeHtml(proj.url)}" target="_blank">${escapeHtml(proj.url)}</a></p>` : ''}
      </div>
    `;
  }

  function renderSkillItem(skill) {
    return `
      <div class="skill-row" style="margin-bottom: 5px;">
        <strong>${escapeHtml(skill.category)}:</strong>
        <span>${escapeHtml(skill.skills)}</span>
        ${skill.proficiency ? `<span class="skill-proficiency" style="font-size: 11px; color: #64748b;">(${escapeHtml(skill.proficiency)})</span>` : ''}
      </div>
    `;
  }

  function renderCertItem(cert) {
    return `
      <li style="margin-bottom: 4px; font-size: 12px;">
        <strong>${escapeHtml(cert.certification_name)}</strong> — ${escapeHtml(cert.issuing_org)}
        ${cert.url ? `(<a href="${escapeHtml(cert.url)}" target="_blank">View</a>)` : ''}
      </li>
    `;
  }

  function renderInnovationItem(inn) {
    return `
      <li style="margin-bottom: 4px; font-size: 12px;">
        <strong>${escapeHtml(inn.title)}</strong> ${inn.date ? `(${escapeHtml(inn.date)})` : ''}
        ${inn.description ? `<p style="margin: 2px 0; font-size: 11.5px;">${escapeHtml(inn.description)}</p>` : ''}
      </li>
    `;
  }

  function renderCourseworkItem(course) {
    return `
      <li style="margin-bottom: 4px; font-size: 12px;">
        <strong>${escapeHtml(course.course_name)}</strong> — ${escapeHtml(course.institution)}
        ${course.grade ? `(Grade: ${escapeHtml(course.grade)})` : ''}
      </li>
    `;
  }

  // ==================== 8. SAVED ITEMS IN EDITOR PANEL ====================
  function initSavedItemsLists() {
    // Render initially for contact or whatever form is active
    renderSectionSavedItems('contactForm');
  }

  function renderSectionSavedItems(formId) {
    const listContainer = document.getElementById('savedItemsContainer');
    if (!listContainer) return;

    const dataKey = SECTION_MAP[formId];
    if (!dataKey || dataKey === 'contacts' || dataKey === 'summary') {
      listContainer.style.display = 'none';
      return;
    }

    const items = currentResume[dataKey] || [];
    if (!items.length) {
      listContainer.style.display = 'block';
      listContainer.innerHTML = `
        <div class="saved-items-header">
          <span><i class="fa-solid fa-list-check"></i> Saved Entries (${items.length})</span>
        </div>
        <div class="saved-empty-state">No entries saved in this section yet. Fill the form above and click Add!</div>
      `;
      return;
    }

    listContainer.style.display = 'block';
    let html = `
      <div class="saved-items-header">
        <span><i class="fa-solid fa-list-check"></i> Saved Entries (${items.length})</span>
        <span style="font-size: 11px; color: #64748b;">Instant Edit / Delete</span>
      </div>
      <div class="saved-items-list">
    `;

    items.forEach(item => {
      let id = item.education_id || item.experience_id || item.project_id || item.skill_id || item.certification_id || item.innovation_id || item.coursework_id;
      let title = item.degree || item.jobTitle || item.projectName || item.category || item.certification_name || item.title || item.course_name || 'Entry';
      let subtitle = item.institution || item.company || item.role || item.skills || item.issuing_org || item.associated_with || '';
      let delUrl = getDeleteUrlForSection(dataKey, id);
      let editUrl = getEditUrlForSection(dataKey, id);

      html += `
        <div class="saved-item-row" id="saved-row-${id}">
          <div class="saved-item-info">
            <div class="saved-item-title">${escapeHtml(title)}</div>
            ${subtitle ? `<div class="saved-item-sub">${escapeHtml(subtitle)}</div>` : ''}
          </div>
          <div class="saved-item-actions">
            <a href="${editUrl}" class="btn-item-action btn-edit" title="Edit Entry">
              <i class="fa-solid fa-pen"></i> Edit
            </a>
            <button class="btn-item-action btn-delete btn-ajax-delete" data-url="${delUrl}" data-id="${id}" title="Delete Entry">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
        </div>
      `;
    });

    html += `</div>`;
    listContainer.innerHTML = html;

    // Attach AJAX delete listeners
    listContainer.querySelectorAll('.btn-ajax-delete').forEach(btn => {
      btn.addEventListener('click', handleAjaxDelete);
    });
  }

  function handleAjaxDelete(e) {
    e.preventDefault();
    const btn = this;
    const url = btn.getAttribute('data-url');
    const id = btn.getAttribute('data-id');

    if (!confirm('Are you sure you want to delete this entry?')) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                      document.querySelector('input[name="csrf_token"]')?.value || '';

    const formData = new FormData();
    formData.append('csrf_token', csrfToken);

    fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
        'Accept': 'application/json'
      },
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const row = document.getElementById(`saved-row-${id}`);
          if (row) {
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '0';
            row.style.transform = 'translateX(20px)';
            setTimeout(() => row.remove(), 300);
          }

          currentResume = data.resume || currentResume;
          renderLiveResume(currentResume);
          showStudioToast(data.message || 'Entry deleted.', 'info');
        } else {
          showStudioToast(data.error || 'Failed to delete entry.', 'danger');
          btn.disabled = false;
          btn.innerHTML = '<i class="fa-solid fa-trash"></i> Delete';
        }
      })
      .catch(err => {
        console.error('Delete error:', err);
        showStudioToast('Network error while deleting.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-trash"></i> Delete';
      });
  }

  function getDeleteUrlForSection(sectionKey, id) {
    const map = {
      education: `/delete_education/${id}`,
      experience: `/delete_experience/${id}`,
      projects: `/delete_project/${id}`,
      skills: `/delete_skill/${id}`,
      certifications: `/delete_certification/${id}`,
      innovations: `/delete_innovation/${id}`,
      coursework: `/delete_coursework/${id}`
    };
    return map[sectionKey] || '#';
  }

  function getEditUrlForSection(sectionKey, id) {
    const map = {
      education: `/edit_education/${id}`,
      experience: `/edit_experience/${id}`,
      projects: `/edit_project/${id}`,
      skills: `/edit_skill/${id}`,
      certifications: `/edit_certification/${id}`,
      innovations: `/edit_innovation/${id}`,
      coursework: `/edit_coursework/${id}`
    };
    return map[sectionKey] || '#';
  }

  // ==================== 9. TOAST NOTIFICATION SYSTEM ====================
  function showStudioToast(message, type = 'info') {
    let container = document.getElementById('studioToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'studioToastContainer';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `studio-toast studio-toast-${type}`;

    const iconClass = type === 'success' ? 'fa-circle-check' : (type === 'danger' ? 'fa-circle-exclamation' : 'fa-circle-info');

    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <i class="fa-solid ${iconClass}"></i>
        <span>${escapeHtml(message)}</span>
      </div>
      <button class="toast-close" style="background: none; border: none; cursor: pointer; color: inherit; font-size: 16px; opacity: 0.7;">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());

    container.appendChild(toast);

    // Auto remove after 3.8s
    setTimeout(() => {
      toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      setTimeout(() => toast.remove(), 400);
    }, 3800);
  }

  // ==================== UTILITIES ====================
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

})();
