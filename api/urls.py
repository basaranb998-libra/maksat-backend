from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'favorites', views.FavoriteVenueViewSet, basename='favorite')
router.register(r'search-history', views.SearchHistoryViewSet, basename='search-history')
router.register(r'profile', views.UserProfileViewSet, basename='profile')

urlpatterns = [
    # Authentication
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),

    # Venue endpoints
    path('venues/generate/', views.generate_venues, name='generate-venues'),
    path('venues/search/', views.search_venues, name='search-venues'),

    # Router URLs
    path('', include(router.urls)),
]
