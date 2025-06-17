from django.contrib import admin
from .models import WorkFormDocument, WorkFormEntry

@admin.register(WorkFormDocument)
class WorkFormDocumentAdmin(admin.ModelAdmin):
    list_display = ('folder_name', 'docx_file', 'preview_image', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('folder_name',)

@admin.register(WorkFormEntry)
class WorkFormEntryAdmin(admin.ModelAdmin):
    list_display = ('document', 'work_date', 'location', 'device', 'created_at')
    list_filter = ('work_date', 'location', 'device')
    search_fields = ('location', 'device')