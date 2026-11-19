/**
 * Must equal `LEGAL_DOCUMENTS` in apps/api/src/yondo_api/account/legal.py: the server refuses consent to any
 * other version (`consent_version_outdated`), so the text shown and the consent recorded cannot drift apart.
 */
export const LEGAL_VERSIONS = { terms: '2026-11-19-draft', privacy: '2026-11-19-draft' } as const;
export type LegalDoc = keyof typeof LEGAL_VERSIONS;
