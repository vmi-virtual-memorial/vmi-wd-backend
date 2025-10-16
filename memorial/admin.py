# memorial/admin.py
from django.contrib import admin
from django import forms
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Conflict, Person, Contribution
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
    list_display = ['display_name', 'class_year', 'conflict', 'rank', 'get_death_date_display', 'has_pdf', 'has_description', 'contribution_count']
    list_filter = ['conflict', 'class_year', 'rank', 'death_date_precision']
    search_fields = ['first_name', 'last_name', 'unit']
    autocomplete_fields = ['conflict']
    
    fieldsets = (
        ('Name', {
            'fields': ('first_name', 'middle_name', 'last_name', 'suffix')
        }),
        ('VMI Information', {
            'fields': ('class_year', 'class_letter')
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
    
    def contribution_count(self, obj):
        """Show number of contributions"""
        total = obj.contributions.count()
        approved = obj.contributions.filter(status='approved').count()
        pending = obj.contributions.filter(status='pending').count()
        
        if pending > 0:
            return format_html(
                '<span style="color: green;">{}</span> / '
                '<span style="color: orange;">{}</span> / '
                '<span>{}</span>',
                approved, pending, total
            )
        return f"{approved} / {total}"
    contribution_count.short_description = 'Contributions (A/P/T)'


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'person_link', 'contributor_email', 'content_type', 
        'status_badge', 'submitted_at', 'reviewed_by'
    ]
    list_filter = ['status', 'content_type', 'submitted_at', 'reviewed_at']
    search_fields = [
        'person__first_name', 'person__last_name', 
        'contributor_email', 'content_text'
    ]
    readonly_fields = [
        'person', 'contributor_email', 'content_type', 'content_text',
        'image_preview', 'submitted_at', 'reviewed_at', 'reviewed_by'
    ]
    
    fieldsets = (
        ('Contribution Info', {
            'fields': ('person', 'contributor_email', 'submitted_at')
        }),
        ('Content', {
            'fields': ('content_type', 'content_text', 'image_preview')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_at', 'reviewed_by', 'rejection_reason')
        })
    )
    
    actions = ['approve_contributions', 'reject_contributions']
    
    def person_link(self, obj):
        """Link to person in admin"""
        url = reverse('admin:memorial_person_change', args=[obj.person.id])
        return format_html('<a href="{}">{}</a>', url, obj.person.full_display_name)
    person_link.short_description = 'Person'
    
    def status_badge(self, obj):
        """Color-coded status badge"""
        colors = {
            'pending': '#FFA500',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def image_preview(self, obj):
        """Preview of uploaded image"""
        if obj.content_image:
            return mark_safe(
                f'<img src="{obj.content_image.url}" '
                f'style="max-width: 300px; max-height: 300px;" />'
            )
        return "No image"
    image_preview.short_description = 'Image Preview'
    
    def approve_contributions(self, request, queryset):
        """Bulk approve action"""
        count = 0
        for contribution in queryset.filter(status='pending'):
            contribution.approve(request.user)
            count += 1
        self.message_user(request, f"{count} contributions approved.")
    approve_contributions.short_description = "Approve selected contributions"
    
    def reject_contributions(self, request, queryset):
        """Bulk reject action"""
        count = 0
        for contribution in queryset.filter(status='pending'):
            contribution.reject(request.user, "Bulk rejection")
            count += 1
        self.message_user(request, f"{count} contributions rejected.")
    reject_contributions.short_description = "Reject selected contributions"
    
    def has_add_permission(self, request):
        """Prevent manual addition through admin"""
        return False