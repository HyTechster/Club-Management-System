from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Faculty(models.TextChoices):
        FCI = "FCI", "Computing and Informatics"
        FOM = "FOM", "Management"
        FCM = "FCM", "Creative Multimedia"
        FOE = "FOE", "Engineering"
        FAC = "FAC", "Applied Communication"
        FOB = "FOB", "Business"
        FOL = "FOL", "Law"
        FET = "FET", "Engineering and Technology"
        OTHER = "OTH", "Other"

    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=120)
    faculty = models.CharField(max_length=3, choices=Faculty.choices, default=Faculty.FCI)
    phone = models.CharField(max_length=20, blank=True)
    joined_on = models.DateField(auto_now_add=True)
    is_active_member = models.BooleanField(default=True)

    # Asked for by createsuperuser, so admins never get a blank (and clashing) student_id.
    REQUIRED_FIELDS = ["email", "student_id", "full_name"]

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name or self.username} ({self.student_id})"

    @property
    def initials(self):
        # Skip Malay/Indian patronymic connectors so "Nur Aisyah binti Rahman" gives "NA".
        skip = {"bin", "binti", "a/l", "a/p", "bt", "b."}
        words = [w for w in (self.full_name or self.username).split() if w.lower() not in skip]
        return "".join(w[0] for w in words[:2]).upper()
