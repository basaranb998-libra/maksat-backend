from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
import googlemaps
import google.generativeai as genai
import urllib.parse

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
        # Gemini 2.0 Flash - Render free tier için optimize
        return genai.GenerativeModel('gemini-2.0-flash')
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
        # Kısa ve öz tatil prompt'u
        experience_prompt = f"""
Sen "{location_query}" için {duration} günlük tatil rotası hazırlayan bir seyahat uzmanısın.

Her gün için 6 aktivite öner: kahvaltı, sabah gezisi, öğle yemeği, öğleden sonra aktivitesi, akşam yemeği, gece aktivitesi.

JSON ARRAY formatında döndür. Her aktivite şu alanlara sahip olmalı:
- id: "day1_1", "day1_2" formatında
- name: Aktivite adı (örn: "Pantheon'u ziyaret et")
- description: 1-2 cümle açıklama
- imageUrl: Unsplash URL (https://images.unsplash.com/photo-...)
- category: "Tatil"
- vibeTags: 3 hashtag array
- address: Tam adres
- priceRange: "$", "$$" veya "$$$"
- googleRating: 4.0-5.0 arası
- noiseLevel: 30-70 arası
- matchScore: 75-95 arası
- itineraryDay: Gün numarası (1, 2, 3...)
- timeSlot: "08:30-09:30" formatında
- duration: "1 saat" formatında
- isSpecificVenue: true/false
- venueName: Mekan ismi (isSpecificVenue=true ise)
- activityType: breakfast/lunch/dinner/sightseeing/shopping/activity
- metrics: {{"ambiance": 80, "accessibility": 85, "popularity": 90}}

Toplam {duration * 6} aktivite döndür. SADECE JSON ARRAY, başka açıklama yok.
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


def generate_michelin_restaurants(location, filters):
    """Michelin Yıldızlı kategorisi için Michelin Guide'dan veri çekme"""
    import json
    import sys

    city = location['city']
    city_slug = city.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

    model = get_genai_model()
    if not model:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        # Gemini'ye Michelin Guide bilgisi ile restoran listesi oluşturmasını iste
        michelin_prompt = f"""
{city} şehrindeki Michelin Guide 2024 restoranlarını listele.

Michelin Guide Türkiye'de {city} için:
- Michelin Yıldızlı restoranlar (1, 2 veya 3 yıldız)
- Bib Gourmand restoranlar
- Michelin Tavsiyeli (Selected) restoranlar

EN AZ 15 RESTORAN LİSTELE. Eğer {city}'de yeterli Michelin restoranı yoksa, yakın bölgelerden (Urla, Çeşme, Alaçatı, Foça vb.) de ekle.

JSON ARRAY formatında döndür. Her restoran:
{{"id": "michelin_1", "name": "Restoran Adı", "description": "2 cümle açıklama", "imageUrl": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800", "category": "Michelin Yıldızlı", "vibeTags": ["#MichelinGuide", "#FineDining", "#Restoran"], "address": "Tam adres, {city}", "priceRange": "$$$", "googleRating": 4.7, "noiseLevel": 35, "matchScore": 92, "googleMapsUrl": "", "michelinStatus": "Michelin Tavsiyeli", "metrics": {{"ambiance": 90, "accessibility": 85, "popularity": 95}}}}

SADECE JSON ARRAY döndür. Minimum 15 restoran."""

        print(f"🍽️ Michelin Guide araması: {city}", file=sys.stderr, flush=True)

        response = model.generate_content(michelin_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        restaurants = json.loads(response_text)

        # Google Maps URL ekle
        for restaurant in restaurants:
            search_query = urllib.parse.quote(f"{restaurant['name']} {city} restaurant")
            restaurant['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(restaurants)} Michelin restoran bulundu", file=sys.stderr, flush=True)

        return Response(restaurants, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Michelin restaurant generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Michelin restoranları getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_local_festivals(location, filters):
    """Yerel Festivaller kategorisi için festival ve etkinlik listesi"""
    import json
    import sys
    from datetime import datetime, timedelta

    city = location['city']
    today = datetime.now()
    current_date = today.strftime("%d %B %Y")  # "13 December 2024"

    # dateRange filtresine göre tarih aralığını belirle
    date_range = filters.get('dateRange', 'Any')

    if date_range == 'ThisWeek':
        end_date = today + timedelta(days=7)
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki (bu hafta içindeki) etkinlikleri listele."
    elif date_range == 'ThisMonth':
        end_date = today + timedelta(days=30)
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki (bu ay içindeki) etkinlikleri listele."
    elif date_range == 'Next6Months':
        end_date = today + timedelta(days=180)
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki (6 ay içindeki) etkinlikleri listele."
    else:  # Any
        end_date = today + timedelta(days=180)
        date_constraint = f"{current_date} ile {end_date.strftime('%d %B %Y')} arasındaki (6 ay içindeki) etkinlikleri listele."

    model = get_genai_model()
    if not model:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        festival_prompt = f"""
{city} ve çevresinde yaklaşan festivaller ve etkinlikleri listele.

BUGÜNÜN TARİHİ: {current_date}

TARİH KURALI (ÇOK ÖNEMLİ!):
{date_constraint}
GEÇMİŞ TARİHLİ veya BELİRTİLEN ARALIK DIŞINDA FESTİVAL LİSTELEME!

Festival türleri:
- Gastronomi festivalleri (yemek, şarap, zeytinyağı vb.)
- Müzik festivalleri
- Kültür ve sanat festivalleri
- Hasat festivalleri
- Yerel geleneksel festivaller

EN AZ 12 FESTİVAL LİSTELE.

JSON ARRAY formatında döndür. Her festival:
{{"id": "festival_1", "name": "Festival Adı", "description": "2 cümle açıklama - ne tür festival, ne yapılıyor", "imageUrl": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=800", "category": "Yerel Festivaller", "vibeTags": ["#Festival", "#Gastronomi", "#YerelLezzet"], "address": "Festival lokasyonu, {city}", "priceRange": "$$", "googleRating": 4.5, "noiseLevel": 65, "matchScore": 88, "googleMapsUrl": "", "isEvent": true, "eventDate": "15-17 Ocak 2025", "ticketUrl": "", "metrics": {{"ambiance": 85, "accessibility": 80, "popularity": 90}}}}

SADECE JSON ARRAY döndür. Minimum 12 festival."""

        print(f"🎪 Yerel Festivaller araması: {city}", file=sys.stderr, flush=True)
        print(f"📅 Tarih filtresi: {date_range} -> {date_constraint}", file=sys.stderr, flush=True)

        response = model.generate_content(festival_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        festivals = json.loads(response_text)

        # Google Maps URL ekle
        for festival in festivals:
            search_query = urllib.parse.quote(f"{festival['name']} {city} festival")
            festival['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(festivals)} festival bulundu", file=sys.stderr, flush=True)

        return Response(festivals, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Festival generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Festivaller getirilirken hata: {str(e)}'},
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

        # Michelin Yıldızlı kategorisi için özel işlem
        if category['name'] == 'Michelin Yıldızlı':
            return generate_michelin_restaurants(location, filters)

        # Yerel Festivaller kategorisi için özel işlem
        if category['name'] == 'Yerel Festivaller':
            return generate_local_festivals(location, filters)

        # Kategori bazlı query mapping (Tatil, Michelin ve Festivaller hariç)
        # ALKOL FİLTRESİNE GÖRE DİNAMİK QUERY OLUŞTUR
        alcohol_filter = filters.get('alcohol', 'Any')

        if alcohol_filter == 'Alcoholic':
            # Alkollü mekan seçilirse SADECE bar, pub, restaurant, wine bar ara
            category_query_map = {
                'İlk Buluşma': 'bar wine bar restaurant pub',
                'İş Yemeği': 'restaurant bar hotel lounge business lunch',
                'Muhabbet': 'bar pub lounge restaurant wine bar',
                'İş Çıkışı Bira & Kokteyl': 'bar pub cocktail bar beer garden',
                'Eğlence & Parti': 'nightclub bar pub dance club',
                'Özel Gün': 'fine dining restaurant wine bar romantic',
                'Kahvaltı & Brunch': 'brunch restaurant bar mimosa',
                'Kafa Dinleme': 'lounge bar quiet restaurant',
                'Odaklanma': 'bar restaurant lounge',
                'Aile Yemeği': 'restaurant bar casual dining',
                '3. Nesil Kahveci': 'wine bar restaurant',
                'Konserler': 'live music venue concert hall bar',
                'Sahne Sanatları': 'theater venue performance hall',
                'Yerel Festivaller': 'festival event venue',
                'Müze': 'museum gallery',
                'Hafta Sonu Gezintisi': 'winery vineyard restaurant',
                'Piknik': 'park garden outdoor',
                'Beach Club': 'beach club bar restaurant',
                'Plaj': 'beach bar restaurant',
                'Adrenalin': 'adventure sports extreme',
                'Spor': 'gym fitness yoga studio',
                'Fine Dining': 'fine dining restaurant wine bar',
                'Michelin Yıldızlı': 'fine dining gourmet restaurant luxury upscale',
            }
        elif alcohol_filter == 'Non-Alcoholic':
            # Alkolsüz mekan seçilirse SADECE cafe, bakery, coffee shop ara
            category_query_map = {
                'İlk Buluşma': 'cafe coffee shop bakery tea house',
                'İş Yemeği': 'business lunch cafe restaurant coffee shop',
                'Muhabbet': 'cafe coffee shop tea house quiet cafe',
                'İş Çıkışı Bira & Kokteyl': 'cafe coffee shop juice bar',
                'Eğlence & Parti': 'entertainment center arcade bowling',
                'Özel Gün': 'restaurant cafe patisserie',
                'Kahvaltı & Brunch': 'breakfast cafe brunch spot bakery',
                'Kafa Dinleme': 'quiet cafe tea house peaceful spot',
                'Odaklanma': 'coworking space cafe library quiet study',
                'Aile Yemeği': 'family restaurant cafe casual dining',
                '3. Nesil Kahveci': 'specialty coffee third wave coffee roastery',
                'Konserler': 'concert hall music venue',
                'Sahne Sanatları': 'theater venue performance hall',
                'Yerel Festivaller': 'festival event venue',
                'Müze': 'museum gallery exhibition',
                'Hafta Sonu Gezintisi': 'scenic spot nature walk daytrip',
                'Piknik': 'park garden picnic area',
                'Beach Club': 'beach club resort',
                'Plaj': 'beach seaside',
                'Adrenalin': 'adventure sports extreme activities',
                'Spor': 'gym fitness yoga studio pilates',
                'Fine Dining': 'fine dining restaurant',
                'Michelin Yıldızlı': 'fine dining gourmet restaurant upscale',
            }
        else:
            # Any seçilirse her türlü mekan (varsayılan)
            category_query_map = {
                'İlk Buluşma': 'cafe restaurant bar wine bar coffee shop',
                'İş Yemeği': 'business lunch restaurant cafe meeting spot',
                'Muhabbet': 'cafe bar lounge restaurant cozy spot conversation friendly',
                'İş Çıkışı Bira & Kokteyl': 'bar pub cocktail bar beer garden after work drinks',
                'Eğlence & Parti': 'nightclub bar pub dance club entertainment',
                'Özel Gün': 'fine dining restaurant romantic celebration',
                'Kahvaltı & Brunch': 'breakfast cafe brunch spot bakery',
                'Kafa Dinleme': 'quiet cafe lounge peaceful spot relaxing',
                'Odaklanma': 'coworking space cafe library quiet study',
                'Aile Yemeği': 'family restaurant casual dining kid friendly',
                '3. Nesil Kahveci': 'specialty coffee third wave coffee roastery artisan',
                'Konserler': 'live music venue concert hall',
                'Sahne Sanatları': 'theater venue stand up comedy performance',
                'Yerel Festivaller': 'festival event food festival',
                'Müze': 'museum gallery art exhibition',
                'Hafta Sonu Gezintisi': 'scenic spot nature daytrip excursion',
                'Piknik': 'park garden picnic area green space',
                'Beach Club': 'beach club resort pool bar',
                'Plaj': 'beach seaside coast',
                'Adrenalin': 'adventure sports extreme activities outdoor',
                'Spor': 'gym fitness yoga studio pilates wellness',
                'Fine Dining': 'fine dining restaurant upscale gourmet',
                'Michelin Yıldızlı': 'fine dining gourmet restaurant luxury upscale tasting menu',
            }

        # Kategori ve filtrelere göre arama sorgusu oluştur
        search_query = category_query_map.get(category['name'], category['name'])

        # Filtrelere göre sorguyu genişlet
        if filters.get('vibes'):
            search_query += f" {' '.join(filters['vibes'])}"

        # Lokasyon oluştur
        city = location['city']
        districts = location.get('districts', [])
        selected_district = districts[0] if districts else None
        search_location = f"{selected_district}, {city}" if selected_district else city
        import sys
        print(f"DEBUG - Selected District: {selected_district}", file=sys.stderr, flush=True)
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

        # ===== PHASE 1: Google Places'dan mekanları topla ve ön-filtrele =====
        venues = []
        filtered_places = []
        alcohol_filter = filters.get('alcohol', 'Any')

        for idx, place in enumerate(places_result.get('results', [])[:20]):
            place_id = place.get('id', f"place_{idx}")
            place_name = place.get('displayName', {}).get('text', '')
            place_address = place.get('formattedAddress', '')
            place_rating = place.get('rating', 0)
            place_types = place.get('types', [])

            # ===== İLÇE FİLTRESİ: Seçilen ilçeye ait olmayan mekanları atla =====
            if selected_district:
                # Adres içinde ilçe adı var mı kontrol et (büyük/küçük harf duyarsız)
                address_lower = place_address.lower()
                district_lower = selected_district.lower()
                # Türkçe karakterleri normalize et
                district_normalized = district_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                address_normalized = address_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                if district_lower not in address_lower and district_normalized not in address_normalized:
                    print(f"❌ İLÇE REJECT - {place_name} adresi '{selected_district}' içermiyor: {place_address}", file=sys.stderr, flush=True)
                    continue

            # Fotoğraf URL'si
            photo_url = None
            if place.get('photos') and len(place['photos']) > 0:
                photo_name = place['photos'][0].get('name', '')
                if photo_name:
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={settings.GOOGLE_MAPS_API_KEY}&maxWidthPx=800"

            # Google Maps URL
            maps_query = urllib.parse.quote(f"{place_name} {place_address}")
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

            # Fiyat aralığı
            price_level_str = place.get('priceLevel', 'PRICE_LEVEL_MODERATE')
            price_level_map = {
                'PRICE_LEVEL_FREE': 1, 'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2, 'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4
            }
            price_level = price_level_map.get(price_level_str, 2)
            price_map = {1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
            price_range = price_map.get(price_level, '$$')

            # Budget filtresine göre kontrol
            budget_filter = filters.get('budget')
            if budget_filter:
                budget_map = {'Ekonomik': [1, 2], 'Orta': [2, 3], 'Lüks': [3, 4]}
                if budget_filter in budget_map and price_level not in budget_map[budget_filter]:
                    continue

            # ===== ALKOL FİLTRESİ SERVER-SIDE DOĞRULAMA =====
            # Mekan ismini küçük harfe çevir (Türkçe karakterleri normalize et)
            place_name_lower = place_name.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
            place_types_str = ' '.join(place_types).lower()

            if alcohol_filter == 'Alcoholic':
                # Kahve/kafe mekanlarını filtrele - hem types hem isimde kontrol et
                coffee_keywords = ['cafe', 'coffee', 'kahve', 'kafe', 'bakery', 'tea_house', 'pastry', 'patisserie', 'firin', 'borek']

                # Types içinde varsa filtrele
                if any(keyword in place_types_str for keyword in coffee_keywords):
                    print(f"❌ ALKOL REJECT (type) - {place_name}: types={place_types}", file=sys.stderr, flush=True)
                    continue

                # İsimde "cafe", "coffee", "kahve" varsa ve bar/pub içermiyorsa filtrele
                is_coffee_name = any(keyword in place_name_lower for keyword in ['cafe', 'coffee', 'kahve', 'kafe'])
                is_bar_name = any(keyword in place_name_lower for keyword in ['bar', 'pub', 'bira', 'meyhane', 'wine'])
                if is_coffee_name and not is_bar_name:
                    print(f"❌ ALKOL REJECT (isim) - {place_name}: kahve/kafe isimli", file=sys.stderr, flush=True)
                    continue

            elif alcohol_filter == 'Non-Alcoholic':
                # Alkollü mekanları filtrele - hem types hem isimde kontrol et
                alcohol_keywords = ['bar', 'pub', 'nightclub', 'wine_bar', 'liquor', 'cocktail', 'meyhane', 'bira']

                # Types içinde varsa filtrele
                if any(keyword in place_types_str for keyword in alcohol_keywords):
                    print(f"❌ ALKOLSÜZ REJECT (type) - {place_name}: types={place_types}", file=sys.stderr, flush=True)
                    continue

                # İsimde "bar", "pub", "meyhane" varsa filtrele
                if any(keyword in place_name_lower for keyword in ['bar', 'pub', 'meyhane', 'bira', 'wine', 'cocktail']):
                    print(f"❌ ALKOLSÜZ REJECT (isim) - {place_name}: alkollü isimli", file=sys.stderr, flush=True)
                    continue

            # Filtreyi geçen mekanları topla
            filtered_places.append({
                'idx': idx,
                'name': place_name,
                'address': place_address,
                'rating': place_rating,
                'types': place_types,
                'photo_url': photo_url,
                'google_maps_url': google_maps_url,
                'price_range': price_range
            })

        # ===== PHASE 2: TEK BİR BATCH GEMİNİ ÇAĞRISI =====
        if filtered_places:
            # Kullanıcı tercihlerini hazırla
            user_preferences = []
            if filters.get('groupSize') and filters['groupSize'] != 'Any':
                user_preferences.append(f"Grup: {filters['groupSize']}")
            if filters.get('alcohol') and filters['alcohol'] != 'Any':
                user_preferences.append(f"ALKOL: {filters['alcohol']}")
            if filters.get('liveMusic') and filters['liveMusic'] != 'Any':
                user_preferences.append(f"CANLI MÜZİK: {filters['liveMusic']}")
            if filters.get('smoking') and filters['smoking'] != 'Any':
                user_preferences.append(f"SİGARA: {filters['smoking']}")
            if filters.get('environment') and filters['environment'] != 'Any':
                user_preferences.append(f"ORTAM: {filters['environment']}")

            preferences_text = ", ".join(user_preferences) if user_preferences else "Özel tercih yok"
            print(f"📋 Gemini BATCH çağrısı - {len(filtered_places)} mekan, filtreler: {preferences_text}", file=sys.stderr, flush=True)

            # Tüm mekanları tek bir prompt'ta gönder
            places_list = "\n".join([
                f"{i+1}. {p['name']} | Tip: {', '.join(p['types'][:2])}"
                for i, p in enumerate(filtered_places[:10])  # Max 10 mekan
            ])

            batch_prompt = f"""Kategori: {category['name']}
Filtreler: {preferences_text}

Aşağıdaki mekanları analiz et ve her biri için JSON döndür:
{places_list}

Her mekan için şu formatta JSON objesi oluştur:
{{"name": "Mekan Adı", "isRelevant": true/false, "description": "2 cümle Türkçe açıklama", "vibeTags": ["#Tag1", "#Tag2", "#Tag3"], "noiseLevel": 30-70, "matchScore": 75-95}}

JSON ARRAY olarak döndür. Sadece uygun mekanları dahil et. SADECE JSON ARRAY, başka bir şey yazma."""

            try:
                model = get_genai_model()
                if model:
                    response = model.generate_content(batch_prompt)
                    response_text = response.text.strip()

                    # JSON parse
                    if '```json' in response_text:
                        response_text = response_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in response_text:
                        response_text = response_text.split('```')[1].split('```')[0].strip()

                    ai_results = json.loads(response_text)

                    # AI sonuçlarını mekanlarla eşleştir
                    ai_by_name = {r.get('name', '').lower(): r for r in ai_results}

                    for place in filtered_places[:10]:
                        ai_data = ai_by_name.get(place['name'].lower(), {})

                        # Uygun değilse skip
                        if ai_data and not ai_data.get('isRelevant', True):
                            continue

                        venue = {
                            'id': f"v{place['idx'] + 1}",
                            'name': place['name'],
                            'description': ai_data.get('description', f"{category['name']} için harika bir mekan."),
                            'imageUrl': place['photo_url'] or 'https://via.placeholder.com/800x600',
                            'category': category['name'],
                            'vibeTags': ai_data.get('vibeTags', ['#Popüler', '#Kaliteli']),
                            'address': place['address'],
                            'priceRange': place['price_range'],
                            'googleRating': place['rating'] if place['rating'] > 0 else 4.0,
                            'noiseLevel': ai_data.get('noiseLevel', 50),
                            'matchScore': ai_data.get('matchScore', 80),
                            'googleMapsUrl': place['google_maps_url'],
                            'metrics': {'ambiance': 80, 'accessibility': 85, 'popularity': 75}
                        }
                        venues.append(venue)

                    print(f"✅ Gemini batch sonucu: {len(venues)} mekan", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"❌ Gemini batch hatası: {e}", file=sys.stderr, flush=True)
                # Fallback: Gemini olmadan mekanları ekle
                for place in filtered_places[:10]:
                    venue = {
                        'id': f"v{place['idx'] + 1}",
                        'name': place['name'],
                        'description': f"{category['name']} için harika bir mekan seçeneği.",
                        'imageUrl': place['photo_url'] or 'https://via.placeholder.com/800x600',
                        'category': category['name'],
                        'vibeTags': ['#Popüler', '#Kaliteli'],
                        'address': place['address'],
                        'priceRange': place['price_range'],
                        'googleRating': place['rating'] if place['rating'] > 0 else 4.0,
                        'noiseLevel': 50,
                        'matchScore': 75,
                        'googleMapsUrl': place['google_maps_url'],
                        'metrics': {'ambiance': 75, 'accessibility': 80, 'popularity': 70}
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
