"""새 메일을 찾아 차례로 전달하는 흐름.

로그는 공개 저장소의 Actions 화면에 그대로 보이므로
제목·보낸 사람·본문은 절대 찍지 않고 메일 번호와 개수만 남긴다.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .forwarding_message import build_forwarding_message
from .inbox_state import InboxState, load_state, save_state
from .naver_inbox import NaverInbox
from .naver_mail_sender import NaverMailSender
from .settings import MAXIMUM_FORWARD_ATTEMPTS, Settings

logger = logging.getLogger(__name__)


@dataclass
class ForwardingSummary:
    forwarded_count: int = 0
    skipped_unique_identifiers: List[int] = field(default_factory=list)
    retry_pending: bool = False

    @property
    def has_problem(self) -> bool:
        return bool(self.skipped_unique_identifiers) or self.retry_pending


def forward_new_messages(settings: Settings) -> ForwardingSummary:
    summary = ForwardingSummary()
    previous_state = load_state(settings.state_file_path)

    with NaverInbox(settings.naver_username, settings.naver_application_password) as inbox:
        if _needs_new_starting_point(previous_state, inbox.unique_identifier_validity):
            _record_starting_point(settings, inbox)
            return summary

        new_unique_identifiers = inbox.unique_identifiers_after(previous_state.last_forwarded_unique_identifier)
        if not new_unique_identifiers:
            logger.info("새 메일 없음")
            return summary

        logger.info("새 메일 %d통 발견", len(new_unique_identifiers))
        with NaverMailSender(
            settings.naver_username, settings.naver_application_password, settings.naver_mail_address
        ) as sender:
            _forward_each(settings, inbox, sender, previous_state, new_unique_identifiers, summary)

    logger.info("전달 완료 %d통", summary.forwarded_count)
    return summary


def _needs_new_starting_point(previous_state: Optional[InboxState], current_validity: int) -> bool:
    # 처음 실행했거나 네이버가 메일 번호 체계를 새로 매겼으면 예전 번호를 믿을 수 없다.
    return previous_state is None or previous_state.unique_identifier_validity != current_validity


def _record_starting_point(settings: Settings, inbox: NaverInbox) -> None:
    """지금 받은메일함에 있는 메일은 건너뛰고, 이후 도착하는 메일부터 전달한다."""
    starting_state = InboxState(
        unique_identifier_validity=inbox.unique_identifier_validity,
        last_forwarded_unique_identifier=inbox.latest_unique_identifier(),
    )
    save_state(settings.state_file_path, starting_state)
    logger.info("기준점 설정: 메일 번호 %d 이후부터 전달합니다", starting_state.last_forwarded_unique_identifier)


def _forward_each(
    settings: Settings,
    inbox: NaverInbox,
    sender: NaverMailSender,
    state: InboxState,
    unique_identifiers: List[int],
    summary: ForwardingSummary,
) -> None:
    for unique_identifier in unique_identifiers:
        try:
            _forward_one(settings, inbox, sender, unique_identifier)
        except Exception as error:  # 어떤 이유로 실패하든 상태를 남기고 멈춰야 같은 메일을 두 번 보내지 않는다.
            state = state.after_failure(unique_identifier)
            logger.error(
                "메일 %d 전달 실패 (%d/%d회): %s",
                unique_identifier,
                state.failed_attempts,
                MAXIMUM_FORWARD_ATTEMPTS,
                type(error).__name__,
            )
            if state.failed_attempts < MAXIMUM_FORWARD_ATTEMPTS:
                save_state(settings.state_file_path, state)
                summary.retry_pending = True
                logger.warning("다음 실행에서 메일 %d부터 다시 시도합니다", unique_identifier)
                return
            logger.warning("메일 %d은(는) 계속 실패해 건너뜁니다", unique_identifier)
            summary.skipped_unique_identifiers.append(unique_identifier)
        else:
            summary.forwarded_count += 1
        state = state.after_forwarding(unique_identifier)
        save_state(settings.state_file_path, state)


def _forward_one(settings: Settings, inbox: NaverInbox, sender: NaverMailSender, unique_identifier: int) -> None:
    raw_message = inbox.fetch_raw_message(unique_identifier)
    if raw_message is None:
        logger.info("메일 %d은(는) 그사이 삭제되어 건너뜁니다", unique_identifier)
        return
    message = build_forwarding_message(raw_message, settings.naver_mail_address, settings.gmail_address)
    sender.send(message, settings.gmail_address)
    logger.info("메일 %d 전달", unique_identifier)
