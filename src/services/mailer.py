import asyncio

from enum import Enum
from pathlib import Path

from aiosmtplib import SMTP, SMTPException, SMTPResponseException
from email.message import EmailMessage


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "resources" / "emails"


class Templates(Enum):
    REG_CONFIRM = "reg_confirm.html"

    @staticmethod
    def load_template(filename: str) -> str:
        path = TEMPLATES_DIR / filename
        return path.read_text(encoding="utf-8")


class Mailer:
    def __init__(
        self,
        smtp_host: str | None,
        smtp_port: str | None,
        smtp_user: str | None,
        smtp_pass: str | None,
    ):
        if smtp_host is None or \
            smtp_port is None or \
            smtp_user is None or \
            smtp_pass is None:
            raise ValueError("Mailer does not accept NoneType arguments. Received: "
                            f"{smtp_host=} | {smtp_port=} | {smtp_user=} | {smtp_pass=}")

        if not smtp_port.isnumeric():
            raise ValueError(f"smtp_port must be numeric: {smtp_port}")

        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass

        self.templates = {}

        for template in Templates:
            self.templates[template] = Templates.load_template(template.value)


    async def send_email(self, to: str, sub: str, body: str, html: str | None = None):
        msg = EmailMessage()
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg["Subject"] = sub

        msg.set_content(body)
        if html is not None:
            msg.add_alternative(html, subtype="html")

        use_tls = self.smtp_port == 465
        start_tls = self.smtp_port == 587 and not use_tls

        async with SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            start_tls=start_tls,
            use_tls=use_tls
        ) as smtp:
            await smtp.login(self.smtp_user, self.smtp_pass)
            await smtp.send_message(msg)

            print(f"Send email to {to} (subject: {sub})")
    
    async def send_email_retries(
        self,
        to: str,
        sub: str,
        body: str,
        html: str | None = None,
        max_attempts: int = 3
    ):
        if not (1 <= max_attempts <= 9):
            raise ValueError(f"{max_attempts=} but must be in [1, 9]")

        for attempt in range(max_attempts):
            try:
                await self.send_email(to, sub, body, html)
                return
            except (SMTPException, SMTPResponseException) as ex:
                delay = 2 * attempt
                print(f"Attempt {attempt + 1} failed: {ex}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        raise RuntimeError(f"Failed to send email after {max_attempts} retries")


class PreaggregatedMailer:
    @staticmethod
    async def send_reg_confirmation(mailer: Mailer, receiver: str, code: str) -> bool:
        html = mailer.templates[Templates.REG_CONFIRM]
        html = html.replace("{{CONFIRMATION_CODE}}", code)

        try:
            await mailer.send_email_retries(
                to=receiver,
                sub="Confirm your account",
                body="",
                html=html,
                max_attempts=3
            )
            return True
        except RuntimeError as ex:
            return False
