import { MotionConfig } from 'motion/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { AuthProvider } from './auth/AuthContext';
import { applySavedLang, LanguageBoundary } from './i18n';
import { ToastProvider } from './ui/feedback';
import { applySavedTheme } from './ui/theme';
import './styles.css';

applySavedTheme();
await applySavedLang();

// One delegated listener feeds the cursor position to every `.spot` surface (CSS does the rest).
document.addEventListener(
  'pointermove',
  (e) => {
    const el = (e.target as HTMLElement | null)?.closest?.<HTMLElement>('.spot');
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
  },
  { passive: true },
);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* "user" honours prefers-reduced-motion for every motion component. */}
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <LanguageBoundary>
              <App />
            </LanguageBoundary>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </MotionConfig>
  </StrictMode>,
);
