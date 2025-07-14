# memorial/admin.py
from django.contrib import admin
from django import forms
from django.core.files.storage import default_storage
from django.conf import settings
from .models import Conflict, Person
import os


class PersonAdminForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        help_text="Upload a PDF file for this person's memorial"
    )
    
    class Meta:
        model = Person
        fields = '__all__'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle PDF upload
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            # Add environment prefix to separate dev/prod files
            env_prefix = 'dev/' if settings.DEBUG else 'prod/'
            
            # Create a meaningful filename
            filename = f"{env_prefix}memorials/{instance.last_name}_{instance.first_name}_{instance.id or 'new'}.pdf"
            filename = filename.replace(' ', '_').lower()
            
            # Save to S3 (or local storage in development)
            path = default_storage.save(filename, pdf_file)
            instance.pdf_key = path
        
        if commit:
            instance.save()
        return instance


@admin.register(Conflict)
class ConflictAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_year', 'end_year', 'casualty_count', 'order']
    list_editable = ['order']
    search_fields = ['name']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    form = PersonAdminForm
    list_display = ['display_name', 'class_year', 'conflict', 'rank', 'date_of_death', 'has_pdf']
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
            'fields': ('pdf_file', 'pdf_key'),
            'description': 'Upload a PDF or view the current S3 key'
        }),
    )
    
    readonly_fields = ['pdf_key']
    
    def has_pdf(self, obj):
        return bool(obj.pdf_key)
    has_pdf.boolean = True
    has_pdf.short_description = 'Has PDF'