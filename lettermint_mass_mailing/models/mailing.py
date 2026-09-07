from odoo import api, fields, models


class Mailing(models.Model):
    _inherit = "mailing.mailing"

    lettermint_api_server = fields.Boolean(compute="_compute_lettermint_api_server")

    @api.depends("mail_server_id.smtp_authentication")
    def _compute_lettermint_api_server(self):
        for mailing in self:
            mailing.lettermint_api_server = (
                mailing.mail_server_id.smtp_authentication == "lettermint"
            )
