# viral-recipe-pipeline

Finds viral recipe Shorts on YouTube, scores them by view velocity, and uses the Claude API to turn spoken transcripts into structured recipe data — ingredients, steps, timings and platform-ready titles in two languages.

Turns an unstructured stream of trending cooking videos into a queryable dataset built to feed short-form video production.

## Pipeline

```
YouTube Data API (discovery) ──> viral scoring ──> transcript (auto captions)
        │                                              │
        └──> output/discovered.csv                     ▼
                                              Claude API (recipe extraction)
                                                       │
                                     ┌─────────────────┴─────────────────┐
                                     ▼                                   ▼
                        output/recipes/{id}.json              output/recipes.csv
```

**Discovery** searches recipe Shorts across English, Turkish and Spanish query sets, then ranks results by view velocity rather than raw view count:

```
viral_score = (views / hours_since_publish) * engagement_bonus
```

**Extraction** pulls the automatic transcript for the top-scoring videos and sends it, with title and description, to the Claude API under a strict output schema.

## Output schema

```json
{
  "dish_name_en": "Garlic Butter Chicken",
  "dish_name_tr": "Sarımsaklı Tereyağlı Tavuk",
  "ingredients": [
    { "item": "chicken breast", "amount": "500", "unit": "g" }
  ],
  "steps": ["Season the chicken...", "Sear over high heat..."],
  "difficulty": "easy",
  "total_time_minutes": 25,
  "tiktok_title_en": "...",
  "tiktok_title_tr": "...",
  "hashtags": ["#chicken", "#easyrecipe"],
  "video_script_hook": "This takes 25 minutes and beats takeout."
}
```

The schema is deliberately production-shaped: `steps` maps to on-screen text overlays, `video_script_hook` to the opening three seconds, and `tiktok_title_*` plus `hashtags` to publish metadata.

## Setup

Requires Python 3.10+, a YouTube Data API v3 key and an Anthropic API key.

```bash
git clone https://github.com/toprakbogachan-max/viral-recipe-pipeline.git
cd viral-recipe-pipeline
pip install -r requirements.txt

export YOUTUBE_API_KEY="..."
export ANTHROPIC_API_KEY="..."

python main.py
```

**Getting a YouTube key:** create a project in the Google Cloud Console, enable *YouTube Data API v3*, then create an API key under Credentials. The free daily quota is 10,000 units and each search costs 100, which comfortably covers one or two full runs per day at default settings.

## Configuration

All thresholds live in `config.py`, separate from pipeline logic, so output quality can be tuned iteratively without touching code paths:

| Setting | Purpose |
|---|---|
| `SEARCH_QUERIES` | Query sets per language (en/tr/es) |
| `MIN_VIEWS` | Floor for a video to enter scoring |
| `MIN_VIEWS_PER_HOUR` | Velocity floor — lower this if results are sparse |
| `TOP_N_TO_EXTRACT` | How many videos reach the Claude API (the main cost lever) |
| `PUBLISHED_WITHIN_DAYS` | Recency window |

## Output

```
output/
├── discovered.csv          # every video clearing the thresholds, ranked by viral score
├── recipes.csv             # flattened summary table
└── recipes/
    └── {video_id}.json     # full structured recipe per video
```

## Design notes

**YouTube as the discovery source.** TikTok and Instagram offer no official API for this kind of discovery, so YouTube Shorts is the only reliable legal source. Reddit (r/recipes) is a candidate for a second source.

**Transcript-first extraction.** Working from automatic captions instead of video frames keeps the pipeline fast and cheap. Videos without a usable transcript are skipped rather than guessed at.

**Two-stage separation.** Discovery and extraction are independent modules, so a run can be re-scored or re-extracted without re-querying the API — which matters given the daily quota.

**Cost control by design.** Discovery is cheap and extraction is not, so `TOP_N_TO_EXTRACT` gates exactly how much reaches the LLM.

## Notes on use

Extracted recipes are intended as data and inspiration. Reproducing a source video frame-for-frame is both a copyright and a platform-policy problem; the output is structured so the same dish can be shot or generated from scratch.

## Roadmap

- [ ] Video generation from the JSON schema (AI imagery + TTS, or stock footage)
- [ ] Deduplication of the same dish across creators
- [ ] Reddit as a second discovery source

## Tech

Python · YouTube Data API v3 · Claude API · `youtube-transcript-api`

## License

MIT
