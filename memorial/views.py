from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from .models import Conflict, Person
from .serializers import (
    ConflictSerializer, ConflictDetailSerializer,
    PersonListSerializer, PersonDetailSerializer
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
        return PersonDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        conflict_id = self.request.query_params.get('conflict', None)
        if conflict_id is not None:
            queryset = queryset.filter(conflict_id=conflict_id)
        return queryset
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Get PDF for a person (placeholder for now)"""
        person = self.get_object()
        
        if not person.pdf_key:
            return Response(
                {"error": "No PDF available for this person"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # TODO: Generate S3 presigned URL and redirect
        # For now, return a placeholder response
        return HttpResponse(
            f"PDF placeholder for {person.display_name}\n"
            f"S3 Key: {person.pdf_key}\n"
            f"This will redirect to S3 presigned URL in production",
            content_type="text/plain"
        )