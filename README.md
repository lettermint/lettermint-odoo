# Official Lettermint connector for Odoo

[![Tests](https://img.shields.io/github/actions/workflow/status/lettermint/lettermint-odoo/test.yml?branch=19.0&label=tests&style=flat-square)](https://github.com/lettermint/lettermint-odoo/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-LGPL--3.0-blue?style=flat-square)](LICENSE)
[![Join our Discord server](https://img.shields.io/discord/1305510095588819035?logo=discord&logoColor=eee&label=Discord&labelColor=464ce5&color=0D0E28&cacheSeconds=43200)](https://lettermint.co/r/discord)

Send email with [Lettermint](https://lettermint.co) from Odoo. Send invoices, notifications, and email campaigns with your Lettermint project.

This connector is in **beta** for Odoo Community 18 and 19. Live email delivery still needs verification. Odoo Enterprise and Odoo.sh have not been verified.

## Features

- Send business email through Lettermint.
- Select a Lettermint route for each outgoing mail server.
- Send campaigns with Odoo tracking and unsubscribe links.
- Test your connection and send a test email from Odoo.

## Requirements

- Odoo Community 18 or 19, with access to install server add-ons.
- A [Lettermint account](https://lettermint.co), a verified sender domain, and a project API token.

For Odoo Online, use the separate [SMTP setup guide](docs/odoo-online.md). These add-ons cannot be installed on Odoo Online.

## Installation

1. Download the branch for your Odoo version: [18.0](https://github.com/lettermint/lettermint-odoo/archive/refs/heads/18.0.zip) or [19.0](https://github.com/lettermint/lettermint-odoo/archive/refs/heads/19.0.zip).
2. Extract the archive. Copy the `lettermint_mail` folder into your Odoo add-ons directory. For campaigns, also copy `lettermint_mass_mailing`.
3. Restart Odoo and enable developer mode.
4. Open **Apps → Update Apps List**.
5. Install **Email API Connector**. For campaigns, also install **Email Campaign Connector** and Odoo **Email Marketing**.

## Configuration

1. In Lettermint, create a project, verify your sender domain, and create a project API token.
2. In Odoo, open **Settings → Technical → Email → Outgoing Mail Servers** in developer mode.
3. Create a server. Select **Lettermint API** under **Authenticate with**.
4. Set **FROM Filtering** to your verified sender address or domain. Set the server priority. A smaller number has higher priority.
5. Enter your project API token. A team API token cannot be used to send email.
6. Enter a route slug, or leave it empty to use the project's default outbound route.
7. Read the data transfer notice, select **Allow email data transfer**, and save.
8. Select **Test Connection** to check your credentials.
9. Select **Send Test Email** and use an address that you control. Check the inbox and your Lettermint activity.

A successful connection test does not confirm that the sender or route is ready. Send a test email before you use the server for business email.

### Email campaigns

Create an outgoing mail server with the Lettermint route for your campaigns. Select this server in the campaign's **Settings → Mail Server** field. If the field is hidden, enable the dedicated outgoing mail server option in Email Marketing settings.

Keep **Use Exclusion List** enabled where this setting is available. Send a test campaign and check its tracking and unsubscribe links before you send it to your contacts.

## Usage notes

- Each email must have at least one visible **To** recipient. Use SMTP for emails with BCC recipients only.
- The limit is 50 recipients per email and 25 MB per request, including attachments.
- Use SMTP for signed or encrypted emails and other message formats that the API does not support.
- Delivery and bounce results are available in Lettermint. They are not synchronized to Odoo. The Odoo **Sent** status does not confirm inbox delivery.
- Configure incoming email in Odoo separately to receive replies.
- To inspect a failed email, open **Settings → Technical → Email → Emails**. Correct the cause before you try again. If the send result is unclear, or the attempt is more than 24 hours old, check Lettermint activity first to avoid duplicate email.

## Data transfer

After administrator consent, the connector sends sender and recipient addresses, message content, headers, and attachments to Lettermint for delivery. A Lettermint account is required. Service fees can apply. See the [Lettermint privacy policy](https://lettermint.co/privacy-policy).

## Support

For help, join our [Discord server](https://lettermint.co/r/discord) or email [help@lettermint.co](mailto:help@lettermint.co).

- [Lettermint documentation](https://lettermint.co/docs)
- [Report an issue](https://github.com/lettermint/lettermint-odoo/issues)

## License

This connector is available under the [LGPL-3.0 license](LICENSE).
