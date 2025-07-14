from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConflictViewSet, PersonViewSet, memorial_index, search_filters, test_s3_connection

router = DefaultRouter()
router.register('conflicts', ConflictViewSet)
router.register('persons', PersonViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('index/', memorial_index, name='memorial-index'),
    path('search-filters/', search_filters, name='search-filters'),
    path('test-s3/', test_s3_connection, name='test-s3'),
]