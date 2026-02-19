// ─── Monitor page — service selector + metrics detail ────────────────────

const selector   = document.getElementById('service-selector');
const timeRange  = document.getElementById('time-range');
const detailBox  = document.getElementById('service-detail');

// ── Populate service dropdown ─────────────────────────────────────────────
async function loadServices() {
    try {
        const res      = await fetch('/api/services');
        const services = await res.json();

        // Save current selection
        const current = selector.value;

        // Rebuild options
        selector.innerHTML = '<option value="">— Select a Service —</option>';
        services.forEach(s => {
            const opt = document.createElement('option');
            opt.value       = s.service;
            opt.textContent = s.service;
            if (s.service === current) opt.selected = true;
            selector.appendChild(opt);
        });

        // If only one service, auto-select it
        if (services.length === 1 && !current) {
            selector.value = services[0].service;
            loadDetail();
        }
    } catch (e) {
        console.error('Failed to load services:', e);
    }
}

// ── Load detail for selected service ─────────────────────────────────────
async function loadDetail() {
    const svc    = selector.value;
    const window = timeRange.value;
    if (!svc) { detailBox.classList.add('hidden'); return; }

    try {
        const res  = await fetch(`/api/service/${encodeURIComponent(svc)}?window=${window}`);
        const data = await res.json();

        detailBox.classList.remove('hidden');

        // ── Header ──
        document.getElementById('detail-service-name').textContent = svc;

        const badge = document.getElementById('detail-status-badge');
        const st    = data.summary?.status ?? 'unknown';
        badge.textContent = st;
        badge.className   = `badge-pill badge-${st}`;

        // ── Metric tiles ──
        document.getElementById('detail-failure-rate').textContent =
            (data.summary?.failure_rate ?? 0) + '%';
        document.getElementById('detail-latency').textContent =
            (data.summary?.avg_latency  ?? 0) + 's';
        document.getElementById('detail-calls').textContent =
            data.summary?.total_calls   ?? 0;
        document.getElementById('detail-window').textContent =
            (data.summary?.window_seconds ?? window) + 's';

        // ── Recommendation ──
        const recBox = document.getElementById('recommendation-box');
        if (data.recommendation) {
            recBox.style.display = '';
            document.getElementById('rec-pattern').textContent =
                data.recommendation.pattern.replace('_', ' ').toUpperCase();
            document.getElementById('rec-reason').textContent =
                data.recommendation.reason;
        } else {
            recBox.style.display = 'none';
        }

        // ── Calls table ──
        const tbody  = document.getElementById('metrics-table-body');
        const metrics = data.metrics ?? [];

        if (!metrics.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-row">No calls recorded in this window</td></tr>`;
            return;
        }

        // newest first
        tbody.innerHTML = [...metrics].reverse().slice(0, 50).map(m => {
            const ts  = new Date(m.timestamp * 1000).toLocaleTimeString();
            const dur = m.duration < 1
                ? (m.duration * 1000).toFixed(0) + 'ms'
                : m.duration.toFixed(3) + 's';
            const ok  = m.status >= 200 && m.status < 400;
            const statusCls = ok ? 'status-ok' : 'status-err';
            return `
            <tr>
              <td>${ts}</td>
              <td>${dur}</td>
              <td><span class="${statusCls}">${m.status || '(conn fail)'}</span></td>
              <td style="color:var(--red);font-size:.8rem">${m.error ?? '—'}</td>
            </tr>`;
        }).join('');

    } catch (e) {
        console.error('Failed to load detail:', e);
    }
}

// ── Events ────────────────────────────────────────────────────────────────
selector.addEventListener('change', loadDetail);
timeRange.addEventListener('change', loadDetail);

// ── Poll ─────────────────────────────────────────────────────────────────
loadServices();
loadDetail();

setInterval(loadServices, 5000);
setInterval(loadDetail,   3000);
