/**
 * AgileFlow Animated Atmospheric Background System
 * Custom theme-tailored animations for all 5 themes in both Light and Dark mode:
 *
 * 1. GAME THEME:
 *    - Dark:  Retro floating pixels, synthwave stars & tiny 8-bit pixel characters (invaders, ghosts, coins, slimes, hearts)
 *    - Light: Pastel arcade particles with hopping pixel slimes, floating coins, pixel stars & hearts
 *
 * 2. FOREST THEME:
 *    - Dark:  Bioluminescent fireflies with realistic breathing glow wandering in organic curved paths
 *    - Light: Flocks of birds with animated flapping wings soaring across the sky, with drifting sunlit leaves
 *
 * 3. CITY THEME:
 *    - Dark:  Night skyline starfield with blinking stars and dramatic diagonal shooting stars / meteors
 *    - Light: Soft, stylized fluffy cumulus clouds drifting across the daylight sky with gentle atmospheric motes
 *
 * 4. ICE THEME:
 *    - Dark:  Polar winter snowfall with intricate 6-point glowing ice crystal snowflakes and wind sway
 *    - Light: Crisp, gentle daytime snowfall drifting down with cold breeze oscillation
 *
 * 5. ZARA LARSSON THEME:
 *    - Dark:  Concert arena stage spotlight beams panning across the sky, floating glowing musical notes (♪, ♫, ♩) & stardust
 *    - Light: Sunburst stage glitter and warm sunset floating musical notes (♪, ♫) drifting in a golden glow
 */

(function () {
    'use strict';

    // 8x8 Pixel Art Bitmaps for Game Theme
    const PIXEL_SPRITES = {
        invader: [
            [0,0,1,0,0,1,0,0],
            [0,0,0,1,1,0,0,0],
            [0,0,1,1,1,1,0,0],
            [0,1,1,0,1,1,0,1],
            [1,1,1,1,1,1,1,1],
            [1,0,1,1,1,1,0,1],
            [1,0,1,0,0,1,0,1],
            [0,0,0,1,1,0,0,0]
        ],
        ghost: [
            [0,0,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,0],
            [1,1,0,1,1,0,1,1],
            [1,1,0,1,1,0,1,1],
            [1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1],
            [1,0,1,1,1,1,0,1],
            [1,0,0,1,1,0,0,1]
        ],
        slime: [
            [0,0,0,1,1,0,0,0],
            [0,0,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,0],
            [1,1,0,1,1,0,1,1],
            [1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1],
            [0,1,1,1,1,1,1,0]
        ],
        coin: [
            [0,0,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,0],
            [1,1,0,0,0,0,1,1],
            [1,1,0,1,1,0,1,1],
            [1,1,0,1,1,0,1,1],
            [1,1,0,0,0,0,1,1],
            [0,1,1,1,1,1,1,0],
            [0,0,1,1,1,1,0,0]
        ],
        heart: [
            [0,1,1,0,0,1,1,0],
            [1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1],
            [0,1,1,1,1,1,1,0],
            [0,0,1,1,1,1,0,0],
            [0,0,0,1,1,0,0,0],
            [0,0,0,0,0,0,0,0]
        ]
    };

    const SPRITE_NAMES = Object.keys(PIXEL_SPRITES);

    class AnimatedBackgroundEngine {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.theme = 'zara_larsson';
            this.mode = 'light';
            this.width = 0;
            this.height = 0;
            this.dpr = 1;
            this.animId = null;
            this.enabled = true;
            this.reducedMotion = false;
            this.lastFrameTime = performance.now();

            // Theme-specific state stores
            this.particles = [];
            this.shootingStars = [];
            this.clouds = [];
            this.birds = [];
            this.pixelCharacters = [];
            this.spotlights = [];

            // Mouse interactivity
            this.mouse = { x: -1000, y: -1000, active: false };
            this.mouseTimeout = null;

            // Timer for shooting stars
            this.nextShootingStarTime = 0;
        }

        init() {
            this.canvas = document.getElementById('themeAnimatedCanvas');
            if (!this.canvas) return;

            this.ctx = this.canvas.getContext('2d', { alpha: true });
            if (!this.ctx) return;

            // Check reduced motion preference
            const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
            this.reducedMotion = motionQuery.matches;
            motionQuery.addEventListener('change', (e) => {
                this.reducedMotion = e.matches;
                this.initCurrentThemeState();
            });

            // Check user toggle preference in localStorage
            const storedPref = localStorage.getItem('agileflow_bg_animated');
            if (storedPref !== null) {
                this.enabled = storedPref === 'true';
            }

            // Detect current theme and mode from body
            const body = document.body;
            this.theme = body.getAttribute('data-theme') || 'zara_larsson';
            this.mode = body.getAttribute('data-mode') || 'light';

            // Set size
            this.handleResize();
            window.addEventListener('resize', () => this.handleResize(), { passive: true });

            // Interactive ambient mouse motion
            window.addEventListener('pointermove', (e) => {
                this.mouse.x = e.clientX;
                this.mouse.y = e.clientY;
                this.mouse.active = true;
                clearTimeout(this.mouseTimeout);
                this.mouseTimeout = setTimeout(() => {
                    this.mouse.active = false;
                }, 2000);
            }, { passive: true });

            // Tab visibility change
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    this.stop();
                } else if (this.enabled) {
                    this.start();
                }
            });

            // Wire up toggle switch
            this.wireToggleSwitch();

            // Apply enabled state to body class
            if (!this.enabled) {
                document.body.classList.add('theme-animation-disabled');
            } else {
                document.body.classList.remove('theme-animation-disabled');
                this.initCurrentThemeState();
                this.start();
            }
        }

        wireToggleSwitch() {
            const toggle = document.getElementById('themeAnimationToggle');
            if (toggle) {
                toggle.checked = this.enabled;
                toggle.onchange = (e) => {
                    this.toggle(e.target.checked);
                };
            }
        }

        toggle(enable) {
            this.enabled = !!enable;
            localStorage.setItem('agileflow_bg_animated', String(this.enabled));

            const toggle = document.getElementById('themeAnimationToggle');
            if (toggle && toggle.checked !== this.enabled) {
                toggle.checked = this.enabled;
            }

            if (this.enabled) {
                document.body.classList.remove('theme-animation-disabled');
                this.initCurrentThemeState();
                this.start();
            } else {
                document.body.classList.add('theme-animation-disabled');
                this.stop();
                if (this.ctx && this.width && this.height) {
                    this.ctx.clearRect(0, 0, this.width, this.height);
                }
            }
        }

        setTheme(theme, mode) {
            let changed = false;
            if (theme && theme !== this.theme) {
                this.theme = theme;
                changed = true;
            }
            if (mode && mode !== this.mode) {
                this.mode = mode;
                changed = true;
            }
            if (changed) {
                this.initCurrentThemeState();
            }
        }

        handleResize() {
            if (!this.canvas) return;
            this.dpr = Math.min(window.devicePixelRatio || 1, 2);
            this.width = window.innerWidth;
            this.height = window.innerHeight;

            this.canvas.width = this.width * this.dpr;
            this.canvas.height = this.height * this.dpr;
            this.canvas.style.width = this.width + 'px';
            this.canvas.style.height = this.height + 'px';

            this.ctx.scale(this.dpr, this.dpr);
            this.initCurrentThemeState();
        }

        // =========================================================================
        // THEME STATE INITIALIZERS
        // =========================================================================

        initCurrentThemeState() {
            if (!this.width || !this.height) return;
            const theme = this.theme;
            const mode = this.mode;

            this.particles = [];
            this.shootingStars = [];
            this.clouds = [];
            this.birds = [];
            this.pixelCharacters = [];
            this.spotlights = [];

            if (theme === 'game') {
                this.initGameTheme(mode);
            } else if (theme === 'forest') {
                this.initForestTheme(mode);
            } else if (theme === 'city') {
                this.initCityTheme(mode);
            } else if (theme === 'ice') {
                this.initIceTheme(mode);
            } else {
                // Zara Larsson
                this.initZaraLarssonTheme(mode);
            }
        }

        // 1. GAME THEME: Pixel Sprites & Retro Pixels
        initGameTheme(mode) {
            const isDark = mode === 'dark';
            const charCount = isDark ? 6 : 5;
            const pixelColorsDark = [
                '#c084fc', '#f43f5e', '#38bdf8', '#fbbf24', '#4ade80'
            ];
            const pixelColorsLight = [
                'rgba(168, 85, 247, 0.75)', 'rgba(244, 63, 94, 0.75)', 'rgba(14, 165, 233, 0.75)', 'rgba(245, 158, 11, 0.75)'
            ];
            const colors = isDark ? pixelColorsDark : pixelColorsLight;

            // Spawn Pixel Characters
            for (let i = 0; i < charCount; i++) {
                const spriteName = SPRITE_NAMES[i % SPRITE_NAMES.length];
                const pixelSize = isDark ? (Math.random() > 0.5 ? 3 : 4) : (Math.random() > 0.5 ? 3 : 4);
                const color = colors[i % colors.length];

                this.pixelCharacters.push({
                    sprite: PIXEL_SPRITES[spriteName],
                    name: spriteName,
                    x: Math.random() * this.width,
                    y: Math.random() * this.height,
                    vx: (Math.random() > 0.5 ? 1 : -1) * (0.35 + Math.random() * 0.45),
                    vy: (Math.random() - 0.5) * 0.3,
                    pixelSize,
                    color,
                    glowColor: color,
                    glowBlur: isDark ? 8 : 4,
                    bouncePhase: Math.random() * Math.PI * 2,
                    bounceSpeed: 0.04 + Math.random() * 0.03
                });
            }

            // Floating background retro pixels
            const count = isDark ? 36 : 28;
            for (let i = 0; i < count; i++) {
                const size = Math.floor(Math.random() * 3 + 2); // 2px, 3px, 4px square pixels
                const color = colors[Math.floor(Math.random() * colors.length)];
                this.particles.push({
                    x: Math.random() * this.width,
                    y: Math.random() * this.height,
                    size,
                    color,
                    vy: -(0.3 + Math.random() * 0.4),
                    vx: (Math.random() - 0.5) * 0.25,
                    pulse: Math.random() * Math.PI * 2,
                    pulseSpeed: 0.03 + Math.random() * 0.03,
                    isDiamond: Math.random() > 0.6,
                    glowColor: color,
                    glowBlur: isDark ? 6 : 2
                });
            }
        }

        // 2. FOREST THEME: Night Fireflies / Day Birds
        initForestTheme(mode) {
            const isDark = mode === 'dark';

            if (isDark) {
                // Fireflies wandering in 2D curved paths with warm golden breathing glow
                const fireflyColors = [
                    '#f59e0b', '#fbbf24', '#fde047', '#facc15', '#a3e635'
                ];
                const count = this.reducedMotion ? 16 : 42;
                for (let i = 0; i < count; i++) {
                    const color = fireflyColors[Math.floor(Math.random() * fireflyColors.length)];
                    this.particles.push({
                        x: Math.random() * this.width,
                        y: Math.random() * this.height,
                        size: 2.2 + Math.random() * 2.8,
                        color,
                        glowColor: color,
                        glowBlur: 16,
                        vx: (Math.random() - 0.5) * 0.5,
                        vy: (Math.random() - 0.5) * 0.5,
                        angle: Math.random() * Math.PI * 2,
                        angleSpeed: (Math.random() - 0.5) * 0.04,
                        pulse: Math.random() * Math.PI * 2,
                        pulseSpeed: 0.015 + Math.random() * 0.025
                    });
                }
            } else {
                // Daytime: Birds flying across sky + gentle leaves drifting
                const birdCount = this.reducedMotion ? 3 : 6;
                for (let i = 0; i < birdCount; i++) {
                    const scale = 0.75 + Math.random() * 0.65;
                    this.birds.push({
                        x: Math.random() * this.width,
                        y: 40 + Math.random() * (this.height * 0.45),
                        vx: 1.1 + Math.random() * 0.8,
                        vy: (Math.random() - 0.5) * 0.15,
                        scale,
                        wingPhase: Math.random() * Math.PI * 2,
                        wingSpeed: 0.08 + Math.random() * 0.04,
                        color: 'rgba(20, 83, 45, 0.55)'
                    });
                }

                // Drifting sunlit organic leaves/pollen
                const leafColors = [
                    'rgba(34, 197, 94, 0.45)',
                    'rgba(217, 119, 6, 0.40)',
                    'rgba(234, 179, 8, 0.40)',
                    'rgba(132, 204, 22, 0.45)'
                ];
                const leafCount = 20;
                for (let i = 0; i < leafCount; i++) {
                    this.particles.push({
                        x: Math.random() * this.width,
                        y: Math.random() * this.height,
                        size: 2.0 + Math.random() * 2.2,
                        color: leafColors[Math.floor(Math.random() * leafColors.length)],
                        vy: 0.35 + Math.random() * 0.3,
                        vx: 0.2 + Math.random() * 0.3,
                        sway: Math.random() * Math.PI * 2,
                        swaySpeed: 0.02 + Math.random() * 0.02
                    });
                }
            }
        }

        // 3. CITY THEME: Night Twinkling Stars & Shooting Stars / Day Clouds
        initCityTheme(mode) {
            const isDark = mode === 'dark';

            if (isDark) {
                // Night: Twinkling Skyline Stars
                const starCount = this.reducedMotion ? 25 : 65;
                for (let i = 0; i < starCount; i++) {
                    this.particles.push({
                        x: Math.random() * this.width,
                        y: Math.random() * (this.height * 0.75), // concentrated in sky
                        size: 1.2 + Math.random() * 2.0,
                        color: Math.random() > 0.4 ? '#ffffff' : (Math.random() > 0.5 ? '#38bdf8' : '#c084fc'),
                        twinkle: Math.random() * Math.PI * 2,
                        twinkleSpeed: 0.02 + Math.random() * 0.04,
                        isCross: Math.random() > 0.75
                    });
                }
                this.nextShootingStarTime = performance.now() + 1500;
            } else {
                // Day: Fluffy stylized drifting clouds
                const cloudCount = this.reducedMotion ? 3 : 5;
                for (let i = 0; i < cloudCount; i++) {
                    const scale = 0.7 + Math.random() * 0.7;
                    const baseRadius = 28 * scale;
                    // Generate 5-6 overlapping puffs
                    const puffs = [
                        { dx: 0, dy: 0, r: baseRadius * 1.1 },
                        { dx: baseRadius * 0.9, dy: -baseRadius * 0.2, r: baseRadius * 0.95 },
                        { dx: -baseRadius * 0.9, dy: -baseRadius * 0.1, r: baseRadius * 0.9 },
                        { dx: baseRadius * 1.7, dy: baseRadius * 0.15, r: baseRadius * 0.75 },
                        { dx: -baseRadius * 1.6, dy: baseRadius * 0.2, r: baseRadius * 0.7 }
                    ];

                    this.clouds.push({
                        x: Math.random() * (this.width + 300) - 150,
                        y: 50 + Math.random() * (this.height * 0.38),
                        vx: 0.18 + Math.random() * 0.22,
                        scale,
                        puffs,
                        color: 'rgba(255, 255, 255, 0.42)'
                    });
                }

                // Sunlight dust motes
                for (let i = 0; i < 22; i++) {
                    this.particles.push({
                        x: Math.random() * this.width,
                        y: Math.random() * this.height,
                        size: 1.5 + Math.random() * 2.0,
                        color: 'rgba(56, 189, 248, 0.35)',
                        vy: -(0.2 + Math.random() * 0.25),
                        vx: 0.15 + Math.random() * 0.2,
                        pulse: Math.random() * Math.PI * 2
                    });
                }
            }
        }

        // 4. ICE THEME: Snowfall & Ice Crystals
        initIceTheme(mode) {
            const isDark = mode === 'dark';
            const count = this.reducedMotion ? 25 : 60;
            const colorsDark = ['#38bdf8', '#7dd3fc', '#bae6fd', '#ffffff'];
            const colorsLight = ['rgba(56, 189, 248, 0.45)', 'rgba(186, 230, 253, 0.65)', 'rgba(255, 255, 255, 0.8)'];
            const colors = isDark ? colorsDark : colorsLight;

            for (let i = 0; i < count; i++) {
                const isSpecial = Math.random() > 0.75;
                const size = isSpecial ? (3.5 + Math.random() * 2.5) : (1.6 + Math.random() * 3.0);
                const color = colors[Math.floor(Math.random() * colors.length)];

                this.particles.push({
                    x: Math.random() * this.width,
                    y: Math.random() * this.height,
                    size,
                    color,
                    vy: 0.4 + Math.random() * 0.55,
                    sway: Math.random() * Math.PI * 2,
                    swaySpeed: 0.015 + Math.random() * 0.025,
                    isCrystal: isSpecial,
                    rot: Math.random() * Math.PI * 2,
                    rotSpeed: (Math.random() - 0.5) * 0.03,
                    glowColor: isDark ? '#38bdf8' : 'rgba(56, 189, 248, 0.3)',
                    glowBlur: isDark ? 8 : 4
                });
            }
        }

        // 5. ZARA LARSSON THEME: Concert Spotlights, Floating Musical Notes & Stardust
        initZaraLarssonTheme(mode) {
            const isDark = mode === 'dark';

            // Panning Stage Spotlights in dark mode
            if (isDark) {
                this.spotlights = [
                    {
                        originX: this.width * 0.25,
                        originY: this.height + 40,
                        angle: -Math.PI / 4,
                        minAngle: -Math.PI / 2.8,
                        maxAngle: -Math.PI / 5,
                        speed: 0.005,
                        width: 140,
                        color: 'rgba(217, 70, 239, 0.08)'
                    },
                    {
                        originX: this.width * 0.75,
                        originY: this.height + 40,
                        angle: -Math.PI * 0.75,
                        minAngle: -Math.PI * 0.82,
                        maxAngle: -Math.PI * 0.68,
                        speed: -0.006,
                        width: 150,
                        color: 'rgba(249, 115, 22, 0.08)'
                    }
                ];
            }

            // Floating Musical Notes (♪, ♫, ♩)
            const noteSymbols = ['♪', '♫', '♩'];
            const noteColorsDark = ['#f472b6', '#fb923c', '#c084fc', '#ffffff'];
            const noteColorsLight = ['rgba(249, 115, 22, 0.55)', 'rgba(244, 63, 94, 0.5)', 'rgba(168, 85, 247, 0.5)'];
            const noteColors = isDark ? noteColorsDark : noteColorsLight;
            const noteCount = isDark ? 16 : 12;

            for (let i = 0; i < noteCount; i++) {
                const symbol = noteSymbols[Math.floor(Math.random() * noteSymbols.length)];
                const color = noteColors[Math.floor(Math.random() * noteColors.length)];
                this.particles.push({
                    isNote: true,
                    symbol,
                    x: Math.random() * this.width,
                    y: Math.random() * this.height,
                    fontSize: 14 + Math.random() * 12,
                    color,
                    vy: -(0.35 + Math.random() * 0.4),
                    sway: Math.random() * Math.PI * 2,
                    swaySpeed: 0.02 + Math.random() * 0.025,
                    pulse: Math.random() * Math.PI * 2,
                    glowColor: isDark ? color : 'transparent',
                    glowBlur: isDark ? 10 : 0
                });
            }

            // Concert Stardust motes
            const dustColorsDark = ['rgba(249, 115, 22, 0.85)', 'rgba(217, 70, 239, 0.8)', 'rgba(255, 255, 255, 0.95)'];
            const dustColorsLight = ['rgba(249, 115, 22, 0.45)', 'rgba(244, 63, 94, 0.4)', 'rgba(251, 191, 36, 0.5)'];
            const dustColors = isDark ? dustColorsDark : dustColorsLight;
            const dustCount = isDark ? 34 : 26;

            for (let i = 0; i < dustCount; i++) {
                const color = dustColors[Math.floor(Math.random() * dustColors.length)];
                this.particles.push({
                    isNote: false,
                    x: Math.random() * this.width,
                    y: Math.random() * this.height,
                    size: 1.5 + Math.random() * 2.4,
                    color,
                    vy: -(0.3 + Math.random() * 0.35),
                    vx: (Math.random() - 0.5) * 0.28,
                    pulse: Math.random() * Math.PI * 2,
                    pulseSpeed: 0.025 + Math.random() * 0.03,
                    isSparkle: Math.random() > 0.65,
                    glowColor: isDark ? color : 'transparent',
                    glowBlur: isDark ? 8 : 0
                });
            }
        }

        // =========================================================================
        // ANIMATION LOOP
        // =========================================================================

        start() {
            if (this.animId) return;
            if (!this.enabled) return;

            const tick = (now) => {
                this.updateAndDraw(now);
                this.animId = requestAnimationFrame(tick);
            };
            this.animId = requestAnimationFrame(tick);
        }

        stop() {
            if (this.animId) {
                cancelAnimationFrame(this.animId);
                this.animId = null;
            }
        }

        updateAndDraw(now) {
            if (!this.ctx || !this.width || !this.height) return;
            const ctx = this.ctx;

            ctx.clearRect(0, 0, this.width, this.height);

            const theme = this.theme;
            const mode = this.mode;

            if (theme === 'game') {
                this.renderGameTheme(ctx, mode);
            } else if (theme === 'forest') {
                this.renderForestTheme(ctx, mode);
            } else if (theme === 'city') {
                this.renderCityTheme(ctx, mode, now);
            } else if (theme === 'ice') {
                this.renderIceTheme(ctx, mode);
            } else {
                this.renderZaraLarssonTheme(ctx, mode);
            }
        }

        // =========================================================================
        // THEME RENDERERS
        // =========================================================================

        // 1. GAME THEME
        renderGameTheme(ctx, mode) {
            const isDark = mode === 'dark';

            // Draw Floating / Walking Pixel Characters
            for (let i = 0; i < this.pixelCharacters.length; i++) {
                const char = this.pixelCharacters[i];
                char.x += char.vx;
                char.y += char.vy;
                char.bouncePhase += char.bounceSpeed;

                const bounceY = Math.sin(char.bouncePhase) * 6;

                // Screen wrapping
                if (char.x > this.width + 40) char.x = -40;
                if (char.x < -40) char.x = this.width + 40;
                if (char.y > this.height + 40) char.y = -40;
                if (char.y < -40) char.y = this.height + 40;

                this.drawPixelSprite(
                    ctx,
                    char.x,
                    char.y + bounceY,
                    char.sprite,
                    char.pixelSize,
                    char.color,
                    char.glowColor,
                    char.glowBlur
                );
            }

            // Draw Retro Square Pixels
            for (let i = 0; i < this.particles.length; i++) {
                const p = this.particles[i];
                p.pulse += p.pulseSpeed;
                p.x += p.vx;
                p.y += p.vy;

                if (p.y < -10) p.y = this.height + 10;
                if (p.x < -10) p.x = this.width + 10;
                if (p.x > this.width + 10) p.x = -10;

                const alpha = 0.5 + 0.5 * Math.sin(p.pulse);
                ctx.save();
                ctx.globalAlpha = Math.max(0.15, alpha);
                if (p.glowBlur > 0) {
                    ctx.shadowColor = p.glowColor;
                    ctx.shadowBlur = p.glowBlur;
                }
                ctx.fillStyle = p.color;

                if (p.isDiamond) {
                    ctx.translate(p.x, p.y);
                    ctx.rotate(Math.PI / 4);
                    ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                } else {
                    ctx.fillRect(p.x, p.y, p.size, p.size);
                }
                ctx.restore();
            }
        }

        drawPixelSprite(ctx, x, y, matrix, pixelSize, color, glowColor, glowBlur) {
            ctx.save();
            if (glowBlur > 0) {
                ctx.shadowColor = glowColor;
                ctx.shadowBlur = glowBlur;
            }
            ctx.fillStyle = color;
            const rows = matrix.length;
            const cols = matrix[0].length;
            const startX = Math.floor(x - (cols * pixelSize) / 2);
            const startY = Math.floor(y - (rows * pixelSize) / 2);

            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    if (matrix[r][c] === 1) {
                        ctx.fillRect(startX + c * pixelSize, startY + r * pixelSize, pixelSize, pixelSize);
                    }
                }
            }
            ctx.restore();
        }

        // 2. FOREST THEME
        renderForestTheme(ctx, mode) {
            const isDark = mode === 'dark';

            if (isDark) {
                // Fireflies wandering with organic breathing glow
                for (let i = 0; i < this.particles.length; i++) {
                    const p = this.particles[i];
                    p.pulse += p.pulseSpeed;
                    p.angle += p.angleSpeed;

                    p.x += Math.cos(p.angle) * 0.65 + p.vx;
                    p.y += Math.sin(p.angle * 0.8) * 0.55 + p.vy;

                    if (p.x < -20) p.x = this.width + 20;
                    if (p.x > this.width + 20) p.x = -20;
                    if (p.y < -20) p.y = this.height + 20;
                    if (p.y > this.height + 20) p.y = -20;

                    // True firefly glow: dark period then warm bloom
                    const glow = Math.pow(Math.max(0, Math.sin(p.pulse)), 3.5);
                    if (glow < 0.05) continue;

                    ctx.save();
                    ctx.globalAlpha = glow;
                    ctx.shadowColor = p.glowColor;
                    ctx.shadowBlur = p.glowBlur;

                    // Outer soft halo
                    ctx.fillStyle = p.color;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();

                    // Bright inner core
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size * 0.45, 0, Math.PI * 2);
                    ctx.fill();

                    ctx.restore();
                }
            } else {
                // Day: Flying Birds
                for (let i = 0; i < this.birds.length; i++) {
                    const bird = this.birds[i];
                    bird.wingPhase += bird.wingSpeed;
                    bird.x += bird.vx;
                    bird.y += bird.vy;

                    if (bird.x > this.width + 60) {
                        bird.x = -60;
                        bird.y = 40 + Math.random() * (this.height * 0.45);
                    }

                    this.drawBird(ctx, bird);
                }

                // Sunlit leaves drifting
                for (let i = 0; i < this.particles.length; i++) {
                    const p = this.particles[i];
                    p.sway += p.swaySpeed;
                    p.y += p.vy;
                    p.x += Math.sin(p.sway) * 0.6 + p.vx;

                    if (p.y > this.height + 20) {
                        p.y = -20;
                        p.x = Math.random() * this.width;
                    }
                    if (p.x > this.width + 20) p.x = -20;

                    ctx.save();
                    ctx.fillStyle = p.color;
                    ctx.beginPath();
                    ctx.ellipse(p.x, p.y, p.size * 1.5, p.size * 0.8, p.sway, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                }
            }
        }

        drawBird(ctx, bird) {
            ctx.save();
            ctx.strokeStyle = bird.color;
            ctx.lineWidth = 1.8 * bird.scale;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            const wingSpan = 14 * bird.scale;
            const wingHeight = Math.sin(bird.wingPhase) * (8 * bird.scale);

            ctx.beginPath();
            // Left wing
            ctx.moveTo(bird.x - wingSpan, bird.y + wingHeight);
            ctx.quadraticCurveTo(bird.x - wingSpan * 0.45, bird.y + wingHeight * 0.35 - 3 * bird.scale, bird.x, bird.y);
            // Right wing
            ctx.quadraticCurveTo(bird.x + wingSpan * 0.45, bird.y + wingHeight * 0.35 - 3 * bird.scale, bird.x + wingSpan, bird.y + wingHeight);
            ctx.stroke();

            ctx.restore();
        }

        // 3. CITY THEME
        renderCityTheme(ctx, mode, now) {
            const isDark = mode === 'dark';

            if (isDark) {
                // Night: Twinkling Stars
                for (let i = 0; i < this.particles.length; i++) {
                    const star = this.particles[i];
                    star.twinkle += star.twinkleSpeed;
                    const alpha = 0.2 + 0.8 * Math.pow(Math.sin(star.twinkle), 2);

                    ctx.save();
                    ctx.globalAlpha = alpha;
                    ctx.fillStyle = star.color;

                    if (star.isCross && alpha > 0.7) {
                        this.drawSparkleStar(ctx, star.x, star.y, 4, star.size * 2.2, star.size * 0.5);
                    } else {
                        ctx.beginPath();
                        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
                        ctx.fill();
                    }
                    ctx.restore();
                }

                // Check for new shooting star trigger
                if (now > this.nextShootingStarTime) {
                    this.triggerShootingStar();
                    this.nextShootingStarTime = now + 2600 + Math.random() * 3200;
                }

                // Draw Shooting Stars
                for (let i = this.shootingStars.length - 1; i >= 0; i--) {
                    const m = this.shootingStars[i];
                    m.x += m.vx;
                    m.y += m.vy;
                    m.life -= 0.022;

                    if (m.life <= 0 || m.x > this.width + 100 || m.y > this.height) {
                        this.shootingStars.splice(i, 1);
                        continue;
                    }

                    ctx.save();
                    ctx.globalAlpha = Math.max(0, m.life);
                    ctx.shadowColor = '#38bdf8';
                    ctx.shadowBlur = 10;

                    // Gradient tail
                    const tailX = m.x - (m.vx / Math.hypot(m.vx, m.vy)) * m.length;
                    const tailY = m.y - (m.vy / Math.hypot(m.vx, m.vy)) * m.length;
                    const grad = ctx.createLinearGradient(tailX, tailY, m.x, m.y);
                    grad.addColorStop(0, 'rgba(56, 189, 248, 0)');
                    grad.addColorStop(0.7, 'rgba(56, 189, 248, 0.6)');
                    grad.addColorStop(1, '#ffffff');

                    ctx.strokeStyle = grad;
                    ctx.lineWidth = 2.4;
                    ctx.lineCap = 'round';

                    ctx.beginPath();
                    ctx.moveTo(tailX, tailY);
                    ctx.lineTo(m.x, m.y);
                    ctx.stroke();

                    // Star head
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(m.x, m.y, 2.5, 0, Math.PI * 2);
                    ctx.fill();

                    ctx.restore();
                }
            } else {
                // Day: Fluffy Moving Clouds
                for (let i = 0; i < this.clouds.length; i++) {
                    const c = this.clouds[i];
                    c.x += c.vx;

                    if (c.x > this.width + 250) {
                        c.x = -250;
                        c.y = 50 + Math.random() * (this.height * 0.38);
                    }

                    this.drawCloud(ctx, c);
                }

                // Gentle sunlit specks
                for (let i = 0; i < this.particles.length; i++) {
                    const p = this.particles[i];
                    p.pulse += 0.03;
                    p.y += p.vy;
                    p.x += p.vx;

                    if (p.y < -10) p.y = this.height + 10;
                    if (p.x > this.width + 10) p.x = -10;

                    ctx.save();
                    ctx.globalAlpha = 0.35 + 0.35 * Math.sin(p.pulse);
                    ctx.fillStyle = p.color;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                }
            }
        }

        triggerShootingStar() {
            const startX = Math.random() * (this.width * 0.7);
            const startY = Math.random() * (this.height * 0.35);
            const speed = 10 + Math.random() * 5;
            const angle = Math.PI / 6 + (Math.random() - 0.5) * 0.2; // roughly 30 degrees diagonal
            this.shootingStars.push({
                x: startX,
                y: startY,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                length: 90 + Math.random() * 60,
                life: 1.0
            });
        }

        drawCloud(ctx, cloud) {
            ctx.save();
            ctx.fillStyle = cloud.color;
            ctx.beginPath();
            for (let i = 0; i < cloud.puffs.length; i++) {
                const p = cloud.puffs[i];
                ctx.moveTo(cloud.x + p.dx + p.r, cloud.y + p.dy);
                ctx.arc(cloud.x + p.dx, cloud.y + p.dy, p.r, 0, Math.PI * 2);
            }
            ctx.fill();
            ctx.restore();
        }

        // 4. ICE THEME: Snowfall & Ice Crystals
        renderIceTheme(ctx, mode) {
            const isDark = mode === 'dark';

            for (let i = 0; i < this.particles.length; i++) {
                const p = this.particles[i];
                p.sway += p.swaySpeed;
                p.rot += p.rotSpeed;
                p.y += p.vy;
                p.x += Math.sin(p.sway) * 0.65;

                if (p.y > this.height + 15) {
                    p.y = -15;
                    p.x = Math.random() * this.width;
                }
                if (p.x > this.width + 15) p.x = -15;
                if (p.x < -15) p.x = this.width + 15;

                ctx.save();
                if (p.glowBlur > 0) {
                    ctx.shadowColor = p.glowColor;
                    ctx.shadowBlur = p.glowBlur;
                }
                ctx.fillStyle = p.color;
                ctx.strokeStyle = p.color;

                if (p.isCrystal && isDark) {
                    // Draw 6-point ice crystal snowflake
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rot);
                    ctx.lineWidth = 1.3;
                    for (let s = 0; s < 3; s++) {
                        ctx.beginPath();
                        ctx.moveTo(0, -p.size);
                        ctx.lineTo(0, p.size);
                        ctx.stroke();
                        ctx.rotate(Math.PI / 3);
                    }
                } else {
                    // Soft circular snow flake
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        }

        // 5. ZARA LARSSON THEME: Stage Spotlights & Floating Musical Notes
        renderZaraLarssonTheme(ctx, mode) {
            const isDark = mode === 'dark';

            // Panning Stage Spotlights in Dark Mode
            if (isDark) {
                for (let i = 0; i < this.spotlights.length; i++) {
                    const beam = this.spotlights[i];
                    beam.angle += beam.speed;
                    if (beam.angle > beam.maxAngle || beam.angle < beam.minAngle) {
                        beam.speed = -beam.speed;
                    }

                    ctx.save();
                    const targetLen = this.height * 1.5;
                    const tipX = beam.originX + Math.cos(beam.angle) * targetLen;
                    const tipY = beam.originY + Math.sin(beam.angle) * targetLen;

                    const perpAngle = beam.angle + Math.PI / 2;
                    const halfWidth = beam.width;
                    const p1X = tipX + Math.cos(perpAngle) * halfWidth;
                    const p1Y = tipY + Math.sin(perpAngle) * halfWidth;
                    const p2X = tipX - Math.cos(perpAngle) * halfWidth;
                    const p2Y = tipY - Math.sin(perpAngle) * halfWidth;

                    const grad = ctx.createLinearGradient(beam.originX, beam.originY, tipX, tipY);
                    grad.addColorStop(0, beam.color);
                    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

                    ctx.fillStyle = grad;
                    ctx.beginPath();
                    ctx.moveTo(beam.originX, beam.originY);
                    ctx.lineTo(p1X, p1Y);
                    ctx.lineTo(p2X, p2Y);
                    ctx.closePath();
                    ctx.fill();
                    ctx.restore();
                }
            }

            // Draw Floating Musical Notes and Stardust
            for (let i = 0; i < this.particles.length; i++) {
                const p = this.particles[i];
                p.pulse += 0.03;
                p.y += p.vy;

                if (p.isNote) {
                    p.sway += p.swaySpeed;
                    p.x += Math.sin(p.sway) * 0.5;
                } else {
                    p.x += p.vx;
                }

                if (p.y < -30) {
                    p.y = this.height + 30;
                    p.x = Math.random() * this.width;
                }
                if (p.x < -30) p.x = this.width + 30;
                if (p.x > this.width + 30) p.x = -30;

                ctx.save();
                if (p.glowBlur > 0) {
                    ctx.shadowColor = p.glowColor;
                    ctx.shadowBlur = p.glowBlur;
                }
                ctx.fillStyle = p.color;

                if (p.isNote) {
                    // Draw Musical Note glyph
                    const alpha = 0.55 + 0.45 * Math.sin(p.pulse);
                    ctx.globalAlpha = Math.max(0.2, alpha);
                    ctx.font = `bold ${Math.round(p.fontSize)}px "Segoe UI Symbol", "Apple Color Emoji", sans-serif`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(p.symbol, p.x, p.y);
                } else if (p.isSparkle) {
                    // Stardust 4-point sparkle star
                    const alpha = 0.5 + 0.5 * Math.sin(p.pulse);
                    ctx.globalAlpha = Math.max(0.2, alpha);
                    this.drawSparkleStar(ctx, p.x, p.y, 4, p.size * 2.0, p.size * 0.4);
                } else {
                    // Stardust circle
                    const alpha = 0.4 + 0.6 * Math.sin(p.pulse);
                    ctx.globalAlpha = Math.max(0.15, alpha);
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        }

        drawSparkleStar(ctx, cx, cy, spikes, outerRadius, innerRadius) {
            let rot = (Math.PI / 2) * 3;
            let x = cx;
            let y = cy;
            const step = Math.PI / spikes;

            ctx.beginPath();
            ctx.moveTo(cx, cy - outerRadius);
            for (let i = 0; i < spikes; i++) {
                x = cx + Math.cos(rot) * outerRadius;
                y = cy + Math.sin(rot) * outerRadius;
                ctx.lineTo(x, y);
                rot += step;

                x = cx + Math.cos(rot) * innerRadius;
                y = cy + Math.sin(rot) * innerRadius;
                ctx.lineTo(x, y);
                rot += step;
            }
            ctx.lineTo(cx, cy - outerRadius);
            ctx.closePath();
            ctx.fill();
        }
    }

    // Expose singleton to window
    const engine = new AnimatedBackgroundEngine();
    window.AgileFlowBackground = engine;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => engine.init());
    } else {
        engine.init();
    }
})();
