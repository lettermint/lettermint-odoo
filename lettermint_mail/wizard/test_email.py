from odoo import _, fields, models, tools
from odoo.exceptions import AccessError, UserError


class TestEmail(models.TransientModel):
    _name = "lettermint.test.email"
    _description = "Send a Lettermint test email"

    mail_server_id = fields.Many2one("ir.mail_server", required=True, ondelete="cascade")
    email_from = fields.Char("From", required=True)
    email_to = fields.Char("Recipient", required=True)

    def action_send(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only administrators can send a test email."))
        if (
            self.mail_server_id.smtp_authentication != "lettermint"
            or not self.mail_server_id.active
        ):
            raise UserError(_("Select an active Lettermint API server."))
        if not tools.email_normalize(self.email_from) or not tools.email_normalize(self.email_to):
            raise UserError(_("Enter one valid sender and one valid recipient."))
        mail = self.env["mail.mail"].create(
            {
                "subject": "Lettermint connection test",
                "body_html": "<p>This is an Odoo delivery test.</p>",
                "email_from": self.email_from,
                "email_to": self.email_to,
                "mail_server_id": self.mail_server_id.id,
                "auto_delete": False,
            }
        )
        mail.send(raise_exception=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("Lettermint accepted the test email. Check the recipient inbox."),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
