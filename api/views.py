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
from .instagram_service import discover_instagram_url

# Türkiye'deki Michelin yıldızlı ve Bib Gourmand restoranlar (2024-2025)
# Normalized isimler - küçük harf ve Türkçe karakterler normalize edilmiş
MICHELIN_STARRED_RESTAURANTS = {
    # İstanbul - Michelin Yıldızlı (2 yıldız)
    'turk fatih tutak': {'stars': 2, 'city': 'İstanbul'},
    # İstanbul - Michelin Yıldızlı (1 yıldız)
    'neolokal': {'stars': 1, 'city': 'İstanbul'},
    'mikla': {'stars': 1, 'city': 'İstanbul'},
    'nicole': {'stars': 1, 'city': 'İstanbul'},
    'araka': {'stars': 1, 'city': 'İstanbul'},
    'arkestra': {'stars': 1, 'city': 'İstanbul'},
    'default': {'stars': 1, 'city': 'İstanbul'},
    'esmae': {'stars': 1, 'city': 'İstanbul'},
    'mürver': {'stars': 1, 'city': 'İstanbul'},
    'murver': {'stars': 1, 'city': 'İstanbul'},
    'octo': {'stars': 1, 'city': 'İstanbul'},
    'azra': {'stars': 1, 'city': 'İstanbul'},
    'esmee': {'stars': 1, 'city': 'İstanbul'},
    # İstanbul - Bib Gourmand
    'aheste': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'aman da bravo': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'casa lavanda': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'cuma': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'kantin': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'privato cafe': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'yeni lokanta': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'gram': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'karakoy lokantasi': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'karaköy lokantası': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'datli maya': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    'tatlı maya': {'stars': 0, 'bib': True, 'city': 'İstanbul'},
    # Bodrum - Michelin Yıldızlı (1 yıldız)
    'kitchen bodrum': {'stars': 1, 'city': 'Bodrum'},
    'iki sandal': {'stars': 1, 'city': 'Bodrum'},
    # Not: Maçakızı ve Zuma Bodrum yıldızlı DEĞİL, sadece Michelin Selected
    # Ankara - Bib Gourmand
    'mikado': {'stars': 0, 'bib': True, 'city': 'Ankara'},
    # İzmir - Michelin Yıldızlı & Bib Gourmand
    'oi filoi': {'stars': 1, 'city': 'İzmir'},
    'hiç': {'stars': 1, 'city': 'İzmir'},  # Hiç Lokanta - Urla
    'hic': {'stars': 1, 'city': 'İzmir'},
    'hiç lokanta': {'stars': 1, 'city': 'İzmir'},
    'hic lokanta': {'stars': 1, 'city': 'İzmir'},
    'vino locale': {'stars': 0, 'bib': True, 'city': 'İzmir'},
    'asma yaprağı': {'stars': 0, 'bib': True, 'city': 'İzmir'},
    'asma yapragi': {'stars': 0, 'bib': True, 'city': 'İzmir'},
    # Alaçatı / Çeşme - Michelin
    'agrilia': {'stars': 1, 'city': 'İzmir'},
    'ferdi baba': {'stars': 0, 'bib': True, 'city': 'İzmir'},
    # Antalya
    'seraser': {'stars': 0, 'bib': True, 'city': 'Antalya'},
}

# Şehir bazlı Michelin restoran isimleri (Google Places araması için)
MICHELIN_RESTAURANTS_BY_CITY = {
    'İstanbul': [
        'Türk Fatih Tutak', 'Neolokal', 'Mikla', 'Nicole Restaurant', 'Araka',
        'Arkestra', 'Default Restaurant', 'Mürver', 'Octo', 'Azra',
        'Aheste', 'Yeni Lokanta', 'Karaköy Lokantası', 'Gram', 'Casa Lavanda'
    ],
    'İzmir': [
        'Hiç Lokanta Urla', 'Oi Filoi İzmir', 'Agrilia Alaçatı', 'Vino Locale',
        'Asma Yaprağı', 'Ferdi Baba Alaçatı'
    ],
    'Bodrum': ['Kitchen Bodrum', 'İki Sandal'],
    'Ankara': ['Mikado Ankara'],
    'Antalya': ['Seraser Fine Dining'],
}

def is_michelin_restaurant(venue_name):
    """
    Restoran isminin Michelin yıldızlı veya Bib Gourmand olup olmadığını kontrol eder.
    Returns: {'isMichelin': bool, 'stars': int, 'isBib': bool} veya None
    """
    # İsmi normalize et
    normalized = venue_name.lower().strip()
    normalized = normalized.replace('ı', 'i').replace('ş', 's').replace('ç', 'c')
    normalized = normalized.replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

    # Direkt eşleşme kontrolü
    for michelin_name, info in MICHELIN_STARRED_RESTAURANTS.items():
        # Hem direkt eşleşme hem de içerme kontrolü yap
        if michelin_name in normalized or normalized in michelin_name:
            return {
                'isMichelin': True,
                'stars': info.get('stars', 0),
                'isBib': info.get('bib', False)
            }

    return None

from .models import FavoriteVenue, SearchHistory, UserProfile, CachedVenue
from django.utils import timezone
from datetime import timedelta
from .cache_service import (
    get_cached_venues_for_hybrid_swr,
    save_venues_to_cache_swr,
    generate_location_key,
    get_cache_stats
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    FavoriteVenueSerializer, SearchHistorySerializer,
    UserProfileSerializer, VenueSearchSerializer,
    VenueGenerateSerializer
)


# Health check endpoint for Render cold start optimization
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Simple health check endpoint to keep the service warm."""
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


# ===== SHORTLINK ENDPOINTS =====
import secrets
from .models import ShortLink

def generate_short_code():
    """6 karakterlik benzersiz kısa kod üret."""
    while True:
        code = secrets.token_urlsafe(4)[:6]
        if not ShortLink.objects.filter(code=code).exists():
            return code


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_shortlink(request):
    """Venue verisi için kısa link oluştur."""
    venue_data = request.data.get('venue_data')
    if not venue_data:
        return Response({'error': 'venue_data gerekli'}, status=status.HTTP_400_BAD_REQUEST)

    code = generate_short_code()
    shortlink = ShortLink.objects.create(code=code, venue_data=venue_data)

    return Response({
        'code': shortlink.code,
        'url': f"https://maksat.app/s/{shortlink.code}"
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_shortlink(request, code):
    """Kısa kod ile venue verisini getir."""
    try:
        shortlink = ShortLink.objects.get(code=code)
        shortlink.access_count += 1
        shortlink.save(update_fields=['access_count'])
        return Response(shortlink.venue_data, status=status.HTTP_200_OK)
    except ShortLink.DoesNotExist:
        return Response({'error': 'Link bulunamadı'}, status=status.HTTP_404_NOT_FOUND)


# Cache stats endpoint for monitoring
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cache_stats(request):
    """
    Cache statistics endpoint for monitoring SWR cache system.
    Shows freshness distribution, category counts, and ongoing refreshes.
    """
    stats = get_cache_stats()
    return Response(stats, status=status.HTTP_200_OK)


# Cache clear endpoint - practicalInfo/atmosphereSummary eksik venue'ları temizler
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def cache_clear_invalid(request):
    """
    Eksik practicalInfo veya atmosphereSummary olan cache kayıtlarını temizler.
    Ayrıca yorumlarda 'kapandı', 'el değişti' gibi ifadeler olan mekanları da siler.
    Romantik kategorilerdeki zincir mekanları da temizler.
    Bu, eski format venue'ların yeniden API'den çekilmesini sağlar.
    """
    import sys

    deleted_count = 0
    deleted_closed = 0
    deleted_missing = 0
    deleted_chains = 0
    venues = CachedVenue.objects.all()

    # Kapanmış mekan tespiti için anahtar kelimeler
    # NOT: "el değiştir" kaldırıldı - el değiştirmek kapanmak anlamına gelmiyor
    closed_keywords = [
        'kalıcı olarak kapan', 'kalici olarak kapan',
        'artık kapalı', 'artik kapali',
        'kapandı', 'kapandi',
        'kapanmış', 'kapanmis',
        'permanently closed', 'closed permanently',
        'yeni işletme', 'yeni isletme',
        'isim değişti', 'isim degisti',
        'yerine açıldı', 'yerine acildi',
        'burası artık', 'burasi artik'
    ]

    # Romantik kategorilerde istenmeyecek zincir mekanlar
    chain_store_blacklist = [
        'starbucks', 'gloria jeans', 'caribou', 'coffee bean', 'espresso lab',
        'mcdonalds', 'burger king', 'wendys', 'kfc', 'popeyes', 'dominos', 'pizza hut',
        'little caesars', 'papa johns', 'sbarro', 'arbys', 'taco bell', 'subway',
        'mado', 'the house cafe', 'house cafe', 'big chefs', 'bigchefs', 'midpoint',
        'baylan', 'divan', 'kahve dunyasi', 'kahve dünyası', 'nero', 'costa coffee',
        'simit sarayi', 'simit sarayı', 'tavuk dunyasi', 'tavuk dünyası', 'usta donerci',
        'komagene', 'baydoner', 'bay döner', 'burger lab', 'zuma', 'etiler', 'nusr-et',
        'dunkin', 'krispy kreme', 'cinnabon', 'hafiz mustafa', 'hafız mustafa',
        'incir', 'saray muhallebicisi', 'pelit', 'faruk gulluoglu', 'faruk güllüoğlu',
        'wok to walk', 'wagamama', 'nandos', 'tgi fridays', 'chilis', 'applebees',
        'hard rock cafe', 'planet hollywood', 'rainforest cafe', 'cheesecake factory',
        'petra roasting', "walter's coffee"
    ]

    romantic_categories = ['İlk Buluşma', 'Özel Gün', 'Fine Dining', 'Romantik Akşam']

    for venue in venues:
        venue_data = venue.venue_data
        should_delete = False
        delete_reason = ""

        # 1. practicalInfo/atmosphereSummary eksik mi kontrol et
        has_practical = 'practicalInfo' in venue_data and venue_data['practicalInfo']
        has_atmosphere = 'atmosphereSummary' in venue_data and venue_data['atmosphereSummary']

        if not has_practical or not has_atmosphere:
            should_delete = True
            delete_reason = "missing_fields"

        # 2. Yorumlarda kapanmış mekan belirtisi var mı kontrol et
        if not should_delete:
            reviews = venue_data.get('googleReviews', [])
            for review in reviews[:5]:  # Son 5 yorumu kontrol et
                review_text = review.get('text', '').lower()
                review_text_normalized = review_text.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                for keyword in closed_keywords:
                    keyword_normalized = keyword.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                    if keyword_normalized in review_text_normalized:
                        should_delete = True
                        delete_reason = f"closed_venue:{keyword}"
                        break
                if should_delete:
                    break

        # 3. Romantik kategorilerde zincir mekan mı kontrol et
        if not should_delete and venue.category in romantic_categories:
            venue_name_lower = venue.name.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
            for chain in chain_store_blacklist:
                chain_normalized = chain.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                if chain_normalized in venue_name_lower:
                    should_delete = True
                    delete_reason = f"chain_store:{chain}"
                    break

        if should_delete:
            print(f"🗑️ CACHE DELETE - {venue.name}: {delete_reason}", file=sys.stderr, flush=True)
            venue.delete()
            deleted_count += 1
            if delete_reason == "missing_fields":
                deleted_missing += 1
            elif delete_reason.startswith("closed_venue"):
                deleted_closed += 1
            elif delete_reason.startswith("chain_store"):
                deleted_chains += 1

    return Response({
        'deleted': deleted_count,
        'deleted_missing_fields': deleted_missing,
        'deleted_closed_venues': deleted_closed,
        'deleted_chain_stores': deleted_chains,
        'message': f'{deleted_count} venue cache\'den silindi ({deleted_missing} eksik alan, {deleted_closed} kapanmış mekan, {deleted_chains} zincir mağaza)'
    }, status=status.HTTP_200_OK)

# Initialize APIs - lazy load to avoid errors during startup
def get_gmaps_client():
    return googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY) if settings.GOOGLE_MAPS_API_KEY else None


# ===== CACHE HELPER FONKSİYONLARI (SWR - Stale-While-Revalidate) =====
CACHE_VENUES_LIMIT = 10  # Cache'ten alınacak venue sayısı (normal istek için)
CACHE_VENUES_LIMIT_LOAD_MORE = 20  # Load More için daha fazla venue çek


def get_cached_venues_for_hybrid(category_name: str, city: str, district: str = None, exclude_ids: set = None, limit: int = 5, refresh_callback=None):
    """
    Hybrid sistem için cache'ten venue'ları çeker (SWR stratejisi ile).

    Freshness Rules:
    - 0-12 saat: FRESH (direkt cache'ten dön)
    - 12-24 saat: STALE (cache'ten dön, arka planda refresh başlat)
    - 24+ saat: EXPIRED (API'ye git, yeni cache oluştur)

    Returns: (venues_list, all_cached_place_ids)
    """
    venues_data, all_cached_ids, freshness = get_cached_venues_for_hybrid_swr(
        category_name=category_name,
        city=city,
        district=district,
        exclude_ids=exclude_ids,
        limit=limit,
        refresh_callback=refresh_callback
    )

    # Backward compatibility - return tuple without freshness
    return venues_data, all_cached_ids


def enrich_cached_venues_with_instagram(venues: list, city: str) -> list:
    """
    Cache'den dönen venue'lara Instagram URL discovery uygula.
    Sadece instagramUrl'si boş olan venue'lar için Google CSE ile arama yapar.
    """
    if not venues:
        return venues

    enriched_count = 0
    for venue in venues:
        # Instagram URL'si zaten varsa atla
        existing_instagram = venue.get('instagramUrl', '')
        if existing_instagram and 'instagram.com/' in existing_instagram:
            continue

        # Instagram URL'si yok, discovery yap
        instagram_url = discover_instagram_url(
            venue_name=venue.get('name', ''),
            city=city,
            website=venue.get('website'),
            existing_instagram=existing_instagram if existing_instagram else None
        )

        if instagram_url:
            venue['instagramUrl'] = instagram_url
            enriched_count += 1
            print(f"🔗 INSTAGRAM ENRICH - {venue.get('name')}: {instagram_url}", file=sys.stderr, flush=True)

    if enriched_count > 0:
        print(f"✨ INSTAGRAM ENRICH - {enriched_count}/{len(venues)} venue zenginleştirildi", file=sys.stderr, flush=True)

    return venues


def save_venues_to_cache(venues: list, category_name: str, city: str, district: str = None, neighborhood: str = None):
    """
    Venue'ları cache'e kaydeder (SWR metadata ile).
    """
    save_venues_to_cache_swr(
        venues=venues,
        category_name=category_name,
        city=city,
        district=district,
        neighborhood=neighborhood
    )

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
                        'reviews', 'photo', 'geometry'
                    ]
                )

                detail_result = details.get('result', {})

                # Fotoğraf URL'i oluştur
                image_url = None
                photos = detail_result.get('photos') or detail_result.get('photo')
                if photos:
                    photo_list = photos if isinstance(photos, list) else [photos]
                    if photo_list and photo_list[0].get('photo_reference'):
                        photo_ref = photo_list[0].get('photo_reference')
                        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={settings.GOOGLE_MAPS_API_KEY}"

                # Çalışma saatlerini işle
                hours = ''
                weekly_hours = []
                is_open_now = None
                opening_hours = detail_result.get('opening_hours', {})
                if opening_hours:
                    weekly_hours = opening_hours.get('weekday_text', [])
                    is_open_now = opening_hours.get('open_now', None)
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
                    'isOpenNow': is_open_now,
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
    """Michelin Yıldızlı kategorisi - Statik liste + Google Places API"""
    import json
    import sys

    city = location['city']
    districts = location.get('districts', [])
    district = districts[0] if districts else None
    location_str = f"{district}, {city}" if district else city

    # Michelin Guide Türkiye 2024 - Tam Liste (170 restoran)
    MICHELIN_DATABASE = {
        "İstanbul": [
            {"name": "Turk Fatih Tutak", "district": "Şişli", "status": "2 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Neolokal", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Nicole", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Akdeniz"},
            {"name": "Mikla", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Araka", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Arkestra", "district": "Beşiktaş", "status": "1 Yıldız", "cuisine": "Modern"},
            {"name": "Sankai by Nagaya", "district": "Beşiktaş", "status": "1 Yıldız", "cuisine": "Japon"},
            {"name": "Casa Lavanda", "district": "Kadıköy", "status": "1 Yıldız", "cuisine": "İtalyan"},
            {"name": "Aida - vino e cucina", "district": "Beyoğlu", "status": "Bib Gourmand", "cuisine": "İtalyan"},
            {"name": "Foxy Nişantaşı", "district": "Şişli", "status": "Bib Gourmand", "cuisine": "Asya Füzyon"},
            {"name": "Tavacı Recep Usta Bostancı", "district": "Kadıköy", "status": "Bib Gourmand", "cuisine": "Kebap"},
            {"name": "The Red Balloon", "district": "Kadıköy", "status": "Bib Gourmand", "cuisine": "Modern"},
            {"name": "Alaf", "district": "Beşiktaş", "status": "Bib Gourmand", "cuisine": "Anadolu"},
            {"name": "Gün Lokantası", "district": "Beyoğlu", "status": "Selected", "cuisine": "Türk"},
            {"name": "Okra İstanbul", "district": "Beyoğlu", "status": "Selected", "cuisine": "Modern Türk"},
            {"name": "Tershane", "district": "Beyoğlu", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Lokanta by Divan", "district": "Şişli", "status": "Selected", "cuisine": "Türk"},
            {"name": "AZUR", "district": "Beşiktaş", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Yeni Lokanta", "district": "Beyoğlu", "status": "Selected", "cuisine": "Modern Türk"},
            {"name": "Pandeli", "district": "Fatih", "status": "Selected", "cuisine": "Türk"},
            {"name": "Topaz", "district": "Beyoğlu", "status": "Selected", "cuisine": "Modern"},
            {"name": "AQUA", "district": "Beşiktaş", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Liman İstanbul", "district": "Sarıyer", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Nobu İstanbul", "district": "Beşiktaş", "status": "Selected", "cuisine": "Japon"},
            {"name": "Karaköy Lokantası", "district": "Beyoğlu", "status": "Selected", "cuisine": "Türk"},
            {"name": "GALLADA", "district": "Beyoğlu", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Mahir Lokantası", "district": "Beşiktaş", "status": "Selected", "cuisine": "Türk"},
            {"name": "Yanyalı Fehmi Lokantası", "district": "Kadıköy", "status": "Selected", "cuisine": "Türk"},
            {"name": "Ali Ocakbaşı Karaköy", "district": "Beyoğlu", "status": "Selected", "cuisine": "Kebap"},
            {"name": "Lokanta 1741", "district": "Beyoğlu", "status": "Selected", "cuisine": "Türk"},
            {"name": "Calipso Fish", "district": "Beşiktaş", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Eleos Yeşilköy", "district": "Bakırköy", "status": "Selected", "cuisine": "Rum"},
            {"name": "1924 İstanbul", "district": "Beyoğlu", "status": "Selected", "cuisine": "Türk"},
            {"name": "OCAK", "district": "Beşiktaş", "status": "Selected", "cuisine": "Kebap"},
            {"name": "Deraliye", "district": "Fatih", "status": "Selected", "cuisine": "Osmanlı"},
            {"name": "Sunset Grill & Bar", "district": "Beşiktaş", "status": "Selected", "cuisine": "Uluslararası"},
            {"name": "Ulus 29", "district": "Beşiktaş", "status": "Selected", "cuisine": "Türk"},
            {"name": "Zuma İstanbul", "district": "Beşiktaş", "status": "Selected", "cuisine": "Japon"},
            {"name": "Hakkasan İstanbul", "district": "Beşiktaş", "status": "Selected", "cuisine": "Çin"},
            {"name": "Spago İstanbul", "district": "Beşiktaş", "status": "Selected", "cuisine": "Kaliforniya"},
        ],
        "Muğla": [
            {"name": "Kitchen", "district": "Bodrum", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "İki Sandal", "district": "Bodrum", "status": "1 Yıldız", "cuisine": "Deniz Ürünleri"},
            {"name": "Otantik Ocakbaşı", "district": "Bodrum", "status": "Bib Gourmand", "cuisine": "Kebap"},
            {"name": "Zuma Bodrum", "district": "Bodrum", "status": "Selected", "cuisine": "Japon"},
            {"name": "Maçakızı", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Hakkasan Bodrum", "district": "Bodrum", "status": "Selected", "cuisine": "Çin"},
            {"name": "Sait", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Bağarası", "district": "Bodrum", "status": "Selected", "cuisine": "Meze"},
            {"name": "Orfoz", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Beynel", "district": "Bodrum", "status": "Selected", "cuisine": "Türk"},
            {"name": "Loft Elia", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Mezegi", "district": "Bodrum", "status": "Selected", "cuisine": "Meze"},
            {"name": "ADA Restaurant", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Hodan Yalıkavak", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Mandalya", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Yakamengen III", "district": "Bodrum", "status": "Selected", "cuisine": "Kebap"},
            {"name": "Malva", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Mori", "district": "Bodrum", "status": "Selected", "cuisine": "Japon"},
            {"name": "Barbarossa", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Orkide Balık", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "ONNO Grill & Bar", "district": "Bodrum", "status": "Selected", "cuisine": "Izgara"},
            {"name": "Kornél", "district": "Bodrum", "status": "Selected", "cuisine": "Modern"},
            {"name": "Tuti", "district": "Bodrum", "status": "Selected", "cuisine": "İtalyan"},
            {"name": "Mezra Yalıkavak", "district": "Bodrum", "status": "Selected", "cuisine": "Türk"},
            {"name": "Karnas Vineyards", "district": "Bodrum", "status": "Selected", "cuisine": "Şarap Evi"},
            {"name": "Kurul Bitez", "district": "Bodrum", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Dereköy Lokantası", "district": "Fethiye", "status": "Selected", "cuisine": "Türk"},
            {"name": "Kısmet Lokantası", "district": "Fethiye", "status": "Selected", "cuisine": "Türk"},
            {"name": "Agora Pansiyon", "district": "Datça", "status": "Selected", "cuisine": "Ev Yemekleri"},
            {"name": "Arka Ristorante Pizzeria", "district": "Bodrum", "status": "Selected", "cuisine": "İtalyan"},
            {"name": "Sia Eli", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
        ],
        "İzmir": [
            {"name": "OD Urla", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Teruar Urla", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Vino Locale", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Hiç Lokanta", "district": "Urla", "status": "Bib Gourmand", "cuisine": "Modern Türk"},
            {"name": "Adil Müftüoğlu", "district": "Konak", "status": "Bib Gourmand", "cuisine": "Köfte"},
            {"name": "LA Mahzen", "district": "Urla", "status": "Bib Gourmand", "cuisine": "Şarap Evi"},
            {"name": "Ayşa Boşnak Börekçisi", "district": "Konak", "status": "Bib Gourmand", "cuisine": "Börek"},
            {"name": "Beğendik Abi", "district": "Konak", "status": "Bib Gourmand", "cuisine": "Köfte"},
            {"name": "Tavacı Recep Usta Alsancak", "district": "Konak", "status": "Bib Gourmand", "cuisine": "Kebap"},
            {"name": "SOTA Alaçatı", "district": "Çeşme", "status": "Selected", "cuisine": "Modern"},
            {"name": "Ferdi Baba", "district": "Çeşme", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Kasap Fuat Alsancak", "district": "Konak", "status": "Selected", "cuisine": "Et"},
            {"name": "Kasap Fuat Çeşme", "district": "Çeşme", "status": "Selected", "cuisine": "Et"},
            {"name": "Emektar Kebap", "district": "Konak", "status": "Selected", "cuisine": "Kebap"},
            {"name": "Balmumu Dükkan Lokanta", "district": "Konak", "status": "Selected", "cuisine": "Türk"},
            {"name": "Seyhan Et", "district": "Konak", "status": "Selected", "cuisine": "Et"},
            {"name": "Kemal'in Yeri", "district": "Konak", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Aslında Meyhane", "district": "Konak", "status": "Selected", "cuisine": "Meyhane"},
            {"name": "Hus Şarapçılık", "district": "Urla", "status": "Selected", "cuisine": "Şarap Evi"},
            {"name": "Asma Yaprağı", "district": "Urla", "status": "Selected", "cuisine": "Ev Yemekleri"},
            {"name": "Narımor", "district": "Konak", "status": "Selected", "cuisine": "Modern Türk"},
            {"name": "Amavi", "district": "Çeşme", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Ritüel", "district": "Konak", "status": "Selected", "cuisine": "Modern"},
            {"name": "Levan", "district": "Konak", "status": "Selected", "cuisine": "Pide"},
            {"name": "Birinci Kordon Balık", "district": "Konak", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "ÇARK Balık Çeşme", "district": "Çeşme", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "İsabey Bağevi", "district": "Selçuk", "status": "Selected", "cuisine": "Şarap Evi"},
            {"name": "Esca", "district": "Çeşme", "status": "Selected", "cuisine": "İtalyan"},
            {"name": "Partal Kardeşler Balık", "district": "Konak", "status": "Selected", "cuisine": "Deniz Ürünleri"},
            {"name": "Roka Bahçe", "district": "Urla", "status": "Selected", "cuisine": "Akdeniz"},
            {"name": "Gula Urla", "district": "Urla", "status": "Selected", "cuisine": "Modern"},
            {"name": "Scappi", "district": "Çeşme", "status": "Selected", "cuisine": "İtalyan"},
        ]
    }

    try:
        # Şehir için Michelin listesini al
        city_restaurants = MICHELIN_DATABASE.get(city, [])

        if not city_restaurants:
            # Şehirde Michelin restoranı yok, fine dining öner
            return Response({
                'venues': [],
                'suggestFineDining': True,
                'message': f'{city} bölgesinde Michelin Guide\'da yer alan restoran bulunamadı. Fine dining restoranları görmek ister misiniz?'
            }, status=status.HTTP_200_OK)

        # İlçe filtresi varsa uygula
        if district:
            city_restaurants = [r for r in city_restaurants if r['district'].lower() == district.lower()]

        print(f"🍽️ Michelin restoran listesi: {city} ({len(city_restaurants)} adet)", file=sys.stderr, flush=True)

        # Google Places API ile zenginleştir
        restaurants = []
        for idx, r in enumerate(city_restaurants):
            search_query = f"{r['name']} {r['district']} {city} restaurant"

            # Badge sadece yıldızlı veya Bib Gourmand için gösterilecek (Selected için değil)
            is_starred_or_bib = 'Yıldız' in r['status'] or 'Bib' in r['status']

            restaurant = {
                'id': f"michelin_{idx+1}",
                'name': r['name'],
                'description': f"{r['cuisine']} mutfağı sunan {r['status']} ödüllü restoran.",
                'imageUrl': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800',
                'category': 'Michelin Yıldızlı',
                'vibeTags': ['#MichelinGuide', f"#{r['cuisine'].replace(' ', '')}"],
                'address': f"{r['district']}, {city}",
                'priceRange': '$$$' if r['status'] == 'Selected' else '$$$$',
                'matchScore': 98 if '2 Yıldız' in r['status'] else 95 if '1 Yıldız' in r['status'] else 90 if 'Bib' in r['status'] else 85,
                'michelinStatus': r['status'],
                'metrics': {'noise': 30, 'light': 65, 'privacy': 70, 'service': 95, 'energy': 55},
                'googleMapsUrl': f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_query)}",
                'isMichelinStarred': is_starred_or_bib  # Sadece yıldızlı/Bib için badge
            }

            # Google Places API ile detay al
            try:
                places_data = search_google_places(search_query, 1)
                if places_data:
                    place = places_data[0]
                    restaurant['googleRating'] = place.get('rating', 4.5)
                    restaurant['googleReviewCount'] = place.get('user_ratings_total', 0)
                    restaurant['website'] = place.get('website', '')
                    restaurant['phoneNumber'] = place.get('formatted_phone_number', '')
                    restaurant['hours'] = place.get('hours', '')
                    restaurant['weeklyHours'] = place.get('weeklyHours', [])
                    restaurant['isOpenNow'] = place.get('isOpenNow', None)
                    if place.get('imageUrl'):
                        restaurant['imageUrl'] = place['imageUrl']
                    if place.get('reviews'):
                        restaurant['googleReviews'] = place['reviews'][:5]
            except Exception as e:
                print(f"⚠️ Google Places error for {r['name']}: {e}", file=sys.stderr, flush=True)
                restaurant['googleRating'] = 4.5
                restaurant['googleReviewCount'] = 0

            restaurants.append(restaurant)

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


def generate_fine_dining_with_michelin(location, filters, exclude_ids=None):
    """Fine Dining kategorisi - önce Michelin restoranları, sonra diğer fine dining mekanlar
    Gemini ile practicalInfo, atmosphereSummary ve enriched description eklenir.
    """
    import json
    import sys
    import requests
    import re

    city = location['city']
    districts = location.get('districts', [])
    neighborhoods = location.get('neighborhoods', [])
    selected_district = districts[0] if districts else None

    # ===== HYBRID CACHE SİSTEMİ =====
    exclude_ids_set = set(exclude_ids) if exclude_ids else set()
    cached_venues, all_cached_ids = get_cached_venues_for_hybrid(
        category_name='Fine Dining',
        city=city,
        district=selected_district,
        exclude_ids=exclude_ids_set,
        limit=CACHE_VENUES_LIMIT
    )
    # API exclude için cache'teki ID'leri ekle
    api_exclude_ids = exclude_ids_set | all_cached_ids
    print(f"🔀 HYBRID - Fine Dining Cache: {len(cached_venues)}, API exclude: {len(api_exclude_ids)}", file=sys.stderr, flush=True)

    # Birden fazla ilçe için search locations oluştur
    search_locations = []
    if districts:
        for d in districts:
            search_locations.append(f"{d}, {city}")
    else:
        search_locations.append(city)

    print(f"🍽️ Fine Dining + Michelin araması: {search_locations}", file=sys.stderr, flush=True)

    # Michelin Guide Türkiye 2024 - İlgili şehir için
    MICHELIN_DATABASE = {
        "İstanbul": [
            {"name": "Turk Fatih Tutak", "district": "Şişli", "status": "2 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Neolokal", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Nicole", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Akdeniz"},
            {"name": "Mikla", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Araka", "district": "Beyoğlu", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Arkestra", "district": "Beşiktaş", "status": "1 Yıldız", "cuisine": "Modern"},
            {"name": "Sankai by Nagaya", "district": "Beşiktaş", "status": "1 Yıldız", "cuisine": "Japon"},
            {"name": "Casa Lavanda", "district": "Kadıköy", "status": "1 Yıldız", "cuisine": "İtalyan"},
            {"name": "Aida - vino e cucina", "district": "Beyoğlu", "status": "Bib Gourmand", "cuisine": "İtalyan"},
            {"name": "Foxy Nişantaşı", "district": "Şişli", "status": "Bib Gourmand", "cuisine": "Asya Füzyon"},
            {"name": "The Red Balloon", "district": "Kadıköy", "status": "Bib Gourmand", "cuisine": "Modern"},
            {"name": "Alaf", "district": "Beşiktaş", "status": "Bib Gourmand", "cuisine": "Anadolu"},
            {"name": "Yeni Lokanta", "district": "Beyoğlu", "status": "Selected", "cuisine": "Modern Türk"},
            {"name": "Sunset Grill & Bar", "district": "Beşiktaş", "status": "Selected", "cuisine": "Uluslararası"},
            {"name": "Ulus 29", "district": "Beşiktaş", "status": "Selected", "cuisine": "Türk"},
            {"name": "Zuma İstanbul", "district": "Beşiktaş", "status": "Selected", "cuisine": "Japon"},
        ],
        "Muğla": [
            {"name": "Kitchen", "district": "Bodrum", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "İki Sandal", "district": "Bodrum", "status": "1 Yıldız", "cuisine": "Deniz Ürünleri"},
            {"name": "Otantik Ocakbaşı", "district": "Bodrum", "status": "Bib Gourmand", "cuisine": "Kebap"},
            {"name": "Zuma Bodrum", "district": "Bodrum", "status": "Selected", "cuisine": "Japon"},
            {"name": "Maçakızı", "district": "Bodrum", "status": "Selected", "cuisine": "Akdeniz"},
        ],
        "İzmir": [
            {"name": "OD Urla", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Teruar Urla", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Vino Locale", "district": "Urla", "status": "1 Yıldız", "cuisine": "Modern Türk"},
            {"name": "Hiç Lokanta", "district": "Urla", "status": "Bib Gourmand", "cuisine": "Modern Türk"},
            {"name": "LA Mahzen", "district": "Urla", "status": "Bib Gourmand", "cuisine": "Şarap Evi"},
            {"name": "SOTA Alaçatı", "district": "Çeşme", "status": "Selected", "cuisine": "Modern"},
            {"name": "Ferdi Baba", "district": "Çeşme", "status": "Selected", "cuisine": "Deniz Ürünleri"},
        ],
        "Ankara": [
            {"name": "Trilye", "district": "Çankaya", "status": "Selected", "cuisine": "Deniz Ürünleri"},
        ],
        "Antalya": [
            {"name": "Seraser Fine Dining", "district": "Muratpaşa", "status": "Selected", "cuisine": "Akdeniz"},
        ],
    }

    try:
        # Tüm mekanları toplama listesi (Gemini'ye gönderilecek)
        all_venues_for_gemini = []
        added_names = set()

        # 1. ADIM: Şehirdeki Michelin restoranlarını al
        city_michelin = MICHELIN_DATABASE.get(city, [])

        # İlçe filtresi varsa uygula (birden fazla ilçe destekli)
        if districts:
            districts_lower = [d.lower() for d in districts]
            city_michelin = [r for r in city_michelin if r['district'].lower() in districts_lower]

        # Michelin restoranları ekle (yıldız sayısına göre sırala)
        def michelin_sort_key(r):
            if '2 Yıldız' in r['status']:
                return 0
            elif '1 Yıldız' in r['status']:
                return 1
            elif 'Bib Gourmand' in r['status']:
                return 2
            else:
                return 3

        city_michelin.sort(key=michelin_sort_key)

        for idx, r in enumerate(city_michelin[:8]):  # Max 8 Michelin restoran
            search_query = f"{r['name']} {r['district']} {city} restaurant"

            # Badge sadece yıldızlı veya Bib Gourmand için gösterilecek (Selected için değil)
            is_starred_or_bib = 'Yıldız' in r['status'] or 'Bib' in r['status']

            venue_data = {
                'id': f"michelin_fd_{idx+1}",
                'name': r['name'],
                'base_description': f"{r['cuisine']} mutfağı sunan {r['status']} ödüllü restoran.",
                'imageUrl': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800',
                'category': 'Fine Dining',
                'vibeTags': ['#MichelinGuide', f"#{r['status'].replace(' ', '')}", f"#{r['cuisine'].replace(' ', '')}"],
                'address': f"{r['district']}, {city}",
                'priceRange': '$$$' if r['status'] == 'Selected' else '$$$$',
                'matchScore': 98 if '2 Yıldız' in r['status'] else 95 if '1 Yıldız' in r['status'] else 92 if 'Bib' in r['status'] else 88,
                'noiseLevel': 30,
                'googleMapsUrl': f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_query)}",
                'isMichelinStarred': is_starred_or_bib,
                'google_reviews': [],  # Gemini için
                'michelin_status': r['status'],
                'cuisine': r['cuisine']
            }

            # Google Places API ile detay al
            try:
                places_data = search_google_places(search_query, 1)
                if places_data:
                    place = places_data[0]
                    venue_data['googleRating'] = place.get('rating', 4.5)
                    venue_data['googleReviewCount'] = place.get('user_ratings_total', 0)
                    venue_data['website'] = place.get('website', '')
                    venue_data['phoneNumber'] = place.get('formatted_phone_number', '')
                    venue_data['hours'] = place.get('hours', '')
                    venue_data['weeklyHours'] = place.get('weeklyHours', [])
                    venue_data['isOpenNow'] = place.get('isOpenNow', None)
                    if place.get('imageUrl'):
                        venue_data['imageUrl'] = place['imageUrl']
                    if place.get('reviews'):
                        venue_data['google_reviews'] = place['reviews'][:5]
                        venue_data['googleReviews'] = place['reviews'][:5]
            except Exception as e:
                print(f"⚠️ Google Places error for {r['name']}: {e}", file=sys.stderr, flush=True)
                venue_data['googleRating'] = 4.5
                venue_data['googleReviewCount'] = 0

            all_venues_for_gemini.append(venue_data)
            added_names.add(r['name'].lower())

        print(f"✅ {len(all_venues_for_gemini)} Michelin restoran eklendi", file=sys.stderr, flush=True)

        # 2. ADIM: Google Places'dan ek fine dining restoranlar
        if len(all_venues_for_gemini) < 10:
            remaining_slots = 10 - len(all_venues_for_gemini)

            url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.types,places.location,places.reviews,places.websiteUri,places.internationalPhoneNumber,places.currentOpeningHours,places.businessStatus"
            }

            query_templates = [
                "fine dining restaurant upscale gourmet in {loc}, Turkey",
                "italian restaurant trattoria osteria in {loc}, Turkey",
                "tasting menu degustasyon chef restaurant in {loc}, Turkey",
                "romantic dinner wine restaurant bistro in {loc}, Turkey",
            ]

            all_places = []
            for search_loc in search_locations:
                for template in query_templates:
                    if len(all_places) >= remaining_slots + 15:
                        break

                    query = template.format(loc=search_loc)
                    payload = {
                        "textQuery": query,
                        "languageCode": "tr",
                        "maxResultCount": 6
                    }
                    print(f"🔍 Fine dining araması: {query}", file=sys.stderr, flush=True)

                    try:
                        response = requests.post(url, json=payload, headers=headers)
                        if response.status_code == 200:
                            places_data = response.json()
                            places_list = places_data.get('places', [])

                            for place in places_list:
                                place_name = place.get('displayName', {}).get('text', '')
                                place_name_lower = place_name.lower()
                                place_address = place.get('formattedAddress', '')
                                place_rating = place.get('rating', 0)
                                place_types = place.get('types', [])

                                if place_name_lower in added_names:
                                    continue

                                if districts:
                                    address_lower = place_address.lower()
                                    address_normalized = address_lower.replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')

                                    district_match = False
                                    for d in districts:
                                        d_lower = d.lower()
                                        d_normalized = d_lower.replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
                                        if d_lower in address_lower or d_normalized in address_normalized:
                                            district_match = True
                                            break

                                    if not district_match:
                                        print(f"❌ Fine Dining İLÇE REJECT - {place_name}: seçilen ilçelerde değil", file=sys.stderr, flush=True)
                                        continue

                                if place_rating < 4.2:
                                    continue

                                excluded_keywords = [
                                    'pastane', 'pasta atölyesi', 'butik pasta', 'patisserie',
                                    'bakery', 'fırın', 'börek', 'simit', 'kafeterya'
                                ]
                                excluded_types = ['bakery', 'cafe', 'meal_takeaway', 'fast_food_restaurant']

                                is_excluded_name = any(kw in place_name_lower for kw in excluded_keywords)
                                is_excluded_type = any(t in place_types for t in excluded_types) and 'restaurant' not in place_types

                                if is_excluded_name or is_excluded_type:
                                    print(f"❌ Fine Dining REJECT - {place_name}: uygun değil", file=sys.stderr, flush=True)
                                    continue

                                all_places.append(place)
                                added_names.add(place_name_lower)

                    except Exception as e:
                        print(f"⚠️ Fine dining sorgu hatası: {e}", file=sys.stderr, flush=True)

            print(f"📊 Toplam {len(all_places)} unique Google Places mekan bulundu", file=sys.stderr, flush=True)

            # Rating'e göre sırala
            all_places.sort(key=lambda x: x.get('rating', 0), reverse=True)

            for idx, place in enumerate(all_places[:remaining_slots]):
                place_name = place.get('displayName', {}).get('text', '')
                place_address = place.get('formattedAddress', '')
                place_rating = place.get('rating', 0)

                photo_url = 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800'
                if place.get('photos'):
                    photo_name = place['photos'][0].get('name', '')
                    if photo_name:
                        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=800&maxWidthPx=800&key={settings.GOOGLE_MAPS_API_KEY}"

                michelin_info = is_michelin_restaurant(place_name)

                # Google reviews al
                google_reviews = []
                raw_reviews = place.get('reviews', [])
                for review in raw_reviews[:5]:
                    google_reviews.append({
                        'authorName': review.get('authorAttribution', {}).get('displayName', 'Anonim'),
                        'rating': review.get('rating', 5),
                        'text': review.get('text', {}).get('text', ''),
                        'relativeTime': review.get('relativePublishTimeDescription', ''),
                        'profilePhotoUrl': review.get('authorAttribution', {}).get('photoUri', '')
                    })

                opening_hours = place.get('currentOpeningHours', {})

                venue_data = {
                    'id': f"fd_{idx+1}",
                    'name': place_name,
                    'base_description': f"Fine dining deneyimi sunan şık ve kaliteli bir restoran.",
                    'imageUrl': photo_url,
                    'category': 'Fine Dining',
                    'vibeTags': ['#FineDining', '#Gourmet'],
                    'address': place_address,
                    'priceRange': '$$$',
                    'googleRating': place_rating,
                    'googleReviewCount': place.get('userRatingCount', 0),
                    'matchScore': 85,
                    'noiseLevel': 35,
                    'googleMapsUrl': f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(place_name + ' ' + city)}",
                    'isMichelinStarred': michelin_info is not None,
                    'weeklyHours': opening_hours.get('weekdayDescriptions', []),
                    'isOpenNow': opening_hours.get('openNow', None),
                    'website': place.get('websiteUri', ''),
                    'phoneNumber': place.get('internationalPhoneNumber', ''),
                    'google_reviews': google_reviews,
                    'googleReviews': google_reviews
                }

                all_venues_for_gemini.append(venue_data)

        print(f"✅ Gemini'ye gönderilecek toplam {len(all_venues_for_gemini)} mekan", file=sys.stderr, flush=True)

        # 3. ADIM: Gemini ile practicalInfo ve atmosphereSummary ekle
        venues = []
        if all_venues_for_gemini:
            # Pratik bilgi içeren yorumları öncelikli seç
            practical_keywords = ['otopark', 'park', 'vale', 'valet', 'rezervasyon', 'bekle', 'sıra', 'kuyruk',
                                  'kalabalık', 'sakin', 'sessiz', 'gürültü', 'çocuk', 'bebek', 'aile',
                                  'vejetaryen', 'vegan', 'alkol', 'rakı', 'şarap', 'bira', 'servis',
                                  'hızlı', 'yavaş', 'pahalı', 'ucuz', 'fiyat', 'hesap', 'bahçe', 'teras', 'dış mekan']

            # Gemini için mekan listesi oluştur
            places_list_items = []
            for i, v in enumerate(all_venues_for_gemini[:10]):
                reviews_text = ""
                if v.get('google_reviews'):
                    all_reviews = v['google_reviews']
                    practical_reviews = []
                    other_reviews = []
                    for r in all_reviews:
                        text = r.get('text', '').lower()
                        if any(kw in text for kw in practical_keywords):
                            practical_reviews.append(r)
                        else:
                            other_reviews.append(r)
                    selected_reviews = practical_reviews[:3] + other_reviews[:2]
                    top_reviews = [r.get('text', '')[:350] for r in selected_reviews if r.get('text')]
                    if top_reviews:
                        reviews_text = f" | Yorumlar: {' /// '.join(top_reviews)}"

                michelin_note = f" | Michelin: {v.get('michelin_status', '')}" if v.get('michelin_status') else ""
                places_list_items.append(
                    f"{i+1}. {v['name']} | Rating: {v.get('googleRating', 'N/A')}{michelin_note}{reviews_text}"
                )
            places_list = "\n".join(places_list_items)

            batch_prompt = f"""Kategori: Fine Dining
Kullanıcı Tercihleri: Fine dining deneyimi, kaliteli restoran

Mekanlar ve Yorumları:
{places_list}

Her mekan için analiz yap ve JSON döndür:
{{
  "name": "Mekan Adı",
  "description": "2 cümle Türkçe - mekanın öne çıkan özelliği, fine dining atmosferi",
  "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
  "practicalInfo": {{
    "reservationNeeded": "Tavsiye Edilir" | "Şart" | "Gerekli Değil" | null,
    "crowdLevel": "Sakin" | "Orta" | "Kalabalık" | null,
    "waitTime": "Bekleme yok" | "10-15 dk" | "20-30 dk" | null,
    "parking": "Kolay" | "Zor" | "Otopark var" | "Yok" | null,
    "hasValet": true | false | null,
    "outdoorSeating": true | false | null,
    "kidFriendly": true | false | null,
    "vegetarianOptions": true | false | null,
    "alcoholServed": true | false | null,
    "serviceSpeed": "Hızlı" | "Normal" | "Yavaş" | null,
    "priceFeeling": "Fiyatına Değer" | "Biraz Pahalı" | "Uygun" | null,
    "mustTry": "Yorumlarda öne çıkan yemek/içecek" | null,
    "headsUp": "Bilmeniz gereken önemli uyarı" | null
  }},
  "atmosphereSummary": {{
    "noiseLevel": "Sessiz" | "Sohbet Dostu" | "Canlı" | "Gürültülü",
    "lighting": "Loş" | "Yumuşak" | "Aydınlık",
    "privacy": "Özel" | "Yarı Özel" | "Açık Alan",
    "energy": "Sakin" | "Dengeli" | "Enerjik",
    "idealFor": ["romantik akşam", "iş yemeği", "özel gün"],
    "notIdealFor": ["aile yemeği"],
    "oneLiner": "Tek cümle Türkçe atmosfer özeti"
  }}
}}

practicalInfo Kuralları (YORUMLARDAN ÇIKAR):
- reservationNeeded: Fine dining genelde "Şart" veya "Tavsiye Edilir"
- crowdLevel: "Sakin", "sessiz", "rahat" → "Sakin". "Kalabalık", "gürültülü" → "Kalabalık"
- parking: "Otopark", "park yeri" → "Otopark var". "Park zor", "park yok" → "Zor". "Park kolay" → "Kolay"
- hasValet: "Vale", "valet" → true. Yoksa null
- outdoorSeating: "Bahçe", "dış mekan", "teras" → true
- kidFriendly: Fine dining genelde false, özellikle belirtilmemişse null
- alcoholServed: Fine dining genelde true (şarap listesi vb.)
- mustTry: Yorumlarda en çok övülen yemek/tasting menu
- headsUp: Önemli uyarılar (dress code, nakit kabul etmeme vb.)

atmosphereSummary Kuralları:
- noiseLevel: Fine dining genelde "Sessiz" veya "Sohbet Dostu"
- lighting: Fine dining genelde "Loş" veya "Yumuşak"
- privacy: Fine dining genelde "Özel" veya "Yarı Özel"
- energy: Fine dining genelde "Sakin" veya "Dengeli"
- idealFor: Max 3 - "romantik akşam", "iş yemeği", "özel gün", "kutlama", "ilk buluşma"
- notIdealFor: Max 2 - "aile yemeği", "hızlı yemek", "çocuklu gelmek"
- oneLiner: Tek cümle atmosfer özeti

SADECE JSON ARRAY döndür, başka açıklama yazma."""

            try:
                model = get_genai_model()
                if model:
                    response = model.generate_content(batch_prompt)
                    response_text = response.text.strip()

                    # Güvenli JSON parse
                    response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                    response_text = response_text.strip()

                    try:
                        ai_results = json.loads(response_text)
                    except json.JSONDecodeError:
                        match = re.search(r'\[.*\]', response_text, re.DOTALL)
                        if match:
                            ai_results = json.loads(match.group())
                        else:
                            print(f"⚠️ Fine Dining JSON parse edilemedi, fallback kullanılıyor", file=sys.stderr, flush=True)
                            ai_results = []

                    # AI sonuçlarını mekanlarla eşleştir
                    ai_by_name = {r.get('name', '').lower(): r for r in ai_results}

                    for venue_data in all_venues_for_gemini[:10]:
                        ai_data = ai_by_name.get(venue_data['name'].lower(), {})

                        venue = {
                            'id': venue_data['id'],
                            'name': venue_data['name'],
                            'description': ai_data.get('description', venue_data['base_description']),
                            'imageUrl': venue_data['imageUrl'],
                            'category': 'Fine Dining',
                            'vibeTags': ai_data.get('vibeTags', venue_data.get('vibeTags', ['#FineDining', '#Gourmet'])),
                            'address': venue_data['address'],
                            'priceRange': venue_data['priceRange'],
                            'googleRating': venue_data.get('googleRating', 4.5),
                            'googleReviewCount': venue_data.get('googleReviewCount', 0),
                            'matchScore': venue_data['matchScore'],
                            'noiseLevel': venue_data['noiseLevel'],
                            'googleMapsUrl': venue_data['googleMapsUrl'],
                            'isMichelinStarred': venue_data.get('isMichelinStarred', False),
                            'googleReviews': venue_data.get('googleReviews', []),
                            'website': venue_data.get('website', ''),
                            'phoneNumber': venue_data.get('phoneNumber', ''),
                            'hours': venue_data.get('hours', ''),
                            'weeklyHours': venue_data.get('weeklyHours', []),
                            'isOpenNow': venue_data.get('isOpenNow', None),
                            'practicalInfo': ai_data.get('practicalInfo', {}),
                            'atmosphereSummary': ai_data.get('atmosphereSummary', {
                                'noiseLevel': 'Sessiz',
                                'lighting': 'Loş',
                                'privacy': 'Özel',
                                'energy': 'Sakin',
                                'idealFor': ['romantik akşam', 'özel gün'],
                                'notIdealFor': [],
                                'oneLiner': 'Fine dining deneyimi sunan şık bir mekan.'
                            })
                        }

                        venues.append(venue)

                    print(f"✅ Gemini ile {len(venues)} Fine Dining mekan zenginleştirildi", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"❌ Gemini Fine Dining hatası: {e}", file=sys.stderr, flush=True)
                # Fallback: Gemini olmadan mekanları ekle
                for venue_data in all_venues_for_gemini[:10]:
                    venue = {
                        'id': venue_data['id'],
                        'name': venue_data['name'],
                        'description': venue_data['base_description'],
                        'imageUrl': venue_data['imageUrl'],
                        'category': 'Fine Dining',
                        'vibeTags': venue_data.get('vibeTags', ['#FineDining', '#Gourmet']),
                        'address': venue_data['address'],
                        'priceRange': venue_data['priceRange'],
                        'googleRating': venue_data.get('googleRating', 4.5),
                        'googleReviewCount': venue_data.get('googleReviewCount', 0),
                        'matchScore': venue_data['matchScore'],
                        'noiseLevel': venue_data['noiseLevel'],
                        'googleMapsUrl': venue_data['googleMapsUrl'],
                        'isMichelinStarred': venue_data.get('isMichelinStarred', False),
                        'googleReviews': venue_data.get('googleReviews', []),
                        'website': venue_data.get('website', ''),
                        'phoneNumber': venue_data.get('phoneNumber', ''),
                        'hours': venue_data.get('hours', ''),
                        'weeklyHours': venue_data.get('weeklyHours', []),
                        'isOpenNow': venue_data.get('isOpenNow', None),
                        'practicalInfo': {},
                        'atmosphereSummary': {
                            'noiseLevel': 'Sessiz',
                            'lighting': 'Loş',
                            'privacy': 'Özel',
                            'energy': 'Sakin',
                            'idealFor': ['romantik akşam', 'özel gün'],
                            'notIdealFor': [],
                            'oneLiner': 'Fine dining deneyimi sunan şık bir mekan.'
                        }
                    }
                    venues.append(venue)

        print(f"✅ API'den {len(venues)} fine dining restoran geldi", file=sys.stderr, flush=True)

        # ===== CACHE'E KAYDET =====
        if venues:
            save_venues_to_cache(
                venues=venues,
                category_name='Fine Dining',
                city=city,
                district=selected_district
            )

        # ===== HYBRID: CACHE + API VENUE'LARINI BİRLEŞTİR =====
        combined_venues = []
        for cv in cached_venues:
            if len(combined_venues) < 10:
                combined_venues.append(cv)
        existing_ids = {v.get('id') for v in combined_venues}
        for av in venues:
            if len(combined_venues) < 10 and av.get('id') not in existing_ids:
                combined_venues.append(av)
                existing_ids.add(av.get('id'))

        print(f"🔀 HYBRID Fine Dining - Cache: {len(cached_venues)}, API: {len(venues)}, Combined: {len(combined_venues)}", file=sys.stderr, flush=True)

        return Response(combined_venues, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Fine Dining generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Fine Dining restoranları getirilirken hata: {str(e)}'},
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


def generate_picnic_experiences(location, filters):
    """Piknik kategorisi için Google Places API ile gerçek tabiat parkları, mesire alanları"""
    import sys
    import os
    import requests
    import random

    city = location['city']
    districts = location.get('districts', [])
    neighborhoods = location.get('neighborhoods', [])
    district = districts[0] if districts else None
    neighborhood = neighborhoods[0] if neighborhoods else None

    # Lokasyon string oluştur
    if neighborhood:
        location_query = f"{neighborhood}, {district}, {city}"
    elif district:
        location_query = f"{district}, {city}"
    else:
        location_query = city

    google_api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not google_api_key:
        return Response(
            {'error': 'Google Maps API key eksik'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    print(f"🌲 Piknik alanı araması (Google Places): {location_query}", file=sys.stderr, flush=True)

    try:
        # Piknik için aranacak yer türleri - birden fazla sorgu yapalım
        picnic_queries = [
            f"tabiat parkı {location_query}",
            f"mesire alanı {location_query}",
            f"piknik alanı {location_query}",
            f"orman parkı {location_query}",
            f"milli park {location_query}",
        ]

        all_places = []
        seen_place_ids = set()

        for query in picnic_queries:
            # Google Places Text Search API
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            search_params = {
                'query': query,
                'key': google_api_key,
                'language': 'tr',
                'type': 'park'  # Park türünde yerler
            }

            response = requests.get(search_url, params=search_params)
            if response.status_code == 200:
                data = response.json()
                places = data.get('results', [])

                for place in places:
                    place_id = place.get('place_id')
                    if place_id and place_id not in seen_place_ids:
                        seen_place_ids.add(place_id)
                        all_places.append(place)

        print(f"📍 {len(all_places)} piknik alanı bulundu", file=sys.stderr, flush=True)

        # Sonuçları işle
        venues = []
        for i, place in enumerate(all_places[:15]):  # Max 15 sonuç
            place_id = place.get('place_id')

            # Place Details API ile detaylı bilgi al
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place_id,
                'key': google_api_key,
                'language': 'tr',
                'fields': 'name,formatted_address,rating,user_ratings_total,photos,reviews,opening_hours,website,formatted_phone_number,geometry,types'
            }

            details_response = requests.get(details_url, params=details_params)
            if details_response.status_code != 200:
                continue

            details = details_response.json().get('result', {})

            # Fotoğraf URL'leri
            photos = details.get('photos', [])
            image_url = ''
            if photos:
                photo_ref = photos[0].get('photo_reference')
                if photo_ref:
                    image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={google_api_key}"

            # Yorumları al
            reviews = details.get('reviews', [])
            google_reviews = []
            for review in reviews[:5]:
                google_reviews.append({
                    'authorName': review.get('author_name', ''),
                    'rating': review.get('rating', 0),
                    'text': review.get('text', ''),
                    'relativeTime': review.get('relative_time_description', ''),
                    'profilePhotoUrl': review.get('profile_photo_url', '')
                })

            # Çalışma saatleri
            hours = details.get('opening_hours', {})
            weekly_hours = hours.get('weekday_text', [])
            is_open_now = hours.get('open_now', None)

            # Google Maps URL
            lat = details.get('geometry', {}).get('location', {}).get('lat', 0)
            lng = details.get('geometry', {}).get('location', {}).get('lng', 0)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

            venue = {
                'id': f"picnic_{i+1}",
                'name': details.get('name', place.get('name', '')),
                'description': f"Doğa ile iç içe piknik alanı. {details.get('formatted_address', '')}",
                'imageUrl': image_url,
                'category': 'Piknik',
                'vibeTags': ['#Doğa', '#Piknik', '#Açıkhava'],
                'noiseLevel': random.randint(15, 35),
                'matchScore': random.randint(80, 95),
                'address': details.get('formatted_address', place.get('formatted_address', '')),
                'priceRange': '$',
                'googleMapsUrl': maps_url,
                'website': details.get('website', ''),
                'phoneNumber': details.get('formatted_phone_number', ''),
                'weeklyHours': weekly_hours,
                'isOpenNow': is_open_now,
                'googleRating': details.get('rating', 0),
                'googleReviewCount': details.get('user_ratings_total', 0),
                'googleReviews': google_reviews,
                'metrics': {
                    'noise': random.randint(10, 30),
                    'light': random.randint(70, 95),
                    'privacy': random.randint(60, 90),
                    'service': random.randint(30, 60),
                    'energy': random.randint(20, 50)
                }
            }
            venues.append(venue)

        print(f"✅ {len(venues)} piknik alanı detaylandırıldı", file=sys.stderr, flush=True)

        return Response(venues, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Picnic generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Piknik alanları getirilirken hata: {str(e)}'},
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


def generate_street_food_places(location, filters, exclude_ids):
    """Sokak Lezzeti kategorisi için çoklu sorgu - her yemek türü için ayrı arama yaparak çeşitlilik sağla
    Gemini ile practicalInfo, atmosphereSummary ve enriched description eklenir.
    """
    import json
    import sys
    import requests
    import re

    city = location['city']
    districts = location.get('districts', [])
    neighborhoods = location.get('neighborhoods', [])
    selected_district = districts[0] if districts else None
    selected_neighborhood = neighborhoods[0] if neighborhoods else None

    # ===== HYBRID CACHE SİSTEMİ =====
    exclude_ids_set = set(exclude_ids) if exclude_ids else set()
    cached_venues, all_cached_ids = get_cached_venues_for_hybrid(
        category_name='Sokak Lezzeti',
        city=city,
        district=selected_district,
        exclude_ids=exclude_ids_set,
        limit=CACHE_VENUES_LIMIT
    )
    api_exclude_ids = exclude_ids_set | all_cached_ids
    print(f"🔀 HYBRID - Sokak Lezzeti Cache: {len(cached_venues)}, API exclude: {len(api_exclude_ids)}", file=sys.stderr, flush=True)

    # Lokasyon string'i oluştur
    if selected_neighborhood:
        search_location = f"{selected_neighborhood}, {selected_district}, {city}"
    elif selected_district:
        search_location = f"{selected_district}, {city}"
    else:
        search_location = city

    print(f"🌯 Sokak Lezzeti (Multi-Query): {search_location}", file=sys.stderr, flush=True)

    # Her yemek türü için ayrı sorgu - çeşitlilik sağlamak için
    street_food_queries = [
        ('kokoreç', 'Kokoreç'),
        ('tantuni', 'Tantuni'),
        ('midye dolma', 'Midye'),
        ('lahmacun', 'Lahmacun'),
        ('pide', 'Pide'),
        ('döner dürüm', 'Döner'),
        ('balık ekmek', 'Balık Ekmek'),
        ('çiğ köfte', 'Çiğ Köfte'),
        ('ciğer kebap', 'Ciğer'),
        ('söğüş işkembe', 'Söğüş'),
    ]

    venues = []
    added_ids = set()

    try:
        for query_term, food_type in street_food_queries:
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.types,places.location,places.reviews,places.websiteUri,places.internationalPhoneNumber,places.currentOpeningHours,places.businessStatus"
                }

                payload = {
                    "textQuery": f"{query_term} in {search_location}, Turkey",
                    "languageCode": "tr",
                    "maxResultCount": 5  # Her kategori için 5 sonuç
                }

                print(f"🔍 Sorgu: {query_term} in {search_location}", file=sys.stderr, flush=True)

                response = requests.post(url, json=payload, headers=headers)

                if response.status_code != 200:
                    print(f"⚠️ API hatası ({query_term}): {response.status_code}", file=sys.stderr, flush=True)
                    continue

                places_data = response.json()
                places = places_data.get('places', [])

                for place in places:
                    place_id = place.get('id', '')
                    place_name = place.get('displayName', {}).get('text', '')
                    place_address = place.get('formattedAddress', '')
                    place_rating = place.get('rating', 0)
                    place_review_count = place.get('userRatingCount', 0)
                    place_types = place.get('types', [])

                    # Daha önce eklendiyse atla
                    if place_id in added_ids:
                        continue

                    # Exclude IDs kontrolü
                    if place_id in exclude_ids:
                        print(f"⏭️ EXCLUDE - {place_name}: zaten gösterildi", file=sys.stderr, flush=True)
                        continue

                    # Rating filtresi - 4.2 ve üzeri
                    if place_rating < 4.2:
                        print(f"❌ RATING REJECT - {place_name}: {place_rating} < 4.2", file=sys.stderr, flush=True)
                        continue

                    # Review count filtresi - minimum 20
                    if place_review_count < 20:
                        print(f"❌ REVIEW COUNT REJECT - {place_name}: {place_review_count} < 20", file=sys.stderr, flush=True)
                        continue

                    # İlçe kontrolü
                    if selected_district:
                        address_lower = place_address.lower()
                        district_lower = selected_district.lower()
                        district_normalized = district_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                        address_normalized = address_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                        if district_lower not in address_lower and district_normalized not in address_normalized:
                            print(f"❌ İLÇE REJECT - {place_name}: {selected_district} içermiyor", file=sys.stderr, flush=True)
                            continue

                    # Tekel/Market filtresi
                    place_name_lower = place_name.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                    place_types_str = ' '.join(place_types).lower()
                    tekel_keywords = ['tekel', 'market', 'bakkal', 'büfe', 'süpermarket', 'grocery', 'liquor store', 'convenience']
                    tekel_types = ['liquor_store', 'convenience_store', 'grocery_store', 'supermarket']

                    if any(t in place_types_str for t in tekel_types) or any(k in place_name_lower for k in tekel_keywords):
                        print(f"❌ TEKEL REJECT - {place_name}", file=sys.stderr, flush=True)
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
                    price_level_str = place.get('priceLevel', 'PRICE_LEVEL_INEXPENSIVE')
                    price_level_map = {
                        'PRICE_LEVEL_FREE': 1, 'PRICE_LEVEL_INEXPENSIVE': 1,
                        'PRICE_LEVEL_MODERATE': 2, 'PRICE_LEVEL_EXPENSIVE': 3,
                        'PRICE_LEVEL_VERY_EXPENSIVE': 4
                    }
                    price_level = price_level_map.get(price_level_str, 1)
                    price_map = {1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
                    price_range = price_map.get(price_level, '$')

                    # Yorumları formatla (googleReviews formatı - frontend ile uyumlu)
                    google_reviews = []
                    raw_reviews = place.get('reviews', [])
                    for review in raw_reviews[:5]:
                        google_reviews.append({
                            'authorName': review.get('authorAttribution', {}).get('displayName', 'Anonim'),
                            'rating': review.get('rating', 5),
                            'text': review.get('text', {}).get('text', ''),
                            'relativeTime': review.get('relativePublishTimeDescription', ''),
                            'profilePhotoUrl': review.get('authorAttribution', {}).get('photoUri', '')
                        })

                    # Vibe tags
                    vibe_tags = ['#SokakLezzeti', f'#{food_type.replace(" ", "")}', '#Yerel']

                    # Çalışma saatleri
                    opening_hours = place.get('currentOpeningHours', {})

                    venue = {
                        'id': place_id,
                        'name': place_name,
                        'base_description': f"{place_name}, {food_type.lower()} konusunda bölgenin en sevilen sokak lezzeti duraklarından biri.",
                        'imageUrl': photo_url or 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',
                        'category': 'Sokak Lezzeti',
                        'vibeTags': vibe_tags,
                        'address': place_address,
                        'priceRange': price_range,
                        'googleRating': place_rating,
                        'googleReviewCount': place_review_count,
                        'matchScore': min(95, int(place_rating * 20 + min(place_review_count / 50, 10))),
                        'noiseLevel': 55,
                        'googleMapsUrl': google_maps_url,
                        'googleReviews': google_reviews,
                        'google_reviews': google_reviews,  # Gemini için
                        'foodType': food_type,
                        'weeklyHours': opening_hours.get('weekdayDescriptions', []),
                        'isOpenNow': opening_hours.get('openNow', None),
                        'website': place.get('websiteUri', ''),
                        'phoneNumber': place.get('internationalPhoneNumber', '')
                    }

                    venues.append(venue)
                    added_ids.add(place_id)
                    print(f"✅ EKLENDI - {place_name} ({food_type}): ⭐{place_rating} ({place_review_count} yorum)", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"⚠️ {query_term} sorgusu hatası: {e}", file=sys.stderr, flush=True)
                continue

        # Puana ve yorum sayısına göre sırala
        venues.sort(key=lambda x: (x['googleRating'], x['googleReviewCount']), reverse=True)

        print(f"🌯 Toplam {len(venues)} sokak lezzeti mekanı bulundu, Gemini ile zenginleştiriliyor...", file=sys.stderr, flush=True)

        # Gemini ile practicalInfo ve atmosphereSummary ekle
        if venues:
            # Pratik bilgi içeren yorumları öncelikli seç
            practical_keywords = ['otopark', 'park', 'vale', 'valet', 'rezervasyon', 'bekle', 'sıra', 'kuyruk',
                                  'kalabalık', 'sakin', 'sessiz', 'gürültü', 'çocuk', 'bebek', 'aile',
                                  'vejetaryen', 'vegan', 'alkol', 'rakı', 'şarap', 'bira', 'servis',
                                  'hızlı', 'yavaş', 'pahalı', 'ucuz', 'fiyat', 'hesap', 'bahçe', 'teras', 'dış mekan', 'nakit']

            places_list_items = []
            for i, v in enumerate(venues[:10]):
                reviews_text = ""
                if v.get('google_reviews'):
                    all_reviews = v['google_reviews']
                    practical_reviews = []
                    other_reviews = []
                    for r in all_reviews:
                        text = r.get('text', '').lower()
                        if any(kw in text for kw in practical_keywords):
                            practical_reviews.append(r)
                        else:
                            other_reviews.append(r)
                    selected_reviews = practical_reviews[:3] + other_reviews[:2]
                    top_reviews = [r.get('text', '')[:350] for r in selected_reviews if r.get('text')]
                    if top_reviews:
                        reviews_text = f" | Yorumlar: {' /// '.join(top_reviews)}"

                food_note = f" | Lezzet: {v.get('foodType', '')}"
                places_list_items.append(
                    f"{i+1}. {v['name']} | Rating: {v.get('googleRating', 'N/A')}{food_note}{reviews_text}"
                )
            places_list = "\n".join(places_list_items)

            batch_prompt = f"""Kategori: Sokak Lezzeti
Kullanıcı Tercihleri: Sokak lezzeti, hızlı yemek, yerel lezzetler

Mekanlar ve Yorumları:
{places_list}

Her mekan için analiz yap ve JSON döndür:
{{
  "name": "Mekan Adı",
  "description": "2 cümle Türkçe - mekanın öne çıkan özelliği, imza lezzeti",
  "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
  "practicalInfo": {{
    "reservationNeeded": null,
    "crowdLevel": "Sakin" | "Orta" | "Kalabalık" | null,
    "waitTime": "Bekleme yok" | "10-15 dk" | "20-30 dk" | null,
    "parking": "Kolay" | "Zor" | "Otopark var" | "Yok" | null,
    "hasValet": true | false | null,
    "outdoorSeating": true | false | null,
    "kidFriendly": true | false | null,
    "vegetarianOptions": true | false | null,
    "alcoholServed": false,
    "serviceSpeed": "Hızlı" | "Normal" | "Yavaş" | null,
    "priceFeeling": "Fiyatına Değer" | "Biraz Pahalı" | "Uygun" | null,
    "mustTry": "İmza yemek" | null,
    "headsUp": "Önemli uyarı (sadece nakit, vs.)" | null
  }},
  "atmosphereSummary": {{
    "noiseLevel": "Sessiz" | "Sohbet Dostu" | "Canlı" | "Gürültülü",
    "lighting": "Loş" | "Yumuşak" | "Aydınlık",
    "privacy": "Özel" | "Yarı Özel" | "Açık Alan",
    "energy": "Sakin" | "Dengeli" | "Enerjik",
    "idealFor": ["hızlı öğün", "gece atıştırmalığı", "arkadaş buluşması"],
    "notIdealFor": ["romantik akşam"],
    "oneLiner": "Tek cümle Türkçe atmosfer özeti"
  }}
}}

practicalInfo Kuralları (YORUMLARDAN ÇIKAR):
- reservationNeeded: Sokak lezzeti için genelde null (rezervasyon olmaz)
- crowdLevel: "Kalabalık", "sıra var" → "Kalabalık". "Sakin" → "Sakin"
- waitTime: "Sıra", "kuyruk", "bekledik" → süreyi tahmin et
- parking: "Otopark", "park yeri" → "Otopark var". "Park zor", "park yok" → "Zor". "Park kolay" → "Kolay". Sokak lezzeti genelde "Zor" veya null
- hasValet: "Vale", "valet" → true. Sokak lezzeti için genelde null
- serviceSpeed: Sokak lezzeti genelde "Hızlı"
- priceFeeling: "Ucuz", "uygun" → "Uygun". "Pahalı" → "Biraz Pahalı"
- mustTry: Yorumlarda en çok övülen yemek
- headsUp: Sadece nakit, temizlik uyarısı vb.

atmosphereSummary Kuralları:
- noiseLevel: Sokak lezzeti genelde "Canlı" veya "Gürültülü"
- lighting: Sokak lezzeti genelde "Aydınlık"
- privacy: Sokak lezzeti genelde "Açık Alan"
- energy: Sokak lezzeti genelde "Enerjik"
- idealFor: Max 3 - "hızlı öğün", "gece atıştırmalığı", "arkadaş buluşması", "ekonomik yemek"
- notIdealFor: Max 2 - "romantik akşam", "iş yemeği", "özel gün"
- oneLiner: Tek cümle atmosfer özeti

SADECE JSON ARRAY döndür, başka açıklama yazma."""

            try:
                model = get_genai_model()
                if model:
                    response = model.generate_content(batch_prompt)
                    response_text = response.text.strip()

                    # Güvenli JSON parse
                    response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                    response_text = response_text.strip()

                    try:
                        ai_results = json.loads(response_text)
                    except json.JSONDecodeError:
                        match = re.search(r'\[.*\]', response_text, re.DOTALL)
                        if match:
                            ai_results = json.loads(match.group())
                        else:
                            print(f"⚠️ Sokak Lezzeti JSON parse edilemedi, fallback kullanılıyor", file=sys.stderr, flush=True)
                            ai_results = []

                    # AI sonuçlarını mekanlarla eşleştir
                    ai_by_name = {r.get('name', '').lower(): r for r in ai_results}

                    final_venues = []
                    for venue_data in venues[:10]:
                        ai_data = ai_by_name.get(venue_data['name'].lower(), {})

                        venue = {
                            'id': venue_data['id'],
                            'name': venue_data['name'],
                            'description': ai_data.get('description', venue_data['base_description']),
                            'imageUrl': venue_data['imageUrl'],
                            'category': 'Sokak Lezzeti',
                            'vibeTags': ai_data.get('vibeTags', venue_data.get('vibeTags', ['#SokakLezzeti'])),
                            'address': venue_data['address'],
                            'priceRange': venue_data['priceRange'],
                            'googleRating': venue_data.get('googleRating', 4.0),
                            'googleReviewCount': venue_data.get('googleReviewCount', 0),
                            'matchScore': venue_data['matchScore'],
                            'noiseLevel': venue_data['noiseLevel'],
                            'googleMapsUrl': venue_data['googleMapsUrl'],
                            'googleReviews': venue_data.get('googleReviews', []),
                            'website': venue_data.get('website', ''),
                            'phoneNumber': venue_data.get('phoneNumber', ''),
                            'weeklyHours': venue_data.get('weeklyHours', []),
                            'isOpenNow': venue_data.get('isOpenNow', None),
                            'foodType': venue_data.get('foodType', ''),
                            'practicalInfo': ai_data.get('practicalInfo', {}),
                            'atmosphereSummary': ai_data.get('atmosphereSummary', {
                                'noiseLevel': 'Canlı',
                                'lighting': 'Aydınlık',
                                'privacy': 'Açık Alan',
                                'energy': 'Enerjik',
                                'idealFor': ['hızlı öğün', 'gece atıştırmalığı'],
                                'notIdealFor': ['romantik akşam'],
                                'oneLiner': 'Sokak lezzeti deneyimi sunan popüler bir mekan.'
                            })
                        }
                        final_venues.append(venue)

                    print(f"✅ Gemini ile {len(final_venues)} Sokak Lezzeti mekan zenginleştirildi", file=sys.stderr, flush=True)
                    return Response(final_venues, status=status.HTTP_200_OK)

            except Exception as e:
                print(f"❌ Gemini Sokak Lezzeti hatası: {e}", file=sys.stderr, flush=True)
                # Fallback: Gemini olmadan mekanları döndür
                for venue_data in venues:
                    venue_data['description'] = venue_data.pop('base_description', venue_data.get('description', ''))
                    venue_data['practicalInfo'] = {}
                    venue_data['atmosphereSummary'] = {
                        'noiseLevel': 'Canlı',
                        'lighting': 'Aydınlık',
                        'privacy': 'Açık Alan',
                        'energy': 'Enerjik',
                        'idealFor': ['hızlı öğün'],
                        'notIdealFor': [],
                        'oneLiner': 'Sokak lezzeti deneyimi sunan popüler bir mekan.'
                    }

        # ===== CACHE'E KAYDET (sadece API'den gelen yeni venue'lar) =====
        if venues:
            save_venues_to_cache(
                venues=venues,
                category_name='Sokak Lezzeti',
                city=city,
                district=selected_district,
                neighborhood=selected_neighborhood
            )

        # ===== HYBRID: CACHE + API VENUE'LARINI BİRLEŞTİR =====
        combined_venues = []
        # Önce cache'ten gelenleri ekle
        for cv in cached_venues:
            if len(combined_venues) < 10:
                combined_venues.append(cv)
        # Sonra API'den gelenleri ekle (duplicate olmayanları)
        existing_ids = {v.get('id') for v in combined_venues}
        for av in venues:
            if len(combined_venues) < 10 and av.get('id') not in existing_ids:
                combined_venues.append(av)
                existing_ids.add(av.get('id'))

        print(f"🔀 HYBRID RESULT - Sokak Lezzeti Cache: {len(cached_venues)}, API: {len(venues)}, Combined: {len(combined_venues)}", file=sys.stderr, flush=True)
        return Response(combined_venues, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Street food generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Sokak lezzetleri getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_party_venues(location, filters, exclude_ids):
    """Eğlence & Parti kategorisi için çoklu sorgu - her mekan türü için ayrı arama yaparak çeşitlilik sağla
    Gemini ile practicalInfo, atmosphereSummary ve enriched description eklenir.
    """
    import json
    import sys
    import requests
    import re

    city = location['city']
    districts = location.get('districts', [])
    neighborhoods = location.get('neighborhoods', [])
    selected_district = districts[0] if districts else None
    selected_neighborhood = neighborhoods[0] if neighborhoods else None

    # ===== HYBRID CACHE SİSTEMİ =====
    exclude_ids_set = set(exclude_ids) if exclude_ids else set()
    cached_venues, all_cached_ids = get_cached_venues_for_hybrid(
        category_name='Eğlence & Parti',
        city=city,
        district=selected_district,
        exclude_ids=exclude_ids_set,
        limit=CACHE_VENUES_LIMIT
    )
    api_exclude_ids = exclude_ids_set | all_cached_ids
    print(f"🔀 HYBRID - Eğlence & Parti Cache: {len(cached_venues)}, API exclude: {len(api_exclude_ids)}", file=sys.stderr, flush=True)

    # Lokasyon string'i oluştur
    if selected_neighborhood:
        search_location = f"{selected_neighborhood}, {selected_district}, {city}"
    elif selected_district:
        search_location = f"{selected_district}, {city}"
    else:
        search_location = city

    print(f"🪩 Eğlence & Parti (Multi-Query): {search_location}", file=sys.stderr, flush=True)

    # Her mekan türü için ayrı sorgu - dans, DJ, parti odaklı
    party_queries = [
        ('nightclub gece kulübü club', 'Gece Kulübü'),
        ('DJ party club', 'DJ & Party'),
        ('beach club party', 'Beach Club'),
        ('dance club elektronik müzik', 'Dans Kulübü'),
        ('rooftop bar party', 'Rooftop'),
        ('club lounge DJ', 'Lounge Club'),
    ]

    venues = []
    added_ids = set()

    # Pavyon/konsomatris filtresi için keywords
    # NOT: "gazino" kaldırıldı - Türk kültüründe geleneksel eğlence mekanları (canlı müzik, fasıl)
    pavyon_keywords = [
        'pavyon', 'konsomatris', 'casino', 'kabare', 'cabaret',
        'gece alemi', 'eglence merkezi', 'dans bar', 'show bar',
        'strip', 'striptiz', 'hostess', 'escort', 'masaj salonu',
        'gentlemen', 'club 18', 'club18', 'adult', 'yetiskin'
    ]

    # Dans kursu/topluluk filtresi için keywords
    dance_school_keywords = [
        'dans kursu', 'dans okulu', 'dans toplulugu', 'dans atolyesi',
        'dance school', 'dance studio', 'dance class', 'dance academy',
        'salsa kursu', 'tango kursu', 'bale', 'ballet', 'zumba',
        'latin dans', 'halk danslari', 'folklor', 'halk dansi', 'tango egitimi',
        'dans egitimi', 'dans dersi', 'swing', 'bachata', 'kizomba',
        'ksk-d', 'kskd'  # Karşıyaka Spor Kulübü Dans
    ]

    # Sahil/Plaj/Park filtresi - açık alan mekanlar parti mekanı değil
    outdoor_location_keywords = [
        'sahil', 'sahili', 'plaj', 'plaji', 'beach', 'koy', 'koyu',
        'park', 'parki', 'bahce', 'bahcesi', 'garden',
        'kordon', 'iskele', 'marina', 'liman'
    ]
    outdoor_location_types = ['park', 'natural_feature', 'tourist_attraction', 'beach']

    # Müzik okulu/merkezi filtresi - parti mekanı değil
    music_school_keywords = [
        'muzik merkezi', 'müzik merkezi', 'muzik okulu', 'müzik okulu',
        'konservatuar', 'conservatory', 'music school', 'music center',
        'muzik kursu', 'müzik kursu', 'enstruman', 'enstrüman',
        'piyano kursu', 'gitar kursu', 'keman kursu', 'bateri kursu',
        'ses egitimi', 'vokal', 'koro', 'choir'
    ]

    # Parti malzemeleri dükkanı filtresi - eğlence mekanı değil, mağaza
    party_store_keywords = [
        'parti malzemeleri', 'parti malzemesi', 'party malzemeleri',
        'dogum gunu malzemeleri', 'doğum günü malzemeleri', 'dogum gunu',
        'parti evi', 'party evi', 'party store', 'party shop',
        'balon', 'baloncu', 'balloon', 'parti susleme', 'parti süsleme',
        'kostum', 'kostüm', 'costume', 'maske', 'parti aksesuar',
        'parti dekor', 'dekorasyon malzemesi', 'kutlama malzemeleri'
    ]
    party_store_types = ['store', 'shopping_mall', 'home_goods_store', 'furniture_store']

    try:
        for query_term, venue_type in party_queries:
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.types,places.location,places.reviews,places.websiteUri,places.internationalPhoneNumber,places.currentOpeningHours,places.businessStatus"
                }

                payload = {
                    "textQuery": f"{query_term} in {search_location}, Turkey",
                    "languageCode": "tr",
                    "maxResultCount": 10  # Her kategori için 10 sonuç
                }

                print(f"🔍 Sorgu: {query_term} in {search_location}", file=sys.stderr, flush=True)

                response = requests.post(url, json=payload, headers=headers)

                if response.status_code != 200:
                    print(f"⚠️ API hatası ({query_term}): {response.status_code}", file=sys.stderr, flush=True)
                    continue

                places_data = response.json()
                places = places_data.get('places', [])

                for place in places:
                    place_id = place.get('id', '')
                    place_name = place.get('displayName', {}).get('text', '')
                    place_address = place.get('formattedAddress', '')
                    place_rating = place.get('rating', 0)
                    place_review_count = place.get('userRatingCount', 0)
                    place_types = place.get('types', [])

                    # Daha önce eklendiyse atla
                    if place_id in added_ids:
                        continue

                    # Exclude IDs kontrolü
                    if place_id in exclude_ids:
                        print(f"⏭️ EXCLUDE - {place_name}: zaten gösterildi", file=sys.stderr, flush=True)
                        continue

                    # Kalıcı/geçici kapalı mekan kontrolü
                    business_status = place.get('businessStatus', 'OPERATIONAL')
                    if business_status in ['CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY']:
                        print(f"❌ KAPALI MEKAN REJECT - {place_name}: {business_status}", file=sys.stderr, flush=True)
                        continue

                    # Son 7 aydır yorum gelmemişse kapalı say
                    raw_reviews = place.get('reviews', [])
                    if raw_reviews:
                        from datetime import datetime, timedelta
                        seven_months_ago = datetime.now() - timedelta(days=210)  # 7 ay

                        latest_review_time = None
                        for review in raw_reviews:
                            publish_time_str = review.get('publishTime', '')
                            if publish_time_str:
                                try:
                                    review_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
                                    review_time = review_time.replace(tzinfo=None)
                                    if latest_review_time is None or review_time > latest_review_time:
                                        latest_review_time = review_time
                                except:
                                    pass

                        if latest_review_time and latest_review_time < seven_months_ago:
                            print(f"❌ ESKİ YORUM REJECT - {place_name}: son yorum {latest_review_time.strftime('%Y-%m-%d')} (7 aydan eski)", file=sys.stderr, flush=True)
                            continue

                    # İlçe kontrolü
                    if selected_district:
                        address_lower = place_address.lower()
                        district_lower = selected_district.lower()
                        district_normalized = district_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                        address_normalized = address_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                        # Alaçatı için özel kontrol (Çeşme içinde)
                        is_alacati = 'alaçatı' in address_lower or 'alacati' in address_normalized
                        is_in_district = district_lower in address_lower or district_normalized in address_normalized

                        if not is_in_district and not (selected_district.lower() == 'çeşme' and is_alacati):
                            print(f"❌ İLÇE REJECT - {place_name}: {selected_district} içermiyor", file=sys.stderr, flush=True)
                            continue

                    # Pavyon/konsomatris filtresi
                    place_name_lower = place_name.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                    place_types_str = ' '.join(place_types).lower()

                    is_pavyon_name = any(keyword in place_name_lower for keyword in pavyon_keywords)
                    is_pavyon_type = any(keyword in place_types_str for keyword in pavyon_keywords)

                    if is_pavyon_name or is_pavyon_type:
                        print(f"❌ PAVYON REJECT - {place_name}", file=sys.stderr, flush=True)
                        continue

                    # Dans kursu/topluluk filtresi
                    is_dance_school = any(keyword in place_name_lower for keyword in dance_school_keywords)
                    dance_types = ['dance_studio', 'dance_school', 'gym', 'fitness_center']
                    is_dance_type = any(t in place_types_str for t in dance_types)

                    if is_dance_school or (is_dance_type and 'bar' not in place_types_str and 'night_club' not in place_types_str):
                        print(f"❌ DANS KURSU REJECT - {place_name}", file=sys.stderr, flush=True)
                        continue

                    # Müzik okulu/merkezi filtresi
                    is_music_school = any(keyword in place_name_lower for keyword in music_school_keywords)
                    if is_music_school:
                        print(f"❌ MÜZİK OKULU REJECT - {place_name}", file=sys.stderr, flush=True)
                        continue

                    # Parti malzemeleri dükkanı filtresi - eğlence mekanı değil, mağaza
                    is_party_store_by_name = any(keyword in place_name_lower for keyword in party_store_keywords)
                    is_party_store_by_type = any(t in place_types_str for t in party_store_types) and not any(t in place_types_str for t in ['bar', 'night_club', 'restaurant'])

                    if is_party_store_by_name or (is_party_store_by_type and 'malzeme' in place_name_lower):
                        print(f"❌ PARTİ MALZEMELERİ DÜKKANI REJECT - {place_name}: mağaza, eğlence mekanı değil", file=sys.stderr, flush=True)
                        continue

                    # Sahil/Plaj/Park filtresi - açık alan mekanlar parti mekanı değil (beach club hariç)
                    is_outdoor_by_name = any(keyword in place_name_lower for keyword in outdoor_location_keywords)
                    is_outdoor_by_type = any(t in place_types_str for t in outdoor_location_types)
                    has_club_keyword = 'club' in place_name_lower or 'kulup' in place_name_lower or 'kulüp' in place_name_lower

                    # Beach club, plaj club gibi mekanlar OK - sadece "sahil", "plaj" gibi açık alanlar reject
                    if (is_outdoor_by_name or is_outdoor_by_type) and not has_club_keyword and 'bar' not in place_types_str and 'night_club' not in place_types_str:
                        print(f"❌ SAHİL/PARK REJECT - {place_name}: açık alan, parti mekanı değil", file=sys.stderr, flush=True)
                        continue

                    # Parti/eğlence mekanı değilse filtrele (sade restoran, kafe, birahaneler)
                    # Öncelik: night_club, beach, club, lounge, DJ içeren mekanlar
                    party_positive_types = ['night_club', 'casino']
                    party_positive_keywords = ['club', 'lounge', 'dj', 'party', 'disco', 'gece', 'beach', 'plaj']
                    non_party_types = ['restaurant', 'cafe', 'meal_takeaway', 'bakery']

                    is_party_type = any(t in place_types_str for t in party_positive_types)
                    has_party_keyword = any(k in place_name_lower for k in party_positive_keywords)
                    is_just_restaurant = any(t in place_types_str for t in non_party_types) and not is_party_type and not has_party_keyword

                    # Sadece restoran/kafe ise ve parti keyword'ü yoksa reddet
                    if is_just_restaurant and 'bar' not in place_types_str:
                        print(f"❌ RESTORAN/KAFE REJECT - {place_name}: parti mekanı değil", file=sys.stderr, flush=True)
                        continue

                    # Rating filtresi - 3.5 ve üzeri (beach club'lar için esnek)
                    if place_rating < 3.5:
                        print(f"❌ RATING REJECT - {place_name}: {place_rating} < 3.5", file=sys.stderr, flush=True)
                        continue

                    # Review count filtresi - minimum 5
                    if place_review_count < 5:
                        print(f"❌ REVIEW COUNT REJECT - {place_name}: {place_review_count} < 5", file=sys.stderr, flush=True)
                        continue

                    # Tekel/Market filtresi
                    tekel_keywords = ['tekel', 'market', 'bakkal', 'büfe', 'süpermarket', 'grocery', 'liquor store', 'convenience']
                    tekel_types = ['liquor_store', 'convenience_store', 'grocery_store', 'supermarket']

                    if any(t in place_types_str for t in tekel_types) or any(k in place_name_lower for k in tekel_keywords):
                        print(f"❌ TEKEL REJECT - {place_name}", file=sys.stderr, flush=True)
                        continue

                    # Hizmet firması filtresi (DJ team, organizasyon vb.)
                    service_keywords = [
                        'dj team', 'dj hizmeti', 'dj kiralama', 'düğün dj', 'dugun dj',
                        'organizasyon', 'event planner', 'etkinlik', 'after party',
                        'ses sistemi', 'ışık sistemi', 'isik sistemi', 'sahne kiralama',
                        'catering', 'ikram hizmeti', 'parti organizasyon'
                    ]
                    service_types = ['event_planner', 'wedding_service', 'catering_service']

                    is_service_by_name = any(keyword in place_name_lower for keyword in service_keywords)
                    is_service_by_type = any(stype in place_types for stype in service_types)

                    # "DJ" kelimesi + night_club/bar tipi yoksa hizmet firması
                    has_dj_in_name = 'dj' in place_name_lower
                    is_actual_venue = any(t in place_types for t in ['night_club', 'bar', 'restaurant', 'cafe'])

                    if is_service_by_name or is_service_by_type or (has_dj_in_name and not is_actual_venue):
                        print(f"❌ HİZMET FİRMASI REJECT - {place_name}: mekan değil hizmet firması", file=sys.stderr, flush=True)
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
                    price_map = {1: '$$', 2: '$$', 3: '$$$', 4: '$$$$'}
                    price_range = price_map.get(price_level, '$$')

                    # Google Reviews formatla
                    google_reviews = []
                    raw_reviews = place.get('reviews', [])
                    sorted_reviews = sorted(
                        raw_reviews,
                        key=lambda r: r.get('publishTime', ''),
                        reverse=True
                    )[:10]
                    for review in sorted_reviews:
                        google_reviews.append({
                            'authorName': review.get('authorAttribution', {}).get('displayName', 'Anonim'),
                            'rating': review.get('rating', 5),
                            'text': review.get('text', {}).get('text', ''),
                            'relativeTime': review.get('relativePublishTimeDescription', ''),
                            'profilePhotoUrl': review.get('authorAttribution', {}).get('photoUri', ''),
                            'publishTime': review.get('publishTime', '')
                        })

                    # Yorumlarda parti/DJ/canlı müzik geçiyor mu kontrol et
                    party_keywords_in_reviews = ['dj', 'canlı müzik', 'canli muzik', 'live music', 'dans', 'dance',
                                                  'parti', 'party', 'gece', 'eğlence', 'eglence', 'sahne',
                                                  'performans', 'konser', 'müzik', 'muzik']
                    all_review_text = ' '.join([r.get('text', {}).get('text', '').lower() for r in raw_reviews])
                    party_keyword_matches = sum(1 for kw in party_keywords_in_reviews if kw in all_review_text)

                    # Bonus puan: Yorumlarda parti keyword'leri varsa
                    party_bonus = min(15, party_keyword_matches * 3)  # Her keyword için +3, max +15

                    # Vibe tags
                    vibe_tags = ['#Eğlence', f'#{venue_type.replace(" ", "")}', '#GeceHayatı']
                    if 'beach' in query_term.lower():
                        vibe_tags.append('#BeachClub')

                    # Yorumlarda DJ/canlı müzik varsa tag ekle
                    if 'dj' in all_review_text:
                        vibe_tags.append('#DJ')
                    if 'canlı müzik' in all_review_text or 'canli muzik' in all_review_text or 'live music' in all_review_text:
                        vibe_tags.append('#CanlıMüzik')
                    if 'dans' in all_review_text or 'dance' in all_review_text:
                        vibe_tags.append('#Dans')

                    # Çalışma saatleri
                    opening_hours = place.get('currentOpeningHours', {})
                    hours_list = opening_hours.get('weekdayDescriptions', [])
                    hours_text = hours_list[0] if hours_list else ''
                    is_open_now = opening_hours.get('openNow', None)

                    venue = {
                        'id': place_id,
                        'name': place_name,
                        'base_description': f"{place_name}, {search_location} bölgesinin popüler {venue_type.lower()} mekanlarından biri.",
                        'imageUrl': photo_url or 'https://images.unsplash.com/photo-1566737236500-c8ac43014a67?w=800',
                        'category': 'Eğlence & Parti',
                        'vibeTags': vibe_tags,
                        'address': place_address,
                        'priceRange': price_range,
                        'googleRating': place_rating,
                        'googleReviewCount': place_review_count,
                        'googleReviews': google_reviews,
                        'google_reviews': google_reviews,  # Gemini için
                        'matchScore': min(98, int(place_rating * 18 + min(place_review_count / 100, 15) + party_bonus)),
                        'noiseLevel': 75,
                        'googleMapsUrl': google_maps_url,
                        'website': place.get('websiteUri', ''),
                        'phoneNumber': place.get('internationalPhoneNumber', ''),
                        'hours': hours_text,
                        'weeklyHours': hours_list,
                        'isOpenNow': is_open_now,
                        'venueType': venue_type
                    }

                    venues.append(venue)
                    added_ids.add(place_id)
                    bonus_info = f" [+{party_bonus} parti bonus]" if party_bonus > 0 else ""
                    print(f"✅ EKLENDI - {place_name} ({venue_type}): ⭐{place_rating} ({place_review_count} yorum){bonus_info}", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"⚠️ {query_term} sorgusu hatası: {e}", file=sys.stderr, flush=True)
                continue

        # Puana ve yorum sayısına göre sırala
        venues.sort(key=lambda x: (x['googleRating'], x['googleReviewCount']), reverse=True)

        print(f"🪩 Toplam {len(venues)} eğlence mekanı bulundu, Gemini ile zenginleştiriliyor...", file=sys.stderr, flush=True)

        # Gemini ile practicalInfo ve atmosphereSummary ekle
        if venues:
            # Pratik bilgi içeren yorumları öncelikli seç
            practical_keywords = ['otopark', 'park', 'vale', 'valet', 'rezervasyon', 'bekle', 'sıra', 'kuyruk',
                                  'kalabalık', 'sakin', 'sessiz', 'gürültü', 'dress code', 'yaş', 'giriş',
                                  'alkol', 'kokteyl', 'bira', 'servis', 'dj', 'müzik', 'dans',
                                  'hızlı', 'yavaş', 'pahalı', 'ucuz', 'fiyat', 'hesap', 'bahçe', 'teras']

            places_list_items = []
            for i, v in enumerate(venues[:10]):
                reviews_text = ""
                if v.get('google_reviews'):
                    all_reviews = v['google_reviews']
                    practical_reviews = []
                    other_reviews = []
                    for r in all_reviews:
                        text = r.get('text', '').lower()
                        if any(kw in text for kw in practical_keywords):
                            practical_reviews.append(r)
                        else:
                            other_reviews.append(r)
                    selected_reviews = practical_reviews[:3] + other_reviews[:2]
                    top_reviews = [r.get('text', '')[:350] for r in selected_reviews if r.get('text')]
                    if top_reviews:
                        reviews_text = f" | Yorumlar: {' /// '.join(top_reviews)}"

                venue_note = f" | Tür: {v.get('venueType', '')}"
                places_list_items.append(
                    f"{i+1}. {v['name']} | Rating: {v.get('googleRating', 'N/A')}{venue_note}{reviews_text}"
                )
            places_list = "\n".join(places_list_items)

            batch_prompt = f"""Kategori: Eğlence & Parti
Kullanıcı Tercihleri: Gece hayatı, dans, parti, eğlence

Mekanlar ve Yorumları:
{places_list}

Her mekan için analiz yap ve JSON döndür:
{{
  "name": "Mekan Adı",
  "description": "2 cümle Türkçe - mekanın parti atmosferi, DJ/müzik tarzı",
  "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
  "practicalInfo": {{
    "reservationNeeded": "Tavsiye Edilir" | "Şart" | "Gerekli Değil" | null,
    "crowdLevel": "Sakin" | "Orta" | "Kalabalık" | null,
    "waitTime": "Bekleme yok" | "10-15 dk" | "20-30 dk" | null,
    "parking": "Kolay" | "Zor" | "Otopark var" | "Yok" | null,
    "hasValet": true | false | null,
    "outdoorSeating": true | false | null,
    "kidFriendly": false,
    "vegetarianOptions": null,
    "alcoholServed": true,
    "serviceSpeed": "Hızlı" | "Normal" | "Yavaş" | null,
    "priceFeeling": "Fiyatına Değer" | "Biraz Pahalı" | "Uygun" | null,
    "mustTry": "İmza kokteyl veya deneyim" | null,
    "headsUp": "Önemli uyarı (dress code, yaş sınırı, vs.)" | null
  }},
  "atmosphereSummary": {{
    "noiseLevel": "Sessiz" | "Sohbet Dostu" | "Canlı" | "Gürültülü",
    "lighting": "Loş" | "Yumuşak" | "Aydınlık",
    "privacy": "Özel" | "Yarı Özel" | "Açık Alan",
    "energy": "Sakin" | "Dengeli" | "Enerjik",
    "idealFor": ["parti gecesi", "dans", "arkadaş grubu"],
    "notIdealFor": ["romantik akşam", "sessiz sohbet"],
    "oneLiner": "Tek cümle Türkçe atmosfer özeti"
  }}
}}

practicalInfo Kuralları (YORUMLARDAN ÇIKAR):
- reservationNeeded: VIP/masa için "Şart", genel giriş için "Gerekli Değil"
- crowdLevel: Gece kulübü genelde "Kalabalık"
- parking: "Otopark", "park yeri" → "Otopark var". "Park zor", "park yok" → "Zor". Gece kulübü genelde "Zor"
- hasValet: "Vale", "valet" → true. Yoksa null veya false
- kidFriendly: Gece kulübü/bar için HER ZAMAN false
- alcoholServed: Gece kulübü/bar için HER ZAMAN true
- headsUp: Dress code, yaş sınırı (21+), giriş ücreti vb.

atmosphereSummary Kuralları:
- noiseLevel: Gece kulübü genelde "Gürültülü", lounge "Canlı"
- lighting: Gece kulübü genelde "Loş"
- privacy: Genelde "Açık Alan" veya "Yarı Özel"
- energy: Parti mekanı genelde "Enerjik"
- idealFor: Max 3 - "parti gecesi", "dans", "arkadaş grubu", "bekarlığa veda", "DJ gecesi"
- notIdealFor: Max 2 - "romantik akşam", "sessiz sohbet", "aile yemeği"
- oneLiner: Tek cümle atmosfer özeti

SADECE JSON ARRAY döndür, başka açıklama yazma."""

            try:
                model = get_genai_model()
                if model:
                    response = model.generate_content(batch_prompt)
                    response_text = response.text.strip()

                    # Güvenli JSON parse
                    response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                    response_text = response_text.strip()

                    try:
                        ai_results = json.loads(response_text)
                    except json.JSONDecodeError:
                        match = re.search(r'\[.*\]', response_text, re.DOTALL)
                        if match:
                            ai_results = json.loads(match.group())
                        else:
                            print(f"⚠️ Eğlence & Parti JSON parse edilemedi, fallback kullanılıyor", file=sys.stderr, flush=True)
                            ai_results = []

                    # AI sonuçlarını mekanlarla eşleştir
                    ai_by_name = {r.get('name', '').lower(): r for r in ai_results}

                    final_venues = []
                    for venue_data in venues[:10]:
                        ai_data = ai_by_name.get(venue_data['name'].lower(), {})

                        venue = {
                            'id': venue_data['id'],
                            'name': venue_data['name'],
                            'description': ai_data.get('description', venue_data['base_description']),
                            'imageUrl': venue_data['imageUrl'],
                            'category': 'Eğlence & Parti',
                            'vibeTags': ai_data.get('vibeTags', venue_data.get('vibeTags', ['#Eğlence'])),
                            'address': venue_data['address'],
                            'priceRange': venue_data['priceRange'],
                            'googleRating': venue_data.get('googleRating', 4.0),
                            'googleReviewCount': venue_data.get('googleReviewCount', 0),
                            'matchScore': venue_data['matchScore'],
                            'noiseLevel': venue_data['noiseLevel'],
                            'googleMapsUrl': venue_data['googleMapsUrl'],
                            'googleReviews': venue_data.get('googleReviews', []),
                            'website': venue_data.get('website', ''),
                            'phoneNumber': venue_data.get('phoneNumber', ''),
                            'hours': venue_data.get('hours', ''),
                            'weeklyHours': venue_data.get('weeklyHours', []),
                            'isOpenNow': venue_data.get('isOpenNow', None),
                            'venueType': venue_data.get('venueType', ''),
                            'practicalInfo': ai_data.get('practicalInfo', {}),
                            'atmosphereSummary': ai_data.get('atmosphereSummary', {
                                'noiseLevel': 'Gürültülü',
                                'lighting': 'Loş',
                                'privacy': 'Açık Alan',
                                'energy': 'Enerjik',
                                'idealFor': ['parti gecesi', 'dans'],
                                'notIdealFor': ['romantik akşam'],
                                'oneLiner': 'Enerjik parti atmosferi sunan popüler bir mekan.'
                            })
                        }
                        final_venues.append(venue)

                    print(f"✅ Gemini ile {len(final_venues)} Eğlence & Parti mekan zenginleştirildi", file=sys.stderr, flush=True)

                    # ===== CACHE'E KAYDET (sadece API'den gelen yeni venue'lar) =====
                    if final_venues:
                        save_venues_to_cache(
                            venues=final_venues,
                            category_name='Eğlence & Parti',
                            city=city,
                            district=selected_district,
                            neighborhood=selected_neighborhood
                        )

                    # ===== HYBRID: CACHE + API VENUE'LARINI BİRLEŞTİR =====
                    combined_venues = []
                    for cv in cached_venues:
                        if len(combined_venues) < 10:
                            combined_venues.append(cv)
                    existing_ids = {v.get('id') for v in combined_venues}
                    for av in final_venues:
                        if len(combined_venues) < 10 and av.get('id') not in existing_ids:
                            combined_venues.append(av)
                            existing_ids.add(av.get('id'))

                    print(f"🔀 HYBRID RESULT - Eğlence & Parti Cache: {len(cached_venues)}, API: {len(final_venues)}, Combined: {len(combined_venues)}", file=sys.stderr, flush=True)
                    return Response(combined_venues, status=status.HTTP_200_OK)

            except Exception as e:
                print(f"❌ Gemini Eğlence & Parti hatası: {e}", file=sys.stderr, flush=True)
                # Fallback: Gemini olmadan mekanları döndür
                for venue_data in venues:
                    venue_data['description'] = venue_data.pop('base_description', venue_data.get('description', ''))
                    venue_data['practicalInfo'] = {}
                    venue_data['atmosphereSummary'] = {
                        'noiseLevel': 'Gürültülü',
                        'lighting': 'Loş',
                        'privacy': 'Açık Alan',
                        'energy': 'Enerjik',
                        'idealFor': ['parti gecesi'],
                        'notIdealFor': [],
                        'oneLiner': 'Enerjik parti atmosferi sunan popüler bir mekan.'
                    }

        # ===== CACHE'E KAYDET (Fallback - sadece API'den gelen yeni venue'lar) =====
        if venues:
            save_venues_to_cache(
                venues=venues,
                category_name='Eğlence & Parti',
                city=city,
                district=selected_district,
                neighborhood=selected_neighborhood
            )

        # ===== HYBRID: CACHE + API VENUE'LARINI BİRLEŞTİR =====
        combined_venues = []
        for cv in cached_venues:
            if len(combined_venues) < 10:
                combined_venues.append(cv)
        existing_ids = {v.get('id') for v in combined_venues}
        for av in venues:
            if len(combined_venues) < 10 and av.get('id') not in existing_ids:
                combined_venues.append(av)
                existing_ids.add(av.get('id'))

        print(f"🔀 HYBRID RESULT - Eğlence & Parti (Fallback) Cache: {len(cached_venues)}, API: {len(venues)}, Combined: {len(combined_venues)}", file=sys.stderr, flush=True)
        return Response(combined_venues, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Party venues generation error: {e}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return Response(
            {'error': f'Eğlence mekanları getirilirken hata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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


# Kategori -> Context mapping (context-based venue matching için)
CATEGORY_TO_CONTEXT = {
    "Fine Dining": "fine_dining",
    "İlk Buluşma": "first_date",
    "İş Yemeği": "business_meal",
    "Muhabbet": "casual_hangout",
    "Özel Gün": "special_occasion",
    "Kahvaltı & Brunch": "breakfast_brunch",
    "Aile Yemeği": "family_meal",
    "Romantik Akşam": "romantic_dinner",
    "İş Çıkışı Bira & Kokteyl": "after_work",
    "Eğlence & Parti": "friends_hangout",
    "Kafa Dinleme": "casual_hangout",
    "3. Nesil Kahveci": "casual_hangout",
    "Meyhane": "friends_hangout",
    "Balıkçı": "fine_dining",
}

def sort_venues_by_context(venues, category_name):
    """Context skoruna göre mekanları sıralar ve 50 altını filtreler"""
    context_key = CATEGORY_TO_CONTEXT.get(category_name, "friends_hangout")

    # Context skoru olan mekanları filtrele ve sırala
    filtered = []
    for v in venues:
        context_score = v.get('contextScore', {})
        score = context_score.get(context_key, 75)  # Default 75 (eğer contextScore yoksa)
        if score >= 50:
            v['matchScore'] = score  # matchScore'u context skoruyla güncelle
            filtered.append(v)

    # Context skoruna göre sırala
    sorted_venues = sorted(filtered, key=lambda x: x['matchScore'], reverse=True)
    return sorted_venues


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
    exclude_ids = set(data.get('excludeIds', []))  # Set for O(1) lookup

    # DEBUG: Log incoming request data (wrapped to prevent BrokenPipeError)
    import sys
    try:
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"🔍 INCOMING REQUEST DEBUG", file=sys.stderr, flush=True)
        print(f"{'='*60}", file=sys.stderr, flush=True)
        print(f"Category: {category}", file=sys.stderr, flush=True)
        print(f"Filters received: {json.dumps(filters, indent=2, ensure_ascii=False)}", file=sys.stderr, flush=True)
        print(f"Alcohol filter value: {filters.get('alcohol', 'NOT SET')}", file=sys.stderr, flush=True)
        print(f"Exclude IDs count: {len(exclude_ids)}", file=sys.stderr, flush=True)
        if exclude_ids:
            print(f"Exclude IDs: {list(exclude_ids)[:5]}...", file=sys.stderr, flush=True)
        print(f"{'='*60}\n", file=sys.stderr, flush=True)
    except BrokenPipeError:
        pass  # İstemci bağlantıyı kapattı, devam et

    try:
        # Tatil kategorisi için özel işlem
        if category['name'] == 'Tatil':
            # Tatil kategorisi için deneyim bazlı öneri sistemi
            return generate_vacation_experiences(location, trip_duration, filters)

        # Fine Dining kategorisi için özel işlem - önce Michelin restoranları
        if category['name'] == 'Fine Dining':
            return generate_fine_dining_with_michelin(location, filters, exclude_ids)

        # Yerel Festivaller kategorisi için özel işlem
        if category['name'] == 'Yerel Festivaller':
            return generate_local_festivals(location, filters)

        # Adrenalin kategorisi için özel işlem - deneyim bazlı
        if category['name'] == 'Adrenalin':
            return generate_adrenaline_experiences(location, filters)

        # Hafta Sonu Gezintisi/Kaçamağı kategorisi için özel işlem - deneyim bazlı
        if category['name'] in ['Hafta Sonu Gezintisi', 'Hafta Sonu Kaçamağı']:
            return generate_weekend_trip_experiences(location, filters)

        # Piknik kategorisi için özel işlem - tabiat parkları ve büyük doğa alanları
        if category['name'] == 'Piknik':
            return generate_picnic_experiences(location, filters)

        # Sahne Sanatları / Tiyatro kategorisi için özel işlem - etkinlik bazlı
        if category['name'] in ['Sahne Sanatları', 'Tiyatro']:
            return generate_performing_arts_events(location, filters)

        # Konserler / Konser kategorisi için özel işlem - etkinlik bazlı
        if category['name'] in ['Konserler', 'Konser']:
            return generate_concerts(location, filters)

        # Sokak Lezzeti kategorisi için özel işlem - Gemini-first arama
        if category['name'] == 'Sokak Lezzeti':
            return generate_street_food_places(location, filters, exclude_ids)

        # Eğlence & Parti kategorisi için özel işlem - çoklu sorgu
        if category['name'] == 'Eğlence & Parti':
            return generate_party_venues(location, filters, exclude_ids)

        # ===== HYBRID CACHE SİSTEMİ =====
        # Cache'ten venue'lar + API'den taze venue'lar = Toplam 10 venue
        city = location.get('city', 'İzmir')
        districts = location.get('districts', [])
        selected_district = districts[0] if districts else None

        # Load More isteği mi kontrol et
        is_load_more_request = bool(exclude_ids) and len(exclude_ids) > 0

        # Load More durumunda cache limitini artır (daha fazla alternatif mekan bul)
        cache_limit = CACHE_VENUES_LIMIT_LOAD_MORE if is_load_more_request else CACHE_VENUES_LIMIT

        # Cache'ten venue'ları ve tüm cache'li place_id'leri al
        cached_venues, all_cached_ids = get_cached_venues_for_hybrid(
            category_name=category['name'],
            city=city,
            district=selected_district,
            exclude_ids=exclude_ids,
            limit=cache_limit
        )

        # API çağrısında cache'teki venue'ları exclude et (tekrar çekmemek için)
        api_exclude_ids = (exclude_ids or set()) | all_cached_ids

        print(f"🔀 HYBRID - Cache: {len(cached_venues)} venue, API exclude: {len(api_exclude_ids)} ID, LoadMore: {is_load_more_request}", file=sys.stderr, flush=True)

        # ===== LOAD MORE: ÖNCE CACHE'TEN YENİ MEKANLAR DENE =====
        # Cache'te henüz gösterilmemiş mekan varsa bunları döndür (API maliyeti yok!)
        if is_load_more_request and len(cached_venues) >= 5:
            print(f"✅ LOAD MORE CACHE HIT - {len(cached_venues)} yeni mekan cache'ten döndürülüyor!", file=sys.stderr, flush=True)
            # Instagram URL enrichment - cache'deki eksik Instagram URL'lerini bul
            enriched_venues = enrich_cached_venues_with_instagram(cached_venues[:10], city)
            return Response(enriched_venues, status=status.HTTP_200_OK)

        # ===== CACHE YETERLI İSE API ÇAĞRISINI ATLA (MALİYET OPTİMİZASYONU) =====
        # Cache'te 10+ venue varsa direkt döndür, API çağrısı yapma
        MIN_VENUES_FOR_CACHE_ONLY = 10  # 10 mekan varsa cache yeterli

        if len(cached_venues) >= MIN_VENUES_FOR_CACHE_ONLY and not is_load_more_request:
            print(f"✅ CACHE HIT - {len(cached_venues)} venue cache'ten döndürülüyor, API çağrısı atlandı!", file=sys.stderr, flush=True)
            # Instagram URL enrichment - cache'deki eksik Instagram URL'lerini bul
            enriched_venues = enrich_cached_venues_with_instagram(cached_venues, city)
            return Response(enriched_venues, status=status.HTTP_200_OK)

        # API'ye gitme gerekiyor - log yaz
        if is_load_more_request:
            print(f"🔄 LOAD MORE - Cache'te yetersiz mekan ({len(cached_venues)}), API'ye gidiliyor...", file=sys.stderr, flush=True)

        # Kategori bazlı query mapping (Tatil, Michelin, Festivaller, Adrenalin, Hafta Sonu Gezintisi, Sahne Sanatları, Konserler ve Sokak Lezzeti hariç)
        # ALKOL FİLTRESİNE GÖRE DİNAMİK QUERY OLUŞTUR
        alcohol_filter = filters.get('alcohol', 'Any')

        if alcohol_filter == 'Alcoholic':
            # Alkollü mekan seçilirse SADECE bar, pub, restaurant, wine bar ara
            category_query_map = {
                'İlk Buluşma': 'bar wine bar restaurant pub',
                'İş Yemeği': 'restaurant bar hotel lounge business lunch',
                'Muhabbet': 'bar pub lounge restaurant wine bar',
                'İş Çıkışı Bira & Kokteyl': 'bar pub cocktail bar beer garden',
                'Eğlence & Parti': 'nightclub bar pub dance club beach club rooftop bar live music lounge',
                'Özel Gün': 'fine dining restaurant wine bar romantic',
                'Kahvaltı & Brunch': 'kahvaltı brunch restaurant bar mimosa serpme kahvaltı',
                'Kafa Dinleme': 'lounge bar quiet restaurant',
                'Odaklanma': 'bar restaurant lounge',
                'Aile Yemeği': 'restaurant bar casual dining',
                '3. Nesil Kahveci': 'specialty coffee third wave coffee roastery cafe',
                'Konserler': 'live music venue concert hall bar',
                'Sahne Sanatları': 'theater venue performance hall',
                'Yerel Festivaller': 'festival event venue',
                'Müze': 'museum',
                'Galeri': 'art gallery contemporary art gallery sanat galerisi',
                'Hafta Sonu Gezintisi': 'winery vineyard restaurant',
                'Piknik': 'park garden outdoor',
                'Beach Club': 'beach club bar restaurant',
                'Plaj': 'beach bar restaurant',
                'Adrenalin': 'adventure sports extreme',
                'Spor': 'gym fitness yoga studio',
                'Fine Dining': 'fine dining restaurant wine bar michelin gourmet upscale luxury tasting menu',
                'Balıkçı': 'balık restoranı seafood restaurant rakı balık',
                'Meyhane': 'meyhane rakı meze',
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
                'Kahvaltı & Brunch': 'kahvaltı breakfast brunch cafe serpme kahvaltı',
                'Kafa Dinleme': 'quiet cafe tea house peaceful spot',
                'Odaklanma': 'coworking space cafe library quiet study',
                'Aile Yemeği': 'family restaurant cafe casual dining',
                '3. Nesil Kahveci': 'specialty coffee third wave coffee roastery',
                'Konserler': 'concert hall music venue',
                'Sahne Sanatları': 'theater venue performance hall',
                'Yerel Festivaller': 'festival event venue',
                'Müze': 'museum exhibition',
                'Galeri': 'art gallery contemporary art gallery sanat galerisi',
                'Hafta Sonu Gezintisi': 'scenic spot nature walk daytrip',
                'Piknik': 'park garden picnic area',
                'Beach Club': 'beach club resort',
                'Plaj': 'beach seaside',
                'Adrenalin': 'adventure sports extreme activities',
                'Spor': 'gym fitness yoga studio pilates',
                'Fine Dining': 'fine dining restaurant gourmet upscale',
            }
        else:
            # Any seçilirse her türlü mekan (varsayılan)
            category_query_map = {
                'İlk Buluşma': 'cafe restaurant bar wine bar coffee shop',
                'İş Yemeği': 'business lunch restaurant cafe meeting spot',
                'Muhabbet': 'cafe bar lounge restaurant cozy spot conversation friendly',
                'İş Çıkışı Bira & Kokteyl': 'bar pub cocktail bar beer garden after work drinks',
                'Eğlence & Parti': 'nightclub bar pub dance club beach club rooftop bar live music lounge entertainment',
                'Özel Gün': 'fine dining restaurant romantic celebration',
                'Kahvaltı & Brunch': 'kahvaltı breakfast brunch cafe serpme kahvaltı',
                'Kafa Dinleme': 'quiet cafe lounge peaceful spot relaxing',
                'Odaklanma': 'coworking space cafe library quiet study',
                'Aile Yemeği': 'family restaurant casual dining kid friendly',
                '3. Nesil Kahveci': 'specialty coffee third wave coffee roastery artisan',
                'Konserler': 'live music venue concert hall',
                'Sahne Sanatları': 'theater venue stand up comedy performance',
                'Yerel Festivaller': 'festival event food festival',
                'Müze': 'museum art exhibition',
                'Galeri': 'art gallery contemporary art gallery sanat galerisi modern art',
                'Hafta Sonu Gezintisi': 'scenic spot nature daytrip excursion',
                'Piknik': 'park garden picnic area green space',
                'Beach Club': 'beach club resort pool bar',
                'Plaj': 'beach seaside coast',
                'Adrenalin': 'adventure sports extreme activities outdoor',
                'Spor': 'gym fitness yoga studio pilates wellness',
                'Fine Dining': 'fine dining restaurant upscale gourmet michelin luxury tasting menu',
                'Meyhane': 'meyhane restaurant turkish tavern rakı meze',
                'Balıkçı': 'balık restoranı seafood restaurant balık lokantası',
                'Sokak Lezzeti': 'kokoreç midye balık ekmek tantuni lahmacun pide söğüş çiğköfte döner',
                'Burger & Fast': 'burger hamburger fast food',
                'Pizzacı': 'pizza pizzeria italian pizza',
            }

        # Kategori ve filtrelere göre arama sorgusu oluştur
        search_query = category_query_map.get(category['name'], category['name'])

        # Filtrelere göre sorguyu genişlet
        if filters.get('vibes'):
            search_query += f" {' '.join(filters['vibes'])}"

        # Lokasyon oluştur
        city = location['city']
        districts = location.get('districts', [])
        neighborhoods = location.get('neighborhoods', [])
        selected_district = districts[0] if districts else None
        selected_neighborhood = neighborhoods[0] if neighborhoods else None

        # Semt varsa semt ile ara, yoksa ilçe ile ara
        if selected_neighborhood:
            search_location = f"{selected_neighborhood}, {selected_district}, {city}"
        elif selected_district:
            search_location = f"{selected_district}, {city}"
        else:
            search_location = city

        import sys
        print(f"DEBUG - Selected District: {selected_district}", file=sys.stderr, flush=True)
        print(f"DEBUG - Selected Neighborhood: {selected_neighborhood}", file=sys.stderr, flush=True)
        print(f"DEBUG - Search Location: {search_location}", file=sys.stderr, flush=True)
        print(f"DEBUG - Exclude IDs count: {len(exclude_ids)}", file=sys.stderr, flush=True)

        # Google Places API'den mekan ara
        gmaps = get_gmaps_client()
        places_result = {'results': []}

        # Nearby Search için uygun kategoriler (Meyhane hariç - text search daha iyi sonuç veriyor)
        nearby_search_categories = ['İş Çıkışı Bira & Kokteyl']

        # Kategori bazlı included types (Google Places API için)
        category_included_types = {
            'İş Çıkışı Bira & Kokteyl': ['bar', 'pub', 'night_club'],
        }

        if gmaps:
            try:
                import requests
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.priceLevel,places.types,places.location,places.reviews,places.websiteUri,places.internationalPhoneNumber,places.currentOpeningHours,places.businessStatus"
                }

                # İş Çıkışı Bira & Kokteyl ve Meyhane için Nearby Search kullan
                if category['name'] in nearby_search_categories:
                    # Önce lokasyonun koordinatlarını al (geocode)
                    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
                    geocode_params = {
                        "address": f"{search_location}, Turkey",
                        "key": settings.GOOGLE_MAPS_API_KEY
                    }
                    geocode_response = requests.get(geocode_url, params=geocode_params)

                    if geocode_response.status_code == 200:
                        geocode_data = geocode_response.json()
                        if geocode_data.get('results'):
                            location_coords = geocode_data['results'][0]['geometry']['location']
                            lat, lng = location_coords['lat'], location_coords['lng']

                            print(f"🗺️ Nearby Search - {category['name']}: {search_location} -> ({lat}, {lng})", file=sys.stderr, flush=True)

                            # Nearby Search API çağrısı
                            nearby_url = "https://places.googleapis.com/v1/places:searchNearby"
                            included_types = category_included_types.get(category['name'], ['bar', 'restaurant'])

                            nearby_payload = {
                                "includedTypes": included_types,
                                "maxResultCount": 20,
                                "locationRestriction": {
                                    "circle": {
                                        "center": {
                                            "latitude": lat,
                                            "longitude": lng
                                        },
                                        "radius": 2000.0  # 2km yarıçap
                                    }
                                },
                                "languageCode": "tr"
                            }

                            print(f"🔍 Nearby Search types: {included_types}", file=sys.stderr, flush=True)

                            response = requests.post(nearby_url, json=nearby_payload, headers=headers)

                            if response.status_code == 200:
                                places_data = response.json()
                                places_result = {'results': places_data.get('places', [])}
                                print(f"✅ Nearby Search sonuç: {len(places_result['results'])} mekan", file=sys.stderr, flush=True)
                            else:
                                print(f"Nearby Search API hatası: {response.status_code} - {response.text}", file=sys.stderr, flush=True)
                                # Fallback: Text Search kullan
                                url = "https://places.googleapis.com/v1/places:searchText"
                                payload = {
                                    "textQuery": f"{search_query} in {search_location}, Turkey",
                                    "languageCode": "tr",
                                    "maxResultCount": 20
                                }
                                response = requests.post(url, json=payload, headers=headers)
                                if response.status_code == 200:
                                    places_data = response.json()
                                    places_result = {'results': places_data.get('places', [])}
                                else:
                                    print(f"❌ Text Search fallback hatası: {response.status_code}", file=sys.stderr, flush=True)
                        else:
                            print(f"⚠️ Geocode sonuç bulunamadı: {search_location}", file=sys.stderr, flush=True)
                    else:
                        print(f"❌ Geocode hatası: {geocode_response.status_code}", file=sys.stderr, flush=True)
                else:
                    # Diğer kategoriler için Text Search kullan
                    url = "https://places.googleapis.com/v1/places:searchText"
                    payload = {
                        "textQuery": f"{search_query} in {search_location}, Turkey",
                        "languageCode": "tr",
                        "maxResultCount": 20  # Maximum sonuç
                    }

                    print(f"DEBUG - Google Places API Query: {payload['textQuery']}", file=sys.stderr, flush=True)

                    response = requests.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        places_data = response.json()
                        places_result = {'results': places_data.get('places', [])}
                    else:
                        print(f"❌ Places API hatası: {response.status_code} - {response.text}", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"❌ Google Places API hatası: {e}", file=sys.stderr, flush=True)

        # Google Places sonuç bulamadıysa boş liste dön (mock data ASLA kullanılmaz)
        if not places_result.get('results'):
            print(f"⚠️ NO RESULTS - Google Places sonuç bulamadı: {category.get('name', 'Unknown')} / {location}", file=sys.stderr, flush=True)
            return Response([], status=status.HTTP_200_OK)

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

            # ===== EXCLUDE IDS FİLTRESİ: Daha önce gösterilen mekanları atla =====
            if place_id in exclude_ids:
                print(f"⏭️ EXCLUDE REJECT - {place_name}: zaten gösterildi (ID: {place_id})", file=sys.stderr, flush=True)
                continue

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

            # ===== MAHALLE/SEMT FİLTRESİ: Seçilen mahalleye ait olmayan mekanları atla =====
            if selected_neighborhood:
                address_lower = place_address.lower()
                neighborhood_lower = selected_neighborhood.lower()
                # Türkçe karakterleri normalize et
                neighborhood_normalized = neighborhood_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                address_normalized = address_lower.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                if neighborhood_lower not in address_lower and neighborhood_normalized not in address_normalized:
                    print(f"❌ MAHALLE REJECT - {place_name} adresi '{selected_neighborhood}' içermiyor: {place_address}", file=sys.stderr, flush=True)
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

            # Balıkçı ve Meyhane kategorilerinde alkol filtresini ATLA - Gemini karar versin
            category_name = category['name']
            skip_alcohol_filter = category_name in ['Balıkçı', 'Meyhane']

            if alcohol_filter == 'Alcoholic' and not skip_alcohol_filter:
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

            elif alcohol_filter == 'Non-Alcoholic' and not skip_alcohol_filter:
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

            # ===== KAPALI MEKAN KONTROLÜ (TÜM KATEGORİLER) =====
            # Kalıcı veya geçici kapalı mekanları hariç tut
            business_status = place.get('businessStatus', 'OPERATIONAL')
            if business_status in ['CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY']:
                print(f"❌ KAPALI MEKAN REJECT - {place_name}: {business_status}", file=sys.stderr, flush=True)
                continue

            # ===== ESKİ YORUM KONTROLÜ (TÜM KATEGORİLER) =====
            # 7 aydır yorum gelmemişse muhtemelen kapalı - filtrele
            # NOT: 50+ yorumu olan popüler mekanlar bu kontrolden muaf (sezonluk mekanlar için)
            if place_review_count < 50:
                raw_reviews = place.get('reviews', [])
                if raw_reviews:
                    from datetime import datetime, timedelta
                    seven_months_ago = datetime.now() - timedelta(days=210)  # 7 ay

                    # En güncel yorumu bul
                    latest_review_time = None
                    for review in raw_reviews:
                        publish_time_str = review.get('publishTime', '')
                        if publish_time_str:
                            try:
                                review_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
                                review_time = review_time.replace(tzinfo=None)
                                if latest_review_time is None or review_time > latest_review_time:
                                    latest_review_time = review_time
                            except:
                                pass

                    # En güncel yorum 7 aydan eski mi?
                    if latest_review_time and latest_review_time < seven_months_ago:
                        print(f"❌ ESKİ YORUM REJECT - {place_name}: son yorum {latest_review_time.strftime('%Y-%m-%d')} (7 aydan eski)", file=sys.stderr, flush=True)
                        continue

            # ===== KAPANMIŞ MEKAN KONTROLÜ (YORUM İÇERİĞİ) =====
            # Google "OPERATIONAL" dese bile yorumlarda "kapandı" yazıyorsa filtrele
            # NOT: "el değiştir" kaldırıldı - el değiştirmek kapanmak anlamına gelmiyor
            raw_reviews = place.get('reviews', [])
            if raw_reviews:
                closed_keywords = [
                    'kalıcı olarak kapan', 'kalici olarak kapan',
                    'artık kapalı', 'artik kapali',
                    'kapandı', 'kapandi',
                    'kapanmış', 'kapanmis',
                    'permanently closed', 'closed permanently',
                    'yeni işletme', 'yeni isletme',
                    'isim değişti', 'isim degisti',
                    'yerine açıldı', 'yerine acildi',
                    'burası artık', 'burasi artik'
                ]

                is_closed_by_reviews = False
                for review in raw_reviews[:5]:  # Son 5 yorumu kontrol et
                    review_text = review.get('text', {}).get('text', '').lower()
                    review_text_normalized = review_text.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')

                    for keyword in closed_keywords:
                        keyword_normalized = keyword.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u')
                        if keyword_normalized in review_text_normalized:
                            is_closed_by_reviews = True
                            print(f"❌ KAPANMIŞ MEKAN (YORUM) REJECT - {place_name}: yorumda '{keyword}' bulundu", file=sys.stderr, flush=True)
                            break
                    if is_closed_by_reviews:
                        break

                if is_closed_by_reviews:
                    continue

            # ===== TEKEL/MARKET FİLTRESİ =====
            # Tüm kategorilerde tekel, market, bakkal gibi yerleri hariç tut
            tekel_keywords = [
                'tekel', 'market', 'bakkal', 'büfe', 'süpermarket', 'grocery',
                'liquor store', 'convenience', 'mini market', 'minimarket',
                'alcohol palace', 'içki', 'şarküteri', 'manav', 'kuruyemiş'
            ]

            # Types içinde liquor_store, convenience_store, grocery_store varsa filtrele
            tekel_types = ['liquor_store', 'convenience_store', 'grocery_store', 'supermarket']
            is_tekel_type = any(t_type in place_types_str for t_type in tekel_types)
            is_tekel_name = any(keyword in place_name_lower for keyword in tekel_keywords)

            if is_tekel_type or is_tekel_name:
                print(f"❌ TEKEL/MARKET REJECT - {place_name}: types={place_types}", file=sys.stderr, flush=True)
                continue

            # ===== RESTORAN KALİTE FİLTRESİ =====
            # Restoran/yemek kategorileri için puan, yorum sayısı ve güncellik kontrolü
            restaurant_categories = [
                'İlk Buluşma', 'Fine Dining', 'Özel Gün', 'İş Yemeği', 'Öğlen Yemeği',
                'Esnaf Lokantası', 'Balıkçı', 'Meyhane', 'Muhabbet', 'Brunch',
                '3. Nesil Kahveci', 'İş Çıkışı Bira & Kokteyl', 'Sokak Lezzeti',
                'Burger & Fast', 'Pizzacı'
            ]

            if category_name in restaurant_categories:
                # 1. Puan filtresi - 4.0 ve üstü kabul
                if place_rating < 4.0:
                    print(f"❌ RESTORAN RATING REJECT - {place_name}: rating={place_rating} < 4.0", file=sys.stderr, flush=True)
                    continue

                # 2. Yorum sayısı filtresi - Sokak Lezzeti için 20, diğerleri için 10
                min_reviews = 20 if category_name == 'Sokak Lezzeti' else 10
                if place_review_count < min_reviews:
                    print(f"❌ RESTORAN REVIEW COUNT REJECT - {place_name}: reviews={place_review_count} < {min_reviews}", file=sys.stderr, flush=True)
                    continue

                # 3. Güncellik filtresi - En güncel yorum 6 aydan eski olmamalı
                # NOT: 50+ yorumu olan popüler mekanlar bu kontrolden muaf (sezonluk mekanlar için)
                if place_review_count < 50:  # Sadece 50'den az yorumu olan mekanlar için güncellik kontrolü
                    raw_reviews = place.get('reviews', [])
                    if raw_reviews:
                        from datetime import datetime, timedelta
                        six_months_ago = datetime.now() - timedelta(days=180)  # 6 ay

                        # En güncel yorumu bul
                        latest_review_time = None
                        for review in raw_reviews:
                            publish_time_str = review.get('publishTime', '')
                            if publish_time_str:
                                try:
                                    # Format: "2024-12-10T14:30:00Z"
                                    review_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
                                    review_time = review_time.replace(tzinfo=None)  # Remove timezone for comparison
                                    if latest_review_time is None or review_time > latest_review_time:
                                        latest_review_time = review_time
                                except:
                                    pass

                        # En güncel yorum 6 aydan eski mi?
                        if latest_review_time and latest_review_time < six_months_ago:
                            print(f"❌ RESTORAN ESKİ YORUM REJECT - {place_name}: son yorum {latest_review_time.strftime('%Y-%m-%d')} (6 aydan eski)", file=sys.stderr, flush=True)
                            continue

            # ===== PAVYON/KONSOMATRIS FİLTRESİ =====
            # Eğlence & Parti kategorisi için uygunsuz mekanları filtrele
            if category['name'] == 'Eğlence & Parti':
                # NOT: "gazino" kaldırıldı - Türk kültüründe geleneksel eğlence mekanları (canlı müzik, fasıl)
                pavyon_keywords = [
                    'pavyon', 'konsomatris', 'casino', 'kabare', 'cabaret',
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

                # ===== HİZMET FİRMASI FİLTRESİ =====
                # DJ hizmeti, organizasyon firmaları, event planner vb. mekan değil hizmet veren firmalar
                service_keywords = [
                    'dj team', 'dj hizmeti', 'dj kiralama', 'düğün dj', 'dugun dj',
                    'organizasyon', 'event planner', 'etkinlik', 'after party',
                    'ses sistemi', 'ışık sistemi', 'isik sistemi', 'sahne kiralama',
                    'catering', 'ikram hizmeti', 'parti organizasyon'
                ]
                service_types = ['event_planner', 'wedding_service', 'catering_service']

                is_service_by_name = any(keyword in place_name_lower for keyword in service_keywords)
                is_service_by_type = any(stype in place_types for stype in service_types)

                # "DJ" kelimesi + night_club/bar tipi yoksa hizmet firması
                has_dj_in_name = 'dj' in place_name_lower
                is_actual_venue = any(t in place_types for t in ['night_club', 'bar', 'restaurant', 'cafe'])

                if is_service_by_name or is_service_by_type or (has_dj_in_name and not is_actual_venue):
                    print(f"❌ HİZMET FİRMASI REJECT - {place_name}: mekan değil hizmet firması (types: {place_types})", file=sys.stderr, flush=True)
                    continue

                # ===== RATING & REVIEW COUNT FİLTRESİ =====
                # Eğlence & Parti kategorisi için düşük puanlı ve az yorumlu mekanları filtrele
                if place_rating < 3.5:
                    print(f"❌ RATING REJECT - {place_name}: rating={place_rating} < 3.5", file=sys.stderr, flush=True)
                    continue

                if place_review_count < 5:
                    print(f"❌ REVIEW REJECT - {place_name}: reviews={place_review_count} < 5", file=sys.stderr, flush=True)
                    continue

            # ===== MEYHANE KATEGORİSİ FİLTRESİ =====
            # Meyhane kategorisinde place_types tabanlı filtreleme - Gemini AI karar verecek
            if category['name'] == 'Meyhane':
                # İsminde meyhane geçenler direkt kabul
                meyhane_keywords = ['meyhane', 'meyhanesi', 'rakı', 'fasıl']
                is_meyhane_by_name = any(keyword in place_name_lower for keyword in meyhane_keywords)

                # Place types ile meyhane olabilecek tipler: bar, restaurant, turkish_restaurant
                meyhane_compatible_types = ['bar', 'restaurant', 'turkish_restaurant', 'meal_takeaway', 'meal_delivery']
                is_meyhane_by_type = any(ptype in place_types for ptype in meyhane_compatible_types)

                # Yorumlarda rakı geçenler de kabul edilsin
                is_meyhane_by_reviews = False
                meyhane_review_keywords = ['rakı', 'raki', 'meyhane', 'meze', 'fasıl', 'fasil']
                for review in raw_reviews[:5]:
                    review_text = review.get('text', {}).get('text', '').lower()
                    if any(keyword in review_text for keyword in meyhane_review_keywords):
                        is_meyhane_by_reviews = True
                        break

                # İsminde, tipinde veya yorumlarında meyhane uyumlu değilse reddet
                if not is_meyhane_by_name and not is_meyhane_by_type and not is_meyhane_by_reviews:
                    print(f"❌ MEYHANE REJECT - {place_name}: uygun tip yok (types: {place_types})", file=sys.stderr, flush=True)
                    continue

                # Gemini AI kararı için devam et - isRelevant kontrolü yapılacak
                print(f"✅ MEYHANE PASS - {place_name}: name_match={is_meyhane_by_name}, type_match={is_meyhane_by_type}, review_match={is_meyhane_by_reviews}", file=sys.stderr, flush=True)

            # ===== BALIKÇI KATEGORİSİ FİLTRESİ =====
            # Balıkçı kategorisinde balık pişiricilerini hariç tut
            if category['name'] == 'Balıkçı':
                # Rating filtresi - 3.9 altını reddet
                if place_rating < 3.9:
                    print(f"❌ BALIKÇI RATING REJECT - {place_name}: rating={place_rating} < 3.9", file=sys.stderr, flush=True)
                    continue

                # Review count filtresi - 10'dan az yorumu reddet
                if place_review_count < 10:
                    print(f"❌ BALIKÇI REVIEW REJECT - {place_name}: reviews={place_review_count} < 10", file=sys.stderr, flush=True)
                    continue

                # İsim bazlı filtre - balık pişiricileri ve marketleri hariç tut
                excluded_keywords = ['pişirici', 'balık ekmek', 'balıkekmek', 'tezgah', 'market', 'pazarı', 'hal']
                is_excluded = any(keyword in place_name_lower for keyword in excluded_keywords)

                if is_excluded:
                    print(f"❌ BALIKÇI REJECT - {place_name}: balık pişirici/market türü", file=sys.stderr, flush=True)
                    continue

            # ===== ZİNCİR MAĞAZA FİLTRESİ (ROMANTİK KATEGORİLER) =====
            # İlk Buluşma, Özel Gün, Fine Dining gibi romantik kategorilerde zincir mekanları filtrele
            romantic_categories = ['İlk Buluşma', 'Özel Gün', 'Fine Dining', 'Romantik Akşam']

            if category_name in romantic_categories:
                chain_store_blacklist = [
                    # Kahve zincirleri
                    'starbucks', 'gloria jeans', 'caribou', 'coffee bean', 'espresso lab',
                    # Fast food
                    'mcdonalds', 'burger king', 'wendys', 'kfc', 'popeyes', 'dominos', 'pizza hut',
                    'little caesars', 'papa johns', 'sbarro', 'arbys', 'taco bell', 'subway',
                    # Türk zincirleri - kafe
                    'mado', 'the house cafe', 'house cafe', 'big chefs', 'bigchefs', 'midpoint',
                    'baylan', 'divan', 'kahve dunyasi', 'kahve dünyası', 'nero', 'costa coffee',
                    # Türk zincirleri - fast food/restoran
                    'simit sarayi', 'simit sarayı', 'tavuk dunyasi', 'tavuk dünyası', 'usta donerci',
                    'komagene', 'baydoner', 'bay döner', 'burger lab', 'zuma', 'etiler', 'nusr-et',
                    # Pastane/tatlıcı zincirleri
                    'dunkin', 'krispy kreme', 'cinnabon', 'hafiz mustafa', 'hafız mustafa',
                    'incir', 'saray muhallebicisi', 'pelit', 'faruk gulluoglu', 'faruk güllüoğlu',
                    # Diğer zincirler
                    'wok to walk', 'wagamama', 'nandos', 'tgi fridays', 'chilis', 'applebees',
                    'hard rock cafe', 'planet hollywood', 'rainforest cafe', 'cheesecake factory',
                    'petra roasting', 'walter\'s coffee'
                ]

                is_chain = any(chain in place_name_lower for chain in chain_store_blacklist)

                if is_chain:
                    print(f"❌ ZİNCİR MEKAN REJECT - {place_name}: romantik kategori için uygunsuz", file=sys.stderr, flush=True)
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
            is_open_now = opening_hours.get('openNow', None)  # Şu an açık mı?

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
                'weeklyHours': hours_list,  # Tüm haftalık saatler
                'isOpenNow': is_open_now  # Şu an açık mı?
            })

        # ===== PHASE 2: TEK BİR BATCH GEMİNİ ÇAĞRISI =====
        if filtered_places:
            # Kullanıcı tercihlerini hazırla - kategori bazlı
            user_preferences = []
            category_name = category.get('name', '')

            # İlgisiz filtreleri atla: Spor, Etkinlik ve Deneyim kategorileri
            skip_venue_filters = category_name in [
                'Spor', 'Konserler', 'Konser', 'Sahne Sanatları', 'Tiyatro', 'Yerel Festivaller',
                'Beach Club', 'Plaj', 'Hafta Sonu Gezintisi', 'Hafta Sonu Kaçamağı', 'Piknik',
                'Müze', 'Galeri', 'Adrenalin'
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

            # Tüm mekanları tek bir prompt'ta gönder - YORUMLARLA BİRLİKTE
            # Pratik bilgi içeren yorumları öncelikli seç
            practical_keywords = ['otopark', 'park', 'vale', 'valet', 'rezervasyon', 'bekle', 'sıra', 'kuyruk',
                                  'kalabalık', 'sakin', 'sessiz', 'gürültü', 'çocuk', 'bebek', 'aile',
                                  'vejetaryen', 'vegan', 'alkol', 'rakı', 'şarap', 'bira', 'servis',
                                  'hızlı', 'yavaş', 'pahalı', 'ucuz', 'fiyat', 'hesap', 'bahçe', 'teras', 'dış mekan']

            places_list_items = []
            for i, p in enumerate(filtered_places[:10]):
                reviews_text = ""
                if p.get('google_reviews'):
                    all_reviews = p['google_reviews']

                    # Pratik bilgi içeren yorumları bul
                    practical_reviews = []
                    other_reviews = []
                    for r in all_reviews:
                        text = r.get('text', '').lower()
                        if any(kw in text for kw in practical_keywords):
                            practical_reviews.append(r)
                        else:
                            other_reviews.append(r)

                    # Pratik bilgi içerenlerden 3 + diğerlerinden en güncel 2 (toplam max 5)
                    selected_reviews = practical_reviews[:3] + other_reviews[:2]
                    top_reviews = [r.get('text', '')[:350] for r in selected_reviews if r.get('text')]
                    if top_reviews:
                        reviews_text = f" | Yorumlar: {' /// '.join(top_reviews)}"

                places_list_items.append(
                    f"{i+1}. {p['name']} | Tip: {', '.join(p['types'][:2])} | Rating: {p.get('rating', 'N/A')}{reviews_text}"
                )
            places_list = "\n".join(places_list_items)

            # Kategori özel talimatları
            category_instruction = ""

            # Balıkçı kategorisi için özel talimat
            if category['name'] == 'Balıkçı' and 'ALKOL: Alcoholic' in preferences_text:
                category_instruction = """
ÖNEMLİ UYARI - BALIKÇI KATEGORİSİ ALKOL FİLTRESİ:
Kullanıcı ALKOLLÜ balık restoranı istiyor. Aşağıdaki mekanları DİKKATLİCE değerlendir:
- Sadece gerçekten alkol servisi yapan, lisanslı balık restoranlarını dahil et
- Sade balık lokantaları, balık evi, balıkçı dükkanı gibi alkol servisi OLMAYAN yerleri REDDET (isRelevant: false)
- Rakı/şarap ile balık yenebilecek kaliteli restoranları tercih et
- "Vedat'ın Balık Evi", "Çarşı Balık", "Girne Balık Evi" gibi sade balık lokantaları genellikle ALKOLSÜZ'dür, dikkat et!
"""
            # Meyhane kategorisi için özel talimat - place_types tabanlı filtreleme sonrası AI değerlendirmesi
            elif category['name'] == 'Meyhane':
                category_instruction = """
ÖNEMLİ UYARI - MEYHANE KATEGORİSİ DEĞERLENDİRMESİ:
Bu kategori için meyhane karakteri taşıyan mekanları değerlendir. DİKKATLİCE incele:
- İsminde "meyhane" geçmese bile meyhane karakteri taşıyan barlar ve restoranlar (rakı/meze servisi, canlı fasıl, geleneksel atmosfer) KABUL ET (isRelevant: true)
- Yorumlarda "rakı", "meze", "fasıl", "canlı müzik", "saz" gibi ifadeler meyhane karakterini gösterir
- Geleneksel Türk içki kültürünü yansıtan mekanları KABUL ET
- Sadece bar/pub konseptinde olup meyhane atmosferi olmayan yerleri REDDET (isRelevant: false)
- Fast food, cafe, tatlıcı gibi alakasız mekanları REDDET (isRelevant: false)
- "Leke", "Balıkçı", "Fasıl", "Meyhane" gibi kelimeler genellikle meyhane karakteri taşır
"""

            batch_prompt = f"""Kategori: {category['name']}
Kullanıcı Tercihleri: {preferences_text}
{category_instruction}

Mekanlar ve Yorumları:
{places_list}

Her mekan için analiz yap ve JSON döndür:
{{
  "name": "Mekan Adı",
  "isRelevant": true/false,
  "description": "2 cümle Türkçe - mekanın öne çıkan özelliği",
  "vibeTags": ["#Tag1", "#Tag2", "#Tag3"],
  "instagramUrl": "https://instagram.com/kullanici_adi" | null,
  "contextScore": {{
    "first_date": 0-100,
    "business_meal": 0-100,
    "casual_hangout": 0-100,
    "fine_dining": 0-100,
    "romantic_dinner": 0-100,
    "friends_hangout": 0-100,
    "family_meal": 0-100,
    "special_occasion": 0-100,
    "breakfast_brunch": 0-100,
    "after_work": 0-100
  }},
  "practicalInfo": {{
    "reservationNeeded": "Tavsiye Edilir" | "Şart" | "Gerekli Değil" | null,
    "crowdLevel": "Sakin" | "Orta" | "Kalabalık" | null,
    "waitTime": "Bekleme yok" | "10-15 dk" | "20-30 dk" | null,
    "parking": "Kolay" | "Zor" | "Otopark var" | "Yok" | null,
    "hasValet": true | false | null,
    "outdoorSeating": true | false | null,
    "kidFriendly": true | false | null,
    "vegetarianOptions": true | false | null,
    "alcoholServed": true | false | null,
    "serviceSpeed": "Hızlı" | "Normal" | "Yavaş" | null,
    "priceFeeling": "Fiyatına Değer" | "Biraz Pahalı" | "Uygun" | null,
    "mustTry": "Yorumlarda öne çıkan yemek/içecek" | null,
    "headsUp": "Bilmeniz gereken önemli uyarı" | null
  }},
  "atmosphereSummary": {{
    "noiseLevel": "Sessiz" | "Sohbet Dostu" | "Canlı" | "Gürültülü",
    "lighting": "Loş" | "Yumuşak" | "Aydınlık",
    "privacy": "Özel" | "Yarı Özel" | "Açık Alan",
    "energy": "Sakin" | "Dengeli" | "Enerjik",
    "idealFor": ["romantik akşam", "ilk buluşma", "arkadaş buluşması"],
    "notIdealFor": ["aile yemeği"],
    "oneLiner": "Tek cümle Türkçe atmosfer özeti"
  }}
}}

Context Skorlama Kuralları:
- first_date: Gürültü düşük, mahremiyet yüksek, görsel olarak etkileyici mekanlar.
- business_meal: Sessiz, hızlı servis, profesyonel atmosfer.
- casual_hangout: Rahat, samimi, arkadaş ortamı.
- fine_dining: Sunum kalitesi, servis, atmosfer, craft/artisan yaklaşımı. El yapımı lezzetler, butik mekan, şef konsepti = yüksek skor.
- romantic_dinner: Loş ışık, mahremiyet, özel atmosfer.
- friends_hangout: Enerjik, sosyal, rahat.
- family_meal: Çocuk dostu, geniş alan, rahat menü.
- special_occasion: Kutlama için uygun, özel deneyim sunan.
- breakfast_brunch: Kahvaltı/brunch için uygunluk.
- after_work: İş çıkışı için uygun, rahatlatıcı.

practicalInfo Kuralları (YORUMLARDAN ÇIKAR):
- reservationNeeded: "Rezervasyon şart", "çok kalabalık", "yer bulmak zor" → "Şart". "Rezervasyon tavsiye" → "Tavsiye Edilir"
- crowdLevel: "Sakin", "sessiz", "rahat" → "Sakin". "Kalabalık", "gürültülü", "dolu" → "Kalabalık"
- waitTime: "Bekledik", "sıra", "kuyruk" → süreyi tahmin et. Hiç bahsedilmemişse null
- parking: "Otopark", "park yeri" → "Otopark var". "Park zor", "park yok" → "Zor". "Park kolay" → "Kolay". Hiç bahsedilmemişse null
- hasValet: "Vale", "valet" → true. Yoksa null
- outdoorSeating: "Bahçe", "dış mekan", "teras" → true
- kidFriendly: "Çocuklu", "aile", "çocuk menüsü" → true. "Bar", "gece kulübü" → false
- vegetarianOptions: "Vejetaryen", "vegan", "sebze" → true
- alcoholServed: "Rakı", "şarap", "bira", "kokteyl" → true
- serviceSpeed: "Hızlı", "geç geldi", "bekledik" → ilgili değeri seç
- priceFeeling: "Pahalı", "ucuz", "fiyatına değer" → seç
- mustTry: Yorumlarda en çok övülen yemek/içecek (varsa)
- headsUp: Önemli uyarılar (nakit, kredi kartı, köpek yasak, vb.)

atmosphereSummary Kuralları:
- noiseLevel: "Sessiz" (fısıltıyla konuşulur), "Sohbet Dostu" (rahat sohbet), "Canlı" (biraz ses), "Gürültülü" (zor duyulur)
- lighting: "Loş" (mum ışığı, romantik), "Yumuşak" (orta aydınlık), "Aydınlık" (net görüş)
- privacy: "Özel" (köşe masalar, separeler), "Yarı Özel" (normal düzen), "Açık Alan" (yakın masalar)
- energy: "Sakin" (dinlendirici), "Dengeli" (orta tempo), "Enerjik" (hareketli)
- idealFor: Max 3 seçenek - "romantik akşam", "ilk buluşma", "iş yemeği", "arkadaş buluşması", "aile yemeği", "sessiz sohbet", "kutlama", "solo yemek"
- notIdealFor: Max 2 seçenek - yukarıdaki listeden
- oneLiner: Tek cümle Türkçe - atmosfer + kime uygun özeti. Örnek: "Loş ışıklı, samimi köşeleriyle romantik akşam yemekleri için ideal"

Önemli:
- Bir mekan birden fazla context'te yüksek skor alabilir
- isRelevant=false olanları JSON'a DAHİL ETME
- Skor 50'nin altındaysa o context için uygun değil demektir
- Yorumları dikkate al (atmosfer, kalabalık, servis hakkında ipuçları içerir)
- vibeTags Türkçe ve # ile başlamalı
- practicalInfo bilgileri YALNIZCA yorumlardan çıkarılmalı, yoksa null yaz
- instagramUrl: Mekanın resmi Instagram hesabını bul. Türkiye'deki mekanların Instagram'ı genellikle mekan_ismi, mekanadi, mekanismişehir formatındadır. Örnek: "Atakent Meyhanesi" → "https://instagram.com/atakent_meyhanesi". Bilinen popüler mekanların Instagram'ını ver. Emin olmadığın veya çok küçük/yerel mekanlar için null yaz.

SADECE JSON ARRAY döndür, başka açıklama yazma."""

            try:
                model = get_genai_model()
                if model:
                    response = model.generate_content(batch_prompt)
                    response_text = response.text.strip()

                    # Güvenli JSON parse
                    import re
                    # Markdown code block temizle
                    response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                    response_text = response_text.strip()

                    try:
                        ai_results = json.loads(response_text)
                    except json.JSONDecodeError:
                        # Array bulmaya çalış
                        match = re.search(r'\[.*\]', response_text, re.DOTALL)
                        if match:
                            ai_results = json.loads(match.group())
                        else:
                            print(f"⚠️ JSON parse edilemedi, fallback kullanılıyor", file=sys.stderr, flush=True)
                            ai_results = []

                    # AI sonuçlarını mekanlarla eşleştir
                    ai_by_name = {r.get('name', '').lower(): r for r in ai_results}

                    for place in filtered_places[:10]:
                        ai_data = ai_by_name.get(place['name'].lower(), {})

                        # Uygun değilse skip
                        if ai_data and not ai_data.get('isRelevant', True):
                            continue

                        # contextScore'dan ilgili kategorinin skorunu al
                        context_scores = ai_data.get('contextScore', {})
                        context_key = CATEGORY_TO_CONTEXT.get(category['name'], 'friends_hangout')
                        category_match_score = context_scores.get(context_key, 75)

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
                            'matchScore': category_match_score,
                            'contextScore': context_scores,
                            'bestTimeSlots': ai_data.get('bestTimeSlots', []),
                            'googleMapsUrl': place['google_maps_url'],
                            'googleReviews': place.get('google_reviews', []),
                            'website': place.get('website', ''),
                            'instagramUrl': discover_instagram_url(
                                venue_name=place['name'],
                                city=city,
                                website=place.get('website'),
                                existing_instagram=ai_data.get('instagramUrl')
                            ) or '',
                            'phoneNumber': place.get('phone_number', ''),
                            'hours': place.get('hours', ''),
                            'weeklyHours': place.get('weeklyHours', []),
                            'isOpenNow': place.get('isOpenNow', None),
                            'isMichelinStarred': is_michelin_restaurant(place['name']) is not None,
                            'practicalInfo': ai_data.get('practicalInfo', {}),
                            'atmosphereSummary': ai_data.get('atmosphereSummary', {
                                'noiseLevel': 'Sohbet Dostu',
                                'lighting': 'Yumuşak',
                                'privacy': 'Yarı Özel',
                                'energy': 'Dengeli',
                                'idealFor': [],
                                'notIdealFor': [],
                                'oneLiner': ''
                            })
                        }

                        # contextScore'dan bestFor oluştur (70+ skorlu context'ler)
                        best_for = []
                        context_to_label = {
                            'first_date': 'İlk Buluşma',
                            'romantic_dinner': 'Romantik Akşam',
                            'business_meal': 'İş Yemeği',
                            'friends_hangout': 'Arkadaşlarla',
                            'family_meal': 'Aile',
                            'special_occasion': 'Özel Gün',
                            'fine_dining': 'Fine Dining',
                            'breakfast_brunch': 'Kahvaltı',
                            'after_work': 'İş Çıkışı'
                        }
                        for ctx, score in context_scores.items():
                            if score >= 70 and ctx in context_to_label:
                                best_for.append(context_to_label[ctx])
                        venue['bestFor'] = best_for[:4]  # Max 4 tane

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
                        'instagramUrl': discover_instagram_url(
                            venue_name=place['name'],
                            city=city,
                            website=place.get('website'),
                            existing_instagram=None
                        ) or '',
                        'phoneNumber': place.get('phone_number', ''),
                        'hours': place.get('hours', ''),
                        'weeklyHours': place.get('weeklyHours', []),
                        'isOpenNow': place.get('isOpenNow', None),
                        'isMichelinStarred': is_michelin_restaurant(place['name']) is not None,
                        'practicalInfo': {},
                        'atmosphereSummary': {
                            'noiseLevel': 'Sohbet Dostu',
                            'lighting': 'Yumuşak',
                            'privacy': 'Yarı Özel',
                            'energy': 'Dengeli',
                            'idealFor': [],
                            'notIdealFor': [],
                            'oneLiner': ''
                        }
                    }
                    venues.append(venue)

        # Match score'a göre sırala
        venues.sort(key=lambda x: x['matchScore'], reverse=True)

        print(f"DEBUG - API'den gelen venues: {len(venues)}", file=sys.stderr, flush=True)

        # ===== API VENUE'LARINI CACHE'E KAYDET =====
        if venues:
            neighborhoods = location.get('neighborhoods', [])
            selected_neighborhood = neighborhoods[0] if neighborhoods else None
            save_venues_to_cache(
                venues=venues,
                category_name=category['name'],
                city=city,
                district=selected_district,
                neighborhood=selected_neighborhood
            )

        # ===== HYBRID: CACHE + API VENUE'LARINI BİRLEŞTİR =====
        # Load More durumunda SADECE API'den gelen yeni mekanları döndür
        # Normal durumda Cache + API birleştir
        combined_venues = []

        if is_load_more_request:
            # LOAD MORE: Sadece API'den gelen yeni mekanları döndür
            # excludeIds zaten cache + mevcut mekanları içeriyor, API sadece yenileri getirir
            for av in venues:
                if len(combined_venues) < 10:
                    combined_venues.append(av)
            print(f"🔄 LOAD MORE RESULT - API'den {len(combined_venues)} yeni mekan döndürülüyor", file=sys.stderr, flush=True)
        else:
            # NORMAL: Önce cache'ten gelenleri ekle
            for cv in cached_venues:
                if len(combined_venues) < 10:
                    combined_venues.append(cv)

            # Sonra API'den gelenleri ekle (tekrar olmaması için ID kontrolü yap)
            existing_ids = {v.get('id') for v in combined_venues}
            for av in venues:
                if len(combined_venues) < 10 and av.get('id') not in existing_ids:
                    combined_venues.append(av)
                    existing_ids.add(av.get('id'))

            print(f"🔀 HYBRID RESULT - Cache: {len(cached_venues)}, API: {len(venues)}, Combined: {len(combined_venues)}", file=sys.stderr, flush=True)

        # Arama geçmişine kaydet
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                user=request.user,
                query=search_query,
                intent=category['name'],
                location=search_location,
                results_count=len(combined_venues)
            )

        return Response(combined_venues, status=status.HTTP_200_OK)

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

