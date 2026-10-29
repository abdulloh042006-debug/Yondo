import { useState, type FormEvent } from 'react';
import { api, ApiError, type Schemas } from '../../api/client';
import { t, type Key } from '../../i18n';
import { Dialog } from '../../ui/feedback';
import { Select, TextArea } from '../../ui/form';

type Category = Schemas['StoryReportWrite']['category'];
const CATEGORIES: Category[] = ['inappropriate_request', 'fake_profile', 'fraud', 'other'];

/**
 * Report one card. Reports go to manual review: the text never claims the card was removed or the author told.
 * Guests are asked to sign in first (the endpoint needs a session).
 */
export function ReportStory({ storyId, signedIn, onClose, onSignIn }: { storyId: string; signedIn: boolean; onClose: () => void; onSignIn: () => void }) {
  const [category, setCategory] = useState<Category>('inappropriate_request');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<'sent' | 'already'>();
  const [err, setErr] = useState<ApiError>();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(undefined);
    try {
      await api.post(`/discovery/stories/${storyId}/report`, { category, description: description.trim() });
      setResult('sent');
    } catch (error) {
      const apiError = error instanceof ApiError ? error : new ApiError(0, 'network_error');
      if (apiError.code === 'story_already_reported') setResult('already');
      else setErr(apiError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open title={t('stories.report')} onClose={onClose}>
      {!signedIn ? (
        <div className="stack">
          <p className="muted">{t('stories.report.signIn')}</p>
          <div className="row">
            <button type="button" className="btn" onClick={onSignIn}>{t('nav.login')}</button>
            <button type="button" className="btn ghost" onClick={onClose}>{t('common.cancel')}</button>
          </div>
        </div>
      ) : result ? (
        <div className="stack">
          <p role="status">{result === 'sent' ? t('stories.report.sent') : t('stories.report.already')}</p>
          <div className="row"><button type="button" className="btn" onClick={onClose}>{t('stories.report.done')}</button></div>
        </div>
      ) : (
        <form className="stack" onSubmit={(e) => void submit(e)} noValidate>
          <Select label={t('reportForm.category')} value={category} onChange={(e) => setCategory(e.target.value as Category)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{t(`stories.report.cat.${c}` as Key)}</option>)}
          </Select>
          <TextArea label={t('stories.report.description')} rows={3} maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} hint={t('stories.report.note')} />
          {err && <p className="err" role="alert">{err.message}</p>}
          <div className="row">
            <button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('reportForm.send')}</button>
            <button type="button" className="btn ghost" onClick={onClose}>{t('common.cancel')}</button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
