"""Failure alerting for the tender scraper.

Sends an email when a scrape run fails or comes back empty, so an outage is
noticed immediately instead of via empty result emails to subscribers.

Configuration is read from environment variables (set these in Cloud Run, e.g.
via secrets) - nothing sensitive is hard-coded:

    SMTP_HOST        e.g. smtp.gmail.com / smtp.sendgrid.net
    SMTP_PORT        default 587 (STARTTLS)
    SMTP_USER        smtp username (for SendGrid this is the literal "apikey")
    SMTP_PASSWORD    smtp password / API key
    ALERT_FROM       from address (defaults to SMTP_USER)
    ALERT_TO         comma-separated recipient list

If SMTP_HOST or ALERT_TO is missing, alerting is skipped with a log line so a
misconfiguration never crashes the scrape run itself.
"""
import os
import ssl
import smtplib
import logging
from email.message import EmailMessage


def _recipients():
    raw = os.getenv("ALERT_TO", "")
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def send_failure_alert(subject, body, png_bytes=None):
    """Best-effort failure email. Never raises - alerting must not break the run."""
    host = os.getenv("SMTP_HOST")
    recipients = _recipients()
    if not host or not recipients:
        logging.warning(
            "Alerting skipped: SMTP_HOST and/or ALERT_TO not configured.")
        return

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        sender = os.getenv("ALERT_FROM") or user or "scraper@localhost"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        if png_bytes:
            msg.add_attachment(
                png_bytes, maintype="image", subtype="png",
                filename="failure_screenshot.png")

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            if user and password:
                server.login(user, password)
            server.send_message(msg)

        logging.info("Failure alert email sent to %s", recipients)
    except Exception as e:
        logging.error("Failed to send failure alert email: %s", e)
