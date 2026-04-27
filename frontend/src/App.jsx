export { default } from './AuthApp';
/*
import { apiRequest } from './api';

const labels = {
  uk: {
    title: 'Інформаційна система диспетчерської служби таксі',
    login: 'Вхід',
    register: 'Реєстрація вимкнена',
    logout: 'Вийти',
    username: 'Логін',
    password: 'Пароль',
    role: 'Роль',
    phone: 'Телефон',
    license: 'Номер посвідчення',
    createOrder: 'Створити замовлення',
    orders: 'Історія замовлень',
    management: 'Керування',
    reports: 'Аналітика',
    driverStatus: 'Статус водія',
    language: 'Мова',
  },
  en: {
    title: 'Taxi Dispatch Information System',
    login: 'Login',
    register: 'Register',
    logout: 'Logout',
    username: 'Username',
    password: 'Password',
    role: 'Role',
    phone: 'Phone',
    license: 'License number',
    createOrder: 'Create order',
    orders: 'Orders history',
    management: 'Management',
    reports: 'Analytics',
    driverStatus: 'Driver status',
    language: 'Language',
  },
};
import { useEffect, useMemo, useState } from 'react';
const roles = ['client', 'driver', 'dispatcher'];
const comfortClasses = ['economy', 'standard', 'business'];

function App() {
    title: 'Uklon Driver/Auth Portal',
    subtitle: 'Швидкий вхід до системи служби таксі',
    login: 'Увійти',
    register: 'Зареєструватись',
    logout: 'Вийти',
    email: 'Пошта',
    password: 'Пароль',
    switchToLogin: 'Вже є акаунт? Увійти',
    switchToRegister: 'Ще немає акаунта? Реєстрація',
    loading: 'Зачекайте…',
    profile: 'Профіль',
    role: 'Роль',
    blocked: 'Заблоковано',
    no: 'Ні',
    yes: 'Так',
    signedIn: 'Ви успішно авторизовані',
    signedOut: 'Сесію завершено',
    sessionRestored: 'Сесію відновлено через refresh token',
    registerSuccess: 'Акаунт створено, ви увійшли автоматично',
    loginSuccess: 'Успішний вхід',
    loggedOutCard: 'Використайте email та пароль для входу або реєстрації',
  },
  en: {
    title: 'Uklon Driver/Auth Portal',
    subtitle: 'Fast sign-in for taxi dispatch service',
    login: 'Sign in',
    register: 'Sign up',
  const [token, setToken] = useState('');
    email: 'Email',
  const [message, setMessage] = useState('');
    switchToLogin: 'Already have an account? Sign in',
    switchToRegister: "Don’t have an account yet? Sign up",
    loading: 'Please wait…',
    profile: 'Profile',

    blocked: 'Blocked',
    no: 'No',
    yes: 'Yes',
    signedIn: 'You are authenticated',
    signedOut: 'Session closed',
    sessionRestored: 'Session restored from refresh token',
    registerSuccess: 'Account created and logged in automatically',
    loginSuccess: 'Signed in successfully',
    loggedOutCard: 'Use your email and password to sign in or sign up',
  },
};
    dropoff_lat: 50.4547,
    dropoff_lng: 30.5238,
    comfort_class: 'standard',
  });

  const [carForm, setCarForm] = useState({
    plate_number: '',
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [mode, setMode] = useState('login');
  const [loading, setLoading] = useState(false);
    color: '',
    comfort_class: 'standard',
    email: '',
  });
    base_fare: 45,

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
        // No active cookie session: stay on auth form silently.
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, [t.sessionRestored]);

  const login = async () => {
    try {
      const tokenData = await apiRequest('/auth/login', {

  const parseError = (error) => {
    try {
      const parsed = JSON.parse(error.message);
      return parsed.detail || error.message;
    } catch {
      return error.message;
    }
  };
        method: 'POST',
        body: JSON.stringify({ email: form.username, password: form.password }),
      });
      setLoading(true);
      setToken(tokenData.accessToken);
        email: form.email,
      const me = await apiRequest('/auth/me', { method: 'GET' }, tokenData.accessToken);
      setUser(me);
      setMessage(`✅ Logged in as ${me.role}`);
      const auth = await apiRequest('/auth/register', {
      setMessage(`❌ ${error.message}`);
    }
  };

      setToken(auth.accessToken);
      const me = await apiRequest('/auth/me', { method: 'GET' }, auth.accessToken);
      setUser(me);
      setMessageType('success');
      setMessage(t.registerSuccess);
    setToken('');
      setMessageType('error');
      setMessage(parseError(error));
    } finally {
      setLoading(false);
    setOrders([]);
    setMessage('Logged out');
  };

  const createOrder = async () => {
      setLoading(true);
    try {
      await apiRequest('/orders', { method: 'POST', body: JSON.stringify(orderForm) }, token);
        body: JSON.stringify({ email: form.email, password: form.password }),
      await loadOrders();
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };
      setMessageType('success');
      setMessage(t.loginSuccess);
  const loadOrders = async () => {
      setMessageType('error');
      setMessage(parseError(error));
    } finally {
      setLoading(false);
      const data = await apiRequest('/orders', { method: 'GET' }, token);
      setOrders(data);
    } catch (error) {
  const logout = async () => {
    try {
      if (token) {
        await apiRequest('/auth/logout', { method: 'POST' }, token);
      }
      await loadCars();
      setMessageType('error');
      setMessage(parseError(error));
      return;
      setMessage(`❌ ${error.message}`);

    setToken('');
    setUser(null);
    setMessageType('success');
    setMessage(t.signedOut);


  const onSubmit = async (event) => {
    event.preventDefault();
    if (mode === 'login') {
      await login();
      return;
    }
    await register();
  };
      <section className="card">
        <h2>{t.register}</h2>
    <main className="uklon-shell">
      <section className="auth-card">
        <div className="auth-top">
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
          <form className="auth-form" onSubmit={onSubmit}>
            <label htmlFor="email">{t.email}</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="name@example.com"
              value={form.email}
              onChange={updateForm}
              required
              autoComplete="email"
            />

            <label htmlFor="password">{t.password}</label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={updateForm}
              required
              minLength={6}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />

            <button className="primary" type="submit" disabled={loading}>
              {loading ? t.loading : mode === 'login' ? t.login : t.register}
            </button>

            <button
              className="secondary"
              type="button"
              disabled={loading}
              onClick={() => setMode((prev) => (prev === 'login' ? 'register' : 'login'))}
            >
              {mode === 'login' ? t.switchToRegister : t.switchToLogin}
            </button>
          </form>
        ) : (
          <div className="profile-card">
            <h2>{t.signedIn}</h2>
            <p>
              <strong>{t.email}:</strong> {user.username}
            </p>
            <p>
              <strong>{t.role}:</strong> {user.role}
            </p>
            <p>
              <strong>{t.blocked}:</strong> {user.is_blocked ? t.yes : t.no}
            </p>

            <button className="primary" type="button" onClick={logout}>
              {t.logout}
            </button>
          </div>
        )}

        {!!message && <p className={`message ${messageType}`}>{message}</p>}

        {!user && <p className="hint">{t.loggedOutCard}</p>}
      </section>
    </main>
                />
*/
