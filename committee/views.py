from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Term


@login_required
def committee_list(request):
    term = Term.current()
    roles = []
    if term:
        roles = sorted(term.roles.select_related("member"), key=lambda r: (r.rank, r.member.full_name))
    return render(request, "committee/list.html", {
        "term": term,
        "exco": [r for r in roles if r.is_exco],
        "ajk": [r for r in roles if not r.is_exco],
    })
