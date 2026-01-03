"""
Stale-While-Revalidate (SWR) Cache Service

Freshness Rules:
- 0-24 saat: FRESH (direkt cache'ten dön)
- 24-96 saat: STALE (cache'ten dön, arka planda refresh)
- 96+ saat: EXPIRED (API'ye git, yeni cache oluştur)
"""

import threading
import hashlib
import sys
from datetime import timedelta
from typing import Callable, List, Dict, Any, Tuple, Set, Optional
from django.utils import timezone
from .gault_millau_data import enrich_venues_with_gault_millau
from .popular_venues_data import enrich_venues_with_instagram


# ===== CONFIGURATION =====
# Dengeli cache stratejisi: Güncel kalma vs API maliyeti
CACHE_FRESH_HOURS = 24      # 0-24 saat: Fresh (direkt cache'ten dön)
CACHE_STALE_HOURS = 96      # 24-96 saat: Stale (cache'ten dön, arka planda refresh)
CACHE_EXPIRED_HOURS = 96    # 96+ saat: Expired (API'ye git)

# In-memory set to track ongoing refresh operations
_refresh_in_progress: Set[str] = set()
_refresh_lock = threading.Lock()


def generate_location_key(category: str, city: str, district: str = None, neighborhood: str = None) -> str:
    """
    Generate a unique cache key for category + location combination.
    Uses MD5 hash for consistent, short keys.
    """
    key_parts = [category.lower(), city.lower()]
    if district:
        key_parts.append(district.lower())
    if neighborhood:
        key_parts.append(neighborhood.lower())

    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()[:16]


def get_cache_age_hours(last_api_call) -> float:
    """Calculate cache age in hours from last_api_call timestamp."""
    if not last_api_call:
        return float('inf')

    age = timezone.now() - last_api_call
    return age.total_seconds() / 3600


def get_cache_freshness(age_hours: float) -> str:
    """
    Determine cache freshness status.
    Returns: 'fresh', 'stale', or 'expired'
    """
    if age_hours < CACHE_FRESH_HOURS:
        return 'fresh'
    elif age_hours < CACHE_STALE_HOURS:
        return 'stale'
    else:
        return 'expired'


def is_refresh_in_progress(cache_key: str) -> bool:
    """Check if a refresh is already in progress for this cache key."""
    with _refresh_lock:
        return cache_key in _refresh_in_progress


def mark_refresh_started(cache_key: str) -> bool:
    """
    Mark refresh as started for this cache key.
    Returns True if successfully marked (no other refresh in progress).
    Returns False if refresh is already in progress.
    """
    with _refresh_lock:
        if cache_key in _refresh_in_progress:
            return False
        _refresh_in_progress.add(cache_key)
        return True


def mark_refresh_completed(cache_key: str):
    """Mark refresh as completed for this cache key."""
    with _refresh_lock:
        _refresh_in_progress.discard(cache_key)


def trigger_background_refresh(
    cache_key: str,
    category_name: str,
    city: str,
    district: str,
    refresh_callback: Callable
):
    """
    Start a background thread to refresh cache.
    Uses a callback function to perform the actual refresh.
    """
    # Check if refresh is already in progress
    if not mark_refresh_started(cache_key):
        print(f"🔄 SWR - Background refresh already in progress for: {cache_key}", file=sys.stderr, flush=True)
        return

    def background_task():
        try:
            print(f"🔄 SWR - Background refresh started for: {cache_key} ({category_name}/{city}/{district or 'ALL'})", file=sys.stderr, flush=True)

            # Execute the refresh callback
            new_venues = refresh_callback(category_name, city, district)

            venue_count = len(new_venues) if new_venues else 0
            print(f"✅ SWR - Background refresh completed for: {cache_key}, {venue_count} venues updated", file=sys.stderr, flush=True)

        except Exception as e:
            print(f"❌ SWR - Background refresh failed for {cache_key}: {e}", file=sys.stderr, flush=True)
        finally:
            mark_refresh_completed(cache_key)

    # Start daemon thread (won't prevent app shutdown)
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()


def get_venues_with_swr(
    category_name: str,
    city: str,
    district: str = None,
    neighborhood: str = None,
    exclude_ids: Set[str] = None,
    limit: int = 5,
    fetch_and_cache_callback: Callable = None,
    refresh_callback: Callable = None
) -> Tuple[List[Dict[str, Any]], Set[str], str]:
    """
    Main SWR function to get venues with stale-while-revalidate strategy.

    Args:
        category_name: Category name (e.g., "Meyhane", "Kahve")
        city: City name
        district: District name (optional)
        neighborhood: Neighborhood name (optional)
        exclude_ids: Set of place_ids to exclude
        limit: Maximum number of venues to return from cache
        fetch_and_cache_callback: Function to fetch fresh data from API
        refresh_callback: Function to call for background refresh

    Returns:
        Tuple of (venues_list, all_cached_place_ids, freshness_status)
    """
    from .models import CachedVenue

    location_key = generate_location_key(category_name, city, district, neighborhood)

    try:
        # Build cache query
        cache_query = CachedVenue.objects.filter(
            category=category_name,
            city__iexact=city
        )

        if district:
            cache_query = cache_query.filter(district__iexact=district)

        if neighborhood:
            cache_query = cache_query.filter(neighborhood__iexact=neighborhood)

        # Get all cached venues for this location
        cached_venues = list(cache_query)

        if not cached_venues:
            # No cache exists - need to fetch from API
            print(f"📭 SWR - No cache for: {location_key} ({category_name}/{city}/{district or 'ALL'})", file=sys.stderr, flush=True)
            return [], set(), 'miss'

        # Get the oldest last_api_call to determine freshness
        oldest_api_call = min(v.last_api_call for v in cached_venues if v.last_api_call)
        age_hours = get_cache_age_hours(oldest_api_call)
        freshness = get_cache_freshness(age_hours)

        # Collect all cached place_ids (for API exclusion)
        all_cached_ids = {v.place_id for v in cached_venues}

        # Filter by exclude_ids - check both place_id AND venue_data['id']
        # Frontend sends venue_data['id'] but we store as place_id
        if exclude_ids:
            def should_exclude(v):
                # Check database place_id
                if v.place_id in exclude_ids:
                    return True
                # Also check venue_data id (what frontend sees)
                venue_id = v.venue_data.get('id', '') if v.venue_data else ''
                if venue_id and venue_id in exclude_ids:
                    return True
                return False

            original_count = len(cached_venues)
            cached_venues = [v for v in cached_venues if not should_exclude(v)]
            filtered_count = original_count - len(cached_venues)
            if filtered_count > 0:
                print(f"🚫 SWR - Excluded {filtered_count} venues from cache (exclude_ids: {len(exclude_ids)})", file=sys.stderr, flush=True)

        # Sort by google_rating (descending) to show best venues first
        cached_venues.sort(key=lambda v: v.google_rating or 0, reverse=True)

        # Get venue data (limited)
        venues_data = [v.venue_data for v in cached_venues[:limit]]

        # Apply Gault & Millau enrichment to cached venues
        venues_data = enrich_venues_with_gault_millau(venues_data)

        # Apply Instagram enrichment to cached venues
        venues_data = enrich_venues_with_instagram(venues_data)

        # Update last_accessed for all venues
        CachedVenue.objects.filter(
            category=category_name,
            city__iexact=city,
            **({"district__iexact": district} if district else {})
        ).update(last_accessed=timezone.now())

        # Log cache status
        print(f"📦 SWR - {freshness.upper()} cache ({age_hours:.1f}h old): {location_key} - {len(venues_data)} venues", file=sys.stderr, flush=True)

        # Handle stale cache - trigger background refresh
        if freshness == 'stale' and refresh_callback:
            trigger_background_refresh(
                cache_key=location_key,
                category_name=category_name,
                city=city,
                district=district,
                refresh_callback=refresh_callback
            )

        # Handle expired cache - caller should fetch fresh data
        if freshness == 'expired':
            print(f"⏰ SWR - Cache expired, needs refresh: {location_key}", file=sys.stderr, flush=True)

        return venues_data, all_cached_ids, freshness

    except Exception as e:
        print(f"❌ SWR ERROR - {category_name}/{city}: {e}", file=sys.stderr, flush=True)
        return [], set(), 'error'


def save_venues_to_cache_swr(
    venues: List[Dict[str, Any]],
    category_name: str,
    city: str,
    district: str = None,
    neighborhood: str = None
) -> int:
    """
    Save venues to cache with SWR metadata.
    Returns number of venues saved.
    """
    from .models import CachedVenue

    if not venues:
        return 0

    location_key = generate_location_key(category_name, city, district, neighborhood)
    now = timezone.now()
    saved_count = 0

    try:
        for venue in venues:
            place_id = venue.get('id', '')

            if not place_id:
                continue

            try:
                CachedVenue.objects.update_or_create(
                    place_id=place_id,
                    defaults={
                        'name': venue.get('name', ''),
                        'category': category_name,
                        'city': city,
                        'district': district or '',
                        'neighborhood': neighborhood or '',
                        'location_key': location_key,
                        'venue_data': venue,
                        'google_rating': venue.get('googleRating'),
                        'google_review_count': venue.get('googleReviewCount'),
                        'last_api_call': now,
                        'last_accessed': now
                    }
                )
                saved_count += 1
            except Exception as e:
                print(f"⚠️ SWR save error for {place_id}: {e}", file=sys.stderr, flush=True)

        print(f"💾 SWR SAVE - {saved_count}/{len(venues)} venues ({location_key})", file=sys.stderr, flush=True)

    except Exception as e:
        print(f"❌ SWR SAVE FAILED - {category_name}/{city}: {e}", file=sys.stderr, flush=True)

    return saved_count


def get_cached_venues_for_hybrid_swr(
    category_name: str,
    city: str,
    district: str = None,
    neighborhood: str = None,
    exclude_ids: Set[str] = None,
    limit: int = 5,
    refresh_callback: Callable = None
) -> Tuple[List[Dict[str, Any]], Set[str], str]:
    """
    Backward-compatible function for hybrid cache system with SWR.
    This replaces the old get_cached_venues_for_hybrid function.

    Returns: (venues_list, all_cached_place_ids, freshness_status)
    """
    return get_venues_with_swr(
        category_name=category_name,
        city=city,
        district=district,
        neighborhood=neighborhood,
        exclude_ids=exclude_ids,
        limit=limit,
        refresh_callback=refresh_callback
    )


# ===== UTILITY FUNCTIONS =====

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    from .models import CachedVenue
    from django.db.models import Count, Min, Max

    now = timezone.now()

    stats = {
        'total_venues': CachedVenue.objects.count(),
        'by_freshness': {
            'fresh': 0,
            'stale': 0,
            'expired': 0
        },
        'by_category': {},
        'refresh_in_progress': list(_refresh_in_progress)
    }

    # Count by freshness
    fresh_cutoff = now - timedelta(hours=CACHE_FRESH_HOURS)
    stale_cutoff = now - timedelta(hours=CACHE_STALE_HOURS)

    stats['by_freshness']['fresh'] = CachedVenue.objects.filter(last_api_call__gte=fresh_cutoff).count()
    stats['by_freshness']['stale'] = CachedVenue.objects.filter(
        last_api_call__lt=fresh_cutoff,
        last_api_call__gte=stale_cutoff
    ).count()
    stats['by_freshness']['expired'] = CachedVenue.objects.filter(last_api_call__lt=stale_cutoff).count()

    # Count by category
    category_counts = CachedVenue.objects.values('category').annotate(count=Count('id'))
    for item in category_counts:
        stats['by_category'][item['category']] = item['count']

    return stats


def clear_expired_cache(older_than_hours: int = 72) -> int:
    """
    Clear cache entries older than specified hours.
    Returns number of deleted entries.
    """
    from .models import CachedVenue

    cutoff = timezone.now() - timedelta(hours=older_than_hours)
    deleted_count, _ = CachedVenue.objects.filter(last_api_call__lt=cutoff).delete()

    print(f"🧹 SWR CLEANUP - Deleted {deleted_count} expired cache entries (>{older_than_hours}h old)", file=sys.stderr, flush=True)

    return deleted_count
