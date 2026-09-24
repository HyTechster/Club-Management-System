import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from committee.models import CommitteeRole, Term
from events.models import Attendance, Event

SEED_PASSWORD = "clubpass123"

MEMBERS = [
    ("1211101001", "Nur Aisyah binti Rahman", "FCI"),
    ("1211101002", "Lim Wei Jie", "FCI"),
    ("1211101003", "Muhammad Hafiz bin Azman", "FOE"),
    ("1211101004", "Kavitha a/p Subramaniam", "FOM"),
    ("1211101005", "Tan Mei Ling", "FCM"),
    ("1211101006", "Amirul Haziq bin Rosli", "FCI"),
    ("1211101007", "Chong Kai Xuan", "FOE"),
    ("1211101008", "Siti Nurhaliza binti Omar", "FAC"),
    ("1211101009", "Arjun a/l Ramesh", "FCI"),
    ("1211101010", "Wong Jia Hui", "FOB"),
    ("1211101011", "Farah Nadia binti Ismail", "FCM"),
    ("1211101012", "Ooi Zhen Hao", "FET"),
    ("1211101013", "Nabil Iskandar bin Zulkifli", "FOM"),
    ("1211101014", "Priya a/p Maniam", "FOL"),
    ("1211101015", "Goh Yi Xuan", "FCI"),
    ("1211101016", "Aina Sofea binti Kamal", "FOE"),
    ("1211101017", "Lee Jun Kit", "FCM"),
    ("1211101018", "Danish Irfan bin Hamdan", "FCI"),
    ("1211101019", "Yap Hui Min", "FAC"),
    ("1211101020", "Harith Aiman bin Yusof", "FOB"),
]

COMMITTEE = {
    "1211101001": CommitteeRole.Title.PRESIDENT,
    "1211101002": CommitteeRole.Title.VICE_PRESIDENT,
    "1211101004": CommitteeRole.Title.SECRETARY,
    "1211101005": CommitteeRole.Title.TREASURER,
    "1211101006": CommitteeRole.Title.AJK,
    "1211101009": CommitteeRole.Title.AJK,
    "1211101012": CommitteeRole.Title.AJK,
}

# (title, venue, days from today, start hour, hours long, capacity, description)
EVENTS = [
    ("Welcome Night 2026", "Dewan Tun Canselor", -40, 20, 3, None,
     "Meet the committee, find your people, and grab some food."),
    ("Intro to Git Workshop", "FCI Lab CQAR1004", -21, 14, 2, 40,
     "Bring your laptop. We will set up Git and push your first repo."),
    ("Futsal Friendly", "Sports Complex Court 2", -7, 17, 2, 20,
     "Casual games, mixed teams. Wear proper shoes."),
    ("Monthly General Meeting", "Lecture Hall CNMX1001", 0, -1, 3, None,
     "Updates from the committee and open floor for ideas."),
    ("Resume Clinic", "Library Discussion Room 3", 5, 15, 2, 15,
     "Get your resume reviewed by seniors who just finished internships."),
    ("Hackathon Briefing", "FCI Lab CQAR2004", 12, 19, 2, 60,
     "Rules, themes, and team matching for next month's hackathon."),
    ("Charity Run 5K", "Main Gate", 26, 7, 3, 120,
     "Registration fees go to a local shelter. Water and medals provided."),
]


class Command(BaseCommand):
    help = "Create a current term, members, a committee and some events. Safe to run more than once."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Run even when DEBUG is off.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                f"Refusing to seed with DEBUG off. Seed accounts (including committee staff) use the "
                f"password '{SEED_PASSWORD}'. Use --force only on a throwaway database."
            )
        User = get_user_model()
        rng = random.Random(42)
        today = timezone.localdate()

        term, _ = Term.objects.update_or_create(
            name=f"{today.year}/{today.year + 1}",
            defaults={
                "starts_on": date(today.year, 1, 1) if today.month < 7 else date(today.year, 7, 1),
                "ends_on": date(today.year, 12, 31) if today.month < 7 else date(today.year + 1, 6, 30),
                "is_current": True,
            },
        )

        members = []
        for student_id, name, faculty in MEMBERS:
            user, created = User.objects.get_or_create(
                student_id=student_id,
                defaults={
                    "username": student_id,
                    "full_name": name,
                    "faculty": faculty,
                    "email": f"{student_id}@student.example.edu.my",
                    "phone": f"01{rng.randint(1, 9)}-{rng.randint(100, 999)} {rng.randint(1000, 9999)}",
                },
            )
            if created:
                user.set_password(SEED_PASSWORD)
                user.save()
            members.append(user)

        committee_group = Group.objects.get(name="Committee")
        exco_group = Group.objects.get(name="Exco")
        for user in members:
            title = COMMITTEE.get(user.student_id)
            if not title:
                continue
            role, _ = CommitteeRole.objects.update_or_create(term=term, member=user, defaults={"title": title})
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            user.groups.add(exco_group if role.is_exco else committee_group)

        president = members[0]
        now = timezone.localtime()
        for title, venue, day, hour, length, capacity, description in EVENTS:
            if hour < 0:
                # Happening right now, so check-in can be tried straight away.
                starts = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hour)
            else:
                starts = (now + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            event, _ = Event.objects.update_or_create(
                title=title,
                defaults={
                    "venue": venue,
                    "description": description,
                    "starts_at": starts,
                    "ends_at": starts + timedelta(hours=length),
                    "capacity": capacity,
                    "checkin_open": day == 0,
                    "created_by": president,
                },
            )
            if day < 0:
                cap = capacity or len(members)
                for member in rng.sample(members, k=min(cap, rng.randint(9, 17))):
                    Attendance.objects.get_or_create(event=event, member=member)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded term {term.name}, {len(members)} members, {len(COMMITTEE)} committee roles, "
            f"{len(EVENTS)} events. Member password: {SEED_PASSWORD}"
        ))
