from django.utils.dateparse import parse_datetime
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token

from .serializer import ClientSerializer, MealPlanSerializer
from core.models import MealPlan, Client


# Create your views here.
def index(request):
    return HttpResponse("Welcome to the API endpoint!")


@login_required
@api_view(["POST"])
def create_client(request):
    # extract profile data if present
    client_data = request.data
    instance = Client.get_client_by_email(client_data.get("email"))
    # if client exists, continue to the profile creation
    if instance:
        serializer = ClientSerializer(instance, data=client_data, partial=True)
    else:
        serializer = ClientSerializer(data=client_data)
    if not serializer.is_valid():
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data, status.HTTP_201_CREATED)


@api_view(["GET"])
def client_handler(request, pk):
    try:
        client = Client.objects.get(id=pk)
    except Client.DoesNotExist:
        return Response({"error": "Client not found"}, status.HTTP_404_NOT_FOUND)
    serializer = ClientSerializer(client)
    return Response(serializer.data)


def register_user(username, password):
    if not username or not password:
        return None, "Username and password are required"
    if User.objects.filter(username=username).exists():
        return None, "Username already exists"
    user = User.objects.create_user(username=username, password=password)
    return user, None


def create_client_helper(data):
    client_serializer = ClientSerializer(data=data)
    if not client_serializer.is_valid():
        return None, client_serializer.errors
    client_serializer.save()
    return client_serializer, None


@api_view(["POST"])
def register(request):
    """register user

    example:
    {
        "username": "johndoe",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@email.com",
        "type": "INDIVIDUAL",
        "date_of_birth":"1990-01-01",
        "gender":"Male",
        "height":180,
        "weight":75,
        "ethnicity":"Asian",
        "allergies":"None",
        "sport":"running",
        "health_conditions":"None",
        "dietary_preferences":"Vegetarian",
        "fitness_goal":"my goal 1",
        "nutritional_goal":"goal 2"
    }
    """
    data = request.data
    username = data.pop("username", None)
    password = data.pop("password", None)

    user, error = register_user(username, password)
    if error:
        return Response(error, status.HTTP_400_BAD_REQUEST)
    data["user"] = user.id

    client_serializer, error = create_client_helper(data)
    if error:
        user.delete()
        return Response(error, status.HTTP_400_BAD_REQUEST)
    return Response(client_serializer.data, status.HTTP_201_CREATED)


@api_view(["POST"])
def login_handler(request):
    data = request.data
    user = authenticate(**data)
    if user is None:
        return Response({"error": "invalid credential"}, status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    try:
        client = Client.objects.get(user=user)
        client_serializer = ClientSerializer(client)
        request.session["client_id"] = client.id
        return Response(client_serializer.data, status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response({"error": e}, status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def check_username(request):
    """Check if a username (email) already exists.

    Query param: ?username=someone@example.com
    Returns: { "exists": true/false }
    """
    username = request.GET.get("username")
    if not username:
        return Response(
            {"error": "username query param required"},
            status.HTTP_400_BAD_REQUEST,
        )
    exists = User.objects.filter(username=username).exists()
    return Response({"exists": exists}, status.HTTP_200_OK)


@login_required
@api_view(["GET"])
def generate_mealPlan(request, client_id):
    client = Client.objects.get(id=client_id)
    return Response({"message": f"will send client info: {client}"}, status.HTTP_200_OK)


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
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
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

def generate_mealPlan(request, client_id):
    client = Client.objects.get(id=client_id)
    return Response({"message": f"will send client info: {client}"}, status.HTTP_200_OK)