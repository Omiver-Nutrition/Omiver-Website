from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta


class Biomarker(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    range_min = models.FloatField()
    range_max = models.FloatField()
    unit = models.CharField(max_length=50)


class BiomarkerTest(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    data = models.JSONField()
    recorded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Profile(models.Model):
    id = models.AutoField(primary_key=True)
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=10)
    height = models.FloatField()
    weight = models.FloatField()
    ethnicity = models.CharField(max_length=100)
    sport = models.CharField(max_length=100)
    health_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    dietary_preferences = models.TextField(blank=True)
    fitness_goal = models.CharField(max_length=100)
    nutritional_goal = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_by_id(profile_id) -> "Profile":
        """
        Retrieve a Profile object by ID.
        Returns the Profile instance if found, else None.
        """
        return Profile.objects.filter(id=profile_id).first()


class Client(models.Model):

    USER_TYPES = [("PROVIDER", "PROVIDER"), ("INDIVIDUAL", "INDIVIDUAL")]
    # link to auth.user
    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, null=True, blank=True
    )

    # extra field
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=10, choices=USER_TYPES, default="INDIVIDUAL")
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<Client {self.first_name} {self.last_name} ({self.email})>"

    @staticmethod
    def get_client_by_email(email) -> "Client":
        """
        Retrieve a Client object by email.
        Returns the Client instance if found, else None.
        """
        return Client.objects.filter(email=email).first()

    @staticmethod
    def get_client_by_id(client_id) -> "Client":
        """
        Retrieve a Client object by ID.
        Returns the Client instance if found, else None.
        """
        return Client.objects.filter(id=client_id).first()


class MealPlan(models.Model):
    """Represents a meal plan associated with a client and a list of meals.

    This model stores meal plan details, including the client, description, and meals for a specific timestamp.
    """

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meals = models.TextField(help_text="JSON or comma-separated list of meals")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<MealPlan for client {self.client} for time {self.timestamp}: {self.meals}>"

    @staticmethod
    def get_meal_plans_by_client_and_date(
        client_id, start_date=None, end_date=None
    ) -> "models.QuerySet":
        """
        Retrieve MealPlan objects for a client within a date range.
        If no date range is provided, defaults to current week.
        Returns a QuerySet of MealPlan instances.
        """
        now = timezone.now()
        if start_date is None or end_date is None:
            # Get start and end of current week (Monday to Sunday)
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(
                days=6, hours=23, minutes=59, seconds=59
            )
            start_date = start_of_week
            end_date = end_of_week
        return MealPlan.objects.filter(
            client_id=client_id, timestamp__range=(start_date, end_date)
        )

    @staticmethod
    def add_meal_plan(client, meals):
        pass
