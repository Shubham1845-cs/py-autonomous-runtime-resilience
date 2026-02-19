// main.js — shared utilities
function formatDuration(seconds) {
    return seconds < 1 ? (seconds * 1000).toFixed(0) + 'ms' : seconds.toFixed(3) + 's';
}
function formatTimestamp(ts) {
    return new Date(ts * 1000).toLocaleTimeString();
}

// Particle background
(function spawnParticles() {
    const el = document.getElementById('particles');
    if (!el) return;
    for (let i = 0; i < 35; i++) {
        const p = document.createElement('div');
        const size = Math.random() * 3 + 1;
        p.style.cssText = `
            position:absolute;
            width:${size}px; height:${size}px;
            border-radius:50%;
            background:rgba(79,142,247,${Math.random() * 0.4 + 0.1});
            left:${Math.random() * 100}%;
            top:${Math.random() * 100}%;
            animation:particleDrift ${10 + Math.random() * 15}s linear ${Math.random() * 10}s infinite;
        `;
        el.appendChild(p);
    }

    const style = document.createElement('style');
    style.textContent = `
        @keyframes particleDrift {
            0%   { transform:translateY(0) translateX(0); opacity:0; }
            10%  { opacity:1; }
            90%  { opacity:.5; }
            100% { transform:translateY(-120vh) translateX(${Math.random()>0.5?'':'-'}${Math.random()*60}px); opacity:0; }
        }
    `;
    document.head.appendChild(style);
})();
