import { useState, type FormEvent } from 'react';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { REPORT_CATEGORY } from '../lib/labels';
import { Dialog, useToast } from './feedback';
import { Select, TextArea } from './form';

type Category = Schemas['ReportWrite']['category'];

/**
 * Report the other participant of a booking. Only `booking_id` is sent: the server derives who that is, so a
 * customer never needs (or sees in the UI) a companion's user id, and a profile id is never sent as a user id.
 */
export function ReportDialog({ bookingId, aboutCompanion, onClose }: { bookingId: string; aboutCompanion: boolean; onClose: () => void }) {
  const toast = useToast();
  const [category, setCategory] = useState<Category>('other');
  const [description, setDescription] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const missing = description.trim() === '';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (missing) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.post('/safety/reports', { booking_id: bookingId, category, description: description.trim() });
      toast.push('ok', t('reportForm.sent'));
      onClose();
    } catch (error) {
      setErr(error instanceof ApiError ? error : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open title={t('reportForm.action')} onClose={onClose}>
      <form className="stack" onSubmit={submit} noValidate>
        <p className="muted">{aboutCompanion ? t('reportForm.aboutCompanion') : t('reportForm.aboutCustomer')}</p>
        <Select label={t('reportForm.category')} value={category} onChange={(e) => setCategory(e.target.value as Category)}>
          {Object.entries(REPORT_CATEGORY).map(([code, label]) => (
            <option key={code} value={code}>{label}</option>
          ))}
        </Select>
        <TextArea
          label={t('reportForm.description')}
          rows={4}
          maxLength={4000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          error={touched && missing ? t('reportForm.descriptionRequired') : err?.fields.description}
        />
        <p className="hint">{t('reportForm.note')}</p>
        {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
        <div className="row">
          <button className="btn" disabled={busy}>{busy && <span className="spinner" aria-hidden="true" />}{t('reportForm.send')}</button>
          <button type="button" className="btn ghost" onClick={onClose}>{t('common.cancel')}</button>
        </div>
      </form>
    </Dialog>
  );
}
