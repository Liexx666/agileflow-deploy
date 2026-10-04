from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from backlog.models import Tag, Sprint, Task, SprintHistory


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
        admin_user = User.objects.filter(is_superuser=True).first() or user_chloe

        # 2. Create Tags
        tags_data = [
            'UI', 'UX', 'Front-end', 'Back-end', 'API', 'Database', 'Testing', 'Framework'
        ]
        tag_objs = {}
        for tag_name in tags_data:
            t, _ = Tag.objects.get_or_create(name=tag_name)
            tag_objs[tag_name] = t

        # 3. Create Sprints matching mockup with proper required dates (US-12 compliant)
        import datetime
        today = datetime.date.today()
        
        sprint1, _ = Sprint.objects.get_or_create(
            name='Sprint 1',
            defaults={
                'status': 'completed',
                'start_date': today - datetime.timedelta(days=28),
                'end_date': today - datetime.timedelta(days=15),
                'goal': 'Project Inception & Planning',
                'product_owner': user_chloe,
                'scrum_master': user_hiromu,
            }
        )
        sprint1.start_date = sprint1.start_date or (today - datetime.timedelta(days=28))
        sprint1.end_date = sprint1.end_date or (today - datetime.timedelta(days=15))
        sprint1.product_owner = sprint1.product_owner or user_chloe
        sprint1.scrum_master = sprint1.scrum_master or user_hiromu
        sprint1.save()
        sprint1.team_members.set([user_ethan, user_siddharth, user_yaoxing])
        if not sprint1.history.exists():
            from django.utils import timezone
            t1 = timezone.now() - datetime.timedelta(days=28)
            t2 = timezone.now() - datetime.timedelta(days=27)
            t3 = timezone.now() - datetime.timedelta(days=15)
            h1 = SprintHistory.objects.create(sprint=sprint1, changed_by=admin_user, description="Admin created sprint 'Sprint 1' with status 'Not Started'")
            h1.timestamp = t1; h1.save(update_fields=['timestamp'])
            h2 = SprintHistory.objects.create(sprint=sprint1, changed_by=admin_user, description=f"Admin assigned {user_chloe.get_full_name()} as Product Owner")
            h2.timestamp = t1; h2.save(update_fields=['timestamp'])
            h3 = SprintHistory.objects.create(sprint=sprint1, changed_by=admin_user, description=f"Admin assigned {user_hiromu.get_full_name()} as Scrum Master")
            h3.timestamp = t1; h3.save(update_fields=['timestamp'])
            h4 = SprintHistory.objects.create(sprint=sprint1, changed_by=admin_user, description="Admin assigned Ethan Tiang Yong Xuan, Siddharth, Li YaoXing to Sprint 1")
            h4.timestamp = t1; h4.save(update_fields=['timestamp'])
            h5 = SprintHistory.objects.create(sprint=sprint1, changed_by=admin_user, description="Admin updated status to 'Completed'")
            h5.timestamp = t3; h5.save(update_fields=['timestamp'])

        sprint2, _ = Sprint.objects.get_or_create(
            name='Sprint 2',
            defaults={
                'status': 'completed',
                'start_date': today - datetime.timedelta(days=14),
                'end_date': today - datetime.timedelta(days=1),
                'goal': 'Architecture & Spikes',
                'product_owner': user_chloe,
                'scrum_master': user_ethan,
            }
        )
        sprint2.start_date = sprint2.start_date or (today - datetime.timedelta(days=14))
        sprint2.end_date = sprint2.end_date or (today - datetime.timedelta(days=1))
        sprint2.product_owner = sprint2.product_owner or user_chloe
        sprint2.scrum_master = sprint2.scrum_master or user_ethan
        sprint2.save()
        sprint2.team_members.set([user_hiromu, user_siddharth, user_yaoxing])
        if not sprint2.history.exists():
            from django.utils import timezone
            t1 = timezone.now() - datetime.timedelta(days=14)
            t2 = timezone.now() - datetime.timedelta(days=1)
            h1 = SprintHistory.objects.create(sprint=sprint2, changed_by=admin_user, description="Admin created sprint 'Sprint 2' with status 'Not Started'")
            h1.timestamp = t1; h1.save(update_fields=['timestamp'])
            h2 = SprintHistory.objects.create(sprint=sprint2, changed_by=admin_user, description=f"Admin assigned {user_chloe.get_full_name()} as Product Owner")
            h2.timestamp = t1; h2.save(update_fields=['timestamp'])
            h3 = SprintHistory.objects.create(sprint=sprint2, changed_by=admin_user, description=f"Admin assigned {user_ethan.get_full_name()} as Scrum Master")
            h3.timestamp = t1; h3.save(update_fields=['timestamp'])
            h4 = SprintHistory.objects.create(sprint=sprint2, changed_by=admin_user, description="Admin assigned Hiromu Tao, Siddharth, Li YaoXing to Sprint 2")
            h4.timestamp = t1; h4.save(update_fields=['timestamp'])
            h5 = SprintHistory.objects.create(sprint=sprint2, changed_by=admin_user, description="Admin updated status to 'Completed'")
            h5.timestamp = t2; h5.save(update_fields=['timestamp'])

        sprint3, _ = Sprint.objects.get_or_create(
            name='Sprint 3',
            defaults={
                'status': 'active',
                'start_date': today,
                'end_date': today + datetime.timedelta(days=13),
                'goal': 'Sprint 2 Core Features & Testing',
                'product_owner': user_chloe,
                'scrum_master': user_siddharth,
            }
        )
        sprint3.start_date = sprint3.start_date or today
        sprint3.end_date = sprint3.end_date or (today + datetime.timedelta(days=13))
        sprint3.product_owner = sprint3.product_owner or user_chloe
        sprint3.scrum_master = sprint3.scrum_master or user_siddharth
        sprint3.save()
        sprint3.team_members.set([user_hiromu, user_ethan, user_yaoxing])
        if not sprint3.history.filter(description__contains="created").exists():
            from django.utils import timezone
            t1 = timezone.now() - datetime.timedelta(days=3)
            h1 = SprintHistory.objects.create(sprint=sprint3, changed_by=admin_user, description="Admin created sprint 'Sprint 3' with status 'Not Started'")
            h1.timestamp = t1; h1.save(update_fields=['timestamp'])
            h2 = SprintHistory.objects.create(sprint=sprint3, changed_by=admin_user, description=f"Admin assigned {user_chloe.get_full_name()} as Product Owner")
            h2.timestamp = t1; h2.save(update_fields=['timestamp'])
            h3 = SprintHistory.objects.create(sprint=sprint3, changed_by=admin_user, description="Admin assigned Hiromu Tao, Ethan Tiang Yong Xuan, Li YaoXing to Sprint 3")
            h3.timestamp = t1; h3.save(update_fields=['timestamp'])
            h4 = SprintHistory.objects.create(sprint=sprint3, changed_by=admin_user, description="Admin updated status to 'Active'")
            h4.timestamp = t1; h4.save(update_fields=['timestamp'])

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
            accumulated_hours=4.5,
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
            accumulated_hours=8.0,
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
            accumulated_hours=3.5,
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
            accumulated_hours=1.5,
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
            accumulated_hours=0.5,
            stage='testing',
            status='not_started',
            assignee=user_yaoxing,
        )
        task5.tags.set([tag_objs['Testing']])

        self.stdout.write(self.style.SUCCESS("Successfully seeded 5 sample mock tasks with consistent 'Task N: Title' format!"))
