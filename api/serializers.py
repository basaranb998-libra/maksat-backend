from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FavoriteVenue, SearchHistory, UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Şifreler eşleşmiyor")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user


class FavoriteVenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteVenue
        fields = ('id', 'place_id', 'name', 'address', 'photo_url', 'rating', 'vibe_score', 'created_at')
        read_only_fields = ('id', 'created_at')


class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ('id', 'query', 'intent', 'location', 'results_count', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'preferred_location', 'preferences', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class VenueSearchSerializer(serializers.Serializer):
    """Venue arama için input serializer"""
    query = serializers.CharField(required=True)
    location = serializers.CharField(required=False, default="İzmir, Turkey")
    radius = serializers.IntegerField(required=False, default=5000)


class CategorySerializer(serializers.Serializer):
    """Kategori bilgisi"""
    id = serializers.CharField()
    name = serializers.CharField()
    icon = serializers.CharField(required=False)
    description = serializers.CharField(required=False)


class LocationSerializer(serializers.Serializer):
    """Konum bilgisi"""
    city = serializers.CharField()
    districts = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class FiltersSerializer(serializers.Serializer):
    """Filtre bilgisi"""
    groupSize = serializers.CharField(required=False)
    budget = serializers.CharField(required=False)
    vibes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    amenities = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    # Vibe filters
    environment = serializers.CharField(required=False)
    smoking = serializers.CharField(required=False)
    liveMusic = serializers.CharField(required=False)
    alcohol = serializers.CharField(required=False)
    # Event filters
    dateRange = serializers.CharField(required=False)
    musicGenre = serializers.CharField(required=False)
    performanceGenre = serializers.CharField(required=False)
    sportType = serializers.CharField(required=False)


class VenueGenerateSerializer(serializers.Serializer):
    """Venue generate endpoint için input serializer"""
    category = CategorySerializer(required=True)
    location = LocationSerializer(required=True)
    filters = FiltersSerializer(required=False, default=dict)
    tripDuration = serializers.IntegerField(required=False)
