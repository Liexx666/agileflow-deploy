from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from backlog.models import Tag, Sprint, Task


class Command(BaseCommand):
    help = 'Seeds 5 sample mockup tasks with consistent Task N: <Title> format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force delete and re-seed sample tasks',
        )

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data for AgileFlow...")

        # 1. Create User accounts for all 5 Team Members and set their passwords
        users_data = [
            ('chloe', 'Chloe', 'Lai Phui Yan', 'clai0045@student.monash.edu'),
            ('hiromu', 'Hiromu', 'Tao', 'htao0001@student.monash.edu'),
            ('ethan', 'Ethan', 'Tiang Yong Xuan', 'etia0001@student.monash.edu'),
            ('siddharth', 'Siddharth', 'Mahendran', 'smah0001@student.monash.edu'),
            ('yaoxing', 'Li', 'YaoXing', 'lyao0001@student.monash.edu'),
        ]
        
        user_objs = {}
        for username, first_name, last_name, email in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email
                }
            )
            # Set the password properly so you can actually log in!
            user.set_password('password123')
            user.save()
            user_objs[username] = user

        user_chloe = user_objs['chloe']
        user_hiromu = user_objs['hiromu']
        user_ethan = user_objs['ethan']
        user_siddharth = user_objs['siddharth']
        user_yaoxing = user_objs['yaoxing']

        # 2. Create Tags
        tags_data = [
            'UI', 'UX', 'Front-end', 'Back-end', 'API', 'Database', 'Testing', 'Framework'
        ]
        tag_objs = {}
        for tag_name in tags_data:
            t, _ = Tag.objects.get_or_create(name=tag_name)
            tag_objs[tag_name] = t

        # 3. Create Sprints matching mockup
        sprint1, _ = Sprint.objects.get_or_create(name='Sprint 1', defaults={'status': 'completed', 'goal': 'Project Inception & Planning'})
        sprint2, _ = Sprint.objects.get_or_create(name='Sprint 2', defaults={'status': 'completed', 'goal': 'Architecture & Spikes'})
        sprint3, _ = Sprint.objects.get_or_create(name='Sprint 3', defaults={'status': 'active', 'goal': 'Sprint 1 Walking Skeleton'})

        # 4. Check if tasks already exist to prevent wiping user data
        if Task.objects.exists() and not options.get('force'):
            self.stdout.write(self.style.SUCCESS("Existing tasks detected in database. Preserving existing tasks without wiping."))
            return

        if options.get('force'):
            Task.objects.all().delete()


        # Task 1
        task1 = Task.objects.create(
            title='Task 1: Design UI/UX Wireframes',
            description='Design user interface wireframes and validate interaction flows.',
            acceptance_criteria='Wireframe layouts approved for desktop and mobile.',
            item_type='story',
            priority='low',
            story_points=3,
            stage='development',
            status='in_progress',
            assignee=user_chloe,
            sprint=sprint3,
        )
        task1.tags.set([tag_objs['UI'], tag_objs['UX']])

        # Task 2
        task2 = Task.objects.create(
            title='Task 2: Implement User Authentication',
            description='Implement authentication login screen and session validation.',
            acceptance_criteria='Valid credentials log in successfully and redirect to backlog.',
            item_type='story',
            priority='urgent',
            story_points=10,
            stage='development',
            status='not_started',
            assignee=user_hiromu,
            sprint=sprint3,
        )
        task2.tags.set([tag_objs['Front-end']])

        # Task 3
        task3 = Task.objects.create(
            title='Task 3: Configure Database Storage',
            description='Set up PostgreSQL relational models and verify connection handling.',
            acceptance_criteria='Migrations apply cleanly and models pass relational checks.',
            item_type='story',
            priority='important',
            story_points=5,
            stage='planning',
            status='not_started',
            assignee=user_ethan,
        )
        task3.tags.set([tag_objs['Database'], tag_objs['Back-end']])

        # Task 4
        task4 = Task.objects.create(
            title='Task 4: Build REST API Endpoints',
            description='Create endpoint to retrieve filtered backlog items and aggregate metrics.',
            acceptance_criteria='Returns JSON response with status 200 and accurate counts.',
            item_type='story',
            priority='medium',
            story_points=2,
            stage='development',
            status='not_started',
            assignee=user_siddharth,
        )
        task4.tags.set([tag_objs['API'], tag_objs['Back-end']])

        # Task 5
        task5 = Task.objects.create(
            title='Task 5: Fix Sprint Date Validation',
            description='Ensure sprint start date is always before end date.',
            acceptance_criteria='Displays validation error message if end date is earlier.',
            item_type='bug',
            priority='low',
            story_points=1,
            stage='testing',
            status='not_started',
            assignee=user_yaoxing,
        )
        task5.tags.set([tag_objs['Testing']])

        self.stdout.write(self.style.SUCCESS("Successfully seeded 5 sample mock tasks with consistent 'Task N: Title' format!"))
