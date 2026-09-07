"""Check module removal in a dedicated local test database."""

if env.cr.dbname != "lettermint_lifecycle":
    raise RuntimeError("Use only the lettermint_lifecycle test database.")
partner = env["res.partner"].create({"name": "Keep business record"})
server = env["ir.mail_server"].create(
    {
        "name": "Keep API server",
        "smtp_authentication": "lettermint",
        "lettermint_token": "test-token",
        "lettermint_consent": True,
    }
)
template = env["mail.template"].create(
    {
        "name": "Keep template",
        "model_id": env.ref("base.model_res_partner").id,
        "mail_server_id": server.id,
        "subject": "Test",
        "body_html": "<p>Test</p>",
    }
)
partner_id, server_id, template_id = partner.id, server.id, template.id
env.cr.commit()
env["ir.module.module"].search(
    [("name", "in", ["lettermint_mail", "lettermint_mass_mailing"])]
).button_immediate_uninstall()
env.cr.execute(
    "SELECT active, smtp_authentication, smtp_host FROM ir_mail_server WHERE id = %s", [server_id]
)
assert env.cr.fetchone() == (False, "login", None)
env.cr.execute("SELECT id FROM res_partner WHERE id = %s", [partner_id])
assert env.cr.fetchone() == (partner_id,)
env.cr.execute("SELECT mail_server_id FROM mail_template WHERE id = %s", [template_id])
assert env.cr.fetchone() == (server_id,)
print("PASS: removal archives the API server and preserves the template and business record")
