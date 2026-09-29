"""
Standardized Nutrition & Energy Calculation Engine (One Source of Truth).
Implements the Mifflin-St Jeor formula and standardized macronutrient distribution rules.
"""

from typing import Dict, Any, Tuple, Optional


def calculate_bmr_and_tdee(
    weight_kg: Optional[float],
    height_cm: Optional[float],
    age: Optional[int],
    gender: Optional[str],
    exercise_days_per_week: Optional[int] = None,
    activity_level: Optional[str] = None
) -> Tuple[float, float]:
    """
    Calculates Basal Metabolic Rate (BMR) using the Mifflin-St Jeor formula,
    and Total Daily Energy Expenditure (TDEE).
    
    Returns:
        (bmr, tdee) in kcal/day
    """
    # Fallback defaults for missing metrics
    w = float(weight_kg) if weight_kg and weight_kg > 0 else 70.0
    h = float(height_cm) if height_cm and height_cm > 0 else 170.0
    a = int(age) if age and age > 0 else 30
    g = (gender or "other").strip().lower()

    # 1. BMR calculation (Mifflin-St Jeor)
    # Men: BMR = (10 * weight in kg) + (6.25 * height in cm) - (5 * age in years) + 5
    # Women: BMR = (10 * weight in kg) + (6.25 * height in cm) - (5 * age in years) - 161
    if g in ["m", "male", "man"]:
        bmr = (10.0 * w) + (6.25 * h) - (5.0 * a) + 5.0
    elif g in ["f", "female", "woman"]:
        bmr = (10.0 * w) + (6.25 * h) - (5.0 * a) - 161.0
    else:
        # Neutral average
        bmr = (10.0 * w) + (6.25 * h) - (5.0 * a) - 78.0

    # 2. Activity Multiplier
    days = exercise_days_per_week if exercise_days_per_week is not None else 3
    if activity_level:
        act = activity_level.lower()
        if "sedentary" in act:
            multiplier = 1.2
        elif "light" in act:
            multiplier = 1.375
        elif "moderate" in act:
            multiplier = 1.55
        elif "very" in act or "heavy" in act:
            multiplier = 1.725
        elif "athlete" in act or "extra" in act:
            multiplier = 1.9
        else:
            multiplier = 1.375
    else:
        if days <= 1:
            multiplier = 1.2
        elif days <= 3:
            multiplier = 1.375
        elif days <= 5:
            multiplier = 1.55
        elif days <= 6:
            multiplier = 1.725
        else:
            multiplier = 1.9

    tdee = round(bmr * multiplier, 1)
    bmr = round(bmr, 1)
    return bmr, tdee


def calculate_target_calories(
    tdee: float,
    fitness_goal: Optional[str] = None,
    nutritional_goal: Optional[str] = None
) -> Tuple[int, int]:
    """
    Calculates daily caloric target based on fitness/nutrition goals.
    
    Returns:
        (target_calories, calorie_delta)
    """
    goal_str = f"{fitness_goal or ''} {nutritional_goal or ''}".lower()
    
    if any(k in goal_str for k in ["fat loss", "weight loss", "cut", "lean", "deficit"]):
        # 15-20% deficit (capped at 500 kcal)
        delta = -max(300, min(500, int(tdee * 0.20)))
    elif any(k in goal_str for k in ["muscle", "hypertrophy", "bulk", "gain", "surplus"]):
        # 10-15% surplus (250-400 kcal)
        delta = max(250, min(400, int(tdee * 0.12)))
    elif any(k in goal_str for k in ["endurance", "performance"]):
        delta = 100
    else:
        # Maintenance
        delta = 0

    target = max(1200, int(round(tdee + delta)))
    return target, delta


def calculate_macronutrients(
    target_calories: int,
    weight_kg: Optional[float] = None,
    fitness_goal: Optional[str] = None,
    nutritional_goal: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates macro distribution (Protein, Carbohydrates, Fat) in grams and percentages.
    - Protein: 1.6 - 2.2 g/kg (4 kcal/g)
    - Fat: 20 - 30% of total calories (9 kcal/g)
    - Carbs: Remainder of calories (4 kcal/g)
    """
    w = float(weight_kg) if weight_kg and weight_kg > 0 else 70.0
    goal_str = f"{fitness_goal or ''} {nutritional_goal or ''}".lower()

    if "keto" in goal_str or "low carb" in goal_str:
        protein_g = int(round(w * 1.8))
        carb_g = min(50, int(round(target_calories * 0.08 / 4.0)))
        fat_calories = target_calories - (protein_g * 4) - (carb_g * 4)
        fat_g = max(40, int(round(fat_calories / 9.0)))
    elif "muscle" in goal_str or "hypertrophy" in goal_str:
        protein_g = int(round(w * 2.0))
        fat_g = int(round((target_calories * 0.25) / 9.0))
        carb_calories = target_calories - (protein_g * 4) - (fat_g * 9)
        carb_g = max(80, int(round(carb_calories / 4.0)))
    elif "fat loss" in goal_str or "weight loss" in goal_str:
        protein_g = int(round(w * 1.9))
        fat_g = int(round((target_calories * 0.25) / 9.0))
        carb_calories = target_calories - (protein_g * 4) - (fat_g * 9)
        carb_g = max(80, int(round(carb_calories / 4.0)))
    else:
        # Balanced 30P / 45C / 25F
        protein_g = int(round((target_calories * 0.30) / 4.0))
        fat_g = int(round((target_calories * 0.25) / 9.0))
        carb_g = int(round((target_calories * 0.45) / 4.0))

    return {
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "protein_pct": round((protein_g * 4 / target_calories) * 100),
        "carb_pct": round((carb_g * 4 / target_calories) * 100),
        "fat_pct": round((fat_g * 9 / target_calories) * 100),
    }
