import json
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountSecurity, UserThemePreference


class ThemePreferencesTests(TestCase):
    """Test suite for per-user themes and background preferences with light/dark modes."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user_one",
            email="user1@example.com",
            password="Password123!",
        )
        self.user2 = User.objects.create_user(
            username="user_two",
            email="user2@example.com",
            password="Password123!",
        )
        AccountSecurity.objects.filter(
            user__in=[self.user1, self.user2]
        ).update(must_change_password=False)

        self.update_url = reverse("accounts:update_theme_preference")

    def test_default_theme_preference_is_zara_larsson_light(self):
        """A new user defaults to Zara Larsson theme and Light mode."""
        pref = UserThemePreference.get_for_user(self.user1)
        self.assertIsNotNone(pref)
        self.assertEqual(pref.theme, UserThemePreference.THEME_ZARA)
        self.assertEqual(pref.mode, UserThemePreference.MODE_LIGHT)

    def test_update_theme_preference_via_json(self):
        """Updating theme and mode via JSON persists to database."""
        self.client.force_login(self.user1)
        payload = {"theme": "ice", "mode": "dark"}
        response = self.client.post(
            self.update_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "ice")
        self.assertEqual(data["mode"], "dark")

        # Verify database record
        pref = UserThemePreference.objects.get(user=self.user1)
        self.assertEqual(pref.theme, "ice")
        self.assertEqual(pref.mode, "dark")

    def test_update_theme_preference_via_post_form(self):
        """Updating theme and mode via form POST persists to database."""
        self.client.force_login(self.user1)
        response = self.client.post(
            self.update_url,
            data={"theme": "forest", "mode": "light"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "forest")
        self.assertEqual(data["mode"], "light")

        pref = UserThemePreference.objects.get(user=self.user1)
        self.assertEqual(pref.theme, "forest")
        self.assertEqual(pref.mode, "light")

    def test_update_invalid_theme_returns_400(self):
        """Reject invalid theme names."""
        self.client.force_login(self.user1)
        response = self.client.post(
            self.update_url,
            data=json.dumps({"theme": "neon_galaxy"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json()["status"])

    def test_update_invalid_mode_returns_400(self):
        """Reject invalid mode choices."""
        self.client.force_login(self.user1)
        response = self.client.post(
            self.update_url,
            data=json.dumps({"mode": "sepia"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json()["status"])

    def test_unauthenticated_user_cannot_update_theme(self):
        """Anonymous requests to update theme must be redirected or rejected."""
        response = self.client.post(
            self.update_url,
            data=json.dumps({"theme": "city"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_get_request_to_update_theme_is_not_allowed(self):
        """GET requests to the update endpoint return 405 Method Not Allowed."""
        self.client.force_login(self.user1)
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 405)

    def test_different_users_have_independent_themes(self):
        """User A and User B maintain separate theme & mode settings."""
        # Set user1 to city dark
        pref1 = UserThemePreference.get_for_user(self.user1)
        pref1.theme = "city"
        pref1.mode = "dark"
        pref1.save()

        # Set user2 to game light
        pref2 = UserThemePreference.get_for_user(self.user2)
        pref2.theme = "game"
        pref2.mode = "light"
        pref2.save()

        # Check user1 context when logged in
        self.client.force_login(self.user1)
        resp1 = self.client.get(reverse("backlog:product_backlog"))
        self.assertEqual(resp1.context["user_theme"], "city")
        self.assertEqual(resp1.context["user_mode"], "dark")
        self.assertContains(resp1, 'data-theme="city"')
        self.assertContains(resp1, 'data-mode="dark"')

        # Check user2 context when logged in
        self.client.force_login(self.user2)
        resp2 = self.client.get(reverse("backlog:product_backlog"))
        self.assertEqual(resp2.context["user_theme"], "game")
        self.assertEqual(resp2.context["user_mode"], "light")
        self.assertContains(resp2, 'data-theme="game"')
        self.assertContains(resp2, 'data-mode="light"')

    def test_navbar_ui_elements_and_buttons_removed(self):
        """Navbar renders mode toggle and backgrounds dropdown, but removes old sprint/product buttons near avatar."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse("backlog:product_backlog"))

        # Mode toggle button exists
        self.assertContains(response, 'id="themeModeToggleBtn"')

        # Backgrounds dropdown and live preview exist
        self.assertContains(response, 'id="backgroundsDropdownBtn"')
        self.assertContains(response, 'id="themeLivePreviewCard"')
        self.assertContains(response, "Backgrounds")
        self.assertContains(response, "Zara Larsson")
        self.assertContains(response, "Ice Theme")
        self.assertContains(response, "City Theme")
        self.assertContains(response, "Forest Theme")
        self.assertContains(response, "Game Theme")

        # The old navbar buttons near profile picture are removed
        # Ensure the navigation actions bar does NOT have 'btn-outline-primary' Sprint Board
        content = response.content.decode()
        nav_start = content.find('class="d-flex align-items-center gap-2 ms-auto flex-wrap">')
        self.assertNotEqual(nav_start, -1)
        nav_end = content.find("</nav>", nav_start)
        navbar_actions_html = content[nav_start:nav_end]

        self.assertNotIn("Sprint Board</a>", navbar_actions_html)
        self.assertNotIn("Product Backlog</a>", navbar_actions_html)

    def test_profile_bar_and_dropdown_header_render_theme_graphics(self):
        """Profile bar avatar button and dropdown menu header include themed graphic elements."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertEqual(response.status_code, 200)

        # Avatar button on navbar bar has profile-avatar-btn styling
        self.assertContains(response, "profile-avatar-btn")

        # Profile menu header has profile-dropdown-header and profileHeaderBackdrop
        self.assertContains(response, "profile-dropdown-header")
        self.assertContains(response, 'id="profileHeaderBackdrop"')
        self.assertContains(response, "profile-large-avatar")

        # Themes context processor provides navbar_svg_light and navbar_svg_dark
        available_themes = response.context["available_themes"]
        for theme in available_themes:
            self.assertIn("navbar_svg_light", theme)
            self.assertIn("navbar_svg_dark", theme)
            self.assertTrue(theme["navbar_svg_light"].endswith(".svg"))
            self.assertTrue(theme["navbar_svg_dark"].endswith(".svg"))

    def test_backgrounds_dropdown_panel_and_status_colors_preservation(self):
        """Dropdown panel is rendered and CSS preserves status badge colors."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertEqual(response.status_code, 200)

        # Backgrounds dropdown button & panel are present in the response
        self.assertContains(response, 'id="backgroundsDropdownBtn"')
        self.assertContains(response, 'id="backgroundsDropdownPanel"')
        self.assertContains(response, "backgrounds-dropdown-panel")

        # Read themes.css to verify overflow is visible (no clipping) and status colors are safeguarded
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            css_content = f.read()

        # Overflow visible so dropdown never appears behind main page
        self.assertIn("overflow: visible !important;", css_content)
        self.assertIn("z-index: 1050 !important;", css_content)
        self.assertIn("z-index: 1060 !important;", css_content)

        # Status badge colours are explicitly protected
        self.assertIn(".badge-sprint-completed", css_content)
        self.assertIn("#22c55e", css_content)
        self.assertIn(".badge-sprint-stopped", css_content)
        self.assertIn("#ef4444", css_content)
        self.assertIn(".badge-sprint-active", css_content)
        self.assertIn("#f59e0b", css_content)
        self.assertIn(".badge-sprint-planning", css_content)
        self.assertIn("#64748b", css_content)

    def test_card_view_toggle_three_dots_and_text_contrast(self):
        """Card view toggle, sprint three-dots button, and links have guaranteed contrast without modifying status colors."""
        from backlog.models import Sprint
        Sprint.objects.create(name="Sprint 1", status="active")
        self.user1.is_staff = True
        self.user1.save()

        self.client.force_login(self.user1)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertEqual(response.status_code, 200)

        # Card view switch elements exist
        self.assertContains(response, 'id="viewLabelCard"')
        self.assertContains(response, 'class="view-toggle-label"')
        self.assertContains(response, 'class="view-toggle-switch"')

        # Sprint options buttons have sprint-options-btn class and three dots
        self.assertContains(response, "sprint-options-btn")
        self.assertContains(response, "bi-three-dots-vertical")

        # Deleted Sprints link has deleted-sprints-link class and theme accent color, without hardcoded dark purple #4b3f72
        self.assertContains(response, "deleted-sprints-link")
        self.assertNotIn('style="color: #4b3f72 !important;"', response.content.decode())

        # Check themes.css rules for typography, three dots, toggle, priority cards, and warning badges
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            css_content = f.read()

        # View toggle styling
        self.assertIn(".view-toggle-label", css_content)
        self.assertIn("#viewLabelCard", css_content)
        self.assertIn(".view-toggle-track", css_content)

        # Three dots button rules for dark and light modes
        self.assertIn(".sprint-options-btn", css_content)
        self.assertIn('body[data-mode="dark"] .sprint-options-btn', css_content)
        self.assertIn('body[data-mode="light"] .sprint-options-btn', css_content)

        # Deleted Sprints and Deleted Tasks links
        self.assertIn(".deleted-sprints-link", css_content)
        self.assertIn(".deleted-tasks-link", css_content)

        # Priority cards child text contrast protection (never white text on lime/yellow/orange cards)
        self.assertIn(".priority-card-low", css_content)
        self.assertIn("#14532d", css_content)  # dark green text on lime
        self.assertIn(".priority-card-medium", css_content)
        self.assertIn("#713f12", css_content)  # dark amber text on yellow
        self.assertIn(".priority-card-important", css_content)
        self.assertIn("#431407", css_content)  # dark red-brown text on orange
        self.assertIn(".priority-card-urgent", css_content)

        # Warning badges guaranteed black text on yellow
        self.assertIn(".badge.bg-warning", css_content)
        self.assertIn("color: #000000 !important;", css_content)

    def test_dark_theme_font_and_contrast_enhancements(self):
        """Verify font families and contrast rules for Task Details, Accounts UI, and Admin Dashboard."""
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            css_content = f.read()

        # Font family rules
        self.assertIn("'Outfit', 'Inter'", css_content)
        self.assertIn("body.app-body", css_content)
        self.assertIn("'Inter'", css_content)

        # Task detail contrast engine
        self.assertIn(".detail-panel", css_content)
        self.assertIn(".detail-field", css_content)
        self.assertIn(".detail-value", css_content)
        self.assertIn(".task-desc-box", css_content)
        self.assertIn(".task-desc-content", css_content)
        self.assertIn('body[data-mode="dark"] .detail-field', css_content)
        self.assertIn('body[data-mode="dark"] .task-desc-content', css_content)

        # Accounts UI contrast rules
        self.assertIn(".account-panel", css_content)
        self.assertIn(".account-name", css_content)
        self.assertIn(".account-username", css_content)
        self.assertIn(".account-table", css_content)
        self.assertIn(".role-pill", css_content)
        self.assertIn(".status-pill", css_content)

        # Admin Dashboard contrast rules & pagination dots suppression
        self.assertIn(".user-summary-heading", css_content)
        self.assertIn("#summaryTargetMemberTitle", css_content)
        self.assertIn("#summaryMemberHeadingText", css_content)
        self.assertIn(".member-name-text", css_content)
        self.assertIn(".dash-pagination-dots", css_content)
        self.assertIn("display: none !important;", css_content)



