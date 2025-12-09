from django.db import models
from django.contrib.auth.models import User


class FavoriteVenue(models.Model):
    """Kullanıcıların favori mekanları"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    place_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    address = models.TextField()
    photo_url = models.URLField(blank=True, null=True)
    rating = models.FloatField(null=True, blank=True)
    vibe_score = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class SearchHistory(models.Model):
    """Kullanıcı arama geçmişi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
    query = models.TextField()
    intent = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Search histories'

    def __str__(self):
        return f"{self.user.username} - {self.query[:50]}"


class UserProfile(models.Model):
    """Kullanıcı profil bilgileri"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    preferred_location = models.CharField(max_length=255, blank=True)
    preferences = models.JSONField(default=dict)  # Vibe tercihleri, kategoriler vb.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
