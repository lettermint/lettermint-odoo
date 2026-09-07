import json
from unittest.mock import Mock, patch
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailing(TransactionCase):
    def test_campaign_pipeline_preserves_unsubscribe(self):
        server = self.env["ir.mail_server"].create(
            {
                "name": "Campaign API",
                "smtp_authentication": "lettermint",
                "from_filter": "example.com",
                "lettermint_token": "campaign-test-token",
                "lettermint_consent": True,
                "lettermint_route": "broadcast",
            }
        )
        contact = self.env["mailing.contact"].create(
            {"name": "Reader", "email": "reader@example.com"}
        )
        mailing = self.env["mailing.mailing"].create(
            {
                "subject": "Campaign test",
                "email_from": "sender@example.com",
                "mailing_model_id": self.env.ref("mass_mailing.model_mailing_list").id,
                "body_html": "<p>Campaign content</p>",
                "mail_server_id": server.id,
            }
        )
        mail = self.env["mail.mail"].create(
            {
                "subject": mailing.subject,
                "email_from": mailing.email_from,
                "email_to": contact.email,
                "body_html": f'<p>Campaign <a href="{mailing.get_base_url()}/unsubscribe_from_list">Unsubscribe</a></p>',
                "mailing_id": mailing.id,
                "model": "mailing.contact",
                "res_id": contact.id,
                "mail_server_id": server.id,
                "auto_delete": False,
            }
        )
        response = Mock(status_code=202)
        response.json.return_value = {"message_id": "campaign-provider-id"}
        with (
            patch("odoo.modules.module.current_test", False),
            patch(
                "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
            ) as request,
        ):
            mail.send(raise_exception=True)
        payload = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(mail.state, "sent")
        self.assertEqual(payload["route"], "broadcast")
        self.assertEqual(payload["headers"]["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertIn("unsubscribe", payload["headers"]["List-Unsubscribe"])
        self.assertNotIn("/unsubscribe_from_list", payload["html"])
        self.assertEqual(payload["settings"], {"track_opens": False, "track_clicks": False})

    def test_campaign_excludes_blacklisted_and_opted_out_contacts(self):
        server = self.env["ir.mail_server"].create(
            {
                "name": "Campaign API",
                "smtp_authentication": "lettermint",
                "from_filter": "example.com",
                "lettermint_token": "campaign-test-token",
                "lettermint_consent": True,
            }
        )
        mailing_list = self.env["mailing.list"].create({"name": "Test list"})
        contacts = self.env["mailing.contact"].create(
            [
                {"name": name, "email": email, "list_ids": [(4, mailing_list.id)]}
                for name, email in [
                    ("Allowed", "allowed@example.com"),
                    ("Blocked", "blocked@example.com"),
                    ("Opted out", "out@example.com"),
                ]
            ]
        )
        self.env["mail.blacklist"].create({"email": "blocked@example.com"})
        subscription = self.env["mailing.subscription"].search(
            [("contact_id", "=", contacts[2].id), ("list_id", "=", mailing_list.id)]
        )
        subscription.opt_out = True
        mailing = self.env["mailing.mailing"].create(
            {
                "subject": "Full campaign test",
                "email_from": "sender@example.com",
                "mailing_model_id": self.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(4, mailing_list.id)],
                "mail_server_id": server.id,
                "body_html": "<p>Hello campaign reader</p>",
                "keep_archives": True,
            }
        )
        # Keep the real composer and exclusion handling; defer delivery until
        # after the composer so Odoo's test transaction is not auto-committed.
        with patch.object(type(self.env["mail.mail"]), "send", return_value=True):
            mailing.action_send_mail()
        queued = self.env["mail.mail"].search(
            [("mailing_id", "=", mailing.id), ("state", "=", "outgoing")]
        )
        self.assertTrue(queued)
        response = Mock(status_code=202)
        response.json.return_value = {"message_id": "campaign-id"}
        with (
            patch("odoo.modules.module.current_test", False),
            patch(
                "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
            ) as request,
        ):
            queued.send(raise_exception=True)
        recipients = [
            email
            for call in request.call_args_list
            for email in json.loads(call.kwargs["data"])["to"]
        ]
        self.assertEqual(len(recipients), 1, recipients)
        self.assertIn("allowed@example.com", recipients[0])
