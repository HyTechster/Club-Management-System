from datetime import date

from django.test import TestCase

from .models import Term


class CurrentTermTests(TestCase):
    def test_only_one_current_term(self):
        old = Term.objects.create(name="2025/2026", starts_on=date(2025, 7, 1), ends_on=date(2026, 6, 30),
                                  is_current=True)
        new = Term.objects.create(name="2026/2027", starts_on=date(2026, 7, 1), ends_on=date(2027, 6, 30),
                                  is_current=True)
        old.refresh_from_db()
        self.assertFalse(old.is_current)
        self.assertTrue(new.is_current)
        self.assertEqual(Term.objects.filter(is_current=True).count(), 1)
        self.assertEqual(Term.current(), new)

    def test_saving_non_current_term_keeps_current(self):
        cur = Term.objects.create(name="2026/2027", starts_on=date(2026, 7, 1), ends_on=date(2027, 6, 30),
                                  is_current=True)
        Term.objects.create(name="2024/2025", starts_on=date(2024, 7, 1), ends_on=date(2025, 6, 30))
        cur.refresh_from_db()
        self.assertTrue(cur.is_current)


class TermValidationTests(TestCase):
    def test_database_refuses_two_current_terms(self):
        from django.db import IntegrityError
        Term.objects.create(name="A", starts_on=date(2025, 7, 1), ends_on=date(2026, 6, 30), is_current=True)
        with self.assertRaises(IntegrityError):
            # Bypasses save(), so only the database constraint stands in the way.
            Term.objects.bulk_create([Term(name="B", starts_on=date(2026, 7, 1), ends_on=date(2027, 6, 30),
                                           is_current=True)])

    def test_full_clean_allows_switching_current_term(self):
        Term.objects.create(name="A", starts_on=date(2025, 7, 1), ends_on=date(2026, 6, 30), is_current=True)
        new = Term(name="B", starts_on=date(2026, 7, 1), ends_on=date(2027, 6, 30), is_current=True)
        new.full_clean()
        new.save()
        self.assertEqual(Term.current(), new)

    def test_end_before_start_is_invalid(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            Term(name="C", starts_on=date(2026, 7, 1), ends_on=date(2026, 1, 1)).full_clean()
