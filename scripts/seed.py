"""Run with odoo shell against the local demo database only."""

import os

if env.cr.dbname != "lettermint_demo":
    raise RuntimeError("Use only the local lettermint_demo database.")
password = os.environ.get("ODOO_DEMO_PASSWORD")
if not password:
    raise RuntimeError("Set ODOO_DEMO_PASSWORD in .env.")
env = env(context=dict(env.context, tracking_disable=True, mail_create_nosubscribe=True))
env.ref("base.user_admin").write({"login": "admin", "password": password})
env["ir.config_parameter"].set_param(
    "web.base.url",
    "http://localhost:" + ("8070" if __import__("odoo").release.version_info[0] == 18 else "8069"),
)
env["ir.config_parameter"].set_param("web.base.url.freeze", True)
env.company.write({"name": "Lettermint Demo", "email": "sender@example.invalid"})


def once(model, domain, values):
    return env[model].with_context(active_test=False).search(domain, limit=1) or env[model].create(
        values
    )


partner = once(
    "res.partner",
    [("email", "=", "reader@example.invalid")],
    {"name": "Example Customer", "email": "reader@example.invalid"},
)
product = once(
    "product.product",
    [("default_code", "=", "LM-DEMO")],
    {"name": "Demo service", "default_code": "LM-DEMO", "type": "service", "list_price": 25},
)
once(
    "sale.order",
    [("client_order_ref", "=", "LM-DEMO")],
    {
        "partner_id": partner.id,
        "client_order_ref": "LM-DEMO",
        "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1, "price_unit": 25})],
    },
)
journal = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", env.company.id)], limit=1
)
if not journal:
    env["account.chart.template"].try_loading("generic_coa", env.company)
    journal = env["account.journal"].search(
        [("type", "=", "sale"), ("company_id", "=", env.company.id)], limit=1
    )
once(
    "account.move",
    [("ref", "=", "LM-DEMO")],
    {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": journal.id,
        "ref": "LM-DEMO",
        "invoice_line_ids": [
            (
                0,
                0,
                {"product_id": product.id, "name": "Demo service", "quantity": 1, "price_unit": 25},
            )
        ],
    },
)
server = once(
    "ir.mail_server",
    [("name", "=", "Lettermint API - configure before use")],
    {
        "name": "Lettermint API - configure before use",
        "smtp_authentication": "lettermint",
        "active": False,
        "from_filter": "example.invalid",
    },
)
mailing_list = once(
    "mailing.list",
    [("name", "=", "Lettermint demo recipients")],
    {"name": "Lettermint demo recipients"},
)
once(
    "mailing.contact",
    [("email", "=", "reader@example.invalid")],
    {
        "name": "Example Reader",
        "email": "reader@example.invalid",
        "list_ids": [(4, mailing_list.id)],
    },
)
once(
    "mailing.mailing",
    [("subject", "=", "Lettermint demo campaign")],
    {
        "subject": "Lettermint demo campaign",
        "email_from": "sender@example.invalid",
        "mailing_model_id": env.ref("mass_mailing.model_mailing_list").id,
        "contact_list_ids": [(4, mailing_list.id)],
        "mail_server_id": server.id,
        "body_html": '<p>This is a local demo campaign.</p><p><a href="/unsubscribe_from_list">Unsubscribe</a></p>',
    },
)
env.cr.commit()
print("Local demo records are ready. API server is archived. No token is set.")

# Keep the sample campaign aligned when this setup is run again.
env["mailing.mailing"].search([("subject", "=", "Lettermint demo campaign")]).write(
    {"mailing_model_id": env.ref("mass_mailing.model_mailing_list").id, "mail_server_id": server.id}
)
env.cr.commit()
