from django.db import models
from django.urls import reverse
from django.utils import timezone


class Conflict(models.Model):
    """Represents a military conflict/war"""
    name = models.CharField(max_length=200)  # e.g., "World War I", "Vietnam War"
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True)  # null for ongoing
    description = models.TextField(blank=True)  # Optional summary
    order = models.IntegerField(default=0)  # for custom sorting
    
    class Meta:
        ordering = ['order', 'start_year']
    
    def __str__(self):
        if self.end_year:
            return f"{self.name} ({self.start_year}-{self.end_year})"
        return f"{self.name} ({self.start_year}-present)"
    
    @property
    def casualty_count(self):
        return self.casualties.count()


class Person(models.Model):
    """Represents a person who died in service"""
    # Name fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    suffix = models.CharField(max_length=20, blank=True)  # Jr., III, etc.
    
    # VMI info
    class_year = models.IntegerField(
        null=True, 
        blank=True,
        help_text="VMI graduation year (e.g., 1965)"
    )
    
    # Military info
    conflict = models.ForeignKey(
        Conflict, 
        on_delete=models.CASCADE, 
        related_name='casualties'
    )
    rank = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=200, blank=True)
    date_of_death = models.DateField(null=True, blank=True)
    
    # Date precision field
    death_date_precision = models.CharField(
        max_length=10,
        choices=[
            ('day', 'Day'),
            ('month', 'Month'),
            ('year', 'Year'),
        ],
        default='day',
        blank=True,
        help_text="Precision of the death date (year only, month and year, or full date)"
    )
    
    # Death details
    death_description = models.TextField(
        blank=True,
        help_text="Description of how this person died (e.g., 'Killed in action during the Battle of Normandy')"
    )
    
    # Memorial content
    pdf_key = models.CharField(
        max_length=500, 
        blank=True,
        help_text="S3 key for the memorial PDF"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = "People"
    
    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}"
        if self.middle_name:
            full_name = f"{self.first_name} {self.middle_name} {self.last_name}"
        if self.suffix:
            full_name = f"{full_name} {self.suffix}"
        if self.class_year:
            full_name = f"{full_name} '{str(self.class_year)[2:]}"  # e.g., John Doe '65
        return full_name
    
    @property
    def display_name(self):
        """Formatted name for display"""
        name_parts = []
        if self.rank:
            name_parts.append(self.rank)
        name_parts.append(self.first_name)
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        if self.suffix:
            name_parts.append(self.suffix)
        return ' '.join(name_parts)
    
    @property
    def full_display_name(self):
        """Display name with class year"""
        name = self.display_name
        if self.class_year:
            name = f"{name} '{str(self.class_year)[2:]}"
        return name
    
    @property
    def death_date_display(self):
        """Display death date according to precision"""
        if not self.date_of_death:
            return None
        
        if self.death_date_precision == 'year':
            return str(self.date_of_death.year)
        elif self.death_date_precision == 'month':
            return self.date_of_death.strftime('%B %Y')
        else:  # 'day' - full precision
            return self.date_of_death.strftime('%B %d, %Y')
    
    def get_absolute_url(self):
        return reverse('person-detail', kwargs={'pk': self.pk})


class ContributionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class Contribution(models.Model):
    """Community contributions for person records"""
    
    # Link to person
    person = models.ForeignKey(
        'Person', 
        on_delete=models.CASCADE, 
        related_name='contributions'
    )
    
    # Contributor info
    contributor_email = models.EmailField(
        help_text="Email of the person submitting this contribution"
    )
    
    # Content
    content_type = models.CharField(
        max_length=10,
        choices=[
            ('text', 'Text'),
            ('image', 'Image'),
            ('both', 'Both'),
        ],
        default='text'
    )
    content_text = models.TextField(
        blank=True,
        help_text="Text content of the contribution"
    )
    content_image = models.ImageField(
        upload_to='contributions/',
        blank=True,
        null=True,
        help_text="Image contribution"
    )
    
    # Moderation
    status = models.CharField(
        max_length=10,
        choices=ContributionStatus.choices,
        default=ContributionStatus.PENDING
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Review info
    reviewed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_contributions'
    )
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['person', 'status']),
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"Contribution for {self.person} by {self.contributor_email} ({self.status})"
    
    def approve(self, user):
        """Approve this contribution"""
        self.status = ContributionStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
    
    def reject(self, user, reason=''):
        """Reject this contribution"""
        self.status = ContributionStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()