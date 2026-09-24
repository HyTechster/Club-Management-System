from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from committee.models import Term
from events.models import Attendance

from .forms import SignUpForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("events:list")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        next_url = request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
            return redirect(next_url)
        return redirect("events:list")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    attendances = (
        Attendance.objects.filter(member=request.user)
        .select_related("event")
        .order_by("-event__starts_at")
    )
    term = Term.current()
    term_count = attendances.filter(
        event__starts_at__date__gte=term.starts_on,
        event__starts_at__date__lte=term.ends_on,
    ).count() if term else 0
    roles = request.user.committee_roles.select_related("term").order_by("-term__starts_on")
    return render(request, "accounts/profile.html", {
        "attendances": attendances,
        "term": term,
        "term_count": term_count,
        "roles": roles,
    })
