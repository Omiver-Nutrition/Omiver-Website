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
    Biomarker, BiomarkerTest, BiomarkerResult, KitCollection, BiomarkerReport,
)


class DeliveryEventInline(admin.TabularInline):
    model = DeliveryEvent
    extra = 0
    readonly_fields = ("timestamp",)


#@admin.register(Client)
#class ClientAdmin(admin.ModelAdmin):
#    list_display = ("id", "email", "first_name", "last_name", "type", "created_at")
#    search_fields = ("email", "first_name", "last_name", "referral_code")
#    list_filter = ("type", "created_at")
#    raw_id_fields = ("user", "referred_by")


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
    # `status` is a derived property now, so it cannot be used in list_filter
    # (admin.E116) and needs a display method to get a sortable-looking column.
    list_display = ("order_number", "client", "test_kit", "current_status", "tracking_number", "order_date")
    list_filter = ("delivery_events__event_type",)
    search_fields = ("order_number", "tracking_number")
    raw_id_fields = ("client",)
    inlines = [DeliveryEventInline]
    actions = [
        "mark_as_shipped",
        "mark_as_in_transit",
        "mark_as_out_for_delivery",
        "mark_as_delivered",
        "mark_as_sample_shipped",
        "mark_as_sample_delivered",
        "mark_as_cancelled",
    ]

    @admin.display(description="Status")
    def current_status(self, obj):
        return obj.get_status_display()

    def _record_event(self, request, queryset, event_type, title, description):
        updated = 0
        with transaction.atomic():
            for order in queryset:
                order.record_event(event_type, title=title, description=description)
                updated += 1

        self.message_user(request, f"Updated {updated} order(s) to {title.lower()}.")

    @admin.action(description="Mark selected orders as shipped to customer")
    def mark_as_shipped(self, request, queryset):
        self._record_event(request, queryset, "SHIPPED", "Shipped", "Your kit has shipped")

    @admin.action(description="Mark selected orders as in transit")
    def mark_as_in_transit(self, request, queryset):
        self._record_event(request, queryset, "IN_TRANSIT", "In Transit", "Your kit is in transit")

    @admin.action(description="Mark selected orders as out for delivery")
    def mark_as_out_for_delivery(self, request, queryset):
        self._record_event(request, queryset, "OUT_FOR_DELIVERY", "Out for Delivery", "Your kit is out for delivery")

    @admin.action(description="Mark selected orders as delivered to customer")
    def mark_as_delivered(self, request, queryset):
        self._record_event(request, queryset, "DELIVERED", "Delivered", "Your kit has been delivered")

    @admin.action(description="Mark selected orders as sample shipped to lab")
    def mark_as_sample_shipped(self, request, queryset):
        self._record_event(
            request, queryset, "SAMPLE_SHIPPED", "Sample Shipped",
            "Sample dropped off and in transit to laboratory",
        )

    @admin.action(description="Mark selected orders as sample received by lab")
    def mark_as_sample_delivered(self, request, queryset):
        self._record_event(
            request, queryset, "SAMPLE_DELIVERED", "Sample Delivered",
            "Your sample has arrived at the laboratory",
        )

    @admin.action(description="Mark selected orders as cancelled")
    def mark_as_cancelled(self, request, queryset):
        self._record_event(request, queryset, "CANCELLED", "Order Cancelled", "Your order has been cancelled")


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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="core_biomarkertest_import_csv",
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        import csv
        import io
        import re
        from datetime import datetime
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone
        from django.contrib import messages
        from django.shortcuts import reverse
        from django.http import HttpResponseRedirect
        from django.template.response import TemplateResponse
        from api.ai_utils import generate_ai_recommendation_draft

        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "No CSV file selected.", level=messages.ERROR)
                return HttpResponseRedirect(reverse("admin:core_biomarkertest_changelist"))

            try:
                file_data = csv_file.read().decode("utf-8")
                csv_reader = csv.DictReader(io.StringIO(file_data))
                headers = [h.strip().lower() for h in csv_reader.fieldnames] if csv_reader.fieldnames else []

                required_long_headers = ["ionidx", "ionmz", "iontopname"]
                is_long_format = all(h in headers for h in required_long_headers)
                is_wide_format = all(h in headers for h in ["barcode_number", "biomarker_name", "value", "recorded_at"])

                if not is_long_format and not is_wide_format:
                    self.message_user(
                        request,
                        f"Invalid CSV format. Expected either IONS long format or biomarker CSV with barcode_number, biomarker_name, value, recorded_at. Found: {', '.join(headers)}",
                        level=messages.ERROR,
                    )
                    return HttpResponseRedirect(reverse("admin:core_biomarkertest_changelist"))

                tests_to_trigger = []
                barcodes_to_finalize = set()
                grouped_data = {}

                if is_long_format:
                    import_time = timezone.now()
                    barcode_pattern = re.compile(r"^(?:Sample_[A-Za-z]+_)?(\d+)$")

                    for row_idx, row in enumerate(csv_reader, start=1):
                        row_clean = {k.strip(): v.strip() if v else "" for k, v in row.items() if k}
                        biomarker_name = row_clean.get("ionTopName") or row_clean.get("ionTopFormula")
                        if not biomarker_name:
                            continue

                        for header, value in row_clean.items():
                            if not header or not value:
                                continue
                            barcode_match = barcode_pattern.match(header.strip())
                            if not barcode_match:
                                continue
                            barcode = barcode_match.group(1)

                            try:
                                assignment = KitBarcodeAssignment.objects.select_related("client").get(barcode_number=barcode)
                            except KitBarcodeAssignment.DoesNotExist:
                                self.message_user(request, f"Row {row_idx}: Barcode '{barcode}' not found. Skipped biomarker '{biomarker_name}'.", level=messages.WARNING)
                                continue

                            try:
                                value_float = float(value)
                            except ValueError:
                                continue

                            client = assignment.client
                            barcodes_to_finalize.add(barcode)
                            key = (client.id, import_time)
                            if key not in grouped_data:
                                grouped_data[key] = {
                                    "client": client,
                                    "recorded_at": import_time,
                                    "results": [],
                                }
                            grouped_data[key]["results"].append((biomarker_name, value_float))
                else:
                    for row_idx, row in enumerate(csv_reader, start=1):
                        row_clean = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}
                        barcode = row_clean.get("barcode_number")
                        biomarker_name = row_clean.get("biomarker_name")
                        value_str = row_clean.get("value")
                        recorded_at_str = row_clean.get("recorded_at")

                        if not barcode or not biomarker_name or not value_str or not recorded_at_str:
                            continue

                        try:
                            assignment = KitBarcodeAssignment.objects.select_related("client").get(barcode_number=barcode)
                        except KitBarcodeAssignment.DoesNotExist:
                            self.message_user(request, f"Row {row_idx}: Barcode '{barcode}' not found in Omiver system. Skipped.", level=messages.WARNING)
                            continue

                        client = assignment.client
                        if client:
                            barcodes_to_finalize.add(barcode)

                        recorded_at = parse_datetime(recorded_at_str)
                        if not recorded_at:
                            self.message_user(request, f"Row {row_idx}: Invalid date format '{recorded_at_str}'. Skipped.", level=messages.WARNING)
                            continue

                        try:
                            value = float(value_str)
                        except ValueError:
                            self.message_user(request, f"Row {row_idx}: Invalid numeric value '{value_str}'. Skipped.", level=messages.WARNING)
                            continue

                        key = (client.id, recorded_at)
                        if key not in grouped_data:
                            grouped_data[key] = {
                                "client": client,
                                "recorded_at": recorded_at,
                                "results": [],
                            }
                        grouped_data[key]["results"].append((biomarker_name, value))

                tests_created = 0
                results_created = 0

                for (client_id, recorded_at), info in grouped_data.items():
                    client = info["client"]
                    recorded_at = info["recorded_at"]

                    with transaction.atomic():
                        test, created = BiomarkerTest.objects.get_or_create(
                            client=client,
                            recorded_at=recorded_at,
                        )
                        if created:
                            tests_created += 1

                        for bm_name, val in info["results"]:
                            bm = Biomarker.objects.filter(name__iexact=bm_name).first()
                            if not bm:
                                bm = Biomarker.objects.create(
                                    name=bm_name,
                                    category="OTHER",
                                    range_min=0.0,
                                    range_max=100.0,
                                    optimal_min=20.0,
                                    optimal_max=80.0,
                                    unit="units",
                                )

                            BiomarkerResult.objects.update_or_create(
                                test=test,
                                biomarker=bm,
                                defaults={"value": val},
                            )
                            results_created += 1

                        tests_to_trigger.append(test.id)

                for barcode in barcodes_to_finalize:
                    assignment = KitBarcodeAssignment.objects.filter(barcode_number=barcode).first()
                    if assignment:
                        order = getattr(assignment, "order", None)
                        collection, _ = KitCollection.objects.get_or_create(
                            kit_barcode=barcode,
                            defaults={
                                "user": assignment.client,
                                "order": order,
                                "status": "FINISHED",
                            },
                        )
                        if collection.status != "FINISHED":
                            collection.status = "FINISHED"
                            collection.save(update_fields=["status", "updated_at"])

                        if order and order.status != "SAMPLE_DELIVERED":
                            # Results exist for this barcode, so the lab has the sample.
                            order.record_event("SAMPLE_DELIVERED")

                triggered_count = 0
                for tid in tests_to_trigger:
                    rec = generate_ai_recommendation_draft(tid)
                    if rec:
                        triggered_count += 1

                self.message_user(
                    request,
                    f"Successfully processed CSV. Created/Updated {tests_created} biomarker tests with {results_created} biomarker results, and successfully generated {triggered_count} AI recommendation drafts!",
                    level=messages.SUCCESS,
                )

            except Exception as e:
                self.message_user(request, f"Failed to process CSV file: {e}", level=messages.ERROR)

            return HttpResponseRedirect(reverse("admin:core_biomarkertest_changelist"))
        context = self.admin_site.each_context(request)
        context["title"] = "Import TASSO CSV"
        return TemplateResponse(request, "admin/core/biomarkertest/import_csv.html", context)


@admin.register(BiomarkerResult)
class BiomarkerResultAdmin(admin.ModelAdmin):
    list_display = ("test", "biomarker", "value", "status")
    list_filter = ("status", "biomarker__category")


@admin.register(KitCollection)
class KitCollectionAdmin(admin.ModelAdmin):
    list_display = ("kit_barcode", "user", "order", "status", "collected_at", "created_at")
    list_filter = ("status",)
    search_fields = ("kit_barcode", "user__email", "order__order_number")


@admin.register(BiomarkerReport)
class BiomarkerReportAdmin(admin.ModelAdmin):
    list_display = ("primary_id", "client", "created_at")
    list_filter = ("created_at",)
    search_fields = ("client__email", "client__first_name", "client__last_name", "report")
