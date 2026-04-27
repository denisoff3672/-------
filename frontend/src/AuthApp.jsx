import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from './api';

const labels = {
  uk: {
    title: 'Uklon Auth Portal',
    subtitle: 'Вхід та реєстрація користувачів',
    login: 'Увійти',
    register: 'Зареєструватись',
    logout: 'Вийти',
    email: 'Пошта',
    password: 'Пароль',
    switchToLogin: 'Вже є акаунт? Увійти',
    switchToRegister: 'Ще немає акаунта? Реєстрація',
    loading: 'Зачекайте…',
    loginSuccess: 'Успішний вхід',
    registerSuccess: 'Акаунт створено, ви авторизовані',
    signedOut: 'Сесію завершено',
    sessionRestored: 'Сесію відновлено через refresh token',
    role: 'Роль',
    blocked: 'Заблоковано',
    yes: 'Так',
    no: 'Ні',
    authHint: 'Введіть email і пароль, щоб увійти або створити акаунт.',
  },
  en: {
    title: 'Uklon Auth Portal',
    subtitle: 'Login and registration',
    login: 'Sign in',
    register: 'Sign up',
    logout: 'Logout',
    email: 'Email',
    password: 'Password',
    switchToLogin: 'Already have an account? Sign in',
    switchToRegister: "Don’t have an account yet? Sign up",
    loading: 'Please wait…',
    loginSuccess: 'Signed in successfully',
    registerSuccess: 'Account created and signed in',
    signedOut: 'Session closed',
    sessionRestored: 'Session restored from refresh token',
    role: 'Role',
    blocked: 'Blocked',
    yes: 'Yes',
    no: 'No',
    authHint: 'Use your email and password to sign in or create account.',
  },
};

function parseError(error) {
  try {
    const parsed = JSON.parse(error.message);
    return parsed.detail || error.message;
  } catch {
    return error.message;
  }
}

export default function AuthApp() {
  const [lang, setLang] = useState('uk');
  const t = useMemo(() => labels[lang], [lang]);

  const [mode, setMode] = useState('login');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');

  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);

  const [form, setForm] = useState({ email: '', password: '' });

  useEffect(() => {
    const restoreSession = async () => {
      try {
        setLoading(true);
        const refreshed = await apiRequest('/auth/refresh', { method: 'POST' });
        setToken(refreshed.accessToken);
        const me = await apiRequest('/auth/me', { method: 'GET' }, refreshed.accessToken);
        setUser(me);
        setMessageType('success');
        setMessage(t.sessionRestored);
      } catch {
        // no active session cookie
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, [t.sessionRestored]);

  const updateField = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleLogin = async () => {
    try {
      setLoading(true);
      const auth = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      setToken(auth.accessToken);

      const me = await apiRequest('/auth/me', { method: 'GET' }, auth.accessToken);
      setUser(me);
      setMessageType('success');
      setMessage(t.loginSuccess);
    } catch (error) {
      setMessageType('error');
      setMessage(parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    try {
      setLoading(true);
      const auth = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      setToken(auth.accessToken);

      const me = await apiRequest('/auth/me', { method: 'GET' }, auth.accessToken);
      setUser(me);
      setMessageType('success');
      setMessage(t.registerSuccess);
    } catch (error) {
      setMessageType('error');
      setMessage(parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await apiRequest('/auth/logout', { method: 'POST' }, token);
      }
      setToken('');
      setUser(null);
      setMessageType('success');
      setMessage(t.signedOut);
    } catch (error) {
      setMessageType('error');
      setMessage(parseError(error));
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (mode === 'login') {
      await handleLogin();
      return;
    }
    await handleRegister();
  };

  return (
    <main className="uklon-shell">
      <section className="auth-card">
        <div className="brand">
          <span className="brand-dot" />
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>

        <div className="lang-row">
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="uk">Українська</option>
            <option value="en">English</option>
          </select>
        </div>

        {!user ? (
          <form className="auth-form" onSubmit={submit}>
            <label htmlFor="email">{t.email}</label>
            <input
              id="email"
              type="email"
              name="email"
              value={form.email}
              onChange={updateField}
              autoComplete="email"
              placeholder="name@example.com"
              required
            />

            <label htmlFor="password">{t.password}</label>
            <input
              id="password"
              type="password"
              name="password"
              value={form.password}
              onChange={updateField}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder="••••••••"
              minLength={6}
              required
            />

            <button type="submit" className="primary" disabled={loading}>
              {loading ? t.loading : mode === 'login' ? t.login : t.register}
            </button>

            <button
              type="button"
              className="secondary"
              disabled={loading}
              onClick={() => setMode((prev) => (prev === 'login' ? 'register' : 'login'))}
            >
              {mode === 'login' ? t.switchToRegister : t.switchToLogin}
            </button>
          </form>
        ) : (
          <div className="profile-card">
            <h2>{form.email || user.username}</h2>
            <p>
              <strong>{t.role}:</strong> {user.role}
            </p>
            <p>
              <strong>{t.blocked}:</strong> {user.is_blocked ? t.yes : t.no}
            </p>

            <button type="button" className="primary" onClick={logout}>
              {t.logout}
            </button>
          </div>
        )}

        {message && <p className={`message ${messageType}`}>{message}</p>}
        {!user && <p className="hint">{t.authHint}</p>}
      </section>
    </main>
  );
}
