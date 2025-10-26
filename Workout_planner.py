# -*- coding: utf-8 -*-
"""
Workout Planner - Robust Version (input normalization + self-healing storage)

Fixes:
- Accepts case-insensitive goals/levels and common aliases
- Normalizes and self-heals workouts.json (keys & missing defaults)
- Keeps previous features: optional matplotlib/reportlab with graceful fallback,
  @timed, ValidationError, intensity wave-peak suppression, progress logs.
"""

import os
import json
import copy
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ---- Optional third-party deps (graceful fallback) ----
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

try:
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    )
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_RL = True
except Exception:
    HAS_RL = False


# -----------------------------
# Canonical dictionaries
# -----------------------------
default_workouts: Dict[str, Dict[str, List[str]]] = {
    "Fat Loss": {
        "Beginner": ["Walking 30 min", "Jump Rope 5 min"],
        "Intermediate": ["Running 30 min", "HIIT 15 min"],
        "Advanced": ["Running 60 min", "HIIT 30 min"]
    },
    "Muscle Gain": {
        "Beginner": ["Push-ups 3x10", "Squats 3x12"],
        "Intermediate": ["Bench Press 4x10", "Pull-ups 3x8"],
        "Advanced": ["Deadlift 4x8", "Barbell Squat 4x10"]
    },
    "Health": {
        "Beginner": ["Yoga 20 min", "Stretching 15 min"],
        "Intermediate": ["Core Training 3x15", "Pilates 20 min"],
        "Advanced": ["CrossFit 30 min", "Weight Training 20 min"]
    }
}

meal_plan: Dict[str, List[str]] = {
    "Fat Loss": ["Chicken breast + vegetables", "Oatmeal + milk", "Salad + salmon"],
    "Muscle Gain": ["Steak + rice", "Protein shake + banana", "Eggs + sweet potato"],
    "Health": ["Fruit platter", "Whole grain bread + eggs", "Steamed fish + vegetables"]
}

intensity_map: Dict[str, int] = {
    "Walking 30 min": 10, "Jump Rope 5 min": 25, "Running 30 min": 40, "HIIT 15 min": 70,
    "Running 60 min": 90, "HIIT 30 min": 100, "Push-ups 3x10": 20, "Squats 3x12": 25,
    "Bench Press 4x10": 50, "Pull-ups 3x8": 55, "Deadlift 4x8": 80, "Barbell Squat 4x10": 75,
    "Yoga 20 min": 10, "Stretching 15 min": 5, "Core Training 3x15": 30, "Pilates 20 min": 20,
    "CrossFit 30 min": 95, "Weight Training 20 min": 60
}

# Aliases (lowercased) -> Canonical
GOAL_ALIASES = {
    "fat loss": "Fat Loss", "fatloss": "Fat Loss", "lose fat": "Fat Loss", "fat": "Fat Loss",
    "muscle gain": "Muscle Gain", "musclegain": "Muscle Gain", "gain muscle": "Muscle Gain", "muscle": "Muscle Gain",
    "health": "Health", "healthy": "Health"
}
LEVEL_ALIASES = {
    "beginner": "Beginner", "newbie": "Beginner", "novice": "Beginner",
    "intermediate": "Intermediate", "mid": "Intermediate",
    "advanced": "Advanced", "adv": "Advanced", "expert": "Advanced"
}


# -----------------------------
# Advanced: Decorator & Custom Exception
# -----------------------------
class ValidationError(Exception):
    """Raised when user input is invalid."""
    pass


def timed(func):
    """Simple timing decorator for demo/analysis."""
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*a, **kw):
        t0 = time.time()
        res = func(*a, **kw)
        dt = time.time() - t0
        print(f"[timed] {func.__name__} took {dt:.3f}s")
        return res
    return wrapper


# -----------------------------
# Normalization helpers
# -----------------------------
def canonical_goal(s: str) -> Optional[str]:
    if not s:
        return None
    key = s.strip().lower()
    return GOAL_ALIASES.get(key)


def canonical_level(s: str) -> Optional[str]:
    if not s:
        return None
    key = s.strip().lower()
    return LEVEL_ALIASES.get(key)


def normalize_workouts_dict(workouts: dict) -> dict:
    """
    Normalize keys of a user-provided workouts dict to canonical Goal/Level.
    Unknown keys are kept but moved under their best-effort canonical parent.
    """
    normalized: Dict[str, Dict[str, List[str]]] = {}

    if not isinstance(workouts, dict):
        return copy.deepcopy(default_workouts)

    for g_key, levels in workouts.items():
        g_can = canonical_goal(g_key) or g_key  # keep custom goals if any
        if g_can not in normalized:
            normalized[g_can] = {}

        if isinstance(levels, dict):
            for l_key, arr in levels.items():
                l_can = canonical_level(l_key) or l_key
                if isinstance(arr, list):
                    normalized[g_can].setdefault(l_can, arr)
        # If levels is not a dict, skip silently

    # Self-heal: ensure defaults exist but DO NOT overwrite user lists
    changed = False
    for g, lvl_map in default_workouts.items():
        normalized.setdefault(g, {})
        for l, default_list in lvl_map.items():
            if l not in normalized[g]:
                normalized[g][l] = default_list[:]  # add missing
                changed = True

    # Remove empty/non-list values (rare corruption cases)
    for g, lvl_map in list(normalized.items()):
        for l, v in list(lvl_map.items()):
            if not isinstance(v, list):
                normalized[g][l] = []
                changed = True

    # Persist back if changes were applied
    if changed:
        try:
            with open("workouts.json", "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2, ensure_ascii=False)
            print("[fix] workouts.json normalized and healed.")
        except Exception:
            pass

    return normalized


# -----------------------------
# Load & save workouts
# -----------------------------
def load_workouts() -> Dict[str, Dict[str, List[str]]]:
    """
    Load workouts from workouts.json if exists, normalize & heal.
    Otherwise deep-copy defaults.
    """
    if os.path.exists("workouts.json"):
        try:
            with open("workouts.json", "r", encoding="utf-8") as f:
                raw = json.load(f)
            return normalize_workouts_dict(raw)
        except Exception:
            print("[warn] workouts.json is unreadable; falling back to defaults.")
            return copy.deepcopy(default_workouts)
    return copy.deepcopy(default_workouts)


def save_workouts(workouts: Dict[str, Dict[str, List[str]]]) -> None:
    """Persist the workouts database to workouts.json (normalized)."""
    normalized = normalize_workouts_dict(workouts)
    with open("workouts.json", "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


# -----------------------------
# Intensity calculation
# -----------------------------
def calculate_intensity(plan: Dict[str, List[str]]) -> Dict[str, int]:
    """
    Sum intensity per day by mapping activities via intensity_map.
    Meals don't contribute to intensity.
    """
    daily_scores: Dict[str, int] = {}
    for day, activities in plan.items():
        score = 0
        for act in activities:
            if act.startswith("Meal"):
                continue
            score += intensity_map.get(act, 20)
        daily_scores[day] = score
    return daily_scores


# -----------------------------
# Plan generation (with @timed and wave-peak suppression)
# -----------------------------
@timed
def generate_plan(workouts: Dict[str, Dict[str, List[str]]],
                  goal_input: str,
                  level_input: str) -> Optional[Tuple[Dict[str, List[str]], str, str]]:
    """
    Generate a 7-day plan.
    Returns (plan, goal_canonical, level_canonical) or None if invalid.
    """
    goal = canonical_goal(goal_input)
    level = canonical_level(level_input)

    if not goal or not level:
        print("Invalid goal or level (format).")
        return None

    # Ensure goal/level present; if missing, try to heal from defaults
    if goal not in workouts:
        workouts[goal] = copy.deepcopy(default_workouts.get(goal, {}))
    if level not in workouts[goal]:
        workouts[goal][level] = copy.deepcopy(default_workouts.get(goal, {}).get(level, []))

    selected = workouts[goal][level]
    if not selected:
        print("No workouts configured for this goal/level.")
        return None

    # Build 7-day plan: pick up to 2 activities + 1 meal
    plan: Dict[str, List[str]] = {}
    for i in range(7):
        k = min(len(selected), 2)
        daily_acts = random.sample(selected, k=k) if k > 0 else []
        meal = f"Meal: {random.choice(meal_plan.get(goal, ['Fruit platter']))}"
        plan[f"Day {i+1}"] = daily_acts + [meal]

    # --- Simple high-intensity wave suppression ---
    scores = calculate_intensity(plan)
    for i in range(2, 8):  # Day 2..7
        prev_day, this_day = f"Day {i-1}", f"Day {i}"
        if scores.get(prev_day, 0) > 80 and scores.get(this_day, 0) > 80:
            acts = plan[this_day]
            non_meal_idxs = [j for j, a in enumerate(acts) if not a.startswith("Meal")]
            if non_meal_idxs:
                hi_idx = max(non_meal_idxs, key=lambda j: intensity_map.get(acts[j], 20))
                acts[hi_idx] = "Yoga 20 min"
                plan[this_day] = acts
                scores = calculate_intensity(plan)

    return plan, goal, level


# -----------------------------
# Save plan & log progress
# -----------------------------
def save_plan(plan: Dict[str, List[str]]) -> str:
    """Save plan to a timestamped .txt file and return path."""
    filename = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for day, activities in plan.items():
            f.write(f"{day}: {', '.join(activities)}\n")
    print(f"Plan saved as {filename}")
    return filename


def log_progress(plan: Optional[Dict[str, List[str]]]) -> None:
    """
    Append a progress record to logs/progress.jsonl for the given day.
    """
    if not plan:
        print("No plan available.")
        return
    day = input("Which day did you complete? (e.g., Day 1): ").strip()
    if day in plan:
        log = {"timestamp": datetime.now().isoformat(), "day": day, "done": plan[day]}
        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", "progress.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
        print(f"Logged progress for {day}. File: {path}")
    else:
        print("Invalid day.")


# -----------------------------
# Add new workout
# -----------------------------
def add_workout(workouts: Dict[str, Dict[str, List[str]]]) -> None:
    """
    Add a new workout item under a goal & level, persist to workouts.json.
    Accepts aliases & case-insensitive input.
    """
    goal_raw = input("Enter goal (Fat Loss/Muscle Gain/Health): ").strip()
    level_raw = input("Enter level (Beginner/Intermediate/Advanced): ").strip()
    new = input("Enter new workout: ").strip()
    if not new:
        raise ValidationError("Workout name cannot be empty.")

    goal = canonical_goal(goal_raw) or goal_raw.strip().title()
    level = canonical_level(level_raw) or level_raw.strip().title()

    workouts.setdefault(goal, {})
    workouts[goal].setdefault(level, [])
    workouts[goal][level].append(new)
    save_workouts(workouts)
    print(f"Workout '{new}' added to {goal} - {level}.")


# -----------------------------
# PDF export with chart (graceful fallback)
# -----------------------------
def show_intensity_chart(intensity: Dict[str, int]) -> Optional[str]:
    """
    Save a bar chart PNG for intensity if matplotlib is available.
    Returns the file path, or None if skipped.
    """
    if not HAS_MPL:
        print("[Info] Matplotlib not installed, skipping chart export (no impact).")
        return None
    plt.figure(figsize=(8, 5))
    plt.bar(list(intensity.keys()), list(intensity.values()), color="skyblue", edgecolor="black")
    plt.title("Workout Intensity for the Week")
    plt.xlabel("Days")
    plt.ylabel("Intensity Score")
    out = "intensity_chart.png"
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    return out


def export_pdf(plan: Dict[str, List[str]],
               intensity: Dict[str, int],
               username: str = "User",
               goal: str = "Goal") -> None:
    """
    Export a PDF report if ReportLab is installed, otherwise export TXT summary.
    """
    if not HAS_RL:
        alt = "workout_plan_summary.txt"
        with open(alt, "w", encoding="utf-8") as f:
            f.write(f"Workout Planner - {goal}\nUser: {username}\n\n")
            for day, acts in plan.items():
                f.write(f"{day}: {', '.join(acts)}\n")
            f.write("\nIntensity:\n")
            for d, s in intensity.items():
                f.write(f"{d}: {s}\n")
        print(f"[Info] ReportLab not installed; exported plain-text summary: {alt}")
        return

    doc = SimpleDocTemplate("workout_plan.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"Workout Planner - {goal}", styles["Title"]))
    story.append(Paragraph(f"User: {username}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Table
    data = [["Day", "Activities"]]
    for day, activities in plan.items():
        data.append([day, ", ".join(activities)])

    table = Table(data, colWidths=[100, 350])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER")
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    # Chart (optional)
    chart_path = show_intensity_chart(intensity)
    if chart_path:
        story.append(Image(chart_path, width=400, height=200))

    doc.build(story)
    print("PDF exported as workout_plan.pdf")


# -----------------------------
# Main program
# -----------------------------
def main() -> None:
    """
    CLI entrypoint for the Workout Planner.
    """
    print("Welcome to Workout Planner!")
    if not HAS_MPL:
        print("[Note] matplotlib not found: chart export will be skipped.")
    if not HAS_RL:
        print("[Note] reportlab not found: PDF export will fall back to TXT.")

    workouts = load_workouts()
    plan: Optional[Dict[str, List[str]]] = None
    intensity: Optional[Dict[str, int]] = None

    # Keep meta info to avoid 'goal' scope issues in export
    plan_meta = {"goal": None, "level": None, "username": "User"}

    while True:
        print("\n=== Main Menu ===")
        print("1. Generate Workout Plan")
        print("2. Add New Workout")
        print("3. Log Workout Progress")
        print("4. Export Report (PDF/TXT)")
        print("5. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            goal_raw = input("Enter goal (Fat Loss/Muscle Gain/Health): ").strip()
            level_raw = input("Enter level (Beginner/Intermediate/Advanced): ").strip()
            res = generate_plan(workouts, goal_raw, level_raw)
            if res:
                plan, goal, level = res
                plan_meta.update({"goal": goal, "level": level})
                print("\n=== Weekly Workout Plan ===")
                for day, activities in plan.items():
                    print(f"{day}: {', '.join(activities)}")
                intensity = calculate_intensity(plan)
                print("\nDaily Intensity:", intensity)
                show_intensity_chart(intensity)
                if input("Save plan to file? (yes/no): ").strip().lower() == "yes":
                    save_plan(plan)

        elif choice == "2":
            try:
                add_workout(workouts)
            except ValidationError as e:
                print("Error:", e)

        elif choice == "3":
            log_progress(plan)

        elif choice == "4":
            if plan and intensity:
                export_pdf(plan, intensity,
                           username=plan_meta.get("username", "User"),
                           goal=(plan_meta.get("goal") or "Goal"))
            else:
                print("Please generate a plan first!")

        elif choice == "5":
            print("Exiting program. Goodbye!")
            break
        else:
            print("Invalid input. Try again.")


if __name__ == "__main__":
    main()
