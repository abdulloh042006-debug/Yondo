import { api } from '../api/client';
import { LEGAL_VERSIONS, type LegalDoc } from './versions';

/** Records acceptance of the document versions this client shows. The server refuses any other version. */
export async function acceptLegal(docs: readonly LegalDoc[] = ['terms', 'privacy']) {
  for (const document of docs) {
    await api.post('/account/consents', { document, version: LEGAL_VERSIONS[document] });
  }
}
