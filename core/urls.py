from django.urls import path

from . import views

urlpatterns = [
    path("", views.index_page, name="index_page"),
    path("information", views.information_page, name="information_page"),
    path("login", views.login_page, name="login_page"),
    path('register', views.register_page, name='register'),
    path("terms", views.terms_page, name="terms_page"),
    path("privacy", views.privacy_page, name="privacy_page"),
]