/**
 * AutoHeal-Py — Three.js 3D Service Topology Visualization (v2)
 *
 * Fixes:
 *  - Labels are bright white and large enough to read
 *  - Service node labels FOLLOW their node as it orbits
 *  - Agent label anchors to the agent sphere
 *  - Traffic particles travel from agent → service node
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js';

const COLORS = {
    healthy:         0x10b981,
    degraded:        0xf59e0b,
    critical:        0xef4444,
    slow:            0xa855f7,
    unknown:         0x6b7280,
    agent:           0x3b82f6,
    edge:            0x334155,
    retry:           0x3b82f6,
    circuit_breaker: 0xf59e0b,
    timeout:         0xa855f7,
};

// ── Module state ──────────────────────────────────────────────────────────────
let _scene, _camera, _renderer, _animId;
let _agentMesh, _agentGlow, _agentLabel;
let _serviceNodes = [];
let _tick = 0;

// ── Init ──────────────────────────────────────────────────────────────────────
export function initTopology(canvas) {
    const W = canvas.offsetWidth || 800;
    const H = canvas.offsetHeight || 340;

    _renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _renderer.setSize(W, H);
    _renderer.setClearColor(0x000000, 0);

    _scene = new THREE.Scene();

    _camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 200);
    _camera.position.set(0, 6, 20);
    _camera.lookAt(0, 0, 0);

    // Lights
    _scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dir = new THREE.DirectionalLight(0xffffff, 1.4);
    dir.position.set(5, 10, 8);
    _scene.add(dir);

    // Agent node (center)
    _agentMesh = _makeSphere(0.9, COLORS.agent, 1.0);
    _agentGlow = _makeGlowSprite(COLORS.agent, 4.0);
    _agentLabel = _makeLabel('AutoHeal Agent', '#94d9ff', 280, 60, 24);
    _agentLabel.scale.set(4.5, 1.0, 1);

    _scene.add(_agentMesh);
    _scene.add(_agentGlow);
    _scene.add(_agentLabel);

    // Resize
    window.addEventListener('resize', () => {
        const W = canvas.offsetWidth, H = canvas.offsetHeight;
        _camera.aspect = W / H;
        _camera.updateProjectionMatrix();
        _renderer.setSize(W, H);
    });

    _animate();
}

// ── Public: update services ───────────────────────────────────────────────────
export function updateTopology(services) {
    // Add new nodes
    services.forEach((svc, i) => {
        if (!_serviceNodes[i]) {
            _serviceNodes[i] = _createServiceNode(svc, i, services.length);
        }
        _updateServiceNode(_serviceNodes[i], svc);
    });

    // Remove extra nodes
    while (_serviceNodes.length > services.length) {
        _removeNode(_serviceNodes.pop());
    }
}

// ── Create a service node object ──────────────────────────────────────────────
function _createServiceNode(svc, idx, total) {
    const angle  = (idx / Math.max(total, 1)) * Math.PI * 2;
    const radius = 5.5;
    const color  = _stateColor(svc.status, svc.active_pattern);

    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius;

    // Sphere
    const mesh  = _makeSphere(0.65, color, 0.95);
    mesh.position.set(x, 0, z);

    // Glow
    const glow  = _makeGlowSprite(color, 2.5);
    glow.position.set(x, 0, z);

    // Edge (connection beam from agent to node)
    const edge  = _makeEdge(x, z);

    // Traffic particles (3 dots per edge)
    const particles = [0, 1, 2].map(pi => _makeParticle(color, pi));

    // Shield rings (hidden until a pattern is active)
    const shield = _makeShieldGroup(color);
    shield.position.set(x, 0, z);
    shield.visible = false;

    // ** Label that travels with the node **
    const shortName = _shortenLabel(svc.service);
    const label = _makeLabel(shortName, '#94d9ff', 320, 64, 22);
    label.scale.set(4.0, 0.9, 1);
    label.position.set(x, -1.5, z);

    _scene.add(mesh);
    _scene.add(glow);
    _scene.add(edge);
    particles.forEach(p => _scene.add(p));
    _scene.add(shield);
    _scene.add(label);

    return {
        mesh, glow, edge, particles, shield, label,
        angle, radius,
        currentStatus:  svc.status,
        currentPattern: svc.active_pattern,
        service:        svc.service,
    };
}

// ── Update an existing node to reflect new API data ───────────────────────────
function _updateServiceNode(node, svc) {
    const color      = _stateColor(svc.status, svc.active_pattern);
    const hasPattern = !!svc.active_pattern;

    node.mesh.material.color.setHex(color);
    node.mesh.material.emissive.setHex(color);
    node.glow.material.color.setHex(color);

    // Shield
    node.shield.visible = hasPattern;
    if (hasPattern) {
        const pc = COLORS[svc.active_pattern] ?? color;
        node.shield.children.forEach(c => c.material.color.setHex(pc));
    }

    // Particle colors
    node.particles.forEach(p => p.material.color.setHex(color));

    node.currentStatus  = svc.status;
    node.currentPattern = svc.active_pattern;

    // Refresh label text if service name changed
    const shortName = _shortenLabel(svc.service);
    // Label sprite is pre-made — we don't regenerate it every frame
}

function _removeNode(node) {
    const objects = [node.mesh, node.glow, node.edge, node.shield, node.label, ...node.particles];
    objects.forEach(o => {
        _scene.remove(o);
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
            if (o.material.map) o.material.map.dispose();
            o.material.dispose();
        }
    });
}

// ── Animation loop ────────────────────────────────────────────────────────────
function _animate() {
    _animId = requestAnimationFrame(_animate);
    _tick++;
    const t = _tick * 0.01;

    // Agent node: pulse
    if (_agentMesh) {
        const s = 1 + 0.09 * Math.sin(t * 1.5);
        _agentMesh.scale.setScalar(s);
        _agentGlow.scale.setScalar(s * 1.6);
        // Agent label just below the sphere
        _agentLabel.position.set(0, -1.6, 0);
    }

    // Service nodes: orbit + label follows
    _serviceNodes.forEach((node, i) => {
        const orbAngle = node.angle + t * 0.10;   // slow orbit
        const x = Math.cos(orbAngle) * node.radius;
        const y = Math.sin(t * 2 + i) * 0.18;      // gentle bob
        const z = Math.sin(orbAngle) * node.radius;

        node.mesh.position.set(x, y, z);
        node.glow.position.set(x, y, z);

        // *** Label follows node ***
        node.label.position.set(x, y - 1.4, z);

        // Pulse scale based on status
        const pf = node.currentStatus === 'critical' ? 0.18
                 : node.currentStatus === 'degraded'  ? 0.12 : 0.06;
        node.mesh.scale.setScalar(1 + pf * Math.sin(t * 3 + i));

        // Shield orbits around node
        if (node.shield.visible) {
            node.shield.position.set(x, y, z);
            node.shield.rotation.z = t * 1.5;
            node.shield.rotation.x = Math.sin(t * 0.5) * 0.3;
            node.shield.scale.setScalar(1 + 0.08 * Math.sin(t * 2));
        }

        // Update edge endpoint to follow orbiting node
        const pos = node.edge.geometry.attributes.position;
        pos.setXYZ(1, x, y, z);
        pos.needsUpdate = true;

        // Traffic particles travel from origin → node
        node.particles.forEach((p, pi) => {
            const phase = ((t * 0.18 + pi * 0.33)) % 1;
            p.position.set(phase * x, phase * y, phase * z);
        });
    });

    // Camera very gentle drift
    _camera.position.x = Math.sin(t * 0.04) * 2.5;
    _camera.position.y = 6 + Math.sin(t * 0.025) * 1.2;
    _camera.lookAt(0, 0, 0);

    _renderer.render(_scene, _camera);
}

// ── Destroy ───────────────────────────────────────────────────────────────────
export function destroyTopology() {
    if (_animId) cancelAnimationFrame(_animId);
    _renderer?.dispose();
    _serviceNodes.forEach(_removeNode);
    _serviceNodes = [];
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function _stateColor(status, pattern) {
    if (pattern) return COLORS[pattern] ?? COLORS[status] ?? COLORS.unknown;
    return COLORS[status] ?? COLORS.unknown;
}

function _makeSphere(r, color, opacity) {
    const geo = new THREE.SphereGeometry(r, 32, 32);
    const mat = new THREE.MeshStandardMaterial({
        color, emissive: color, emissiveIntensity: 0.18,
        transparent: true, opacity,
    });
    return new THREE.Mesh(geo, mat);
}

function _makeGlowSprite(color, size) {
    const cv  = document.createElement('canvas');
    cv.width  = cv.height = 128;
    const ctx = cv.getContext('2d');
    const g   = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    const rgb = _hexRgb(color);
    g.addColorStop(0,   `rgba(${rgb},0.55)`);
    g.addColorStop(0.4, `rgba(${rgb},0.20)`);
    g.addColorStop(1,   `rgba(${rgb},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    const mat = new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(cv),
        transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
    });
    const s = new THREE.Sprite(mat);
    s.scale.setScalar(size);
    return s;
}

/**
 * Create a bright, readable label sprite.
 * @param {string} text   - text to display
 * @param {string} color  - CSS color for text (e.g. '#ffffff')
 * @param {number} cw     - canvas width
 * @param {number} ch     - canvas height
 * @param {number} fs     - font size (px)
 */
function _makeLabel(text, color, cw, ch, fs) {
    const cv  = document.createElement('canvas');
    cv.width  = cw; cv.height = ch;
    const ctx = cv.getContext('2d');

    // Pill background for contrast
    ctx.fillStyle = 'rgba(5,12,28,0.75)';
    const pad = 8, r = 10;
    _roundRect(ctx, pad, ch/2 - fs/2 - 6, cw - pad*2, fs + 12, r);
    ctx.fill();

    // Text
    ctx.fillStyle  = color;
    ctx.font       = `bold ${fs}px Inter, system-ui, sans-serif`;
    ctx.textAlign  = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, cw / 2, ch / 2);

    const mat = new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(cv),
        transparent: true, depthWrite: false,
    });
    return new THREE.Sprite(mat);
}

function _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

function _makeEdge(tx, tz) {
    const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(tx, 0, tz),
    ]);
    const mat = new THREE.LineBasicMaterial({
        color: COLORS.edge, transparent: true, opacity: 0.4,
    });
    return new THREE.Line(geo, mat);
}

function _makeParticle(color, idx) {
    const geo = new THREE.SphereGeometry(0.07, 8, 8);
    const mat = new THREE.MeshBasicMaterial({
        color, transparent: true, opacity: 0.9 - idx * 0.15,
    });
    return new THREE.Mesh(geo, mat);
}

function _makeShieldGroup(color) {
    const group = new THREE.Group();
    for (let i = 0; i < 3; i++) {
        const geo = new THREE.TorusGeometry(1.05 + i * 0.22, 0.028, 8, 64);
        const mat = new THREE.MeshBasicMaterial({
            color, transparent: true, opacity: 0.55 - i * 0.12,
        });
        const t = new THREE.Mesh(geo, mat);
        t.rotation.x = Math.PI / 2 + i * 0.4;
        group.add(t);
    }
    return group;
}

function _shortenLabel(name) {
    // "localhost:8001" → "localhost:8001", very long names get trimmed
    return name.length > 20 ? name.slice(0, 18) + '…' : name;
}

function _hexRgb(hex) {
    return `${(hex >> 16) & 255},${(hex >> 8) & 255},${hex & 255}`;
}
