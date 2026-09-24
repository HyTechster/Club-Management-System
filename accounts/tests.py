from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from config.exports import safe_cell

User = get_user_model()

SIGNUP = {
    "student_id": "1211100100", "full_name": "Hana Yusri", "faculty": "FCI",
    "email": "hana@example.com", "password1": "a-strong-pass-771", "password2": "a-strong-pass-771",
}


def make_user(student_id, **extra):
    return User.objects.create_user(username=student_id, student_id=student_id,
                                    full_name=f"Member {student_id}", password="pw-for-tests-123", **extra)


class SignUpTests(TestCase):
    def test_next_to_other_site_is_ignored(self):
        response = self.client.post(reverse("signup") + "?next=https://evil.example/", SIGNUP)
        self.assertRedirects(response, reverse("events:list"))

    def test_next_on_same_site_is_followed(self):
        response = self.client.post(reverse("signup") + "?next=/checkin/abc/", SIGNUP)
        self.assertRedirects(response, "/checkin/abc/", fetch_redirect_response=False)

    def test_student_id_matching_admin_username_is_rejected(self):
        User.objects.create_superuser(username="wan", email="w@example.com", password="x-pass-1234",
                                      student_id="ADMIN01", full_name="Wan")
        response = self.client.post(reverse("signup"), {**SIGNUP, "student_id": "wan"})
        self.assertEqual(response.status_code, 200)  # form error, not a 500
        self.assertFalse(User.objects.filter(email="hana@example.com").exists())

    def test_duplicate_student_id_is_rejected(self):
        make_user("1211100100")
        response = self.client.post(reverse("signup"), SIGNUP)
        self.assertContains(response, "already registered")

    def test_bad_student_id_format_is_rejected(self):
        for bad in ["12 34 56", "=cmd()", "abc"]:
            response = self.client.post(reverse("signup"), {**SIGNUP, "student_id": bad})
            self.assertEqual(response.status_code, 200, bad)
        self.assertEqual(User.objects.count(), 0)

    def test_signup_cannot_grant_staff(self):
        self.client.post(reverse("signup"), {**SIGNUP, "is_staff": "on", "is_superuser": "on"})
        user = User.objects.get(student_id="1211100100")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class AdminEscalationTests(TestCase):
    def setUp(self):
        self.ajk = make_user("1211100200", is_staff=True)
        self.ajk.groups.add(Group.objects.get(name="Committee"))
        self.other_staff = make_user("1211100201", is_staff=True)
        self.other_staff.groups.add(Group.objects.get(name="Exco"))
        self.member = make_user("1211100202")
        self.root = User.objects.create_superuser(username="root", email="r@example.com", password="x-pass-1234",
                                                  student_id="ROOT01", full_name="Root")
        self.client.force_login(self.ajk)

    def change_url(self, user):
        return reverse("admin:accounts_user_change", args=[user.pk])

    def test_committee_cannot_make_self_superuser(self):
        response = self.client.get(self.change_url(self.ajk))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="is_superuser"')
        self.assertNotContains(response, 'name="groups"')

    def test_committee_cannot_touch_other_staff_or_superuser(self):
        for target in [self.root, self.other_staff]:
            password_url = reverse("admin:auth_user_password_change", args=[target.pk])
            self.assertEqual(self.client.get(password_url).status_code, 403, target)
            response = self.client.post(self.change_url(target), {"username": target.username})
            self.assertEqual(response.status_code, 403, target)

    def test_committee_can_edit_regular_member(self):
        self.assertEqual(self.client.get(self.change_url(self.member)).status_code, 200)

    def test_superuser_still_sees_access_fields(self):
        self.client.force_login(self.root)
        self.assertContains(self.client.get(self.change_url(self.ajk)), 'name="is_superuser"')


class CsvExportTests(TestCase):
    def test_formula_cells_are_neutralised(self):
        self.assertEqual(safe_cell("=HYPERLINK(\"x\")"), "'=HYPERLINK(\"x\")")
        self.assertEqual(safe_cell("+60123"), "'+60123")
        self.assertEqual(safe_cell("Nur Aisyah"), "Nur Aisyah")
        self.assertEqual(safe_cell(None), "")

    def test_member_export_escapes_names(self):
        make_user("1211100300")
        User.objects.filter(student_id="1211100300").update(full_name="=1+1")
        root = User.objects.create_superuser(username="root", email="r@example.com", password="x-pass-1234",
                                             student_id="ROOT01", full_name="Root")
        self.client.force_login(root)
        response = self.client.post(reverse("admin:accounts_user_changelist"), {
            "action": "export_members_csv",
            "_selected_action": list(User.objects.values_list("pk", flat=True)),
        })
        body = response.content.decode("utf-8-sig")
        self.assertIn("'=1+1", body)
        self.assertNotIn(",=1+1", body)
