from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConflictViewSet, PersonViewSet

router = DefaultRouter()
router.register('conflicts', ConflictViewSet)
router.register('persons', PersonViewSet)

urlpatterns = [
    path('', include(router.urls)),
]