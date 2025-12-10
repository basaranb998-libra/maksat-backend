from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
import googlemaps
import google.generativeai as genai

from .models import FavoriteVenue, SearchHistory, UserProfile
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    FavoriteVenueSerializer, SearchHistorySerializer,
    UserProfileSerializer, VenueSearchSerializer,
    VenueGenerateSerializer
)

# Initialize APIs - lazy load to avoid errors during startup
def get_gmaps_client():
    return googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY) if settings.GOOGLE_MAPS_API_KEY else None

def get_genai_model():
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    return None

def generate_mock_venues(category, location, filters):
    """Mock venue data generator"""
    import random

    city = location['city']
    districts = location.get('districts', [])
    district = districts[0] if districts else city

    # Kategori bazlı örnek mekanlar
    mock_places = {
        'İlk Buluşma': [
            {'name': 'Kahve Dünyası', 'type': 'Kafe', 'vibes': ['#Sakin', '#Rahat', '#Sıcak']},
            {'name': 'Starbucks', 'type': 'Kafe', 'vibes': ['#Modern', '#WiFi', '#Sessiz']},
            {'name': 'Mado', 'type': 'Cafe & Restaurant', 'vibes': ['#Aile', '#Geleneksel', '#Tatlı']},
            {'name': 'The House Cafe', 'type': 'Kafe', 'vibes': ['#Şık', '#Popüler', '#Instagram']},
            {'name': 'Petra Roasting Co.', 'type': 'Kafe', 'vibes': ['#Specialty', '#Sessiz', '#Kaliteli']},
        ],
        'Tatil': [
            {'name': 'Lara Beach Hotel', 'type': 'Otel', 'vibes': ['#Plaj', '#HerŞeyDahil', '#Lüks']},
            {'name': 'Rixos Premium', 'type': 'Resort', 'vibes': ['#Lüks', '#Spa', '#Aktivite']},
            {'name': 'Maxx Royal', 'type': 'Otel', 'vibes': ['#VIP', '#Plaj', '#Gourmet']},
        ],
        'İş Toplantısı': [
            {'name': 'Starbucks Reserve', 'type': 'Kafe', 'vibes': ['#Sessiz', '#WiFi', '#Professional']},
            {'name': 'Hilton Meeting Room', 'type': 'Toplantı Salonu', 'vibes': ['#İş', '#Teknoloji', '#Profesyonel']},
        ],
    }

    # Kategoriye göre veya varsayılan mekanlar
    places_list = mock_places.get(category['name'], mock_places['İlk Buluşma'])

    venues = []
    for idx, place_data in enumerate(places_list[:10]):
        # Budget filtresine göre fiyat belirle
        budget = filters.get('budget', 'Orta')
        if budget == 'Ekonomik':
            price_range = random.choice(['$', '$$'])
            price_level = random.randint(1, 2)
        elif budget == 'Lüks':
            price_range = random.choice(['$$$', '$$$$'])
            price_level = random.randint(3, 4)
        else:
            price_range = '$$'
            price_level = 2

        # Gemini ile açıklama oluştur
        description = f"{place_data['name']}, {district} bölgesinde {category['name']} için ideal bir mekan."
        model = get_genai_model()
        if model:
            try:
                prompt = f"{place_data['name']} adlı {place_data['type']} için {category['name']} kategorisinde 2 cümlelik Türkçe açıklama yaz."
                response = model.generate_content(prompt)
                description = response.text.strip()
            except:
                pass

        venue = {
            'id': f"v{idx + 1}",
            'name': place_data['name'],
            'description': description,
            'imageUrl': f"https://via.placeholder.com/800x600?text={place_data['name']}",
            'category': category['name'],
            'vibeTags': place_data['vibes'],
            'address': f"{place_data['name']}, {district}, {city}",
            'priceRange': price_range,
            'googleRating': round(random.uniform(4.0, 4.9), 1),
            'noiseLevel': random.randint(30, 70),
            'matchScore': random.randint(75, 95),
            'metrics': {
                'ambiance': random.randint(70, 95),
                'accessibility': random.randint(75, 95),
                'popularity': random.randint(70, 90)
            }
        }
        venues.append(venue)

    # Match score'a göre sırala
    venues.sort(key=lambda x: x['matchScore'], reverse=True)
    return venues


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """Kullanıcı kayıt endpoint'i"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """Kullanıcı giriş endpoint'i"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Geçersiz kullanıcı adı veya şifre'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout(request):
    """Kullanıcı çıkış endpoint'i"""
    request.user.auth_token.delete()
    return Response({'message': 'Başarıyla çıkış yapıldı'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def generate_venues(request):
    """AI destekli mekan önerisi endpoint'i"""
    import json
    import random

    serializer = VenueGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    category = data['category']
    location = data['location']
    filters = data.get('filters', {})
    trip_duration = data.get('tripDuration')

    try:
        # Kategori ve filtrelere göre arama sorgusu oluştur
        search_query = f"{category['name']}"

        # Filtrelere göre sorguyu genişlet
        if filters.get('vibes'):
            search_query += f" {' '.join(filters['vibes'])}"

        # Lokasyon oluştur
        city = location['city']
        districts = location.get('districts', [])
        search_location = f"{districts[0]}, {city}" if districts else city

        # Google Places API'den mekan ara
        gmaps = get_gmaps_client()

        # Google Places API çalışmazsa mock data kullan
        use_mock_data = not gmaps
        places_result = {'results': []}

        if gmaps:
            try:
                # Yeni Places API (Text Search) kullanarak ara
                import requests
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.photos,places.priceLevel,places.types,places.location"
                }
                payload = {
                    "textQuery": f"{search_query} {search_location}",
                    "languageCode": "tr",
                    "maxResultCount": 15
                }

                response = requests.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    places_data = response.json()
                    places_result = {'results': places_data.get('places', [])}
                else:
                    print(f"Places API hatası: {response.status_code} - {response.text}")
                    use_mock_data = True

            except Exception as e:
                print(f"Google Places API hatası: {e}")
                use_mock_data = True

        # Mock data kullanılacaksa örnek mekanlar oluştur
        if use_mock_data or not places_result.get('results'):
            mock_venues = generate_mock_venues(category, location, filters)
            return Response(mock_venues, status=status.HTTP_200_OK)

        venues = []
        for idx, place in enumerate(places_result.get('results', [])[:15]):
            # Yeni API formatı
            place_id = place.get('id', f"place_{idx}")
            place_name = place.get('displayName', {}).get('text', '')
            place_address = place.get('formattedAddress', '')
            place_rating = place.get('rating', 0)
            place_types = place.get('types', [])

            # Fotoğraf URL'si (yeni API formatı)
            photo_url = None
            if place.get('photos') and len(place['photos']) > 0:
                photo_name = place['photos'][0].get('name', '')
                if photo_name:
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={settings.GOOGLE_MAPS_API_KEY}&maxWidthPx=800"

            # Fiyat aralığı (yeni API PRICE_LEVEL_* formatı)
            price_level_str = place.get('priceLevel', 'PRICE_LEVEL_MODERATE')
            price_level_map = {
                'PRICE_LEVEL_FREE': 1,
                'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2,
                'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4
            }
            price_level = price_level_map.get(price_level_str, 2)
            price_map = {1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
            price_range = price_map.get(price_level, '$$')

            # Budget filtresine göre kontrol et
            budget_filter = filters.get('budget')
            if budget_filter:
                budget_map = {'Ekonomik': [1, 2], 'Orta': [2, 3], 'Lüks': [3, 4]}
                if budget_filter in budget_map and price_level not in budget_map[budget_filter]:
                    continue

            # Gemini ile detaylı analiz
            try:
                analysis_prompt = f"""
                Mekan: {place_name}
                Kategori: {category['name']}
                Adres: {place_address}
                Tip: {', '.join(place_types[:3])}
                Rating: {place_rating}

                Bu mekanı analiz ederek aşağıdaki bilgileri JSON formatında döndür:
                {{
                    "description": "Mekan hakkında 2-3 cümlelik açıklama (Türkçe)",
                    "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
                    "noiseLevel": 40,
                    "matchScore": 85,
                    "metrics": {{
                        "ambiance": 85,
                        "accessibility": 90,
                        "popularity": 80
                    }}
                }}

                Sadece JSON döndür, başka açıklama ekleme.
                """

                model = get_genai_model()
                if not model:
                    raise Exception("Gemini API key eksik")
                response = model.generate_content(analysis_prompt)

                # JSON parse et
                response_text = response.text.strip()
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()

                ai_data = json.loads(response_text)

                # Venue objesi oluştur
                venue = {
                    'id': f"v{idx + 1}",
                    'name': place_name,
                    'description': ai_data.get('description', 'Açıklama ekleniyor...'),
                    'imageUrl': photo_url or 'https://via.placeholder.com/800x600',
                    'category': category['name'],
                    'vibeTags': ai_data.get('vibeTags', ['#Popüler']),
                    'address': place_address,
                    'priceRange': price_range,
                    'googleRating': place_rating if place_rating > 0 else 4.0,
                    'noiseLevel': ai_data.get('noiseLevel', 50),
                    'matchScore': ai_data.get('matchScore', 75),
                    'metrics': ai_data.get('metrics', {
                        'ambiance': 75,
                        'accessibility': 80,
                        'popularity': 70
                    })
                }

                venues.append(venue)

            except Exception as e:
                print(f"AI analiz hatası: {e}")
                # Fallback venue data
                venue = {
                    'id': f"v{idx + 1}",
                    'name': place_name,
                    'description': f"{category['name']} için harika bir mekan seçeneği.",
                    'imageUrl': photo_url or 'https://via.placeholder.com/800x600',
                    'category': category['name'],
                    'vibeTags': ['#Popüler', '#Kaliteli'],
                    'address': place_address,
                    'priceRange': price_range,
                    'googleRating': place_rating if place_rating > 0 else 4.0,
                    'noiseLevel': 50,
                    'matchScore': 75,
                    'metrics': {
                        'ambiance': 75,
                        'accessibility': 80,
                        'popularity': 70
                    }
                }
                venues.append(venue)

        # Match score'a göre sırala
        venues.sort(key=lambda x: x['matchScore'], reverse=True)

        # İlk 8-10 sonucu döndür
        final_venues = venues[:10]

        # Arama geçmişine kaydet
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                user=request.user,
                query=search_query,
                intent=category['name'],
                location=search_location,
                results_count=len(final_venues)
            )

        return Response(final_venues, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(f"Generate venues hatası: {e}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Mekan önerisi oluşturulurken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def search_venues(request):
    """Venue arama endpoint'i - Google Places + Gemini entegrasyonu"""
    serializer = VenueSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    query = serializer.validated_data['query']
    location = serializer.validated_data['location']
    radius = serializer.validated_data['radius']

    try:
        # Google Places API'den mekan arama
        gmaps = get_gmaps_client()
        if not gmaps:
            return Response(
                {'error': 'Google Maps API key eksik'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        places_result = gmaps.places(
            query=query,
            location=location,
            radius=radius,
            language='tr'
        )

        venues = []
        for place in places_result.get('results', [])[:10]:  # İlk 10 sonuç
            # Her mekan için detay al
            place_id = place['place_id']
            details = gmaps.place(place_id, language='tr')
            place_details = details.get('result', {})

            # Fotoğraf URL'si oluştur
            photo_url = None
            if place_details.get('photos'):
                photo_ref = place_details['photos'][0]['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={settings.GOOGLE_MAPS_API_KEY}"

            venue_data = {
                'place_id': place_id,
                'name': place_details.get('name', ''),
                'address': place_details.get('formatted_address', ''),
                'rating': place_details.get('rating'),
                'photo_url': photo_url,
                'types': place_details.get('types', []),
                'price_level': place_details.get('price_level'),
            }

            # Gemini ile vibe analizi
            try:
                vibe_prompt = f"""
                Mekan: {venue_data['name']}
                Adres: {venue_data['address']}
                Kategoriler: {', '.join(venue_data['types'][:5])}
                Rating: {venue_data['rating']}

                Bu mekanın vibe'ını analiz et ve şu kategorilerde 0-10 arası puan ver:
                - romantic (romantik)
                - casual (rahat, gündelik)
                - professional (iş toplantısı için uygun)
                - social (arkadaşlarla takılmak için)
                - quiet (sessiz, sakin)
                - energetic (enerjik, hareketli)

                JSON formatında döndür: {{"romantic": 8, "casual": 5, ...}}
                """

                model = get_genai_model()
                if not model:
                    raise Exception("Gemini API key eksik")
                response = model.generate_content(vibe_prompt)

                # JSON parse et (basit versiyon)
                import json
                vibe_text = response.text.strip()
                # JSON'u extract et
                if '{' in vibe_text and '}' in vibe_text:
                    json_start = vibe_text.index('{')
                    json_end = vibe_text.rindex('}') + 1
                    vibe_scores = json.loads(vibe_text[json_start:json_end])
                    venue_data['vibe_score'] = vibe_scores
                else:
                    venue_data['vibe_score'] = {}

            except Exception as e:
                print(f"Vibe analizi hatası: {e}")
                venue_data['vibe_score'] = {}

            venues.append(venue_data)

        # Arama geçmişine kaydet
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                user=request.user,
                query=query,
                intent=query,  # Gemini ile intent analizi yapılabilir
                location=location,
                results_count=len(venues)
            )

        return Response({
            'query': query,
            'location': location,
            'results': venues
        })

    except Exception as e:
        return Response(
            {'error': f'Arama hatası: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class FavoriteVenueViewSet(viewsets.ModelViewSet):
    """Favori mekanlar CRUD işlemleri"""
    serializer_class = FavoriteVenueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteVenue.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Arama geçmişi görüntüleme"""
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)


class UserProfileViewSet(viewsets.ModelViewSet):
    """Kullanıcı profili yönetimi"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Mevcut kullanıcının profilini getir"""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
