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
        assignment = KitBarcodeAssignment.objects.create(
            client=client_obj,
            test_kit=kit,
            barcode_number='TEST123',
        )
        order.barcode_assignment = assignment
        order.save()

        resp = self.client.get('/api/barcode/lookup', {'barcode': 'TEST123'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('found'))
        self.assertEqual(data.get('barcode'), 'TEST123')
        self.assertEqual(data.get('client_id'), client_obj.id)
        self.assertEqual(data.get('order_id'), order.id)
        self.assertEqual(data.get('test_kit'), kit.name)

    def test_link_unassigned_barcode(self):
        kit = TestKit.objects.create(name='Unit Test Kit', biomarker_count=0, price=0)
        client_obj = Client.objects.create(email='link+barcode@example.com', first_name='Link', last_name='Tester')
        order = Order.objects.create(
            client=client_obj,
            test_kit=kit,
            order_number='LINK' + uuid.uuid4().hex[:10],
            quantity=1,
            status='PENDING',
        )
        assignment = KitBarcodeAssignment.objects.create(
            client=None,
            test_kit=kit,
            barcode_number='TEST-LINK-123',
        )
        order.barcode_assignment = assignment
        order.save()

        resp = self.client.post('/api/barcode/link', {
            'barcode_number': 'TEST-LINK-123',
            'client_id': client_obj.id,
        }, content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('linked'))
        self.assertTrue(data.get('already_linked'))
        self.assertEqual(data.get('client_id'), client_obj.id)

        lookup = self.client.get('/api/barcode/lookup', {'barcode': 'TEST-LINK-123'})
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(lookup.json().get('client_id'), client_obj.id)

    def test_link_rejects_other_client(self):
        kit = TestKit.objects.create(name='Unit Test Kit', biomarker_count=0, price=0)
        owner = Client.objects.create(email='owner+barcode@example.com', first_name='Owner', last_name='Tester')
        other = Client.objects.create(email='other+barcode@example.com', first_name='Other', last_name='Tester')
        order = Order.objects.create(
            client=owner,
            test_kit=kit,
            order_number='OWN' + uuid.uuid4().hex[:10],
            quantity=1,
            status='PENDING',
        )
        assignment = KitBarcodeAssignment.objects.create(
            client=owner,
            test_kit=kit,
            barcode_number='TEST-LOCKED-123',
        )
        order.barcode_assignment = assignment
        order.save()

        resp = self.client.post('/api/barcode/link', {
            'barcode_number': 'TEST-LOCKED-123',
            'client_id': other.id,
        }, content_type='application/json')

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json().get('message'), 'Barcode is already linked to another client')

    def test_link_allows_same_client(self):
        kit = TestKit.objects.create(name='Unit Test Kit', biomarker_count=0, price=0)
        client_obj = Client.objects.create(email='same+barcode@example.com', first_name='Same', last_name='Tester')
        order = Order.objects.create(
            client=client_obj,
            test_kit=kit,
            order_number='SAME' + uuid.uuid4().hex[:10],
            quantity=1,
            status='PENDING',
        )
        assignment = KitBarcodeAssignment.objects.create(
            client=client_obj,
            test_kit=kit,
            barcode_number='TEST-SAME-123',
        )
        order.barcode_assignment = assignment
        order.save()

        resp = self.client.post('/api/barcode/link', {
            'barcode_number': 'TEST-SAME-123',
            'client_id': client_obj.id,
        }, content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('linked'))
        self.assertTrue(data.get('already_linked'))
        self.assertEqual(data.get('client_id'), client_obj.id)

    def test_create_assignment_from_order_code(self):
        kit = TestKit.objects.create(name='Unit Test Kit', biomarker_count=0, price=0)
        client_obj = Client.objects.create(email='assign+barcode@example.com', first_name='Assign', last_name='Tester')
        order = Order.objects.create(
            client=client_obj,
            test_kit=kit,
            order_number='ASSIGN' + uuid.uuid4().hex[:10],
            quantity=1,
            status='PENDING',
        )

        resp = self.client.post('/api/barcode/assign', {
            'kit_code': order.order_number,
            'barcode_number': 'TEST123',
        }, content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('created'))
        self.assertEqual(data.get('barcode_number'), 'TEST123')
        self.assertEqual(data.get('client_id'), client_obj.id)
        self.assertEqual(data.get('order_id'), order.id)
        self.assertEqual(data.get('test_kit_id'), kit.id)

        lookup = self.client.get('/api/barcode/lookup', {'barcode': 'TEST123'})
        self.assertEqual(lookup.status_code, 200)
        lookup_data = lookup.json()
        self.assertTrue(lookup_data.get('found'))
        self.assertEqual(lookup_data.get('order_id'), order.id)