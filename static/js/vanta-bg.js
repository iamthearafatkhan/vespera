// static/js/vanta-bg.js
// Vespera — Vanta NET background, theme-aware.
// NET renders its own opaque canvas (needed for its blending math), so we
// fade it in via CSS opacity and skip the mesh layer.

(function () {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced || typeof window.VANTA === 'undefined') return;

    const el = document.getElementById('vanta-bg');
    if (!el) return;

    const isSmallScreen = window.innerWidth < 640;
    let effect = null;

    function readTheme() {
        const isDark = document.documentElement.classList.contains('dark');
        return {
            // NET likes its own solid backdrop — we use our theme bg colors
            bg: isDark ? '#1b1b1e' : '#f4f5f8',
            // dots stay pacific blue in both themes
            color: '#58a4b0',
            // slight brightness nudge so dots pop on light bg
            isDark,
        };
    }

    function start() {
        const t = readTheme();
        effect = window.VANTA.NET({
            el: '#vanta-bg',
            mouseControls: true,
            touchControls: true,
            gyroControls: false,
            minHeight: 200,
            minWidth: 200,

            // scale down on mobile for battery
            scale: 1.0,
            scaleMobile: 0.6,

            // colors
            color: t.color,
            backgroundColor: t.bg,

            // density + spread — tuned to feel calm, not busy
            points: isSmallScreen ? 6 : 9,   // grid side length (points²)
            maxDistance: 22,                       // line length threshold
            spacing: 18,                       // distance between grid cells
            showDots: true,                     // little glowing nodes
        });

        // fade the whole canvas in — prevents a hard pop on first paint
        el.style.opacity = '0';
        el.style.transition = 'opacity .9s ease';
        requestAnimationFrame(() => { el.style.opacity = '1'; });
    }

    function stop() {
        if (effect) { effect.destroy(); effect = null; }
    }

    start();

    // re-init when theme flips
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.attributeName === 'class') { stop(); start(); break; }
        }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    // pause when tab is hidden — saves CPU
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stop();
        else start();
    });
})();