import re

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

STUDENT_ID_RE = re.compile(r"^[0-9A-Za-z]{6,20}$")


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["student_id", "full_name", "faculty", "email"]
        labels = {"student_id": "Student ID", "full_name": "Full name"}
        help_texts = {"student_id": "The number on your student card."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "At least 8 characters. Not only numbers."
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].help_text = ""

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"].strip()
        if not STUDENT_ID_RE.match(student_id):
            raise forms.ValidationError("Use the ID on your student card: 6 to 20 letters or numbers, no spaces.")
        # The student ID becomes the username, which may already belong to an admin account.
        if User.objects.filter(username__iexact=student_id).exists():
            raise forms.ValidationError("This student ID is already registered.")
        return student_id

    def save(self, commit=True):
        user = super().save(commit=False)
        # Members log in with their student ID.
        user.username = self.cleaned_data["student_id"]
        if commit:
            user.save()
        return user
