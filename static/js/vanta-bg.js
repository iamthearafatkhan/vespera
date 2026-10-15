// static/js/vanta-bg.js
// Vespera — Vanta DOTS background, theme-aware.
//
// Vanta reads colors once at init, so when the user toggles theme we destroy
// and re-create the effect. That's cheap (~50ms) and gives us a clean
// transition because the canvas fades via CSS opacity.

(function () {
    // ---- guard: no WebGL, no Vanta, or reduced-motion → skip entirely ----
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isSmallScreen = window.innerWidth < 480;
    if (prefersReduced || typeof window.VANTA === 'undefined') {
        return;
    }

    const el = document.getElementById('vanta-bg');
    if (!el) return;

    let effect = null;

    // Read theme colors from our CSS variables so the effect matches the palette
    function readTheme() {
        const css = getComputedStyle(document.documentElement);
        const isDark = document.documentElement.classList.contains('dark');
        return {
            accent: css.getPropertyValue('--ves-accent').trim() || '#58a4b0',
            accent2: css.getPropertyValue('--ves-accent-2').trim() || '#a9bcd0',
            // canvas background — transparent so the CSS mesh behind shows through
            bg: isDark ? '#1b1b1e' : '#f4f5f8',
            isDark: isDark,
        };
    }

    function start() {
        const t = readTheme();
        effect = window.VANTA.DOTS({
            el: '#vanta-bg',
            mouseControls: true,
            touchControls: true,
            gyroControls: false,
            minHeight: 200,
            minWidth: 200,

            // Scale — smaller on mobile to save battery
            scale: 1.0,
            scaleMobile: 0.55,

            // Colors straight from our palette
            color: t.accent,       // dot color (pacific blue in both themes)
            color2: t.accent2,      // line color (powder blue)

            // Make the canvas transparent so the CSS mesh blurs through underneath
            backgroundColor: t.bg,
            backgroundAlpha: 0,

            // Density + size — tuned to feel "premium", not "screen saver"
            size: 2.2,
            spacing: 55,

            // Constellation lines on, but sparse
            showLines: true,
        });

        // Fade in — prevents a hard pop on first load
        el.style.opacity = '0';
        el.style.transition = 'opacity .8s ease';
        requestAnimationFrame(() => { el.style.opacity = '1'; });
    }

    function stop() {
        if (effect) {
            effect.destroy();
            effect = null;
        }
    }

    // ---- go ----
    start();

    // Re-init when theme class flips on <html>
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.attributeName === 'class') {
                stop();
                start();
                break;
            }
        }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    // Pause the animation when the tab is hidden — saves CPU on laptops
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stop();
        } else {
            start();
        }
    });
})();