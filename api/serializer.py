from rest_framework import serializers

from core.models import *


# Move ProfileSerializer above ClientSerializer to fix NameError
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "date_of_birth",
            "sex",
            "height",
            "weight",
            "ethnicity",
            "allergies",
            "sport",
            "fitness_goal",
            "nutritional_goal",
        ]


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
            "profile",
        ]


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = "__all__"
