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

def search_google_places(query, max_results=1):
    """
    Google Places API ile mekan araması yapar.
    Website, telefon, çalışma saatleri ve yorumları döndürür.
    """
    import requests

    gmaps = get_gmaps_client()
    if not gmaps:
        return []

    try:
        # Text Search ile mekan bul
        places_result = gmaps.places(query=query)

        if not places_result.get('results'):
            return []

        results = []
        for place in places_result['results'][:max_results]:
            place_id = place.get('place_id')

            # Place Details ile detaylı bilgi al
            if place_id:
                details = gmaps.place(
                    place_id=place_id,
                    fields=[
                        'name', 'formatted_address', 'formatted_phone_number',
                        'website', 'opening_hours', 'rating', 'user_ratings_total',
                        'reviews', 'photos', 'geometry'
                    ]
                )

                detail_result = details.get('result', {})

                # Fotoğraf URL'i oluştur
                image_url = None
                if detail_result.get('photos'):
                    photo_ref = detail_result['photos'][0].get('photo_reference')
                    if photo_ref:
                        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={settings.GOOGLE_MAPS_API_KEY}"

                # Çalışma saatlerini işle
                hours = ''
                weekly_hours = []
                opening_hours = detail_result.get('opening_hours', {})
                if opening_hours:
                    weekly_hours = opening_hours.get('weekday_text', [])
                    if weekly_hours:
                        # Bugünün çalışma saatini bul
                        from datetime import datetime
                        today_idx = datetime.now().weekday()
                        if today_idx < len(weekly_hours):
                            hours = weekly_hours[today_idx]

                # Google Reviews'ları işle
                google_reviews = []
                if detail_result.get('reviews'):
                    for review in detail_result['reviews'][:5]:
                        google_reviews.append({
                            'authorName': review.get('author_name', ''),
                            'rating': review.get('rating', 5),
                            'text': review.get('text', ''),
                            'relativeTime': review.get('relative_time_description', ''),
                            'profilePhotoUrl': review.get('profile_photo_url', '')
                        })

                results.append({
                    'name': detail_result.get('name', place.get('name')),
                    'address': detail_result.get('formatted_address', place.get('formatted_address', '')),
                    'formatted_phone_number': detail_result.get('formatted_phone_number', ''),
                    'website': detail_result.get('website', ''),
                    'hours': hours,
                    'weeklyHours': weekly_hours,
                    'rating': detail_result.get('rating', place.get('rating')),
                    'user_ratings_total': detail_result.get('user_ratings_total', place.get('user_ratings_total', 0)),
                    'reviews': google_reviews,
                    'imageUrl': image_url,
                    'geometry': detail_result.get('geometry', place.get('geometry'))
                })

        return results

    except Exception as e:
        import sys
        print(f"⚠️ Google Places API error: {e}", file=sys.stderr, flush=True)
        return []

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
        # İlçe bilgisini al
        districts = location.get('districts', [])
        district = districts[0] if districts else None

        # Konum string'ini oluştur
        if district:
            location_str = f"{district}, {city}"
            location_constraint = f"SADECE {district}, {city} ilçesinde bulunan"
        else:
            location_str = city
            location_constraint = f"SADECE {city} ili sınırları içinde bulunan"

        # includFineDining flag'i kontrol et (frontend'den gelebilir)
        include_fine_dining = filters.get('includeFineDining', False)

        if include_fine_dining:
            # Fine dining dahil et
            michelin_prompt = f"""
{city} ilindeki en kaliteli fine dining restoranlarını listele.

{city} ili kapsamı: {city} merkez ve TÜM ilçeleri dahil (örn: Bodrum, Marmaris, Fethiye, Datça, Dalaman vb.)

Fine dining kriterleri:
- Şık ve zarif atmosfer
- Yüksek kaliteli mutfak
- Profesyonel servis
- Rezervasyon gerektiren mekanlar

ÖNEMLİ: Sadece {city} ili sınırları içindeki restoranları listele. İzmir, İstanbul gibi BAŞKA İLLERDEN restoran EKLEME!

JSON ARRAY formatında döndür. Her restoran:
{{"id": "fine_1", "name": "Restoran Adı", "description": "2 cümle açıklama", "imageUrl": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800", "category": "Michelin Yıldızlı", "vibeTags": ["#FineDining", "#Restoran"], "address": "İlçe, {city}", "priceRange": "$$$", "noiseLevel": 30, "matchScore": 92, "michelinStatus": "Fine Dining", "metrics": {{"noise": 30, "light": 60, "privacy": 70, "service": 95, "energy": 50}}}}

SADECE JSON ARRAY döndür. En az 8-10 restoran listele."""
        else:
            # Sadece Michelin restoranları
            michelin_prompt = f"""
Michelin Guide Türkiye 2024'te {city} ilinde yer alan restoranları listele.

{city} ili kapsamı: {city} merkez ve TÜM ilçeleri dahil!
Örneğin Muğla için: Bodrum, Marmaris, Fethiye, Datça, Dalaman, Köyceğiz vb. ilçelerdeki Michelin restoranları DAHİL.

Michelin kategorileri:
- Michelin Yıldızlı (1, 2, 3 yıldız)
- Bib Gourmand
- Michelin Tavsiyeli (Selected)

ÖNEMLİ:
- {city} ilinin TÜM ilçelerindeki Michelin restoranlarını dahil et
- Sadece BAŞKA İLLERDEN (İzmir, İstanbul, Ankara vb.) restoran EKLEME
- Urla, Alaçatı, Çeşme = İZMİR'e ait, {city}'ya değil!

Eğer {city} ilinde hiç Michelin restoranı yoksa BOŞ ARRAY [] döndür.

JSON ARRAY formatında döndür. Her restoran:
{{"id": "michelin_1", "name": "Restoran Adı", "description": "2 cümle açıklama", "imageUrl": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800", "category": "Michelin Yıldızlı", "vibeTags": ["#MichelinGuide", "#FineDining"], "address": "İlçe, {city}", "priceRange": "$$$", "noiseLevel": 30, "matchScore": 92, "michelinStatus": "Yıldızlı/BibGourmand/Tavsiyeli", "metrics": {{"noise": 30, "light": 60, "privacy": 70, "service": 95, "energy": 50}}}}

SADECE JSON ARRAY döndür."""

        print(f"🍽️ Michelin Guide araması: {location_str}", file=sys.stderr, flush=True)

        response = model.generate_content(michelin_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        restaurants = json.loads(response_text)

        # Google Places API ile zenginleştir
        for restaurant in restaurants:
            search_query = urllib.parse.quote(f"{restaurant['name']} {location_str} restaurant")
            restaurant['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

            # Google Places API ile detay bilgileri al
            try:
                places_data = search_google_places(f"{restaurant['name']} {location_str}", 1)
                if places_data:
                    place = places_data[0]
                    # Gerçek Google verilerini ekle
                    restaurant['googleRating'] = place.get('rating', 4.5)
                    restaurant['googleReviewCount'] = place.get('user_ratings_total', 0)
                    restaurant['website'] = place.get('website', '')
                    restaurant['phoneNumber'] = place.get('formatted_phone_number', '')
                    restaurant['hours'] = place.get('hours', '')
                    restaurant['weeklyHours'] = place.get('weeklyHours', [])
                    # Fotoğraf URL'i
                    if place.get('imageUrl'):
                        restaurant['imageUrl'] = place['imageUrl']
                    # Google Reviews
                    if place.get('reviews'):
                        restaurant['googleReviews'] = place['reviews'][:5]
            except Exception as e:
                print(f"⚠️ Google Places error for {restaurant['name']}: {e}", file=sys.stderr, flush=True)
                restaurant['googleRating'] = 4.5
                restaurant['googleReviewCount'] = 0

        print(f"✅ {len(restaurants)} Michelin restoran bulundu", file=sys.stderr, flush=True)

        # Eğer hiç Michelin restoran yoksa ve fine dining dahil edilmediyse, öneri sun
        if len(restaurants) == 0 and not include_fine_dining:
            return Response({
                'venues': [],
                'suggestFineDining': True,
                'message': f'{location_str} bölgesinde Michelin Guide\'da yer alan restoran bulunamadı. Fine dining restoranları görmek ister misiniz?'
            }, status=status.HTTP_200_OK)

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
    """Yerel Festivaller kategorisi için gerçek festival ve etkinlik listesi - Google Search grounding ile"""
    import json
    import sys
    import re
    from datetime import datetime, timedelta
    from google import genai
    from google.genai import types

    city = location['city']
    today = datetime.now()
    current_date = today.strftime("%d %B %Y")
    current_date_iso = today.strftime("%Y-%m-%d")
    current_year = today.year

    # dateRange filtresine göre tarih aralığını belirle
    date_range = filters.get('dateRange', 'Any')

    if date_range == 'Today':
        end_date = today
        search_date = "bugün"
        date_constraint = f"SADECE BUGÜN ({current_date}) devam eden veya başlayan etkinlikleri listele."
        end_date_iso = today.strftime("%Y-%m-%d")
    elif date_range == 'ThisWeek':
        end_date = today + timedelta(days=7)
        search_date = "bu hafta"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasında başlayan veya devam eden etkinlikleri listele. Bu tarih aralığı DIŞINDA kalan festivalleri LİSTELEME!"
        end_date_iso = end_date.strftime("%Y-%m-%d")
    elif date_range == 'ThisMonth':
        end_date = today + timedelta(days=30)
        search_date = "bu ay"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasında başlayan veya devam eden etkinlikleri listele. Bu tarih aralığı DIŞINDA kalan festivalleri LİSTELEME!"
        end_date_iso = end_date.strftime("%Y-%m-%d")
    else:  # Any
        end_date = today + timedelta(days=90)
        search_date = "yaklaşan"
        date_constraint = f"{current_date} ile {end_date.strftime('%d %B %Y')} arasında başlayan veya devam eden etkinlikleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")

    if not settings.GEMINI_API_KEY:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        print(f"🎪 Yerel Festivaller (Google Search): {city} - {search_date} ({date_range})", file=sys.stderr, flush=True)
        print(f"📅 Tarih aralığı: {current_date_iso} -> {end_date_iso}", file=sys.stderr, flush=True)

        festival_prompt = f"""
{city} şehrinde {search_date} düzenlenecek festival ve etkinlikleri internetten ara ve listele.

BUGÜNÜN TARİHİ: {current_date} ({current_year})
TARİH FİLTRESİ (ÇOK ÖNEMLİ!): {date_constraint}

KURALLAR:
1. Başlangıç tarihi {end_date.strftime('%d %B %Y')} tarihinden SONRA olan festivalleri LİSTELEME
2. Bitiş tarihi {current_date} tarihinden ÖNCE olan (bitmiş) festivalleri LİSTELEME
3. Şu an devam eden festivalleri dahil et
4. startDate alanı ZORUNLU - ISO formatında (YYYY-MM-DD) festivalin başlangıç tarihi

ARANACAK ETKİNLİK TÜRLERİ (SADECE BUNLAR):
- Yılbaşı festivalleri ve Christmas etkinlikleri
- Gastronomi festivalleri (yemek, şarap, zeytinyağı vb.)
- Müzik festivalleri ve konserler
- Kültür ve sanat festivalleri (tiyatro, sergi, film vb.)
- Yerel şenlikler ve halk festivalleri (çiçek, hasat vb.)
- Alışveriş fuarları ve outlet festivalleri

HARİÇ TUTULACAK ETKİNLİKLER (BUNLARI LİSTELEME!):
- Genel Kurul toplantıları (oda, dernek, şirket vb.)
- Kongre ve konferanslar
- İş toplantıları ve seminerleri
- Resmi törenler ve açılışlar
- Spor müsabakaları ve maçlar
- Eğitim etkinlikleri ve workshoplar

JSON ARRAY formatında döndür. Her festival için:
{{"id": "festival_1", "name": "Festival Adı", "description": "Açıklama", "imageUrl": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=800", "category": "Yerel Festivaller", "vibeTags": ["#Festival"], "address": "Mekan, {city}", "priceRange": "$", "googleRating": 4.5, "noiseLevel": 65, "matchScore": 88, "googleMapsUrl": "", "isEvent": true, "eventDate": "9-14 Aralık 2025", "startDate": "2025-12-09", "endDate": "2025-12-14", "ticketUrl": "", "festivalType": "Yılbaşı", "metrics": {{"ambiance": 85, "accessibility": 80, "popularity": 90}}}}

SADECE JSON ARRAY döndür."""

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=festival_prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        response_text = response.text.strip()
        print(f"📝 Response length: {len(response_text)}", file=sys.stderr, flush=True)

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        if not response_text.startswith('['):
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx + 1]

        festivals = json.loads(response_text)

        # Tarih bazlı filtreleme ve sıralama
        def parse_date(date_str):
            """Tarih string'ini datetime'a çevir"""
            if not date_str:
                return None
            try:
                # ISO format: 2025-12-09
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return None

        def extract_start_date_from_event_date(event_date):
            """eventDate'den başlangıç tarihini çıkar: '9-14 Aralık 2025' -> '2025-12-09'"""
            if not event_date:
                return None
            try:
                # Türkçe ay isimleri
                months_tr = {
                    'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6,
                    'temmuz': 7, 'ağustos': 8, 'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12
                }
                event_date_lower = event_date.lower()

                # Yıl bul
                year_match = re.search(r'20\d{2}', event_date)
                year = int(year_match.group()) if year_match else current_year

                # Ay bul
                month = None
                for month_name, month_num in months_tr.items():
                    if month_name in event_date_lower:
                        month = month_num
                        break

                if not month:
                    return None

                # Gün bul (ilk sayı)
                day_match = re.search(r'(\d{1,2})', event_date)
                day = int(day_match.group(1)) if day_match else 1

                return datetime(year, month, day)
            except:
                return None

        # Kurumsal/bürokratik etkinlikleri filtrelemek için anahtar kelimeler
        excluded_keywords = [
            'genel kurul', 'kongre', 'konferans', 'seminer', 'toplantı',
            'açılış töreni', 'oda ', 'odası', 'dernek', 'birlik',
            'workshop', 'eğitim', 'kurs', 'sınav', 'miting',
            'meclis', 'belediye meclis'
        ]

        filtered_festivals = []
        for festival in festivals:
            # Kurumsal etkinlikleri ele
            festival_name_lower = festival.get('name', '').lower()
            is_excluded = any(keyword in festival_name_lower for keyword in excluded_keywords)
            if is_excluded:
                print(f"⏭️ Kurumsal etkinlik elendi: {festival.get('name')}", file=sys.stderr, flush=True)
                continue

            # startDate varsa kullan, yoksa eventDate'den çıkar
            start_date = parse_date(festival.get('startDate'))
            if not start_date:
                start_date = extract_start_date_from_event_date(festival.get('eventDate'))

            # endDate varsa kullan
            end_date_fest = parse_date(festival.get('endDate'))
            if not end_date_fest:
                # eventDate'den bitiş tarihini çıkarmaya çalış (örn: "9-14 Aralık" -> 14)
                event_date = festival.get('eventDate', '')
                end_match = re.search(r'-(\d{1,2})', event_date)
                if end_match and start_date:
                    try:
                        end_day = int(end_match.group(1))
                        end_date_fest = start_date.replace(day=end_day)
                    except:
                        end_date_fest = start_date

            # Filtreleme: Bitmiş festivalleri çıkar
            if end_date_fest and end_date_fest.date() < today.date():
                print(f"⏭️ Bitmiş festival atlandı: {festival.get('name')} (bitiş: {end_date_fest})", file=sys.stderr, flush=True)
                continue

            # Filtreleme: Seçilen tarih aralığı dışındakileri çıkar
            if start_date and start_date.date() > end_date.date():
                print(f"⏭️ Tarih aralığı dışında: {festival.get('name')} (başlangıç: {start_date})", file=sys.stderr, flush=True)
                continue

            # Sıralama için sort_date ekle
            festival['_sort_date'] = start_date or datetime(2099, 12, 31)
            filtered_festivals.append(festival)

        # Başlangıç tarihine göre sırala (en erken başlayan üstte)
        filtered_festivals.sort(key=lambda x: x['_sort_date'])

        # _sort_date'i temizle ve Google Maps URL ekle
        for festival in filtered_festivals:
            del festival['_sort_date']
            search_query = urllib.parse.quote(f"{festival['name']} {city} {current_year}")
            festival['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(filtered_festivals)} festival bulundu (filtreleme sonrası)", file=sys.stderr, flush=True)

        return Response(filtered_festivals, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Festival generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Festivaller getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_concerts(location, filters):
    """Konserler kategorisi için canlı müzik etkinlikleri - Google Search grounding ile"""
    import json
    import sys
    import re
    from datetime import datetime, timedelta
    from google import genai
    from google.genai import types

    city = location['city']
    today = datetime.now()
    current_date = today.strftime("%d %B %Y")
    current_date_iso = today.strftime("%Y-%m-%d")
    current_year = today.year

    # dateRange filtresine göre tarih aralığını belirle
    date_range = filters.get('dateRange', 'Any')
    music_genre = filters.get('musicGenre', 'Any')

    if date_range == 'Today':
        end_date = today
        search_date = "bugün"
        date_constraint = f"SADECE BUGÜN ({current_date}) olan konserleri listele."
        end_date_iso = today.strftime("%Y-%m-%d")
    elif date_range == 'ThisWeek':
        end_date = today + timedelta(days=7)
        search_date = "bu hafta"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki konserleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")
    elif date_range == 'ThisMonth':
        end_date = today + timedelta(days=30)
        search_date = "bu ay"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki konserleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")
    else:  # Any
        end_date = today + timedelta(days=60)
        search_date = "yaklaşan"
        date_constraint = f"{current_date} ile {end_date.strftime('%d %B %Y')} arasındaki konserleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")

    # Müzik türü filtresi
    genre_search = ""
    genre_constraint = ""
    if music_genre == 'Pop':
        genre_search = "pop konserleri"
        genre_constraint = "SADECE pop müzik konserleri listele."
    elif music_genre == 'Rock':
        genre_search = "rock konserleri"
        genre_constraint = "SADECE rock müzik konserleri listele."
    elif music_genre == 'Jazz':
        genre_search = "jazz konserleri"
        genre_constraint = "SADECE jazz konserleri listele."
    elif music_genre == 'Electronic':
        genre_search = "elektronik müzik DJ performansları"
        genre_constraint = "SADECE elektronik müzik ve DJ performansları listele."
    elif music_genre == 'Rap':
        genre_search = "rap hip-hop konserleri"
        genre_constraint = "SADECE rap ve hip-hop konserleri listele."
    elif music_genre == 'Alternative':
        genre_search = "alternatif indie konserleri"
        genre_constraint = "SADECE alternatif ve indie müzik konserleri listele."
    elif music_genre == 'Classical':
        genre_search = "klasik müzik konserleri senfonik"
        genre_constraint = "SADECE klasik müzik ve senfonik konserleri listele."
    else:
        genre_search = "konser canlı müzik"

    if not settings.GEMINI_API_KEY:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        print(f"🎸 Konserler (Google Search): {city} - {search_date} ({date_range}) - {music_genre}", file=sys.stderr, flush=True)
        print(f"📅 Tarih aralığı: {current_date_iso} -> {end_date_iso}", file=sys.stderr, flush=True)

        concert_prompt = f"""
{city} şehrinde {search_date} gerçekleşecek {genre_search} etkinliklerini internetten ara ve listele.

BUGÜNÜN TARİHİ: {current_date} ({current_year})
TARİH FİLTRESİ (ÇOK ÖNEMLİ!): {date_constraint}
{genre_constraint}

KURALLAR:
1. Başlangıç tarihi {end_date.strftime('%d %B %Y')} tarihinden SONRA olan konserleri LİSTELEME
2. Bitiş tarihi {current_date} tarihinden ÖNCE olan (bitmiş) konserleri LİSTELEME
3. startDate alanı ZORUNLU - ISO formatında (YYYY-MM-DD) konserin tarihi

ARANACAK ETKİNLİK TÜRLERİ:
- Solo sanatçı konserleri
- Grup konserleri ve canlı performanslar
- DJ setleri ve elektronik müzik partileri
- Akustik performanslar
- Açık hava konserleri
- Festival konserleri

BİLİNEN MEKANLAR:
- İstanbul: Zorlu PSM, Volkswagen Arena, KüçükÇiftlik Park, Harbiye Açıkhava, Maximum Uniq, IF Performance Hall, Babylon, Dorock XL
- Ankara: CSO Ada Ankara, CerModern, Bilkent ODEON, Congresium
- İzmir: AASSM, Kültürpark Açıkhava, IF Performance Hall İzmir, Hangout PSM
- Diğer: Beyrut Performance (Karşıyaka), Mask Club, Bohemian

BİLET SATIŞ SİTELERİ:
- Biletix: biletix.com
- Passo: passo.com.tr
- Biletinial: biletinial.com

JSON ARRAY formatında döndür. Her konser için:
{{"id": "concert_1", "name": "Sanatçı/Grup Adı Konseri", "description": "Kısa açıklama - sanatçı hakkında veya konser detayı", "imageUrl": "https://images.unsplash.com/photo-1540039155733-5bb30b53aa14?w=800", "category": "Konserler", "vibeTags": ["#CanlıMüzik", "#Konser", "#Pop"], "address": "Mekan adresi, {city}", "priceRange": "$$", "googleRating": 4.5, "noiseLevel": 75, "matchScore": 90, "googleMapsUrl": "", "isEvent": true, "eventDate": "20 Aralık 2024, Cuma 21:00", "startDate": "2024-12-20", "ticketUrl": "https://biletix.com/...", "musicGenre": "Pop", "venue": "Mekan adı", "metrics": {{"ambiance": 85, "accessibility": 80, "popularity": 92}}}}

SADECE JSON ARRAY döndür."""

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=concert_prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        response_text = response.text.strip()
        print(f"📝 Response length: {len(response_text)}", file=sys.stderr, flush=True)

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        if not response_text.startswith('['):
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx + 1]

        concerts = json.loads(response_text)

        # Tarih bazlı filtreleme ve sıralama
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return None

        def extract_start_date_from_event_date(event_date):
            if not event_date:
                return None
            try:
                months_tr = {
                    'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6,
                    'temmuz': 7, 'ağustos': 8, 'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12
                }
                event_date_lower = event_date.lower()
                year_match = re.search(r'20\d{2}', event_date)
                year = int(year_match.group()) if year_match else current_year
                month = None
                for month_name, month_num in months_tr.items():
                    if month_name in event_date_lower:
                        month = month_num
                        break
                if not month:
                    return None
                day_match = re.search(r'(\d{1,2})', event_date)
                day = int(day_match.group(1)) if day_match else 1
                return datetime(year, month, day)
            except:
                return None

        filtered_concerts = []
        for concert in concerts:
            start_date = parse_date(concert.get('startDate'))
            if not start_date:
                start_date = extract_start_date_from_event_date(concert.get('eventDate'))

            # Filtreleme: Bitmiş konserleri çıkar
            if start_date and start_date.date() < today.date():
                print(f"⏭️ Geçmiş konser atlandı: {concert.get('name')} ({start_date})", file=sys.stderr, flush=True)
                continue

            # Filtreleme: Seçilen tarih aralığı dışındakileri çıkar
            if start_date and start_date.date() > end_date.date():
                print(f"⏭️ Tarih aralığı dışında: {concert.get('name')} ({start_date})", file=sys.stderr, flush=True)
                continue

            concert['_sort_date'] = start_date or datetime(2099, 12, 31)
            filtered_concerts.append(concert)

        # Başlangıç tarihine göre sırala
        filtered_concerts.sort(key=lambda x: x['_sort_date'])

        # _sort_date'i temizle ve Google Maps URL ekle
        for concert in filtered_concerts:
            del concert['_sort_date']
            venue_name = concert.get('venue', concert['name'])
            search_query = urllib.parse.quote(f"{venue_name} {city} konser")
            concert['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(filtered_concerts)} konser bulundu (filtreleme sonrası)", file=sys.stderr, flush=True)

        return Response(filtered_concerts, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Concert generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Konserler getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_adrenaline_experiences(location, filters):
    """Adrenalin kategorisi için deneyim bazlı öneri sistemi"""
    import json
    import sys

    city = location['city']
    districts = location.get('districts', [])
    district = districts[0] if districts else None
    location_query = f"{district}, {city}" if district else city

    model = get_genai_model()
    if not model:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        adrenaline_prompt = f"""
{location_query} ve çevresinde yapılabilecek adrenalin dolu deneyimleri listele.

Deneyim türleri (çeşitlilik olsun):
- Yamaç paraşütü / Paragliding
- Dalış / Tüplü dalış / Serbest dalış
- Rafting / Kano / Kayak
- Bungee jumping
- Zipline / Tirolyen
- Off-road / ATV / Safari turu
- Uçuş deneyimi / Tandem atlayış
- Tırmanış / Kaya tırmanışı
- Sörf / Kitesurf / Windsurf
- Dağ bisikleti
- At binme / Safari
- Go-kart / Karting

{location_query} bölgesine uygun EN AZ 10 FARKLI DENEYİM öner. Bölgede popüler olan aktivitelere öncelik ver.

JSON ARRAY formatında döndür. Her deneyim:
{{"id": "adrenaline_1", "name": "Deneyim Adı", "description": "2-3 cümle açıklama - ne yapılıyor, nasıl bir deneyim", "imageUrl": "https://images.unsplash.com/photo-...", "category": "Adrenalin", "vibeTags": ["#Adrenalin", "#Macera", "#Doğa"], "address": "Aktivite lokasyonu, {city}", "priceRange": "$$", "googleRating": 4.6, "noiseLevel": 60, "matchScore": 90, "googleMapsUrl": "", "metrics": {{"ambiance": 85, "accessibility": 75, "popularity": 88}}}}

SADECE JSON ARRAY döndür. Minimum 10 deneyim."""

        print(f"🏔️ Adrenalin deneyimleri araması: {location_query}", file=sys.stderr, flush=True)

        response = model.generate_content(adrenaline_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        experiences = json.loads(response_text)

        # Google Maps URL ekle
        for exp in experiences:
            search_query = urllib.parse.quote(f"{exp['name']} {city}")
            exp['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(experiences)} adrenalin deneyimi bulundu", file=sys.stderr, flush=True)

        return Response(experiences, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Adrenaline experience generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Adrenalin deneyimleri getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_weekend_trip_experiences(location, filters):
    """Hafta Sonu Gezintisi kategorisi için deneyim bazlı öneri sistemi"""
    import json
    import sys

    city = location['city']
    districts = location.get('districts', [])
    district = districts[0] if districts else None
    location_query = f"{district}, {city}" if district else city

    model = get_genai_model()
    if not model:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        weekend_prompt = f"""
{location_query} ve çevresinde hafta sonu günübirlik gezilecek, görülecek yerleri listele.

Deneyim türleri (çeşitlilik olsun):
- Doğa yürüyüşü / Trekking rotaları
- Tarihi köyler ve kasabalar
- Şelale ve doğal güzellikler
- Botanik bahçeleri / Tabiat parkları
- Antik kentler ve ören yerleri
- Bağ bozumu / Şarap rotaları
- Göl kenarı piknik alanları
- Manzara seyir noktaları
- Termal kaplıcalar
- El sanatları köyleri
- Organik çiftlikler / Köy kahvaltısı
- Bisiklet rotaları

{location_query} bölgesinden günübirlik ulaşılabilir (max 2 saat mesafe) EN AZ 10 FARKLI DENEYİM öner.

JSON ARRAY formatında döndür. Her deneyim:
{{"id": "weekend_1", "name": "Deneyim/Yer Adı", "description": "2-3 cümle açıklama - ne görülür, ne yapılır, neden güzel", "imageUrl": "https://images.unsplash.com/photo-...", "category": "Hafta Sonu Gezintisi", "vibeTags": ["#HaftaSonu", "#Doğa", "#Gezi"], "address": "Lokasyon, İlçe", "priceRange": "$", "googleRating": 4.5, "noiseLevel": 30, "matchScore": 88, "googleMapsUrl": "", "metrics": {{"ambiance": 90, "accessibility": 80, "popularity": 85}}}}

SADECE JSON ARRAY döndür. Minimum 10 deneyim."""

        print(f"🌲 Hafta Sonu Gezintisi araması: {location_query}", file=sys.stderr, flush=True)

        response = model.generate_content(weekend_prompt)
        response_text = response.text.strip()

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        experiences = json.loads(response_text)

        # Google Maps URL ekle
        for exp in experiences:
            search_query = urllib.parse.quote(f"{exp['name']} {city}")
            exp['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(experiences)} hafta sonu deneyimi bulundu", file=sys.stderr, flush=True)

        return Response(experiences, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Weekend trip generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Hafta sonu gezintileri getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_performing_arts_events(location, filters):
    """Sahne Sanatları kategorisi için tiyatro, stand-up, opera, bale etkinlikleri - Google Search grounding ile"""
    import json
    import sys
    import re
    from datetime import datetime, timedelta
    from google import genai
    from google.genai import types

    city = location['city']
    today = datetime.now()
    current_date = today.strftime("%d %B %Y")
    current_date_iso = today.strftime("%Y-%m-%d")
    current_year = today.year

    # dateRange filtresine göre tarih aralığını belirle
    date_range = filters.get('dateRange', 'Any')
    performance_genre = filters.get('performanceGenre', 'Any')

    if date_range == 'Today':
        end_date = today
        search_date = "bugün"
        date_constraint = f"SADECE BUGÜN ({current_date}) olan etkinlikleri listele."
        end_date_iso = today.strftime("%Y-%m-%d")
    elif date_range == 'ThisWeek':
        end_date = today + timedelta(days=7)
        search_date = "bu hafta"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki etkinlikleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")
    elif date_range == 'ThisMonth':
        end_date = today + timedelta(days=30)
        search_date = "bu ay"
        date_constraint = f"SADECE {current_date} ile {end_date.strftime('%d %B %Y')} arasındaki etkinlikleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")
    else:  # Any
        end_date = today + timedelta(days=60)
        search_date = "yaklaşan"
        date_constraint = f"{current_date} ile {end_date.strftime('%d %B %Y')} arasındaki etkinlikleri listele."
        end_date_iso = end_date.strftime("%Y-%m-%d")

    # Tür filtresi
    genre_search = ""
    genre_constraint = ""
    if performance_genre == 'Theater':
        genre_search = "tiyatro oyunları"
        genre_constraint = "SADECE tiyatro oyunları listele (dram, komedi, trajedi)."
    elif performance_genre == 'Standup':
        genre_search = "stand-up komedi gösterileri"
        genre_constraint = "SADECE stand-up komedi gösterileri listele."
    elif performance_genre == 'OperaBallet':
        genre_search = "opera bale gösterileri"
        genre_constraint = "SADECE opera ve bale gösterileri listele."
    elif performance_genre == 'Musical':
        genre_search = "müzikal gösteriler"
        genre_constraint = "SADECE müzikal gösteriler listele."
    elif performance_genre == 'Dance':
        genre_search = "dans gösterileri"
        genre_constraint = "SADECE dans gösterileri listele (modern dans, flamenko, vb.)."
    else:
        genre_search = "tiyatro stand-up opera bale müzikal"

    if not settings.GEMINI_API_KEY:
        return Response(
            {'error': 'Gemini API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        print(f"🎭 Sahne Sanatları (Google Search): {city} - {search_date} ({date_range}) - {performance_genre}", file=sys.stderr, flush=True)
        print(f"📅 Tarih aralığı: {current_date_iso} -> {end_date_iso}", file=sys.stderr, flush=True)

        arts_prompt = f"""
{city} şehrinde {search_date} gerçekleşecek {genre_search} etkinliklerini internetten ara ve listele.

BUGÜNÜN TARİHİ: {current_date} ({current_year})
TARİH FİLTRESİ (ÇOK ÖNEMLİ!): {date_constraint}
{genre_constraint}

KURALLAR:
1. Başlangıç tarihi {end_date.strftime('%d %B %Y')} tarihinden SONRA olan etkinlikleri LİSTELEME
2. Bitiş tarihi {current_date} tarihinden ÖNCE olan (bitmiş) etkinlikleri LİSTELEME
3. startDate alanı ZORUNLU - ISO formatında (YYYY-MM-DD) etkinliğin tarihi

ARANACAK ETKİNLİK TÜRLERİ:
- Tiyatro oyunları (dram, komedi, trajedi)
- Stand-up komedi gösterileri
- Opera ve bale performansları
- Müzikal gösterileri
- Dans gösterileri (modern dans, flamenko, vb.)

BİLİNEN MEKANLAR:
- İstanbul: Zorlu PSM, DasDas, IKSV Salon, Maximum Uniq, Babylon, Harbiye Açıkhava, İstanbul Devlet Tiyatrosu, Şehir Tiyatroları, DOB, Caddebostan Kültür Merkezi, Moda Sahnesi, Uniq Hall
- Ankara: CSO Ada Ankara, CerModern, Ankara Devlet Tiyatrosu, Bilkent ODEON
- İzmir: AASSM, İzmir Devlet Tiyatrosu, Kültürpark Açıkhava, EBSO Konser Salonu, İzmir Sanat

BİLET SATIŞ SİTELERİ:
- Biletix: biletix.com
- Passo: passo.com.tr
- Biletinial: biletinial.com
- Mobilet: mobilet.com

JSON ARRAY formatında döndür. Her etkinlik için:
{{"id": "arts_1", "name": "Gösteri Adı", "description": "Oyuncular veya kısa açıklama", "imageUrl": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=800", "category": "Sahne Sanatları", "vibeTags": ["#Tiyatro", "#Komedi"], "address": "Mekan adresi, {city}", "priceRange": "$$", "googleRating": 4.5, "noiseLevel": 40, "matchScore": 90, "googleMapsUrl": "", "isEvent": true, "eventDate": "20 Aralık 2024, Cuma 20:30", "startDate": "2024-12-20", "ticketUrl": "https://biletix.com/...", "performanceType": "Tiyatro", "venue": "Mekan adı", "metrics": {{"ambiance": 90, "accessibility": 85, "popularity": 88}}}}

SADECE JSON ARRAY döndür."""

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=arts_prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        response_text = response.text.strip()
        print(f"📝 Response length: {len(response_text)}", file=sys.stderr, flush=True)
        print(f"📝 Response preview: {response_text[:500]}...", file=sys.stderr, flush=True)

        # JSON parse et
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        if not response_text.startswith('['):
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx + 1]
            else:
                # JSON array bulunamadı - boş liste döndür
                print(f"⚠️ JSON array bulunamadı, boş liste döndürülüyor", file=sys.stderr, flush=True)
                return Response([], status=status.HTTP_200_OK)

        try:
            events = json.loads(response_text)
        except json.JSONDecodeError as je:
            print(f"⚠️ JSON parse hatası: {je}", file=sys.stderr, flush=True)
            print(f"⚠️ Parsed text: {response_text[:500]}", file=sys.stderr, flush=True)

            # Kesilmiş JSON'u kurtarmaya çalış
            # Son tamamlanmış objeyi bul
            events = []
            depth = 0
            in_string = False
            escape_next = False
            last_complete_idx = -1

            for i, char in enumerate(response_text):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        last_complete_idx = i

            if last_complete_idx > 0:
                # Son tamamlanmış objeye kadar al
                truncated_json = response_text[:last_complete_idx + 1] + ']'
                try:
                    events = json.loads(truncated_json)
                    print(f"✅ Kesilmiş JSON kurtarıldı - {len(events)} etkinlik", file=sys.stderr, flush=True)
                except json.JSONDecodeError as je2:
                    print(f"⚠️ JSON kurtarma başarısız: {je2}", file=sys.stderr, flush=True)
                    events = []

            if not events:
                return Response([], status=status.HTTP_200_OK)

        # Tarih bazlı filtreleme ve sıralama
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return None

        def extract_start_date_from_event_date(event_date):
            if not event_date:
                return None
            try:
                months_tr = {
                    'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6,
                    'temmuz': 7, 'ağustos': 8, 'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12
                }
                event_date_lower = event_date.lower()
                year_match = re.search(r'20\d{2}', event_date)
                year = int(year_match.group()) if year_match else current_year
                month = None
                for month_name, month_num in months_tr.items():
                    if month_name in event_date_lower:
                        month = month_num
                        break
                if not month:
                    return None
                day_match = re.search(r'(\d{1,2})', event_date)
                day = int(day_match.group(1)) if day_match else 1
                return datetime(year, month, day)
            except:
                return None

        filtered_events = []
        for event in events:
            start_date = parse_date(event.get('startDate'))
            if not start_date:
                start_date = extract_start_date_from_event_date(event.get('eventDate'))

            # Filtreleme: Bitmiş etkinlikleri çıkar
            if start_date and start_date.date() < today.date():
                print(f"⏭️ Geçmiş etkinlik atlandı: {event.get('name')} ({start_date})", file=sys.stderr, flush=True)
                continue

            # Filtreleme: Seçilen tarih aralığı dışındakileri çıkar
            if start_date and start_date.date() > end_date.date():
                print(f"⏭️ Tarih aralığı dışında: {event.get('name')} ({start_date})", file=sys.stderr, flush=True)
                continue

            event['_sort_date'] = start_date or datetime(2099, 12, 31)
            filtered_events.append(event)

        # Başlangıç tarihine göre sırala
        filtered_events.sort(key=lambda x: x['_sort_date'])

        # _sort_date'i temizle ve Google Maps URL ekle
        for event in filtered_events:
            del event['_sort_date']
            venue_name = event.get('venue', event['name'])
            search_query = urllib.parse.quote(f"{venue_name} {city}")
            event['googleMapsUrl'] = f"https://www.google.com/maps/search/?api=1&query={search_query}"

        print(f"✅ {len(filtered_events)} sahne sanatları etkinliği bulundu (filtreleme sonrası)", file=sys.stderr, flush=True)

        return Response(filtered_events, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Performing arts generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Sahne sanatları etkinlikleri getirilirken hata: {str(e)}'},
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
            'imageUrl': 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',
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
def google_login(request):
    """Google OAuth ile kullanıcı girişi"""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    credential = request.data.get('credential')

    if not credential:
        return Response(
            {'error': 'Google credential eksik'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Google ID token'i dogrula
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )

        # Token'dan kullanici bilgilerini al
        google_id = idinfo['sub']
        email = idinfo.get('email', '')
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        picture = idinfo.get('picture', '')

        # Kullaniciyi bul veya olustur (email'e gore)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0] + '_' + google_id[:8],
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        # Mevcut kullanici ise bilgilerini guncelle
        if not created:
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.save()

        # UserProfile olustur/guncelle
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Google avatar ve auth bilgilerini kaydet
        if not profile.preferences:
            profile.preferences = {}
        profile.preferences['avatar_url'] = picture
        profile.preferences['auth_provider'] = 'google'
        profile.preferences['google_id'] = google_id
        profile.save()

        # Token olustur
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar_url': picture,
            },
            'created': created
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': f'Gecersiz Google token: {str(e)}'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': f'Google giris hatasi: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def extract_website(url):
    """Instagram ve sosyal medya linklerini website'den ayırır"""
    if not url:
        return ''
    # Instagram, Facebook, Twitter linkleri website değil
    social_media_domains = ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com', 'youtube.com']
    for domain in social_media_domains:
        if domain in url.lower():
            return ''
    return url

def extract_instagram(url):
    """URL'den Instagram linkini çıkarır"""
    if not url:
        return ''
    if 'instagram.com' in url.lower():
        return url
    return ''


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

    # DEBUG: Log incoming request data (wrapped to prevent BrokenPipeError)
    import sys
    try:
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"🔍 INCOMING REQUEST DEBUG", file=sys.stderr, flush=True)
        print(f"{'='*60}", file=sys.stderr, flush=True)
        print(f"Category: {category}", file=sys.stderr, flush=True)
        print(f"Filters received: {json.dumps(filters, indent=2, ensure_ascii=False)}", file=sys.stderr, flush=True)
        print(f"Alcohol filter value: {filters.get('alcohol', 'NOT SET')}", file=sys.stderr, flush=True)
        print(f"{'='*60}\n", file=sys.stderr, flush=True)
    except BrokenPipeError:
        pass  # İstemci bağlantıyı kapattı, devam et

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

        # Adrenalin kategorisi için özel işlem - deneyim bazlı
        if category['name'] == 'Adrenalin':
            return generate_adrenaline_experiences(location, filters)

        # Hafta Sonu Gezintisi kategorisi için özel işlem - deneyim bazlı
        if category['name'] == 'Hafta Sonu Gezintisi':
            return generate_weekend_trip_experiences(location, filters)

        # Sahne Sanatları kategorisi için özel işlem - etkinlik bazlı
        if category['name'] == 'Sahne Sanatları':
            return generate_performing_arts_events(location, filters)

        # Konserler kategorisi için özel işlem - etkinlik bazlı
        if category['name'] == 'Konserler':
            return generate_concerts(location, filters)

        # Kategori bazlı query mapping (Tatil, Michelin, Festivaller, Adrenalin, Hafta Sonu Gezintisi, Sahne Sanatları ve Konserler hariç)
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
                'Meyhane': 'meyhane restaurant turkish tavern rakı meze',
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
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.types,places.location,places.reviews,places.websiteUri,places.internationalPhoneNumber,places.currentOpeningHours"
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
            place_review_count = place.get('userRatingCount', 0)
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

            # ===== PAVYON/KONSOMATRIS FİLTRESİ =====
            # Eğlence & Parti kategorisi için uygunsuz mekanları filtrele
            if category['name'] == 'Eğlence & Parti':
                pavyon_keywords = [
                    'pavyon', 'konsomatris', 'gazino', 'casino', 'kabare', 'cabaret',
                    'gece alemi', 'eglence merkezi', 'dans bar', 'show bar',
                    'strip', 'striptiz', 'hostess', 'escort', 'masaj salonu',
                    'gentlemen', 'club 18', 'club18', 'adult', 'yetiskin'
                ]

                # İsimde veya types'da pavyon tarzı kelimeler varsa filtrele
                is_pavyon_name = any(keyword in place_name_lower for keyword in pavyon_keywords)
                is_pavyon_type = any(keyword in place_types_str for keyword in pavyon_keywords)

                if is_pavyon_name or is_pavyon_type:
                    print(f"❌ PAVYON REJECT - {place_name}: uygunsuz mekan", file=sys.stderr, flush=True)
                    continue

                # ===== RATING & REVIEW COUNT FİLTRESİ =====
                # Eğlence & Parti kategorisi için düşük puanlı ve az yorumlu mekanları filtrele
                if place_rating < 4.6:
                    print(f"❌ RATING REJECT - {place_name}: rating={place_rating} < 4.6", file=sys.stderr, flush=True)
                    continue

                if place_review_count < 15:
                    print(f"❌ REVIEW REJECT - {place_name}: reviews={place_review_count} < 15", file=sys.stderr, flush=True)
                    continue

            # ===== MEYHANE KATEGORİSİ FİLTRESİ =====
            # Meyhane kategorisinde SADECE isminde "meyhane" geçen mekanları kabul et
            if category['name'] == 'Meyhane':
                meyhane_keywords = ['meyhane', 'meyhanesi']
                is_meyhane = any(keyword in place_name_lower for keyword in meyhane_keywords)

                if not is_meyhane:
                    print(f"❌ MEYHANE REJECT - {place_name}: isminde 'meyhane' yok", file=sys.stderr, flush=True)
                    continue

            # Google Reviews'ı parse et (max 10, en yeniden eskiye sıralı)
            google_reviews = []
            raw_reviews = place.get('reviews', [])
            # publishTime'a göre en yeniden eskiye sırala
            sorted_reviews = sorted(
                raw_reviews,
                key=lambda r: r.get('publishTime', ''),
                reverse=True
            )[:10]  # Max 10 yorum
            for review in sorted_reviews:
                google_reviews.append({
                    'authorName': review.get('authorAttribution', {}).get('displayName', 'Anonim'),
                    'rating': review.get('rating', 5),
                    'text': review.get('text', {}).get('text', ''),
                    'relativeTime': review.get('relativePublishTimeDescription', ''),
                    'profilePhotoUrl': review.get('authorAttribution', {}).get('photoUri', ''),
                    'publishTime': review.get('publishTime', '')
                })

            # Çalışma saatleri - tüm hafta
            opening_hours = place.get('currentOpeningHours', {})
            hours_list = opening_hours.get('weekdayDescriptions', [])  # 7 günlük liste
            hours_text = hours_list[0] if hours_list else ''  # Bugünün saati (backward compat)

            # Filtreyi geçen mekanları topla
            filtered_places.append({
                'idx': idx,
                'name': place_name,
                'address': place_address,
                'rating': place_rating,
                'review_count': place_review_count,
                'types': place_types,
                'photo_url': photo_url,
                'google_maps_url': google_maps_url,
                'price_range': price_range,
                'google_reviews': google_reviews,
                'website': extract_website(place.get('websiteUri', '')),
                'instagram_url': extract_instagram(place.get('websiteUri', '')),
                'phone_number': place.get('internationalPhoneNumber', ''),
                'hours': hours_text,
                'weeklyHours': hours_list  # Tüm haftalık saatler
            })

        # ===== PHASE 2: TEK BİR BATCH GEMİNİ ÇAĞRISI =====
        if filtered_places:
            # Kullanıcı tercihlerini hazırla - kategori bazlı
            user_preferences = []
            category_name = category.get('name', '')

            # İlgisiz filtreleri atla: Spor, Etkinlik ve Deneyim kategorileri
            skip_venue_filters = category_name in [
                'Spor', 'Konserler', 'Sahne Sanatları', 'Yerel Festivaller',
                'Beach Club', 'Plaj', 'Hafta Sonu Gezintisi', 'Piknik',
                'Müze', 'Adrenalin', 'Michelin Yıldızlı'
            ]

            if not skip_venue_filters:
                # Standart mekan filtreleri (restoran, bar, kafe vs. için)
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

            # Spor kategorisi için sadece sportType filtresi
            if category_name == 'Spor' and filters.get('sportType') and filters['sportType'] != 'Any':
                user_preferences.append(f"SPOR TÜRÜ: {filters['sportType']}")

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
{{"name": "Mekan Adı", "isRelevant": true/false, "description": "2 cümle Türkçe açıklama", "vibeTags": ["#Tag1", "#Tag2", "#Tag3"], "noiseLevel": 30-70, "matchScore": 75-95, "metrics": {{"noise": 20-80, "energy": 20-80, "service": 40-90, "light": 30-80, "privacy": 20-80}}}}

metrics açıklamaları:
- noise: Gürültü seviyesi (20=sessiz, 80=gürültülü)
- energy: Ortam enerjisi (20=sakin, 80=enerjik)
- service: Hizmet hızı/kalitesi (40=yavaş, 90=hızlı ve kaliteli)
- light: Aydınlatma (30=loş, 80=aydınlık)
- privacy: Mahremiyet (20=kalabalık, 80=özel)

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
                            'imageUrl': place['photo_url'] or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',
                            'category': category['name'],
                            'vibeTags': ai_data.get('vibeTags', ['#Popüler', '#Kaliteli']),
                            'address': place['address'],
                            'priceRange': place['price_range'],
                            'googleRating': place['rating'] if place['rating'] > 0 else 4.0,
                            'googleReviewCount': place.get('review_count', 0),
                            'noiseLevel': ai_data.get('noiseLevel', 50),
                            'matchScore': ai_data.get('matchScore', 80),
                            'googleMapsUrl': place['google_maps_url'],
                            'googleReviews': place.get('google_reviews', []),
                            'website': place.get('website', ''),
                            'instagramUrl': place.get('instagram_url', ''),
                            'phoneNumber': place.get('phone_number', ''),
                            'hours': place.get('hours', ''),
                            'weeklyHours': place.get('weeklyHours', []),
                            'metrics': ai_data.get('metrics', {'noise': 50, 'energy': 50, 'service': 70, 'light': 60, 'privacy': 50})
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
                        'imageUrl': place['photo_url'] or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',
                        'category': category['name'],
                        'vibeTags': ['#Popüler', '#Kaliteli'],
                        'address': place['address'],
                        'priceRange': place['price_range'],
                        'googleRating': place['rating'] if place['rating'] > 0 else 4.0,
                        'googleReviewCount': place.get('review_count', 0),
                        'noiseLevel': 50,
                        'matchScore': 75,
                        'googleMapsUrl': place['google_maps_url'],
                        'googleReviews': place.get('google_reviews', []),
                        'website': place.get('website', ''),
                        'instagramUrl': place.get('instagram_url', ''),
                        'phoneNumber': place.get('phone_number', ''),
                        'hours': place.get('hours', ''),
                        'weeklyHours': place.get('weeklyHours', []),
                        'metrics': {'noise': 50, 'energy': 50, 'service': 70, 'light': 60, 'privacy': 50}
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
