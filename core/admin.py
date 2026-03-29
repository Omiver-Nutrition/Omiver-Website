from django.contrib import admin
from .models import (
    TestKit, Order, DeliveryEvent, PaymentInfo, BillingAddress, Purchase,
    Biomarker, BiomarkerTest, BiomarkerResult,
)


class DeliveryEventInline(admin.TabularInline):
    model = DeliveryEvent
    extra = 0
    readonly_fields = ("timestamp",)


class BillingAddressInline(admin.StackedInline):
    model = BillingAddress
    extra = 0


@admin.register(TestKit)
class TestKitAdmin(admin.ModelAdmin):
    list_display = ("name", "biomarker_count", "price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "client", "test_kit", "status", "tracking_number", "order_date")
    list_filter = ("status",)
    search_fields = ("order_number", "tracking_number")
    inlines = [DeliveryEventInline]


@admin.register(DeliveryEvent)
class DeliveryEventAdmin(admin.ModelAdmin):
    list_display = ("order", "event_type", "title", "is_completed", "timestamp")
    list_filter = ("event_type", "is_completed")


@admin.register(PaymentInfo)
class PaymentInfoAdmin(admin.ModelAdmin):
    list_display = ("client", "cardholder_name", "card_last_four", "card_brand", "amount", "payment_status", "created_at")
    list_filter = ("payment_status", "card_brand")
    inlines = [BillingAddressInline]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "test_kit", "status", "created_at")
    list_filter = ("status",)


class BiomarkerResultInline(admin.TabularInline):
    model = BiomarkerResult
    extra = 0
    autocomplete_fields = ["biomarker"]


@admin.register(Biomarker)
class BiomarkerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "range_min", "range_max", "unit")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(BiomarkerTest)
class BiomarkerTestAdmin(admin.ModelAdmin):
    list_display = ("client", "recorded_at", "created_at")
    list_filter = ("recorded_at",)
    inlines = [BiomarkerResultInline]


@admin.register(BiomarkerResult)
class BiomarkerResultAdmin(admin.ModelAdmin):
    list_display = ("test", "biomarker", "value", "status")
    list_filter = ("status", "biomarker__category")

