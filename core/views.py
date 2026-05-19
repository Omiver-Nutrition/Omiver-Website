from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
import os

def index_page(request):
    return render(request, "core/index.html")

def information_page(request):
    return render(request, "core/information.html")

def login_page(request):
    if request.method == 'POST':
        # username = request.POST['username']
        code = request.POST['login_code']
        user = authenticate(
            request,
            username=os.getenv('DJANGO_SUPERUSER_USERNAME'),
            password=os.getenv('DJANGO_SUPERUSER_PASSWORD'),
        )
        if code == "omiver":
            login(request, user)  # Log in the user (you can create a demo user if needed)
            return redirect('demo/select')
        else:
            messages.error(request, "Invalid code. Please try again.")
    return render(request, "core/login.html")

def register_page(request):
    return render(request, "core/register.html")

def terms_page(request):
    return render(request, "core/terms.html")

def privacy_page(request):
    return render(request, "core/privacy.html")