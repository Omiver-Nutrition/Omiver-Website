from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # meal plan api
    path("mealPlan", views.meal_plan, name="meal_plan"),
    path(
        "mealPlan/generate/<int:client_id>",
        views.generate_mealPlan,
        name="generate_mealPlan",
    ),
    # client api
    path("client", views.create_client, name="create_client"),
    path("client/<int:pk>", views.client_handler, name="client_handler"),
    # account api
    path("register", views.register, name="register"),
    path("check_email", views.check_email, name="check_email"),
    path("login", views.login_handler, name="login"),
]
