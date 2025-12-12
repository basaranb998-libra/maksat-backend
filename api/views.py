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
        # Gemini 2.5 Flash model - cost-effective option
        return genai.GenerativeModel('gemini-2.5-flash')
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
        # Yeni deneyim odaklı prompt - Gemini kendisi araştırsın
        experience_prompt = f"""
Sen "{location_query}" şehrini avucunun içi gibi bilen, cool ve deneyim odaklı bir 'Lokal Rehber'sin.

🎯 GÖREV: {duration} günlük, NOKTA ATIŞI deneyim listesi hazırla.

## ÖNEMLİ: "Sadece Mekan Değil, DENEYİM Öner"
❌ Kötü: "Louvre Müzesi"
✅ İyi: "Louvre'da Mona Lisa'yı gör ve selfie çek"
✅ İyi: "Trocadéro Bahçesi'nden Eyfel Kulesi manzarasıyla kahvaltı"

## NASIL YAPACAKSIN?
1. Kendi bilgin ve verilerinle "{location_query}" hakkında düşün:
   - En ünlü 3-5 landmark nedir?
   - Yerel halkın gittiği en iyi yemek mekanları neresi?
   - Turistik olmayan gizli yerler var mı?
   - Hangi mahalleler birbirine yakın?

2. Günlük Plan Yap:
   - SABAH (09:00-12:00): Kahvaltı + Aktivite/Müze
   - ÖĞLEN (12:00-15:00): Öğle yemeği + Gezinti
   - AKŞAM (18:00-22:00): Akşam yemeği/Bar/Gece hayatı
   - Her gün FARKLI bölgelerde olsun ama aynı gün içinde yakın yerler

3. Deneyim İsimlendirme:
   Format: "[Mekan]'da/de [AKSİYON]"
   Örnekler:
   - "Galata Kulesi'nde gün batımı izle"
   - "Karaköy Lokantası'nda döner ye"
   - "Ulus Parkı'nda piknik yap"
   - "Konyaaltı Plajı'nda denize gir"

## ÇIKTI FORMATI (JSON ARRAY)
[
  {{
    "id": "exp_1",
    "name": "[Mekan İsmi]'nda/de [Ne Yapılacak]",
    "description": "2-3 cümle: Neden gidilmeli? Ne özel?",
    "imageUrl": "https://images.unsplash.com/photo-[şehir-ile-ilgili-gerçek-unsplash-ID]",
    "category": "Tatil",
    "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
    "address": "Tam adres, {location_query}",
    "priceRange": "$$",
    "googleRating": 4.5,
    "noiseLevel": 40,
    "matchScore": 85,
    "itineraryDay": 1,
    "metrics": {{"ambiance": 85, "accessibility": 90, "popularity": 80}}
  }}
]

## KISITLAMALAR
✅ {duration * 3} ile {duration * 4} ARASI deneyim döndür (her gün 3-4 deneyim)
✅ Her gün SABAH, ÖĞLEN, AKŞAM dengesi olsun
✅ Aynı gün içindeki yerler birbirine YAKIN olsun (max 5-10km)
✅ Gerçek mekan isimleri kullan
✅ imageUrl için Unsplash'ten {location_query} ile ilgili gerçek fotoğraf URL'leri bul
✅ SADECE JSON döndür, başka hiçbir açıklama ekleme

Başla!
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

    try:
        # Tatil kategorisi için özel işlem
        if category['name'] == 'Tatil':
            # Tatil kategorisi için deneyim bazlı öneri sistemi
            return generate_vacation_experiences(location, trip_duration, filters)

        # DİNAMİK GOOGLE PLACES SORGUSU - Kategori + Vibe Kombinasyonu
        # Kullanıcının vibe ve kategori seçimlerine göre HASSAS sorgu oluştur

        category_name = category['name']
        vibes = filters.get('vibes', [])
        alcohol_pref = filters.get('alcohol', '')
        amenities = filters.get('amenities', [])

        # Temel kategori sorgusu
        base_queries = {
            'İlk Buluşma': 'cafe restaurant coffee shop',
            'İş Toplantısı': 'business cafe hotel lounge',
            'Arkadaşlarla Takılma': 'bar pub restaurant lounge',
            'Aile Yemeği': 'family restaurant',
            'Romantik Akşam': 'romantic restaurant fine dining',
            'Çalışma': 'cafe coworking library',
        }

        search_query = base_queries.get(category_name, category_name)

        # ALKOL TERCİHİNE GÖRE SORGUYU GÜÇLÜ ŞEKİLDE DEĞİŞTİR
        if alcohol_pref == 'Alcoholic':
            # Alkollü mekan isteniyorsa bar/pub önceliklendir
            if category_name == 'İlk Buluşma':
                search_query = 'wine bar cocktail bar pub restaurant bar'  # Cafe/coffee shop KALDIR
            elif category_name == 'Arkadaşlarla Takılma':
                search_query = 'bar pub cocktail lounge nightlife'
            elif category_name == 'Romantik Akşam':
                search_query = 'wine bar romantic restaurant cocktail bar'
        elif alcohol_pref == 'Non-Alcoholic':
            # Alkolsüz mekan isteniyorsa bar/pub'ı KALDIR
            if category_name == 'İlk Buluşma':
                search_query = 'cafe coffee shop tea house'
            elif category_name == 'Arkadaşlarla Takılma':
                search_query = 'cafe restaurant hangout'

        # VİBE'LARA GÖRE SORGUYU GENİŞLET
        if '#Canlı' in vibes or '#Hareketli' in vibes:
            search_query += ' live music nightlife entertainment'
        elif '#Sakin' in vibes or '#Huzurlu' in vibes:
            search_query += ' quiet peaceful calm'

        # AMENITY'LERE GÖRE SORGUYU GENİŞLET
        if 'Açık Hava' in amenities:
            search_query += ' outdoor terrace garden rooftop'

        # Lokasyon oluştur
        city = location['city']
        districts = location.get('districts', [])
        search_location = f"{districts[0]}, {city}" if districts else city
        import sys
        print(f"DEBUG - Search Location: {search_location}", file=sys.stderr, flush=True)
        print(f"DEBUG - Full location data: {location}", file=sys.stderr, flush=True)

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
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.photos,places.priceLevel,places.types,places.location,places.websiteUri,places.internationalPhoneNumber,places.regularOpeningHours,places.userRatingCount,places.reviews"
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

        # BATCH PROCESSING - Tüm mekanları tek seferde Gemini'ye gönder
        places_list = places_result.get('results', [])[:15]

        # Önce tüm mekan bilgilerini topla
        places_data = []
        for idx, place in enumerate(places_list):
            # Yeni API formatı
            place_id = place.get('id', f"place_{idx}")
            place_name = place.get('displayName', {}).get('text', '')
            place_address = place.get('formattedAddress', '')
            place_rating = place.get('rating', 0)
            place_types = place.get('types', [])

            # Google Places'ten gelen ek bilgiler
            place_website = place.get('websiteUri', '')
            place_phone = place.get('internationalPhoneNumber', '')
            place_review_count = place.get('userRatingCount', 0)

            # Çalışma saatleri
            place_hours = ''
            opening_hours = place.get('regularOpeningHours', {})
            if opening_hours and 'weekdayDescriptions' in opening_hours:
                # İlk günü al (genellikle Pazartesi)
                place_hours = opening_hours['weekdayDescriptions'][0] if opening_hours['weekdayDescriptions'] else ''
                # Sadece saatleri al (örn: "Pazartesi: 09:00 - 22:00" -> "09:00 - 22:00")
                if ':' in place_hours:
                    place_hours = place_hours.split(':', 1)[1].strip()

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

            # Mekan bilgilerini listeye ekle
            places_data.append({
                'idx': idx,
                'id': place_id,
                'name': place_name,
                'address': place_address,
                'rating': place_rating,
                'review_count': place_review_count,
                'types': place_types,
                'price_range': price_range,
                'photo_url': photo_url,
                'website': place_website,
                'phone': place_phone,
                'hours': place_hours
            })

        # Filtreleri hazırla (tek sefer)
        group_size = filters.get('groupSize', '')
        if group_size == 'Solo':
            group_logic = "Tek kişilik oturma düzenleri, sessiz ortam."
        elif group_size == 'Couple':
            group_logic = "İkili masalar, romantik atmosfer."
        elif group_size == 'Small Group':
            group_logic = "4-6 kişilik masalar."
        elif group_size == 'Big Group':
            group_logic = "Geniş masalar, grup rezervasyonu."
        else:
            group_logic = "Belirtilmemiş."

        amenities = filters.get('amenities', [])
        env_logic = "Açık hava/teras tercihi VAR" if 'Açık Hava' in amenities else "Tercihi yok"

        vibes = filters.get('vibes', [])
        if '#Canlı' in vibes or '#Hareketli' in vibes:
            music_logic = "Canlı müzik, hareketli atmosfer BEKLENİYOR."
        elif '#Sakin' in vibes or '#Huzurlu' in vibes:
            music_logic = "Sakin ortam BEKLENİYOR."
        else:
            music_logic = "Belirtilmemiş."

        alcohol_pref = filters.get('alcohol', '')
        category_name = category['name']
        if alcohol_pref == 'Alcoholic':
            alcohol_logic = "ALKOL SERVİSİ ZORUNLU! Cafe/kahveci ASLA ÖNERME."
        elif alcohol_pref == 'Non-Alcoholic':
            alcohol_logic = "Alkolsüz mekan tercih ediliyor."
        else:
            alcohol_logic = "Belirtilmemiş."

        # BATCH GEMINI ÇAĞRISI - Tüm mekanları tek seferde analiz et
        try:
            # Mekan listesini hazırla
            venues_list_str = ""
            for p in places_data:
                venues_list_str += f"\n{p['idx']+1}. {p['name']} | Types: {', '.join(p['types'][:5])} | Rating: {p['rating']}/5 ({p['review_count']} yorum) | Fiyat: {p['price_range']}"

            # Kısaltılmış batch prompt
            batch_prompt = f"""Sen mekan vibe analisti asistanısın. Aşağıdaki {len(places_data)} mekanı analiz et.

KULLANICI TERCİHLERİ:
- Kategori: {category_name}
- Alkol: {alcohol_logic}
- Müzik: {music_logic}
- Grup: {group_logic}

KURALLAR:
1. Alkol "ZORUNLU" ise → Sadece bar/pub/wine_bar UYGUN, cafe/coffee_shop UYGUN DEĞİL
2. "Alkolsüz" ise → Bar/pub UYGUN DEĞİL
3. "Canlı müzik BEKLENİYOR" ise → Sessiz cafe UYGUN DEĞİL
4. Google Types listesine DİKKAT ET

MEKANLAR:{venues_list_str}

ÇIKTI: JSON array döndür. Her mekan için:
{{"idx": 0, "relevant": true/false, "description": "...", "vibeTags": ["#Tag1"], "noiseLevel": 50, "matchScore": 80}}

Uygun OLMAYAN mekanlar için: {{"idx": X, "relevant": false}}
ASLA ```json kullanma, sadece JSON array döndür."""

            model = get_genai_model()
            if not model:
                # Gemini AI ile deneyim odaklı tatil planı oluştur
                model = get_genai_model()
                if not model:
                    return Response(
                        {'error': 'Gemini API key eksik'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )

                try:
                    # Daha katı, parse-edilebilir prompt (sadece JSON array döndürmesini garanti etmeye çalışır)
                    experience_prompt = f"""
            Sen o şehri avucunun içi gibi bilen, cool ve deneyim odaklı bir 'Lokal Rehber'sin.
            Görevin: "{location_query}" için {duration} günlük, NOKTA ATIŞI ve AKSİYON ODAKLI bir liste hazırlamak.

            ## STRATEJİ: "Sadece Mekan Değil, Deneyim Öner"
            Kullanıcıya sadece "Louvre Müzesi" deme. "Louvre'da Mona Lisa'yı gör" veya "Tuileries Bahçesinde yürüyüş yap" de.

            ## GÖREVLER
            1. **Google Search Kullan**: "{location_query} top things to do", "{location_query} best local food" aramaları yap.
            2. **Rota Planla**: Mekanları birbirine yakınlığına göre günlere ayır.
            3. **Çeşitlilik**: Landmark, Yeme/İçme, Aktivite karışık olsun.
            4. **Google Maps Verisi**: Açık/kapalı durumunu, saatleri, telefonu ve fotoğrafı Maps'ten çek.

            ## ÇIKTI FORMATI (SADECE JSON ARRAY)
            Lütfen ÇOK KESİN OLARAK SADECE ve SADECE bir JSON ARRAY dönün. Hiçbir ek açıklama, başlık ya da Markdown bloğu ekleme.
            Her obje aşağıdaki alanları içermeli (örnek gösterim):
            [
              {
                "id": "exp_1",
                "name": "Deneyimin adı (Örn: Eyfel Kulesi'nde gün batımı izle)",
                "description": "2-3 cümlelik detaylı açıklama. Ne yapılacak, neden özel?",
                "imageUrl": "https://images.unsplash.com/photo-...",
                "category": "Tatil",
                "vibeTags": ["#Romantik", "#Manzara", "#İkonik"],
                "address": "Gerçek mekan adresi",
                "priceRange": "$" veya "$$" veya "$$$" veya "$$$$",
                "googleRating": 4.5,
                "noiseLevel": 30,
                "matchScore": 85,
                "itineraryDay": 1,
                "metrics": {"ambiance": 85, "accessibility": 90, "popularity": 95}
              }
            ]

            Kurallar:
            - Her gün için 3-4 deneyim öner (toplam {duration * 3} ile {duration * 4}).
            - Sabah/öğle/akşam dengesi (kahvaltı/brunch, öğlen aktivite, akşam yemek/bar).
            - Aynı gün içindeki mekanlar birbirine yakın olmalı.
            """

                    response = model.generate_content(experience_prompt)
                    response_text = response.text.strip()

                    # Güvenli JSON array çıkarımı: ilk '[' ve son ']' arasını al
                    try:
                        first = response_text.find('[')
                        last = response_text.rfind(']')
                        if first != -1 and last != -1 and last > first:
                            json_text = response_text[first:last+1]
                        else:
                            # fallback to previous heuristic for codeblocks
                            if '```json' in response_text:
                                json_text = response_text.split('```json')[1].split('```')[0].strip()
                            elif '```' in response_text:
                                json_text = response_text.split('```')[1].split('```')[0].strip()
                            else:
                                json_text = response_text

                        experiences = json.loads(json_text)
                    except Exception as parse_exc:
                        import sys
                        print(f"Vacation JSON parse error: {parse_exc}", file=sys.stderr, flush=True)
                        # Fallback: generate mock experiences with itineraryDay populated
                        mock_venues = generate_mock_venues({'name': 'Tatil'}, location, filters)
                        # convert mock venues into experience-like objects with itineraryDay distribution
                        experiences = []
                        day = 1
                        per_day = max(1, min(4, (trip_duration * 3) // max(1, trip_duration)))
                        for idx, mv in enumerate(mock_venues):
                            exp = {
                                'id': mv.get('id', f'mock_{idx}'),
                                'name': mv.get('name'),
                                'description': mv.get('description'),
                                'imageUrl': mv.get('imageUrl'),
                                'category': 'Tatil',
                                'vibeTags': mv.get('vibeTags', []),
                                'address': mv.get('address'),
                                'priceRange': mv.get('priceRange'),
                                'googleRating': mv.get('googleRating'),
                                'noiseLevel': mv.get('noiseLevel'),
                                'matchScore': mv.get('matchScore'),
                                'itineraryDay': (idx // 3) + 1,
                                'metrics': mv.get('metrics', {})
                            }
                            experiences.append(exp)

                    # Ensure each experience has required fields and itineraryDay
                    for i, exp in enumerate(experiences):
                        if 'id' not in exp:
                            exp['id'] = f"exp_{random.randint(1000, 9999)}"
                        exp['category'] = 'Tatil'
                        if 'itineraryDay' not in exp or not isinstance(exp['itineraryDay'], int):
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

                # 2. ORTAM TERCİHİ (İç/Dış mekan)
                amenities = filters.get('amenities', [])
                if 'Açık Hava' in amenities:
                    env_logic = "Açık hava/teras/bahçe tercihi VAR. Outdoor seating önemli."
                elif 'İç Mekan' in amenities:
                    env_logic = "İç mekan tercihi VAR. Kapalı alan öncelikli."
                else:
                    env_logic = "İç/dış mekan tercihi belirtilmemiş."

                # 3. SİGARA/AÇIK ALAN
                if 'Açık Hava' in amenities:
                    smoking_logic = "Açık hava tercihi mevcut. Sigara içilebilir alan olması artı."
                else:
                    smoking_logic = "Sigara tercihi belirtilmemiş."

                # 4. MÜZİK TERCİHİ
                vibes = filters.get('vibes', [])
                if '#Canlı' in vibes or '#Hareketli' in vibes:
                    music_logic = "Canlı müzik, DJ, hareketli atmosfer BEKLENİYOR. Sessiz mekanlar UYGUN DEĞİL."
                elif '#Sakin' in vibes or '#Huzurlu' in vibes:
                    music_logic = "Sakin, sessiz ortam BEKLENİYOR. Yüksek müzikli mekanlar UYGUN DEĞİL."
                else:
                    music_logic = "Müzik tercihi belirtilmemiş."

                # 5. ALKOL TERCİHİ - EN ÖNEMLİ FİLTRE!
                alcohol_pref = filters.get('alcohol', '')
                category_name = category['name']

                # Kahvaltı kategorileri için alkol öncelikli değil
                breakfast_categories = ['Kahvaltı', 'Brunch']

                if category_name in breakfast_categories:
                    alcohol_logic = "Kahvaltı/Brunch kategorisi - Alkol servisi öncelik değil."
                elif alcohol_pref == 'Alcoholic':
                    # Kullanıcı açıkça alkollü mekan seçmiş
                    alcohol_logic = "ALKOL SERVİSİ ZORUNLU! Bar, pub, alkol satan restaurant tercih et. Cafe, kahveci ASLA ÖNERME."
                elif alcohol_pref == 'Non-Alcoholic':
                    # Kullanıcı alkolsüz mekan seçmiş
                    alcohol_logic = "Alkolsüz mekan tercih ediliyor. Cafe, kahveci, family restaurant uygun."
                elif category_name in ['Arkadaşlarla Takılma', 'Romantik Akşam']:
                    # Kategori alkollü mekan çağrıştırıyor ama kullanıcı belirtmemiş
                    alcohol_logic = "Alkol servisi olan mekanlar öncelikli ama zorunlu değil."
                else:
                    alcohol_logic = "Alkol tercihi belirtilmemiş."

                # 6. KATEGORİYE ÖZEL MANTIKLAR
                special_logic = ""
                if 'museum' in ' '.join(place_types).lower():
                    special_logic += "- Müze/Kültürel mekan: Eğitici, sakin, kültürel değer önemli.\n"
                if 'cafe' in ' '.join(place_types).lower() or 'coffee' in ' '.join(place_types).lower():
                    special_logic += "- Cafe/Kahveci: Kahve kalitesi, çalışma ortamı uygunluğu önemli.\n"
                if 'gym' in ' '.join(place_types).lower() or 'sports' in ' '.join(place_types).lower():
                    special_logic += "- Spor tesisi: Ekipman kalitesi, hijyen, aktivite çeşitliliği önemli.\n"

                # GELİŞMİŞ SİSTEM TALİMATI - Kategori + Vibe Derin Analizi
                system_instruction = f"""# SİSTEM TALİMATI - Mekan Vibe Analisti

Sen yerel mekanları çok iyi tanıyan, vibe analizi konusunda uzman bir asistansın.
Google Places'ten gelen mekan bilgilerini analiz edip, kullanıcının kategori ve vibe tercihlerine uygunluğunu değerlendiriyorsun.

## 1. KATEGORİ UYGUNLUK ANALİZİ (KESİN KURALLAR)

**İlk Buluşma:**
✅ UYGUN: cafe, restaurant, coffee shop, wine bar, bistro, tea house
❌ UYGUN DEĞİL: nightclub, spa, gym, hotel, hospital, store, bank, fast food chain

**Arkadaşlarla Takılma:**
✅ UYGUN: bar, pub, restaurant, lounge, cafe (eğer sosyalleşmeye uygunsa), brewery
❌ UYGUN DEĞİL: hospital, hotel, spa, gym, bank, office

**İş Toplantısı:**
✅ UYGUN: cafe, hotel lounge, restaurant (sakin), coworking space, business center
❌ UYGUN DEĞİL: nightclub, bar (gürültülü), gym, spa

**Romantik Akşam:**
✅ UYGUN: romantic restaurant, fine dining, wine bar, rooftop restaurant, bistro
❌ UYGUN DEĞİL: fast food, cafe (casual), gym, hospital, nightclub (çok gürültülü)

## 2. VİBE UYGUNLUK ANALİZİ (DERİN DEĞERLENDİRME)

**ALKOL FİLTRESİ - EN YÜKSEK ÖNCELİK:**
- Eğer "ALKOL SERVİSİ ZORUNLU" görürsen:
  → Mekan TİPİ 'bar', 'pub', 'wine_bar', 'night_club', 'restaurant' olmalı
  → 'cafe', 'coffee_shop', 'tea_house' ASLA KABUL ETME
  → Restaurant ise alkol servisi yaptığından emin ol (Google types'da 'bar' veya isminde 'wine', 'cocktail' olmalı)

- Eğer "Alkolsüz mekan" görürsen:
  → 'bar', 'pub', 'night_club', 'wine_bar' ASLA KABUL ETME
  → 'cafe', 'coffee_shop', 'restaurant', 'tea_house' tercih et

**MÜZİK/ATMOSFER FİLTRESİ:**
- Eğer "Canlı müzik BEKLENİYOR" görürsen:
  → Google types'da 'live_music', 'night_club', 'bar' olmalı
  → Mekan ismine bak: 'live', 'music', 'jazz', 'rock' gibi kelimeler varsa artı puan
  → Cafe/sessiz restaurant UYGUN DEĞİL

- Eğer "Sakin ortam BEKLENİYOR" görürsen:
  → 'night_club', 'bar', 'live_music' UYGUN DEĞİL
  → 'cafe', 'library', 'quiet restaurant' tercih et

**GRUP BOYUTU FİLTRESİ:**
- "Big Group" için: Geniş otururma alanı, grup rezervasyonu yapılabilir olmalı
- "Solo" için: Tek başına çalışma/okuma yapılabilir ortam
- "Couple" için: İkili masalar, romantik/mahrem atmosfer

## 3. MEKAN TİPİ ANALİZİ (Google Types Kullanımı)

Google'dan gelen `types` alanına DİKKAT ET:
- 'cafe' + 'bar' birlikte varsa → Alkol servisi YAPILIYORDUR
- 'coffee_shop' tek başına varsa → Alkol servisi YOK
- 'restaurant' + 'bar' → Alkol servisi VAR
- 'restaurant' + 'cafe' → Alkol servisi OLABİLİR (ismi kontrol et)

## 4. MATCH SCORE HESAPLAMA (0-100)

Match score şu kriterlere göre hesapla:
- Kategori uygunluğu: %40 ağırlık
- Alkol/müzik/ortam vibe uyumu: %30 ağırlık
- Grup boyutu uyumu: %15 ağırlık
- Fiyat uyumu: %15 ağırlık

Örnek:
- Tam uyumlu mekan: 85-100
- İyi uyumlu: 70-84
- Orta uyumlu: 50-69
- Düşük uyum: 30-49
- Uygun değil: <30 (isRelevant: false dön)

## 5. ÇIKTI FORMATI

Eğer mekan UYGUN DEĞİLSE (kategori veya vibe uyumsuz):
{{"isRelevant": false}}

Eğer UYGUNSA:
{{
  "isRelevant": true,
  "description": "2-3 cümle Türkçe açıklama (atmosfer, neden uygun, öne çıkan özellik)",
  "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
  "noiseLevel": 0-100,
  "matchScore": 0-100,
  "metrics": {{
    "ambiance": 0-100,
    "accessibility": 0-100,
    "popularity": 0-100
  }}
}}

## ÖNEMLİ UYARILAR
- ASLA Markdown kod bloğu kullanma (```json gibi)
- Sadece düz JSON döndür
- isRelevant: false için sebep belirtme, sadece false dön
- Match score'u cömert değil, gerçekçi hesapla
"""

                user_prompt = f"""# DEĞERLENDİRME TALEBİ

**MEKAN BİLGİLERİ:**
- İsim: {place_name}
- Google Types: {', '.join(place_types[:8])}
- Adres: {place_address}
- Rating: {place_rating}/5.0 (⭐ {place_review_count} değerlendirme)
- Fiyat: {price_range}

**KULLANICI İSTEĞİ:**
- Kategori: {category_name}
- Grup Boyutu: {group_logic}
- Ortam Tercihi: {env_logic}
- Sigara/Açık Alan: {smoking_logic}
- Müzik Tercihi: {music_logic}
- Alkol Tercihi: {alcohol_logic}

**ÖZEL NOTLAR:**
{special_logic if special_logic else "Yok"}

---

**GÖREV:** Yukarıdaki mekanı analiz et ve SİSTEM TALİMATI kurallarına göre değerlendir.

ÖZELLİKLE DİKKAT ET:
1. Google Types listesine bak - mekan gerçekten ne?
2. Alkol filtresi varsa KESİNLİKLE uygula (cafe ≠ bar!)
3. Müzik/atmosfer filtresi varsa KESİNLİKLE uygula
4. Match score'u GERÇEKÇI hesapla (vibe uyumsuzsa düşük ver)

Çıktı (sadece JSON):
"""

                # Sistem talimatı + kullanıcı promptu birleştir
                analysis_prompt = system_instruction + "\n\n" + user_prompt

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

                # Google Maps URL oluştur
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={place_name.replace(' ', '+')}&query_place_id={place_id}"

                # Venue objesi oluştur - Google Places bilgilerini kullan, Gemini sadece vibe analizi yapsın
                venue = {
                    'id': f"v{idx + 1}",
                    'name': place_name,
                    'description': ai_data.get('description', 'Açıklama ekleniyor...'),
                    'imageUrl': photo_url or 'https://via.placeholder.com/800x600',
                    'category': category['name'],
                    'vibeTags': ai_data.get('vibeTags', ['#Popüler']),
                    'address': place_address,
                    'googleMapsUrl': google_maps_url,
                    'priceRange': price_range,
                    'googleRating': place_rating if place_rating > 0 else 4.0,
                    'googleReviewCount': place_review_count,
                    'noiseLevel': ai_data.get('noiseLevel', 50),
                    'matchScore': ai_data.get('matchScore', 75),
                    'metrics': ai_data.get('metrics', {
                        'ambiance': 75,
                        'accessibility': 80,
                        'popularity': 70
                    }),
                    # Google Places'ten gelen bilgiler (Gemini'den DEĞİL)
                    'website': place_website,
                    'phoneNumber': place_phone,
                    'hours': place_hours
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
