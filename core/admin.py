from django.contrib import admin
from django.db import transaction
from .models import (
    TestKit, Order, KitBarcodeAssignment, DeliveryEvent, ShippingInfo, PaymentInfo, BillingAddress, Purchase, ShippingAddress,
    DietLog, ExerciseLog,
    Biomarker, BiomarkerTest, BiomarkerResult,
)


class DeliveryEventInline(admin.TabularInline):
    model = DeliveryEvent
    extra = 0
    readonly_fields = ("timestamp",)


class BillingAddressInline(admin.StackedInline):
    model = BillingAddress
    extra = 0


@admin.register(ShippingInfo)
class ShippingInfoAdmin(admin.ModelAdmin):
    list_display = ("order", "tracking_number", "date_shipped", "created_at")
    search_fields = ("order__order_number", "tracking_number")
    list_filter = ("date_shipped",)


@admin.register(TestKit)
class TestKitAdmin(admin.ModelAdmin):
    list_display = ("name", "biomarker_count", "price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "client", "test_kit", "status", "tracking_number", "order_date")
    list_filter = ("status",)
    search_fields = ("order_number", "tracking_number")
    inlines = [DeliveryEventInline]
    actions = [
        "mark_as_confirmed",
        "mark_as_shipped",
        "mark_as_in_transit",
        "mark_as_out_for_delivery",
        "mark_as_delivered",
        "mark_as_cancelled",
    ]


@admin.register(KitBarcodeAssignment)
class KitBarcodeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("barcode_number", "order_number", "client", "order", "test_kit", "created_at")
    search_fields = ("barcode_number", "order_number", "client__email", "order__order_number", "test_kit__name")
    list_filter = ("test_kit",)
    exclude = ("client",)


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("client", "label", "street_address", "city", "state", "zip_code", "country", "is_default")
    search_fields = ("client__email", "street_address", "city", "zip_code")
    list_filter = ("is_default",)

    def _set_status_with_event(self, request, queryset, status, title, description, event_type=None, completed=False):
        event_type = event_type or status
        updated = 0

        with transaction.atomic():
            for order in queryset:
                order.status = status
                order.save(update_fields=["status", "updated_at"])

                DeliveryEvent.objects.create(
                    order=order,
                    event_type=event_type,
                    title=title,
                    description=description,
                    is_completed=completed,
                )
                order.delivery_events.exclude(event_type=event_type).update(is_completed=True)
                updated += 1

        self.message_user(request, f"Updated {updated} order(s) to {title.lower()}.")

    @admin.action(description="Mark selected orders as confirmed")
    def mark_as_confirmed(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "CONFIRMED",
            "Order Confirmed",
            "Your order has been confirmed",
            event_type="ORDER_PLACED",
            completed=True,
        )

    @admin.action(description="Mark selected orders as shipped")
    def mark_as_shipped(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "SHIPPED",
            "Shipped",
            "Your order has shipped",
            completed=True,
        )

    @admin.action(description="Mark selected orders as in transit")
    def mark_as_in_transit(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "IN_TRANSIT",
            "In Transit",
            "Your order is in transit",
            completed=True,
        )

    @admin.action(description="Mark selected orders as out for delivery")
    def mark_as_out_for_delivery(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "OUT_FOR_DELIVERY",
            "Out for Delivery",
            "Your order is out for delivery",
            completed=True,
        )

    @admin.action(description="Mark selected orders as delivered")
    def mark_as_delivered(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "DELIVERED",
            "Delivered",
            "Your order has been delivered",
            completed=True,
        )

    @admin.action(description="Mark selected orders as cancelled")
    def mark_as_cancelled(self, request, queryset):
        self._set_status_with_event(
            request,
            queryset,
            "CANCELLED",
            "Order Cancelled",
            "Your order has been cancelled",
            event_type="ORDER_PLACED",
            completed=False,
        )


@admin.register(DeliveryEvent)
class DeliveryEventAdmin(admin.ModelAdmin):
    list_display = ("order", "event_type", "title", "is_completed", "timestamp")
    list_filter = ("event_type", "is_completed")


@admin.register(DietLog)
class DietLogAdmin(admin.ModelAdmin):
    list_display = ("client", "created_at")
    list_filter = ("created_at",)
    search_fields = ("client__email", "client__first_name", "client__last_name")


@admin.register(ExerciseLog)
class ExerciseLogAdmin(admin.ModelAdmin):
    list_display = ("client", "created_at")
    list_filter = ("created_at",)
    search_fields = ("client__email", "client__first_name", "client__last_name")


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

