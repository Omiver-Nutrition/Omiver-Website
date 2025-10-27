from rest_framework import serializers

from core.models import *

from django.contrib.auth.models import User


# Move ProfileSerializer above ClientSerializer to fix NameError
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "date_of_birth",
            "ethnicity",
            "allergies",
            "sport",
            "health_conditions",
            "dietary_preferences",
            "gender",
            "height",
            "weight",
            "fitness_goal",
            "nutritional_goal",
        ]


class ClientSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    class Meta:
        model = Client
        fields = [
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "type",
            "profile",
        ]


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = "__all__"
