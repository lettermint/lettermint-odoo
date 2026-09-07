import json
from email.message import EmailMessage
from unittest.mock import Mock, patch

import requests

from odoo.tests import TransactionCase, tagged
from ..transport import ApiSession, DeliveryError, prepare_payload


@tagged("post_install", "-at_install")
class TestTransport(TransactionCase):
    def message(self):
        message = EmailMessage()
        message["From"] = "Sender <sender@example.com>"
        message["To"] = "Reader <reader@example.com>"
        message["Message-ID"] = "<test@example.com>"
        message["Subject"] = "Test message"
        message.set_content("Plain text body")
        return message

    def session(self):
        return ApiSession(
            "secret-test-token", "outgoing", "example.com", "sender@example.com", "test-db", 1
        )

    def test_recipients_and_bcc(self):
        msg = self.message()
        msg["Cc"] = "copy@example.com, skipped@example.com"
        msg["Bcc"] = "hidden@example.com"
        msg["Reply-To"] = "replies@example.com"
        payload = prepare_payload(
            msg, ["reader@example.com", "copy@example.com", "hidden@example.com"], "route"
        )
        self.assertEqual(payload["to"], ["Reader <reader@example.com>"])
        self.assertEqual(payload["cc"], ["copy@example.com"])
        self.assertEqual(payload["bcc"], ["hidden@example.com"])
        self.assertEqual(payload["reply_to"], ["replies@example.com"])
        self.assertNotIn("skipped@example.com", json.dumps(payload))
        self.assertNotIn("Bcc", payload["headers"])

    def test_no_bcc_exposure(self):
        msg = self.message()
        with self.assertRaises(DeliveryError):
            prepare_payload(msg, ["hidden@example.com"], "")

    def test_html_pdf_inline_and_thread_headers(self):
        msg = self.message()
        msg["References"] = "<parent@example.com>"
        msg["In-Reply-To"] = "<parent@example.com>"
        msg.add_alternative('<p>Hello <img src="cid:logo@example.com"></p>', subtype="html")
        msg.get_payload()[1].add_related(
            b"PNG", maintype="image", subtype="png", cid="<logo@example.com>", filename="logo.png"
        )
        msg.add_attachment(
            b"%PDF-test", maintype="application", subtype="pdf", filename="invoice.pdf"
        )
        payload = prepare_payload(msg, ["reader@example.com"], "")
        self.assertIn("cid:logo@example.com", payload["html"])
        self.assertEqual(payload["headers"]["X-LM-Preserve-Message-ID"], "true")
        self.assertEqual(payload["headers"]["References"], "<parent@example.com>")
        self.assertEqual(len(payload["attachments"]), 2)
        self.assertEqual(payload["attachments"][0]["content_id"], "logo@example.com")

    def test_campaign_keeps_links_and_disables_double_tracking(self):
        msg = self.message()
        msg["X-Lettermint-Odoo-Campaign"] = "true"
        msg["List-Unsubscribe"] = "<https://odoo.example/unsubscribe/token>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        payload = prepare_payload(msg, ["reader@example.com"], "")
        self.assertEqual(payload["settings"], {"track_opens": False, "track_clicks": False})
        self.assertEqual(payload["headers"]["List-Unsubscribe"], msg["List-Unsubscribe"])
        self.assertNotIn("X-Lettermint-Odoo-Campaign", payload["headers"])

    def test_retry_stable_key_and_payload(self):
        msg = self.message()
        session = self.session()
        response = Mock(status_code=202)
        response.json.return_value = {"message_id": "accepted-id"}
        with patch(
            "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
        ) as request:
            session.send_message(msg, "bounce@example.com", ["reader@example.com"])
            first = request.call_args.kwargs
            msg["Date"] = "Mon, 07 Sep 2026 12:00:00 +0000"
            session.send_message(msg, "bounce@example.com", ["reader@example.com"])
            second = request.call_args.kwargs
        self.assertEqual(first["headers"]["Idempotency-Key"], second["headers"]["Idempotency-Key"])
        self.assertEqual(first["data"], second["data"])
        self.assertFalse(first["allow_redirects"])
        self.assertEqual(first["timeout"], (10, 60))

    def test_followers_get_distinct_keys(self):
        session = self.session()
        msg = self.message()
        response = Mock(status_code=202)
        response.json.return_value = {"message_id": "accepted-id"}
        with patch(
            "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
        ) as request:
            session.send_message(msg, "sender@example.com", ["reader@example.com"])
            first = request.call_args.kwargs["headers"]["Idempotency-Key"]
            msg.replace_header("To", "other@example.com")
            session.send_message(msg, "sender@example.com", ["other@example.com"])
            self.assertNotEqual(first, request.call_args.kwargs["headers"]["Idempotency-Key"])

    def test_http_errors_are_redacted(self):
        for status in (301, 401, 403, 409, 422, 429, 500):
            with self.subTest(status=status):
                response = Mock(status_code=status, text="secret-test-token private body")
                with patch(
                    "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
                ):
                    with self.assertRaises(DeliveryError) as error:
                        self.session().send_message(self.message(), "", ["reader@example.com"])
                self.assertIn(str(status), str(error.exception))
                self.assertNotIn("secret", str(error.exception))
                response.close.assert_called_once()

    def test_network_error_is_redacted(self):
        with patch(
            "odoo.addons.lettermint_mail.transport.requests.request",
            side_effect=requests.Timeout("secret-test-token"),
        ):
            with self.assertRaises(DeliveryError) as error:
                self.session().ping()
        self.assertNotIn("secret", str(error.exception))

    def test_invalid_success_response(self):
        response = Mock(status_code=202)
        for value in ({}, [], {"message_id": None}):
            response.json.return_value = value
            with patch(
                "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
            ):
                with self.assertRaises(DeliveryError):
                    self.session().send_message(self.message(), "", ["reader@example.com"])

    def test_attached_email_is_not_used_as_body(self):
        msg = self.message()
        attached = self.message()
        attached.replace_header("Subject", "Attached message")
        msg.add_attachment(attached, filename="original.eml")
        payload = prepare_payload(msg, ["reader@example.com"], "")
        self.assertEqual(len(payload["attachments"]), 1)
        self.assertEqual(payload["attachments"][0]["content_type"], "message/rfc822")
        self.assertEqual(payload["text"], "Plain text body\n")

    def test_duplicate_custom_headers_fail(self):
        msg = self.message()
        msg["X-Custom"] = "one"
        msg["X-Custom"] = "two"
        with self.assertRaises(DeliveryError):
            prepare_payload(msg, ["reader@example.com"], "")
