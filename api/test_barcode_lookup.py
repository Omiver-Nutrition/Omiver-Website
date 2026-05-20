import uuid

from django.test import TestCase

from core.models import Client, KitBarcodeAssignment, Order, TestKit


class BarcodeLookupTests(TestCase):
    def test_lookup_not_found(self):
        resp = self.client.get('/api/barcode/lookup', {'barcode': 'NOTFOUND'})
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.json().get('found'))

    def test_lookup_found(self):
        kit = TestKit.objects.create(name='Unit Test Kit', biomarker_count=0, price=0)
        client_obj = Client.objects.create(email='test+barcode@example.com', first_name='Barcode', last_name='Tester')
        order = Order.objects.create(
            client=client_obj,
            test_kit=kit,
            order_number='UT' + uuid.uuid4().hex[:10],
            quantity=1,
            status='PENDING',
        )
        KitBarcodeAssignment.objects.create(
            client=client_obj,
            order=order,
            test_kit=kit,
            barcode_number='TEST123',
        )

        resp = self.client.get('/api/barcode/lookup', {'barcode': 'TEST123'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('found'))
        self.assertEqual(data.get('barcode'), 'TEST123')
        self.assertEqual(data.get('client_id'), client_obj.id)
        self.assertEqual(data.get('order_id'), order.id)
        self.assertEqual(data.get('test_kit'), kit.name)