"""`python -m naver_gmail_forward` 로 실행하는 입구."""

import logging
import sys

from .forwarder import forward_new_messages
from .settings import load_settings_from_environment

SUCCESS_EXIT_CODE = 0
FAILURE_EXIT_CODE = 1

KOREAN_LEVEL_NAMES = {
    logging.DEBUG: "디버그",
    logging.INFO: "정보",
    logging.WARNING: "경고",
    logging.ERROR: "실패",
    logging.CRITICAL: "치명",
}


def configure_logging() -> None:
    for level, korean_name in KOREAN_LEVEL_NAMES.items():
        logging.addLevelName(level, korean_name)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)


def main() -> int:
    configure_logging()
    summary = forward_new_messages(load_settings_from_environment())
    if summary.has_problem:
        # 실패로 끝내야 GitHub 가 실패 알림 메일을 보내 준다.
        return FAILURE_EXIT_CODE
    return SUCCESS_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
