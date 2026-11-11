"""Knowledge-base documents for the AI assistant: metadata schema and validator.

Layout (see knowledge/README.md): ``knowledge/{public,internal,shared}/**/*.md``.
Each document starts with TOML front-matter between ``+++`` lines (stdlib ``tomllib``, so no
new dependency), followed by one ``## <language>`` section per declared language.

Only documents with ``status = "approved"`` are indexable. Anything else (draft, review,
deprecated) is validated but never handed to retrieval, so unapproved text cannot reach an
answer.

Usage: ``python -m yondo_api.assistant.kb --check [--root PATH]`` (exit 1 on any error).
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

AUDIENCES = ('public', 'internal', 'shared')
STATUSES = ('draft', 'review', 'approved', 'deprecated')
LANGUAGES = ('uz', 'ru', 'en')
REQUIRED = (
    'id',
    'title',
    'audience',
    'languages',
    'category',
    'status',
    'version',
    'source',
    'updated_at',
)
SLUG = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)*$')
SECTION = re.compile(r'^## (uz|ru|en)\s*$', re.MULTILINE)
DEFAULT_ROOT = Path(__file__).resolve().parents[5] / 'knowledge'


@dataclass(frozen=True, slots=True)
class KnowledgeDoc:
    path: Path
    id: str
    title: str
    audience: str
    languages: tuple[str, ...]
    category: str
    status: str
    version: int
    source: str
    updated_at: date
    sections: dict[str, str]

    @property
    def indexable(self) -> bool:
        return self.status == 'approved'


class KnowledgeError(ValueError):
    pass


def split_front_matter(text: str) -> tuple[str, str]:
    lines = text.split('\n')
    if not lines or lines[0].strip() != '+++':
        raise KnowledgeError('missing front-matter: the file must start with a "+++" line')
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '+++':
            return '\n'.join(lines[1:i]), '\n'.join(lines[i + 1 :])
    raise KnowledgeError('front-matter is not closed by a "+++" line')


def parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(SECTION.finditer(body))
    for n, match in enumerate(matches):
        end = matches[n + 1].start() if n + 1 < len(matches) else len(body)
        lang = match.group(1)
        if lang in sections:
            raise KnowledgeError(f'duplicate "## {lang}" section')
        sections[lang] = body[match.end() : end].strip()
    return sections


def parse_doc(path: Path, root: Path) -> KnowledgeDoc:
    raw, body = split_front_matter(path.read_text(encoding='utf-8'))
    try:
        meta = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        raise KnowledgeError(f'front-matter is not valid TOML: {exc}') from exc

    missing = [key for key in REQUIRED if key not in meta]
    if missing:
        raise KnowledgeError(f'missing metadata: {", ".join(missing)}')
    unknown = sorted(set(meta) - set(REQUIRED))
    if unknown:
        raise KnowledgeError(f'unknown metadata: {", ".join(unknown)}')

    for key in ('id', 'title', 'audience', 'category', 'status', 'source'):
        if not isinstance(meta[key], str) or not meta[key].strip():
            raise KnowledgeError(f'{key} must be a non-empty string')
    if not SLUG.match(meta['id']):
        raise KnowledgeError('id must be a lowercase slug (a-z, 0-9, "-" or ".")')
    if not SLUG.match(meta['category']):
        raise KnowledgeError('category must be a lowercase slug')
    if meta['audience'] not in AUDIENCES:
        raise KnowledgeError(f'audience must be one of {AUDIENCES}')
    folder = path.relative_to(root).parts[0]
    if folder != meta['audience']:
        raise KnowledgeError(f'audience "{meta["audience"]}" does not match folder "{folder}/"')
    if meta['status'] not in STATUSES:
        raise KnowledgeError(f'status must be one of {STATUSES}')
    version = meta['version']
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise KnowledgeError('version must be an integer >= 1')
    updated = meta['updated_at']
    if type(updated) is not date:  # a TOML local date (YYYY-MM-DD), not a datetime
        raise KnowledgeError('updated_at must be a date (YYYY-MM-DD)')

    languages = meta['languages']
    if (
        not isinstance(languages, list)
        or not languages
        or any(lang not in LANGUAGES for lang in languages)
        or len(set(languages)) != len(languages)
    ):
        raise KnowledgeError(
            f'languages must be a non-empty list of distinct values from {LANGUAGES}'
        )

    sections = parse_sections(body)
    if set(sections) != set(languages):
        raise KnowledgeError(
            f'sections {sorted(sections)} do not match languages {sorted(languages)}'
        )
    empty = [lang for lang, text in sections.items() if not text]
    if empty:
        raise KnowledgeError(f'empty section(s): {", ".join(empty)}')

    return KnowledgeDoc(
        path=path,
        id=meta['id'],
        title=meta['title'],
        audience=meta['audience'],
        languages=tuple(languages),
        category=meta['category'],
        status=meta['status'],
        version=version,
        source=meta['source'],
        updated_at=updated,
        sections=sections,
    )


def doc_paths(root: Path) -> list[Path]:
    """Every knowledge document. README.md files describe folders and are not documents."""
    return sorted(
        path
        for audience in AUDIENCES
        for path in (root / audience).rglob('*.md')
        if path.name != 'README.md'
    )


def load(root: Path = DEFAULT_ROOT) -> tuple[list[KnowledgeDoc], list[str]]:
    """Parse every document under ``root``; return the valid ones and one message per problem."""
    docs: list[KnowledgeDoc] = []
    errors: list[str] = []
    if not root.is_dir():
        return docs, [f'{root}: knowledge root not found']
    for path in doc_paths(root):
        try:
            docs.append(parse_doc(path, root))
        except (KnowledgeError, OSError, UnicodeDecodeError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    seen: dict[str, Path] = {}
    for doc in docs:
        if doc.id in seen:
            errors.append(
                f'{doc.path.relative_to(root)}: duplicate id "{doc.id}" '
                f'(also {seen[doc.id].relative_to(root)})'
            )
        seen.setdefault(doc.id, doc.path)
    return docs, errors


def indexable(docs: list[KnowledgeDoc]) -> list[KnowledgeDoc]:
    """The only documents retrieval may use: approved ones."""
    return [doc for doc in docs if doc.indexable]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate the assistant knowledge base.')
    parser.add_argument('--check', action='store_true', help='validate and exit 1 on any error')
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT, help='knowledge/ directory')
    args = parser.parse_args(argv)
    docs, errors = load(args.root)
    for error in errors:
        print(f'ERROR {error}')
    statuses = Counter(doc.status for doc in docs)
    summary = ', '.join(f'{status} {statuses[status]}' for status in STATUSES)
    print(
        f'knowledge: {len(docs)} valid, {len(errors)} error(s); {summary}; '
        f'indexable {len(indexable(docs))}'
    )
    return 1 if errors and args.check else 0


if __name__ == '__main__':
    sys.exit(main())
