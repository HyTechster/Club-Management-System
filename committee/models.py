from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Term(models.Model):
    name = models.CharField(max_length=20, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            # Backs up save(): the database itself refuses a second current term.
            models.UniqueConstraint(fields=["is_current"], condition=models.Q(is_current=True),
                                    name="one_current_term"),
        ]

    def __str__(self):
        return self.name + (" (current)" if self.is_current else "")

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on <= self.starts_on:
            raise ValidationError({"ends_on": "The term must end after it starts."})

    def validate_constraints(self, exclude=None):
        # save() moves "current" off the old term, so the form must not reject it first.
        exclude = set(exclude or ()) | {"is_current"}
        super().validate_constraints(exclude=exclude)

    def save(self, *args, **kwargs):
        # Only one term can be current at a time.
        with transaction.atomic():
            if self.is_current:
                Term.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
            super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(is_current=True).first()


class CommitteeRole(models.Model):
    class Title(models.TextChoices):
        PRESIDENT = "PRES", "President"
        VICE_PRESIDENT = "VP", "Vice President"
        SECRETARY = "SEC", "Secretary"
        TREASURER = "TRE", "Treasurer"
        AJK = "AJK", "AJK"

    EXCO_TITLES = {Title.PRESIDENT, Title.VICE_PRESIDENT, Title.SECRETARY, Title.TREASURER}

    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="roles")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="committee_roles")
    title = models.CharField(max_length=4, choices=Title.choices)

    class Meta:
        unique_together = [("term", "member")]
        ordering = ["term", "title"]

    def __str__(self):
        return f"{self.get_title_display()}: {self.member.full_name} ({self.term.name})"

    @property
    def is_exco(self):
        return self.title in self.EXCO_TITLES

    @property
    def rank(self):
        return list(self.Title.values).index(self.title)
