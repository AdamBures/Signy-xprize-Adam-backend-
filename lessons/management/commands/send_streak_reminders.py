from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from lessons.models import UserProgress
from django.core.mail import send_mail

User = get_user_model()

class Command(BaseCommand):
    help = 'Sends email reminders to users who have not completed a lesson today before midnight'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write(f"Running streak reminders for date: {today}")

        users = User.objects.filter(is_active=True)
        count_sent = 0

        for user in users:
            has_activity = UserProgress.objects.filter(
                user=user,
                updated_at__date=today,
                completed=True
            ).exists()

            if not has_activity:
                self.stdout.write(f"User {user.username} has no activity today. Sending reminder...")
                try:
                    send_mail(
                        subject="Tvůj streak je v ohrožení! 🔥",
                        message=f"Ahoj {user.first_name or user.username},\n\ndnes jsi ještě nedokončil žádnou lekci v aplikaci HandSign. Procvič si aspoň jedno slovíčko před půlnocí, ať nepřijdeš o svůj {user.current_streak}denní streak!\n\nZabere to jen 2 minuty.\n\nTým HandSign",
                        from_email="reminders@handsign.cz",
                        recipient_list=[user.email or "user@example.com"],
                        fail_silently=False
                    )
                    count_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {user.username}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully sent {count_sent} reminder emails."))
