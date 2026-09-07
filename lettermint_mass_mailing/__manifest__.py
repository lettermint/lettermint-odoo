{
    "name": "Email Campaign Connector",
    "version": "19.0.0.1.0",
    "summary": "Send Odoo email through Lettermint",
    "description": "Requires a Lettermint account. Service fees can apply. After "
    "administrator consent, this module sends sender and recipient "
    "addresses, message content, headers, and attachments to "
    "Lettermint for email delivery. No delivery or bounce "
    "synchronization is included.",
    "author": "Lettermint",
    "website": "https://lettermint.co",
    "license": "LGPL-3",
    "category": "Marketing/Email Marketing",
    "depends": ["lettermint_mail", "mass_mailing"],
    "external_dependencies": {"python": ["requests"]},
    "data": ["views/mailing_views.xml"],
    "installable": True,
    "application": True,
    "price": 0.0,
    "currency": "EUR",
    "images": ["static/description/banner.png"],
    "support": "help@lettermint.co",
}
