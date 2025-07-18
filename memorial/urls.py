# memorial/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers
from .views import (
    ConflictViewSet, PersonViewSet, ContributionViewSet,
    memorial_index, search_filters, test_s3_connection,
    pending_contributions, contribution_stats,
    create_contribution, get_csrf_token
)

# Main router
router = DefaultRouter()
router.register('conflicts', ConflictViewSet)
router.register('persons', PersonViewSet)

# Nested router for person contributions (admin only except creation)
persons_router = nested_routers.NestedDefaultRouter(router, 'persons', lookup='person')
persons_router.register('contributions', ContributionViewSet, basename='person-contributions')

urlpatterns = [
    # CSRF token endpoint (must be first for frontend)
    path('csrf/', get_csrf_token, name='csrf-token'),
    
    # Public endpoints
    path('index/', memorial_index, name='memorial-index'),
    path('search-filters/', search_filters, name='search-filters'),
    
    # Contribution creation (public with throttling and CSRF)
    path('persons/<int:person_id>/contributions/', create_contribution, name='create-contribution'),
    
    # Admin-only endpoints
    path('contributions/pending/', pending_contributions, name='pending-contributions'),
    path('contributions/stats/', contribution_stats, name='contribution-stats'),
    path('test-s3/', test_s3_connection, name='test-s3'),
    
    # Include routers
    path('', include(router.urls)),
    path('', include(persons_router.urls)),
]