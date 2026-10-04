from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Sprint, SprintHistory


class AssignSprintRoleTests(TestCase):
    """
    Automated tests for assigning Scrum Master and Product Owner to a Sprint.
    Verifies that the roles can be updated properly, and that conflicts are prevented.
    """

    def setUp(self):
        self.client = Client()

        # Regular user who will make the changes
        self.editor = User.objects.create_user(
            username="editor_user",
            first_name="Editor",
            last_name="User",
            email="editor@example.com",
            password="Password123!",
        )

        # Users to be assigned
        self.user1 = User.objects.create_user(
            username="user1",
            first_name="Alice",
            last_name="One",
            email="alice@example.com",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            first_name="Bob",
            last_name="Two",
            email="bob@example.com",
        )

        self.sprint = Sprint.objects.create(
            name="Test Sprint",
            status="not_started",
        )
        self.sprint.team_members.add(self.user1, self.user2)

        self.client.force_login(self.editor)

    def test_assign_scrum_master_successfully(self):
        url = reverse("backlog:assign_sprint_role", kwargs={"sprint_id": self.sprint.id, "role": "scrum_master"})
        response = self.client.post(url, {"user_id": self.user1.id})
        
        # Verify redirect
        self.assertRedirects(response, reverse("backlog:product_backlog"))
        
        # Verify DB update
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.scrum_master, self.user1)
        
        # Verify History
        history = SprintHistory.objects.filter(sprint=self.sprint).latest("timestamp")
        self.assertIn("Alice One", history.description)
        self.assertIn("Scrum Master", history.description)

    def test_assign_product_owner_successfully(self):
        url = reverse("backlog:assign_sprint_role", kwargs={"sprint_id": self.sprint.id, "role": "product_owner"})
        response = self.client.post(url, {"user_id": self.user2.id})
        
        # Verify redirect
        self.assertRedirects(response, reverse("backlog:product_backlog"))
        
        # Verify DB update
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.product_owner, self.user2)
        
        # Verify History
        history = SprintHistory.objects.filter(sprint=self.sprint).latest("timestamp")
        self.assertIn("Bob Two", history.description)
        self.assertIn("Product Owner", history.description)

    def test_cannot_assign_same_person_to_both_roles(self):
        # Assign User1 as Product Owner
        self.sprint.product_owner = self.user1
        self.sprint.save()

        # Try to assign User1 as Scrum Master
        url = reverse("backlog:assign_sprint_role", kwargs={"sprint_id": self.sprint.id, "role": "scrum_master"})
        response = self.client.post(url, {"user_id": self.user1.id}, follow=True)
        
        # Verify error message is in response
        self.assertContains(response, "You cannot be both the Scrum Master and Product Owner.")
        
        # Verify DB not updated
        self.sprint.refresh_from_db()
        self.assertIsNone(self.sprint.scrum_master)

    def test_cannot_assign_empty_user(self):
        url = reverse("backlog:assign_sprint_role", kwargs={"sprint_id": self.sprint.id, "role": "scrum_master"})
        response = self.client.post(url, {"user_id": ""}, follow=True)
        
        # Verify error message
        self.assertContains(response, "Please select a user.")
        
        # Verify DB not updated
        self.sprint.refresh_from_db()
        self.assertIsNone(self.sprint.scrum_master)
