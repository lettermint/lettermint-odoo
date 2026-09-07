# Use Lettermint with Odoo Online

Odoo Online can use the Lettermint SMTP relay. It cannot install the Lettermint API add-ons in this repository.

This setup has not been verified on an Odoo Online account. Check email delivery, replies, and campaign unsubscribe links before use.

## Requirements

- An Odoo Online account with access to outgoing email server settings.
- A Lettermint project with SMTP enabled, a verified sender domain, and a project API token.

## Configuration

1. Enable SMTP in your Lettermint project.
2. In Odoo settings, enable custom email servers.
3. Create an outgoing email server with these settings:

| Setting | Value |
| --- | --- |
| Host | `smtp.lettermint.co` |
| Port | `465` |
| Encryption | SSL/TLS with certificate verification |
| Username | `lettermint` |
| Password | Your project API token |
| FROM Filtering | Your verified sender address or domain |

Port `587` with STARTTLS is also available. Use certificate verification where the Odoo version provides this option. Do not use an unencrypted connection.

If your token has IP restrictions, allow the Odoo server's outgoing IP address.

4. Save and select **Test Connection**.
5. Send an email to an address that you control. Check the inbox and Lettermint activity.

## Email campaigns

SMTP uses your project's default outbound route. To use separate routes for business email and campaigns, create two Lettermint projects. Set the required default route in each project.

Create an Odoo outgoing server for each project with its project API token. Select the campaign server in Email Marketing settings. Send a test campaign and check the unsubscribe link before you send to your contacts.

## Replies and delivery results

Configure Odoo incoming email separately. Reply to a test invoice and a discussion notification. Check that each reply appears on the correct Odoo record. Reply handling with this setup has not been verified.

Use Lettermint activity to check delivery and bounce results. A successful connection test does not confirm inbox delivery or correct reply handling.

## Support

- [Lettermint SMTP documentation](https://lettermint.co/docs/guides/send-email-with-smtp)
- [Odoo outgoing email documentation](https://www.odoo.com/documentation/19.0/applications/general/email_communication/email_servers_outbound.html)
- [Contact Lettermint](mailto:help@lettermint.co)
