from django.utils.dateparse import parse_datetime
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from .serializer import ClientSerializer, MealPlanSerializer, ProfileSerializer
from core.models import MealPlan, Client, Profile


# Create your views here.
def index(request):
    return HttpResponse("Welcome to the API endpoint!")


@api_view(["POST"])
def create_client(request):
    # extract profile data if present
    client_data = request.data
    profile_data = client_data.pop("profile", None)

    client_instance = Client.objects.filter(email=client_data.get("email")).first()
    # if client exists, continue to the profile creation
    if client_instance:
        client_serializer = ClientSerializer(
            client_instance, data=client_data, partial=True
        )
    else:
        client_serializer = ClientSerializer(data=client_data)
    if not client_serializer.is_valid():
        return Response(client_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    client_serializer.save()
    # create profile for client
    if profile_data:
        profile_data = profile_data.copy()
        if client_instance and client_instance.profile:
            profile_serializer = ProfileSerializer(
                client_instance.profile, data=profile_data, partial=True
            )
        else:
            profile_serializer = ProfileSerializer(data=profile_data)
        if not profile_serializer.is_valid():
            return Response(
                profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        profile_serializer.save()
        client = client_serializer.data.copy()
        client["profile"] = profile_serializer.data.get("id")
        # save to client
        client_serializer = ClientSerializer(
            client_serializer.instance, client, partial=True
        )
        if not client_serializer.is_valid():
            return Response(
                client_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        client_serializer.save()
    return Response(client_serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def client_handler(request, pk):
    client = Client.objects.get(id=pk)
    serializer = ClientSerializer(client)
    if client.profile:
        profile_serializer = ProfileSerializer(client.profile)
        data = serializer.data
        data["profile"] = profile_serializer.data
        return Response(data)
    return Response(serializer.data)


def register_user(username, password):
    if not username or not password:
        return None, "Username and password are required"
    if User.objects.filter(username=username).exists():
        return None, "Username already exists"
    user = User.objects.create_user(username=username, password=password)
    return user, None

def create_client(data):
    client_serializer = ClientSerializer(data=data)
    if not client_serializer.is_valid():
        return None, client_serializer.errors
    client_serializer.save()
    return client_serializer, None

def create_profile(data):
    profile_serializer = ProfileSerializer(data=data)
    if not profile_serializer.is_valid():
        return None, profile_serializer.errors
    profile_serializer.save()
    return profile_serializer, None


@api_view(["POST"])
def register(request):
    data = request.data
    username = data.pop("username", None)
    password = data.pop("password", None)
    
    user, error = register_user(username, password)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    data["user"] = user.id
    profile = data.pop("profile", None)
    
    client_serializer, error = create_client(data)
    if error:
        user.delete()
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
    client_serializer.instance
    if profile:
        profile_serializer, error = create_profile(profile)
        if error:
            user.delete()
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        {"message": "User registered successfully"}, status=status.HTTP_201_CREATED
    )


@login_required
@api_view(["GET"])
def generate_mealPlan(request, client_id):
    client = Client.objects.get(id=client_id)
    return Response(
        {"message": f"will send client info: {client}"}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
def meal_plan(request):
    """
    Handles the meal plan requests.
    Accepts client_id, start_date, and end_date as query parameters.
    Returns the meal plan for the specified client and date range.
    """
    client_id = request.GET.get("client_id")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if not client_id:
        return Response(
            {"error": "client_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    # Optionally parse start_date and end_date if provided
    start_dt = parse_datetime(start_date) if start_date else None
    end_dt = parse_datetime(end_date) if end_date else None
    meal_plans = MealPlan.get_meal_plans_by_client_and_date(client_id, start_dt, end_dt)
    # Serialize meal plans
    meal_plan_list = [
        {
            "id": mp.id,
            "client_id": mp.client_id,
            "timestamp": mp.timestamp,
            "meals": mp.meals,
            "created_at": mp.created_at,
            "updated_at": mp.updated_at,
        }
        for mp in meal_plans
    ]
    meal_plan = MealPlanSerializer(meal_plan_list, many=True)
    return Response(meal_plan.data)
