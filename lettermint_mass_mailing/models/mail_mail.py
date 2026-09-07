from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _prepare_outgoing_list(self, *args, **kwargs):
        outgoing = super()._prepare_outgoing_list(*args, **kwargs)
        server = kwargs.get("mail_server") or (args[0] if args else False) or self.mail_server_id
        if self.mailing_id and server and server.smtp_authentication == "lettermint":
            for values in outgoing:
                values["headers"] = dict(
                    values["headers"], **{"X-Lettermint-Odoo-Campaign": "true"}
                )
        return outgoing
