import unittest
from email.header import decode_header, make_header
from email.utils import parseaddr

from naver_gmail_forward.forwarding_message import FORWARDED_SENDER_LABEL, build_forwarding_message

SENDER_ADDRESS = "me@naver.com"
RECIPIENT_ADDRESS = "me@gmail.com"

RAW_MESSAGE = (
    "From: =?UTF-8?B?7ZmN6ri464+Z?= <hong@example.com>\r\n"
    "To: me@naver.com\r\n"
    "Cc: other@example.com\r\n"
    "Subject: =?UTF-8?B?7JWI64WV7ZWY7IS47JqU?=\r\n"
    "Message-ID: <original@example.com>\r\n"
    "DKIM-Signature: v=1; a=rsa-sha256; d=example.com\r\n"
    "Content-Type: text/plain; charset=utf-8\r\n"
    "Content-Transfer-Encoding: 8bit\r\n"
    "\r\n"
    "본문입니다.\r\n"
).encode("utf-8")


def read_sender_field(message) -> tuple:
    """메일 프로그램처럼 이름과 주소를 먼저 나눈 뒤 이름만 풀어 (표시 이름, 실제 주소)로 돌려준다."""
    encoded_display_name, address = parseaddr(message["From"])
    return str(make_header(decode_header(encoded_display_name))), address


class BuildForwardingMessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.message = build_forwarding_message(RAW_MESSAGE, SENDER_ADDRESS, RECIPIENT_ADDRESS)

    def test_sends_from_naver_account_to_gmail(self) -> None:
        _, actual_sender_address = read_sender_field(self.message)
        self.assertEqual(actual_sender_address, SENDER_ADDRESS)
        self.assertEqual(self.message["To"], RECIPIENT_ADDRESS)

    def test_sender_field_shows_original_name_address_and_forwarding(self) -> None:
        display_name, _ = read_sender_field(self.message)
        self.assertEqual(display_name, f"홍길동 (hong@example.com) - {FORWARDED_SENDER_LABEL}")

    def test_sender_field_without_original_name_shows_address(self) -> None:
        raw_message = b"From: hong@example.com\r\nSubject: test\r\n\r\nbody\r\n"
        message = build_forwarding_message(raw_message, SENDER_ADDRESS, RECIPIENT_ADDRESS)
        display_name, _ = read_sender_field(message)
        self.assertEqual(display_name, f"hong@example.com - {FORWARDED_SENDER_LABEL}")

    def test_sender_field_without_original_sender_shows_only_label(self) -> None:
        raw_message = b"Subject: test\r\n\r\nbody\r\n"
        message = build_forwarding_message(raw_message, SENDER_ADDRESS, RECIPIENT_ADDRESS)
        display_name, _ = read_sender_field(message)
        self.assertEqual(display_name, FORWARDED_SENDER_LABEL)
        self.assertIsNone(message["Reply-To"])

    def test_keeps_original_sender_as_reply_address(self) -> None:
        self.assertIn("hong@example.com", self.message["Reply-To"])

    def test_removes_original_recipients_and_signature(self) -> None:
        self.assertIsNone(self.message["Cc"])
        self.assertIsNone(self.message["DKIM-Signature"])
        self.assertEqual(len(self.message.get_all("From")), 1)
        self.assertNotEqual(self.message["Message-ID"], "<original@example.com>")

    def test_keeps_subject_and_body(self) -> None:
        self.assertEqual(self.message["Subject"], "=?UTF-8?B?7JWI64WV7ZWY7IS47JqU?=")
        self.assertIn("본문입니다.".encode("utf-8"), self.message.as_bytes())


if __name__ == "__main__":
    unittest.main()
