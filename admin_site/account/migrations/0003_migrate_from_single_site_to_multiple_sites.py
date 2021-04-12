from django.db import migrations, models

SUPER_ADMIN = 0
SITE_USER = 1
SITE_ADMIN = 2

def migrate_from_single_site_to_multiple_sites(apps, schema_editor):
	UserProfile = apps.get_model("account", "UserProfile")
	SiteMembership = apps.get_model("account", "SiteMembership")

	for user_profile in UserProfile.objects.all():
		if user_profile.type == SUPER_ADMIN:
			user = user_profile.user
			user.is_staff = True
			user.is_admin = True
			user.save()

		else:
			SiteMembership.objects.create(
				user_profile=user_profile,
				site=user_profile.site,
				site_user_type=user_profile.type
			)




class Migration(migrations.Migration):

    dependencies = [('account', '0002_auto_20210409_1139')]

    operations = [
    	migrations.RunPython(migrate_from_single_site_to_multiple_sites),
    ]