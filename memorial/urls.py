from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConflictViewSet, PersonViewSet, memorial_index, search_filters

router = DefaultRouter()
router.register('conflicts', ConflictViewSet)
router.register('persons', PersonViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('index/', memorial_index, name='memorial-index'),
    path('search-filters/', search_filters, name='search-filters'),
]