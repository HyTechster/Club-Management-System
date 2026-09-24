from django.contrib.auth.management import create_permissions
from django.db import migrations

COMMITTEE_PERMS = [
    ("events", "event", ["view", "add", "change"]),
    ("events", "attendance", ["view", "add", "change"]),
    ("accounts", "user", ["view", "add", "change"]),
]
EXCO_EXTRA_PERMS = [
    ("committee", "term", ["view", "add", "change", "delete"]),
    ("committee", "committeerole", ["view", "add", "change", "delete"]),
]


def _perms(apps, spec):
    Permission = apps.get_model("auth", "Permission")
    perms = []
    for app_label, model, actions in spec:
        for action in actions:
            perms.append(Permission.objects.get(
                content_type__app_label=app_label, codename=f"{action}_{model}"
            ))
    return perms


def create_groups(apps, schema_editor):
    # Permissions are normally created after migrate finishes, so make them now.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    committee, _ = Group.objects.get_or_create(name="Committee")
    committee.permissions.set(_perms(apps, COMMITTEE_PERMS))
    exco, _ = Group.objects.get_or_create(name="Exco")
    exco.permissions.set(_perms(apps, COMMITTEE_PERMS + EXCO_EXTRA_PERMS))


def remove_groups(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=["Committee", "Exco"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("accounts", "0001_initial"),
        ("committee", "0001_initial"),
        ("events", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_groups, remove_groups)]
