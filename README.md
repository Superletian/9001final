# Workout Planner

## What it does
Generate a 7-day workout + meal plan customized by goal/level; compute daily intensity; avoid back-to-back heavy days; log progress; export PDF (falls back to TXT); optional chart.

## How to run
- Python 3.x
- Run: `python main.py`
- No special libraries required. If `matplotlib`/`reportlab` are missing, the program degrades gracefully.

## Advanced topics implemented
- Decorator (`@timed`) • Custom Exception (`ValidationError`)
- JSON persistence • Robust input (aliases, case-insensitive)
- Self-healing `workouts.json` • Optional-deps fallback

## Files generated
- `plan_YYYYMMDD_HHMMSS.txt`
- `logs/progress.jsonl`
- `intensity_chart.png` (if matplotlib)
- `workout_plan.pdf` or `workout_plan_summary.txt`
