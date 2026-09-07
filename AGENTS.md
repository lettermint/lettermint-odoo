# Development rules

- Use Simplified Technical English for documentation and user-facing text.
- Keep Odoo documentation focused on customer requirements, installation, configuration, usage, and support. Follow the README style of the existing Lettermint SDKs. Do not document implementation details, internal research, test reports, or release procedures in customer documentation.
- Support Odoo Community 18 and 19. Check the relevant Odoo source before changing mail behavior.
- Run `scripts/test.sh 18` and `scripts/test.sh 19` after transport or model changes.
- Run lifecycle checks after manifest, field, or uninstall changes.
- Keep live email credentials out of code, logs, screenshots, and Git. Local `.env` and `.build` are ignored.
- Unit and integration tests must mock the API. Do not send live email without a controlled sender and recipient supplied for that test.
- Keep the RFC Message-ID distinct from the Lettermint message UUID.
- Treat the prepared Odoo envelope as the delivery recipient list. Do not send to display-only addresses or expose BCC recipients.
- Do not claim Odoo Online, Enterprise, or Odoo.sh verification without tests in that environment.
