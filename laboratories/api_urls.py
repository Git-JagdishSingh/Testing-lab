from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, LaboratoryViewSet, ReviewViewSet, SearchAPIView

app_name = 'api'

router = DefaultRouter()
router.register(r'laboratories', LaboratoryViewSet, basename='laboratory')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('search/', SearchAPIView.as_view(), name='api-search'),
]

urlpatterns += router.urls
