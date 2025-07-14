from rest_framework import serializers
from .models import Conflict, Person


class PersonListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing people"""
    display_name = serializers.ReadOnlyField()
    full_display_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Person
        fields = ['id', 'display_name', 'full_display_name', 'rank', 'unit', 'class_year', 'death_description']


class PersonDetailSerializer(serializers.ModelSerializer):
    """Full details for individual person"""
    display_name = serializers.ReadOnlyField()
    full_display_name = serializers.ReadOnlyField()
    conflict_name = serializers.CharField(source='conflict.name', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Person
        fields = [
            'id', 'first_name', 'middle_name', 'last_name', 'suffix',
            'display_name', 'full_display_name', 'class_year', 'rank', 'unit', 
            'date_of_death', 'death_description', 'conflict', 'conflict_name', 
            'pdf_key', 'pdf_url'
        ]
    
    def get_pdf_url(self, obj):
        """Generate S3 URL or placeholder"""
        if obj.pdf_key:
            # TODO: Generate actual S3 presigned URL
            return f"/api/memorial/persons/{obj.id}/pdf/"
        return None


class PersonSearchSerializer(serializers.ModelSerializer):
    """Serializer for search results"""
    display_name = serializers.ReadOnlyField()
    full_display_name = serializers.ReadOnlyField()
    conflict_name = serializers.CharField(source='conflict.name', read_only=True)
    conflict_id = serializers.IntegerField(source='conflict.id', read_only=True)
    
    class Meta:
        model = Person
        fields = [
            'id', 'display_name', 'full_display_name', 'class_year',
            'rank', 'unit', 'date_of_death', 'conflict_name', 'conflict_id'
        ]


class ConflictSerializer(serializers.ModelSerializer):
    """Conflict with casualty count"""
    casualty_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Conflict
        fields = [
            'id', 'name', 'start_year', 'end_year', 
            'description', 'casualty_count', 'order'
        ]


class ConflictDetailSerializer(serializers.ModelSerializer):
    """Conflict with list of casualties"""
    casualty_count = serializers.ReadOnlyField()
    casualties = PersonListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conflict
        fields = [
            'id', 'name', 'start_year', 'end_year', 
            'description', 'casualty_count', 'order', 'casualties'
        ]