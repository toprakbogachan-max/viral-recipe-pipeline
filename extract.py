"""
Tarif çıkarma modülü:
1. youtube-transcript-api ile otomatik altyazıyı çeker (yoksa açıklamayla devam eder)
2. Claude API'ye transkript + başlık + açıklamayı verip yapılandırılmış JSON tarif alır
   (malzemeler, adımlar, süre + bonus: TikTok başlığı ve hashtag'ler)
"""
import json

import anthropic

import config

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    _HAS_TRANSCRIPT_API = True
except ImportError:
    _HAS_TRANSCRIPT_API = False

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = """Aşağıda viral bir yemek tarifi videosunun bilgileri var. \
Bu bilgilerden yapılandırılmış bir tarif çıkar.

VIDEO BAŞLIĞI: {title}

VIDEO AÇIKLAMASI:
{description}

TRANSKRİPT (otomatik altyazı, hatalı olabilir):
{transcript}

SADECE aşağıdaki şemada geçerli bir JSON döndür, başka hiçbir şey yazma \
(markdown kod bloğu da kullanma):

{{
  "is_recipe": true/false,
  "dish_name": "yemeğin adı",
  "dish_name_tr": "yemeğin Türkçe adı",
  "cuisine": "mutfak türü",
  "difficulty": "kolay/orta/zor",
  "total_time_minutes": sayı veya null,
  "servings": sayı veya null,
  "ingredients": [{{"item": "malzeme", "amount": "miktar veya null"}}],
  "steps": ["adım 1", "adım 2"],
  "tiktok_title_en": "İngilizce dikkat çekici başlık (max 100 karakter)",
  "tiktok_title_tr": "Türkçe dikkat çekici başlık (max 100 karakter)",
  "hashtags": ["#tag1", "#tag2"],
  "video_script_hook": "videonun ilk 3 saniyesi için hook cümlesi",
  "confidence": "high/medium/low - bilgilerin ne kadar eksiksiz olduğu"
}}

Eğer içerik bir yemek tarifi değilse is_recipe: false döndür ve diğer alanları boş bırak. \
Transkriptte eksik bilgi varsa videodaki bağlamdan makul tahmin yap ama confidence'ı düşür."""


def get_transcript(video_id: str) -> str:
    """Otomatik altyazıyı dener; bulamazsa boş string döner."""
    if not _HAS_TRANSCRIPT_API:
        return ""
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=["en", "tr", "es"])
        return " ".join(snippet.text for snippet in transcript)
    except Exception:
        # Eski API sürümü için geriye dönük uyumluluk
        try:
            data = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en", "tr", "es"]
            )
            return " ".join(seg["text"] for seg in data)
        except Exception:
            return ""


def extract_recipe(video: dict) -> dict | None:
    """Tek video için Claude'dan yapılandırılmış tarif alır."""
    transcript = get_transcript(video["video_id"])
    if not transcript and len(video.get("description", "")) < 50:
        print(f"  ! {video['video_id']}: transkript yok, açıklama çok kısa - atlanıyor")
        return None

    prompt = EXTRACTION_PROMPT.format(
        title=video["title"],
        description=video.get("description", "")[:3000],
        transcript=transcript[:8000] if transcript else "(transkript bulunamadı)",
    )

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Olası kod bloğu sarmalayıcılarını temizle
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        recipe = json.loads(raw)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        print(f"  ! {video['video_id']}: çıkarma hatası: {e}")
        return None

    if not recipe.get("is_recipe"):
        print(f"  - {video['video_id']}: tarif değil, atlandı")
        return None

    recipe["source"] = {
        "video_id": video["video_id"],
        "url": video["url"],
        "channel": video["channel"],
        "views": video["views"],
        "viral_score": video["viral_score"],
        "query_lang": video["query_lang"],
    }
    recipe["has_transcript"] = bool(transcript)
    return recipe
