// Dashboard — real-time service health
async function updateDashboard() {
    try {
        const [statsRes, servicesRes] = await Promise.all([
            fetch('/api/stats'),
            fetch('/api/services')
        ]);
        const stats    = await statsRes.json();
        const services = await servicesRes.json();

        // ── Stats bar ──
        document.getElementById('dash-services').textContent = stats.total_services;
        document.getElementById('dash-calls').textContent    = Number(stats.total_calls).toLocaleString();
        document.getElementById('dash-patterns').textContent = stats.active_patterns;
        document.getElementById('dash-status').textContent   = stats.system_status;

        // ── Services grid ──
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
                    <div class="health-bar-fill" style="width:${healthPct}%;background:${healthPct > 60 ? 'linear-gradient(90deg,var(--green),var(--accent))' : healthPct > 30 ? 'linear-gradient(90deg,var(--amber),var(--red))' : 'var(--red)'}"></div>
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

setInterval(updateDashboard, 2000);
updateDashboard();
