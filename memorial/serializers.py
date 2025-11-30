from rest_framework import serializers
from .models import Conflict, Person, Contribution, Award, PersonAward


class PersonListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing people"""
    display_name = serializers.ReadOnlyField()
    full_display_name = serializers.ReadOnlyField()
    death_date_display = serializers.ReadOnlyField()
    has_awards = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ['id', 'display_name', 'full_display_name', 'rank', 'unit', 'class_year', 'class_letter', 'death_description', 'death_date_display', 'has_awards']

    def get_has_awards(self, obj):
        return obj.person_awards.exists()


class PersonDetailSerializer(serializers.ModelSerializer):
    """Full details for individual person"""
    display_name = serializers.ReadOnlyField()
    full_display_name = serializers.ReadOnlyField()
    conflict_name = serializers.CharField(source='conflict.name', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    death_date_display = serializers.ReadOnlyField()

    class Meta:
        model = Person
        fields = [
            'id', 'first_name', 'middle_name', 'last_name', 'suffix',
            'display_name', 'full_display_name', 'class_year', 'class_letter', 'rank', 'unit',
            'date_of_death', 'death_date_precision', 'death_date_display',
            'death_description', 'conflict', 'conflict_name',
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
    death_date_display = serializers.ReadOnlyField()
    has_awards = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            'id', 'display_name', 'full_display_name', 'class_year', 'class_letter',
            'rank', 'unit', 'date_of_death', 'death_date_display',
            'conflict_name', 'conflict_id', 'has_awards'
        ]

    def get_has_awards(self, obj):
        return obj.person_awards.exists()


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


# Contribution serializers
class ContributionSerializer(serializers.ModelSerializer):
    """Base serializer for contributions"""
    contributor_email = serializers.EmailField(required=True)
    reviewed_by_username = serializers.CharField(
        source='reviewed_by.username', 
        read_only=True
    )
    
    class Meta:
        model = Contribution
        fields = [
            'id', 'person', 'contributor_email', 'content_type',
            'content_text', 'content_image', 'status', 'submitted_at',
            'reviewed_at', 'reviewed_by', 'reviewed_by_username',
            'rejection_reason'
        ]
        read_only_fields = [
            'id', 'status', 'submitted_at', 'reviewed_at', 
            'reviewed_by', 'rejection_reason'
        ]


class ContributionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating contributions"""
    content_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Contribution
        fields = ['contributor_email', 'content_type', 'content_text', 'content_image']
    
    def validate(self, data):
        """Ensure content matches content_type"""
        content_type = data.get('content_type')
        
        if content_type in ['text', 'both'] and not data.get('content_text'):
            raise serializers.ValidationError(
                "Text content is required for text contributions"
            )
        
        if content_type in ['image', 'both'] and not data.get('content_image'):
            raise serializers.ValidationError(
                "Image is required for image contributions"
            )
        
        return data


class ContributionPublicSerializer(serializers.ModelSerializer):
    """Public view of approved contributions only"""
    contributor_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Contribution
        fields = [
            'id', 'content_type', 'content_text', 'content_image',
            'submitted_at', 'contributor_display'
        ]
    
    def get_contributor_display(self, obj):
        """Partially mask email for privacy"""
        email = obj.contributor_email
        parts = email.split('@')
        if len(parts) == 2:
            name = parts[0]
            if len(name) > 2:
                masked = name[0] + '*' * (len(name) - 2) + name[-1]
            else:
                masked = name[0] + '*'
            return f"{masked}@{parts[1]}"
        return "Anonymous"


class ContributionReviewSerializer(serializers.Serializer):
    """Serializer for approving/rejecting contributions"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                "Rejection reason is required when rejecting a contribution"
            )
        return data


class PersonAwardSerializer(serializers.ModelSerializer):
    """Serializer for person awards (used in person detail)"""
    award_id = serializers.IntegerField(source='award.id', read_only=True)
    award_name = serializers.CharField(source='award.name', read_only=True)
    award_image_filename = serializers.CharField(source='award.image_filename', read_only=True)

    class Meta:
        model = PersonAward
        fields = [
            'award_id', 'award_name', 'award_image_filename',
            'count', 'date_awarded', 'citation'
        ]


class PersonDetailSerializerWithContributions(PersonDetailSerializer):
    """Person details including approved contributions and awards"""
    contributions = ContributionPublicSerializer(many=True, read_only=True)

    class Meta(PersonDetailSerializer.Meta):
        fields = PersonDetailSerializer.Meta.fields + ['contributions', 'awards']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Only show approved contributions
        data['contributions'] = ContributionPublicSerializer(
            instance.contributions.filter(status='approved'),
            many=True
        ).data
        # Include awards
        data['awards'] = PersonAwardSerializer(
            instance.person_awards.all(),
            many=True
        ).data
        return data


# Award serializers
class AwardListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing awards"""
    recipient_count = serializers.ReadOnlyField()
    total_awards_given = serializers.ReadOnlyField()

    class Meta:
        model = Award
        fields = [
            'id', 'name', 'short_description', 'image_filename',
            'recipient_count', 'total_awards_given', 'order'
        ]


class AwardRecipientSerializer(serializers.ModelSerializer):
    """Serializer for recipients shown on award detail page"""
    person_id = serializers.IntegerField(source='person.id', read_only=True)
    display_name = serializers.CharField(source='person.display_name', read_only=True)
    full_display_name = serializers.CharField(source='person.full_display_name', read_only=True)
    class_year = serializers.IntegerField(source='person.class_year', read_only=True)
    class_letter = serializers.CharField(source='person.class_letter', read_only=True)
    conflict_name = serializers.CharField(source='person.conflict.name', read_only=True)
    pdf_key = serializers.CharField(source='person.pdf_key', read_only=True)

    class Meta:
        model = PersonAward
        fields = [
            'person_id', 'display_name', 'full_display_name',
            'class_year', 'class_letter', 'conflict_name', 'pdf_key',
            'count', 'date_awarded', 'citation'
        ]


class AwardDetailSerializer(serializers.ModelSerializer):
    """Full award details with recipients list"""
    recipient_count = serializers.ReadOnlyField()
    total_awards_given = serializers.ReadOnlyField()
    recipients = AwardRecipientSerializer(source='person_awards', many=True, read_only=True)

    class Meta:
        model = Award
        fields = [
            'id', 'name', 'short_description', 'long_description',
            'image_filename', 'recipient_count', 'total_awards_given',
            'order', 'recipients'
        ]