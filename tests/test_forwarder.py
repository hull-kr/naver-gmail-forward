import tempfile
import unittest
from pathlib import Path
from unittest import mock

from naver_gmail_forward import forwarder
from naver_gmail_forward.inbox_state import InboxState, load_state, save_state
from naver_gmail_forward.settings import MAXIMUM_FORWARD_ATTEMPTS, Settings

CURRENT_VALIDITY = 7
RAW_MESSAGE = b"From: a@example.com\r\nSubject: test\r\n\r\nbody\r\n"


class FakeInbox:
    def __init__(self, unique_identifiers):
        self.unique_identifiers = unique_identifiers
        self.unique_identifier_validity = CURRENT_VALIDITY

    def __enter__(self):
        return self

    def __exit__(self, *exception_details):
        pass

    def latest_unique_identifier(self):
        return max(self.unique_identifiers, default=0)

    def unique_identifiers_after(self, last_forwarded_unique_identifier):
        return [number for number in self.unique_identifiers if number > last_forwarded_unique_identifier]

    def fetch_raw_message(self, unique_identifier):
        return RAW_MESSAGE


class FakeSender:
    def __init__(self, always_fails=False):
        self.always_fails = always_fails
        self.sent_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *exception_details):
        pass

    def send(self, message, recipient_address):
        if self.always_fails:
            raise OSError("전송 실패 흉내")
        self.sent_count += 1


class ForwardNewMessagesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.state_file_path = Path(self.temporary_directory.name) / "state.json"
        self.settings = Settings("me", "password", "me@gmail.com", self.state_file_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_forwarder(self, inbox, sender):
        with mock.patch.object(forwarder, "NaverInbox", return_value=inbox), mock.patch.object(
            forwarder, "NaverMailSender", return_value=sender
        ):
            return forwarder.forward_new_messages(self.settings)

    def test_first_run_only_records_starting_point(self) -> None:
        sender = FakeSender()
        self.run_forwarder(FakeInbox([1, 2, 3]), sender)
        self.assertEqual(sender.sent_count, 0)
        self.assertEqual(load_state(self.state_file_path).last_forwarded_unique_identifier, 3)

    def test_forwards_only_messages_after_last_one(self) -> None:
        save_state(self.state_file_path, InboxState(CURRENT_VALIDITY, 3))
        sender = FakeSender()
        summary = self.run_forwarder(FakeInbox([1, 2, 3, 4, 5]), sender)
        self.assertEqual(sender.sent_count, 2)
        self.assertFalse(summary.has_problem)
        self.assertEqual(load_state(self.state_file_path).last_forwarded_unique_identifier, 5)

    def test_changed_validity_resets_starting_point(self) -> None:
        save_state(self.state_file_path, InboxState(CURRENT_VALIDITY + 1, 1))
        sender = FakeSender()
        self.run_forwarder(FakeInbox([1, 2]), sender)
        self.assertEqual(sender.sent_count, 0)
        self.assertEqual(load_state(self.state_file_path).unique_identifier_validity, CURRENT_VALIDITY)

    def test_failure_keeps_position_for_retry(self) -> None:
        save_state(self.state_file_path, InboxState(CURRENT_VALIDITY, 3))
        summary = self.run_forwarder(FakeInbox([4, 5]), FakeSender(always_fails=True))
        state = load_state(self.state_file_path)
        self.assertTrue(summary.retry_pending)
        self.assertEqual(state.last_forwarded_unique_identifier, 3)
        self.assertEqual(state.failed_attempts, 1)

    def test_repeated_failure_skips_message(self) -> None:
        last_attempt_state = InboxState(CURRENT_VALIDITY, 3, 4, MAXIMUM_FORWARD_ATTEMPTS - 1)
        save_state(self.state_file_path, last_attempt_state)
        summary = self.run_forwarder(FakeInbox([4]), FakeSender(always_fails=True))
        self.assertEqual(summary.skipped_unique_identifiers, [4])
        self.assertEqual(load_state(self.state_file_path).last_forwarded_unique_identifier, 4)


if __name__ == "__main__":
    unittest.main()
