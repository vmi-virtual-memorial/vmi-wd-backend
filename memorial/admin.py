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
        widgets = {
            'death_description': forms.Textarea(attrs={'rows': 4, 'cols': 80}),
            'date_of_death': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for date fields
        self.fields['date_of_death'].help_text = (
            "Enter the full date. Use January 1st for year-only dates, "
            "and the 1st of the month for month-year dates."
        )
        self.fields['death_date_precision'].help_text = (
            "Select the precision of the date entered above. "
            "This controls how the date is displayed on the site."
        )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle PDF upload
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            # Save instance first to get an ID if it's new
            if not instance.id:
                instance.save()
            
            # Add environment prefix to separate dev/prod files
            env_prefix = 'dev/' if settings.DEBUG else 'prod/'
            
            # Create a meaningful filename with actual ID
            filename = f"{env_prefix}memorials/{instance.last_name}_{instance.first_name}_{instance.id}.pdf"
            filename = filename.replace(' ', '_').lower()
            
            # Delete old file if pdf_key already exists and is different
            if instance.pdf_key and instance.pdf_key != filename:
                try:
                    default_storage.delete(instance.pdf_key)
                except Exception:
                    pass  # Ignore errors when deleting old files
            
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
    list_display = ['display_name', 'class_year', 'conflict', 'rank', 'get_death_date_display', 'has_pdf', 'has_description']
    list_filter = ['conflict', 'class_year', 'rank', 'death_date_precision']
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
            'fields': ('conflict', 'rank', 'unit')
        }),
        ('Death Information', {
            'fields': ('date_of_death', 'death_date_precision'),
            'description': 'For partial dates: Use January 1st for year-only, and the 1st of the month for month-year dates.'
        }),
        ('Death Details', {
            'fields': ('death_description',),
            'classes': ('wide',),  # Makes the text field wider
        }),
        ('Memorial Content', {
            'fields': ('pdf_file', 'pdf_key'),
            'description': 'Upload a PDF or view the current S3 key'
        }),
    )
    
    readonly_fields = ['pdf_key']
    
    def get_death_date_display(self, obj):
        """Display death date in list view"""
        return obj.death_date_display or 'Unknown'
    get_death_date_display.short_description = 'Date of Death'
    get_death_date_display.admin_order_field = 'date_of_death'
    
    def has_pdf(self, obj):
        return bool(obj.pdf_key)
    has_pdf.boolean = True
    has_pdf.short_description = 'Has PDF'
    
    def has_description(self, obj):
        return bool(obj.death_description)
    has_description.boolean = True
    has_description.short_description = 'Has Description'