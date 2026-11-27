"""받은 메일 원문을 Gmail 로 보낼 메일로 바꾼다.

본문과 첨부는 그대로 두고 주소 관련 머리글만 바꾼다.
네이버 SMTP 는 로그인한 계정 주소로만 보낼 수 있으므로 보내는 사람은 내 네이버 주소가 되고,
원래 보낸 사람은 표시 이름과 '회신 주소(Reply-To)'로 남겨 Gmail 에서 바로 답장할 수 있게 한다.
"""

import email
from email.header import decode_header, make_header
from email.message import Message
from email.utils import formataddr, make_msgid, parseaddr

FORWARDED_SENDER_LABEL = "네이버 메일 전달"

# 원래 주소 정보와, 원본 발송 서버의 서명이라 전달 뒤에는 맞지 않게 되는 머리글.
REPLACED_HEADER_NAMES = (
    "From",
    "Sender",
    "To",
    "Cc",
    "Bcc",
    "Reply-To",
    "Return-Path",
    "Delivered-To",
    "Message-ID",
    "DKIM-Signature",
    "Authentication-Results",
    "ARC-Seal",
    "ARC-Message-Signature",
    "ARC-Authentication-Results",
)


def build_forwarding_message(raw_message: bytes, sender_address: str, recipient_address: str) -> Message:
    message = email.message_from_bytes(raw_message)
    original_sender = message.get("From", "")
    original_reply_address = message.get("Reply-To", "") or original_sender

    for header_name in REPLACED_HEADER_NAMES:
        del message[header_name]

    message["From"] = formataddr((_describe_original_sender(original_sender), sender_address), charset="utf-8")
    message["To"] = recipient_address
    message["Message-ID"] = make_msgid()
    if original_reply_address:
        message["Reply-To"] = original_reply_address
    return message


def _describe_original_sender(original_sender: str) -> str:
    if not original_sender:
        return FORWARDED_SENDER_LABEL
    display_name, address = parseaddr(_decode_header_value(original_sender))
    sender_name = display_name or address or FORWARDED_SENDER_LABEL
    return f"{sender_name} ({FORWARDED_SENDER_LABEL})"


def _decode_header_value(header_value: str) -> str:
    try:
        return str(make_header(decode_header(header_value)))
    except (LookupError, UnicodeDecodeError, ValueError):
        # 알 수 없는 문자 인코딩이면 해독하지 않은 값을 그대로 쓴다.
        return header_value
