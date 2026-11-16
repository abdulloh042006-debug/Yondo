import { t } from '../i18n';
import { useId, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react';

interface Common {
  label: string;
  hint?: ReactNode;
  error?: string;
}

/** `live`: a polite status line under the field (e.g. "username available"), tied to it like the hint. */
export function Field({ label, hint, error, live, ...rest }: Common & { live?: ReactNode } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  const described = [error ? `${id}-e` : hint ? `${id}-h` : null, live !== undefined ? `${id}-s` : null].filter(Boolean).join(' ');
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        className="input"
        aria-invalid={!!error}
        aria-describedby={described || undefined}
        {...rest}
      />
      {live !== undefined && (
        <span id={`${id}-s`} role="status" className="hint">
          {live}
        </span>
      )}
      {error ? (
        <span id={`${id}-e`} className="err" role="alert">
          {error}
        </span>
      ) : (
        hint && (
          <span id={`${id}-h`} className="hint">
            {hint}
          </span>
        )
      )}
    </div>
  );
}

export function TextArea({ label, hint, error, ...rest }: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} className="input" aria-invalid={!!error} {...rest} />
      {error ? (
        <span className="err" role="alert">
          {error}
        </span>
      ) : (
        hint && <span className="hint">{hint}</span>
      )}
    </div>
  );
}

export function Select({
  label,
  error,
  children,
  ...rest
}: Common & React.SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} className="input" aria-invalid={!!error} {...rest}>
        {children}
      </select>
      {error && (
        <span className="err" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

/** One "show password" box per form; it changes every password field of that form. */
export function ShowPassword({ id, checked, onChange }: { id: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="consent" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{t('login.pw.show')}</span>
    </label>
  );
}
