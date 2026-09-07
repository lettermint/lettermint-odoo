"""Run with odoo shell on the local demo database. Roll back all changes."""

import base64
import json
from email.message import EmailMessage
from unittest.mock import Mock, patch

if env.cr.dbname != "lettermint_demo":
    raise RuntimeError("Use only the local demo database.")
try:
    server = env["ir.mail_server"].create(
        {
            "name": "Business flow test",
            "smtp_authentication": "lettermint",
            "lettermint_token": "mock-token",
            "lettermint_consent": True,
            "from_filter": "example.invalid",
            "sequence": -100,
        }
    )
    response = Mock(status_code=202)
    response.json.return_value = {"message_id": "mock-accepted-id"}
    with (
        patch(
            "odoo.addons.lettermint_mail.transport.requests.request", return_value=response
        ) as request,
        patch("smtplib.SMTP", side_effect=AssertionError("Unexpected SMTP connection")),
        patch("smtplib.SMTP_SSL", side_effect=AssertionError("Unexpected SMTP connection")),
    ):
        invoice = env["account.move"].search([("ref", "=", "LM-DEMO")], limit=1)
        assert invoice, "Missing demo invoice"
        env["ir.config_parameter"].set_param("report.url", "http://odoo:8069")
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
            "account.account_invoices", res_ids=invoice.ids
        )
        assert pdf.startswith(b"%PDF"), "Invalid invoice PDF"
        attachment = env["ir.attachment"].create(
            {
                "name": "invoice.pdf",
                "datas": base64.b64encode(pdf),
                "mimetype": "application/pdf",
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )
        mail = env["mail.mail"].create(
            {
                "subject": "Invoice delivery test",
                "email_from": "sender@example.invalid",
                "email_to": "reader@example.invalid",
                "model": "account.move",
                "res_id": invoice.id,
                "body_html": "<p>Your invoice is attached.</p>",
                "attachment_ids": [(4, attachment.id)],
                "mail_server_id": server.id,
                "auto_delete": False,
            }
        )
        mail.send(raise_exception=True)
        payload = json.loads(request.call_args.kwargs["data"])
        assert mail.state == "sent"
        assert any(base64.b64decode(a["content"]) == pdf for a in payload["attachments"])
        print("PASS: real Odoo invoice PDF reaches the API payload unchanged")

        user = (
            env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Reset Test",
                    "login": "reset@example.invalid",
                    "email": "reset@example.invalid",
                }
            )
        )
        before = request.call_count
        user.action_reset_password()
        assert request.call_count == before + 1, "No reset email sent"
        payload = json.loads(request.call_args.kwargs["data"])
        assert "/web/reset_password" in payload["html"]
        print("PASS: Odoo password reset uses the API transport")

        # Use the RFC ID returned through Odoo, not the provider UUID.
        reply = EmailMessage()
        reply["From"] = "reader@example.invalid"
        reply["To"] = "sender@example.invalid"
        reply["Subject"] = "Re: Invoice delivery test"
        reply["Message-ID"] = "<invoice-reply@example.invalid>"
        reply["In-Reply-To"] = mail.message_id
        reply["References"] = mail.message_id
        reply.set_content("The invoice was received.")
        target_id = env["mail.thread"].message_process(None, reply.as_bytes())
        assert target_id == invoice.id
        assert (
            env["mail.message"].search_count(
                [
                    ("message_id", "=", "<invoice-reply@example.invalid>"),
                    ("model", "=", "account.move"),
                    ("res_id", "=", invoice.id),
                ]
            )
            == 1
        )
        print("PASS: an inbound reply reaches the original invoice")
finally:
    env.cr.rollback()
