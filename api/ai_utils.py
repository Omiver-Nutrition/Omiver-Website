import os
import json
import logging
from typing import Optional
from datetime import date
from django.utils import timezone
from core.models import BiomarkerTest, Recommendation, MealPlan, ExercisePlan
from .llm_engine import generate_structured_plan

logger = logging.getLogger(__name__)


def extract_client_profile_and_markers(test: BiomarkerTest):
    """
    Extracts structured client profile and abnormal/all biomarker results from a BiomarkerTest.
    """
    client = test.client
    results = test.results.select_related("biomarker").all()

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

    dob = client.date_of_birth if client else None
    if isinstance(dob, date):
        age = (timezone.now().date() - dob).days // 365
    else:
        age = "Unknown"

    profile = {
        "client_id": client.id if client else None,
        "email": client.email if client else "",
        "age": age,
        "gender": client.gender if client else "Unknown",
        "height": client.height if client else None,
        "weight": client.weight if client else None,
        "sport": client.sport if client else None,
        "fitness_goal": client.fitness_goal if client else None,
        "nutritional_goal": client.nutritional_goal if client else None,
        "health_conditions": client.health_conditions if client else None,
        "dietary_preferences": client.dietary_preferences if client else None,
        "weekly_exercise_routine": client.weekly_exercise_routine if client else None,
        "exercise_days_per_week": client.exercise_days_per_week if client else None,
        "exercise_types": client.exercise_types if client else None,
    }

    return profile, abnormal_markers, all_markers_summary


def generate_ai_recommendation_draft(test_id: int, user_role: str = "dietician") -> Optional[Recommendation]:
    """
    Generates a personalized recommendation draft using the unified LLM Engine.
    Also synchronizes meals into MealPlan.
    """
    try:
        test = BiomarkerTest.objects.select_related("client").get(pk=test_id)
    except BiomarkerTest.DoesNotExist:
        logger.error(f"BiomarkerTest with ID {test_id} not found.")
        return None

    client = test.client
    profile, abnormal_markers, all_markers = extract_client_profile_and_markers(test)

    # Invoke LLM engine
    plan_json = generate_structured_plan(
        client_profile=profile,
        abnormal_markers=abnormal_markers,
        all_markers=all_markers,
        user_role=user_role
    )

    dietary_draft = plan_json.get("dietary_recommendations", {})
    exercise_draft = plan_json.get("exercise_recommendations", {})
    summary_text = dietary_draft.get("summary", "")[:490]

    # Save to Recommendation model
    recommendation, created = Recommendation.objects.get_or_create(
        client=client,
        biomarker_test=test,
        defaults={
            "status": "DRAFT",
            "text": summary_text,
            "dietary_draft": dietary_draft,
            "exercise_draft": exercise_draft,
        }
    )

    if not created:
        recommendation.dietary_draft = dietary_draft
        recommendation.exercise_draft = exercise_draft
        recommendation.text = summary_text
        recommendation.status = "DRAFT"
        recommendation.save()

    # Automatically synchronize food into MealPlan and exercise into ExercisePlan model
    if client and "sample_meal_plan" in dietary_draft:
        try:
            MealPlan.objects.create(
                client=client,
                meals=json.dumps(dietary_draft["sample_meal_plan"])
            )
        except Exception as e:
            logger.warning(f"Could not persist MealPlan record: {e}")

    if client and exercise_draft:
        try:
            ExercisePlan.objects.create(
                client=client,
                biomarker_test=test,
                summary=exercise_draft.get("summary", ""),
                frequency=exercise_draft.get("frequency", ""),
                activities=exercise_draft.get("activities", []),
                precautions=exercise_draft.get("precautions", [])
            )
        except Exception as e:
            logger.warning(f"Could not persist ExercisePlan record: {e}")

    return recommendation


def regenerate_ai_recommendation_with_feedback(recommendation_id: int, doctor_feedback: str) -> Optional[Recommendation]:
    """
    Regenerates AI recommendations with doctor feedback incorporated.
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

    if test:
        profile, abnormal_markers, all_markers = extract_client_profile_and_markers(test)
    else:
        profile = {
            "client_id": client.id if client else None,
            "email": client.email if client else "",
            "dietary_preferences": client.dietary_preferences if client else None,
            "health_conditions": client.health_conditions if client else None,
            "fitness_goal": client.fitness_goal if client else None,
            "height": client.height if client else None,
            "weight": client.weight if client else None,
        }
        abnormal_markers = []
        all_markers = []

    plan_json = generate_structured_plan(
        client_profile=profile,
        abnormal_markers=abnormal_markers,
        all_markers=all_markers,
        user_role="dietician",
        doctor_feedback=doctor_feedback
    )

    dietary_draft = plan_json.get("dietary_recommendations", {})
    exercise_draft = plan_json.get("exercise_recommendations", {})
    summary_text = dietary_draft.get("summary", "")[:490]

    rec.dietary_draft = dietary_draft
    rec.exercise_draft = exercise_draft
    rec.text = summary_text
    rec.status = "PENDING_REVIEW"
    rec.save()

    return rec
