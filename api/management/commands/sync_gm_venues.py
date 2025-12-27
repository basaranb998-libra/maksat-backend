"""
Gault & Millau restoranlarını Google Places + Gemini ile senkronize et.

Kullanım:
    python manage.py sync_gm_venues          # Tüm restoranları sync et
    python manage.py sync_gm_venues --force  # is_synced olanları da yeniden sync et
    python manage.py sync_gm_venues --dry-run # Sadece ne yapılacağını göster
"""

import json
import time
import random
from typing import Optional
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import googlemaps
import google.generativeai as genai

from api.models import GaultMillauVenue
from api.gault_millau_data import GAULT_MILLAU_RESTAURANTS_LIST


class Command(BaseCommand):
    help = 'Gault & Millau restoranlarını Google Places ve Gemini ile senkronize et'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Daha önce sync edilmiş restoranları da yeniden sync et',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece ne yapılacağını göster, veritabanını değiştirme',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maksimum sync edilecek restoran sayısı (0 = sınırsız)',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(self.style.NOTICE(
            f"🍽️ Gault & Millau Sync başlıyor... "
            f"(force={force}, dry_run={dry_run}, limit={limit})"
        ))

        # API clients
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY) if settings.GOOGLE_MAPS_API_KEY else None
        if not gmaps:
            self.stdout.write(self.style.ERROR("❌ GOOGLE_MAPS_API_KEY bulunamadı!"))
            return

        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.stdout.write(self.style.ERROR("❌ GEMINI_API_KEY bulunamadı!"))
            return

        synced_count = 0
        skipped_count = 0
        error_count = 0

        for i, restaurant in enumerate(GAULT_MILLAU_RESTAURANTS_LIST):
            if limit > 0 and synced_count >= limit:
                self.stdout.write(self.style.WARNING(f"⚠️ Limit'e ulaşıldı: {limit}"))
                break

            name = restaurant['name']
            city = restaurant['city']
            toques = restaurant['toques']

            # Mevcut kayıt var mı kontrol et
            existing = GaultMillauVenue.objects.filter(name=name, city=city).first()

            if existing and existing.is_synced and not force:
                self.stdout.write(f"⏭️ Atlanıyor (zaten sync): {name}")
                skipped_count += 1
                continue

            self.stdout.write(f"\n🔄 [{i+1}/{len(GAULT_MILLAU_RESTAURANTS_LIST)}] {name} ({toques} Toque)")

            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"  [DRY-RUN] Sync edilecek: {name}"))
                synced_count += 1
                continue

            try:
                # 1. Google Places'ta ara
                place_data = self._search_google_places(gmaps, name, city)
                if not place_data:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ Google Places'ta bulunamadı: {name}"))
                    error_count += 1
                    continue

                # 2. Place Details al
                details = self._get_place_details(gmaps, place_data['place_id'])
                if not details:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ Place Details alınamadı: {name}"))
                    error_count += 1
                    continue

                # 3. Gemini ile zenginleştir
                venue_data = self._enrich_with_gemini(model, name, city, details, restaurant)
                if not venue_data:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ Gemini zenginleştirmesi başarısız: {name}"))
                    error_count += 1
                    continue

                # 4. Veritabanına kaydet
                self._save_to_database(restaurant, details, venue_data)
                synced_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Sync başarılı: {name}"))

                # Rate limiting - API quotalarını aşmamak için
                time.sleep(1.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Hata: {e}"))
                error_count += 1
                continue

        # Özet
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"✅ Sync tamamlandı: {synced_count} restoran"))
        self.stdout.write(f"⏭️ Atlanan: {skipped_count}")
        self.stdout.write(self.style.ERROR(f"❌ Hata: {error_count}") if error_count > 0 else f"❌ Hata: {error_count}")

    def _search_google_places(self, gmaps, name: str, city: str) -> Optional[dict]:
        """Google Places Text Search ile restoran ara."""
        try:
            query = f"{name} restaurant {city}"
            results = gmaps.places(query=query, language='tr')

            if results.get('results'):
                # İlk sonucu al
                return results['results'][0]
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Google Places arama hatası: {e}"))
            return None

    def _get_place_details(self, gmaps, place_id: str) -> Optional[dict]:
        """Google Places Details API ile detayları al."""
        try:
            result = gmaps.place(
                place_id=place_id,
                fields=[
                    'name', 'formatted_address', 'geometry', 'rating', 'user_ratings_total',
                    'opening_hours', 'formatted_phone_number', 'website', 'photo',
                    'price_level', 'reviews', 'type', 'url', 'place_id'
                ],
                language='tr'
            )
            return result.get('result')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Place Details hatası: {e}"))
            return None

    def _enrich_with_gemini(self, model, name: str, city: str, details: dict, gm_info: dict) -> Optional[dict]:
        """Gemini ile venue verisini zenginleştir."""
        try:
            # Yorumları al
            reviews = details.get('reviews', [])
            reviews_text = "\n".join([f"- {r.get('text', '')[:200]}" for r in reviews[:5]])

            prompt = f"""
Sen bir restoran analiz uzmanısın. Aşağıdaki Gault & Millau ödüllü restoran için detaylı venue verisi oluştur.

RESTORAN: {name}
ŞEHİR: {city}
GAULT MILLAU: {gm_info['toques']} Toque {f"- {gm_info.get('award')}" if gm_info.get('award') else ""}
ŞEF: {gm_info.get('chef') or 'Bilinmiyor'}

GOOGLE YORUMLARI:
{reviews_text if reviews_text else 'Yorum bulunamadı'}

GOOGLE RATING: {details.get('rating', 'N/A')}
FİYAT SEVİYESİ: {"$" * (details.get('price_level', 3) or 3)}

Aşağıdaki JSON formatında yanıt ver (sadece JSON, başka açıklama yok):
{{
  "description": "2-3 cümlelik etkileyici açıklama (Türkçe)",
  "vibeTags": ["3-5 hashtag array"],
  "noiseLevel": 40-70 arası sayı,
  "matchScore": 85-95 arası sayı,
  "metrics": {{
    "noise": 40-70,
    "light": 50-80,
    "privacy": 60-90,
    "service": 80-95,
    "energy": 50-80
  }},
  "priceRange": "$$$" veya "$$$$",
  "practicalInfo": {{
    "reservationNeeded": "Şart" veya "Tavsiye Edilir",
    "crowdLevel": "Orta" veya "Kalabalık",
    "waitTime": "Rezervasyonla yok",
    "parking": "Vale var" veya "Zor",
    "hasValet": true veya false,
    "outdoorSeating": true veya false,
    "kidFriendly": true veya false,
    "vegetarianOptions": true veya false,
    "alcoholServed": true veya false,
    "serviceSpeed": "Normal" veya "Yavaş",
    "priceFeeling": "Fiyatına Değer" veya "Biraz Pahalı",
    "mustTry": "Öne çıkan yemek",
    "headsUp": "Önemli not varsa"
  }},
  "atmosphereSummary": {{
    "noiseLevel": "Sohbet Dostu",
    "lighting": "Loş" veya "Yumuşak",
    "privacy": "Yarı Özel",
    "energy": "Dengeli",
    "idealFor": ["romantik akşam", "iş yemeği"],
    "notIdealFor": ["çocuklu aileler"],
    "oneLiner": "Tek cümle atmosfer özeti"
  }}
}}
"""
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON parse
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()

            return json.loads(response_text)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Gemini hatası: {e}"))
            return None

    def _save_to_database(self, gm_info: dict, details: dict, venue_data: dict):
        """Veritabanına kaydet veya güncelle."""
        name = gm_info['name']
        city = gm_info['city']
        place_id = details.get('place_id')

        # Photo URL oluştur
        photo_url = None
        photos = details.get('photos') or details.get('photo')
        if photos and len(photos) > 0:
            photo_ref = photos[0].get('photo_reference')
            if photo_ref:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={settings.GOOGLE_MAPS_API_KEY}"

        # Çalışma saatleri
        hours = None
        weekly_hours = None
        is_open_now = None
        if details.get('opening_hours'):
            weekly_hours = details['opening_hours'].get('weekday_text', [])
            is_open_now = details['opening_hours'].get('open_now')
            # Bugünün saatini al
            if weekly_hours:
                from datetime import datetime
                day_index = datetime.now().weekday()
                if day_index < len(weekly_hours):
                    hours = weekly_hours[day_index]

        # Google Reviews
        google_reviews = []
        for review in details.get('reviews', [])[:10]:
            google_reviews.append({
                'authorName': review.get('author_name', 'Anonim'),
                'rating': review.get('rating', 0),
                'text': review.get('text', ''),
                'relativeTime': review.get('relative_time_description', ''),
                'profilePhotoUrl': review.get('profile_photo_url')
            })

        # Full venue data oluştur
        full_venue_data = {
            'id': place_id,
            'name': name,
            'description': venue_data.get('description', ''),
            'imageUrl': photo_url,
            'category': 'Fine Dining',
            'vibeTags': venue_data.get('vibeTags', []),
            'noiseLevel': venue_data.get('noiseLevel', 50),
            'matchScore': venue_data.get('matchScore', 90),
            'metrics': venue_data.get('metrics', {}),
            'address': details.get('formatted_address', ''),
            'priceRange': venue_data.get('priceRange', '$$$'),
            'googleMapsUrl': details.get('url'),
            'instagramUrl': f"https://instagram.com/{gm_info.get('instagram')}" if gm_info.get('instagram') else None,
            'website': details.get('website'),
            'phoneNumber': details.get('formatted_phone_number'),
            'hours': hours,
            'weeklyHours': weekly_hours,
            'isOpenNow': is_open_now,
            'googleRating': details.get('rating'),
            'googleReviewCount': details.get('user_ratings_total'),
            'googleReviews': google_reviews,
            'gaultMillauToques': gm_info['toques'],
            'gaultMillauAward': gm_info.get('award'),
            'practicalInfo': venue_data.get('practicalInfo', {}),
            'atmosphereSummary': venue_data.get('atmosphereSummary', {}),
        }

        # Veritabanına kaydet
        obj, created = GaultMillauVenue.objects.update_or_create(
            name=name,
            city=city,
            defaults={
                'place_id': place_id,
                'toques': gm_info['toques'],
                'award': gm_info.get('award'),
                'chef': gm_info.get('chef'),
                'categories': gm_info.get('categories', []),
                'venue_data': full_venue_data,
                'instagram': gm_info.get('instagram'),
                'website': details.get('website'),
                'is_active': True,
                'is_synced': True,
                'last_synced': timezone.now(),
            }
        )

        action = "Oluşturuldu" if created else "Güncellendi"
        self.stdout.write(f"    💾 {action}: {name}")
