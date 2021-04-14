from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from account.models import UserProfile, SiteMembership


admin.site.unregister(User)


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 1


@admin.register(User)
class MyUserAdmin(UserAdmin):
    inlines = [UserProfileInline]


class SiteMembershipInline(admin.TabularInline):
    model = SiteMembership
    extra = 0
    pass


@admin.register(UserProfile)
class MyUserProfileAdmin(admin.ModelAdmin):
    inlines = [SiteMembershipInline]
