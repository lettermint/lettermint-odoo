from odoo import _, api, fields, models, modules, release
from odoo.exceptions import AccessError, UserError, ValidationError

from ..transport import ApiSession, DeliveryError


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    smtp_authentication = fields.Selection(
        selection_add=[("lettermint", "Lettermint API")], ondelete={"lettermint": "set default"}
    )
    lettermint_token = fields.Char("Project API token", groups="base.group_system", copy=False)
    lettermint_route = fields.Char(
        "Lettermint route",
        groups="base.group_system",
        help="Enter the route slug. Leave empty to use the project default outbound route.",
    )
    lettermint_consent = fields.Boolean(
        "Allow email data transfer",
        groups="base.group_system",
        copy=False,
        help="Allow sender and recipient addresses, message content, headers, and attachments to be sent to Lettermint.",
    )

    @api.constrains("smtp_authentication", "lettermint_token", "lettermint_consent", "active")
    def _check_lettermint_configuration(self):
        for server in self:
            if server.smtp_authentication == "lettermint" and server.active:
                if not server.lettermint_token or not server.lettermint_consent:
                    raise ValidationError(
                        _(
                            "Set the project API token and allow data transfer before you enable this server."
                        )
                    )

    def _lettermint_session(self, smtp_from=None):
        self.ensure_one()
        if not self.lettermint_consent or not self.lettermint_token:
            raise UserError(_("Set the project API token and allow data transfer first."))
        return ApiSession(
            self.lettermint_token,
            self.lettermint_route,
            self.from_filter,
            smtp_from,
            self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            self.id,
        )

    def _lettermint_connect(self, host, smtp_from, mail_server_id, allow_archived):
        server = self.sudo().browse(mail_server_id) if mail_server_id else self.browse()
        if not server and not host:
            server, smtp_from = self.sudo()._find_mail_server(smtp_from)
        if not server or server.smtp_authentication != "lettermint":
            return None
        if release.version_info[0] >= 19:
            self._check_forced_mail_server(server, allow_archived, smtp_from)
        elif not server.active and not allow_archived:
            raise UserError(_("This mail server is archived."))
        return server._lettermint_session(smtp_from)

    # Odoo renamed the connection method in 19. These explicit adapters keep
    # the signature and normal SMTP behavior of each supported version.
    if release.version_info[0] == 18:

        def connect(
            self,
            host=None,
            port=None,
            user=None,
            password=None,
            encryption=None,
            smtp_from=None,
            ssl_certificate=None,
            ssl_private_key=None,
            smtp_debug=False,
            mail_server_id=None,
            allow_archived=False,
        ):
            if modules.module.current_test:
                return None
            session = self._lettermint_connect(host, smtp_from, mail_server_id, allow_archived)
            if session:
                return session
            return super().connect(
                host,
                port,
                user,
                password,
                encryption,
                smtp_from,
                ssl_certificate,
                ssl_private_key,
                smtp_debug,
                mail_server_id,
                allow_archived,
            )
    else:

        def _connect__(
            self,
            host=None,
            port=None,
            user=None,
            password=None,
            encryption=None,
            smtp_from=None,
            ssl_certificate=None,
            ssl_private_key=None,
            smtp_debug=False,
            mail_server_id=None,
            allow_archived=False,
        ):
            if self._disable_send():
                return None
            session = self._lettermint_connect(host, smtp_from, mail_server_id, allow_archived)
            if session:
                return session
            return super()._connect__(
                host,
                port,
                user,
                password,
                encryption,
                smtp_from,
                ssl_certificate,
                ssl_private_key,
                smtp_debug,
                mail_server_id,
                allow_archived,
            )

    def test_smtp_connection(self, autodetect_max_email_size=False):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only administrators can test this connection."))
        if self.smtp_authentication != "lettermint":
            return super().test_smtp_connection(autodetect_max_email_size=autodetect_max_email_size)
        session = self._lettermint_session()
        try:
            session.ping()
        except DeliveryError as error:
            raise UserError(str(error)) from None
        finally:
            session.quit()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Lettermint"),
                "message": _(
                    "The API token is valid. Send a test email to check the sender and route."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_lettermint_test_email(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only administrators can send a test email."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Send a test email"),
            "res_model": "lettermint.test.email",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_mail_server_id": self.id,
                "default_email_from": self._get_test_email_from(),
            },
        }
