(function () {
    "use strict";

    // ─── Tunables ──────────────────────────────────────────────────────────────
    const SPOT_COUNT = 8;        // aurora blob count
    const DRIFT      = 0.00020; // blob wander speed
    const SPOT_MAX_A = 0.99;    // near-opaque peak alpha
    const VIG_ALPHA  = 0.0;    // vignette edge darkness
    const TARGET_FPS = 30;      // throttle to 30fps — aurora drift is slow
    const FRAME_MS   = 1000 / TARGET_FPS;
    const GRAIN_FPS  = 12;      // grain shift rate

    // Canvas resolution scale — render at half resolution for huge perf win,
    // the soft blobs look identical at 0.5x
    const CANVAS_SCALE = 0.5;

    // Fully saturated film-burn colours matching the reference image exactly
    // Light mode (dark logo, near-black base): maximum vibrancy
    const DARK_PAL = [
        [255,  50, 120],  // hot pink
        [50,  100, 255],  // electric blue
        [175,  65, 255],  // vivid purple/lavender
        [255, 130,  75],  // vivid peach-orange
        [35,  195, 200],  // cyan-teal
    ];
    // Dark mode (light logo, near-white base): same hues, slightly toned
    const LIGHT_PAL = [
        [220,  40, 100],  // deep rose
        [40,   80, 220],  // strong blue
        [145,  50, 215],  // purple
        [255, 179, 217],  // pastel pink
        [25,  165, 170],  // teal
    ];

    // ─── Helpers ──────────────────────────────────────────────────────────────
    function isDark() {
        return document.body.getAttribute("data-md-color-scheme") === "slate";
    }

    function rng(seed) {
        const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
        return x - Math.floor(x);
    }

    function createSpots(count = SPOT_COUNT) {
        return Array.from({ length: count }, (_, i) => ({
            phaseX:     rng(i * 11 + 1) * Math.PI * 2,
            phaseY:     rng(i * 11 + 2) * Math.PI * 2,
            freqX:      0.40 + rng(i * 11 + 3) * 0.8,
            freqY:      0.40 + rng(i * 11 + 4) * 0.8,
            ampX:       0.12 + rng(i * 11 + 5) * 0.28,
            ampY:       0.12 + rng(i * 11 + 6) * 0.28,
            baseX:      0.05 + rng(i * 11 + 7) * 0.90,
            baseY:      0.05 + rng(i * 11 + 8) * 0.90,
            rx:         0.06 + rng(i * 11 + 9)  * 0.12,
            ry:         0.12 + rng(i * 11 + 10) * 0.23,
            alphaPhase: rng(i * 11 + 12) * Math.PI * 2,
            alphaFreq:  0.18 + rng(i * 11 + 13) * 0.55,
            ci: i % 5,
        }));
    }

    // ─── Pre-baked grain frames ──────────────────────────────────────────────
    // Instead of live random noise generation (very high CPU fill / recalculation),
    // we pre-bake a pool of static noise canvases once at startup.
    // Cycling through a small set of random frames produces the exact same organic
    // shimmering grain effect with absolute ZERO runtime JS compute!
    const GRAIN_SIZE         = 128; // tiny texture, tiled
    const GRAIN_FRAMES_COUNT = 6;   // 6 frames is visually indistinguishable from infinite
    const grainCanvases      = [];
    let currentGrainFrame    = 0;
    let grainTimer           = null;

    function prebakeGrain() {
        if (grainCanvases.length > 0) return; // already pre-baked
        for (let f = 0; f < GRAIN_FRAMES_COUNT; f++) {
            const c = document.createElement("canvas");
            c.width = GRAIN_SIZE;
            c.height = GRAIN_SIZE;
            const ctx = c.getContext("2d");
            const imgData = ctx.createImageData(GRAIN_SIZE, GRAIN_SIZE);
            const d = imgData.data;
            for (let i = 0; i < d.length; i += 4) {
                const v = (Math.random() * 255) | 0;
                d[i] = v; d[i+1] = v; d[i+2] = v; d[i+3] = 255;
            }
            ctx.putImageData(imgData, 0, 0);
            grainCanvases.push(c);
        }
    }

    function rotateGrainFrame() {
        currentGrainFrame = (currentGrainFrame + 1) % GRAIN_FRAMES_COUNT;
    }

    function startGrain() {
        stopGrain();
        prebakeGrain();
        grainTimer = setInterval(rotateGrainFrame, 1000 / GRAIN_FPS);
    }

    function stopGrain() {
        if (grainTimer) { clearInterval(grainTimer); grainTimer = null; }
    }

    // ─── Canvas-based aurora renderer ─────────────────────────────────────────
    // Draws elliptical radial gradient blobs + vignette on a canvas.
    // This replaces the per-frame CSS gradient string building which was
    // the #1 performance killer (style recalc + repaint every frame).

    function drawAurora(ctx, w, h, spots, t, dark) {
        const pal  = dark ? LIGHT_PAL : DARK_PAL;

        // Clear to base color
        if (dark) {
            ctx.fillStyle = "rgba(240,238,225,1)";
        } else {
            ctx.fillStyle = "rgba(4,4,10,1)";
        }
        ctx.fillRect(0, 0, w, h);

        // Draw each aurora blob as an elliptical radial gradient.
        // CSS multiple backgrounds use normal alpha compositing (source-over),
        // NOT screen blend — each gradient paints on top with transparency.

        for (const s of spots) {
            const cx = (s.baseX + Math.sin(t * DRIFT * s.freqX + s.phaseX) * s.ampX) * w;
            const cy = (s.baseY + Math.cos(t * DRIFT * s.freqY + s.phaseY) * s.ampY) * h;
            const rx = s.rx * w;
            const ry = s.ry * h;

            const pulse = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(t * DRIFT * s.alphaFreq * 4 + s.alphaPhase));
            const a = SPOT_MAX_A * pulse;
            const [cr, cg, cb] = pal[s.ci];

            // Use ellipse transform: scale Y, draw circle gradient
            ctx.save();
            ctx.translate(cx, cy);
            ctx.scale(1, ry / rx);

            const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
            grad.addColorStop(0, `rgba(${cr},${cg},${cb},${a})`);
            grad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);

            ctx.fillStyle = grad;
            // fillRect in scaled coords: cover the gradient circle of radius rx.
            // The scale(1, ry/rx) transform handles the elliptical stretching.
            ctx.fillRect(-rx, -rx, rx * 2, rx * 2);
            ctx.restore();
        }

        // Vignette
        const vcR = dark ? 14 : 10;
        const vcG = dark ? 16 : 20;
        const vcB = dark ? 20 : 50;
        const maxDim = Math.max(w, h);
        const vigGrad = ctx.createRadialGradient(w / 2, h / 2, w * 0.14, w / 2, h / 2, maxDim * 0.7);
        vigGrad.addColorStop(0, "transparent");
        vigGrad.addColorStop(1, `rgba(${vcR},${vcG},${vcB},${VIG_ALPHA})`);
        ctx.fillStyle = vigGrad;
        ctx.fillRect(0, 0, w, h);
    }

    // ─── Lifecycle ─────────────────────────────────────────────────────────────
    let animId     = null;
    let entries    = [];
    let observer   = null;
    let isVisible  = true;
    let lastFrameT = 0;

    function stopAll() {
        if (animId) { cancelAnimationFrame(animId); animId = null; }
        stopGrain();
        if (observer) { observer.disconnect(); observer = null; }
        entries = [];
    }

    function initHero() {
        stopAll();

        // Always initialize grain texture
        prebakeGrain();

        // 1. Setup Navbar Logos (always globally visible!)
        const logoWrappers = document.querySelectorAll(".zyx-nav-logo-wrapper");
        logoWrappers.forEach(wrapper => {
            const img = wrapper.querySelector(".zyx-nav-logo-image");
            if (!img) return;

            const canvas = wrapper.querySelector(".zyx-nav-logo-gradient");
            const grainDiv = wrapper.querySelector(".zyx-nav-logo-grain");
            if (!canvas || !grainDiv) return;

            // Apply dynamic mask based on image src
            canvas.style.webkitMaskImage = `url("${img.src}")`;
            canvas.style.maskImage       = `url("${img.src}")`;
            grainDiv.style.webkitMaskImage = `url("${img.src}")`;
            grainDiv.style.maskImage       = `url("${img.src}")`;

            const entry = {
                wrapper,
                canvas,
                grainCanvas: grainDiv,
                ctx: null,
                grainCtx: null,
                spots: createSpots(4), // Simpler: 4 spots for logo
                isLogo: true,
                hoverActive: false,
                leaveTimer: null,
                lastGradW: 0,
                lastGradH: 0,
                lastGrainW: 0,
                lastGrainH: 0
            };

            wrapper.addEventListener("mouseenter", () => {
                if (entry.leaveTimer) {
                    clearTimeout(entry.leaveTimer);
                    entry.leaveTimer = null;
                }
                entry.hoverActive = true;
            });

            wrapper.addEventListener("mouseleave", () => {
                entry.leaveTimer = setTimeout(() => {
                    entry.hoverActive = false;
                }, 500); // 500ms to allow CSS fade-out transition to finish smoothly
            });

            entries.push(entry);
        });

        // 2. Setup Page Hero (only if on homepage)
        const inner = document.querySelector(".md-content__inner");
        let hasHero = false;
        if (inner) {
            const pageIndex = inner.querySelector(".page-index");
            if (pageIndex) {
                // Clean up any leftover wrappers from prior init
                inner.querySelectorAll(".zyx-hero-wrapper").forEach(wrap => {
                    const img = wrap.querySelector(".zyx-hero-image");
                    if (img) {
                        img.className = [...wrap.classList]
                            .filter(c => c !== "zyx-hero-wrapper")
                            .join(" ");
                        wrap.parentNode.insertBefore(img, wrap);
                    }
                    wrap.remove();
                });

                const lightImg = inner.querySelector(".hero-light");
                const darkImg  = inner.querySelector(".hero-dark");
                if (lightImg || darkImg) {
                    hasHero = true;

                    function wrapImg(img) {
                        if (!img) return;

                        const origClass = img.className;

                        // Wrapper div
                        const wrapper = document.createElement("div");
                        wrapper.className = "zyx-hero-wrapper " + origClass;
                        img.parentNode.insertBefore(wrapper, img);
                        img.className = "zyx-hero-image";
                        wrapper.appendChild(img);

                        // Canvas for aurora gradient (replaces the CSS gradient div)
                        const canvas = document.createElement("canvas");
                        canvas.className = "zyx-hero-gradient";
                        canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;" +
                            "-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat;-webkit-mask-position:center;" +
                            "mask-size:contain;mask-repeat:no-repeat;mask-position:center;";
                        canvas.style.webkitMaskImage = `url("${img.src}")`;
                        canvas.style.maskImage       = `url("${img.src}")`;
                        wrapper.appendChild(canvas);

                        // Grain overlay using pre-baked texture (replaces SVG feTurbulence)
                        const grainDiv = document.createElement("canvas");
                        grainDiv.className = "zyx-hero-grain";
                        grainDiv.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;" +
                            "mix-blend-mode:overlay;opacity:0.40;" +
                            "-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat;-webkit-mask-position:center;" +
                            "mask-size:contain;mask-repeat:no-repeat;mask-position:center;";
                        grainDiv.style.webkitMaskImage = `url("${img.src}")`;
                        grainDiv.style.maskImage       = `url("${img.src}")`;
                        wrapper.appendChild(grainDiv);

                        entries.push({
                            wrapper,
                            canvas,
                            grainCanvas: grainDiv,
                            ctx: null,        // lazily initialized
                            grainCtx: null,
                            spots: createSpots(8),
                            isLogo: false,
                            lastGradW: 0,
                            lastGradH: 0,
                            lastGrainW: 0,
                            lastGrainH: 0
                        });
                    }

                    wrapImg(lightImg);
                    wrapImg(darkImg);
                }
            }
        }

        // 3. Setup IntersectionObserver for the hero wrappers
        const visibilityMap = new Map();
        observer = new IntersectionObserver((ioEntries) => {
            for (const e of ioEntries) {
                visibilityMap.set(e.target, e.isIntersecting);
            }
            isVisible = false;
            for (const v of visibilityMap.values()) {
                if (v) { isVisible = true; break; }
            }
        }, { threshold: 0 });

        for (const e of entries) {
            if (!e.isLogo) {
                observer.observe(e.wrapper);
            }
        }

        if (!hasHero) {
            isVisible = false;
        }

        // ─── Animation loop ───────────────────────────────────────────────────
        function loop(t) {
            animId = requestAnimationFrame(loop);

            // Skip frame if not visible AND no active logo is hovered/fading out
            let anyLogoActive = false;
            for (const e of entries) {
                if (e.isLogo && e.hoverActive) {
                    anyLogoActive = true;
                    break;
                }
            }
            if (!isVisible && !anyLogoActive) return;
            if (t - lastFrameT < FRAME_MS) return;
            lastFrameT = t;

            const dark = isDark();

            for (const e of entries) {
                const isLight = e.wrapper.classList.contains("hero-light") || e.wrapper.classList.contains("logo-light");
                const isDarkE = e.wrapper.classList.contains("hero-dark") || e.wrapper.classList.contains("logo-dark");
                if (!((dark && isDarkE) || (!dark && isLight))) continue;

                // For logo, only draw if hovered or in fade-out window
                if (e.isLogo && !e.hoverActive) continue;

                // Decouple resolutions: Gradient is scaled down (50% on hero, 100% on logo)
                // Grain is ALWAYS 100% resolution for perfect, high-fidelity crisp "fuzz"!
                const rect = e.wrapper.getBoundingClientRect();
                const gradScale  = e.isLogo ? 1 : CANVAS_SCALE;
                const grainScale = 1;

                const dwGrad  = Math.round(rect.width  * gradScale);
                const dhGrad  = Math.round(rect.height * gradScale);
                const dwGrain = Math.round(rect.width  * grainScale);
                const dhGrain = Math.round(rect.height * grainScale);

                if (dwGrad < 1 || dhGrad < 1 || dwGrain < 1 || dhGrain < 1) continue;

                // Resize gradient canvas only when dimensions change
                if (e.lastGradW !== dwGrad || e.lastGradH !== dhGrad) {
                    e.canvas.width  = dwGrad;
                    e.canvas.height = dhGrad;
                    e.ctx = e.canvas.getContext("2d");
                    e.lastGradW = dwGrad;
                    e.lastGradH = dhGrad;
                }

                // Resize grain canvas only when dimensions change
                if (e.lastGrainW !== dwGrain || e.lastGrainH !== dhGrain) {
                    e.grainCanvas.width  = dwGrain;
                    e.grainCanvas.height = dhGrain;
                    e.grainCtx = e.grainCanvas.getContext("2d");
                    e.lastGrainW = dwGrain;
                    e.lastGrainH = dhGrain;
                }

                // Draw aurora on gradient canvas
                drawAurora(e.ctx, dwGrad, dhGrad, e.spots, t, dark);

                // Draw grain on high-res grain canvas using a pre-baked static frame pattern
                if (grainCanvases.length > 0 && e.grainCtx) {
                    e.grainCtx.clearRect(0, 0, dwGrain, dhGrain);
                    const activeGrainCanvas = grainCanvases[currentGrainFrame];
                    const pattern = e.grainCtx.createPattern(activeGrainCanvas, "repeat");
                    if (pattern) {
                        e.grainCtx.fillStyle = pattern;
                        e.grainCtx.fillRect(0, 0, dwGrain, dhGrain);
                    }
                }
            }
        }

        animId = requestAnimationFrame(loop);
        startGrain();
    }

    // Theme change observer
    new MutationObserver(() => {
        // rAF loop auto-adapts next frame via isDark()
    }).observe(document.body, {
        attributes: true,
        attributeFilter: ["data-md-color-scheme"],
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHero);
    } else {
        initHero();
    }

    document.addEventListener("DOMContentSwitch", initHero);
})();
