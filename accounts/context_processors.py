from .models import UserThemePreference

AVAILABLE_THEMES = [
    {
        "id": "zara_larsson",
        "name": "Zara Larsson",
        "tagline": "Default sunset & midnight sun glow",
        "swatch_light": "linear-gradient(135deg, #fff7ed 0%, #fed7aa 50%, #f472b6 100%)",
        "swatch_dark": "linear-gradient(135deg, #180d1e 0%, #2e1045 50%, #701a75 100%)",
        "svg_light": "/static/images/themes/zara_larsson_light.svg",
        "svg_dark": "/static/images/themes/zara_larsson_dark.svg",
        "navbar_svg_light": "/static/images/themes/navbar/navbar_zara_larsson_light.svg",
        "navbar_svg_dark": "/static/images/themes/navbar/navbar_zara_larsson_dark.svg",
        "accent": "#f97316",
        "icon": "bi-sunset-fill",
    },
    {
        "id": "ice",
        "name": "Ice Theme",
        "tagline": "Frosty glacial cyan & polar snow",
        "swatch_light": "linear-gradient(135deg, #f0f9ff 0%, #bae6fd 50%, #7dd3fc 100%)",
        "swatch_dark": "linear-gradient(135deg, #071526 0%, #0c2540 50%, #0369a1 100%)",
        "svg_light": "/static/images/themes/ice_light.svg",
        "svg_dark": "/static/images/themes/ice_dark.svg",
        "navbar_svg_light": "/static/images/themes/navbar/navbar_ice_light.svg",
        "navbar_svg_dark": "/static/images/themes/navbar/navbar_ice_dark.svg",
        "accent": "#0ea5e9",
        "icon": "bi-snow2",
    },
    {
        "id": "city",
        "name": "City Theme",
        "tagline": "Urban skyline (Daylight & Cyber Night)",
        "swatch_light": "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #94a3b8 100%)",
        "swatch_dark": "linear-gradient(135deg, #090d16 0%, #111827 50%, #1e1b4b 100%)",
        "svg_light": "/static/images/themes/city_light.svg",
        "svg_dark": "/static/images/themes/city_dark.svg",
        "navbar_svg_light": "/static/images/themes/navbar/navbar_city_light.svg",
        "navbar_svg_dark": "/static/images/themes/navbar/navbar_city_dark.svg",
        "accent": "#3b82f6",
        "icon": "bi-buildings-fill",
    },
    {
        "id": "forest",
        "name": "Forest Theme",
        "tagline": "Lush emerald canopy & misty pine",
        "swatch_light": "linear-gradient(135deg, #f0fdf4 0%, #bbf7d0 50%, #86efac 100%)",
        "swatch_dark": "linear-gradient(135deg, #051a11 0%, #0b2d1f 50%, #064e3b 100%)",
        "svg_light": "/static/images/themes/forest_light.svg",
        "svg_dark": "/static/images/themes/forest_dark.svg",
        "navbar_svg_light": "/static/images/themes/navbar/navbar_forest_light.svg",
        "navbar_svg_dark": "/static/images/themes/navbar/navbar_forest_dark.svg",
        "accent": "#10b981",
        "icon": "bi-tree-fill",
    },
    {
        "id": "game",
        "name": "Game Theme",
        "tagline": "Retro arcade & synthwave cyber neon",
        "swatch_light": "linear-gradient(135deg, #faf5ff 0%, #e9d5ff 50%, #c084fc 100%)",
        "swatch_dark": "linear-gradient(135deg, #0d0b1a 0%, #1e1233 50%, #581c87 100%)",
        "svg_light": "/static/images/themes/game_light.svg",
        "svg_dark": "/static/images/themes/game_dark.svg",
        "navbar_svg_light": "/static/images/themes/navbar/navbar_game_light.svg",
        "navbar_svg_dark": "/static/images/themes/navbar/navbar_game_dark.svg",
        "accent": "#a855f7",
        "icon": "bi-controller",
    },
]


def theme_context(request):
    """Expose the user's active theme, mode, and available presets globally in templates."""
    user = getattr(request, "user", None)
    theme = UserThemePreference.THEME_ZARA
    mode = UserThemePreference.MODE_LIGHT

    if user and user.is_authenticated:
        pref = UserThemePreference.get_for_user(user)
        if pref:
            theme = pref.theme
            mode = pref.mode

    return {
        "user_theme": theme,
        "user_mode": mode,
        "available_themes": AVAILABLE_THEMES,
    }
