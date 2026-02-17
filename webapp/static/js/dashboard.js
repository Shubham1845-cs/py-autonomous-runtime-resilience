// Dashboard Page JavaScript

async function updateDashboard() {
    try {
        // Fetch global stats
        const statsRes = await fetch('/api/stats');
        const stats = await statsRes.json();
        
        document.getElementById('dash-services').textContent = stats.total_services;
        document.getElementById('dash-calls').textContent = stats.total_calls.toLocaleString();
        document.getElementById('dash-patterns').textContent = stats.active_patterns;
        
        const statusEl = document.getElementById('dash-status');
        statusEl.textContent = stats.system_status;
        
        // Update status color
        statusEl.className = 'stat-value';
        if (stats.system_status === 'Critical') {
            statusEl.style.color = 'var(--accent-red)';
        } else if (stats.system_status === 'Degraded') {
            statusEl.style.color = 'var(--accent-amber)';
        } else {
            statusEl.style.color = 'var(--accent-green)';
        }

        // Fetch services
        const servicesRes = await fetch('/api/services');
        const services = await servicesRes.json();
        
        const container = document.getElementById('services-container');
        
        if (services.length === 0) {
            container.innerHTML = `
                <div class="loading-state">
                    <p>No services monitored yet. Make some HTTP calls to see them here!</p>
                </div>`;
            return;
        }

        container.innerHTML = services.map(s => `
            <div class="service-card ${s.status}">
                <div class="card-header">
                    <div>
                        <h3 style="font-size: 1.125rem; margin-bottom: 0.5rem;">${s.service}</h3>
                        <span class="status-badge status-${s.status}">${s.status}</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="metric-row">
                        <span class="metric-label">Failure Rate</span>
                        <span class="metric-value ${s.failure_rate > 20 ? 'status-critical' : ''}">${s.failure_rate}%</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Avg. Latency</span>
                        <span class="metric-value">${s.avg_latency}s</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Calls</span>
                        <span class="metric-value">${s.total_calls}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Window</span>
                        <span class="metric-value">${s.window_seconds}s</span>
                    </div>
                    <div style="margin-top: 1rem;">
                        <span class="metric-label" style="display: block; margin-bottom: 0.5rem;">Health Score</span>
                        <progress value="${100 - s.failure_rate}" max="100"></progress>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to update dashboard:', error);
        document.getElementById('services-container').innerHTML = `
            <div class="loading-state">
                <p style="color: var(--accent-red);">Error loading data. Please check if the backend is running.</p>
            </div>`;
    }
}

// Update every 2 seconds
setInterval(updateDashboard, 2000);
updateDashboard();
