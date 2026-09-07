# Lettermint Email API Connector for Odoo

Send invoices, notifications, and other Odoo email with [Lettermint](https://lettermint.co).

This connector is in **beta** for Odoo Community 18 and 19. Live email delivery still needs verification. Odoo Enterprise and Odoo.sh have not been verified. Odoo Online requires separate SMTP setup.

## Installation

Use the module for your Odoo version. Copy it into your Odoo add-ons directory, restart Odoo, and update the Apps list in developer mode. Install **Email API Connector**.

## Configuration

Create a Lettermint project, verify your sender domain, and create a project API token. In Odoo outgoing mail server settings, select **Lettermint API**. Enter your token, sender filter, and optional route. Read and accept the data transfer notice. Save, test the connection, and send a test email to an address that you control.

For campaigns, select the required server in the campaign's **Settings → Mail Server** field. Check tracking and unsubscribe links with a test campaign.

See the [installation and configuration guide](https://github.com/lettermint/lettermint-odoo#installation) for full instructions.

## Usage notes

- Each email needs at least one visible **To** recipient. Use SMTP for emails with BCC recipients only, signed or encrypted emails, and other unsupported formats.
- The limit is 50 recipients per email and 25 MB per request, including attachments.
- Check Lettermint activity before you retry an email if the result is unclear or the attempt is more than 24 hours old.
- Delivery and bounce results are not synchronized to Odoo. The Odoo **Sent** status does not confirm inbox delivery.
- Configure incoming email in Odoo separately to receive replies.

## Data transfer

After administrator consent, sender and recipient addresses, message content, headers, and attachments are sent to Lettermint for delivery. A Lettermint account is required. Service fees can apply. See the [Lettermint privacy policy](https://lettermint.co/privacy-policy).

## Support

Join our [Discord server](https://lettermint.co/r/discord) or email [help@lettermint.co](mailto:help@lettermint.co).

## License

This connector is available under the [LGPL-3.0 license](LICENSE).
