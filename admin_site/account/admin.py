from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.db import transaction

from account.models import UserProfile, SiteMembership

admin.site.unregister(User)


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    readonly_fields = (
        "id",
        "sites",
    )
    show_change_link = True
    extra = 0

    def sites(self, obj):
        return obj.sites.values_list("name")


@admin.register(User)
class MyUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = (
        "username",
        "email",
        "last_login",
        "sites",
        "is_staff",
        "is_active",
        "user_profile",
    )
    search_fields = ("username", "email")

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not hasattr(obj, "user_profile"):
            UserProfile.objects.create(user=obj)

    def sites(self, obj):
        return list(obj.user_profile.sites.all())


class SiteMembershipInline(admin.TabularInline):
    model = SiteMembership
    extra = 0


@admin.register(UserProfile)
class MyUserProfileAdmin(admin.ModelAdmin):
    inlines = [SiteMembershipInline]
    list_display = ("user", "user_sites", "language")
    list_filter = ("sites",)
    search_fields = ("user__username",)

    def user_sites(self, obj):
        return list(obj.sites.all())
