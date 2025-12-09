# Maksat Backend API

Django REST Framework backend for Maksat - Intent-based venue discovery platform.

## Features

- 🔐 User authentication (register, login, logout)
- 📍 Venue search with Google Places API
- 🎯 AI-powered vibe analysis with Gemini
- ⭐ Favorite venues management
- 📜 Search history tracking
- 👤 User profile management

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Kullanıcı kaydı
- `POST /api/auth/login/` - Giriş yap
- `POST /api/auth/logout/` - Çıkış yap

### Venues
- `POST /api/venues/search/` - Mekan ara

### Favorites
- `GET /api/favorites/` - Favorileri listele
- `POST /api/favorites/` - Favori ekle
- `DELETE /api/favorites/{id}/` - Favori sil

### Search History
- `GET /api/search-history/` - Arama geçmişi

### Profile
- `GET /api/profile/me/` - Profil bilgilerini getir
- `PATCH /api/profile/me/` - Profil güncelle

## Environment Variables

```env
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=.onrender.com
GOOGLE_MAPS_API_KEY=your-google-maps-key
GEMINI_API_KEY=your-gemini-key
FRONTEND_URL=https://your-frontend-url.com
```

## Deployment to Render

1. GitHub'a push edin
2. Render.com'da yeni Web Service oluşturun
3. Environment Variables'ları ekleyin
4. Build Command: `./build.sh`
5. Start Command: `gunicorn maksat_backend.wsgi:application`

## Local Development

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# Dependencies kur
pip install -r requirements.txt

# .env dosyası oluştur
cp .env.example .env
# .env dosyasını düzenle

# Database migrate
python manage.py migrate

# Superuser oluştur
python manage.py createsuperuser

# Server başlat
python manage.py runserver
```

## Tech Stack

- Django 4.2
- Django REST Framework
- Google Maps API
- Google Gemini AI
- SQLite (development) / PostgreSQL (production)
