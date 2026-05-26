import asyncio

from enum import Enum
from pathlib import Path

import logging

from aiosmtplib import SMTP, SMTPException, SMTPResponseException
from email.message import EmailMessage

from vigmykd.services import Service


RES_DIR = Path("/app/resources")
TEMPLATES_DIR = RES_DIR / "emails"


class Templates(Enum):
    REG_CONFIRM = "reg_confirm.html"
    DEL_CONFIRM = "del_confirm.html"

    @staticmethod
    def load_template(filename: str) -> str:
        path = TEMPLATES_DIR / filename
        return path.read_text(encoding="utf-8")


class Mailer(Service):
    logger = logging.getLogger("services.mailer")

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

    async def init(self):
        if not await self.is_healthy():
            self.logger.error("❌ SMTP INIT FAIL")
            raise SystemExit(1)

    async def get_smtp(self) -> SMTP:
        """Do not forget to close the returned resource"""
        use_tls = self.smtp_port == 465
        start_tls = self.smtp_port == 587 and not use_tls

        return SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            start_tls=start_tls,
            use_tls=use_tls
        )

    async def is_healthy(self) -> bool:
        smtp: SMTP | None = None
        try:
            smtp = await self.get_smtp()
            return True
        except asyncio.TimeoutError:
            self.logger.error("❌ SMTP HEALTH CHECK FAIL: Timed out")
            return False
        except Exception:
            # self.logger.error(f"❌ SMTP HEALTH CHECK FAIL: Unknown exception: {ex}")
            # return False
            # instead delegate it to the service handler
            raise
        finally:
            # just in case
            if smtp and smtp.is_connected:
                try:
                    await smtp.quit()
                except Exception:
                    pass

    async def send_email(self, to: str, sub: str, body: str, html: str | None = None):
        msg = EmailMessage()
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg["Subject"] = sub

        msg.set_content(body)
        if html is not None:
            msg.add_alternative(html, subtype="html")

        async with await self.get_smtp() as smtp:
            await smtp.login(self.smtp_user, self.smtp_pass)
            await smtp.send_message(msg)

            self.logger.info(f"📨 Sent email to {to} (subject: {sub})")

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
                self.logger.warning(f"⚠️ SMTP: Attempt {attempt + 1} failed: {ex}."
                                    f" Retrying in {delay} seconds...")
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
        except RuntimeError:
            return False

    @staticmethod
    async def send_del_confirmation(mailer: Mailer, receiver: str, code: str) -> bool:
        html = mailer.templates[Templates.DEL_CONFIRM]
        html = html.replace("{{CONFIRMATION_CODE}}", code)

        try:
            await mailer.send_email_retries(
                to=receiver,
                sub="Confirm account deletion",
                body="",
                html=html,
                max_attempts=3
            )
            return True
        except RuntimeError:
            return False