"""Retrieval-only answers: the best-matching approved knowledge section, returned verbatim.

Nothing is generated and nothing leaves the server (docs/ai-assistant/phase-a-audit.md §9).
``answer()`` returns the stored title and text of one approved section with its source, or
``found=False`` when no section scores at least the threshold (the client then points to Help).

Matching is the same on every database: questions and sections are normalised (lower case,
Uzbek 1995 and 2026 spellings folded by ``discovery/textfold.py``), function words dropped, and
every question word is compared with the section's words, tolerating small typos and word
endings. On PostgreSQL, full-text search and ``pg_trgm`` first narrow the candidates in SQL;
SQLite (tests, local runs) scores all rows of the language. Mode is enforced in the query:
public mode sees ``public`` and ``shared`` sections only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.discovery.textfold import fold_uz

LANGUAGES = ('uz', 'ru', 'en')
MODES = {'public': ('public', 'shared'), 'internal': ('public', 'shared', 'internal')}
CANDIDATES = 20
WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")

# Grammar words that carry no topic. Kept short on purpose: topic words always count.
STOPWORDS: dict[str, frozenset[str]] = {
    'en': frozenset(
        'a an the is are am be was were do does did i my me you your it its to of in on at for '
        'and or can could how what when where why who which this that there please about with '
        'from by as if not no yes so get'.split()
    ),
    'ru': frozenset(
        'и в во на с со к ко по о об от до за из у а но или ли не да как что где когда '
        'почему зачем кто это этот эта эти мне меня мой моя мои я вы ваш ты можно ли '
        'есть быть для при же бы то'.split()
    ),
    'uz': frozenset(
        'va bilan uchun ham bu shu u men mening siz sizning qanday qanaqa nima nimani '
        "qachon qayerda nega kim mi mumkinmi bo'ladimi bormi yo'q ha emas".split()
    ),
}


@dataclass(frozen=True, slots=True)
class Answer:
    found: bool
    score: float
    doc_id: str | None = None
    title: str | None = None
    answer: str | None = None
    source: str | None = None
    version: int | None = None


def normalise(text: str, language: str) -> str:
    """Lower case; Uzbek folded so the 1995 and 2026 alphabets compare equal."""
    text = fold_uz(text) if language == 'uz' else text.lower()
    return text.replace('ё', 'е')


def words(text: str, language: str) -> list[str]:
    stop = STOPWORDS.get(language, frozenset())
    return [w for w in WORD.findall(normalise(text, language)) if len(w) > 1 and w not in stop]


def word_similarity(a: str, b: str) -> float:
    """1 for equal words; high for a shared stem or a small typo; 0 when unrelated."""
    if a == b:
        return 1.0
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 4 and long_.startswith(short):
        return 0.9  # word ending: book/booking, oplat/oplata
    prefix = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        prefix += 1
    if prefix >= 5 and prefix >= 0.6 * len(short):
        return 0.85  # shared stem with different endings: оплата/оплатить
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio if len(short) >= 4 and ratio >= 0.75 else 0.0  # small typo: paymnet/payment


def score(question: str, title: str, answer: str, language: str) -> float:
    """Share of the question's topic words found in the section (title words count fully,
    words found only in the answer text count 0.8)."""
    asked = words(question, language)
    if not asked:
        return 0.0
    title_words = set(words(title, language))
    answer_words = set(words(answer, language))
    total = 0.0
    for word in asked:
        in_title = max((word_similarity(word, w) for w in title_words), default=0.0)
        in_answer = max((word_similarity(word, w) for w in answer_words), default=0.0)
        total += max(in_title, 0.8 * in_answer)
    return round(total / len(asked), 4)


async def candidates(session: AsyncSession, question: str, language: str, audiences: tuple):
    from yondo_api.assistant.models import AssistantSection

    query = select(AssistantSection).where(
        AssistantSection.language == language, AssistantSection.audience.in_(audiences)
    )
    if session.get_bind().dialect.name == 'postgresql':
        asked = words(question, language)
        if not asked:
            return []
        text = ' '.join(asked)
        vector = func.to_tsvector('simple', AssistantSection.search_text)
        terms = func.websearch_to_tsquery('simple', ' or '.join(asked))
        trigram = func.word_similarity(literal(text), AssistantSection.search_text)
        query = (
            query.where(or_(vector.op('@@')(terms), trigram > 0.2))
            .order_by((func.ts_rank(vector, terms) + trigram).desc())
            .limit(CANDIDATES)
        )
    return list((await session.scalars(query)).all())


async def answer(
    session: AsyncSession, question: str, language: str, mode: str, *, min_score: float
) -> Answer:
    if language not in LANGUAGES:
        raise ValueError(f'language must be one of {LANGUAGES}')
    if mode not in MODES:
        raise ValueError(f'mode must be one of {tuple(MODES)}')
    question = question[:1000]  # matching only; the question itself is never stored
    best, best_score = None, 0.0
    for row in await candidates(session, question, language, MODES[mode]):
        value = score(question, row.title, row.answer, language)
        if value > best_score or (
            value == best_score and best is not None and row.doc_id < best.doc_id
        ):
            best, best_score = row, value
    if best is None or best_score < min_score:
        return Answer(found=False, score=best_score)
    return Answer(
        found=True,
        score=best_score,
        doc_id=best.doc_id,
        title=best.title,
        answer=best.answer,
        source=best.source,
        version=best.version,
    )
