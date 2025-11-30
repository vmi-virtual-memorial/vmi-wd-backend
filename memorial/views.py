from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from PIL import Image
import io

from .models import Conflict, Person, Contribution, Award
from .serializers import (
    ConflictSerializer, ConflictDetailSerializer,
    PersonListSerializer, PersonDetailSerializer,
    PersonSearchSerializer, PersonDetailSerializerWithContributions,
    ContributionSerializer, ContributionCreateSerializer,
    ContributionPublicSerializer, ContributionReviewSerializer,
    AwardListSerializer, AwardDetailSerializer
)


# Constants for contribution validation
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
MAX_IMAGE_DIMENSIONS = (4000, 4000)  # Max width/height


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for conflicts"""
    queryset = Conflict.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConflictDetailSerializer
        return ConflictSerializer


class AwardViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for awards/decorations"""
    queryset = Award.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AwardDetailSerializer
        return AwardListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Optional: Filter by conflict (awards given to people in that conflict)
        conflict_id = self.request.query_params.get('conflict')
        if conflict_id:
            queryset = queryset.filter(
                person_awards__person__conflict_id=conflict_id
            ).distinct()

        return queryset.order_by('order', 'name')


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for people"""
    queryset = Person.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PersonDetailSerializer
        elif self.action == 'search':
            return PersonDetailSerializer
        return PersonDetailSerializerWithContributions

    def paginate_queryset(self, queryset):
        """Override pagination to allow bypassing it with ?paginate=false"""
        paginate = self.request.query_params.get('paginate', 'true').lower()
        if paginate == 'false':
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        queryset = super().get_queryset()
        conflict_id = self.request.query_params.get('conflict', None)

        if conflict_id is not None:
            queryset = queryset.filter(conflict_id=conflict_id)
            return queryset.order_by('last_name', 'first_name')

        order_by = self.request.query_params.get('order_by', 'name')

        if order_by == 'class_year':
            return queryset.order_by('class_year', 'last_name', 'first_name')
        else:
            return queryset.order_by('last_name', 'first_name')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search and filter people"""
        queryset = Person.objects.all()

        # Memorial document filter
        has_document = request.query_params.get('has_document', '').lower()
        if has_document == 'true':
            queryset = queryset.exclude(pdf_key='').exclude(pdf_key__isnull=True)

        # Name search (across all name fields)
        search_term = request.query_params.get('q', '')
        if search_term:
            queryset = queryset.filter(
                Q(first_name__icontains=search_term) |
                Q(middle_name__icontains=search_term) |
                Q(last_name__icontains=search_term) |
                Q(suffix__icontains=search_term)
            )

        # Class year filter (can be comma-separated)
        class_years = request.query_params.get('class_year', '')
        if class_years:
            years = [int(y.strip()) for y in class_years.split(',') if y.strip().isdigit()]
            if years:
                queryset = queryset.filter(class_year__in=years)

        # Conflict filter (can be comma-separated)
        conflict_ids = request.query_params.get('conflict', '')
        if conflict_ids:
            ids = [int(id.strip()) for id in conflict_ids.split(',') if id.strip().isdigit()]
            if ids:
                queryset = queryset.filter(conflict_id__in=ids)

        # Date range filter
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        no_date = request.query_params.get('no_date', '').lower() == 'true'

        if no_date:
            queryset = queryset.filter(date_of_death__isnull=True)
        else:
            if date_from:
                try:
                    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
                    queryset = queryset.filter(date_of_death__gte=date_from_parsed)
                except ValueError:
                    pass

            if date_to:
                try:
                    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
                    queryset = queryset.filter(date_of_death__lte=date_to_parsed)
                except ValueError:
                    pass

        queryset = queryset.order_by('last_name', 'first_name')

        serializer = PersonDetailSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Get PDF for a person - generates presigned S3 URL or serves local file"""
        try:
            person = self.get_object()
        except Exception as e:
            return Response(
                {"error": "Person not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not person.pdf_key:
            return Response(
                {"error": "No PDF available for this person"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # In development, serve local files
        if settings.DEBUG:
            try:
                from django.http import FileResponse
                import os
                file_path = os.path.join(settings.MEDIA_ROOT, person.pdf_key)
                response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
                response['X-Frame-Options'] = 'SAMEORIGIN'
                return response
            except FileNotFoundError:
                return Response(
                    {"error": "PDF file not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # In production, generate presigned URL and redirect to it
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': person.pdf_key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )
            
            response = HttpResponseRedirect(presigned_url)
            response['X-Frame-Options'] = 'SAMEORIGIN'
            return response
            
        except ClientError as e:
            return Response(
                {"error": "Failed to generate PDF URL"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def contributions(self, request, pk=None):
        """Get approved contributions for a person"""
        person = self.get_object()
        contributions = person.contributions.filter(status='approved')
        serializer = ContributionPublicSerializer(contributions, many=True)
        return Response({
            'count': contributions.count(),
            'results': serializer.data
        })


class ContributionViewSet(viewsets.ModelViewSet):
    """API endpoints for contributions - Admin only except for creation"""
    queryset = Contribution.objects.all()
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        elif self.action == 'review':
            return ContributionReviewSerializer
        return ContributionSerializer
    
    def get_permissions(self):
        """
        Anyone can create contributions (with throttling)
        Only admin can list, update, or delete
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_throttles(self):
        """Apply throttling to creation"""
        if self.action == 'create':
            return [AnonRateThrottle()]
        return []
    
    def validate_image(self, image_file):
        """Validate uploaded image"""
        if image_file.size > MAX_IMAGE_SIZE:
            raise ValidationError(f"Image size must be less than {MAX_IMAGE_SIZE // 1024 // 1024}MB")
        
        if image_file.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Image type must be one of: {', '.join(ALLOWED_IMAGE_TYPES)}")
        
        try:
            img = Image.open(image_file)
            img.verify()
            
            image_file.seek(0)
            img = Image.open(image_file)
            
            if img.width > MAX_IMAGE_DIMENSIONS[0] or img.height > MAX_IMAGE_DIMENSIONS[1]:
                raise ValidationError(
                    f"Image dimensions must be less than {MAX_IMAGE_DIMENSIONS[0]}x{MAX_IMAGE_DIMENSIONS[1]}"
                )
            
            image_file.seek(0)
            
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
    
    def create(self, request, *args, **kwargs):
        """Create a new contribution with validation"""
        person_id = self.kwargs.get('person_pk')
        
        if not person_id:
            return Response(
                {"error": "Person ID not found in URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return Response(
                {"error": "Person not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate image if provided
        image = request.FILES.get('content_image')
        if image:
            try:
                self.validate_image(image)
            except ValidationError as e:
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        contribution = serializer.save(person=person)
        
        return Response(
            ContributionSerializer(contribution).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def review(self, request, pk=None):
        """Approve or reject a contribution"""
        contribution = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        
        if action == 'approve':
            contribution.approve(request.user)
        else:  # reject
            rejection_reason = serializer.validated_data.get('rejection_reason', '')
            contribution.reject(request.user, rejection_reason)
        
        return Response(ContributionSerializer(contribution).data)
    
    def list(self, request, *args, **kwargs):
        """List contributions with filtering (admin only)"""
        queryset = self.get_queryset()
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        person_id = request.query_params.get('person')
        if person_id:
            queryset = queryset.filter(person_id=person_id)
        
        queryset = queryset.order_by('-submitted_at')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })


@api_view(['GET'])
def memorial_index(request):
    """Get all conflicts with their casualties for the memorial index"""
    conflicts = Conflict.objects.all()
    data = []

    # Get sort parameter from query params (default to alphabetical)
    sort_by = request.query_params.get('sort', 'alphabetical')

    for conflict in conflicts:
        if sort_by == 'class_year':
            # Sort by class year (nulls last), then by name
            casualties = Person.objects.filter(conflict=conflict).extra(
                select={'class_year_null': 'class_year IS NULL'},
                order_by=['class_year_null', 'class_year', 'last_name', 'first_name']
            )
        else:
            # Default to alphabetical sorting
            casualties = Person.objects.filter(conflict=conflict).order_by('last_name', 'first_name')

        conflict_data = ConflictSerializer(conflict).data
        conflict_data['casualties'] = PersonDetailSerializer(casualties, many=True).data
        data.append(conflict_data)

    return Response(data)


@api_view(['GET'])
def search_filters(request):
    """Get available filter options for the search page"""
    conflicts = Conflict.objects.all().values('id', 'name', 'start_year', 'end_year')
    class_years = Person.objects.exclude(class_year__isnull=True).values_list('class_year', flat=True).distinct().order_by('class_year')
    
    return Response({
        'conflicts': list(conflicts),
        'class_years': list(class_years)
    })


# Admin-only views for managing contributions
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def pending_contributions(request):
    """Get all pending contributions for admin review"""
    contributions = Contribution.objects.filter(status='pending').order_by('-submitted_at')
    
    data = []
    for contrib in contributions:
        contrib_data = ContributionSerializer(contrib).data
        contrib_data['person_details'] = PersonListSerializer(contrib.person).data
        data.append(contrib_data)
    
    return Response({
        'count': contributions.count(),
        'results': data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def contribution_stats(request):
    """Get statistics about contributions"""
    from django.db.models import Count
    
    stats = Contribution.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        approved=Count('id', filter=Q(status='approved')),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    
    recent = Contribution.objects.order_by('-submitted_at')[:10]
    
    return Response({
        'stats': stats,
        'recent': ContributionSerializer(recent, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def test_s3_connection(request):
    """Test S3 configuration in production - Admin only"""
    try:
        import boto3
        from django.conf import settings
        
        if not settings.AWS_ACCESS_KEY_ID:
            return Response({
                "error": "AWS_ACCESS_KEY_ID not configured",
                "debug": settings.DEBUG,
                "bucket": settings.AWS_STORAGE_BUCKET_NAME
            })
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        response = s3_client.list_objects_v2(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            MaxKeys=5
        )
        
        files = []
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
        
        return Response({
            "status": "success",
            "bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "region": settings.AWS_S3_REGION_NAME,
            "files_found": len(files),
            "sample_files": files[:5],
            "debug": settings.DEBUG
        })
        
    except Exception as e:
        return Response({
            "error": str(e),
            "type": type(e).__name__,
            "debug": settings.DEBUG
        }, status=500)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([permissions.AllowAny])
def create_contribution(request, person_id):
    """Simple endpoint to create a contribution with CSRF and throttling"""
    # Apply throttling
    throttle = AnonRateThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {"error": "Rate limit exceeded. Please try again later."}, 
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        return Response(
            {"error": "Person not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ContributionCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate image if provided
    image = request.FILES.get('content_image')
    if image:
        if image.size > MAX_IMAGE_SIZE:
            return Response(
                {"error": f"Image size must be less than {MAX_IMAGE_SIZE // 1024 // 1024}MB"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                {"error": f"Image type must be one of: {', '.join(ALLOWED_IMAGE_TYPES)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    contribution = serializer.save(person=person)
    
    return Response(
        ContributionSerializer(contribution).data,
        status=status.HTTP_201_CREATED
    )

@api_view(['GET'])
@ensure_csrf_cookie
def get_csrf_token(request):
    """Get CSRF token for frontend"""
    return JsonResponse({
        'csrfToken': get_token(request)
    })