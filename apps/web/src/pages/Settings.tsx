import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Reveal } from '../ui/motion';
import { ThemePicker } from '../ui/theme';

export function Settings() {
  const { user } = useAuth();
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h1>Sozlamalar</h1>
      <Reveal>
        <section className="glass pad stack" aria-labelledby="look-h">
          <h2 id="look-h">Ko‘rinish</h2>
          <p className="muted">Ilova rangini tanlang. Tanlov faqat shu qurilmada saqlanadi.</p>
          <ThemePicker />
        </section>
      </Reveal>
      <Reveal delay={0.05}>
        <section className="glass pad stack" aria-labelledby="acc-h">
          <h2 id="acc-h">Hisob</h2>
          {user ? (
            <Link className="btn" to="/account" style={{ width: 'fit-content' }}>Hisobim va shaxsiy ma’lumotlar</Link>
          ) : (
            <Link className="btn" to="/login" style={{ width: 'fit-content' }}>Kirish</Link>
          )}
        </section>
      </Reveal>
    </div>
  );
}
