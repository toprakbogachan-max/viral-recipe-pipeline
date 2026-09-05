"""
Viral Recipe Pipeline - Ana orkestratör

Akış:
  1. discover_all()   -> viral Shorts'ları bul ve skorla
  2. extract_recipe() -> en iyi N video için Claude ile tarif çıkar
  3. Çıktılar:
       output/recipes/{video_id}.json  (tam yapılandırılmış tarif)
       output/recipes.csv              (özet tablo - CapCut/planlama için)
       output/discovered.csv           (skorlanan tüm videolar)

Kullanım:
  export YOUTUBE_API_KEY="..."
  export ANTHROPIC_API_KEY="..."
  python main.py
"""
import csv
import json
import os
import sys

import config
from discover import discover_all
from extract import extract_recipe


def check_keys() -> None:
    missing = []
    if not config.YOUTUBE_API_KEY:
        missing.append("YOUTUBE_API_KEY")
    if not config.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"HATA: Eksik ortam değişkenleri: {', '.join(missing)}")
        sys.exit(1)


def write_discovered_csv(videos: list[dict]) -> None:
    path = os.path.join(config.OUTPUT_DIR, "discovered.csv")
    if not videos:
        return
    fields = [
        "video_id", "url", "title", "channel", "query_lang", "query",
        "published_at", "duration_sec", "views", "likes",
        "views_per_hour", "engagement", "viral_score",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(videos)
    print(f"[çıktı] {path} ({len(videos)} video)")


def write_recipes(recipes: list[dict]) -> None:
    os.makedirs(config.RECIPES_DIR, exist_ok=True)

    rows = []
    for r in recipes:
        vid = r["source"]["video_id"]
        json_path = os.path.join(config.RECIPES_DIR, f"{vid}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)

        rows.append({
            "video_id": vid,
            "source_url": r["source"]["url"],
            "dish_name": r.get("dish_name", ""),
            "dish_name_tr": r.get("dish_name_tr", ""),
            "cuisine": r.get("cuisine", ""),
            "difficulty": r.get("difficulty", ""),
            "total_time_min": r.get("total_time_minutes", ""),
            "ingredient_count": len(r.get("ingredients", [])),
            "step_count": len(r.get("steps", [])),
            "tiktok_title_en": r.get("tiktok_title_en", ""),
            "tiktok_title_tr": r.get("tiktok_title_tr", ""),
            "hashtags": " ".join(r.get("hashtags", [])),
            "hook": r.get("video_script_hook", ""),
            "confidence": r.get("confidence", ""),
            "viral_score": r["source"]["viral_score"],
            "views": r["source"]["views"],
            "lang": r["source"]["query_lang"],
        })

    with open(config.CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[çıktı] {config.CSV_PATH} ({len(rows)} tarif)")


def main() -> None:
    check_keys()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # 1. Keşif
    videos = discover_all()
    if not videos:
        print("Hiç video bulunamadı. Eşikleri (config.py) gevşetmeyi dene.")
        return
    write_discovered_csv(videos)

    # 2. Tarif çıkarma (en iyi N)
    top = videos[: config.TOP_N_TO_EXTRACT]
    print(f"\n[çıkarma] En iyi {len(top)} video işleniyor...")
    recipes = []
    for i, video in enumerate(top, 1):
        print(f"  ({i}/{len(top)}) {video['title'][:60]}")
        recipe = extract_recipe(video)
        if recipe:
            recipes.append(recipe)

    if not recipes:
        print("Hiç tarif çıkarılamadı.")
        return

    # 3. Çıktılar
    write_recipes(recipes)
    print(f"\nBitti: {len(recipes)} tarif hazır. Sıradaki adım: video üretimi (v2).")


if __name__ == "__main__":
    main()
