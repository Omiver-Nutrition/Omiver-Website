from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db import transaction
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    Client, TestKit, Order, KitBarcodeAssignment, DeliveryEvent, ShippingInfo, PaymentInfo, BillingAddress, Purchase, ShippingAddress,
    DietLog, ExerciseLog,
    Biomarker, BiomarkerTest, BiomarkerResult, KitCollection, KitResult,
)


class DeliveryEventInline(admin.TabularInline):
    model = DeliveryEvent
    extra = 0
    readonly_fields = ("timestamp",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "first_name", "last_name", "type", "created_at")
    search_fields = ("email", "first_name", "last_name", "referral_code")
    list_filter = ("type", "created_at")
    raw_id_fields = ("user", "referred_by")


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
    search_fields = ("name",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "client", "test_kit", "status", "tracking_number", "order_date")
    list_filter = ("status",)
    search_fields = ("order_number", "tracking_number")
    raw_id_fields = ("client",)
    inlines = [DeliveryEventInline]
    actions = [
        "mark_as_confirmed",
        "mark_as_shipped",
        "mark_as_in_transit",
        "mark_as_out_for_delivery",
        "mark_as_delivered",
        "mark_as_cancelled",
    ]

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


@admin.register(KitBarcodeAssignment)
class KitBarcodeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("barcode_number", "client", "order", "test_kit", "collected_at", "mark_collected_link", "created_at")
    search_fields = ("barcode_number", "client__email", "order__order_number", "test_kit__name")
    list_filter = ("test_kit",)
    raw_id_fields = ("client", "order")
    autocomplete_fields = ("test_kit",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="core_kitbarcodeassignment_import_csv",
            ),
            path(
                "<int:assignment_id>/mark-collected/",
                self.admin_site.admin_view(self.mark_collected_view),
                name="core_kitbarcodeassignment_mark_collected",
            ),
        ]
        return custom_urls + urls

    def mark_collected_link(self, obj):
        if obj.collected_at:
            return obj.collected_at.strftime("%Y-%m-%d %H:%M:%S")
        url = reverse("admin:core_kitbarcodeassignment_mark_collected", args=[obj.id])
        return format_html('<a class="button" href="{}">Sample Collected</a>', url)

    mark_collected_link.short_description = "Sample Collected"

    def mark_collected_view(self, request, assignment_id):
        assignment = self.get_queryset(request).filter(pk=assignment_id).first()
        if assignment is None:
            self.message_user(request, "Barcode assignment not found.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:core_kitbarcodeassignment_changelist"))

        assignment.collected_at = timezone.now()
        assignment.save(update_fields=["collected_at", "updated_at"])
        self.message_user(request, f"Marked {assignment.barcode_number} as collected.", level=messages.SUCCESS)
        return HttpResponseRedirect(reverse("admin:core_kitbarcodeassignment_changelist"))

    def import_csv_view(self, request):
        import csv
        import io
        from django.utils.dateparse import parse_datetime
        from api.ai_utils import generate_ai_recommendation_draft
        from django.template.response import TemplateResponse

        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "No CSV file selected.", level=messages.ERROR)
                return HttpResponseRedirect(reverse("admin:core_kitbarcodeassignment_changelist"))

            try:
                # Read file as text
                file_data = csv_file.read().decode("utf-8")
                csv_reader = csv.DictReader(io.StringIO(file_data))
                
                # Check for required headers
                headers = [h.strip().lower() for h in csv_reader.fieldnames] if csv_reader.fieldnames else []
                required = ["barcode_number", "biomarker_name", "value", "recorded_at"]
                if not all(r in headers for r in required):
                    self.message_user(
                        request, 
                        f"Invalid CSV format. Required headers: {', '.join(required)}. Found: {', '.join(headers)}", 
                        level=messages.ERROR
                    )
                    return HttpResponseRedirect(reverse("admin:core_kitbarcodeassignment_changelist"))

                imported_rows = 0
                tests_to_trigger = []
                barcodes_to_finalize = set()

                # Group values in memory by (client, recorded_at)
                grouped_data = {}

                for row_idx, row in enumerate(csv_reader, start=1):
                    # Handle case-insensitive header mapping
                    row_clean = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}
                    
                    barcode = row_clean.get("barcode_number")
                    biomarker_name = row_clean.get("biomarker_name")
                    value_str = row_clean.get("value")
                    recorded_at_str = row_clean.get("recorded_at")

                    if not barcode or not biomarker_name or not value_str or not recorded_at_str:
                        # Skip empty rows or log warning
                        continue

                    # 1. Look up barcode assignment
                    try:
                        assignment = KitBarcodeAssignment.objects.select_related("client").get(barcode_number=barcode)
                    except KitBarcodeAssignment.DoesNotExist:
                        self.message_user(request, f"Row {row_idx}: Barcode '{barcode}' not found in Omiver system. Skipped.", level=messages.WARNING)
                        continue

                    client = assignment.client
                    if client:
                        barcodes_to_finalize.add(barcode)

                    # 2. Parse recorded_at
                    recorded_at = parse_datetime(recorded_at_str)
                    if not recorded_at:
                        self.message_user(request, f"Row {row_idx}: Invalid date format '{recorded_at_str}'. Skipped.", level=messages.WARNING)
                        continue

                    # 3. Parse value
                    try:
                        value = float(value_str)
                    except ValueError:
                        self.message_user(request, f"Row {row_idx}: Invalid numeric value '{value_str}'. Skipped.", level=messages.WARNING)
                        continue

                    # Group key
                    key = (client.id, recorded_at)
                    if key not in grouped_data:
                        grouped_data[key] = {
                            "client": client,
                            "recorded_at": recorded_at,
                            "results": []
                        }
                    
                    grouped_data[key]["results"].append((biomarker_name, value))

                # Now process each group transactionally
                tests_created = 0
                results_created = 0

                for (client_id, recorded_at), info in grouped_data.items():
                    client = info["client"]
                    recorded_at = info["recorded_at"]
                    
                    with transaction.atomic():
                        # Find or create BiomarkerTest run
                        test, created = BiomarkerTest.objects.get_or_create(
                            client=client,
                            recorded_at=recorded_at
                        )
                        if created:
                            tests_created += 1

                        for bm_name, val in info["results"]:
                            # Look up or create Biomarker
                            bm = Biomarker.objects.filter(name__iexact=bm_name).first()
                            if not bm:
                                bm = Biomarker.objects.create(
                                    name=bm_name,
                                    category="OTHER",
                                    range_min=0.0,
                                    range_max=100.0,
                                    optimal_min=20.0,
                                    optimal_max=80.0,
                                    unit="units"
                                )

                            # Create or update BiomarkerResult
                            BiomarkerResult.objects.update_or_create(
                                test=test,
                                biomarker=bm,
                                defaults={"value": val}
                            )
                            results_created += 1

                        tests_to_trigger.append(test.id)

                # 4. Finalize the associated kit collections, orders, and kit results
                for barcode in barcodes_to_finalize:
                    assignment = KitBarcodeAssignment.objects.filter(barcode_number=barcode).first()
                    if assignment:
                        order = getattr(assignment, "order", None)
                        # Find or create KitCollection
                        collection, _ = KitCollection.objects.get_or_create(
                            kit_barcode=barcode,
                            defaults={
                                "user": assignment.client,
                                "order": order,
                                "status": "FINISHED",
                            }
                        )
                        if collection.status != "FINISHED":
                            collection.status = "FINISHED"
                            collection.save(update_fields=["status", "updated_at"])

                        # Update Order status
                        if order:
                            order.status = "FINISHED"
                            order.save(update_fields=["status", "updated_at"])

                        # Create or update KitResult
                        KitResult.objects.update_or_create(
                            kit_barcode=barcode,
                            defaults={"result_info": f"Imported results successfully."}
                        )

                # 5. Trigger AI recommendation drafts for the imported tests!
                triggered_count = 0
                for tid in tests_to_trigger:
                    rec = generate_ai_recommendation_draft(tid)
                    if rec:
                        triggered_count += 1

                self.message_user(
                    request,
                    f"Successfully processed CSV. Created/Updated {tests_created} biomarker tests with {results_created} biomarker results, and successfully generated {triggered_count} AI recommendation drafts!",
                    level=messages.SUCCESS
                )

            except Exception as e:
                self.message_user(request, f"Failed to process CSV file: {e}", level=messages.ERROR)

            return HttpResponseRedirect(reverse("admin:core_kitbarcodeassignment_changelist"))

        # GET request: render file upload template
        context = self.admin_site.each_context(request)
        context["title"] = "Import TASSO CSV Results"
        return TemplateResponse(request, "admin/core/kitbarcodeassignment/import_csv.html", context)


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("client", "label", "street_address", "city", "state", "zip_code", "country", "is_default")
    search_fields = ("client__email", "street_address", "city", "zip_code")
    list_filter = ("is_default",)


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


@admin.register(KitCollection)
class KitCollectionAdmin(admin.ModelAdmin):
    list_display = ("kit_barcode", "user", "order", "status", "collected_at", "created_at")
    list_filter = ("status",)
    search_fields = ("kit_barcode", "user__email", "order__order_number")


@admin.register(KitResult)
class KitResultAdmin(admin.ModelAdmin):
    list_display = ("kit_barcode", "created_at")
    search_fields = ("kit_barcode",)

