import { useMemo, useState } from 'react';
import { apiRequest } from './api';

const labels = {
  uk: {
    title: 'Інформаційна система диспетчерської служби таксі',
    login: 'Вхід',
    register: 'Реєстрація',
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

const roles = ['client', 'driver', 'dispatcher', 'admin'];
const comfortClasses = ['economy', 'standard', 'business'];

function App() {
  const [lang, setLang] = useState('uk');
  const t = useMemo(() => labels[lang], [lang]);

  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);
  const [message, setMessage] = useState('');

  const [form, setForm] = useState({
    username: '',
    password: '',
    role: 'client',
    phone: '',
    license_number: '',
  });

  const [orderForm, setOrderForm] = useState({
    pickup_address: 'Kyiv, Khreshchatyk',
    dropoff_address: 'Kyiv, Maidan',
    pickup_lat: 50.4501,
    pickup_lng: 30.5234,
    dropoff_lat: 50.4547,
    dropoff_lng: 30.5238,
    comfort_class: 'standard',
  });

  const [carForm, setCarForm] = useState({
    plate_number: '',
    model: '',
    color: '',
    comfort_class: 'standard',
    technical_status: 'good',
  });

  const [tariffForm, setTariffForm] = useState({
    comfort_class: 'standard',
    base_fare: 45,
    price_per_km: 15,
    price_per_minute: 2,
    night_multiplier: 1.15,
  });

  const [orders, setOrders] = useState([]);
  const [cars, setCars] = useState([]);
  const [tariffs, setTariffs] = useState([]);
  const [report, setReport] = useState(null);

  const canManage = user?.role === 'admin' || user?.role === 'dispatcher';

  const updateForm = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const register = async () => {
    try {
      const payload = {
        username: form.username,
        password: form.password,
        role: form.role,
        ...(form.role === 'client' ? { phone: form.phone } : {}),
        ...(form.role === 'driver' ? { license_number: form.license_number } : {}),
      };

      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setMessage('✅ Registered successfully');
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const login = async () => {
    try {
      const tokenData = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: form.username, password: form.password }),
      });
      setToken(tokenData.access_token);

      const me = await apiRequest('/auth/me', { method: 'GET' }, tokenData.access_token);
      setUser(me);
      setMessage(`✅ Logged in as ${me.role}`);
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const logout = () => {
    setToken('');
    setUser(null);
    setOrders([]);
    setMessage('Logged out');
  };

  const createOrder = async () => {
    try {
      await apiRequest('/orders', { method: 'POST', body: JSON.stringify(orderForm) }, token);
      setMessage('✅ Order created');
      await loadOrders();
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const loadOrders = async () => {
    try {
      const data = await apiRequest('/orders', { method: 'GET' }, token);
      setOrders(data);
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const updateDriverStatus = async (status) => {
    try {
      await apiRequest(
        '/management/drivers/me/status',
        { method: 'PATCH', body: JSON.stringify({ status }) },
        token
      );
      setMessage('✅ Driver status updated');
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const createCar = async () => {
    try {
      await apiRequest('/management/cars', { method: 'POST', body: JSON.stringify(carForm) }, token);
      setMessage('✅ Car added');
      await loadCars();
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const loadCars = async () => {
    try {
      const data = await apiRequest('/management/cars', { method: 'GET' }, token);
      setCars(data);
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const saveTariff = async () => {
    try {
      await apiRequest('/management/tariffs', { method: 'POST', body: JSON.stringify(tariffForm) }, token);
      setMessage('✅ Tariff saved');
      await loadTariffs();
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const loadTariffs = async () => {
    try {
      const data = await apiRequest('/management/tariffs', { method: 'GET' }, token);
      setTariffs(data);
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  const loadReport = async () => {
    const start = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString();
    const end = new Date().toISOString();

    try {
      const data = await apiRequest(
        `/management/reports/summary?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
        { method: 'GET' },
        token
      );
      setReport(data);
    } catch (error) {
      setMessage(`❌ ${error.message}`);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>{t.title}</h1>
        <div className="top-row">
          <label>
            {t.language}:
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              <option value="uk">Українська</option>
              <option value="en">English</option>
            </select>
          </label>

          {user && (
            <button onClick={logout} type="button">
              {t.logout}
            </button>
          )}
        </div>
      </header>

      <section className="card">
        <h2>{t.register}</h2>
        <div className="grid">
          <input name="username" placeholder={t.username} value={form.username} onChange={updateForm} />
          <input
            name="password"
            type="password"
            placeholder={t.password}
            value={form.password}
            onChange={updateForm}
          />
          <select name="role" value={form.role} onChange={updateForm}>
            {roles.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          <input name="phone" placeholder={t.phone} value={form.phone} onChange={updateForm} />
          <input
            name="license_number"
            placeholder={t.license}
            value={form.license_number}
            onChange={updateForm}
          />
        </div>
        <div className="actions">
          <button onClick={register} type="button">
            {t.register}
          </button>
          <button onClick={login} type="button">
            {t.login}
          </button>
        </div>
      </section>

      {user && (
        <>
          {(user.role === 'client' || user.role === 'dispatcher' || user.role === 'admin') && (
            <section className="card">
              <h2>{t.createOrder}</h2>
              <div className="grid">
                <input
                  value={orderForm.pickup_address}
                  onChange={(e) => setOrderForm((p) => ({ ...p, pickup_address: e.target.value }))}
                />
                <input
                  value={orderForm.dropoff_address}
                  onChange={(e) => setOrderForm((p) => ({ ...p, dropoff_address: e.target.value }))}
                />
                <input
                  type="number"
                  value={orderForm.pickup_lat}
                  onChange={(e) => setOrderForm((p) => ({ ...p, pickup_lat: Number(e.target.value) }))}
                />
                <input
                  type="number"
                  value={orderForm.pickup_lng}
                  onChange={(e) => setOrderForm((p) => ({ ...p, pickup_lng: Number(e.target.value) }))}
                />
                <input
                  type="number"
                  value={orderForm.dropoff_lat}
                  onChange={(e) => setOrderForm((p) => ({ ...p, dropoff_lat: Number(e.target.value) }))}
                />
                <input
                  type="number"
                  value={orderForm.dropoff_lng}
                  onChange={(e) => setOrderForm((p) => ({ ...p, dropoff_lng: Number(e.target.value) }))}
                />
                <select
                  value={orderForm.comfort_class}
                  onChange={(e) => setOrderForm((p) => ({ ...p, comfort_class: e.target.value }))}
                >
                  {comfortClasses.map((comfort) => (
                    <option key={comfort} value={comfort}>
                      {comfort}
                    </option>
                  ))}
                </select>
              </div>
              <div className="actions">
                <button onClick={createOrder}>{t.createOrder}</button>
                <button onClick={loadOrders}>{t.orders}</button>
              </div>
              <ul>
                {orders.map((order) => (
                  <li key={order.id}>
                    #{order.id} {order.pickup_address} → {order.dropoff_address} | {order.status} |{' '}
                    {order.estimated_cost} UAH
                  </li>
                ))}
              </ul>
            </section>
          )}

          {user.role === 'driver' && (
            <section className="card">
              <h2>{t.driverStatus}</h2>
              <div className="actions">
                <button onClick={() => updateDriverStatus('free')}>Free</button>
                <button onClick={() => updateDriverStatus('break')}>Break</button>
                <button onClick={() => updateDriverStatus('inactive')}>Inactive</button>
              </div>
              <button onClick={loadOrders}>{t.orders}</button>
              <ul>
                {orders.map((order) => (
                  <li key={order.id}>
                    #{order.id} {order.pickup_address} → {order.dropoff_address} | {order.status}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {canManage && (
            <section className="card">
              <h2>{t.management}</h2>
              <h3>Cars</h3>
              <div className="grid">
                <input
                  placeholder="Plate"
                  value={carForm.plate_number}
                  onChange={(e) => setCarForm((p) => ({ ...p, plate_number: e.target.value }))}
                />
                <input
                  placeholder="Model"
                  value={carForm.model}
                  onChange={(e) => setCarForm((p) => ({ ...p, model: e.target.value }))}
                />
                <input
                  placeholder="Color"
                  value={carForm.color}
                  onChange={(e) => setCarForm((p) => ({ ...p, color: e.target.value }))}
                />
                <select
                  value={carForm.comfort_class}
                  onChange={(e) => setCarForm((p) => ({ ...p, comfort_class: e.target.value }))}
                >
                  {comfortClasses.map((comfort) => (
                    <option key={comfort} value={comfort}>
                      {comfort}
                    </option>
                  ))}
                </select>
              </div>
              <div className="actions">
                <button onClick={createCar}>Add Car</button>
                <button onClick={loadCars}>Load Cars</button>
              </div>
              <ul>
                {cars.map((car) => (
                  <li key={car.id}>
                    {car.plate_number} | {car.model} | {car.comfort_class}
                  </li>
                ))}
              </ul>

              <h3>Tariffs</h3>
              <div className="grid">
                <select
                  value={tariffForm.comfort_class}
                  onChange={(e) => setTariffForm((p) => ({ ...p, comfort_class: e.target.value }))}
                >
                  {comfortClasses.map((comfort) => (
                    <option key={comfort} value={comfort}>
                      {comfort}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  value={tariffForm.base_fare}
                  onChange={(e) => setTariffForm((p) => ({ ...p, base_fare: Number(e.target.value) }))}
                />
                <input
                  type="number"
                  value={tariffForm.price_per_km}
                  onChange={(e) => setTariffForm((p) => ({ ...p, price_per_km: Number(e.target.value) }))}
                />
                <input
                  type="number"
                  value={tariffForm.price_per_minute}
                  onChange={(e) =>
                    setTariffForm((p) => ({ ...p, price_per_minute: Number(e.target.value) }))
                  }
                />
                <input
                  type="number"
                  value={tariffForm.night_multiplier}
                  onChange={(e) =>
                    setTariffForm((p) => ({ ...p, night_multiplier: Number(e.target.value) }))
                  }
                />
              </div>
              <div className="actions">
                <button onClick={saveTariff}>Save Tariff</button>
                <button onClick={loadTariffs}>Load Tariffs</button>
              </div>
              <ul>
                {tariffs.map((tariff) => (
                  <li key={tariff.id}>
                    {tariff.comfort_class} → {tariff.price_per_km} UAH/km
                  </li>
                ))}
              </ul>
            </section>
          )}

          {canManage && (
            <section className="card">
              <h2>{t.reports}</h2>
              <button onClick={loadReport}>Load 30 days report</button>
              {report && (
                <div>
                  <p>Total orders: {report.total_orders}</p>
                  <p>Completed orders: {report.completed_orders}</p>
                  <p>Revenue: {report.revenue} UAH</p>
                </div>
              )}
            </section>
          )}
        </>
      )}

      {!!message && <p className="message">{message}</p>}
    </div>
  );
}

export default App;
