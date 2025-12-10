# API Endpoint Test Kılavuzu

## `/api/venues/generate` Endpoint'i

### Endpoint Bilgisi
- **URL**: `http://localhost:8000/api/venues/generate/`
- **Method**: `POST`
- **Authentication**: Gerekli değil (AllowAny)

### Request Format

```json
{
  "category": {
    "id": "1",
    "name": "İlk Buluşma"
  },
  "location": {
    "city": "İstanbul",
    "districts": ["Kadıköy"]
  },
  "filters": {
    "groupSize": "Couple",
    "budget": "Orta",
    "vibes": ["#Romantik", "#Sakin"],
    "amenities": ["WiFi", "Outdoor"]
  },
  "tripDuration": 3
}
```

### Response Format

```json
[
  {
    "id": "v1",
    "name": "Mekan Adı",
    "description": "Mekan hakkında açıklama...",
    "imageUrl": "https://...",
    "category": "İlk Buluşma",
    "vibeTags": ["#Romantik", "#Sakin"],
    "address": "Kadıköy, İstanbul",
    "priceRange": "$$",
    "googleRating": 4.5,
    "noiseLevel": 40,
    "matchScore": 85,
    "metrics": {
      "ambiance": 85,
      "accessibility": 90,
      "popularity": 80
    }
  }
]
```

### Özellikler

1. **Google Places API Entegrasyonu**
   - Kategori ve lokasyona göre gerçek mekanları arar
   - Mekan fotoğraflarını Google Places'ten alır
   - Google rating ve adres bilgilerini kullanır

2. **Gemini AI Analizi**
   - Her mekan için AI destekli açıklama üretir
   - Vibe etiketleri oluşturur
   - Gürültü seviyesi ve match score hesaplar
   - Ambiance, accessibility, popularity metrikleri üretir

3. **Filtreleme**
   - Budget filtresine göre mekanları filtreler (Ekonomik/Orta/Lüks)
   - Vibe'lara göre arama sorgusunu zenginleştirir
   - Match score'a göre sonuçları sıralar

### API Key Ayarları

`.env` dosyasına aşağıdaki anahtarları ekleyin:

```env
GOOGLE_MAPS_API_KEY=your-actual-google-maps-api-key
GEMINI_API_KEY=your-actual-gemini-api-key
```

**✅ Google Places API (New) Entegrasyonu Tamamlandı!**

Endpoint şimdi Google'ın yeni Places API'sini kullanıyor ve gerçek mekan verileri döndürüyor.

#### API Özellikleri
- ✅ **Google Places API (New)**: Gerçek mekan verileri, fotoğraflar, rating'ler
- ✅ **Gemini AI**: Mekan açıklamaları ve analiz (fallback ile)
- ✅ **Smart Fallback**: API çalışmazsa otomatik mock data
- ✅ **Budget Filtering**: Ekonomik/Orta/Lüks filtreleme
- ✅ **Match Score**: AI destekli uygunluk skorlama

### Test Komutları

```bash
# Basit test
curl -X POST http://localhost:8000/api/venues/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "category": {"id": "1", "name": "İlk Buluşma"},
    "location": {"city": "İstanbul", "districts": ["Kadıköy"]},
    "filters": {"groupSize": "Couple", "budget": "Orta"}
  }'

# Filtreleri ile test
curl -X POST http://localhost:8000/api/venues/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "category": {"id": "2", "name": "Tatil"},
    "location": {"city": "Antalya", "districts": ["Kaleiçi"]},
    "filters": {
      "groupSize": "Family",
      "budget": "Lüks",
      "vibes": ["#Beach", "#Relaxing"]
    },
    "tripDuration": 7
  }'
```

### Hata Durumları

1. **API Key Eksik**
   ```json
   {
     "error": "Google Maps API key eksik"
   }
   ```
   Status Code: 503

2. **Validation Hatası**
   ```json
   {
     "category": ["This field is required."]
   }
   ```
   Status Code: 400

3. **Genel Hata**
   ```json
   {
     "error": "Mekan önerisi oluşturulurken hata: [hata mesajı]"
   }
   ```
   Status Code: 500

### Notlar

- Endpoint authentication gerektirmez ama kullanıcı login ise arama geçmişine kaydedilir
- İlk 10 en uygun mekanı döndürür
- Gerçek API key'ler olmadan test için fallback data kullanılır
- Tatil kategorisi için `tripDuration` parametresi kullanılabilir
