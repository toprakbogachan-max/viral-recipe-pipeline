"""
Keşif modülü: YouTube Data API ile viral yemek tarifi Shorts'larını bulur ve skorlar.
Skorlama mantığı: view velocity (izlenme/saat) + engagement bonusu.
"""
import re
from datetime import datetime, timedelta, timezone

import requests

import config

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_iso_duration(duration: str) -> int:
    """ISO 8601 süresini (PT1M30S) saniyeye çevirir."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def search_videos(query: str, lang: str) -> list[str]:
    """Tek sorgu için video ID listesi döner."""
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=config.PUBLISHED_WITHIN_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "key": config.YOUTUBE_API_KEY,
        "part": "id",
        "q": query,
        "type": "video",
        "videoDuration": "short",  # < 4 dakika
        "order": "viewCount",
        "publishedAfter": published_after,
        "maxResults": config.RESULTS_PER_QUERY,
        "relevanceLanguage": lang,
    }
    r = requests.get(SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return [item["id"]["videoId"] for item in r.json().get("items", [])]


def fetch_video_details(video_ids: list[str]) -> list[dict]:
    """videos.list ile istatistik + süre + açıklama çeker (50'lik batch)."""
    details = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        params = {
            "key": config.YOUTUBE_API_KEY,
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
        }
        r = requests.get(VIDEOS_URL, params=params, timeout=30)
        r.raise_for_status()
        details.extend(r.json().get("items", []))
    return details


def score_video(item: dict) -> dict | None:
    """Viral skoru hesaplar; eşikleri geçemeyenler için None döner."""
    stats = item.get("statistics", {})
    snippet = item.get("snippet", {})
    duration = _parse_iso_duration(item.get("contentDetails", {}).get("duration", ""))

    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))

    if views < config.MIN_VIEWS or duration > config.MAX_DURATION_SECONDS or duration == 0:
        return None

    published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
    hours = max((datetime.now(timezone.utc) - published).total_seconds() / 3600, 1.0)

    views_per_hour = views / hours
    if views_per_hour < config.MIN_VIEWS_PER_HOUR:
        return None

    engagement = likes / views if views else 0.0
    viral_score = views_per_hour * (1 + engagement * 10)

    return {
        "video_id": item["id"],
        "url": f"https://www.youtube.com/watch?v={item['id']}",
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "description": snippet.get("description", ""),
        "published_at": snippet["publishedAt"],
        "duration_sec": duration,
        "views": views,
        "likes": likes,
        "views_per_hour": round(views_per_hour, 1),
        "engagement": round(engagement, 4),
        "viral_score": round(viral_score, 1),
    }


def discover_all() -> list[dict]:
    """Tüm dillerdeki tüm sorguları çalıştırır, skorlar, tekilleştirir, sıralar."""
    seen: dict[str, dict] = {}

    for lang, queries in config.SEARCH_QUERIES.items():
        for query in queries:
            print(f"[keşif] ({lang}) '{query}' aranıyor...")
            try:
                ids = search_videos(query, lang)
            except requests.HTTPError as e:
                print(f"  ! arama hatası: {e}")
                continue

            new_ids = [vid for vid in ids if vid not in seen]
            if not new_ids:
                continue

            for item in fetch_video_details(new_ids):
                scored = score_video(item)
                if scored:
                    scored["query_lang"] = lang
                    scored["query"] = query
                    seen[scored["video_id"]] = scored

    ranked = sorted(seen.values(), key=lambda v: v["viral_score"], reverse=True)
    print(f"[keşif] toplam {len(ranked)} video eşikleri geçti")
    return ranked
