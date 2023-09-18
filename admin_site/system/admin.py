from hashlib import md5

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html_join, escape, mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from system.models import (
    AssociatedScript,
    AssociatedScriptParameter,
    Batch,
    BatchParameter,
    Citizen,
    Configuration,
    ConfigurationEntry,
    FeaturePermission,
    ImageVersion,
    Input,
    Job,
    EventRuleServer,
    PC,
    PCGroup,
    Script,
    ScriptTag,
    SecurityEvent,
    SecurityProblem,
    Site,
    WakeChangeEvent,
    WakeWeekPlan,
)

from changelog.models import (
    Changelog,
    ChangelogComment,
    ChangelogTag,
)


class ConfigurationEntryInline(admin.TabularInline):
    model = ConfigurationEntry
    extra = 0


class SiteInlineForConfiguration(admin.TabularInline):
    model = Site
    extra = 0


class PCGroupInline(admin.TabularInline):
    model = PCGroup
    extra = 0


class PCInlineForConfiguration(admin.TabularInline):
    model = PC
    extra = 0


class ConfigurationAdmin(admin.ModelAdmin):
    fields = ["name"]
    search_fields = ("name",)
    inlines = [
        ConfigurationEntryInline,
        SiteInlineForConfiguration,
        PCGroupInline,
        PCInlineForConfiguration,
    ]


class PCInline(admin.TabularInline):
    model = PC.pc_groups.through
    extra = 0


class AssociatedScriptInline(admin.TabularInline):
    model = AssociatedScript
    extra = 0


class PCGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "site")
    list_filter = ("site",)
    inlines = [PCInline, AssociatedScriptInline]


class JobInline(admin.TabularInline):
    fields = ("id", "pc", "status", "user", "created", "started", "finished")
    readonly_fields = ("id", "pc", "status", "user", "created", "started", "finished")
    model = Job
    extra = 0
    can_delete = False
    show_change_link = True


class BatchParameterInline(admin.TabularInline):
    model = BatchParameter
    extra = 0


class BatchAdmin(admin.ModelAdmin):
    list_display = ("id", "site", "name", "script")
    fields = ("site", "name", "script")
    list_filter = ("site",)
    search_fields = ("name", "site__name", "script__name")
    inlines = [JobInline, BatchParameterInline]


class InputInline(admin.TabularInline):
    model = Input
    extra = 0


class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_global",
        "is_security_script",
        "is_hidden",
        "site",
        "jobs_per_site",
        "jobs_per_site_for_the_last_year",
        "associations_to_groups_per_site",
        "uid",
        "executable_code",
    )
    filter_horizontal = ("tags",)
    readonly_fields = ("user_created", "user_modified")
    search_fields = ("name", "executable_code")
    inlines = [InputInline]

    def is_global(self, obj):
        return obj.is_global

    is_global.boolean = True
    is_global.short_description = _("Global")
    is_global.admin_order_field = "site"

    def jobs_per_site(self, obj):
        sites = Site.objects.filter(batches__script=obj).annotate(
            num_jobs=Count("batches__jobs")
        )

        return format_html_join(
            "\n", "<p>{} - {}</p>", ([(site.name, site.num_jobs) for site in sites])
        )

    jobs_per_site.short_description = _("Jobs per site")

    def jobs_per_site_for_the_last_year(self, obj):
        now = timezone.now()
        a_year_ago = now.replace(year=now.year - 1)

        sites = Site.objects.filter(
            batches__script=obj, batches__jobs__started__gte=a_year_ago
        ).annotate(num_jobs=Count("batches__jobs"))

        return format_html_join(
            "\n", "<p>{} - {}</p>", ([(site.name, site.num_jobs) for site in sites])
        )

    jobs_per_site_for_the_last_year.short_description = _(
        "Jobs per Site for the last year"
    )

    def associations_to_groups_per_site(self, obj):
        sites = Site.objects.all()
        pairs = []
        for site in sites:
            count = AssociatedScript.objects.filter(
                script=obj.id, group__site=site.id
            ).count()
            if count > 0:
                pairs.append(tuple((site, count)))

        return format_html_join(
            "\n", "<p>{} - {}</p>", ([(pair[0], pair[1]) for pair in pairs])
        )


class PCInlineForSiteAdmin(admin.TabularInline):
    model = PC
    fields = ("name", "uid")
    readonly_fields = ("name", "uid")
    extra = 0

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj):
        return False


class FeaturePermissionInlineForSiteAdmin(admin.TabularInline):
    model = FeaturePermission.sites.through
    extra = 0


class SiteAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "number_of_computers",
        "created",
        "number_of_borgerpc_computers",
        "number_of_kioskpc_computers",
        "paid_for_access_until",
    )
    search_fields = ("name",)
    inlines = (
        FeaturePermissionInlineForSiteAdmin,
        PCInlineForSiteAdmin,
    )
    readonly_fields = ("created",)

    def number_of_borgerpc_computers(self, obj):
        borgerpc_computers_count = (
            PC.objects.filter(site=obj)
            .filter(configuration__entries__value="os2borgerpc")
            .count()
        )

        return borgerpc_computers_count

    def number_of_kioskpc_computers(self, obj):
        kioskpc_computers_count = (
            PC.objects.filter(site=obj)
            .filter(configuration__entries__value="os2borgerpc kiosk")
            .count()
        )

        return kioskpc_computers_count

    def number_of_computers(self, obj):
        return obj.pcs.count()

    number_of_computers.short_description = _("Number of computers")
    number_of_kioskpc_computers.short_description = _("Number of KioskPC computers")
    number_of_borgerpc_computers.short_description = _("Number of BorgerPC computers")


class FeaturePermissionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "uid",
    )
    list_filter = ("name",)
    search_fields = ("name", "uid")


class PCAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "uid",
        "site_link",
        "is_activated",
        "last_seen",
        "created",
        "os2borgerpc_client_version",
    )
    list_filter = (
        "site",
        "is_activated",
    )
    search_fields = ("name", "uid")
    readonly_fields = ("created",)

    def site_link(self, obj):
        link = reverse("admin:system_site_change", args=[obj.site_id])
        return mark_safe(f'<a href="{link}">{escape(obj.site.__str__())}</a>')

    def os2borgerpc_client_version(self, obj):
        return obj.configuration.get("_os2borgerpc.client_version")

    site_link.short_description = _("Site")
    site_link.admin_order_field = "site"

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        # PC UID is generated from a hashed MAC address
        # so by hashing the input we allow searching by MAC address.
        maybe_uid_hash = md5(search_term.encode("utf-8").lower()).hexdigest()
        queryset |= self.model.objects.filter(uid=maybe_uid_hash)
        return queryset, may_have_duplicates


class JobAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "status",
        "user",
        "pc",
        "created",
        "started",
        "finished",
    )
    list_filter = ("status",)
    search_fields = ("batch__script__name", "user__username", "pc__name")
    readonly_fields = ("created", "started", "finished")


class ScriptTagAdmin(admin.ModelAdmin):
    pass


class ImageVersionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "platform", "image_version", "os", "release_date")


class SecurityProblemAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "level", "security_script")


class EventRuleServerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "site",
        "level",
        "monitor_period_start",
        "monitor_period_end",
        "maximum_offline_period",
    )


class SecurityEventAdmin(admin.ModelAdmin):
    list_display = (
        "problem",
        "event_rule_server",
        "get_site",
        "occurred_time",
        "reported_time",
        "pc",
        "status",
    )
    search_fields = ("pc__site__name", "problem__name", "pc__name", "status")
    list_filter = (
        ("problem__security_script", admin.RelatedOnlyFieldListFilter),
        ("occurred_time", admin.DateFieldListFilter),
        ("reported_time", admin.DateFieldListFilter),
        "status",
        "pc__site",
    )

    @admin.display(description="Site", ordering="pc__site")
    def get_site(self, obj):
        return obj.pc.site


class AssociatedScriptParameterInline(admin.TabularInline):
    model = AssociatedScriptParameter
    extra = 0


class AssociatedScriptAdmin(admin.ModelAdmin):
    list_display = ("script", "get_site", "group", "position")
    search_fields = ("script__name",)
    inlines = [AssociatedScriptParameterInline]

    @admin.display(description="Site", ordering="group__site")
    def get_site(self, obj):
        return obj.group.site


class AssociatedScriptParameterAdmin(admin.ModelAdmin):
    list_display = (
        "associated_script",
        "input",
        "string_value",
        "file_value",
        "get_site",
    )
    search_fields = ("associated_script__script__name",)

    @admin.display(description="Site", ordering="associated_script__group__site")
    def get_site(self, obj):
        return obj.associated_script.group.site


class CitizenAdmin(admin.ModelAdmin):
    list_display = ("citizen_id", "last_successful_login", "site")
    search_fields = ("citizen_id",)


class ChangelogAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "version",
        "created",
        "updated",
    )
    search_fields = (
        "title",
        "version",
    )
    filter_horizontal = ("tags",)


class ChangelogTagAdmin(admin.ModelAdmin):
    pass


class ChangelogCommentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created",
        "changelog",
        "content",
    )
    readonly_fields = (
        "created",
        "user",
        "parent_comment",
        "changelog",
    )


class WakeWeekPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "enabled",
        "site",
        "sleep_state",
        "monday_on",
        "monday_off",
        "tuesday_on",
        "tuesday_off",
        "wednesday_on",
        "wednesday_off",
        "thursday_on",
        "thursday_off",
        "friday_on",
        "friday_off",
        "saturday_on",
        "saturday_off",
        "sunday_on",
        "sunday_off",
    )
    inlines = [PCGroupInline]
    filter_horizontal = ("wake_change_events",)
    list_filter = ("site",)
    search_fields = ("name",)


class WakeWeekPlanInline(admin.TabularInline):
    model = WakeWeekPlan.wake_change_events.through
    extra = 0


class WakeChangeEventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "date_start",
        "date_end",
        "time_start",
        "time_end",
        "site",
    )
    inlines = [WakeWeekPlanInline]
    list_filter = ("site",)


ar = admin.site.register

ar(AssociatedScript, AssociatedScriptAdmin)
ar(AssociatedScriptParameter, AssociatedScriptParameterAdmin)
ar(Batch, BatchAdmin)
ar(BatchParameter)
ar(Changelog, ChangelogAdmin)
ar(ChangelogComment, ChangelogCommentAdmin)
ar(ChangelogTag, ChangelogTagAdmin)
ar(Citizen, CitizenAdmin)
ar(Configuration, ConfigurationAdmin)
ar(FeaturePermission, FeaturePermissionAdmin)
ar(ImageVersion, ImageVersionAdmin)
ar(Job, JobAdmin)
ar(EventRuleServer, EventRuleServerAdmin)
ar(PC, PCAdmin)
ar(PCGroup, PCGroupAdmin)
ar(Script, ScriptAdmin)
ar(ScriptTag, ScriptTagAdmin)
ar(SecurityEvent, SecurityEventAdmin)
ar(SecurityProblem, SecurityProblemAdmin)
ar(Site, SiteAdmin)
ar(WakeChangeEvent, WakeChangeEventAdmin)
ar(WakeWeekPlan, WakeWeekPlanAdmin)
