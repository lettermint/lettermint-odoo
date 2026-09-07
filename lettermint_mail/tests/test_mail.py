import json
from unittest.mock import Mock, patch

from odoo import release
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

from ..hooks import uninstall_hook


@tagged("post_install", "-at_install")
class TestMail(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = cls.env["ir.mail_server"].create(
            {
                "name": "Lettermint test",
                "smtp_authentication": "lettermint",
                "lettermint_token": "test-token",
                "lettermint_consent": True,
                "lettermint_route": "outgoing",
                "from_filter": "example.com",
                "sequence": 1,
            }
        )

    def new_mail(self, **values):
        return self.env["mail.mail"].create(
            dict(
                {
                    "email_from": "sender@example.com",
                    "email_to": "reader@example.com",
                    "subject": "Odoo pipeline test",
                    "body_html": "<p>Hello from Odoo</p>",
                    "mail_server_id": self.server.id,
                    "auto_delete": False,
                },
                **values,
            )
        )

    def send(self, mail, status=202):
        response = Mock(status_code=status)
        response.json.return_value = {"message_id": "provider-id"}
        with (
            patch("odoo.modules.module.current_test", False),
            patch(
                "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
            ) as request,
        ):
            mail.send(raise_exception=True)
        return request

    def test_queue_preserves_odoo_message_id(self):
        mail = self.new_mail()
        original_id = mail.message_id
        request = self.send(mail)
        self.assertEqual(mail.state, "sent")
        self.assertEqual(mail.message_id, original_id)
        payload = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(payload["route"], "outgoing")
        self.assertEqual(payload["headers"]["Message-Id"], original_id)
        self.assertEqual(payload["headers"]["X-LM-Preserve-Message-ID"], "true")

    def test_queue_failure_is_visible(self):
        mail = self.new_mail()
        response = Mock(status_code=429)
        with (
            patch("odoo.modules.module.current_test", False),
            patch("odoo.addons.lettermint_mail.transport.requests.request", return_value=response),
        ):
            mail.send()
        self.assertEqual(mail.state, "exception")
        self.assertIn("429", mail.failure_reason)
        self.assertNotIn("test-token", mail.failure_reason)

    def test_retry_uses_same_idempotency_key(self):
        mail = self.new_mail()
        response = Mock(status_code=503)
        with (
            patch("odoo.modules.module.current_test", False),
            patch(
                "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
            ) as request,
        ):
            mail.send()
            key = request.call_args.kwargs["headers"]["Idempotency-Key"]
        mail.write({"state": "outgoing"})
        retried = self.send(mail)
        self.assertEqual(key, retried.call_args.kwargs["headers"]["Idempotency-Key"])

    def test_automatic_server_selection(self):
        request = self.send(self.new_mail(mail_server_id=False))
        self.assertEqual(json.loads(request.call_args.kwargs["data"])["route"], "outgoing")

    def test_no_network_during_odoo_tests(self):
        with patch("odoo.addons.lettermint_mail.transport.requests.request") as request:
            self.new_mail().send()
        request.assert_not_called()

    def test_disabled_server_does_not_fall_back(self):
        mail = self.new_mail()
        self.server.active = False
        with patch("odoo.addons.lettermint_mail.transport.requests.request") as request:
            with self.assertRaises(MailDeliveryException):
                self.send(mail)
        request.assert_not_called()

    def test_consent_required(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.server.lettermint_consent = False

    def test_token_access(self):
        user = self.env["res.users"].create(
            {
                "name": "Mail user",
                "login": "mail-test-user",
                "group_ids" if release.version_info[0] >= 19 else "groups_id": [
                    (6, 0, [self.env.ref("base.group_user").id])
                ],
            }
        )
        with self.assertRaises(AccessError):
            self.server.with_user(user).read(["lettermint_token"])
        with self.assertRaises(AccessError):
            self.server.with_user(user).test_smtp_connection()

    def test_ping_does_not_send_mail(self):
        response = Mock(status_code=200)
        with patch(
            "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
        ) as request:
            self.server.test_smtp_connection()
        self.assertEqual(request.call_args.args, ("GET", "https://api.lettermint.co/v1/ping"))

    def test_standard_smtp_is_unchanged(self):
        smtp_server = self.env["ir.mail_server"].create(
            {
                "name": "SMTP test",
                "smtp_host": "smtp.invalid",
                "from_filter": "example.com",
                "smtp_encryption": "none",
            }
        )
        connection = Mock()
        with (
            patch("odoo.modules.module.current_test", False),
            patch("smtplib.SMTP", return_value=connection),
            patch("odoo.addons.lettermint_mail.transport.requests.request") as request,
        ):
            self.new_mail(mail_server_id=smtp_server.id).send(raise_exception=True)
        connection.send_message.assert_called_once()
        request.assert_not_called()

    def test_uninstall_archives_only_api_servers(self):
        smtp_server = self.env["ir.mail_server"].create(
            {"name": "Keep SMTP", "smtp_host": "smtp.invalid"}
        )
        self.server.flush_recordset()
        uninstall_hook(self.env)
        self.assertFalse(self.server.active)
        self.assertTrue(smtp_server.active)
        self.assertTrue(self.server.exists())
