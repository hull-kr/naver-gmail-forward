"""실행에 필요한 설정값과 고정 상수를 모아 둔다."""

import os
from dataclasses import dataclass
from pathlib import Path

NAVER_IMAP_HOST = "imap.naver.com"
NAVER_IMAP_PORT = 993
NAVER_SMTP_HOST = "smtp.naver.com"
NAVER_SMTP_PORT = 465
NAVER_MAIL_DOMAIN = "naver.com"

# 네이버의 스팸메일함은 받은메일함과 별개 폴더라서, 받은메일함만 열면 스팸은 저절로 빠진다.
INBOX_FOLDER_NAME = "INBOX"

NETWORK_TIMEOUT_SECONDS = 60

# 같은 메일 전달이 이 횟수만큼 연달아 실패하면 그 메일은 건너뛰고 다음 메일로 넘어간다.
MAXIMUM_FORWARD_ATTEMPTS = 3

DEFAULT_STATE_FILE_PATH = ".state/naver-inbox-state.json"

NAVER_USERNAME_VARIABLE = "NAVER_USERNAME"
NAVER_APPLICATION_PASSWORD_VARIABLE = "NAVER_APPLICATION_PASSWORD"
GMAIL_ADDRESS_VARIABLE = "GMAIL_ADDRESS"
STATE_FILE_PATH_VARIABLE = "STATE_FILE_PATH"


class MissingSettingError(RuntimeError):
    """꼭 필요한 환경 변수가 비어 있을 때 낸다."""


@dataclass(frozen=True)
class Settings:
    naver_username: str
    naver_application_password: str
    gmail_address: str
    state_file_path: Path

    @property
    def naver_mail_address(self) -> str:
        """아이디만 넣었든 주소 전체를 넣었든 보내는 사람 주소를 만든다."""
        if "@" in self.naver_username:
            return self.naver_username
        return f"{self.naver_username}@{NAVER_MAIL_DOMAIN}"


def load_settings_from_environment() -> Settings:
    return Settings(
        naver_username=_read_required_variable(NAVER_USERNAME_VARIABLE),
        naver_application_password=_read_required_variable(NAVER_APPLICATION_PASSWORD_VARIABLE),
        gmail_address=_read_required_variable(GMAIL_ADDRESS_VARIABLE),
        state_file_path=Path(os.environ.get(STATE_FILE_PATH_VARIABLE, DEFAULT_STATE_FILE_PATH)),
    )


def _read_required_variable(variable_name: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if not value:
        raise MissingSettingError(f"환경 변수 {variable_name} 이(가) 비어 있습니다. GitHub Secrets 를 확인하세요.")
    return value
