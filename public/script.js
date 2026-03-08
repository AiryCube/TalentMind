/* ═══════════════════════════════════════════════════════════════
   LinkedIn Recruiter Agent — Dashboard JavaScript
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// ─── DOM Elements ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Navigation ────────────────────────────────────────────────
const navLinks = $$('.nav-link');
const sections = $$('.content-section');
const pageTitle = $('#page-title');

const sectionTitles = {
    dashboard: 'Dashboard',
    interactions: 'Interações',
    alerts: 'Alertas & Entrevistas',
    config: 'Configurações',
};

function switchSection(sectionId) {
    navLinks.forEach((l) => l.classList.remove('active'));
    sections.forEach((s) => s.classList.remove('active'));

    const link = $(`[data-section="${sectionId}"]`);
    const section = $(`#section-${sectionId}`);
    if (link) link.classList.add('active');
    if (section) section.classList.add('active');
    if (pageTitle) pageTitle.textContent = sectionTitles[sectionId] || 'Dashboard';

    // Load data for the section
    if (sectionId === 'interactions') loadInteractions();
    if (sectionId === 'alerts') loadAlerts();
    if (sectionId === 'config') loadConfig();
}

navLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        switchSection(link.dataset.section);
    });
});

// Link "Ver todas" on dashboard
const linkSeeAll = $('#link-see-all-interactions');
if (linkSeeAll) {
    linkSeeAll.addEventListener('click', (e) => {
        e.preventDefault();
        switchSection('interactions');
    });
}

// Mobile menu toggle
const menuToggle = $('#menu-toggle');
const sidebar = $('#sidebar');
if (menuToggle) {
    menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
}

// ─── Toast Notifications ──────────────────────────────────────
function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle', warning: 'exclamation-triangle' };
    toast.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i> ${message}`;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 4000);
}

// ─── API Helpers ──────────────────────────────────────────────
async function api(path, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (err) {
        console.error(`API ${path}:`, err);
        throw err;
    }
}

// ─── Dashboard ────────────────────────────────────────────────
async function loadDashboard() {
    try {
        // Load message history stats
        const historyData = await api('/messages/history').catch(() => ({ messages: [] }));
        const messages = historyData.messages || [];
        const replies = messages.filter((m) => m.reply);

        $('#stat-total-messages').textContent = messages.length;
        $('#stat-replies').textContent = replies.length;

        // Load alerts
        const alertsData = await api('/config/alerts/list').catch(() => ({ alerts: [] }));
        const alerts = alertsData.alerts || [];
        const interviews = alerts.filter((a) => a.alert_type === 'interview');

        $('#stat-interviews').textContent = interviews.length;
        $('#stat-alerts').textContent = alerts.length;

        // Update badge
        const badge = $('#alert-badge');
        if (alerts.length > 0) {
            badge.style.display = 'inline';
            badge.textContent = alerts.length;
        } else {
            badge.style.display = 'none';
        }

        // Render recent interactions (last 5)
        renderRecentInteractions(messages.slice(0, 5));

        // Render upcoming events
        renderUpcomingEvents(alerts);
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
}

function renderRecentInteractions(messages) {
    const container = $('#recent-interactions');
    if (!messages.length) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Nenhuma interação registrada ainda</p></div>';
        return;
    }
    container.innerHTML = messages.map((m) => renderInteractionItem(m)).join('');
}

function renderUpcomingEvents(alerts) {
    const container = $('#upcoming-events');
    const upcoming = alerts.filter((a) => a.scheduled_at && new Date(a.scheduled_at) > new Date());
    if (!upcoming.length) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-calendar-xmark"></i><p>Nenhum evento agendado</p></div>';
        return;
    }
    container.innerHTML = upcoming.map((a) => renderAlertItem(a)).join('');
}

// ─── Interactions ─────────────────────────────────────────────
let allInteractions = [];

async function loadInteractions() {
    const container = $('#interaction-list');
    try {
        const data = await api('/messages/history');
        allInteractions = data.messages || [];
        renderInteractions(allInteractions);
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Erro ao carregar interações</p></div>';
    }
}

function renderInteractions(messages) {
    const container = $('#interaction-list');
    if (!messages.length) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Nenhuma interação registrada</p></div>';
        return;
    }
    container.innerHTML = messages.map((m) => renderInteractionItem(m)).join('');
}

function renderInteractionItem(m) {
    const initials = (m.sender || '?').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
    const time = m.created_at ? formatDate(m.created_at) : '';
    const msgPreview = truncate(m.text || '', 200);
    const replyPreview = m.reply ? truncate(m.reply, 200) : '';

    return `
        <div class="interaction-item">
            <div class="interaction-avatar">${initials}</div>
            <div class="interaction-content">
                <div class="interaction-header">
                    <span class="interaction-sender">${escapeHtml(m.sender || 'Desconhecido')}</span>
                    <span class="interaction-time">${time}</span>
                </div>
                <div class="interaction-msg">${escapeHtml(msgPreview)}</div>
                ${replyPreview ? `<div class="interaction-reply">${escapeHtml(replyPreview)}</div>` : ''}
            </div>
        </div>
    `;
}

// Search filter
const searchInput = $('#search-interactions');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        const filtered = allInteractions.filter(
            (m) =>
                (m.sender || '').toLowerCase().includes(q) ||
                (m.text || '').toLowerCase().includes(q) ||
                (m.reply || '').toLowerCase().includes(q)
        );
        renderInteractions(filtered);
    });
}

// ─── Alerts ───────────────────────────────────────────────────
async function loadAlerts() {
    const container = $('#alerts-list');
    try {
        const data = await api('/config/alerts/list');
        const alerts = data.alerts || [];
        if (!alerts.length) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><p>Nenhum alerta ativo</p></div>';
            return;
        }
        container.innerHTML = alerts.map((a) => renderAlertItem(a)).join('');
        // Bind dismiss buttons
        container.querySelectorAll('.btn-dismiss-alert').forEach((btn) => {
            btn.addEventListener('click', () => dismissAlert(btn.dataset.id));
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Erro ao carregar alertas</p></div>';
    }
}

function renderAlertItem(a) {
    const iconClass = { interview: 'fa-bullseye', followup: 'fa-paper-plane', reminder: 'fa-clock' };
    const typeLabel = { interview: 'Entrevista', followup: 'Follow-up', reminder: 'Lembrete' };
    const icon = iconClass[a.alert_type] || 'fa-bell';
    const label = typeLabel[a.alert_type] || a.alert_type;
    const time = a.scheduled_at ? formatDate(a.scheduled_at) : '';

    return `
        <div class="alert-item">
            <div class="alert-icon ${a.alert_type}"><i class="fas ${icon}"></i></div>
            <div class="alert-body">
                <div class="alert-title">${escapeHtml(a.title)}</div>
                ${a.description ? `<div class="alert-desc">${escapeHtml(a.description)}</div>` : ''}
                <div class="alert-time"><i class="far fa-clock"></i> ${time || label}</div>
            </div>
            <div class="alert-actions">
                <button class="btn btn-sm btn-danger btn-dismiss-alert" data-id="${a.id}" title="Dispensar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `;
}

async function dismissAlert(id) {
    try {
        await api(`/config/alerts/${id}`, { method: 'DELETE' });
        showToast('Alerta dispensado', 'success');
        loadAlerts();
        loadDashboard();
    } catch (err) {
        showToast('Erro ao dispensar alerta', 'error');
    }
}

// New alert modal
const modalNewAlert = $('#modal-new-alert');
const btnNewAlert = $('#btn-new-alert');
const btnCloseModal = $('#btn-close-modal');
const btnCancelAlert = $('#btn-cancel-alert');
const btnSaveAlert = $('#btn-save-alert');

if (btnNewAlert) btnNewAlert.addEventListener('click', () => (modalNewAlert.style.display = 'flex'));
if (btnCloseModal) btnCloseModal.addEventListener('click', () => (modalNewAlert.style.display = 'none'));
if (btnCancelAlert) btnCancelAlert.addEventListener('click', () => (modalNewAlert.style.display = 'none'));

if (btnSaveAlert) {
    btnSaveAlert.addEventListener('click', async () => {
        const alertType = $('#alert-type').value;
        const title = $('#alert-title').value.trim();
        const description = $('#alert-description').value.trim();
        const datetime = $('#alert-datetime').value;

        if (!title) {
            showToast('Preencha o título do alerta', 'warning');
            return;
        }

        try {
            await api('/config/alerts/create', {
                method: 'POST',
                body: JSON.stringify({
                    alert_type: alertType,
                    title,
                    description: description || null,
                    scheduled_at: datetime || null,
                }),
            });
            showToast('Alerta criado com sucesso!', 'success');
            modalNewAlert.style.display = 'none';
            // Clear form
            $('#alert-title').value = '';
            $('#alert-description').value = '';
            $('#alert-datetime').value = '';
            loadAlerts();
            loadDashboard();
        } catch (err) {
            showToast('Erro ao criar alerta', 'error');
        }
    });
}

// ─── Config ───────────────────────────────────────────────────

// Simple text/textarea fields
const configFields = [
    { id: 'cfg-profile-summary', key: 'profile_summary' },
    { id: 'cfg-skills', key: 'skills' },
    { id: 'cfg-seniority', key: 'seniority' },
    { id: 'cfg-contact-email', key: 'contact_email' },
    { id: 'cfg-contact-whatsapp', key: 'contact_whatsapp' },
    { id: 'cfg-contact-phone', key: 'contact_phone' },
    { id: 'cfg-salary-expectation', key: 'salary_expectation' },
    { id: 'cfg-target-roles', key: 'target_roles' },
    { id: 'cfg-availability', key: 'availability' },
    { id: 'cfg-availability-notes', key: 'availability_notes' },
    { id: 'cfg-system-prompt', key: 'system_prompt' },
];

// Checkbox group fields (stored as comma-separated values)
const checkboxGroupFields = [
    { groupId: 'cfg-work-model-group', key: 'work_model' },
    { groupId: 'cfg-company-type-group', key: 'company_type' },
    { groupId: 'cfg-contract-type-group', key: 'contract_type' },
];

function getCheckboxValues(groupId) {
    const group = $(`#${groupId}`);
    if (!group) return '';
    const checked = group.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checked).map((cb) => cb.value).join(',');
}

function setCheckboxValues(groupId, value) {
    const group = $(`#${groupId}`);
    if (!group || !value) return;
    const values = value.split(',').map((v) => v.trim());
    group.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.checked = values.includes(cb.value);
    });
}

async function loadConfig() {
    try {
        const data = await api('/config/all');
        const cfg = data.config || {};

        // Text fields
        configFields.forEach(({ id, key }) => {
            const el = $(`#${id}`);
            if (el && cfg[key]) el.value = cfg[key];
        });

        // Checkbox groups
        checkboxGroupFields.forEach(({ groupId, key }) => {
            if (cfg[key]) setCheckboxValues(groupId, cfg[key]);
        });

        // Resume status
        try {
            const resumeData = await api('/config/resume/status');
            if (resumeData.has_resume) {
                $('#resume-status').style.display = 'block';
                $('#resume-ext-label').textContent = resumeData.extension.toUpperCase();
            }
        } catch (e) {
            console.error('Failed to load resume status:', e);
        }

    } catch (err) {
        console.error('Failed to load config:', err);
    }
}

const btnSaveConfig = $('#btn-save-config');
const saveStatus = $('#save-status');

if (btnSaveConfig) {
    btnSaveConfig.addEventListener('click', async () => {
        // Gather text field values
        const updates = configFields
            .map(({ id, key }) => {
                const el = $(`#${id}`);
                return el ? { key, value: el.value } : null;
            })
            .filter((u) => u !== null);

        // Gather checkbox group values
        checkboxGroupFields.forEach(({ groupId, key }) => {
            const val = getCheckboxValues(groupId);
            if (val) updates.push({ key, value: val });
        });

        try {
            await api('/config/save-batch', {
                method: 'PUT',
                body: JSON.stringify(updates),
            });
            showToast('Configurações salvas!', 'success');
            saveStatus.textContent = '✓ Salvo';
            saveStatus.classList.add('visible');
            setTimeout(() => saveStatus.classList.remove('visible'), 3000);
        } catch (err) {
            showToast('Erro ao salvar configurações', 'error');
        }
    });
}

// Upload Resume Logic
const btnUploadResume = $('#btn-upload-resume');
const resumeUpload = $('#resume-upload');

if (btnUploadResume && resumeUpload) {
    btnUploadResume.addEventListener('click', async () => {
        const file = resumeUpload.files[0];
        if (!file) {
            showToast('Por favor, selecione um arquivo primeiro', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const btnOriginalText = btnUploadResume.innerHTML;
        btnUploadResume.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
        btnUploadResume.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/config/resume`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('Falha no upload');

            showToast('Currículo salvo no servidor', 'success');

            // Extract extension to show in UI
            const nameParts = file.name.split('.');
            const ext = nameParts.length > 1 ? '.' + nameParts.pop() : '';

            $('#resume-status').style.display = 'block';
            $('#resume-ext-label').textContent = ext.toUpperCase();
            resumeUpload.value = ''; // clear input

        } catch (err) {
            console.error(err);
            showToast('Erro ao fazer upload do currículo', 'error');
        } finally {
            btnUploadResume.innerHTML = btnOriginalText;
            btnUploadResume.disabled = false;
        }
    });
}

// ─── Auto-fill Profile from LinkedIn ──────────────────────────
const btnAutofill = $('#btn-autofill-profile');
if (btnAutofill) {
    btnAutofill.addEventListener('click', async () => {
        const container = $('#autofill-status-container');
        const banner = $('#autofill-banner');

        container.style.display = 'block';
        banner.className = 'autofill-banner';
        banner.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando dados do seu perfil LinkedIn...';

        try {
            const data = await api('/linkedin/profile');
            const profile = data.profile || {};

            // Build summary from LinkedIn profile data
            const parts = [];

            if (profile.name) parts.push(`Nome: ${profile.name}`);
            if (profile.headline) parts.push(`Título: ${profile.headline}`);
            if (profile.location) parts.push(`Local: ${profile.location}`);
            if (profile.about) parts.push(`\nSobre:\n${profile.about}`);
            if (profile.experience && profile.experience.length) {
                parts.push(`\nExperiência recente:`);
                profile.experience.slice(0, 3).forEach((exp) => {
                    const line = `• ${exp.title || ''} — ${exp.company || ''} (${exp.duration || ''})`;
                    parts.push(line);
                });
            }
            if (profile.education && profile.education.length) {
                parts.push(`\nFormação:`);
                profile.education.slice(0, 2).forEach((edu) => {
                    parts.push(`• ${edu.school || ''} — ${edu.degree || ''}`);
                });
            }
            if (profile.skills && profile.skills.length) {
                const skillsEl = $('#cfg-skills');
                if (skillsEl && !skillsEl.value) {
                    skillsEl.value = profile.skills.join(', ');
                }
            }

            const summary = parts.join('\n');
            if (summary) {
                const summaryEl = $('#cfg-profile-summary');
                if (summaryEl) summaryEl.value = summary;
            }

            // Fill headline as seniority hint if empty
            if (profile.headline) {
                const seniorityEl = $('#cfg-seniority');
                if (seniorityEl && !seniorityEl.value) {
                    seniorityEl.value = profile.headline;
                }
            }

            banner.className = 'autofill-banner success';
            banner.innerHTML = '<i class="fas fa-check-circle"></i> Perfil preenchido com dados do LinkedIn! Revise e ajuste conforme necessário.';
            showToast('Perfil preenchido com sucesso!', 'success');
        } catch (err) {
            banner.className = 'autofill-banner error';
            banner.innerHTML = `<i class="fas fa-exclamation-circle"></i> Erro ao buscar perfil: ${escapeHtml(err.message)}. Verifique se o agente está logado no LinkedIn.`;
            showToast('Erro ao buscar perfil do LinkedIn', 'error');
        }
    });
}

// ─── Status Check ─────────────────────────────────────────────
async function checkStatus() {
    const indicator = $('#agent-status-indicator');
    try {
        const data = await api('/linkedin/status');
        const dot = indicator.querySelector('.status-dot');
        const label = indicator.querySelector('span:last-child');
        if (data.status === 'success' && data.is_logged_in) {
            dot.className = 'status-dot online';
            label.textContent = 'Agente Online';
            showToast('Agente conectado ao LinkedIn', 'success');
        } else if (data.status === 'success') {
            dot.className = 'status-dot offline';
            label.textContent = 'Não logado';
            showToast('Navegador ativo, mas não logado no LinkedIn', 'warning');
        } else {
            dot.className = 'status-dot offline';
            label.textContent = 'Agente Offline';
            showToast('Erro ao conectar com o navegador', 'error');
        }
    } catch (err) {
        showToast('Não foi possível verificar o status', 'error');
    }
}

$('#btn-check-status').addEventListener('click', checkStatus);
$('#btn-refresh').addEventListener('click', () => {
    showToast('Atualizando...', 'info');
    loadDashboard();
});

const btnRunAgent = $('#btn-run-agent');
if (btnRunAgent) {
    btnRunAgent.addEventListener('click', async () => {
        showToast('Iniciando o agente... Isso pode levar alguns minutos.', 'info');
        btnRunAgent.disabled = true;
        btnRunAgent.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

        try {
            const result = await api('/messages/process', { method: 'POST' });
            const qty = result.processed ? result.processed.length : 0;
            showToast(`Processamento concluído! ${qty} mensagens respondidas.`, 'success');
            loadDashboard(); // atualiza a tela
        } catch (err) {
            showToast('Erro ao rodar agente: ' + err.message, 'error');
        } finally {
            btnRunAgent.disabled = false;
            btnRunAgent.innerHTML = '<i class="fas fa-robot"></i> Rodar Agente (2026)';
        }
    });
}

// ─── Utility Functions ────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(text, maxLen) {
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

function formatDate(dateStr) {
    try {
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        const mins = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (diff < 0) {
            // Future date
            const absDays = Math.abs(days);
            if (absDays === 0) return `Hoje, ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
            if (absDays === 1) return `Amanhã, ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
            return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        }

        if (mins < 1) return 'Agora mesmo';
        if (mins < 60) return `${mins}min atrás`;
        if (hours < 24) return `${hours}h atrás`;
        if (days < 7) return `${days}d atrás`;
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
    } catch {
        return dateStr;
    }
}

// ─── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});