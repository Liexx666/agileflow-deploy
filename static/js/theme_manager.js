/**
 * AgileFlow Theme & Background Graphic Manager
 * 10 Presets (5 Graphic Backgrounds x Light/Dark Modes)
 * Manages live preview with real SVG artwork, instant CSS variable application, and DB persistence.
 */

(function () {
    const THEMES_CONFIG = {
        zara_larsson: {
            name: "Zara Larsson",
            light: {
                svg: "/static/images/themes/zara_larsson_light.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_zara_larsson_light.svg",
                cardBg: "rgba(255, 255, 255, 0.95)",
                accent: "#f97316",
                text: "#ffffff",
                tagBg: "rgba(255, 255, 255, 0.9)",
                tagColor: "#ea580c"
            },
            dark: {
                svg: "/static/images/themes/zara_larsson_dark.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_zara_larsson_dark.svg",
                cardBg: "rgba(30, 18, 40, 0.88)",
                accent: "#fb923c",
                text: "#ffffff",
                tagBg: "rgba(251, 146, 60, 0.25)",
                tagColor: "#fdba74"
            }
        },
        ice: {
            name: "Ice Theme",
            light: {
                svg: "/static/images/themes/ice_light.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_ice_light.svg",
                cardBg: "rgba(255, 255, 255, 0.95)",
                accent: "#0284c7",
                text: "#ffffff",
                tagBg: "rgba(255, 255, 255, 0.9)",
                tagColor: "#0284c7"
            },
            dark: {
                svg: "/static/images/themes/ice_dark.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_ice_dark.svg",
                cardBg: "rgba(10, 31, 58, 0.88)",
                accent: "#38bdf8",
                text: "#ffffff",
                tagBg: "rgba(56, 189, 248, 0.25)",
                tagColor: "#7dd3fc"
            }
        },
        city: {
            name: "City Theme",
            light: {
                svg: "/static/images/themes/city_light.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_city_light.svg",
                cardBg: "rgba(255, 255, 255, 0.95)",
                accent: "#2563eb",
                text: "#ffffff",
                tagBg: "rgba(255, 255, 255, 0.9)",
                tagColor: "#1d4ed8"
            },
            dark: {
                svg: "/static/images/themes/city_dark.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_city_dark.svg",
                cardBg: "rgba(17, 24, 39, 0.88)",
                accent: "#06b6d4",
                text: "#ffffff",
                tagBg: "rgba(6, 182, 212, 0.25)",
                tagColor: "#22d3ee"
            }
        },
        forest: {
            name: "Forest Theme",
            light: {
                svg: "/static/images/themes/forest_light.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_forest_light.svg",
                cardBg: "rgba(255, 255, 255, 0.95)",
                accent: "#059669",
                text: "#ffffff",
                tagBg: "rgba(255, 255, 255, 0.9)",
                tagColor: "#059669"
            },
            dark: {
                svg: "/static/images/themes/forest_dark.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_forest_dark.svg",
                cardBg: "rgba(11, 41, 30, 0.88)",
                accent: "#34d399",
                text: "#ffffff",
                tagBg: "rgba(52, 211, 153, 0.25)",
                tagColor: "#6ee7b7"
            }
        },
        game: {
            name: "Game Theme",
            light: {
                svg: "/static/images/themes/game_light.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_game_light.svg",
                cardBg: "rgba(255, 255, 255, 0.95)",
                accent: "#7c3aed",
                text: "#ffffff",
                tagBg: "rgba(255, 255, 255, 0.9)",
                tagColor: "#7c3aed"
            },
            dark: {
                svg: "/static/images/themes/game_dark.svg",
                navbarSvg: "/static/images/themes/navbar/navbar_game_dark.svg",
                cardBg: "rgba(25, 17, 45, 0.88)",
                accent: "#c084fc",
                text: "#ffffff",
                tagBg: "rgba(168, 85, 247, 0.3)",
                tagColor: "#d8b4fe"
            }
        }
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function initThemeEngine() {
        const body = document.body;
        let currentTheme = body.getAttribute("data-theme") || "zara_larsson";
        let currentMode = body.getAttribute("data-mode") || "light";

        const modeToggleBtn = document.getElementById("themeModeToggleBtn");
        const modeThumbIcon = document.getElementById("themeModeThumbIcon");
        const previewCard = document.getElementById("themeLivePreviewCard");
        const previewTitle = document.getElementById("themePreviewTitle");
        const previewModeTag = document.getElementById("themePreviewModeTag");
        const previewMiniCard = document.getElementById("themePreviewMiniCard");
        const previewMiniButton = document.getElementById("themePreviewMiniButton");

        function updatePreview(themeKey, modeKey) {
            if (!previewCard) return;
            const config = THEMES_CONFIG[themeKey] || THEMES_CONFIG.zara_larsson;
            const modeConfig = config[modeKey] || config.light;

            previewCard.style.backgroundImage = `url('${modeConfig.svg}')`;
            previewCard.style.backgroundSize = "cover";
            previewCard.style.backgroundPosition = "center bottom";

            if (previewTitle) {
                previewTitle.textContent = config.name;
            }
            if (previewModeTag) {
                previewModeTag.textContent = modeKey.toUpperCase();
                previewModeTag.style.background = modeConfig.tagBg;
                previewModeTag.style.color = modeConfig.tagColor;
            }
            if (previewMiniCard) {
                previewMiniCard.style.background = modeConfig.cardBg;
            }
            if (previewMiniButton) {
                previewMiniButton.style.background = modeConfig.accent;
                previewMiniButton.style.color = modeConfig.text;
            }
        }

        function updateThumbnails(modeKey) {
            document.querySelectorAll(".theme-option-item").forEach(item => {
                const key = item.getAttribute("data-theme-key");
                const config = THEMES_CONFIG[key];
                if (config) {
                    const thumb = item.querySelector(".theme-graphic-thumbnail");
                    if (thumb) {
                        const imgUrl = modeKey === "dark" ? config.dark.svg : config.light.svg;
                        thumb.style.backgroundImage = `url('${imgUrl}')`;
                    }
                }
            });
        }

        function applyTheme(theme, mode, persist = true) {
            currentTheme = theme;
            currentMode = mode;

            body.setAttribute("data-theme", theme);
            body.setAttribute("data-mode", mode);
            document.documentElement.setAttribute("data-theme", theme);
            document.documentElement.setAttribute("data-mode", mode);

            // Update mode toggle switch UI
            if (modeToggleBtn) {
                modeToggleBtn.setAttribute("aria-checked", mode === "dark" ? "true" : "false");
                modeToggleBtn.setAttribute("title", mode === "dark" ? "Switch to Light mode" : "Switch to Dark mode");
            }
            if (modeThumbIcon) {
                modeThumbIcon.className = mode === "dark" ? "bi bi-moon-stars-fill" : "bi bi-sun-fill";
            }

            // Update active option in backgrounds menu
            document.querySelectorAll(".theme-option-item").forEach(item => {
                if (item.getAttribute("data-theme-key") === theme) {
                    item.classList.add("active");
                } else {
                    item.classList.remove("active");
                }
            });

            // Update option thumbnails and live preview
            updateThumbnails(mode);
            updatePreview(theme, mode);

            // Update animated atmospheric background
            if (window.AgileFlowBackground && typeof window.AgileFlowBackground.setTheme === "function") {
                window.AgileFlowBackground.setTheme(theme, mode);
            }

            // Update profile dropdown header backdrop if present
            const profileBackdrop = document.getElementById("profileHeaderBackdrop");
            const config = THEMES_CONFIG[theme];
            if (profileBackdrop && config) {
                const modeCfg = config[mode] || config.light;
                if (modeCfg && modeCfg.navbarSvg) {
                    profileBackdrop.style.backgroundImage = `url('${modeCfg.navbarSvg}')`;
                }
            }

            // Save to localStorage for instant boot
            localStorage.setItem("agileflow_theme", theme);
            localStorage.setItem("agileflow_mode", mode);

            // Persist to database if requested
            if (persist && window.AGILEFLOW_THEME_UPDATE_URL) {
                const csrfToken = getCookie("csrftoken");
                fetch(window.AGILEFLOW_THEME_UPDATE_URL, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken || "",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify({ theme: theme, mode: mode })
                }).catch(err => {
                    console.warn("Failed to persist theme preference to database:", err);
                });
            }
        }

        // Mode toggle button click handler
        if (modeToggleBtn) {
            modeToggleBtn.addEventListener("click", function (e) {
                e.preventDefault();
                const newMode = currentMode === "light" ? "dark" : "light";
                applyTheme(currentTheme, newMode, true);
            });
        }

        // Theme option items selection and preview hover
        document.querySelectorAll(".theme-option-item").forEach(item => {
            const themeKey = item.getAttribute("data-theme-key");

            // Hover preview
            item.addEventListener("mouseenter", function () {
                updatePreview(themeKey, currentMode);
                if (window.AgileFlowBackground && typeof window.AgileFlowBackground.setTheme === "function") {
                    window.AgileFlowBackground.setTheme(themeKey, currentMode);
                }
            });

            // Revert preview on mouse leave if not selected
            item.addEventListener("mouseleave", function () {
                updatePreview(currentTheme, currentMode);
                if (window.AgileFlowBackground && typeof window.AgileFlowBackground.setTheme === "function") {
                    window.AgileFlowBackground.setTheme(currentTheme, currentMode);
                }
            });

            // Click to select
            item.addEventListener("click", function (e) {
                e.preventDefault();
                applyTheme(themeKey, currentMode, true);
            });
        });

        // Initialize preview & thumbnails on page load
        updateThumbnails(currentMode);
        updatePreview(currentTheme, currentMode);
        if (window.AgileFlowBackground && typeof window.AgileFlowBackground.setTheme === "function") {
            window.AgileFlowBackground.setTheme(currentTheme, currentMode);
            if (typeof window.AgileFlowBackground.wireToggleSwitch === "function") {
                window.AgileFlowBackground.wireToggleSwitch();
            }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initThemeEngine);
    } else {
        initThemeEngine();
    }
})();
