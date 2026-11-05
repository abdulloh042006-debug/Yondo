"""Spelling-insensitive matching for Uzbek Latin text.

Uzbek is written in two Latin alphabets: the 1995 one (o‘ g‘ sh ch, apostrophes in many
shapes) and the 2026 one (ö ğ ş ç, tutuq ʼ; law signed 2026-10-21, in force from 2027-04-22).
Profiles, cities and search queries can use either, so discovery folds both sides to one
ASCII form before comparing:
"Toshkent", "Toşkent" and "TOSHKENT" all match, as do "o‘zbek", "o'zbek", "oʻzbek" and "özbek".
"""

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

# Order matters only in that every target is plain ASCII, so no rule feeds another.
FOLD_PAIRS: tuple[tuple[str, str], ...] = (
    ('Ş', 'sh'),
    ('ş', 'sh'),
    ('Ç', 'ch'),
    ('ç', 'ch'),
    ('Ö', "o'"),
    ('ö', "o'"),
    ('Ğ', "g'"),
    ('ğ', "g'"),
    ('‘', "'"),  # U+2018, 1995 o‘/g‘
    ('’', "'"),  # U+2019, common tutuq / typed apostrophe
    ('ʻ', "'"),  # U+02BB, official 1995 o‘/g‘ sign
    ('ʼ', "'"),  # U+02BC, tutuq
    ('`', "'"),
)


def fold_uz(text: str) -> str:
    """Python side of the fold; must stay identical to :func:`fold_uz_sql`."""
    for source, target in FOLD_PAIRS:
        text = text.replace(source, target)
    return text.lower()


def fold_uz_sql(column: ColumnElement[str]) -> ColumnElement[str]:
    """SQL side of the fold (nested REPLACE + LOWER; works on PostgreSQL and SQLite)."""
    expression: ColumnElement[str] = column
    for source, target in FOLD_PAIRS:
        expression = func.replace(expression, source, target)
    return func.lower(expression)
