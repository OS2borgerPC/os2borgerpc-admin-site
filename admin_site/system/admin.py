
from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html_join, escape, mark_safe
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from hashlib import md5

from system.models import (
    Configuration,
    ConfigurationEntry,
    PackageList,
    Package,
    Site,
    Distribution,
    PCGroup,
    PC,
    CustomPackages,
    PackageInstallInfo,
    PackageStatus,
    ImageVersion,
    SecurityEvent,
    SecurityProblem,
    Script,
    Batch,
    Job,
    Input,
    BatchParameter,
    AssociatedScript,
    AssociatedScriptParameter,
    ScriptTag,
)

ar = admin.site.register


class PackageInstallInfoInline(admin.TabularInline):
    model = PackageInstallInfo
    extra = 3


class PackageStatusInline(admin.TabularInline):
    model = PackageStatus
    extra = 3


class ConfigurationEntryInline(admin.TabularInline):
    model = ConfigurationEntry
    extra = 3


class PackageListAdmin(admin.ModelAdmin):
    inlines = [PackageStatusInline]


class CustomPackagesAdmin(admin.ModelAdmin):
    inlines = [PackageInstallInfoInline]


class ConfigurationAdmin(admin.ModelAdmin):
    fields = ['name']
    inlines = [ConfigurationEntryInline]


class PCInline(admin.TabularInline):
    model = PC.pc_groups.through
    extra = 3


class PCGroupAdmin(admin.ModelAdmin):
    inlines = [PCInline]


class JobInline(admin.TabularInline):
    fields = ['pc']
    model = Job
    extra = 1


class BatchParameterInline(admin.TabularInline):
    model = BatchParameter
    extra = 1


class BatchAdmin(admin.ModelAdmin):
    fields = ['site', 'name', 'script']
    inlines = [JobInline, BatchParameterInline]


class AssociatedScriptParameterInline(admin.TabularInline):
    model = AssociatedScriptParameter
    extra = 1


class InputInline(admin.TabularInline):
    model = Input
    extra = 1


class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_global",
        "is_security_script",
        "site",
        "jobs_per_site",
        "jobs_per_site_for_the_last_year",
        "deleted",
    )
    filter_horizontal = ("tags",)
    readonly_fields = ("user_created", "user_modified")
    list_filter = ("deleted",)
    search_fields = ("name",)
    inlines = [InputInline]

    def is_global(self, obj):
        return obj.is_global
    is_global.boolean = True
    is_global.short_description = _("Global")

    def jobs_per_site(self, obj):
        sites = Site.objects.filter(
            batches__script=obj
        ).annotate(num_jobs=Count("batches__jobs"))

        return format_html_join(
            "\n",
            "<p>{} - {}</p>",
            ([(site.name, site.num_jobs) for site in sites])
        )

    jobs_per_site.short_description = _("Jobs per site")

    def jobs_per_site_for_the_last_year(self, obj):
        now = timezone.now()
        a_year_ago = now.replace(year=now.year-1)

        sites = Site.objects.filter(
            batches__script=obj,
            batches__jobs__started__gte=a_year_ago
        ).annotate(num_jobs=Count("batches__jobs"))

        return format_html_join(
            "\n",
            "<p>{} - {}</p>",
            ([(site.name, site.num_jobs) for site in sites])
        )

    jobs_per_site_for_the_last_year.short_description = _(
        "Jobs per Site for the last year"
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


class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "number_of_computers")
    search_fields = ("name",)
    inlines = (PCInlineForSiteAdmin,)

    def number_of_computers(self, obj):
        return obj.pcs.count()
    number_of_computers.short_description = _('Number of computers')


class PCAdmin(admin.ModelAdmin):
    list_display = ("name", "uid", "site_link", "is_active", "last_seen")
    search_fields = ("name", "uid")

    def site_link(self, obj):
        link = reverse("admin:system_site_change", args=[obj.site_id])
        return mark_safe(
            f'<a href="{link}">{escape(obj.site.__str__())}</a>'
        )

    site_link.short_description = _('Site')
    site_link.admin_order_field = 'site'

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term,
        )
        # PC UID is generated from a hashed MAC address
        # so by reversing the process we allow searching by MAC address.
        maybe_uid_hash = md5(search_term.encode('utf-8')).hexdigest()
        queryset |= self.model.objects.filter(uid=maybe_uid_hash)
        return queryset, may_have_duplicates


class JobAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "user", "pc")
    search_fields = ("user", "pc")


class ScriptTagAdmin(admin.ModelAdmin):
    pass


ar(Configuration, ConfigurationAdmin)
ar(PackageList)
ar(CustomPackages, CustomPackagesAdmin)
ar(Site, SiteAdmin)
ar(Distribution)
ar(PCGroup, PCGroupAdmin)
ar(PC, PCAdmin)
ar(Package)
ar(ImageVersion)
# Job related stuff
ar(Script, ScriptAdmin)
ar(ScriptTag, ScriptTagAdmin)
ar(Batch, BatchAdmin)
ar(Job, JobAdmin)
ar(BatchParameter)
ar(AssociatedScript)
ar(AssociatedScriptParameter)
ar(SecurityEvent)
ar(SecurityProblem)
