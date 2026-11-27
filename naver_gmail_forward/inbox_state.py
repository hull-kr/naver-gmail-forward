"""어디까지 전달했는지를 기록하는 상태.

메일 내용은 담지 않는다. IMAP 이 메일마다 붙이는 고유 번호(UID)와
그 번호 체계의 유효값(UIDVALIDITY), 실패 횟수만 남긴다.
"""

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InboxState:
    unique_identifier_validity: int
    last_forwarded_unique_identifier: int
    failing_unique_identifier: Optional[int] = None
    failed_attempts: int = 0

    def after_forwarding(self, unique_identifier: int) -> "InboxState":
        return replace(
            self,
            last_forwarded_unique_identifier=unique_identifier,
            failing_unique_identifier=None,
            failed_attempts=0,
        )

    def after_failure(self, unique_identifier: int) -> "InboxState":
        if self.failing_unique_identifier == unique_identifier:
            attempts = self.failed_attempts + 1
        else:
            attempts = 1
        return replace(self, failing_unique_identifier=unique_identifier, failed_attempts=attempts)


def load_state(state_file_path: Path) -> Optional[InboxState]:
    if not state_file_path.exists():
        return None
    stored_values = json.loads(state_file_path.read_text(encoding="utf-8"))
    return InboxState(**stored_values)


def save_state(state_file_path: Path, state: InboxState) -> None:
    state_file_path.parent.mkdir(parents=True, exist_ok=True)
    state_file_path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
