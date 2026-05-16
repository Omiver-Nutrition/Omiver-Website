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
    path("validate_referral_code", views.validate_referral_code, name="validate_referral_code"),
    path("verify-kit-code", views.verify_kit_code, name="verify_kit_code"),
    path("login", views.login_handler, name="login"),
    path("logout", views.logout_handler, name="logout"),
    path("verify-token", views.verify_token_handler, name="verify_token"),
    # password reset via API for SPA
    path("password-reset", views.password_reset_request, name="password_reset_request"),
    path("password-reset/confirm", views.password_reset_confirm, name="password_reset_confirm"),
    # test kits
    path("kits", views.list_kits, name="list_kits"),
    # orders & shipping tracking
    path("orders", views.list_orders, name="list_orders"),
    path("orders/export/csv", views.export_orders_csv, name="export_orders_csv"),
    path("orders/create", views.create_order, name="create_order"),
    path("orders/track", views.track_order, name="track_order"),
    path("orders/<int:pk>", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status", views.update_order_status, name="update_order_status"),
    # checkout & purchases
    path("checkout", views.checkout, name="checkout"),
    path("create-payment-intent", views.create_payment_intent, name="create_payment_intent"),
    path("confirm-payment", views.confirm_payment, name="confirm_payment"),
    path("stripe-webhook", views.stripe_webhook, name="stripe_webhook"),

    path("purchases", views.purchase_history, name="purchase_history"),
    path("purchases/<int:pk>", views.purchase_detail, name="purchase_detail"),
    # biomarkers & dashboard
    path("biomarkers", views.list_biomarkers, name="list_biomarkers"),
    path("biomarker-tests", views.list_biomarker_tests, name="list_biomarker_tests"),
    path("biomarker-tests/<int:pk>", views.biomarker_test_detail, name="biomarker_test_detail"),
    path("dashboard", views.client_dashboard, name="client_dashboard"),
    path("payments", views.client_payments, name="client_payments"),
    path("memberships", views.client_memberships, name="client_memberships"),
    # provider
    path("provider/referral-link", views.get_referral_link, name="get_referral_link"),
    path("provider/patients", views.get_provider_patients, name="get_provider_patients"),
    # pricing
    path("pricing/tiers", views.get_all_pricing_tiers, name="get_all_pricing_tiers"),
    path("pricing/tiers/<int:kit_id>", views.get_kit_pricing_tiers, name="get_kit_pricing_tiers"),
]

