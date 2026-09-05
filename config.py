"""
Viral Recipe Pipeline - Konfigürasyon
API anahtarlarını ortam değişkeni olarak ver:
  export YOUTUBE_API_KEY="..."
  export ANTHROPIC_API_KEY="..."
"""
import os

# --- API Anahtarları ---
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Keşif Ayarları ---
# Dil bazlı arama sorguları (Twitch pipeline'daki çoklu dil mantığıyla aynı)
SEARCH_QUERIES = {
    "en": [
        "easy recipe shorts",
        "viral recipe",
        "quick dinner recipe",
        "one pan recipe",
        "5 minute recipe",
    ],
    "tr": [
        "kolay tarif",
        "pratik yemek tarifi",
        "viral tarif",
        "5 dakikada tarif",
    ],
    "es": [
        "receta facil",
        "receta viral",
        "receta rapida",
    ],
}

# Son kaç gün içinde yayınlanmış videolara bakılsın
PUBLISHED_WITHIN_DAYS = 7

# Maksimum video süresi (saniye) - Shorts formatı
MAX_DURATION_SECONDS = 180

# Sorgu başına çekilecek sonuç sayısı
RESULTS_PER_QUERY = 25

# --- Skorlama Ayarları ---
# viral_score = (views / saat) * (1 + engagement_bonus)
MIN_VIEWS = 10_000            # bu altındakiler elenir
MIN_VIEWS_PER_HOUR = 100      # hız eşiği
TOP_N_TO_EXTRACT = 15         # tarif çıkarılacak en iyi N video

# --- Claude Ayarları ---
CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000

# --- Çıktı ---
OUTPUT_DIR = "output"
RECIPES_DIR = os.path.join(OUTPUT_DIR, "recipes")
CSV_PATH = os.path.join(OUTPUT_DIR, "recipes.csv")
