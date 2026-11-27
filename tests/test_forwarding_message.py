import unittest

from naver_gmail_forward.forwarding_message import build_forwarding_message

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


class BuildForwardingMessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.message = build_forwarding_message(RAW_MESSAGE, SENDER_ADDRESS, RECIPIENT_ADDRESS)

    def test_sends_from_naver_account_to_gmail(self) -> None:
        self.assertIn(SENDER_ADDRESS, self.message["From"])
        self.assertEqual(self.message["To"], RECIPIENT_ADDRESS)

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
