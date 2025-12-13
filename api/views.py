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
        # Gemini 2.0 Flash Experimental - Stable model
        return genai.GenerativeModel('gemini-2.0-flash-exp')
    return None

def generate_vacation_experiences(location, trip_duration, filters):
    """Tatil kategorisi için deneyim odaklı öneri sistemi"""
    import json
    import random

    city = location['city']
    districts = location.get('districts', [])
    location_query = f"{districts[0]}, {city}" if districts else city
    duration = trip_duration if trip_duration else 3  # Varsayılan 3 gün

    # Gemini AI ile deneyim bazlı tatil planı oluştur
    model = get_genai_model()
    if not model:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        # Yeni deneyim odaklı prompt - Cool Lokal Rehber tarzı
        experience_prompt = f"""
Sen "{location_query}" şehrini avucunun içi gibi bilen, cool ve deneyim odaklı bir 'Lokal Rehber'sin.
Görevin: "{location_query}" için {duration} günlük, NOKTA ATIŞI ve AKSİYON ODAKLI bir liste hazırlamak.

## STRATEJİ: "Sadece Mekan Değil, Deneyim Öner"
Kullanıcıya sadece "Louvre Müzesi" deme. "Louvre'da Mona Lisa'yı gör" veya "Tuileries Bahçesinde yürüyüş yap" de.

## GÖREVLER
1. **Google Search Kullan (Zihinde)**: "{location_query} top things to do", "{location_query} best local food" gibi aramalar düşün.
2. **Rota Planla**: Mekanları birbirine yakınlığına göre günlere ayır. Aynı bölgedeki aktiviteleri ard arda sırala.
3. **Çeşitlilik**: Landmark (müze, tarihi yer), Yeme/İçme (kahvaltı, öğle, akşam), Aktivite (yürüyüş, alışveriş) karışık olsun.
4. **Günlük 8-10 Aktivite**: Her gün sabahtan akşama dolu dolu program (08:00-22:00 arası).
5. **60% Generic, 40% Spesifik**: Generic aktiviteler kullanıcının keşfetmesini sağlar, spesifik mekanlar ise must-see yerlerdir

## GÜNLÜK PROGRAM YAPISI
Her gün şu yapıda olmalı:
- 08:00-09:30: Sabah kahvaltısı (yerel bir kafede)
- 10:00-12:00: Sabah aktivitesi (müze, landmark, gezinti)
- 12:30-14:00: Öğle yemeği (yerel restoran)
- 14:30-17:00: Öğleden sonra aktivitesi (müze, park, alışveriş)
- 17:30-19:00: Akşam aktivitesi (manzara noktası, yürüyüş)
- 19:30-21:00: Akşam yemeği (restoran, bar)
- 21:30-23:00: Gece aktivitesi (bar, kulüp, gece gezintisi - opsiyonel)

## ÇIKTI FORMATI (JSON ARRAY)
[
  {{
    "id": "day1_morning_1",
    "name": "Sant'Eustachio Il Caffè'de geleneksel İtalyan kahvaltısı",
    "description": "Roma'nın en ünlü kahve dükkanlarından birinde, taze cornetto ve cappuccino ile güne başla. 1938'den beri hizmet veren bu tarihi mekan, Pantheon'a 2 dakika yürüme mesafesinde.",
    "imageUrl": "https://images.unsplash.com/photo-1509042239860-f550ce710b93",
    "category": "Tatil",
    "vibeTags": ["#Kahvaltı", "#Yerel", "#Tarihi"],
    "address": "Piazza di S. Eustachio, 82, 00186 Roma RM, İtalya",
    "priceRange": "$",
    "googleRating": 4.4,
    "noiseLevel": 45,
    "matchScore": 88,
    "itineraryDay": 1,
    "timeSlot": "08:30-09:30",
    "duration": "1 saat",
    "isSpecificVenue": true,
    "venueName": "Sant'Eustachio Il Caffè",
    "activityType": "breakfast",
    "metrics": {{
      "ambiance": 85,
      "accessibility": 90,
      "popularity": 95
    }}
  }},
  {{
    "id": "day1_morning_2",
    "name": "Pantheon'u ziyaret et",
    "description": "2000 yıllık Roma'nın en iyi korunmuş antik yapısını keşfet. Orta kubbedeki açıklıktan giren ışık büyüleyici. Ücretsiz giriş, içeride 30-45 dakika geçir.",
    "imageUrl": "https://images.unsplash.com/photo-1552832230-c0197dd311b5",
    "category": "Tatil",
    "vibeTags": ["#Tarihi", "#Kültür", "#İkonik"],
    "address": "Piazza della Rotonda, 00186 Roma RM, İtalya",
    "priceRange": "$",
    "googleRating": 4.7,
    "noiseLevel": 60,
    "matchScore": 92,
    "itineraryDay": 1,
    "timeSlot": "10:00-11:00",
    "duration": "1 saat",
    "isSpecificVenue": true,
    "venueName": "Pantheon",
    "activityType": "sightseeing",
    "metrics": {{
      "ambiance": 95,
      "accessibility": 85,
      "popularity": 98
    }}
  }},
  {{
    "id": "day1_lunch_1",
    "name": "Trastevere'de yerel bir trattoria'da öğle yemeği",
    "description": "Trastevere bölgesinin dar sokaklarında gizli bir trattoria bul. Cacio e pepe veya carbonara dene. Yerel halk tarafından tercih edilen bu bölge otantik Roma mutfağını sunar.",
    "imageUrl": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5",
    "category": "Tatil",
    "vibeTags": ["#Yerel", "#Otantik", "#İtalyan"],
    "address": "Trastevere, Roma RM, İtalya",
    "priceRange": "$$",
    "googleRating": 4.5,
    "noiseLevel": 55,
    "matchScore": 85,
    "itineraryDay": 1,
    "timeSlot": "12:30-14:00",
    "duration": "1.5 saat",
    "isSpecificVenue": false,
    "activityType": "lunch",
    "metrics": {{
      "ambiance": 80,
      "accessibility": 85,
      "popularity": 88
    }}
  }}
]

## KURALLAR
- {duration} gün × 8-12 aktivite = Toplam {duration * 8} - {duration * 12} aktivite döndür
- Her aktiviteye "timeSlot" ekle (örn: "08:30-09:30", "14:00-16:30")
- Her aktiviteye "duration" ekle (örn: "1 saat", "2.5 saat")
- Kahvaltı, öğle, akşam yemeği MUTLAKA ekle
- Aktiviteler birbirine yakın olsun (max 15-20 dakika yürüme)
- Unsplash fotoğraf URL'leri ekle (aktiviteye uygun)
- Her gün için itineraryDay değerini doğru ata (1, 2, 3...)
- ID formatı: "day{{X}}_{{zamanDilimi}}_{{sıra}}" (örn: "day1_morning_1", "day2_afternoon_3")

## ÖNEMLİ: isSpecificVenue ve activityType
- **isSpecificVenue**: true ise gerçek mekan ismi var (örn: "Sant'Eustachio Il Caffè", "Pantheon", "Trevi Çeşmesi")
- **isSpecificVenue**: false ise generic aktivite (örn: "Trastevere'de yerel trattoria", "Monti bölgesinde vintage butikler")
- **venueName**: Eğer isSpecificVenue=true ise, mekanın tam ismini yaz. False ise boş bırak.
- **activityType**: breakfast, lunch, dinner, cafe, bar, dessert, sightseeing, shopping, activity gibi değerler kullan

## GENERIC vs SPESİFİK ÖRNEKLER
GENERIC (isSpecificVenue=false):
- "Trastevere'de yerel bir trattoria'da öğle yemeği" (activityType: lunch)
- "Monti bölgesinde butik mağazalarda alışveriş" (activityType: shopping)
- "Testaccio'da street food tadımı" (activityType: lunch)
- "Tiber nehri kenarında yürüyüş" (activityType: activity)

SPESİFİK (isSpecificVenue=true, venueName dolu):
- "Pantheon'u ziyaret et" (venueName: "Pantheon", activityType: sightseeing)
- "Sant'Eustachio Il Caffè'de kahvaltı" (venueName: "Sant'Eustachio Il Caffè", activityType: breakfast)
- "Piazza Navona'da gezinti" (venueName: "Piazza Navona", activityType: sightseeing)

Her gün için 60% generic, 40% spesifik aktivite dengesi kur.

SADECE JSON ARRAY döndür, başka açıklama ekleme.
"""

        response = model.generate_content(experience_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        experiences = json.loads(response_text)

        # Validate ve düzenle
        for exp in experiences:
            # ID yoksa ekle
            if 'id' not in exp:
                exp['id'] = f"exp_{random.randint(1000, 9999)}"
            # Category zorla
            exp['category'] = 'Tatil'
            # ItineraryDay yoksa hesapla
            if 'itineraryDay' not in exp:
                exp['itineraryDay'] = 1

        return Response(experiences, status=status.HTTP_200_OK)

    except Exception as e:
        import sys
        print(f"❌ Vacation experience generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Tatil deneyimi oluşturulurken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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

    # DEBUG: Log incoming request data
    import sys
    print(f"\n{'='*60}", file=sys.stderr, flush=True)
    print(f"🔍 INCOMING REQUEST DEBUG", file=sys.stderr, flush=True)
    print(f"{'='*60}", file=sys.stderr, flush=True)
    print(f"Category: {category}", file=sys.stderr, flush=True)
    print(f"Filters received: {json.dumps(filters, indent=2, ensure_ascii=False)}", file=sys.stderr, flush=True)
    print(f"Alcohol filter value: {filters.get('alcohol', 'NOT SET')}", file=sys.stderr, flush=True)
    print(f"{'='*60}\n", file=sys.stderr, flush=True)

    try:
        # Tatil kategorisi için özel işlem
        if category['name'] == 'Tatil':
            # Tatil kategorisi için deneyim bazlı öneri sistemi
            return generate_vacation_experiences(location, trip_duration, filters)

        # Kategori bazlı query mapping (Tatil hariç)
        # ALKOL FİLTRESİNE GÖRE DİNAMİK QUERY OLUŞTUR
        alcohol_filter = filters.get('alcohol', 'Any')

        if alcohol_filter == 'Alcoholic':
            # Alkollü mekan seçilirse SADECE bar, pub, restaurant, wine bar ara
            category_query_map = {
                'İlk Buluşma': 'bar wine bar restaurant pub',
                'İş Toplantısı': 'restaurant bar hotel lounge',
                'Arkadaşlarla Takılma': 'bar pub nightclub restaurant',
                'Aile Yemeği': 'restaurant bar casual dining',
                'Romantik Akşam': 'romantic restaurant wine bar fine dining',
                'Çalışma': 'restaurant bar cafe',  # Çalışma için alkollü mekan mantıksız ama kullanıcı seçerse
            }
        elif alcohol_filter == 'Non-Alcoholic':
            # Alkolsüz mekan seçilirse SADECE cafe, bakery, coffee shop ara
            category_query_map = {
                'İlk Buluşma': 'cafe coffee shop bakery tea house',
                'İş Toplantısı': 'business meeting cafe coffee shop',
                'Arkadaşlarla Takılma': 'cafe coffee shop hangout spot',
                'Aile Yemeği': 'family restaurant cafe casual dining',
                'Romantik Akşam': 'cafe coffee shop bakery',
                'Çalışma': 'coworking space cafe library quiet study',
            }
        else:
            # Any seçilirse her türlü mekan (varsayılan)
            category_query_map = {
                'İlk Buluşma': 'cafe restaurant bar wine bar coffee shop',
                'İş Toplantısı': 'business meeting cafe hotel conference restaurant',
                'Arkadaşlarla Takılma': 'bar pub restaurant cafe hangout spot',
                'Aile Yemeği': 'family restaurant casual dining',
                'Romantik Akşam': 'romantic restaurant wine bar fine dining cafe',
                'Çalışma': 'coworking space cafe library quiet study',
            }

        # Kategori ve filtrelere göre arama sorgusu oluştur
        search_query = category_query_map.get(category['name'], category['name'])

        # Filtrelere göre sorguyu genişlet
        if filters.get('vibes'):
            search_query += f" {' '.join(filters['vibes'])}"

        # Lokasyon oluştur
        city = location['city']
        districts = location.get('districts', [])
        search_location = f"{districts[0]}, {city}" if districts else city
        import sys
        print(f"DEBUG - Alcohol Filter: {alcohol_filter}", file=sys.stderr, flush=True)
        print(f"DEBUG - Search Query: {search_query}", file=sys.stderr, flush=True)
        print(f"DEBUG - Search Location: {search_location}", file=sys.stderr, flush=True)

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
                    "textQuery": f"{search_query} in {search_location}, Turkey",
                    "languageCode": "tr",
                    "maxResultCount": 20  # Gemini filtreleyeceği için daha fazla sonuç iste
                }

                print(f"DEBUG - Google Places API Query: {payload['textQuery']}", file=sys.stderr, flush=True)

                response = requests.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    places_data = response.json()
                    places_result = {'results': places_data.get('places', [])}
                else:
                    print(f"Places API hatası: {response.status_code} - {response.text}", file=sys.stderr, flush=True)
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

            # ===== ALKOL FİLTRESİ SERVER-SIDE DOĞRULAMA (Gemini'den ÖNCE) =====
            # Bu kontrol Gemini'ye gitmeden ÖNCE yapılır ve kesin kurallara göre reddeder
            alcohol_filter = filters.get('alcohol', 'Any')

            # Alkollü mekan isteniyor ama coffee shop/cafe gelmiş → Reddet
            if alcohol_filter == 'Alcoholic':
                coffee_types = ['cafe', 'coffee_shop', 'bakery', 'coffee', 'tea_house', 'pastry_shop']
                if any(t in place_types for t in coffee_types):
                    print(f"❌ SERVER REJECT - Alcoholic filter but coffee shop: {place_name} (types: {place_types})", file=sys.stderr, flush=True)
                    continue  # Bu mekanı atla, Gemini'ye gönderme

            # Alkolsüz mekan isteniyor ama bar/pub gelmiş → Reddet
            elif alcohol_filter == 'Non-Alcoholic':
                alcohol_types = ['bar', 'pub', 'nightclub', 'wine_bar', 'liquor_store', 'cocktail_bar']
                if any(t in place_types for t in alcohol_types):
                    print(f"❌ SERVER REJECT - Non-Alcoholic filter but bar: {place_name} (types: {place_types})", file=sys.stderr, flush=True)
                    continue  # Bu mekanı atla, Gemini'ye gönderme

            # Gemini ile detaylı analiz ve kategori uygunluk kontrolü
            try:
                # Kullanıcı vibe filterlerini hazırla
                user_preferences = []
                if filters.get('groupSize'):
                    user_preferences.append(f"Grup Boyutu: {filters['groupSize']}")
                if filters.get('budget'):
                    user_preferences.append(f"Bütçe: {filters['budget']}")
                if filters.get('vibes'):
                    user_preferences.append(f"Vibe'lar: {', '.join(filters['vibes'])}")
                if filters.get('amenities'):
                    user_preferences.append(f"İmkanlar: {', '.join(filters['amenities'])}")

                # ÇOK ÖNEMLİ: Alkol/Sigara/Müzik filtreleri
                if filters.get('alcohol'):
                    user_preferences.append(f"🍷 Alkol: {filters['alcohol']}")
                if filters.get('liveMusic'):
                    user_preferences.append(f"🎵 Canlı Müzik: {filters['liveMusic']}")
                if filters.get('smoking'):
                    user_preferences.append(f"🚬 Sigara: {filters['smoking']}")
                if filters.get('environment'):
                    user_preferences.append(f"🏠 Ortam: {filters['environment']}")

                preferences_text = "\n".join(user_preferences) if user_preferences else "Belirtilmemiş"

                analysis_prompt = f"""
Sen bir mekan filtreleme asistanısın. Görevin: Verilen mekanın kullanıcı tercihlerine uygun olup olmadığını kontrol etmek.

MEKAN BİLGİSİ:
- İsim: {place_name}
- Tip: {', '.join(place_types[:3])}
- Rating: {place_rating}
- Fiyat: {price_range}

İSTENEN KATEGORİ: {category['name']}

KULLANICI FİLTRELERİ:
{preferences_text}

=== KRİTİK ALKOL FİLTRESİ KURALLARI (EN ÖNEMLİ) ===

ÖNEMLİ: Aşağıdaki kuralları HARFIYYEN uygula:

1. EĞER filtrelerde "🍷 Alkol: Alcoholic" VARSA:
   → Mekan tipi "cafe", "coffee_shop", "bakery", "coffee" içeriyorsa → MUTLAKA "isRelevant": false
   → Sadece "bar", "pub", "nightclub", "restaurant", "wine_bar" gibi alkol servisi yapan yerler → "isRelevant": true

2. EĞER filtrelerde "🍷 Alkol: Non-Alcoholic" VARSA:
   → Mekan tipi "bar", "pub", "nightclub", "wine_bar", "liquor_store" içeriyorsa → MUTLAKA "isRelevant": false
   → Sadece "cafe", "coffee_shop", "bakery", "tea_house" gibi alkolsüz yerler → "isRelevant": true

3. EĞER filtrelerde "🍷 Alkol: Any" VARSA veya alkol filtresi YOK ise:
   → Tüm mekan tipleri kabul edilir

=== SİGARA FİLTRESİ KURALLARI ===

4. EĞER filtrelerde "🚬 Sigara: Non-Smoking" VARSA:
   → Mekanda sigara içilebiliyorsa → "isRelevant": false
   → Mekan kapalı ve smokefree ise → "isRelevant": true

5. EĞER filtrelerde "🚬 Sigara: Allowed" VARSA:
   → Mekanda sigara içilemiyorsa → "isRelevant": false

6. EĞER filtrelerde "🚬 Sigara: Any" VARSA:
   → Her türlü mekan kabul edilir

=== ORTAM FİLTRESİ KURALLARI ===

7. EĞER filtrelerde "🏠 Ortam: Indoor" VARSA:
   → Tamamen açık hava mekanları → "isRelevant": false

8. EĞER filtrelerde "🏠 Ortam: Outdoor" VARSA:
   → Tamamen kapalı mekanlar → "isRelevant": false

9. EĞER filtrelerde "🏠 Ortam: Any" VARSA:
   → Her türlü mekan kabul edilir

=== CANLI MÜZİK FİLTRESİ ===

10. EĞER filtrelerde "🎵 Canlı Müzik: Yes" VARSA:
    → Canlı müzik yoksa → "isRelevant": false

11. EĞER filtrelerde "🎵 Canlı Müzik: No" VARSA:
    → Canlı müzik varsa → "isRelevant": false

12. EĞER filtrelerde "🎵 Canlı Müzik: Any" VARSA:
    → Her türlü mekan kabul edilir

=== KATEGORİ UYGUNLUĞU ===

- "İlk Buluşma": cafe, restaurant, bistro, wine_bar uygun → nightclub, gym uygun değil
- "Arkadaşlarla Takılma": bar, pub, restaurant, cafe uygun → hospital, bank uygun değil
- "İş Toplantısı": cafe, restaurant, hotel_bar uygun → nightclub, spa uygun değil

=== ÇIKTI FORMATI ===

Yukarıdaki FİLTRE KURALLARINI kontrol ettikten sonra JSON formatında döndür:

{{
    "isRelevant": true/false,
    "description": "Mekan açıklaması (Türkçe, 2 cümle)",
    "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
    "noiseLevel": 0-100,
    "matchScore": 0-100,
    "metrics": {{
        "ambiance": 0-100,
        "accessibility": 0-100,
        "popularity": 0-100
    }}
}}

ÖNEMLİ: Eğer ALKOL FİLTRESİ ihlal edildiyse (örn: "Alcoholic" ama mekan cafe), MUTLAKA "isRelevant": false döndür.

SADECE JSON döndür, başka hiçbir şey yazma.
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

                # Kategoriye uygun değilse skip et
                if not ai_data.get('isRelevant', True):
                    print(f"DEBUG - Skipping irrelevant venue: {place_name}", file=sys.stderr, flush=True)
                    continue

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
@permission_classes([permissions.AllowAny])
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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_similar_venues(request):
    """Tatil aktivitesi için benzer mekanlar getir (Google Places API)"""
    import json

    venue_name = request.data.get('venueName')
    venue_type = request.data.get('venueType')  # 'breakfast', 'lunch', 'dinner', 'cafe', 'bar', etc.
    location_query = request.data.get('location')  # 'Roma, İtalya'

    if not venue_name or not location_query:
        return Response(
            {'error': 'venueName ve location gerekli'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Venue type'a göre arama sorgusu oluştur
        type_query_map = {
            'breakfast': 'breakfast cafe brunch',
            'lunch': 'lunch restaurant trattoria',
            'dinner': 'dinner restaurant fine dining',
            'cafe': 'cafe coffee shop',
            'bar': 'bar pub cocktail',
            'dessert': 'dessert gelato pastry',
            'activity': 'attraction tourist spot',
        }

        search_type = type_query_map.get(venue_type, 'restaurant cafe')

        # Google Places API ile benzer mekanlar ara
        import requests
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.photos,places.priceLevel,places.types,places.location"
        }
        payload = {
            "textQuery": f"{search_type} in {location_query}",
            "languageCode": "tr",
            "maxResultCount": 10
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            return Response(
                {'error': f'Google Places API hatası: {response.status_code}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        places_data = response.json()
        places = places_data.get('places', [])

        # Her mekan için Gemini ile detaylı analiz
        similar_venues = []
        model = get_genai_model()

        for idx, place in enumerate(places[:8]):  # İlk 8 mekan
            place_name = place.get('displayName', {}).get('text', '')
            place_address = place.get('formattedAddress', '')
            place_rating = place.get('rating', 0)

            # Fotoğraf URL'si
            photo_url = None
            if place.get('photos') and len(place['photos']) > 0:
                photo_name = place['photos'][0].get('name', '')
                if photo_name:
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={settings.GOOGLE_MAPS_API_KEY}&maxWidthPx=800"

            # Fiyat seviyesi
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

            # Gemini ile açıklama oluştur
            description = f"{place_name}, {location_query} bölgesinde harika bir {venue_type} seçeneği."
            vibe_tags = ['#Popüler', '#Kaliteli']

            if model:
                try:
                    description_prompt = f"""
                    Mekan: {place_name}
                    Adres: {place_address}
                    Kategori: {venue_type}
                    Rating: {place_rating}

                    Bu mekan için:
                    1. 2 cümlelik Türkçe açıklama yaz (neden bu mekana gidilmeli?)
                    2. 3 adet vibe tag öner (örn: #Romantik, #Yerel, #Lüks)

                    JSON formatında döndür:
                    {{
                        "description": "...",
                        "vibeTags": ["#Tag1", "#Tag2", "#Tag3"]
                    }}
                    """

                    ai_response = model.generate_content(description_prompt)
                    ai_text = ai_response.text.strip()

                    if '```json' in ai_text:
                        ai_text = ai_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in ai_text:
                        ai_text = ai_text.split('```')[1].split('```')[0].strip()

                    ai_data = json.loads(ai_text)
                    description = ai_data.get('description', description)
                    vibe_tags = ai_data.get('vibeTags', vibe_tags)
                except:
                    pass

            venue_obj = {
                'id': f'similar_{idx + 1}',
                'name': place_name,
                'description': description,
                'imageUrl': photo_url or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4',
                'category': venue_type.capitalize(),
                'vibeTags': vibe_tags,
                'address': place_address,
                'priceRange': price_range,
                'googleRating': place_rating if place_rating > 0 else 4.0,
                'noiseLevel': 50,
                'matchScore': int(place_rating * 20) if place_rating > 0 else 80,
                'metrics': {
                    'noise': 50,
                    'light': 60,
                    'privacy': 55,
                    'service': 70,
                    'energy': 65
                }
            }

            similar_venues.append(venue_obj)

        return Response(similar_venues, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(f"Similar venues hatası: {e}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Benzer mekanlar getirilirken hata: {str(e)}'},
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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_travel_logistics(request):
    """
    Tatil için seyahat lojistiği seçeneklerini döndürür (uçak, feribot, otel, araç kiralama)
    Google Places API (Otel, Rent-a-car) ve Skyscanner API (Uçak) kullanır

    Request body:
    {
        "country": "Yunanistan",
        "city": "Sakız Adası",
        "days": 3,
        "transportationType": "ferry",
        "departureDate": "2025-07-15",
        "returnDate": "2025-07-18",
        "needsRentalCar": true,
        "needsHotel": true
    }
    """
    import random
    import requests

    try:
        data = request.data
        country = data.get('country', '')
        city = data.get('city', '')
        days = data.get('days', 3)
        transport_type = data.get('transportationType')
        needs_rental = data.get('needsRentalCar', False)
        needs_hotel = data.get('needsHotel', False)
        departure_date = data.get('departureDate')
        return_date = data.get('returnDate')

        response_data = {}
        location_query = f"{city}, {country}"

        # Transportation Options
        if transport_type and transport_type != 'own_car':
            response_data['transportation'] = {
                'type': transport_type,
                'departureDate': data.get('departureDate'),
                'returnDate': data.get('returnDate')
            }

            if transport_type == 'flight':
                # Skyscanner affiliate link oluştur
                # Format: https://www.skyscanner.com.tr/transport/flights/[origin]/[destination]/[outbound-date]/[return-date]/
                # Türkiye havalimanı kodları (en yaygın)
                origin_code = 'IST'  # İstanbul varsayılan

                # Destination code mapping (basitleştirilmiş)
                destination_mapping = {
                    'Roma': 'FCO',
                    'Milano': 'MXP',
                    'Paris': 'CDG',
                    'Barselona': 'BCN',
                    'Madrid': 'MAD',
                    'Atina': 'ATH',
                    'Selanik': 'SKG',
                    'Santorini': 'JTR',
                    'Mikonos': 'JMK',
                    'Rodos': 'RHO',
                    'Londra': 'LHR',
                    'Berlin': 'BER',
                    'Amsterdam': 'AMS'
                }

                dest_code = destination_mapping.get(city, 'ATH')  # Varsayılan Atina

                # Tarih formatı: YYMMDD
                dep_date_formatted = departure_date.replace('-', '')[2:] if departure_date else ''
                ret_date_formatted = return_date.replace('-', '')[2:] if return_date else ''

                skyscanner_link = f"https://www.skyscanner.com.tr/transport/flights/{origin_code}/{dest_code}/{dep_date_formatted}/{ret_date_formatted}/?adultsv2=1&cabinclass=economy&childrenv2=&inboundaltsenabled=false&outboundaltsenabled=false&preferdirects=false&ref=home&rtn=1"

                # Mock flight data (gerçek API olmadan)
                response_data['transportation']['flightOptions'] = [
                    {
                        'id': '1',
                        'airline': 'Turkish Airlines',
                        'departureTime': '10:30',
                        'arrivalTime': '12:45',
                        'duration': '2s 15dk',
                        'price': random.randint(1000, 1500),
                        'currency': '₺',
                        'affiliateLink': skyscanner_link
                    },
                    {
                        'id': '2',
                        'airline': 'Pegasus',
                        'departureTime': '14:20',
                        'arrivalTime': '16:30',
                        'duration': '2s 10dk',
                        'price': random.randint(800, 1200),
                        'currency': '₺',
                        'affiliateLink': skyscanner_link
                    },
                    {
                        'id': '3',
                        'airline': 'AnadoluJet',
                        'departureTime': '18:45',
                        'arrivalTime': '21:00',
                        'duration': '2s 15dk',
                        'price': random.randint(900, 1300),
                        'currency': '₺',
                        'affiliateLink': skyscanner_link
                    }
                ]

            elif transport_type == 'ferry':
                # Feribotlines affiliate link oluştur
                # Format: https://www.feribotlines.com/[route]
                # Türkiye limanları için

                # Feribotlines - Türkiye'de feribot rezervasyon platformu
                origin_port = 'cesme'  # Çeşme varsayılan (Yunan adaları için)

                # Destination port mapping
                ferry_destination_mapping = {
                    'Sakız': 'sakiz-adasi',
                    'Sakız Adası': 'sakiz-adasi',
                    'Samos': 'samos',
                    'Rodos': 'rodos',
                    'Kos': 'kos',
                    'Mikonos': 'mikonos',
                    'Santorini': 'santorini',
                    'Atina': 'pire',
                    'Girit': 'girit'
                }

                dest_port = ferry_destination_mapping.get(city, 'sakiz-adasi')

                # Feribotlines.com - Türk feribot rezervasyon sitesi
                feribotlines_link = f"https://www.feribotlines.com/{origin_port}-{dest_port}"

                # Alternatif: Sealines.com.tr
                sealines_link = f"https://www.sealines.com.tr/feribot/{origin_port}-{dest_port}"

                # Ferry companies in Aegean - Gerçek şirketler
                response_data['transportation']['ferryOptions'] = [
                    {
                        'id': '1',
                        'company': 'Ertürk Denizcilik',
                        'departureTime': '08:00',
                        'arrivalTime': '09:30',
                        'duration': '1s 30dk',
                        'price': random.randint(40, 60),
                        'currency': '€',
                        'affiliateLink': feribotlines_link
                    },
                    {
                        'id': '2',
                        'company': 'Turyol',
                        'departureTime': '12:30',
                        'arrivalTime': '14:15',
                        'duration': '1s 45dk',
                        'price': random.randint(35, 50),
                        'currency': '€',
                        'affiliateLink': feribotlines_link
                    },
                    {
                        'id': '3',
                        'company': 'Meander Travel',
                        'departureTime': '16:00',
                        'arrivalTime': '17:20',
                        'duration': '1s 20dk',
                        'price': random.randint(45, 65),
                        'currency': '€',
                        'affiliateLink': sealines_link
                    }
                ]

        # Rental Car Options - Google Places API
        if needs_rental:
            try:
                # Google Places API ile araç kiralama firmalarını bul
                places_url = "https://places.googleapis.com/v1/places:searchText"
                places_headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.photos"
                }
                places_payload = {
                    "textQuery": f"car rental in {location_query}",
                    "languageCode": "tr",
                    "maxResultCount": 10
                }

                places_response = requests.post(places_url, json=places_payload, headers=places_headers)

                rental_options = []
                car_types = ['Fiat Egea', 'Renault Clio', 'Volkswagen Golf', 'Hyundai i20', 'Toyota Corolla']
                transmissions = ['manual', 'automatic']

                if places_response.status_code == 200:
                    places_data = places_response.json()
                    rental_companies = places_data.get('places', [])[:5]  # İlk 5 firma

                    for idx, company in enumerate(rental_companies):
                        company_name = company.get('displayName', {}).get('text', f'Rental Company {idx+1}')

                        # Bilinen firmalara normalize et
                        normalized_name = company_name
                        if 'europcar' in company_name.lower():
                            normalized_name = 'Europcar'
                        elif 'budget' in company_name.lower():
                            normalized_name = 'Budget'
                        elif 'avis' in company_name.lower():
                            normalized_name = 'Avis'
                        elif 'enterprise' in company_name.lower():
                            normalized_name = 'Enterprise'
                        elif 'hertz' in company_name.lower():
                            normalized_name = 'Hertz'

                        car_type = car_types[idx % len(car_types)]
                        transmission = transmissions[idx % len(transmissions)]

                        # Fiyat hesaplama (transmisyon tipine göre)
                        base_price = random.randint(250, 350)
                        if transmission == 'automatic':
                            base_price += 70

                        # Fotoğraf - araç tipine göre
                        car_images = {
                            'Fiat Egea': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400',
                            'Renault Clio': 'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=400',
                            'Volkswagen Golf': 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400',
                            'Hyundai i20': 'https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=400',
                            'Toyota Corolla': 'https://images.unsplash.com/photo-1623869675781-80aa31592804?w=400'
                        }
                        car_image = car_images.get(car_type, 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400')

                        # Rentalcars.com affiliate link
                        city_encoded = city.replace(' ', '+')
                        rentalcars_link = f"https://www.rentalcars.com/SearchResults.do?doSrpModal=false&location={city_encoded}&dropOff={city_encoded}&pickUpDate={departure_date}&dropOffDate={return_date}"

                        rental_options.append({
                            'id': str(idx + 1),
                            'company': normalized_name,
                            'carType': car_type,
                            'transmission': transmission,
                            'pricePerDay': base_price,
                            'currency': '₺',
                            'affiliateLink': rentalcars_link,
                            'imageUrl': car_image
                        })
                else:
                    # API başarısız olursa fallback
                    rental_options = [
                        {
                            'id': '1',
                            'company': 'Europcar',
                            'carType': 'Fiat Egea',
                            'transmission': 'manual',
                            'pricePerDay': 280,
                            'currency': '₺',
                            'affiliateLink': f'https://www.rentalcars.com/SearchResults.do?location={city}',
                            'imageUrl': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400'
                        },
                        {
                            'id': '2',
                            'company': 'Budget',
                            'carType': 'Renault Clio',
                            'transmission': 'automatic',
                            'pricePerDay': 350,
                            'currency': '₺',
                            'affiliateLink': f'https://www.rentalcars.com/SearchResults.do?location={city}',
                            'imageUrl': 'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=400'
                        }
                    ]

                response_data['rentalCar'] = {
                    'requested': True,
                    'options': rental_options[:5]  # Max 5 seçenek
                }
            except Exception as e:
                print(f"Rental car API error: {e}")
                # Fallback to mock data
                response_data['rentalCar'] = {
                    'requested': True,
                    'options': [{
                        'id': '1',
                        'company': 'Europcar',
                        'carType': 'Fiat Egea',
                        'transmission': 'manual',
                        'pricePerDay': 280,
                        'currency': '₺',
                        'affiliateLink': f'https://www.rentalcars.com/SearchResults.do?location={city}',
                        'imageUrl': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400'
                    }]
                }

        # Hotel Options - Google Places API
        if needs_hotel:
            try:
                # Google Places API ile otel arama
                places_url = "https://places.googleapis.com/v1/places:searchText"
                places_headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.editorialSummary"
                }
                places_payload = {
                    "textQuery": f"hotels in {location_query}",
                    "languageCode": "tr",
                    "maxResultCount": 10
                }

                places_response = requests.post(places_url, json=places_payload, headers=places_headers)

                hotel_options = []
                if places_response.status_code == 200:
                    places_data = places_response.json()
                    hotels = places_data.get('places', [])[:5]  # İlk 5 otel

                    for idx, hotel in enumerate(hotels):
                        hotel_name = hotel.get('displayName', {}).get('text', f'{city} Hotel {idx+1}')
                        hotel_address = hotel.get('formattedAddress', f'{city}, {country}')
                        hotel_rating = hotel.get('rating', 4.0)
                        review_count = hotel.get('userRatingCount', 0)

                        # Fotoğraf URL'si
                        photo_url = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600'
                        if hotel.get('photos') and len(hotel['photos']) > 0:
                            photo_name = hotel['photos'][0].get('name', '')
                            if photo_name:
                                photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={settings.GOOGLE_MAPS_API_KEY}&maxWidthPx=800"

                        # Fiyat tahmini (Google Places genelde fiyat döndürmez, tahmini oluşturuyoruz)
                        price_level_str = hotel.get('priceLevel', 'PRICE_LEVEL_MODERATE')
                        price_map = {
                            'PRICE_LEVEL_FREE': random.randint(300, 500),
                            'PRICE_LEVEL_INEXPENSIVE': random.randint(500, 800),
                            'PRICE_LEVEL_MODERATE': random.randint(800, 1200),
                            'PRICE_LEVEL_EXPENSIVE': random.randint(1200, 2000),
                            'PRICE_LEVEL_VERY_EXPENSIVE': random.randint(2000, 3500)
                        }
                        estimated_price = price_map.get(price_level_str, random.randint(700, 1200))

                        # Booking.com affiliate link oluştur
                        hotel_name_encoded = hotel_name.replace(' ', '+')
                        city_encoded = city.replace(' ', '+')
                        booking_link = f"https://www.booking.com/searchresults.html?ss={hotel_name_encoded}+{city_encoded}&checkin={departure_date}&checkout={return_date}"

                        # Amenities (varsayılan)
                        amenities = ['WiFi', 'Kahvaltı', 'Klima']
                        if hotel_rating >= 4.5:
                            amenities.extend(['Havuz', 'Spa'])
                        if 'beach' in hotel_address.lower() or 'sahil' in hotel_address.lower():
                            amenities.append('Deniz Manzarası')

                        hotel_options.append({
                            'id': str(idx + 1),
                            'name': hotel_name,
                            'rating': round(hotel_rating, 1),
                            'pricePerNight': estimated_price,
                            'currency': '₺',
                            'affiliateLink': booking_link,
                            'location': hotel_address,
                            'imageUrl': photo_url,
                            'amenities': amenities[:4],  # Max 4 amenity
                            'reviewCount': review_count
                        })
                else:
                    # API başarısız olursa fallback mock data
                    hotel_options = [
                        {
                            'id': '1',
                            'name': f'{city} Grand Palace Hotel',
                            'rating': 4.5,
                            'pricePerNight': 1000,
                            'currency': '₺',
                            'affiliateLink': f'https://www.booking.com/searchresults.html?ss={city}',
                            'location': f'Merkez, {city}',
                            'imageUrl': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600',
                            'amenities': ['WiFi', 'Kahvaltı', 'Havuz', 'Spa']
                        }
                    ]

                response_data['accommodation'] = {
                    'requested': True,
                    'options': hotel_options
                }
            except Exception as e:
                print(f"Hotel API error: {e}")
                # Fallback to mock data on error
                response_data['accommodation'] = {
                    'requested': True,
                    'options': [{
                        'id': '1',
                        'name': f'{city} Hotel',
                        'rating': 4.0,
                        'pricePerNight': 800,
                        'currency': '₺',
                        'affiliateLink': f'https://www.booking.com/searchresults.html?ss={city}',
                        'location': f'{city}, {country}',
                        'imageUrl': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600',
                        'amenities': ['WiFi', 'Kahvaltı']
                    }]
                }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(f"Travel logistics hatası: {e}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Seyahat lojistiği getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
