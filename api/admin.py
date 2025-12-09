from django.contrib import admin
from .models import FavoriteVenue, SearchHistory, UserProfile


@admin.register(FavoriteVenue)
class FavoriteVenueAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'rating', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'address', 'user__username')


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'location', 'results_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query', 'intent', 'user__username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_location', 'created_at')
    search_fields = ('user__username',)
