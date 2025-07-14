from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from .models import Conflict, Person
from .serializers import (
    ConflictSerializer, ConflictDetailSerializer,
    PersonListSerializer, PersonDetailSerializer,
    PersonSearchSerializer
)


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for conflicts"""
    queryset = Conflict.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConflictDetailSerializer
        return ConflictSerializer


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for people"""
    queryset = Person.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PersonListSerializer
        elif self.action == 'search':
            return PersonSearchSerializer
        return PersonDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        conflict_id = self.request.query_params.get('conflict', None)
        if conflict_id is not None:
            queryset = queryset.filter(conflict_id=conflict_id)
        # Always order by last name, then first name for consistency
        return queryset.order_by('last_name', 'first_name')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search and filter people"""
        queryset = Person.objects.all()
        
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
        
        # Order results
        queryset = queryset.order_by('last_name', 'first_name')
        
        # Paginate if needed (for now, return all for infinite scroll)
        serializer = PersonSearchSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Get PDF for a person - generates presigned S3 URL or serves local file"""
        person = self.get_object()
        
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
                return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
            except FileNotFoundError:
                return Response(
                    {"error": "PDF file not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # In production, generate presigned URL
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
            
            # Redirect to the presigned URL
            return HttpResponseRedirect(presigned_url)
            
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return Response(
                {"error": "Failed to generate PDF URL"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def memorial_index(request):
    """Get all conflicts with their casualties for the memorial index"""
    conflicts = Conflict.objects.all()
    data = []
    
    for conflict in conflicts:
        casualties = Person.objects.filter(conflict=conflict).order_by('last_name', 'first_name')
        conflict_data = ConflictSerializer(conflict).data
        conflict_data['casualties'] = PersonListSerializer(casualties, many=True).data
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

@api_view(['GET'])
def test_s3_connection(request):
    """Test S3 configuration in production"""
    try:
        import boto3
        from django.conf import settings
        
        # Check if credentials are set
        if not settings.AWS_ACCESS_KEY_ID:
            return Response({
                "error": "AWS_ACCESS_KEY_ID not configured",
                "debug": settings.DEBUG,
                "bucket": settings.AWS_STORAGE_BUCKET_NAME
            })
        
        # Try to connect to S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # List objects
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