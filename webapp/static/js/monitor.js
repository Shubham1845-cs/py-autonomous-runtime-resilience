// Monitor Page JavaScript

let currentService = null;
let currentWindow = 300;

async function loadServiceSelector() {
    try {
        const res = await fetch('/api/services');
        const services = await res.json();
        
        const selector = document.getElementById('service-selector');
        selector.innerHTML = '<option value="">Select a service...</option>' +
            services.map(s => `<option value="${s.service}">${s.service}</option>`).join('');
        
        selector.addEventListener('change', (e) => {
            currentService = e.target.value;
            if (currentService) {
                loadServiceDetail();
            } else {
                document.getElementById('service-detail').classList.add('hidden');
            }
        });
    } catch (error) {
        console.error('Failed to load services:', error);
    }
}

async function loadServiceDetail() {
    if (!currentService) return;
    
    try {
        const res = await fetch(`/api/service/${currentService}`);
        const data = await res.json();
        
        const detailEl = document.getElementById('service-detail');
        detailEl.classList.remove('hidden');
        
        // Update header
        document.getElementById('detail-service-name').textContent = data.summary.service;
        const badge = document.getElementById('detail-status-badge');
        badge.textContent = data.summary.status;
        badge.className = `status-badge status-${data.summary.status}`;
        
        // Update metrics
        document.getElementById('detail-failure-rate').textContent = data.summary.failure_rate + '%';
        document.getElementById('detail-latency').textContent = data.summary.avg_latency + 's';
        document.getElementById('detail-calls').textContent = data.summary.total_calls;
        document.getElementById('detail-window').textContent = data.summary.window_seconds + 's';
        
        // Update recommendation
        const recBox = document.getElementById('recommendation-box');
        if (data.recommendation) {
            recBox.style.display = 'block';
            document.getElementById('rec-pattern').textContent = data.recommendation.pattern.replace('_', ' ').toUpperCase();
            document.getElementById('rec-reason').textContent = data.recommendation.reason;
        } else {
            recBox.style.display = 'none';
        }
        
        // Update metrics table
        const tbody = document.getElementById('metrics-table-body');
        if (data.metrics.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No metrics available</td></tr>';
        } else {
            tbody.innerHTML = data.metrics.slice(0, 20).map(m => `
                <tr>
                    <td>${formatTimestamp(m.timestamp)}</td>
                    <td>${formatDuration(m.duration)}</td>
                    <td><span class="status-badge ${m.status >= 400 || m.status === 0 ? 'status-critical' : 'status-healthy'}">${m.status || 'ERR'}</span></td>
                    <td>${m.error || '-'}</td>
                </tr>
            `).join('');
        }
        
    } catch (error) {
        console.error('Failed to load service detail:', error);
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
}

function formatDuration(seconds) {
    if (seconds < 1) {
        return (seconds * 1000).toFixed(0) + 'ms';
    }
    return seconds.toFixed(3) + 's';
}

// Time range selector
document.getElementById('time-range').addEventListener('change', (e) => {
    currentWindow = parseInt(e.target.value);
    if (currentService) {
        loadServiceDetail();
    }
});

// Initialize
loadServiceSelector();

// Auto-refresh every 3 seconds if a service is selected
setInterval(() => {
    if (currentService) {
        loadServiceDetail();
    }
}, 3000);
