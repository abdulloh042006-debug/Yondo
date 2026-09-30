import re

from yondo_api.api.errors import ApplicationError

_PHONE_FORMAT = re.compile(r'^[+\d\s().-]+$')


def normalize_uzbekistan_phone(phone_number: str) -> str:
    value = phone_number.strip()
    if (
        not value
        or not _PHONE_FORMAT.fullmatch(value)
        or ('+' in value and (not value.startswith('+') or value.count('+') != 1))
    ):
        raise ApplicationError('invalid_phone_number', 'Enter a valid Uzbekistan phone number', 422)

    digits = re.sub(r'\D', '', value)
    if digits.startswith('00'):
        digits = digits[2:]
    if len(digits) == 9:
        digits = f'998{digits}'
    if len(digits) != 12 or not digits.startswith('998'):
        raise ApplicationError('invalid_phone_number', 'Enter a valid Uzbekistan phone number', 422)
    return f'+{digits}'
