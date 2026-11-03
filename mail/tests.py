from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendEmailTests(TestCase):
    def post(self, **data):
        return self.client.post(reverse("send-email"), data)

    def test_message_text_is_included_in_the_email(self):
        response = self.post(name="Ada Lovelace", email="ada@example.com", message="I'd like pricing for 20 kits.")

        self.assertContains(response, "form-response success")
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, "Website: Inquiry from Ada Lovelace")
        self.assertIn("I'd like pricing for 20 kits.", sent.body)
        self.assertIn("ada@example.com", sent.body)
        self.assertIn("Ada Lovelace", sent.body)
        self.assertEqual(sent.reply_to, ["ada@example.com"])

    def test_newline_in_name_does_not_break_the_send(self):
        response = self.post(name="Ada\nLovelace", email="ada@example.com", message="Hello")

        self.assertContains(response, "form-response success")
        self.assertEqual(mail.outbox[0].subject, "Website: Inquiry from Ada Lovelace")

    def test_missing_fields_send_nothing(self):
        response = self.post(name="Ada", email="ada@example.com", message="")

        self.assertContains(response, "Information is missing")
        self.assertEqual(len(mail.outbox), 0)
