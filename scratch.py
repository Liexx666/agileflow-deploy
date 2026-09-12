import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agileflow_project.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from backlog.models import Task

user = User.objects.first()
if not user:
    user = User.objects.create(username="testuser")

task = Task.objects.first()
if not task:
    task = Task.objects.create(title="test task")

client = Client()
client.force_login(user)

print(f"Fetching task {task.id} detail...")
response = client.get(f"/tasks/{task.id}/")
print(f"Detail Response: {response.status_code}")

print(f"Fetching task {task.id} edit...")
response = client.get(f"/tasks/{task.id}/edit/")
print(f"Edit Response: {response.status_code}")
