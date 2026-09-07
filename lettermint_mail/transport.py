"""Adapt Odoo's prepared message to the Lettermint sending API."""

import base64
import hashlib
import json
from email.utils import getaddresses, formataddr

import requests

API_URL = "https://api.lettermint.co/v1"
TIMEOUT = (10, 60)


class DeliveryError(Exception):
    """An error that is safe to show in Odoo's mail log."""


def addresses(message, field):
    return [
        (name, address)
        for name, address in getaddresses([str(value) for value in message.get_all(field, [])])
        if address
    ]


def prepare_payload(message, recipients, route):
    # Odoo's envelope is authoritative. Never send to display-only or skipped addresses.
    remaining = dict.fromkeys(recipients)
    payload = {"from": str(message["From"]), "subject": str(message["Subject"] or "")}
    for field in ("to", "cc"):
        values = []
        for name, address in addresses(message, field):
            if address in remaining:
                values.append(formataddr((name, address), charset="utf-8"))
                remaining.pop(address)
        if values:
            payload[field] = values
    if remaining:
        payload["bcc"] = list(remaining)
    if not payload.get("to"):
        raise DeliveryError(
            "Lettermint API requires a visible To recipient. Use SMTP for BCC-only or display-only To messages."
        )
    if len(set(recipients)) > 50:
        raise DeliveryError("Lettermint permits at most 50 recipients per message.")
    reply_to = addresses(message, "Reply-To")
    if reply_to:
        payload["reply_to"] = [formataddr(value, charset="utf-8") for value in reply_to]
    if route:
        payload["route"] = route
    excluded = {
        "from",
        "to",
        "cc",
        "bcc",
        "reply-to",
        "subject",
        "date",
        "return-path",
        "sender",
        "mime-version",
        "content-type",
        "content-transfer-encoding",
        "x-forge-to",
        "x-msg-to-add",
        "x-msg-to-consolidate",
        "idempotency-key",
        "x-lettermint-route",
        "x-lm-preserve-message-id",
        "x-lettermint-odoo-campaign",
    }
    headers = {}
    seen = set()
    for key, value in message.items():
        if key.lower() in excluded:
            continue
        if key.lower() in seen:
            raise DeliveryError(
                "The API cannot preserve repeated custom headers. Use SMTP for this message."
            )
        seen.add(key.lower())
        # Unfold headers before JSON encoding. No SMTP MIME boundaries enter the payload.
        headers[key] = " ".join(str(value).splitlines())
    if message["Message-ID"]:
        headers["X-LM-Preserve-Message-ID"] = "true"
    payload["headers"] = headers
    if message["X-Lettermint-Odoo-Campaign"]:
        # Odoo owns the open pixel, click links, and unsubscribe links.
        payload["settings"] = {"track_opens": False, "track_clicks": False}
    bodies = {"text/plain": [], "text/html": []}
    attachments = []

    def visit(part):
        content_type = part.get_content_type()
        filename = part.get_filename()
        attachment = bool(
            filename
            or part.get_content_disposition() == "attachment"
            or part.get("Content-ID")
            or content_type == "message/rfc822"
        )
        if part.is_multipart() and not attachment:
            if content_type not in (
                "multipart/mixed",
                "multipart/alternative",
                "multipart/related",
            ):
                raise DeliveryError("This MIME structure requires SMTP delivery.")
            for child in part.get_payload():
                visit(child)
            return
        if content_type in bodies and not attachment:
            try:
                bodies[content_type].append(
                    (part.get_payload(decode=True) or b"").decode(
                        part.get_content_charset() or "utf-8"
                    )
                )
            except (UnicodeError, LookupError):
                raise DeliveryError("The message body has an invalid character encoding.") from None
            return
        data = part.get_payload(decode=True)
        if content_type == "message/rfc822" and part.is_multipart():
            data = b"\r\n".join(child.as_bytes() for child in part.get_payload())
        if data is None:
            raise DeliveryError("This attachment cannot be converted for API delivery.")
        item = {
            "filename": filename
            or ("attachment.eml" if content_type == "message/rfc822" else "attachment"),
            "content": base64.b64encode(data).decode("ascii"),
            "content_type": str(part.get("Content-Type", content_type)),
        }
        if part.get("Content-ID"):
            item["content_id"] = str(part["Content-ID"]).strip("<>")
        attachments.append(item)

    visit(message)
    for mime, field in [("text/plain", "text"), ("text/html", "html")]:
        if len(bodies[mime]) > 1:
            raise DeliveryError("Multiple body parts of the same type require SMTP delivery.")
        if bodies[mime]:
            payload[field] = bodies[mime][0]
    if attachments:
        payload["attachments"] = attachments
    return payload


class ApiSession:
    """Use the small session interface called by ir.mail_server.send_email."""

    def __init__(self, token, route, from_filter, smtp_from, database_uuid, server_id):
        self._token = token
        self.route = route
        self.from_filter = from_filter
        self.smtp_from = smtp_from
        self._namespace = f"{database_uuid}:{server_id}"
        self.mail_server_name = "Lettermint API"
        self.last_message_id = None

    def _request(self, method, path, payload=None, key=None):
        headers = {
            "X-Lettermint-Token": self._token,
            "Accept": "application/json",
            "User-Agent": "lettermint-odoo/0.1.0",
        }
        if key:
            headers["Idempotency-Key"] = key
        data = None
        if payload is not None:
            data = json.dumps(
                payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode()
            if len(data) > 25 * 1024 * 1024:
                raise DeliveryError("The API request exceeds the 25 MB size limit.")
            headers["Content-Type"] = "application/json"
        try:
            response = requests.request(
                method,
                API_URL + path,
                headers=headers,
                data=data,
                timeout=TIMEOUT,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise DeliveryError(
                "Cannot reach Lettermint. Check the connection before you retry. The delivery result can be unknown."
            ) from None
        try:
            if not 200 <= response.status_code < 300:
                details = {
                    401: "Check the project API token.",
                    403: "Check project access and the token IP allowlist.",
                    409: "The request conflicts with an earlier send. Do not change the key to force a retry.",
                    422: "Check the sender domain, route, recipients, content, and attachments.",
                    429: "The sending limit was reached. Retry later.",
                }
                raise DeliveryError(
                    f"Lettermint returned HTTP {response.status_code}. "
                    + details.get(response.status_code, "Check Lettermint status before you retry.")
                )
            if path == "/ping":
                return None
            try:
                result = response.json()
            except ValueError:
                raise DeliveryError(
                    "Lettermint returned an invalid response. The delivery result is unknown."
                ) from None
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("message_id"), str)
                or not result["message_id"]
            ):
                raise DeliveryError(
                    "Lettermint returned no message ID. The delivery result is unknown."
                )
            return result["message_id"]
        finally:
            response.close()

    def ping(self):
        self._request("GET", "/ping")

    def send_message(self, message, from_addr, to_addrs):
        payload = prepare_payload(message, to_addrs, self.route)
        # Exclude Date and MIME boundaries. Keep a key stable across Odoo queue retries.
        # Recipient set is necessary: Odoo can send one Message-ID to several followers.
        message_id = str(message.get("Message-ID", ""))
        if not message_id:
            raise DeliveryError("A Message-ID is required for safe API retries.")
        identity = json.dumps([self._namespace, message_id, sorted(set(to_addrs))])
        key = "odoo-" + hashlib.sha256(identity.encode()).hexdigest()
        self.last_message_id = self._request("POST", "/send", payload, key)
        return {}

    def quit(self):
        self._token = None
        return (221, b"Closed")
