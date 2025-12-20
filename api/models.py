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


class CachedVenue(models.Model):
    """API çağrılarını azaltmak için cache'lenmiş mekan verileri"""
    place_id = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, db_index=True)  # Kategori adı (Meyhane, Kafe, vb.)
    city = models.CharField(max_length=100, db_index=True)  # İl
    district = models.CharField(max_length=100, blank=True, db_index=True)  # İlçe
    neighborhood = models.CharField(max_length=100, blank=True)  # Mahalle/Semt

    # Tüm venue verisi JSON olarak
    venue_data = models.JSONField()  # Gemini'den gelen tüm venue objesi

    # Google Places verileri (ayrı tutuyoruz çünkü güncellenebilir)
    google_rating = models.FloatField(null=True, blank=True)
    google_review_count = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Veri güncelliği için - 30 günden eski veriler yeniden sorgulanabilir
    last_api_call = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Cached Venue'
        verbose_name_plural = 'Cached Venues'
        indexes = [
            models.Index(fields=['category', 'city', 'district']),
            models.Index(fields=['category', 'city']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category} - {self.city})"
