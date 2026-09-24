from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Attendance, Event

User = get_user_model()


def make_user(student_id, **extra):
    return User.objects.create_user(
        username=student_id, student_id=student_id, full_name=f"Member {student_id}",
        password="pw-for-tests-123", **extra,
    )


class CheckInTests(TestCase):
    def setUp(self):
        self.member = make_user("1211100001")
        now = timezone.now()
        self.event = Event.objects.create(
            title="General Meeting", venue="Hall", checkin_open=True,
            starts_at=now - timedelta(minutes=10), ends_at=now + timedelta(hours=2),
        )
        self.url = reverse("events:checkin", args=[self.event.checkin_token])
        self.client.force_login(self.member)

    def test_get_shows_confirm_without_checking_in(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Check me in")
        self.assertFalse(Attendance.objects.exists())

    def test_post_checks_in(self):
        response = self.client.post(self.url)
        self.assertContains(response, "You're in!")
        self.assertTrue(Attendance.objects.filter(event=self.event, member=self.member).exists())

    def test_duplicate_scan_is_harmless(self):
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertContains(response, "You're in!")
        self.assertEqual(Attendance.objects.count(), 1)

    def test_closed_checkin_is_refused(self):
        self.event.checkin_open = False
        self.event.save()
        response = self.client.post(self.url)
        self.assertContains(response, "Check-in is closed")
        self.assertFalse(Attendance.objects.exists())

    def test_wrong_token_is_refused(self):
        response = self.client.post(reverse("events:checkin", args=["not-a-real-token"]))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Attendance.objects.exists())

    def test_regenerated_token_invalidates_old_qr(self):
        self.event.regenerate_token()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)

    def test_too_early_is_refused(self):
        now = timezone.now()
        self.event.starts_at = now + timedelta(hours=1)
        self.event.ends_at = now + timedelta(hours=3)
        self.event.save()
        response = self.client.post(self.url)
        self.assertContains(response, "has not started yet")
        self.assertFalse(Attendance.objects.exists())

    def test_thirty_minutes_early_is_allowed(self):
        now = timezone.now()
        self.event.starts_at = now + timedelta(minutes=25)
        self.event.ends_at = now + timedelta(hours=2)
        self.event.save()
        self.client.post(self.url)
        self.assertEqual(Attendance.objects.count(), 1)

    def test_after_end_is_refused(self):
        now = timezone.now()
        self.event.starts_at = now - timedelta(hours=3)
        self.event.ends_at = now - timedelta(minutes=1)
        self.event.save()
        response = self.client.post(self.url)
        self.assertContains(response, "has ended")
        self.assertFalse(Attendance.objects.exists())

    def test_inactive_member_is_refused(self):
        self.member.is_active_member = False
        self.member.save()
        response = self.client.post(self.url)
        self.assertContains(response, "membership is not active")
        self.assertFalse(Attendance.objects.exists())

    def test_full_event_is_refused(self):
        self.event.capacity = 1
        self.event.save()
        Attendance.objects.create(event=self.event, member=make_user("1211100002"))
        response = self.client.post(self.url)
        self.assertContains(response, "full")
        self.assertEqual(Attendance.objects.count(), 1)

    def test_logged_out_redirects_to_login_and_back(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}", fetch_redirect_response=False)
        response = self.client.post(f"{reverse('login')}?next={self.url}", {
            "username": "1211100001", "password": "pw-for-tests-123", "next": self.url,
        })
        self.assertRedirects(response, self.url, fetch_redirect_response=False)


class PermissionTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.event = Event.objects.create(
            title="Workshop", venue="Lab", starts_at=now, ends_at=now + timedelta(hours=1),
        )
        self.qr_url = reverse("events:qr", args=[self.event.pk])

    def test_groups_created_by_migration(self):
        committee = Group.objects.get(name="Committee")
        exco = Group.objects.get(name="Exco")
        committee_perms = set(committee.permissions.values_list("codename", flat=True))
        exco_perms = set(exco.permissions.values_list("codename", flat=True))
        self.assertIn("change_event", committee_perms)
        self.assertNotIn("change_term", committee_perms)
        self.assertTrue(committee_perms <= exco_perms)
        self.assertIn("change_term", exco_perms)
        self.assertIn("add_committeerole", exco_perms)

    def test_regular_member_cannot_see_qr_page(self):
        self.client.force_login(make_user("1211100003"))
        response = self.client.get(self.qr_url)
        self.assertEqual(response.status_code, 302)

    def test_committee_can_see_qr_page(self):
        user = make_user("1211100004", is_staff=True)
        user.groups.add(Group.objects.get(name="Committee"))
        self.client.force_login(user)
        response = self.client.get(self.qr_url)
        self.assertContains(response, "<svg")
        self.assertIn(self.event.checkin_token, response.context["checkin_url"])

    def test_committee_cannot_manage_terms_but_exco_can(self):
        committee_user = make_user("1211100005", is_staff=True)
        committee_user.groups.add(Group.objects.get(name="Committee"))
        exco_user = make_user("1211100006", is_staff=True)
        exco_user.groups.add(Group.objects.get(name="Exco"))
        self.assertFalse(committee_user.has_perm("committee.change_term"))
        self.assertTrue(exco_user.has_perm("committee.change_term"))
        self.assertTrue(exco_user.has_perm("events.change_event"))


class MemberPageTests(TestCase):
    def test_member_pages_need_login(self):
        for name in ["events:list", "profile", "committee"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)

    def test_member_pages_render(self):
        self.client.force_login(make_user("1211100007"))
        for name in ["events:list", "profile", "committee"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_signup_logs_in_with_student_id(self):
        response = self.client.post(reverse("signup"), {
            "student_id": "1211100008", "full_name": "Hana Yusri", "faculty": "FCI",
            "email": "hana@example.com", "password1": "a-strong-pass-771", "password2": "a-strong-pass-771",
        })
        self.assertRedirects(response, reverse("events:list"))
        self.assertEqual(User.objects.get(student_id="1211100008").username, "1211100008")


class ValidationAndSeedTests(TestCase):
    def test_event_must_end_after_start(self):
        from django.core.exceptions import ValidationError
        now = timezone.now()
        with self.assertRaises(ValidationError):
            Event(title="X", venue="Y", starts_at=now, ends_at=now - timedelta(hours=1)).full_clean()

    def test_seed_refuses_when_debug_off(self):
        from django.core.management import CommandError, call_command
        with self.settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("seed")
        self.assertFalse(User.objects.exists())

    def test_seed_is_idempotent(self):
        from io import StringIO

        from django.core.management import call_command
        with self.settings(DEBUG=True):
            call_command("seed", stdout=StringIO())
            counts = (User.objects.count(), Event.objects.count(), Attendance.objects.count())
            call_command("seed", stdout=StringIO())
        self.assertEqual(counts, (User.objects.count(), Event.objects.count(), Attendance.objects.count()))

    def test_password_reset_url_is_not_exposed(self):
        self.assertEqual(self.client.get("/accounts/password_reset/").status_code, 404)
