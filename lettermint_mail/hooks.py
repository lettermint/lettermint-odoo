def uninstall_hook(env):
    # Keep server records and their business links. Disable API servers before
    # Odoo removes the custom fields and resets the authentication selection.
    env.cr.execute(
        "UPDATE ir_mail_server SET active = false, smtp_host = NULL, smtp_pass = NULL WHERE smtp_authentication = 'lettermint'"
    )
    env["ir.mail_server"].invalidate_model()
