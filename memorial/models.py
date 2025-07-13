from django.db import models
from django.urls import reverse


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
    
    def get_absolute_url(self):
        return reverse('person-detail', kwargs={'pk': self.pk})