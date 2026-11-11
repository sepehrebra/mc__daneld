import os
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from farms.models import Farm, Plot
from operations.models import Operation


class Command(BaseCommand):
    help = "Seed an empty, explicitly configured Django development database."

    @transaction.atomic
    def handle(self, *args, **options):
        if not os.environ.get("DJANGO_DATABASE_PATH"):
            raise CommandError("Set DJANGO_DATABASE_PATH to a separate development database.")
        password = os.environ.get("DJANGO_DEMO_PASSWORD", "")
        if not 8 <= len(password) <= 128:
            raise CommandError("Set DJANGO_DEMO_PASSWORD to 8–128 characters.")
        if User.objects.exists():
            raise CommandError("The development database must be empty.")

        owner = User.objects.create(full_name="کاربر آزمایشی", phone="+989123456789",
                                    password_hash=make_password(password))
        now = timezone.now()
        today = timezone.localtime(now, ZoneInfo("Asia/Tehran")).date()
        for farm_name in ("مزرعه شمالی", "مزرعه مرکزی", "مزرعه جنوبی"):
            farm = Farm.objects.create(owner=owner, name=farm_name)
            for plot_name in ("قطعه یک", "قطعه دو"):
                plot = Plot.objects.create(farm=farm, name=plot_name, area_m2=1000)
                for title, day, status in (
                    ("آبیاری عقب‌افتاده", -1, "planned"),
                    ("آبیاری امروز", 0, "in_progress"),
                    ("آبیاری آینده", 3, "planned"),
                    ("آبیاری انجام‌شده", -2, "completed"),
                    ("آبیاری لغوشده", 1, "cancelled"),
                ):
                    Operation.objects.create(
                        plot=plot, created_by=owner, title=title, operation_type="irrigation",
                        scheduled_date=today + timedelta(days=day), status=status,
                        completed_at=now + timedelta(days=day) if status == "completed" else None,
                    )
        self.stdout.write(self.style.SUCCESS("Seeded 1 user, 3 farms, 6 plots, and 30 operations."))
