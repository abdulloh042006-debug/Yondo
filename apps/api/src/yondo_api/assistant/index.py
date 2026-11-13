"""Index approved knowledge documents into ``assistant_sections`` (one row per doc and language).

    python -m yondo_api.assistant.index [--root PATH]

Only ``status = "approved"`` documents are indexed. A row is rewritten only when its content hash
changes; rows of documents that are no longer approved (or no longer exist) are removed. The
indexer refuses to run while the knowledge validator reports any error, so a duplicate id or a
broken document can never be half-indexed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.assistant import kb
from yondo_api.assistant.models import AssistantSection
from yondo_api.assistant.retrieval import normalise
from yondo_api.config import Settings, get_settings


class KnowledgeIndexError(RuntimeError):
    """The knowledge base has validation errors; nothing was indexed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__(f'{len(errors)} knowledge validation error(s); index not changed')
        self.errors = errors


@dataclass(frozen=True, slots=True)
class IndexResult:
    added: int
    updated: int
    unchanged: int
    removed: int


def kb_root(settings: Settings) -> Path:
    return Path(settings.assistant_kb_root) if settings.assistant_kb_root else kb.DEFAULT_ROOT


def split_heading(text: str, fallback: str) -> tuple[str, str]:
    """A section that starts with "### Question" gives (question, rest); otherwise (title, text)."""
    first, _, rest = text.partition('\n')
    if first.startswith('### '):
        return first[4:].strip(), rest.strip()
    return fallback, text


def section_rows(doc: kb.KnowledgeDoc) -> dict[tuple[str, str], dict[str, object]]:
    rows: dict[tuple[str, str], dict[str, object]] = {}
    for language, text in doc.sections.items():
        title, answer = split_heading(text, doc.title)
        row: dict[str, object] = {
            'doc_id': doc.id,
            'language': language,
            'audience': doc.audience,
            'category': doc.category,
            'version': doc.version,
            'source': doc.source,
            'title': title,
            'answer': answer,
        }
        row['content_hash'] = hashlib.sha256(
            json.dumps(row, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        row['search_text'] = normalise(f'{title}\n{answer}', language)
        rows[(doc.id, language)] = row
    return rows


async def reindex(session: AsyncSession, root: Path) -> IndexResult:
    docs, errors = kb.load(root)
    if errors:
        raise KnowledgeIndexError(errors)
    wanted: dict[tuple[str, str], dict[str, object]] = {}
    for doc in kb.indexable(docs):
        wanted.update(section_rows(doc))

    existing = {
        (row.doc_id, row.language): row
        for row in (await session.scalars(select(AssistantSection))).all()
    }
    added = updated = unchanged = removed = 0
    for key, row in existing.items():
        if key not in wanted:
            await session.delete(row)
            removed += 1
    for key, values in wanted.items():
        current = existing.get(key)
        if current is None:
            session.add(AssistantSection(**values))
            added += 1
        elif current.content_hash != values['content_hash']:
            for name, value in values.items():
                setattr(current, name, value)
            updated += 1
        else:
            unchanged += 1
    await session.commit()
    return IndexResult(added, updated, unchanged, removed)


async def run(root: Path, settings: Settings) -> int:
    from yondo_api.db.session import create_database_engine, create_session_factory

    engine = create_database_engine(settings.database_url_async)
    try:
        async with create_session_factory(engine)() as session:
            try:
                result = await reindex(session, root)
            except KnowledgeIndexError as exc:
                for error in exc.errors:
                    print(f'ERROR {error}')
                print(f'index: refused ({exc})')
                return 1
    finally:
        await engine.dispose()
    print(
        f'index: {result.added} added, {result.updated} updated, '
        f'{result.unchanged} unchanged, {result.removed} removed'
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Index approved knowledge documents.')
    parser.add_argument('--root', type=Path, default=None, help='knowledge/ directory')
    args = parser.parse_args(argv)
    settings = get_settings()
    return asyncio.run(run(args.root or kb_root(settings), settings))


if __name__ == '__main__':
    sys.exit(main())
