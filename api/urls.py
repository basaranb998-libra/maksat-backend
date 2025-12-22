from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'favorites', views.FavoriteVenueViewSet, basename='favorite')
router.register(r'search-history', views.SearchHistoryViewSet, basename='search-history')
router.register(r'profile', views.UserProfileViewSet, basename='profile')

urlpatterns = [
    # Health check (for Render cold start)
    path('health/', views.health_check, name='health-check'),

    # Cache monitoring
    path('cache/stats/', views.cache_stats, name='cache-stats'),
    path('cache/clear-invalid/', views.cache_clear_invalid, name='cache-clear-invalid'),

    # Authentication
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/google/', views.google_login, name='google-login'),

    # Venue endpoints
    path('venues/generate/', views.generate_venues, name='generate-venues'),
    path('venues/search/', views.search_venues, name='search-venues'),
    path('venues/similar/', views.get_similar_venues, name='similar-venues'),

    # Router URLs
    path('', include(router.urls)),
]
