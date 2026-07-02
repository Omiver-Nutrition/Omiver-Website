import os
import json
import logging
import requests
from django.utils import timezone
from core.models import Client, BiomarkerTest, BiomarkerResult, Recommendation

logger = logging.getLogger(__name__)

def generate_ai_recommendation_draft(test_id):
    """
    Asynchronously or synchronously generates an initial AI recommendation draft
    based on the BiomarkerTest results and the client's health profile.
    Uses Gemini API if configured, otherwise falls back to a smart, dynamic mock.
    """
    try:
        test = BiomarkerTest.objects.select_related("client").get(pk=test_id)
    except BiomarkerTest.DoesNotExist:
        logger.error(f"BiomarkerTest with ID {test_id} not found.")
        return None

    client = test.client
    results = test.results.select_related("biomarker").all()

    # 1. Gather abnormal biomarkers
    abnormal_markers = []
    all_markers_summary = []
    for r in results:
        status = r.status or "NORMAL"
        marker_info = {
            "name": r.biomarker.name,
            "value": r.value,
            "unit": r.biomarker.unit,
            "status": status,
            "normal_range": f"{r.biomarker.range_min} - {r.biomarker.range_max}"
        }
        all_markers_summary.append(marker_info)
        if status in ["LOW", "HIGH"]:
            abnormal_markers.append(marker_info)

    # 2. Gather client health profile
    profile = {
        "email": client.email,
        "age": (timezone.now().date() - client.date_of_birth).days // 365 if client.date_of_birth else "Unknown",
        "gender": client.gender or "Unknown",
        "height": client.height,
        "weight": client.weight,
        "sport": client.sport,
        "fitness_goal": client.fitness_goal,
        "nutritional_goal": client.nutritional_goal,
        "health_conditions": client.health_conditions,
        "dietary_preferences": client.dietary_preferences,
        "weekly_exercise_routine": client.weekly_exercise_routine,
        "exercise_days_per_week": client.exercise_days_per_week,
        "exercise_types": client.exercise_types,
    }

    # 3. Construct Prompt
    prompt = f"""
    You are Omiver's elite metabolic health AI. Generate a personalized, medical-grade dietary and exercise draft plan for a client based on their profile and latest biomarker test results.
    
    CLIENT PROFILE:
    - Age: {profile['age']}, Gender: {profile['gender']}
    - Weight: {profile['weight']} kg, Height: {profile['height']} cm
    - Main Fitness Goal: {profile['fitness_goal']}
    - Nutritional Goal: {profile['nutritional_goal']}
    - Health Conditions: {profile['health_conditions']}
    - Dietary Preferences: {profile['dietary_preferences']}
    - Current Exercise Routine: {profile['weekly_exercise_routine']} ({profile['exercise_days_per_week']} days/week, types: {profile['exercise_types']})

    BIOMARKER TEST RESULTS:
    {json.dumps(all_markers_summary, indent=2)}

    ABNORMAL MARKERS (Focus heavily on correcting these):
    {json.dumps(abnormal_markers, indent=2)}

    Output your response STRICTLY as a valid JSON object matching the following structure exactly, with no additional markdown formatting, conversational text, or backticks:
    {{
      "dietary_recommendations": {{
        "summary": "A concise paragraph addressing their biomarker status and how nutrition helps.",
        "dos": ["Food/nutrient 1", "Food/nutrient 2", "Food/nutrient 3"],
        "donts": ["Avoided item 1", "Avoided item 2"],
        "sample_meal_plan": [
          {{"meal": "Breakfast", "suggestion": "Suggested meal description"}},
          {{"meal": "Lunch", "suggestion": "Suggested meal description"}},
          {{"meal": "Dinner", "suggestion": "Suggested meal description"}}
        ]
      }},
      "exercise_recommendations": {{
        "summary": "A concise paragraph explaining how to optimize physical training for their targets.",
        "frequency": "E.g., 3-4 sessions per week",
        "activities": ["Activity 1", "Activity 2", "Activity 3"],
        "precautions": ["Precaution 1"]
      }}
    }}
    """

    api_key = os.getenv("GEMINI_API_KEY")
    ai_json = None

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                result_data = response.json()
                text_response = result_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                ai_json = json.loads(text_response)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}. Falling back to rule-based mock generation.")

    if not ai_json:
        # 4. Smart dynamic fallback mock generation
        ai_json = generate_dynamic_mock_recommendation(profile, abnormal_markers)

    # 5. Save to Recommendation model
    recommendation, created = Recommendation.objects.get_or_create(
        client=client,
        biomarker_test=test,
        defaults={
            "status": "DRAFT",
            "text": ai_json["dietary_recommendations"]["summary"][:490],
            "dietary_draft": ai_json["dietary_recommendations"],
            "exercise_draft": ai_json["exercise_recommendations"],
        }
    )

    if not created:
        recommendation.dietary_draft = ai_json["dietary_recommendations"]
        recommendation.exercise_draft = ai_json["exercise_recommendations"]
        recommendation.text = ai_json["dietary_recommendations"]["summary"][:490]
        recommendation.status = "DRAFT"
        recommendation.save()

    return recommendation


def generate_dynamic_mock_recommendation(profile, abnormal_markers):
    """
    Generates high-quality, tailored recommendations based on the patient's actual
    biomarker and fitness profile as a robust rule-based mock when Gemini API is unavailable.
    """
    has_high_cholesterol = any("cholesterol" in m["name"].lower() or "ldl" in m["name"].lower() for m in abnormal_markers)
    has_low_vit_d = any("vitamin d" in m["name"].lower() or "vit d" in m["name"].lower() for m in abnormal_markers)
    has_high_sugar = any("glucose" in m["name"].lower() or "hba1c" in m["name"].lower() for m in abnormal_markers)

    # Draft dietary recommendations
    diet_summary = f"Based on your results showing {len(abnormal_markers)} abnormal biomarkers, "
    diet_dos = ["Leafy green vegetables", "Lean proteins (poultry, fish)", "Hydration (2.5L water/day)"]
    diet_donts = ["Refined sugar", "Ultra-processed snacks"]
    breakfast = "Scrambled egg whites with avocado on whole-grain sourdough toast."
    lunch = "Large mixed greens salad with grilled chicken breast, quinoa, and olive oil dressing."
    dinner = "Steamed cod or wild-caught salmon with wild rice and broccoli."

    if has_high_cholesterol:
        diet_summary += "we recommend focused reduction of saturated fats and high-density lipoprotein support. "
        diet_dos.extend(["Soluble oat fiber", "Omega-3 rich seeds (chia, flax)", "Olive oil"])
        diet_donts.extend(["Fried foods", "Butter and heavy cream"])
        breakfast = "Steel-cut oatmeal topped with chia seeds, flax seeds, and fresh berries."
    if has_low_vit_d:
        diet_summary += "we recommend increasing dietary vitamin D and healthy fats absorption. "
        diet_dos.extend(["Fortified plant milk", "Egg yolks", "Mackerels and salmon"])
    if has_high_sugar:
        diet_summary += "we advise reducing simple glycemic index foods to stabilize glucose curves. "
        diet_dos.extend(["Cinnamon", "Legumes and beans", "Extra avocado and healthy fiber"])
        diet_donts.extend(["White bread", "Sweetened beverages"])
        breakfast = "Greek yogurt with pumpkin seeds, cinnamon, and handful of walnuts."

    if not abnormal_markers:
        diet_summary += "your biomarkers are in great optimal and normal ranges! We recommend a general maintenance diet to sustain your metabolic health."

    # Draft exercise recommendations
    exercise_summary = "To support your metabolic markers and goals, we advise a structured balance of Zone 2 cardiovascular training and progressive resistance work."
    exercise_activities = ["Brisk walking", "Bodyweight squats/lunges", "Core stabilization drills"]
    exercise_precautions = ["Ensure proper warming up for 10 minutes prior to workouts."]

    if "weight" in str(profile["fitness_goal"]).lower() or "muscle" in str(profile["fitness_goal"]).lower():
        exercise_summary += " Heavy emphasis placed on hyper-trophy and strength-building to boost basal metabolic rate."
        exercise_activities = ["Deadlifts (moderate weight)", "Dumbbell chest presses", "Pull-ups or lat pulldowns"]
    elif "cardio" in str(profile["exercise_types"]).lower() or "run" in str(profile["exercise_types"]).lower():
        exercise_summary += " Designed to increase aerobic base (VO2 Max) and improve capillary density."
        exercise_activities = ["Zone 2 jogging", "Interval cycling (HIIT)", "Rowing machine"]

    if has_high_cholesterol:
        exercise_summary += " High lipids indicate a strong benefit from consistent moderate-intensity cardiovascular training to upregulate HDL-C clearance."
        exercise_activities.append("45 minutes of steady-state stationary cycling")

    return {
        "dietary_recommendations": {
            "summary": diet_summary.strip(),
            "dos": list(set(diet_dos)),
            "donts": list(set(diet_donts)),
            "sample_meal_plan": [
                {"meal": "Breakfast", "suggestion": breakfast},
                {"meal": "Lunch", "suggestion": lunch},
                {"meal": "Dinner", "suggestion": dinner}
            ]
        },
        "exercise_recommendations": {
            "summary": exercise_summary.strip(),
            "frequency": f"{profile['exercise_days_per_week'] or 3} to 4 sessions per week",
            "activities": list(set(exercise_activities)),
            "precautions": exercise_precautions
        }
    }


def regenerate_ai_recommendation_with_feedback(recommendation_id, doctor_feedback):
    """
    Subsequent AI generation that integrates the doctor's specific feedback to refine the plan.
    Transitions status to REVISING, then saves back to PENDING_REVIEW.
    """
    try:
        rec = Recommendation.objects.select_related("client", "biomarker_test").get(pk=recommendation_id)
    except Recommendation.DoesNotExist:
        logger.error(f"Recommendation with ID {recommendation_id} not found.")
        return None

    client = rec.client
    test = rec.biomarker_test
    
    rec.doctor_feedback = doctor_feedback
    rec.status = "REVISING"
    rec.save(update_fields=["status", "doctor_feedback"])

    results = test.results.select_related("biomarker").all() if test else []
    abnormal_markers = []
    for r in results:
        if r.status in ["LOW", "HIGH"]:
            abnormal_markers.append({
                "name": r.biomarker.name,
                "value": r.value,
                "unit": r.biomarker.unit,
                "status": r.status
            })

    prompt = f"""
    You are Omiver's elite metabolic health AI. You have previously generated a draft recommendation for this client, and their doctor has reviewed it and provided specific feedback.
    You MUST adjust your recommendations to satisfy the doctor's requirements completely.
    
    DOCTOR'S DIRECT FEEDBACK (Acknowledge and execute this perfectly):
    "{doctor_feedback}"

    CLIENT DETAILS:
    - Dietary Prefs: {client.dietary_preferences}
    - Health Conditions: {client.health_conditions}
    - Goal: {client.fitness_goal}

    PREVIOUS AI DIET DRAFT:
    {json.dumps(rec.dietary_draft, indent=2)}

    PREVIOUS AI EXERCISE DRAFT:
    {json.dumps(rec.exercise_draft, indent=2)}

    Output your updated response STRICTLY as a valid JSON object matching the following structure exactly, with no additional formatting:
    {{
      "dietary_recommendations": {{
        "summary": "A refined dietary paragraph incorporating doctor feedback.",
        "dos": ["Updated item 1", "Updated item 2"],
        "donts": ["Avoided item 1"],
        "sample_meal_plan": [
          {{"meal": "Breakfast", "suggestion": "Refined breakfast"}},
          {{"meal": "Lunch", "suggestion": "Refined lunch"}},
          {{"meal": "Dinner", "suggestion": "Refined dinner"}}
        ]
      }},
      "exercise_recommendations": {{
        "summary": "A refined exercise paragraph incorporating doctor feedback.",
        "frequency": "Updated frequency",
        "activities": ["Updated activity 1", "Updated activity 2"],
        "precautions": ["Updated precaution"]
      }}
    }}
    """

    api_key = os.getenv("GEMINI_API_KEY")
    ai_json = None

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                result_data = response.json()
                text_response = result_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                ai_json = json.loads(text_response)
        except Exception as e:
            logger.error(f"Gemini feedback revision failed: {e}. Falling back to rule-based adjustment.")

    if not ai_json:
        # Static mock revision: Append doctor feedback notes to existing drafts
        diet_summary = f"{rec.dietary_draft.get('summary', '')} (Adjusted per doctor notes: {doctor_feedback})"
        exercise_summary = f"{rec.exercise_draft.get('summary', '')} (Adjusted per doctor notes: {doctor_feedback})"
        
        ai_json = {
            "dietary_recommendations": {
                "summary": diet_summary,
                "dos": rec.dietary_draft.get("dos", []) + ["Adjusted Item"],
                "donts": rec.dietary_draft.get("donts", []),
                "sample_meal_plan": rec.dietary_draft.get("sample_meal_plan", [])
            },
            "exercise_recommendations": {
                "summary": exercise_summary,
                "frequency": rec.exercise_draft.get("frequency", "3 sessions/week"),
                "activities": rec.exercise_draft.get("activities", []) + ["Swimming / Low-Impact Cardio"],
                "precautions": rec.exercise_draft.get("precautions", []) + ["Avoid knee stress"]
            }
        }

    rec.dietary_draft = ai_json["dietary_recommendations"]
    rec.exercise_draft = ai_json["exercise_recommendations"]
    rec.text = ai_json["dietary_recommendations"]["summary"][:490]
    rec.status = "PENDING_REVIEW"
    rec.save()

    return rec
