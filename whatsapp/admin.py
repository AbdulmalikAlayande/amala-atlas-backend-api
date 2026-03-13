from django.contrib import admin

from whatsapp.models import WhatsAppSession


@admin.register(WhatsAppSession)
class WhatsAppSessionAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'state', 'created_at')
    list_filter = ('state',)
    search_fields = ('phone_number',)
