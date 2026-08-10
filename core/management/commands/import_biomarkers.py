import os
import csv
import math

import django
from django.core.management.base import BaseCommand

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'omiver_website.settings')
django.setup()

from collections import defaultdict
from statistics import median
from decimal import Decimal

from core.models import Biomarker, BiomarkerTest, BiomarkerResult, TestKit, Client, KitBarcodeAssignment


def to_decimal(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return Decimal(str(s[int(k)]))
    return Decimal(str(s[f])) * (Decimal(c) - Decimal(str(k))) + Decimal(str(s[c])) * (Decimal(str(k)) - Decimal(f))


class Command(BaseCommand):
    help = 'Import biomarker definitions and test results from ions_clean.csv'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', type=int, required=True, help='Client ID to associate tests with')
        parser.add_argument('--kit-id', type=int, required=True, help='TestKit ID to associate tests with')
        parser.add_argument('--clear', action='store_true', help='Clear existing biomarker tests for client before import')

    def handle(self, *args, **options):
        client_id = options['client_id']
        kit_id = options['kit_id']
        clear = options['clear']

        try:
            client = Client.objects.get(pk=client_id)
            kit = TestKit.objects.get(pk=kit_id)
        except (Client.DoesNotExist, TestKit.DoesNotExist) as e:
            self.stdout.write(self.style.ERROR(f'Invalid client or kit: {e}'))
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, '..', '..', '..', '..', 'ions_clean.csv'),
            os.path.join(base_dir, '..', '..', 'ions_clean.csv'),
            r'C:\project\omiver\ions_clean.csv',
        ]
        csv_path = next((p for p in candidates if os.path.exists(p)), None)

        if not csv_path or not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'ions_clean.csv not found at {csv_path}'))
            return

        rows = []
        sample_cols = []

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            sample_cols = [h for h in headers if h.startswith('Sample')]
            for row in reader:
                rows.append(row)

        # Aggregate per biomarker name
        agg = defaultdict(lambda: {
            'ionMz': None,
            'ionAverageInt': None,
            'ionTopFormula': None,
            'ionTopMod': None,
            'ionGapHits': None,
            'values': [],
        })

        for row in rows:
            name = (row.get('ionTopName') or '').strip()
            if not name:
                continue

            info = agg[name]
            info['ionMz'] = row.get('ionMz', info['ionMz'])
            info['ionAverageInt'] = row.get('ionAverageInt', info['ionAverageInt'])
            info['ionTopFormula'] = row.get('ionTopFormula', info['ionTopFormula'])
            info['ionTopMod'] = row.get('ionTopMod', info['ionTopMod'])
            info['ionGapHits'] = row.get('ionGapHits', info['ionGapHits'])

            for col in sample_cols:
                v = to_decimal(row.get(col))
                if v is not None:
                    info['values'].append(v)

        # Import biomarkers
        created_biomarkers = 0
        updated_biomarkers = 0

        for name, info in agg.items():
            values = info['values']
            if not values:
                continue

            avg = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
            q25 = percentile(values, 25)
            q75 = percentile(values, 75)
            median_v = median(values)

            additional = {
                'ionMz': float(to_decimal(info['ionMz'])) if to_decimal(info['ionMz']) is not None else None,
                'ionAverageInt': float(to_decimal(info['ionAverageInt'])) if to_decimal(info['ionAverageInt']) is not None else None,
                'ionTopFormula': info['ionTopFormula'],
                'ionTopMod': info['ionTopMod'],
                'ionGapHits': float(to_decimal(info['ionGapHits'])) if to_decimal(info['ionGapHits']) is not None else None,
                'sample_count': len(values),
                'values_median': float(median_v),
            }

            _, created_flag = Biomarker.objects.update_or_create(
                name=name,
                defaults={
                    'category': 'OTHER',
                    'range_min': min_v,
                    'range_max': max_v,
                    'optimal_min': q25,
                    'optimal_max': q75,
                    'average_value': avg,
                    'unit': '',
                    'additional_information': additional,
                },
            )
            created_biomarkers += int(created_flag)
            updated_biomarkers += int(not created_flag)

        # Clear existing tests if requested
        if clear:
            deleted_count, _ = BiomarkerTest.objects.filter(client=client).delete()
            self.stdout.write(self.style.SUCCESS(f'Cleared {deleted_count} existing tests for client {client_id}'))

        # Create biomarker tests - one per sample column
        created_tests = 0
        created_results = 0
        created_assignments = 0

        # Build a lookup for biomarker names -> ids
        biomarker_id_map = {bm.name: bm.id for bm in Biomarker.objects.all()}

        # Parse sample columns into barcode numbers
        for sample_col in sample_cols:
            # Extract barcode number from Sample_* headers (e.g. "Sample_A_21191288" -> "21191288")
            parts = sample_col.split('_')
            barcode_number = parts[-1] if parts else sample_col

            from django.utils import timezone
            recorded_at = timezone.now()

            # Find or create barcode assignment for this sample
            assignment, assignment_created = KitBarcodeAssignment.objects.get_or_create(
                barcode_number=barcode_number,
                defaults={
                    'client': client,
                    'test_kit': kit,
                },
            )
            if not assignment_created and assignment.client_id != client.id:
                assignment.client = client
                assignment.test_kit = kit
                assignment.save()
            created_assignments += int(assignment_created)

            # Build results data as JSON: [{biomarker_id, value}, ...]
            results_data = []
            for row in rows:
                name = (row.get('ionTopName') or '').strip()
                if not name or name not in biomarker_id_map:
                    continue

                value_str = row.get(sample_col)
                if value_str is None or value_str.strip() == '':
                    continue

                try:
                    value = float(value_str)
                except (ValueError, TypeError):
                    continue

                results_data.append({
                    'biomarker_id': biomarker_id_map[name],
                    'value': value,
                })

            # Create a single BiomarkerTest with data JSON format
            test = BiomarkerTest.objects.create(
                client=client,
                barcode_assignment=assignment,
                recorded_at=recorded_at,
                data=results_data,
            )
            created_tests += 1

            # Populate BiomarkerResult rows via bulk create
            results_to_create = []
            for item in results_data:
                try:
                    bm = Biomarker.objects.get(pk=item['biomarker_id'])
                except Biomarker.DoesNotExist:
                    continue

                value = item['value']
                status = 'NORMAL'
                if bm.optimal_min is not None and bm.optimal_max is not None:
                    if bm.optimal_min <= value <= bm.optimal_max:
                        status = 'OPTIMAL'
                    elif bm.range_min <= value <= bm.range_max:
                        status = 'NORMAL'
                    elif value < bm.range_min:
                        status = 'LOW'
                    else:
                        status = 'HIGH'
                else:
                    if bm.range_min <= value <= bm.range_max:
                        status = 'NORMAL'
                    elif value < bm.range_min:
                        status = 'LOW'
                    else:
                        status = 'HIGH'

                results_to_create.append(
                    BiomarkerResult(
                        test=test,
                        biomarker=bm,
                        value=value,
                        status=status,
                    )
                )
                created_results += 1

            BiomarkerResult.objects.bulk_create(results_to_create)

        self.stdout.write(self.style.SUCCESS(
            f'Imported {created_biomarkers} biomarkers, updated {updated_biomarkers} biomarkers, '
            f'created {created_assignments} barcode assignments, created {created_tests} tests, {created_results} results for client {client_id}'
        ))
