import re
from pathlib import Path

import pytest

from yondo_api.assistant import kb

REPO = Path(__file__).resolve().parents[3]
I18N = REPO / 'apps' / 'web' / 'src' / 'i18n'

GOOD = """+++
id = "faq.sample"
title = "Sample"
audience = "public"
languages = ["uz", "en"]
category = "faq"
status = "approved"
version = 1
source = "test"
updated_at = 2026-11-10
+++

## uz

Matn.

## en

Text.
"""


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_valid_document_is_parsed_and_indexable(tmp_path):
    write(tmp_path, 'public/faq/sample.md', GOOD)
    docs, errors = kb.load(tmp_path)
    assert errors == []
    [doc] = docs
    assert doc.id == 'faq.sample'
    assert doc.languages == ('uz', 'en')
    assert doc.sections == {'uz': 'Matn.', 'en': 'Text.'}
    assert kb.indexable(docs) == docs


@pytest.mark.parametrize('status', ['draft', 'review', 'deprecated'])
def test_only_approved_documents_are_indexable(tmp_path, status):
    write(tmp_path, 'public/a.md', GOOD.replace('status = "approved"', f'status = "{status}"'))
    docs, errors = kb.load(tmp_path)
    assert errors == [] and len(docs) == 1
    assert kb.indexable(docs) == []


@pytest.mark.parametrize(
    ('change', 'message'),
    [
        (('id = "faq.sample"\n', ''), 'missing metadata: id'),
        (('updated_at = 2026-11-10\n', ''), 'missing metadata: updated_at'),
        (('version = 1\n', 'version = 1\nowner = "x"\n'), 'unknown metadata: owner'),
        (('status = "approved"', 'status = "published"'), 'status must be one of'),
        (('audience = "public"', 'audience = "everyone"'), 'audience must be one of'),
        (('audience = "public"', 'audience = "internal"'), 'does not match folder'),
        (('languages = ["uz", "en"]', 'languages = ["uz", "de"]'), 'languages must be'),
        (('languages = ["uz", "en"]', 'languages = ["uz", "uz"]'), 'languages must be'),
        (('languages = ["uz", "en"]', 'languages = ["uz", "ru", "en"]'), 'do not match languages'),
        (('version = 1', 'version = 0'), 'version must be'),
        (('version = 1', 'version = "1"'), 'version must be'),
        (('updated_at = 2026-11-10', 'updated_at = "2026-11-10"'), 'updated_at must be a date'),
        (('updated_at = 2026-11-10', 'updated_at = 2026-11-10T10:00:00Z'), 'updated_at must be'),
        (('id = "faq.sample"', 'id = "FAQ Sample"'), 'id must be a lowercase slug'),
        (('title = "Sample"', 'title = ""'), 'title must be a non-empty string'),
        (('Text.\n', ''), 'empty section'),
        (('title = "Sample"', 'title = "Sample'), 'not valid TOML'),
    ],
)
def test_invalid_metadata_is_rejected(tmp_path, change, message):
    old, new = change
    assert GOOD.count(old) == 1
    write(tmp_path, 'public/a.md', GOOD.replace(old, new))
    docs, errors = kb.load(tmp_path)
    assert docs == []
    assert len(errors) == 1 and message in errors[0], errors


def test_missing_or_unclosed_front_matter_is_rejected(tmp_path):
    write(tmp_path, 'public/no-front.md', '## uz\n\nMatn.\n')
    write(tmp_path, 'public/unclosed.md', GOOD.replace('+++\n\n## uz', '\n## uz'))
    docs, errors = kb.load(tmp_path)
    assert docs == []
    assert any('missing front-matter' in e for e in errors)
    assert any('not closed' in e for e in errors)


def test_duplicate_ids_are_rejected(tmp_path):
    write(tmp_path, 'public/a.md', GOOD)
    write(tmp_path, 'public/b.md', GOOD)
    _, errors = kb.load(tmp_path)
    assert len(errors) == 1 and 'duplicate id "faq.sample"' in errors[0]


def test_readme_files_and_other_folders_are_not_documents(tmp_path):
    write(tmp_path, 'public/README.md', '# not a document')
    write(tmp_path, 'drafts/x.md', '# outside the audience folders')
    docs, errors = kb.load(tmp_path)
    assert docs == [] and errors == []


def test_cli_check_exit_codes(tmp_path, capsys):
    write(tmp_path, 'public/a.md', GOOD)
    assert kb.main(['--check', '--root', str(tmp_path)]) == 0
    assert 'indexable 1' in capsys.readouterr().out
    write(tmp_path, 'public/b.md', GOOD.replace('status = "approved"', 'status = "ok"'))
    assert kb.main(['--check', '--root', str(tmp_path)]) == 1
    assert 'ERROR public/b.md' in capsys.readouterr().out


def test_repository_knowledge_base_is_valid():
    docs, errors = kb.load(kb.DEFAULT_ROOT)
    assert errors == []
    assert {doc.id for doc in docs} >= {f'faq.{k}' for k in FAQ_KEYS}


FAQ_KEYS = ('what', 'book', 'pay', 'cancel', 'verified', 'companion', 'privacy', 'delete', 'data')


def i18n_faq(lang: str) -> dict[str, dict[str, str]]:
    pattern = re.compile(r"^  'help\.faq\.([a-z]+)\.([qa])': '([^'\\]*)',?$", re.MULTILINE)
    found: dict[str, dict[str, str]] = {}
    for key, kind, text in pattern.findall((I18N / f'{lang}.ts').read_text(encoding='utf-8')):
        found.setdefault(key, {})[kind] = text
    return found


def test_seed_faq_is_verbatim_from_the_web_app_and_approved():
    docs = {doc.id: doc for doc in kb.load(kb.DEFAULT_ROOT)[0]}
    strings = {lang: i18n_faq(lang) for lang in kb.LANGUAGES}
    assert set(strings['uz']) == set(FAQ_KEYS)
    for key in FAQ_KEYS:
        doc = docs[f'faq.{key}']
        assert doc.audience == 'public' and doc.category == 'faq'
        assert doc.status == 'approved'  # CEO approval (decision Q5), after the verifier review
        for lang in kb.LANGUAGES:
            entry = strings[lang][key]
            assert doc.sections[lang] == f'### {entry["q"]}\n\n{entry["a"]}', (key, lang)
