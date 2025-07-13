# memorial/admin.py
from django.contrib import admin
from .models import Conflict, Person


@admin.register(Conflict)
class ConflictAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_year', 'end_year', 'casualty_count', 'order']
    list_editable = ['order']
    search_fields = ['name']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'class_year', 'conflict', 'rank', 'date_of_death']
    list_filter = ['conflict', 'class_year', 'rank']
    search_fields = ['first_name', 'last_name', 'unit']
    autocomplete_fields = ['conflict']
    
    fieldsets = (
        ('Name', {
            'fields': ('first_name', 'middle_name', 'last_name', 'suffix')
        }),
        ('VMI Information', {
            'fields': ('class_year',)
        }),
        ('Military Information', {
            'fields': ('conflict', 'rank', 'unit', 'date_of_death')
        }),
        ('Memorial Content', {
            'fields': ('pdf_key',)
        }),
    )