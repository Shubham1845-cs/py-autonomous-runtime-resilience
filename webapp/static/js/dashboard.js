// ─── Dashboard — real-time service health + agent events ───────────────────

// ── PATTERN META ──────────────────────────────────────────────────────────
const PATTERN_META = {
    circuit_breaker: { icon: 'fa-bolt',         label: 'Circuit Breaker', color: '#f59e0b' },
    retry:           { icon: 'fa-rotate-right',  label: 'Retry',           color: '#3b82f6' },
    timeout:         { icon: 'fa-hourglass-half',label: 'Timeout',         color: '#a855f7' },
};

// ── EVENT META ────────────────────────────────────────────────────────────
const EVENT_META = {
    pattern_injected: { icon: 'fa-shield-plus',      color: '#10b981', label: 'Injected'  },
    pattern_removed:  { icon: 'fa-shield-slash',      color: '#6b7280', label: 'Removed'   },
    service_critical: { icon: 'fa-circle-exclamation',color: '#ef4444', label: 'Critical'  },
    service_healthy:  { icon: 'fa-circle-check',      color: '#10b981', label: 'Recovered' },
    scan_complete:    { icon: 'fa-magnifying-glass',  color: '#4f8ef7', label: 'Scan'      },
};

// ── SERVICE CARDS ─────────────────────────────────────────────────────────
// Track previous pattern state per service to detect changes
const _prevPatterns = {};

async function updateDashboard() {
    try {
        const [statsRes, servicesRes] = await Promise.all([
            fetch('/api/stats'),
            fetch('/api/services'),
        ]);
        const stats    = await statsRes.json();
        const services = await servicesRes.json();

        // Feed 3D topology (if module is loaded)
        if (typeof window._topology3dUpdate === 'function') {
            window._topology3dUpdate(services);
        }

        // Stats bar
        document.getElementById('dash-services').textContent = stats.total_services;
        document.getElementById('dash-calls').textContent    = Number(stats.total_calls).toLocaleString();
        document.getElementById('dash-patterns').textContent = stats.active_patterns;
        document.getElementById('dash-status').textContent   = stats.system_status;

        // Status icon colour
        const statusIcon = document.getElementById('dash-status-icon');
        if (statusIcon) {
            statusIcon.style.color =
                stats.system_status === 'Critical'  ? 'var(--red)'   :
                stats.system_status === 'Degraded'  ? 'var(--amber)' : 'var(--green)';
        }

        // Services grid
        const container = document.getElementById('services-container');
        if (!services.length) {
            container.innerHTML = `
              <div class="empty-card">
                <i class="fa-solid fa-satellite-dish fa-beat-fade"></i>
                <p>No services monitored yet.<br>Make HTTP calls with <code>install_monitor()</code> active.</p>
              </div>`;
            return;
        }

        container.innerHTML = services.map(s => {
            const healthPct = Math.max(0, 100 - parseFloat(s.failure_rate));
            const stateIcon = {
                healthy:  'fa-circle-check',
                degraded: 'fa-triangle-exclamation',
                critical: 'fa-circle-xmark',
                slow:     'fa-gauge-simple-low',
            }[s.status] ?? 'fa-circle-question';

        // ── Pattern UI: badge + explanation panel ──────────────────────────
        const PATTERN_EXPLAIN = {
            retry: {
                what: 'Retry with Exponential Backoff',
                why:  'High rate of transient failures (HTTP 5xx / network errors) detected.',
                does: 'Automatically re-attempts failed requests up to <b>3×</b> using exponential backoff, recovering from temporary outages without crashing.',
                icon: 'fa-rotate-right',
                color: '#3b82f6',
            },
            circuit_breaker: {
                what: 'Circuit Breaker',
                why:  'Sustained failure rate crossed critical threshold — service is overloaded.',
                does: 'Stops all traffic to the failing service immediately <b>(OPEN state)</b>, preventing cascading failures. Auto-retries after a cooldown period.',
                icon: 'fa-bolt',
                color: '#f59e0b',
            },
            timeout: {
                what: 'Timeout Guard',
                why:  'Average response latency is dangerously high — requests hanging.',
                does: 'Cuts off slow requests after a configurable deadline, preventing thread exhaustion and resource starvation on the client side.',
                icon: 'fa-hourglass-half',
                color: '#a855f7',
            },
        };

        let patternPanel = '';
        if (s.active_pattern) {
            const ex  = PATTERN_EXPLAIN[s.active_pattern] ?? { what: s.active_pattern, why: 'Anomaly detected.', does: 'Resilience pattern active.', icon: 'fa-shield-halved', color: '#6b7280' };
            const cfg = s.pattern_details?.config ?? {};
            const age = s.pattern_details?.age_seconds != null ? Math.round(s.pattern_details.age_seconds) + 's' : 'N/A';

            // Config rows (only show fields that exist)
            const cfgRows = Object.entries(cfg).map(([k, v]) =>
                `<div class="pi-cfg-row"><span class="pi-cfg-key">${k.replace(/_/g,' ')}</span><span class="pi-cfg-val">${v}</span></div>`
            ).join('');

            patternPanel = `
            <div class="pattern-info-panel" style="--pc:${ex.color};--pbg:${ex.color}18">
              <div class="pip-header">
                <div class="pip-badge">
                  <i class="fa-solid fa-shield-halved pip-shield"></i>
                  <span class="pip-label">PROTECTED</span>
                </div>
                <span class="pip-pattern-name"><i class="fa-solid ${ex.icon}"></i> ${ex.what}</span>
              </div>

              <div class="pip-row">
                <span class="pip-field-label"><i class="fa-solid fa-arrow-right"></i> Wrapping</span>
                <span class="pip-field-val"><code>requests</code> library calls to <code>${s.service}</code></span>
              </div>
              <div class="pip-row">
                <span class="pip-field-label"><i class="fa-solid fa-triangle-exclamation"></i> Triggered by</span>
                <span class="pip-field-val">${ex.why}</span>
              </div>
              <div class="pip-row">
                <span class="pip-field-label"><i class="fa-solid fa-circle-info"></i> What it does</span>
                <span class="pip-field-val">${ex.does}</span>
              </div>
              ${cfgRows ? `<div class="pip-cfg-block"><div class="pip-cfg-title">⚙️ Pattern Config</div>${cfgRows}</div>` : ''}
              <div class="pip-age">Active for <b>${age}</b></div>
            </div>`;
        }

        const barColor = healthPct > 60
            ? 'linear-gradient(90deg,var(--green),var(--accent))'
            : healthPct > 30
                ? 'linear-gradient(90deg,var(--amber),var(--red))'
                : 'var(--red)';

            // Detect pattern change to trigger flash animation
            const prevPattern = _prevPatterns[s.service];
            const curPattern  = s.active_pattern || null;
            const patternChanged = prevPattern !== curPattern;
            _prevPatterns[s.service] = curPattern;
            const flashClass = patternChanged && curPattern ? ' pip-flash' : '';

            return `
            <div class="service-card ${s.status}">
              <div class="sc-card-header">
                <div class="sc-card-title">
                  <i class="fa-solid fa-server"></i>
                  ${s.service}
                </div>
                <span class="badge-pill badge-${s.status}">
                  <i class="fa-solid ${stateIcon}"></i>
                  ${s.status}
                </span>
              </div>
              <div class="pattern-panel-slot${flashClass}">${patternPanel}</div>
              <div class="sc-card-body">
                <div class="sc-metric-row">
                  <span class="lbl"><i class="fa-solid fa-triangle-exclamation"></i>Failure Rate</span>
                  <span class="val" style="color:${parseFloat(s.failure_rate) > 20 ? 'var(--red)' : 'var(--green)'}">${s.failure_rate}%</span>
                </div>
                <div class="sc-metric-row">
                  <span class="lbl"><i class="fa-solid fa-stopwatch"></i>Avg Latency</span>
                  <span class="val">${s.avg_latency}s</span>
                </div>
                <div class="sc-metric-row">
                  <span class="lbl"><i class="fa-solid fa-arrow-right-arrow-left"></i>Total Calls</span>
                  <span class="val">${s.total_calls}</span>
                </div>
                <div class="sc-metric-row">
                  <span class="lbl"><i class="fa-solid fa-clock"></i>Window</span>
                  <span class="val">${s.window_seconds}s</span>
                </div>
                <div class="health-bar">
                  <div class="health-bar-track">
                    <div class="health-bar-fill" style="width:${healthPct}%;background:${barColor}"></div>
                  </div>
                </div>
              </div>
            </div>`;
        }).join('');

    } catch (e) {
        console.error('Dashboard update error:', e);
        document.getElementById('services-container').innerHTML = `
          <div class="empty-card">
            <i class="fa-solid fa-circle-xmark" style="color:var(--red)"></i>
            <p>Cannot connect to backend. Is <code>app.py</code> running?</p>
          </div>`;
    }
}

// ── AGENT STATUS ──────────────────────────────────────────────────────────
async function updateAgentStatus() {
    try {
        const res  = await fetch('/api/agent/status');
        const data = await res.json();

        const scansEl   = document.getElementById('ag-scans');
        const uptimeEl  = document.getElementById('ag-uptime');
        const activeEl  = document.getElementById('ag-active');
        const pillEl    = document.getElementById('ag-running-pill');

        if (scansEl)  scansEl.textContent  = data.scan_count ?? '—';
        if (activeEl) activeEl.textContent = data.active_injections ?? 0;

        if (uptimeEl) {
            const u = Math.round(data.uptime_seconds ?? 0);
            uptimeEl.textContent = u < 60 ? `${u}s` : u < 3600 ? `${Math.floor(u/60)}m ${u%60}s` : `${Math.floor(u/3600)}h`;
        }

        if (pillEl) {
            const running = data.running;
            pillEl.innerHTML = running
                ? `<i class="fa-solid fa-circle" style="color:var(--green)"></i> Running`
                : `<i class="fa-solid fa-circle" style="color:var(--red)"></i> Stopped`;
        }
    } catch (_) { /* agent not yet started */ }
}

// ── AGENT EVENTS FEED ─────────────────────────────────────────────────────
let _lastEventTs = 0;

async function updateEventsFeed() {
    try {
        const res    = await fetch('/api/agent/events?limit=25');
        const events = await res.json();  // newest-last from API
        const feed   = document.getElementById('events-feed');
        if (!feed) return;

        // Filter out idle scan_complete events (keep scans with actions + all other events)
        const visible = events.filter(e =>
            e.event !== 'scan_complete' || (e.details?.actions_taken ?? 0) > 0
        );

        if (!visible.length) {
            // Show latest scan info instead of static placeholder
            const latest = events[events.length - 1];
            if (latest?.details?.scan_number) {
                feed.innerHTML = `<div class="event-row" style="opacity:.6">
                    <div class="ev-icon" style="background:#6b728020;color:#6b7280"><i class="fa-solid fa-radar"></i></div>
                    <div class="ev-body">
                        <div class="ev-title"><span class="ev-label" style="color:#6b7280">Scanning</span></div>
                        <div class="ev-detail">Scan #${latest.details.scan_number} — ${latest.details.services_scanned} service(s) monitored, no issues detected</div>
                    </div>
                    <div class="ev-time">${new Date(latest.timestamp * 1000).toLocaleTimeString()}</div>
                </div>`;
            }
            return;
        }

        // Render newest first
        const reversed = [...visible].reverse();
        feed.innerHTML = reversed.map(e => {
            const meta  = EVENT_META[e.event] ?? { icon: 'fa-circle-info', color: '#6b7280', label: e.event };
            const time  = new Date(e.timestamp * 1000).toLocaleTimeString();
            const isNew = e.timestamp > _lastEventTs;

            let detail = '';
            if (e.details?.pattern)      detail += ` <strong>${e.details.pattern.replace('_', ' ')}</strong>`;
            if (e.details?.reason)       detail += ` — ${e.details.reason}`;
            if (e.details?.health_state) detail += ` <span class="ev-state ev-${e.details.health_state}">${e.details.health_state}</span>`;

            return `
            <div class="event-row ${isNew ? 'event-new' : ''}">
              <div class="ev-icon" style="background:${meta.color}20;color:${meta.color}">
                <i class="fa-solid ${meta.icon}"></i>
              </div>
              <div class="ev-body">
                <div class="ev-title">
                  <span class="ev-label" style="color:${meta.color}">${meta.label}</span>
                  <span class="ev-service">${e.service}</span>
                </div>
                <div class="ev-detail">${detail}</div>
              </div>
              <div class="ev-time">${time}</div>
            </div>`;
        }).join('');

        // Update watermark
        if (visible.length) _lastEventTs = Math.max(...visible.map(e => e.timestamp));

    } catch (_) { /* silently skip */ }
}

// Initial calls
updateDashboard();
updateAgentStatus();
updateEventsFeed();

setInterval(updateDashboard,   1500);  // fast — mirrors agent 2s scan
setInterval(updateAgentStatus, 2000);
setInterval(updateEventsFeed,  2000);

// ═══════════════════════════════════════════════════════════════════════════
// CHAOS CONTROL PANEL
// ═══════════════════════════════════════════════════════════════════════════

/** Map mode → CSS hex colour */
const CHAOS_COLORS = {
    error_storm:     '#ef4444',
    latency_spike:   '#f59e0b',
    connection_drop: '#a855f7',
    partial_outage:  '#3b82f6',
};

/** Map mode → FA icon class */
const CHAOS_ICONS = {
    error_storm:     'fa-bolt',
    latency_spike:   'fa-hourglass-half',
    connection_drop: 'fa-plug-circle-xmark',
    partial_outage:  'fa-cloud-bolt',
};

/** Map mode → button element id */
const CHAOS_BTN_IDS = {
    error_storm:     'btn-error-storm',
    latency_spike:   'btn-latency-spike',
    connection_drop: 'btn-connection-drop',
    partial_outage:  'btn-partial-outage',
};

/** Convert a CSS hex like #ef4444 → "239 68 68" for use in rgba(). */
function hexToRgbSpace(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r} ${g} ${b}`;
}

/**
 * Render the chaos panel from an API status object.
 * @param {Object} status - response from GET /api/chaos
 */
function applyChaosStatus(status) {
    const panel  = document.getElementById('chaos-panel');
    const ring   = document.getElementById('chaos-ring');
    const icon   = document.getElementById('chaos-state-icon');
    const label  = document.getElementById('chaos-mode-label');
    const sub    = document.getElementById('chaos-mode-sub');
    if (!panel) return;

    const mode   = status.mode;
    const active = status.active;
    const color  = active ? (CHAOS_COLORS[mode] || '#ef4444') : '#10b981';
    const rgb    = hexToRgbSpace(color);

    // Toggle active class on panel
    panel.classList.toggle('chaos-active', active);

    // Update CSS custom properties so the ring/stripe pick up the right colour
    panel.style.setProperty('--chaos-color', color);
    panel.style.setProperty('--chaos-rgb',   rgb);
    ring.style.borderColor = color;

    // Update icon
    const iconClass = active ? (CHAOS_ICONS[mode] || 'fa-biohazard') : 'fa-circle-check';
    icon.className = `fa-solid ${iconClass} chaos-state-icon`;

    // Update status text
    label.textContent = active ? status.label : 'No Fault Active';
    sub.textContent   = active
        ? `Active for ${status.age_seconds}s — AutoHeal agent is watching`
        : 'System is nominal';

    // Highlight active button, unhighlight others
    Object.entries(CHAOS_BTN_IDS).forEach(([m, btnId]) => {
        const btn = document.getElementById(btnId);
        if (btn) btn.classList.toggle('active', active && m === mode);
    });
}

/** Toggle the `chaos-active` class instantly for immediate feedback before the poll. */
function _optimisticUpdate(mode) {
    const color = CHAOS_COLORS[mode] || '#ef4444';
    const panel = document.getElementById('chaos-panel');
    if (panel) {
        panel.classList.add('chaos-active');
        panel.style.setProperty('--chaos-color', color);
        panel.style.setProperty('--chaos-rgb',   hexToRgbSpace(color));
    }
    const icon = document.getElementById('chaos-state-icon');
    if (icon) icon.className = `fa-solid ${CHAOS_ICONS[mode] || 'fa-biohazard'} chaos-state-icon`;
}

/**
 * Inject a fault mode via POST /api/chaos.
 * @param {string} mode - one of the valid chaos mode strings
 */
async function injectChaos(mode) {
    // Optimistic visual update before the request returns
    _optimisticUpdate(mode);

    try {
        const res  = await fetch('/api/chaos', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ mode }),
        });
        const data = await res.json();
        if (!data.ok) console.warn('[Chaos] inject failed:', data.error);

        // Sync authoritative state
        await updateChaosPanel();
    } catch (err) {
        console.error('[Chaos] network error:', err);
    }
}

/**
 * Clear all active faults via DELETE /api/chaos.
 */
async function clearChaos() {
    const panel = document.getElementById('chaos-panel');
    if (panel) panel.classList.remove('chaos-active');

    try {
        await fetch('/api/chaos', { method: 'DELETE' });
        await updateChaosPanel();
    } catch (err) {
        console.error('[Chaos] clear error:', err);
    }
}

/**
 * Poll /api/chaos and refresh the UI.
 */
async function updateChaosPanel() {
    try {
        const res    = await fetch('/api/chaos');
        const status = await res.json();
        applyChaosStatus(status);
    } catch (_) { /* silently skip */ }
}

// Initial load + 2-second polling
updateChaosPanel();
setInterval(updateChaosPanel, 2000);
