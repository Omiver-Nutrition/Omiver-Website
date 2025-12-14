from rest_framework import serializers

from core.models import *

from django.contrib.auth.models import User


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "type",
            "date_of_birth",
            "gender",
            "height",
            "weight",
            "ethnicity",
            "allergies",
            "sport",
            "health_conditions",
            "dietary_preferences",
            "fitness_goal",
            "nutritional_goal",
        ]

class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = "__all__"
