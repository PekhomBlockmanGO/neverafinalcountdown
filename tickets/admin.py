from django.contrib import admin
from .models import Ticket, TicketLog


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'location', 'area', 'specific_area',
        'category', 'priority', 'status', 'source', 'created_at',
    )
    list_filter = ('status', 'priority', 'category', 'source', 'site')
    search_fields = ('description', 'reporter_phone', 'reporter_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(TicketLog)
class TicketLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'status', 'timestamp', 'remarks')
    list_filter = ('status',)
    search_fields = ('ticket__id', 'remarks')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
