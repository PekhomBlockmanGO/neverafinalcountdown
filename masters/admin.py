from django.contrib import admin
from django.utils.html import mark_safe
from .models import Site, Area, Location, SpecificArea


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'active')
    list_filter = ('active',)
    search_fields = ('name',)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'site')
    list_filter = ('site',)
    search_fields = ('name',)


@admin.register(SpecificArea)
class SpecificAreaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'area', 'get_site', 'floor',
        'specific_area', 'qr_enabled', 'qr_preview',
    )
    list_filter = ('area', 'specific_area', 'qr_enabled')
    search_fields = ('name', 'qr_token')
    readonly_fields = ('qr_token', 'qr_preview')
    actions = ['regenerate_qr_codes']

    def get_site(self, obj):
        return obj.area.site.name if obj.area and obj.area.site else "—"
    get_site.short_description = 'Site'
    get_site.admin_order_field = 'area__site__name'

    def qr_preview(self, obj):
        if obj.qr_image:
            return mark_safe(
                f'<a href="{obj.qr_image.url}" target="_blank">'
                f'<img src="{obj.qr_image.url}" width="60" height="60" '
                f'style="border-radius:6px;border:1px solid #ddd;"/></a>'
            )
        return "—"
    qr_preview.short_description = 'QR Preview'

    @admin.action(description="Regenerate QR codes for selected locations")
    def regenerate_qr_codes(self, request, queryset):
        count = 0
        for location in queryset:
            location.regenerate_qr()
            count += 1
        self.message_user(request, f"Regenerated QR codes for {count} location(s).")
