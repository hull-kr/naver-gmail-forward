"""네이버 받은메일함을 IMAP 으로 읽는다.

받은메일함을 읽기 전용으로 열고 BODY.PEEK 로 가져오므로
네이버 쪽의 '읽음' 표시는 바뀌지 않는다.
"""

import imaplib
from typing import List, Optional

from .settings import INBOX_FOLDER_NAME, NAVER_IMAP_HOST, NAVER_IMAP_PORT, NETWORK_TIMEOUT_SECONDS

SUCCESS_STATUS = "OK"
FETCH_WHOLE_MESSAGE_WITHOUT_MARKING_READ = "(BODY.PEEK[])"


class InboxError(RuntimeError):
    """IMAP 서버가 요청을 거절했을 때 낸다."""


class NaverInbox:
    def __init__(self, username: str, application_password: str) -> None:
        self._username = username
        self._application_password = application_password
        self._connection: Optional[imaplib.IMAP4_SSL] = None
        self.unique_identifier_validity = 0

    def __enter__(self) -> "NaverInbox":
        self._connection = imaplib.IMAP4_SSL(NAVER_IMAP_HOST, NAVER_IMAP_PORT, timeout=NETWORK_TIMEOUT_SECONDS)
        self._connection.login(self._username, self._application_password)
        status, _ = self._connection.select(INBOX_FOLDER_NAME, readonly=True)
        self._require_success(status, "받은메일함 열기")
        self.unique_identifier_validity = self._read_unique_identifier_validity()
        return self

    def __exit__(self, *exception_details) -> None:
        if self._connection is None:
            return
        try:
            self._connection.logout()
        except (imaplib.IMAP4.error, OSError):
            pass

    def latest_unique_identifier(self) -> int:
        unique_identifiers = self._search("ALL")
        return max(unique_identifiers, default=0)

    def unique_identifiers_after(self, last_forwarded_unique_identifier: int) -> List[int]:
        # "n:*" 검색은 n 보다 큰 메일이 없어도 가장 마지막 메일 하나를 돌려주므로 다시 걸러 낸다.
        next_unique_identifier = last_forwarded_unique_identifier + 1
        unique_identifiers = self._search("UID", f"{next_unique_identifier}:*")
        return sorted(
            unique_identifier
            for unique_identifier in unique_identifiers
            if unique_identifier > last_forwarded_unique_identifier
        )

    def fetch_raw_message(self, unique_identifier: int) -> Optional[bytes]:
        """메일 원문을 메모리로만 가져온다. 그사이 지워진 메일이면 None."""
        status, response_parts = self._connection.uid(
            "FETCH", str(unique_identifier), FETCH_WHOLE_MESSAGE_WITHOUT_MARKING_READ
        )
        self._require_success(status, f"메일 {unique_identifier} 가져오기")
        for response_part in response_parts:
            if isinstance(response_part, tuple):
                _, raw_message = response_part
                return raw_message
        return None

    def _search(self, *criteria: str) -> List[int]:
        status, response_parts = self._connection.uid("SEARCH", *criteria)
        self._require_success(status, "메일 검색")
        found_numbers = b" ".join(part for part in response_parts if part)
        return [int(number) for number in found_numbers.split()]

    def _read_unique_identifier_validity(self) -> int:
        _, values = self._connection.response("UIDVALIDITY")
        if not values or values[0] is None:
            raise InboxError("받은메일함의 UIDVALIDITY 값을 받지 못했습니다.")
        return int(values[0])

    @staticmethod
    def _require_success(status: str, action_description: str) -> None:
        if status != SUCCESS_STATUS:
            raise InboxError(f"{action_description} 실패 (서버 응답: {status})")
