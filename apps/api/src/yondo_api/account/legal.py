"""Current versions of the public legal documents.

The web app renders the matching text (apps/web/src/legal) and sends the version back when the user
accepts it; a mismatch is refused, so text and recorded consent can never drift apart silently.
Bump a version whenever the document changes materially: every user is then asked to accept again.
"""

LEGAL_DOCUMENTS: dict[str, str] = {
    'terms': '2026-10-23-draft',
    'privacy': '2026-10-23-draft',
}

# Personal data is erased (or irreversibly de-identified) within this many days of a confirmed
# deletion request (owner decision 2026-10-23). The request becomes due one day earlier so that a
# daily job still finishes inside the window.
DELETION_WINDOW_DAYS = 30
DELETION_DUE_AFTER_DAYS = DELETION_WINDOW_DAYS - 1
