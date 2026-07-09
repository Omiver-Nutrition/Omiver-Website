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
    path("barcode/lookup", views.lookup_barcode, name="lookup_barcode"),
    path("barcode/link", views.link_barcode_assignment, name="link_barcode_assignment"),
    path("barcode/unlink", views.unlink_barcode_assignment, name="unlink_barcode_assignment"),
    path("barcode/collect", views.mark_barcode_collected, name="mark_barcode_collected"),
    path("barcode/assign", views.create_barcode_assignment, name="create_barcode_assignment"),
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

    path("shipping-addresses", views.list_shipping_addresses, name="list_shipping_addresses"),
    path("shipping-address", views.default_shipping_address, name="default_shipping_address"),

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
    # recommendations & AI draft workflow
    path("recommendations", views.get_recommendations, name="get_recommendations"),
    path("recommendations/<int:pk>/feedback", views.submit_doctor_feedback_api, name="submit_doctor_feedback_api"),
    path("recommendations/<int:pk>/approve", views.approve_recommendation_api, name="approve_recommendation_api"),
    path("recommendations/generate", views.generate_recommendation_draft_api, name="generate_recommendation_draft_api"),
    # pricing
    path("pricing/tiers", views.get_all_pricing_tiers, name="get_all_pricing_tiers"),
    path("pricing/tiers/<int:kit_id>", views.get_kit_pricing_tiers, name="get_kit_pricing_tiers"),

    # commissions (removed)

    # KitCollection Endpoints
    path("collection/<int:order_id>", views.get_kit_collection, name="get_kit_collection"),
    path("collection/scan", views.collection_scan, name="collection_scan"),
    path("collection/log", views.collection_log, name="collection_log"),
    path("collection/ship", views.collection_ship_return, name="collection_ship_return"),

    # Vendor Endpoints
    path("vendor/receive", views.vendor_receive_kit, name="vendor_receive_kit"),
    path("vendor/finish", views.vendor_finish_kit, name="vendor_finish_kit"),
]

