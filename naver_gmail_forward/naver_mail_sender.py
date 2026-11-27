"""네이버 SMTP 로 메일을 보낸다."""

import smtplib
from email.message import Message
from typing import Optional

from .settings import NAVER_SMTP_HOST, NAVER_SMTP_PORT, NETWORK_TIMEOUT_SECONDS


class NaverMailSender:
    def __init__(self, username: str, application_password: str, sender_address: str) -> None:
        self._username = username
        self._application_password = application_password
        self._sender_address = sender_address
        self._connection: Optional[smtplib.SMTP_SSL] = None

    def __enter__(self) -> "NaverMailSender":
        self._connection = smtplib.SMTP_SSL(NAVER_SMTP_HOST, NAVER_SMTP_PORT, timeout=NETWORK_TIMEOUT_SECONDS)
        self._connection.login(self._username, self._application_password)
        return self

    def __exit__(self, *exception_details) -> None:
        if self._connection is None:
            return
        try:
            self._connection.quit()
        except (smtplib.SMTPException, OSError):
            pass

    def send(self, message: Message, recipient_address: str) -> None:
        self._connection.sendmail(self._sender_address, [recipient_address], message.as_bytes())
