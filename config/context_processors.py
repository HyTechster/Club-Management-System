from django.conf import settings


def club(request):
    return {"CLUB_NAME": settings.CLUB_NAME}
