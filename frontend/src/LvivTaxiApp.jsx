import { useEffect, useMemo, useState } from 'react';
import { API_URL, apiRequest } from './api';

const CLASS_ORDER = ['economy', 'standard', 'comfort', 'business'];
const CLASS_LABELS = {
  economy: 'Економ',
  standard: 'Стандарт',
  comfort: 'Комфорт',
  business: 'Бізнес',
};

const UKR_FIRST_NAMES = ['Олександр', 'Андрій', 'Тарас', 'Іван', 'Василь', 'Дмитро', 'Максим', 'Роман', 'Богдан', 'Ярослав'];
const UKR_LAST_NAMES = ['Коваль', 'Шевченко', 'Мельник', 'Бондар', 'Ткачук', 'Кравченко', 'Олійник', 'Поліщук', 'Бойко', 'Савчук'];

const DRIVER_STATUS_LABELS = {
  free: 'В роботі',
  on_order: 'На замовленні',
  break: 'Пауза',
  inactive: 'Неактивний',
};

const ORDER_STATUS_LABELS = {
  pending: 'Очікує підтвердження',
  assigned: 'Прийнято водієм',
  driver_arrived: 'Водій на місці',
  in_progress: 'Поїздка триває',
  completed: 'Виконано',
  cancelled: 'Скасовано',
};
const ACTIVE_CLIENT_ORDER_STATUSES = new Set(['pending', 'assigned', 'driver_arrived', 'in_progress']);
const LVIV_BOUNDS = {
  minLat: 49.77,
  maxLat: 49.9,
  minLng: 23.9,
  maxLng: 24.1,
};

function parseError(error) {
  try {
    const parsed = JSON.parse(error.message);
    return parsed.detail || error.message;
  } catch {
    return error.message;
  }
}

function classRank(className) {
  return CLASS_ORDER.indexOf(className) + 1;
}

function money(value) {
  if (value === undefined || value === null) return '-';
  return `${Number(value).toFixed(2)} грн`;
}

function shortAddress(value) {
  if (!value) return '-';
  const parts = value.split(',').map((item) => item.trim()).filter(Boolean);
  return parts.slice(0, 2).join(', ') || value;
}

function displayDriverName(name, driverId) {
  if (!name) return 'Невідомий водій';
  if (!/driver\d+/i.test(name) && !/import/i.test(name)) return name;
  const base = Number(driverId) || name.length;
  const first = UKR_FIRST_NAMES[base % UKR_FIRST_NAMES.length];
  const last = UKR_LAST_NAMES[Math.floor(base / UKR_FIRST_NAMES.length) % UKR_LAST_NAMES.length];
  return `${first} ${last}`;
}

function buildGoogleMapUrl(pickup, dropoff) {
  if (pickup?.lat && pickup?.lng && dropoff?.lat && dropoff?.lng) {
    return `https://www.google.com/maps?output=embed&hl=uk&saddr=${pickup.lat},${pickup.lng}&daddr=${dropoff.lat},${dropoff.lng}`;
  }
  if (pickup?.lat && pickup?.lng) {
    return `https://www.google.com/maps?output=embed&hl=uk&q=${pickup.lat},${pickup.lng}`;
  }
  return '';
}

function isWithinLviv(lat, lng) {
  return lat >= LVIV_BOUNDS.minLat && lat <= LVIV_BOUNDS.maxLat && lng >= LVIV_BOUNDS.minLng && lng <= LVIV_BOUNDS.maxLng;
}

async function geocodeAddress(query) {
  const normalized = query.trim();
  if (!normalized) throw new Error('Вкажіть адресу');
  const lvivQuery = /львів/i.test(normalized) ? normalized : `${normalized}, Львів`;
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=uk&q=${encodeURIComponent(lvivQuery)}`
  );
  if (!response.ok) throw new Error('Не вдалося знайти адресу');

  const data = await response.json();
  if (!Array.isArray(data) || data.length === 0) throw new Error('Адресу не знайдено');
  if (!isWithinLviv(Number(data[0].lat), Number(data[0].lon))) {
    throw new Error('Сервіс працює тільки в межах Львова');
  }

  return {
    lat: Number(data[0].lat),
    lng: Number(data[0].lon),
    displayName: data[0].display_name,
  };
}

async function searchAddressSuggestions(query) {
  const normalized = query.trim();
  if (normalized.length < 3) return [];
  const lvivQuery = /львів/i.test(normalized) ? normalized : `${normalized}, Львів`;
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&limit=5&accept-language=uk&q=${encodeURIComponent(lvivQuery)}`
  );
  if (!response.ok) return [];
  const data = await response.json();
  if (!Array.isArray(data)) return [];
  return data
    .map((item) => ({
      lat: Number(item.lat),
      lng: Number(item.lon),
      displayName: item.display_name,
    }))
    .filter((item) => isWithinLviv(item.lat, item.lng));
}

async function reverseGeocode(lat, lng) {
  const response = await fetch(
    `https://nominatim.openstreetmap.org/reverse?format=json&accept-language=uk&lat=${lat}&lon=${lng}`
  );
  if (!response.ok) throw new Error('Не вдалося визначити адресу');

  const data = await response.json();
  return data.display_name || `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
}

export default function LvivTaxiApp() {
  const [mode, setMode] = useState('login');
  const [selectedRole, setSelectedRole] = useState('client');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    password: '',
    license_series: '',
    license_number: '',
  });

  const [adminData, setAdminData] = useState({
    applications: [],
    classApplications: [],
    drivers: [],
    fleetCars: [],
    logs: [],
    analytics: null,
    driverStats: [],
    reviews: [],
    selectedCarId: null,
    selectedDriverId: null,
    selectedDriverDetails: null,
    selectedDriverByCar: {},
    classApprovalByDriver: {},
    classReviewNoteByDriver: {},
    classApprovalByApplication: {},
    classReviewNoteById: {},
    activeView: 'requests',
    rejectionDraftByApplication: {},
    searchQuery: '',
    searchResults: null,
    searching: false,
    importingParquet: false,
    selectedParquetFile: null,
    selectedAddressesFile: null,
    importFiles: [],
    applicationsQuery: '',
    orderLogsQuery: '',
    classLogsQuery: '',
    driverApplicationLogsQuery: '',
    fleetQuery: '',
    pendingClassQuery: '',
    statsMetric: 'revenue',
    driverStatsQuery: '',
    adminReviewsQuery: '',
  });

  const [clientData, setClientData] = useState({
    pickup_address: '',
    dropoff_address: '',
    pickup_lat: null,
    pickup_lng: null,
    dropoff_lat: null,
    dropoff_lng: null,
    quote: null,
    selected_class: 'economy',
    ordersTab: 'active',
    orders: [],
    pickup_suggestions: [],
    dropoff_suggestions: [],
    open_suggestions_for: null,
    reviewDraftByOrder: {},
    geolocLoading: false,
    geocodeLoading: false,
    creatingOrder: false,
    cancellingOrder: false,
    creatingReview: false,
    pendingOrderConfirmation: null,
  });

  const [driverData, setDriverData] = useState({
    profile: null,
    orders: [],
    reviews: [],
    classApplications: [],
    ownCarForm: {
      make: '',
      model: '',
      production_year: 2018,
      plate_number: '',
      engine: '',
      transmission: 'automatic',
      requested_car_class: 'economy',
    },
    loadingOwnCar: false,
    loadingLocation: false,
    loadingStatus: false,
    loadingOrderAction: false,
    ownCarModalOpen: false,
    ordersTab: 'active',
    reviewsQuery: '',
  });

  const setFlash = (type, text) => {
    setMessageType(type);
    setMessage(text);
  };

  const showToast = (text) => {
    setToastMessage(text);
  };

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = setTimeout(() => setToastMessage(''), 3000);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const selectedFleetCar = useMemo(
    () => adminData.fleetCars.find((car) => car.id === adminData.selectedCarId) || null,
    [adminData.fleetCars, adminData.selectedCarId]
  );

  const clientMapUrl = useMemo(
    () =>
      buildGoogleMapUrl(
        { lat: clientData.pickup_lat, lng: clientData.pickup_lng },
        { lat: clientData.dropoff_lat, lng: clientData.dropoff_lng }
      ),
    [clientData.pickup_lat, clientData.pickup_lng, clientData.dropoff_lat, clientData.dropoff_lng]
  );

  const driverMapUrl = useMemo(() => {
    if (!driverData.profile?.current_lat || !driverData.profile?.current_lng) return '';
    return buildGoogleMapUrl({ lat: driverData.profile.current_lat, lng: driverData.profile.current_lng }, null);
  }, [driverData.profile]);

  const driverAllowedClasses = useMemo(() => {
    const approved = driverData.profile?.approved_car_class || 'economy';
    return CLASS_ORDER.filter((item) => classRank(item) <= classRank(approved));
  }, [driverData.profile?.approved_car_class]);

  const updateField = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const loadAdminData = async (accessToken) => {
    const [applications, classApplications, drivers, fleetCars, logs, analytics, driverStats, reviews] = await Promise.all([
      apiRequest('/management/driver-applications?limit=1000', { method: 'GET' }, accessToken),
      apiRequest('/management/driver-class-applications?limit=1000', { method: 'GET' }, accessToken),
      apiRequest('/management/drivers', { method: 'GET' }, accessToken),
      apiRequest('/management/fleet/cars', { method: 'GET' }, accessToken),
      apiRequest('/management/analytics/order-logs?limit=1000', { method: 'GET' }, accessToken),
      apiRequest('/management/analytics/overview', { method: 'GET' }, accessToken),
      apiRequest('/management/analytics/drivers', { method: 'GET' }, accessToken),
      apiRequest('/management/reviews', { method: 'GET' }, accessToken),
    ]);

    setAdminData((prev) => ({
      ...prev,
      applications,
      classApplications,
      drivers,
      fleetCars,
      logs,
      analytics,
      driverStats,
      reviews,
    }));
  };

  const loadClientData = async (accessToken) => {
    const orders = await apiRequest('/orders', { method: 'GET' }, accessToken);
    setClientData((prev) => ({ ...prev, orders }));
  };

  const loadDriverData = async (accessToken) => {
    const [profile, orders, reviews, classApplications] = await Promise.all([
      apiRequest('/management/drivers/me/profile', { method: 'GET' }, accessToken),
      apiRequest('/orders', { method: 'GET' }, accessToken),
      apiRequest('/management/reviews/me', { method: 'GET' }, accessToken),
      apiRequest('/management/drivers/me/class-applications', { method: 'GET' }, accessToken),
    ]);

    setDriverData((prev) => ({
      ...prev,
      profile,
      orders,
      reviews,
      classApplications,
    }));
  };

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const refreshed = await apiRequest('/auth/refresh', { method: 'POST' });
        setToken(refreshed.accessToken);
        const me = await apiRequest('/auth/me', { method: 'GET' }, refreshed.accessToken);
        setUser(me);
        setFlash('success', 'Сесію відновлено');
      } catch {
        // no active session
      }
    };
    restoreSession();
  }, []);

  useEffect(() => {
    if (!token || !user) return;
    const run = async () => {
      try {
        if (user.role === 'admin') await loadAdminData(token);
        if (user.role === 'client') await loadClientData(token);
        if (user.role === 'driver') await loadDriverData(token);
      } catch (error) {
        setFlash('error', parseError(error));
      }
    };
    run();
  }, [token, user]);

  useEffect(() => {
    if (!token || !user) return undefined;
    const interval = setInterval(() => {
      if (user.role === 'admin') loadAdminData(token).catch(() => null);
      if (user.role === 'client') loadClientData(token).catch(() => null);
      if (user.role === 'driver') loadDriverData(token).catch(() => null);
    }, 10000);
    return () => clearInterval(interval);
  }, [token, user]);

  useEffect(() => {
    const loadQuote = async () => {
      if (
        clientData.pickup_lat === null ||
        clientData.pickup_lng === null ||
        clientData.dropoff_lat === null ||
        clientData.dropoff_lng === null
      ) {
        return;
      }

      try {
        const quote = await apiRequest('/orders/quote', {
          method: 'POST',
          body: JSON.stringify({
            pickup_lat: clientData.pickup_lat,
            pickup_lng: clientData.pickup_lng,
            dropoff_lat: clientData.dropoff_lat,
            dropoff_lng: clientData.dropoff_lng,
          }),
        });
        setClientData((prev) => ({ ...prev, quote }));
      } catch (error) {
        setFlash('error', parseError(error));
      }
    };

    loadQuote();
  }, [clientData.pickup_lat, clientData.pickup_lng, clientData.dropoff_lat, clientData.dropoff_lng]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!clientData.pickup_address || clientData.open_suggestions_for !== 'pickup') return;
      const suggestions = await searchAddressSuggestions(clientData.pickup_address);
      setClientData((prev) => ({ ...prev, pickup_suggestions: suggestions }));
    }, 350);
    return () => clearTimeout(timer);
  }, [clientData.pickup_address, clientData.open_suggestions_for]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!clientData.dropoff_address || clientData.open_suggestions_for !== 'dropoff') return;
      const suggestions = await searchAddressSuggestions(clientData.dropoff_address);
      setClientData((prev) => ({ ...prev, dropoff_suggestions: suggestions }));
    }, 350);
    return () => clearTimeout(timer);
  }, [clientData.dropoff_address, clientData.open_suggestions_for]);

  useEffect(() => {
    if (!token || !user || user.role !== 'admin' || !adminData.selectedDriverId) return;
    const run = async () => {
      try {
        const details = await apiRequest(
          `/management/analytics/drivers/${adminData.selectedDriverId}`,
          { method: 'GET' },
          token
        );
        setAdminData((prev) => ({ ...prev, selectedDriverDetails: details }));
      } catch (error) {
        setFlash('error', parseError(error));
      }
    };
    run();
  }, [token, user, adminData.selectedDriverId]);

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
      setMessage('');
      showToast('Вхід виконано');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    try {
      setLoading(true);
      if (selectedRole === 'driver') {
        await apiRequest('/auth/driver-applications', {
          method: 'POST',
          body: JSON.stringify({
            first_name: form.first_name,
            last_name: form.last_name,
            phone: form.phone,
            email: form.email,
            password: form.password,
            license_series: form.license_series,
            license_number: form.license_number,
          }),
        });

        setFlash('success', 'Заявку водія відправлено адміну');
        setMode('login');
        return;
      }

      const auth = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          phone: form.phone,
          email: form.email,
          password: form.password,
        }),
      });
      setToken(auth.accessToken);
      const me = await apiRequest('/auth/me', { method: 'GET' }, auth.accessToken);
      setUser(me);
      setFlash('success', 'Реєстрація успішна');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (token) await apiRequest('/auth/logout', { method: 'POST' }, token);
    } catch {
      // ignore logout failures
    }
    setToken('');
    setUser(null);
    setMessage('');
    showToast('Ви вийшли з системи');
  };

  const submitAuth = async (event) => {
    event.preventDefault();
    if (mode === 'login') {
      await handleLogin();
      return;
    }
    await handleRegister();
  };

  const reviewDriverApplication = async (applicationId, approve) => {
    try {
      setLoading(true);
      await apiRequest(
        `/management/driver-applications/${applicationId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ approve }),
        },
        token
      );
      await loadAdminData(token);
      setFlash('success', approve ? 'Заявку підтверджено' : 'Заявку відхилено');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const reviewDriverClassApplication = async (applicationId, approve) => {
    const note = (adminData.classReviewNoteById[applicationId] || '').trim();
    if (note.length < 3) {
      setFlash('error', 'Вкажіть коментар (мінімум 3 символи)');
      return;
    }

    try {
      setLoading(true);
      await apiRequest(
        `/management/driver-class-applications/${applicationId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            approve,
            review_note: note,
            approved_car_class: approve ? adminData.classApprovalByApplication[applicationId] || null : null,
          }),
        },
        token
      );
      await loadAdminData(token);
      setFlash('success', approve ? 'Заявку на клас авто підтверджено' : 'Заявку на клас авто відхилено');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const assignFleetCarToDriver = async (carId) => {
    const driverId = Number(adminData.selectedDriverByCar[carId]);
    if (!driverId) {
      setFlash('error', 'Оберіть водія для видачі авто');
      return;
    }

    try {
      setLoading(true);
      await apiRequest(
        `/management/drivers/${driverId}/assign-car`,
        {
          method: 'PATCH',
          body: JSON.stringify({ car_id: carId }),
        },
        token
      );
      await loadAdminData(token);
      setFlash('success', 'Авто видано водію');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const detectMyLocation = () => {
    if (!navigator.geolocation) {
      setFlash('error', 'Браузер не підтримує геолокацію');
      return;
    }

    setClientData((prev) => ({ ...prev, geolocLoading: true }));

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        if (!isWithinLviv(lat, lng)) {
          setClientData((prev) => ({ ...prev, geolocLoading: false }));
          setFlash('error', 'Сервіс працює тільки в межах Львова');
          return;
        }
        try {
          const address = await reverseGeocode(lat, lng);
          setClientData((prev) => ({
            ...prev,
            pickup_lat: lat,
            pickup_lng: lng,
            pickup_address: address,
            geolocLoading: false,
          }));
          setFlash('success', 'Поточну адресу визначено');
        } catch (error) {
          setClientData((prev) => ({
            ...prev,
            pickup_lat: lat,
            pickup_lng: lng,
            pickup_address: `${lat.toFixed(6)}, ${lng.toFixed(6)}`,
            geolocLoading: false,
          }));
          setFlash('error', parseError(error));
        }
      },
      (error) => {
        setClientData((prev) => ({ ...prev, geolocLoading: false }));
        setFlash('error', error.message || 'Не вдалося отримати геолокацію');
      }
    );
  };

  const resolveAddress = async (type) => {
    const source = type === 'pickup' ? clientData.pickup_address : clientData.dropoff_address;
    try {
      setClientData((prev) => ({ ...prev, geocodeLoading: true }));
      const place = await geocodeAddress(source);
      setClientData((prev) => ({
        ...prev,
        ...(type === 'pickup'
          ? { pickup_address: place.displayName, pickup_lat: place.lat, pickup_lng: place.lng }
          : { dropoff_address: place.displayName, dropoff_lat: place.lat, dropoff_lng: place.lng }),
        geocodeLoading: false,
      }));
    } catch (error) {
      setClientData((prev) => ({ ...prev, geocodeLoading: false }));
      setFlash('error', parseError(error));
    }
  };

  const selectAddressSuggestion = (type, suggestion) => {
    if (!isWithinLviv(suggestion.lat, suggestion.lng)) {
      setFlash('error', 'Сервіс працює тільки в межах Львова');
      return;
    }
    setClientData((prev) => ({
      ...prev,
      ...(type === 'pickup'
        ? {
            pickup_address: suggestion.displayName,
            pickup_lat: suggestion.lat,
            pickup_lng: suggestion.lng,
            pickup_suggestions: [],
            open_suggestions_for: null,
          }
        : {
            dropoff_address: suggestion.displayName,
            dropoff_lat: suggestion.lat,
            dropoff_lng: suggestion.lng,
            dropoff_suggestions: [],
            open_suggestions_for: null,
          }),
    }));
  };

  const createOrder = async (comfortClass) => {
    if (!clientData.pickup_address || !clientData.dropoff_address) {
      setFlash('error', 'Заповніть адреси поїздки');
      return;
    }
    if (
      clientData.pickup_lat === null ||
      clientData.pickup_lng === null ||
      clientData.dropoff_lat === null ||
      clientData.dropoff_lng === null
    ) {
      setFlash('error', 'Потрібно визначити координати обох адрес');
      return;
    }
    if (!isWithinLviv(clientData.pickup_lat, clientData.pickup_lng) || !isWithinLviv(clientData.dropoff_lat, clientData.dropoff_lng)) {
      setFlash('error', 'Замовлення доступні тільки в межах Львова');
      return;
    }
    setClientData((prev) => ({
      ...prev,
      pendingOrderConfirmation: {
        comfortClass,
        pickup_address: prev.pickup_address,
        dropoff_address: prev.dropoff_address,
      },
    }));
  };

  const confirmCreateOrder = async () => {
    const comfortClass = clientData.pendingOrderConfirmation?.comfortClass;
    if (!comfortClass) return;
    try {
      setClientData((prev) => ({ ...prev, creatingOrder: true, selected_class: comfortClass }));
      await apiRequest(
        '/orders',
        {
          method: 'POST',
          body: JSON.stringify({
            pickup_address: clientData.pickup_address,
            dropoff_address: clientData.dropoff_address,
            pickup_lat: clientData.pickup_lat,
            pickup_lng: clientData.pickup_lng,
            dropoff_lat: clientData.dropoff_lat,
            dropoff_lng: clientData.dropoff_lng,
            comfort_class: comfortClass,
          }),
        },
        token
      );
      await loadClientData(token);
      setFlash('success', `Замовлення створено (${CLASS_LABELS[comfortClass]})`);
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setClientData((prev) => ({ ...prev, creatingOrder: false, pendingOrderConfirmation: null }));
    }
  };

  const cancelOrderSearch = async (orderId) => {
    try {
      setClientData((prev) => ({ ...prev, cancellingOrder: true }));
      await apiRequest(`/orders/${orderId}/cancel`, { method: 'PATCH' }, token);
      await loadClientData(token);
      setFlash('success', 'Пошук водія скасовано');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setClientData((prev) => ({ ...prev, cancellingOrder: false }));
    }
  };

  const updateReviewDraft = (orderId, field, value) => {
    setClientData((prev) => ({
      ...prev,
      reviewDraftByOrder: {
        ...prev.reviewDraftByOrder,
        [orderId]: {
          rating: 5,
          comment: '',
          ...(prev.reviewDraftByOrder[orderId] || {}),
          [field]: value,
        },
      },
    }));
  };

  const submitReview = async (orderId) => {
    const draft = clientData.reviewDraftByOrder[orderId] || { rating: 5, comment: '' };
    try {
      setClientData((prev) => ({ ...prev, creatingReview: true }));
      await apiRequest(
        '/orders/review',
        {
          method: 'POST',
          body: JSON.stringify({
            order_id: orderId,
            rating: Number(draft.rating ?? 5),
            comment: draft.comment?.trim() || null,
          }),
        },
        token
      );
      await loadClientData(token);
      setFlash('success', 'Дякуємо за оцінку водія');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setClientData((prev) => ({ ...prev, creatingReview: false }));
    }
  };

  const updateDriverOwnCarField = (event) => {
    const { name, value } = event.target;
    setDriverData((prev) => ({
      ...prev,
      ownCarForm: {
        ...prev.ownCarForm,
        [name]: name === 'production_year' ? Number(value) : value,
      },
    }));
  };

  const submitDriverOwnCar = async (event) => {
    event.preventDefault();
    try {
      setDriverData((prev) => ({ ...prev, loadingOwnCar: true }));
      await apiRequest(
        '/management/drivers/me/own-car',
        {
          method: 'PATCH',
          body: JSON.stringify(driverData.ownCarForm),
        },
        token
      );
      await loadDriverData(token);
      setFlash('success', 'Дані власного авто відправлені адміну');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingOwnCar: false }));
    }
  };

  const updateDriverLocation = () => {
    if (!navigator.geolocation) {
      setFlash('error', 'Браузер не підтримує геолокацію');
      return;
    }

    setDriverData((prev) => ({ ...prev, loadingLocation: true }));
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        if (!isWithinLviv(position.coords.latitude, position.coords.longitude)) {
          setDriverData((prev) => ({ ...prev, loadingLocation: false }));
          setFlash('error', 'Оновлення позиції доступне тільки в межах Львова');
          return;
        }
        try {
          await apiRequest(
            '/management/drivers/me/location',
            {
              method: 'PATCH',
              body: JSON.stringify({ lat: position.coords.latitude, lng: position.coords.longitude }),
            },
            token
          );
          await loadDriverData(token);
          setFlash('success', 'Геопозицію водія оновлено');
        } catch (error) {
          setFlash('error', parseError(error));
        } finally {
          setDriverData((prev) => ({ ...prev, loadingLocation: false }));
        }
      },
      (error) => {
        setDriverData((prev) => ({ ...prev, loadingLocation: false }));
        setFlash('error', error.message || 'Не вдалося отримати геопозицію');
      }
    );
  };

  const setDriverStatus = async (nextStatus) => {
    try {
      setDriverData((prev) => ({ ...prev, loadingStatus: true }));
      await apiRequest(
        '/management/drivers/me/status',
        {
          method: 'PATCH',
          body: JSON.stringify({ status: nextStatus }),
        },
        token
      );
      await loadDriverData(token);
      setFlash('success', `Статус водія: ${DRIVER_STATUS_LABELS[nextStatus] || nextStatus}`);
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingStatus: false }));
    }
  };

  const driverOrderDecision = async (orderId, accept) => {
    try {
      setDriverData((prev) => ({ ...prev, loadingOrderAction: true }));
      await apiRequest(
        `/orders/${orderId}/decision`,
        {
          method: 'PATCH',
          body: JSON.stringify({ accept }),
        },
        token
      );
      await loadDriverData(token);
      setFlash('success', accept ? 'Замовлення прийнято' : 'Замовлення відхилено');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingOrderAction: false }));
    }
  };

  const updateOrderStatus = async (orderId, statusName) => {
    try {
      setDriverData((prev) => ({ ...prev, loadingOrderAction: true }));
      await apiRequest(
        `/orders/${orderId}/status`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status: statusName }),
        },
        token
      );
      await loadDriverData(token);
      setFlash('success', 'Статус замовлення оновлено');
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingOrderAction: false }));
    }
  };

  const searchAdminEntities = async () => {
    const query = adminData.searchQuery.trim();
    if (query.length < 2) {
      setFlash('error', 'Вкажіть мінімум 2 символи для пошуку');
      return;
    }
    try {
      setAdminData((prev) => ({ ...prev, searching: true }));
      const result = await apiRequest(`/management/analytics/search?q=${encodeURIComponent(query)}`, { method: 'GET' }, token);
      setAdminData((prev) => ({ ...prev, searchResults: result }));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setAdminData((prev) => ({ ...prev, searching: false }));
    }
  };

  const handleImportFilesSelect = (event) => {
    const selected = Array.from(event.target.files || []);
    const parquetFile =
      selected.find((item) => item.name.toLowerCase().includes('.parquet')) ||
      selected.find((item) => (item.type || '').toLowerCase().includes('parquet')) ||
      selected[0] ||
      null;
    let addressesFile =
      selected.find((item) => item.name.toLowerCase().includes('.csv')) ||
      selected.find((item) => (item.type || '').toLowerCase().includes('csv')) ||
      null;
    if (!addressesFile && selected.length >= 2) {
      addressesFile = selected.find((item) => item !== parquetFile) || null;
    }
    setAdminData((prev) => ({
      ...prev,
      importFiles: selected,
      selectedParquetFile: parquetFile,
      selectedAddressesFile: addressesFile,
    }));
  };

  const importParquetByAdmin = async () => {
    if (!adminData.selectedParquetFile) {
      setFlash('error', 'Спочатку оберіть parquet файл');
      return;
    }

    try {
      setAdminData((prev) => ({ ...prev, importingParquet: true }));
      const formData = new FormData();
      formData.append('file', adminData.selectedParquetFile);
      if (adminData.selectedAddressesFile) {
        formData.append('addresses_file', adminData.selectedAddressesFile);
      }
      const response = await fetch(`${API_URL}/management/seed/import-parquet`, {
        method: 'POST',
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(JSON.stringify(payload));
      }
      await loadAdminData(token);
      showToast(`Parquet імпортовано. Додано замовлень: ${payload.records?.orders || 0}`);
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setAdminData((prev) => ({
        ...prev,
        importingParquet: false,
        selectedParquetFile: null,
        selectedAddressesFile: null,
        importFiles: [],
      }));
    }
  };

  const filteredApplications = useMemo(() => {
    const query = adminData.applicationsQuery.trim().toLowerCase();
    const source = adminData.applications.filter((item) => item.status === 'pending');
    if (!query) return source.slice(0, 5);
    return source
      .filter((item) =>
        [item.first_name, item.last_name, item.email, item.phone, item.license_number, item.status]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(query)
      )
      .slice(0, 5);
  }, [adminData.applications, adminData.applicationsQuery]);

  const filteredOrderLogs = useMemo(() => {
    const query = adminData.orderLogsQuery.trim().toLowerCase();
    const source = adminData.logs;
    if (!query) return source.slice(0, 5);
    return source
      .filter((item) =>
        [item.order_id, item.status, item.pickup_address, item.dropoff_address, item.client_id, item.driver_id]
          .join(' ')
          .toLowerCase()
          .includes(query)
      )
      .slice(0, 5);
  }, [adminData.logs, adminData.orderLogsQuery]);

  const filteredClassLogs = useMemo(() => {
    const query = adminData.classLogsQuery.trim().toLowerCase();
    const source = adminData.classApplications.filter((application) => application.status !== 'pending');
    if (!query) return source.slice(0, 5);
    return source
      .filter((item) =>
        [item.id, item.driver_id, item.status, item.review_note, item.requested_car_class]
          .join(' ')
          .toLowerCase()
          .includes(query)
      )
      .slice(0, 5);
  }, [adminData.classApplications, adminData.classLogsQuery]);

  const filteredDriverApplicationLogs = useMemo(() => {
    const query = adminData.driverApplicationLogsQuery.trim().toLowerCase();
    const source = adminData.applications.filter((item) => item.status !== 'pending');
    if (!query) return source.slice(0, 5);
    return source
      .filter((item) =>
        [item.id, item.first_name, item.last_name, item.email, item.phone, item.status]
          .join(' ')
          .toLowerCase()
          .includes(query)
      )
      .slice(0, 5);
  }, [adminData.applications, adminData.driverApplicationLogsQuery]);

  const adminChartData = useMemo(() => {
    const analytics = adminData.analytics || {};
    if (adminData.statsMetric === 'fleet') {
      return CLASS_ORDER.map((carClass) => ({
        key: carClass,
        label: CLASS_LABELS[carClass],
        value: analytics.orders_by_car_class?.[carClass] || 0,
      }));
    }
    const source = adminData.statsMetric === 'revenue' ? analytics.revenue_by_period : analytics.orders_count_by_period;
    const periodLabels = {
      day: '1 день',
      week: '1 тиждень',
      month: '1 місяць',
      year: '1 рік',
    };
    return ['day', 'week', 'month', 'year'].map((period) => ({
      key: period,
      label: periodLabels[period],
      value: source?.[period] || 0,
    }));
  }, [adminData.analytics, adminData.statsMetric]);

  const adminChartMax = useMemo(
    () => Math.max(...adminChartData.map((item) => Number(item.value) || 0), 1),
    [adminChartData]
  );

  const filteredFleetCars = useMemo(() => {
    const query = adminData.fleetQuery.trim().toLowerCase();
    if (!query) return adminData.fleetCars.slice(0, 5);
    return adminData.fleetCars.filter((car) =>
      [car.plate_number, car.make, car.model, car.assigned_driver_name, car.assigned_driver_id]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [adminData.fleetCars, adminData.fleetQuery]);

  const filteredPendingClassApplications = useMemo(() => {
    const pending = adminData.classApplications.filter((application) => application.status === 'pending');
    const query = adminData.pendingClassQuery.trim().toLowerCase();
    if (!query) return pending.slice(0, 5);
    return pending.filter((application) =>
      [application.id, application.driver_id, application.requested_car_class, application.own_car_make, application.own_car_model, application.own_car_plate]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [adminData.classApplications, adminData.pendingClassQuery]);

  const filteredDriverStats = useMemo(() => {
    const query = adminData.driverStatsQuery.trim().toLowerCase();
    if (!query) return adminData.driverStats.slice(0, 20);
    return adminData.driverStats.filter((driver) =>
      [driver.driver_id, displayDriverName(driver.driver_name, driver.driver_id), driver.email]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [adminData.driverStats, adminData.driverStatsQuery]);

  const filteredAdminReviews = useMemo(() => {
    const query = adminData.adminReviewsQuery.trim().toLowerCase();
    if (!query) return adminData.reviews.slice(0, 12);
    return adminData.reviews.filter((review) =>
      [review.id, review.order_id, review.rating, review.comment]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [adminData.reviews, adminData.adminReviewsQuery]);

  const renderAdminPanel = () => (
    <div
      className={`dashboard-grid admin-dashboard ${adminData.activeView === 'logs' ? 'admin-logs-layout' : ''} ${
        ['requests', 'stats', 'search'].includes(adminData.activeView) ? 'admin-two-columns' : ''
      }`}
    >
      <section className="panel-card wide admin-header">
        <h3>Панель адміністратора</h3>
        <div className="inline-actions admin-tabs">
          <button type="button" className={`secondary compact ${adminData.activeView === 'requests' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'requests' }))}>
            Заявки
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'logs' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'logs' }))}>
            Логи подій
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'stats' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'stats' }))}>
            Статистика
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'fleet' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'fleet' }))}>
            Автопарк
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'search' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'search' }))}>
            Пошук
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'import' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'import' }))}>
            Імпортувати дані
          </button>
        </div>
      </section>

      {adminData.activeView === 'requests' && (
        <>
          <section className="panel-card admin-column">
            <h3>Заявки водіїв</h3>
            <input
              placeholder="Пошук заявки водія"
              value={adminData.applicationsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, applicationsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredApplications.length === 0 && <p className="muted">Немає заявок. Розділ готовий до нових звернень.</p>}
              {filteredApplications.map((application) => (
                <div key={application.id} className="list-item">
                  <p>
                    <strong>{application.first_name} {application.last_name}</strong>
                  </p>
                  <p>{application.email}</p>
                  <p>Права: {application.license_series} {application.license_number}</p>
                  <p>Статус: {application.status}</p>
                  {application.status === 'pending' && (
                    <div className="inline-actions">
                      <button type="button" className="primary compact" onClick={() => reviewDriverApplication(application.id, true)}>
                        Підтвердити
                      </button>
                      <button type="button" className="secondary compact" onClick={() => reviewDriverApplication(application.id, false)}>
                        Відхилити
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>Класи доступу водіїв</h3>
            <input
              placeholder="Пошук заявки на клас"
              value={adminData.pendingClassQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, pendingClassQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredPendingClassApplications.length === 0 && <p className="muted">Немає активних заявок. Очікуємо нові запити.</p>}
              {filteredPendingClassApplications.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>Driver #{application.driver_id}</strong></p>
                  <p>Клас заявки: {CLASS_LABELS[application.requested_car_class]}</p>
                  <p>
                    Авто: {application.own_car_make} {application.own_car_model} ({application.own_car_plate})
                  </p>
                  <select
                    value={adminData.classApprovalByApplication[application.id] || application.requested_car_class}
                    onChange={(event) =>
                      setAdminData((prev) => ({
                        ...prev,
                        classApprovalByApplication: {
                          ...prev.classApprovalByApplication,
                          [application.id]: event.target.value,
                        },
                      }))
                    }
                  >
                    {CLASS_ORDER.map((carClass) => (
                      <option key={carClass} value={carClass}>
                        {CLASS_LABELS[carClass]}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="Коментар адміністратора"
                    value={adminData.classReviewNoteById[application.id] || ''}
                    onChange={(event) =>
                      setAdminData((prev) => ({
                        ...prev,
                        classReviewNoteById: {
                          ...prev.classReviewNoteById,
                          [application.id]: event.target.value,
                        },
                      }))
                    }
                  />
                  <div className="inline-actions">
                    <button type="button" className="primary compact" onClick={() => reviewDriverClassApplication(application.id, true)}>
                      Одобрити
                    </button>
                    <button type="button" className="secondary compact" onClick={() => reviewDriverClassApplication(application.id, false)}>
                      Відхилити
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

        </>
      )}

      {adminData.activeView === 'logs' && (
        <>
          <section className="panel-card admin-column">
            <h3>Логи замовлень</h3>
            <input
              placeholder="Пошук логу замовлення"
              value={adminData.orderLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, orderLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredOrderLogs.map((log) => (
                <div key={log.order_id} className="list-item">
                  <p><strong>Замовлення #{log.order_id}</strong></p>
                  <p>{ORDER_STATUS_LABELS[log.status] || log.status}</p>
                  <p>{log.pickup_address} {'->'} {log.dropoff_address}</p>
                  <p>{log.distance_km} км | Повна вартість: {money(log.final_cost ?? log.estimated_cost)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>Одобрення класу автомобіля (логи)</h3>
            <input
              placeholder="Пошук логу по класу авто"
              value={adminData.classLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, classLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredClassLogs.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>Заявка #{application.id}</strong></p>
                  <p>Водій: #{application.driver_id}</p>
                  <p>Статус: {application.status}</p>
                  <p>Коментар: {application.review_note || '-'}</p>
                </div>
              ))}
            </div>
          </section>
          <section className="panel-card admin-column">
            <h3>Логи заявок водіїв</h3>
            <input
              placeholder="Пошук логу заявки водія"
              value={adminData.driverApplicationLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, driverApplicationLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredDriverApplicationLogs.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>Заявка #{application.id}</strong></p>
                  <p>{application.first_name} {application.last_name}</p>
                  <p>{application.email} | {application.phone}</p>
                  <p>Статус: {application.status}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {adminData.activeView === 'stats' && (
        <>
          <section className="panel-card admin-column">
            <h3>Статистика водія</h3>
            <input
              placeholder="Пошук водія: ім'я / email / id"
              value={adminData.driverStatsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, driverStatsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredDriverStats.map((driver) => (
                <button
                  key={driver.driver_id}
                  type="button"
                  className={`secondary ${adminData.selectedDriverId === driver.driver_id ? 'active' : ''}`}
                  onClick={() =>
                    setAdminData((prev) => ({
                      ...prev,
                      selectedDriverId: driver.driver_id,
                      selectedDriverDetails: null,
                    }))
                  }
                >
                  {displayDriverName(driver.driver_name, driver.driver_id)} | {driver.completed_orders} поїздок
                </button>
              ))}
              {adminData.selectedDriverDetails && (
                <div className="list-item">
                  <p><strong>{displayDriverName(adminData.selectedDriverDetails.driver_name, adminData.selectedDriverDetails.driver_id)}</strong></p>
                  <p>Email: {adminData.selectedDriverDetails.email}</p>
                  <p>Кількість поїздок: {adminData.selectedDriverDetails.total_trips}</p>
                  <p>Авто: {adminData.selectedDriverDetails.active_car || '-'}</p>
                  <p>Рейтинг: {adminData.selectedDriverDetails.avg_rating}/5</p>
                </div>
              )}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>Статистика</h3>
            <select
              value={adminData.statsMetric}
              onChange={(event) => setAdminData((prev) => ({ ...prev, statsMetric: event.target.value }))}
            >
              <option value="revenue">Каса</option>
              <option value="orders">Кількість замовлень</option>
              <option value="fleet">Кількість авто в автопарку</option>
            </select>
            <div className="bar-chart">
              {adminChartData.map((item) => (
                <div key={item.key} className="bar-item">
                  <span className="bar-value">{adminData.statsMetric === 'revenue' ? money(item.value) : item.value}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ height: `${Math.max((Number(item.value) / adminChartMax) * 100, 4)}%` }} />
                  </div>
                  <span className="bar-label">{item.label}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card wide">
            <h3>Відгуки клієнтів</h3>
            <input
              placeholder="Пошук конкретного відгуку"
              value={adminData.adminReviewsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, adminReviewsQuery: event.target.value }))}
            />
            {filteredAdminReviews.slice(0, 12).map((review) => (
              <div key={review.id} className="list-item">
                <p><strong>Замовлення #{review.order_id}</strong> | Оцінка: {review.rating}/5</p>
                <p>{review.comment || 'Без коментаря'}</p>
              </div>
            ))}
          </section>
        </>
      )}

      {adminData.activeView === 'search' && (
        <>
          <section className="panel-card wide">
            <h3>Пошук (замовлення / водії)</h3>
            <p className="muted">Пошук за телефоном, номером поїздки, ПІБ клієнта/водія, email, номером авто.</p>
            <div className="input-row">
              <input
                value={adminData.searchQuery}
                onChange={(event) => setAdminData((prev) => ({ ...prev, searchQuery: event.target.value }))}
                placeholder="Введіть запит"
              />
              <button type="button" className="primary compact" onClick={searchAdminEntities} disabled={adminData.searching}>
                {adminData.searching ? 'Пошук...' : 'Знайти'}
              </button>
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>Знайдені замовлення</h3>
            <div className="scroll-list">
              {(adminData.searchResults?.orders || []).map((order) => (
                <div key={order.order_id} className="list-item">
                  <p><strong>Замовлення #{order.order_id}</strong> ({order.status})</p>
                  <p>Клієнт: {order.client_name} | {order.client_phone}</p>
                  <p>Маршрут: {order.pickup_address} {'->'} {order.dropoff_address}</p>
                  <p>Водій: {order.driver_name || '-'} | Сума: {money(order.final_cost)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>Знайдені водії</h3>
            <div className="scroll-list">
              {(adminData.searchResults?.drivers || []).map((driver) => (
                <div key={driver.driver_id} className="list-item">
                  <p><strong>{displayDriverName(driver.driver_name, driver.driver_id)}</strong> ({driver.status})</p>
                  <p>{driver.phone} | {driver.email}</p>
                  <p>Права: {driver.license_number}</p>
                  <p>Авто: {driver.active_car || '-'}</p>
                  <p>Індивідуальна статистика: {driver.completed_orders} поїздок, рейтинг {driver.avg_rating}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {adminData.activeView === 'fleet' && (
        <section className="panel-card wide">
          <h3>Автопарк</h3>
          <input
            placeholder="Пошук авто: водій / номер / марка / модель"
            value={adminData.fleetQuery}
            onChange={(event) => setAdminData((prev) => ({ ...prev, fleetQuery: event.target.value }))}
          />
          <div className="fleet-grid">
            {filteredFleetCars.map((car) => (
              <button
                key={car.id}
                type="button"
                className={`fleet-car ${car.is_occupied ? 'occupied' : 'free'} ${adminData.selectedCarId === car.id ? 'active' : ''}`}
                onClick={() => setAdminData((prev) => ({ ...prev, selectedCarId: car.id }))}
              >
                <strong>{car.make} {car.model}</strong>
                <span>{car.plate_number}</span>
                <span>Клас: {CLASS_LABELS[car.comfort_class]}</span>
                <span>{car.is_occupied ? `Зайняте (${car.assigned_driver_name || 'водій'})` : 'Вільне'}</span>
              </button>
            ))}
          </div>
          {selectedFleetCar && (
            <div className="car-detail">
              <h4>{selectedFleetCar.make} {selectedFleetCar.model}</h4>
              <p><strong>Номер:</strong> {selectedFleetCar.plate_number}</p>
              <p><strong>Рік:</strong> {selectedFleetCar.production_year}</p>
              <p><strong>Двигун:</strong> {selectedFleetCar.engine}</p>
              <p><strong>Коробка:</strong> {selectedFleetCar.transmission}</p>
              <p><strong>Водій:</strong> {selectedFleetCar.assigned_driver_name || 'Не призначено'}</p>

              {!selectedFleetCar.is_occupied && (
                <div className="assign-row">
                  <select
                    value={adminData.selectedDriverByCar[selectedFleetCar.id] || ''}
                    onChange={(event) =>
                      setAdminData((prev) => ({
                        ...prev,
                        selectedDriverByCar: {
                          ...prev.selectedDriverByCar,
                          [selectedFleetCar.id]: event.target.value,
                        },
                      }))
                    }
                  >
                    <option value="">Оберіть водія</option>
                    {adminData.drivers.map((driver) => (
                      <option key={driver.id} value={driver.id}>
                        {driver.driver_name} ({driver.status})
                      </option>
                    ))}
                  </select>
                  <button type="button" className="primary compact" onClick={() => assignFleetCarToDriver(selectedFleetCar.id)}>
                    Видати авто
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {adminData.activeView === 'import' && (
        <section className="panel-card wide">
          <h3>Імпорт даних</h3>
          <p className="muted">Оберіть потрібний файл для імпорту даних.</p>
          <div className="import-row">
            <input
              id="parquet-import"
              type="file"
              accept=".parquet,.csv,text/csv"
              multiple
              onChange={handleImportFilesSelect}
              disabled={adminData.importingParquet}
            />
            <button
              type="button"
              className="primary compact"
              onClick={importParquetByAdmin}
              disabled={adminData.importingParquet || !adminData.selectedParquetFile}
            >
              {adminData.importingParquet ? 'Імпорт...' : 'Імпортувати'}
            </button>
          </div>
        </section>
      )}
    </div>
  );

  const renderClientPanel = () => (
    <div className="dashboard-grid">
      <section className="panel-card wide">
        <h3>Замовлення поїздки</h3>
        <div className="form-grid">
          <button type="button" className="secondary" onClick={detectMyLocation} disabled={clientData.geolocLoading}>
            {clientData.geolocLoading ? 'Визначаємо геолокацію...' : 'Дозволити геопозицію'}
          </button>

          <label htmlFor="pickup_address">Звідки їдете</label>
          <div className="input-row">
            <input
              id="pickup_address"
              value={clientData.pickup_address}
              onChange={(event) =>
                setClientData((prev) => ({
                  ...prev,
                  pickup_address: event.target.value,
                  pickup_lat: null,
                  pickup_lng: null,
                  open_suggestions_for: 'pickup',
                }))
              }
              placeholder="Вкажіть адресу відправлення"
            />
            <button type="button" className="secondary compact" onClick={() => resolveAddress('pickup')} disabled={clientData.geocodeLoading}>
              Знайти
            </button>
          </div>
          {clientData.open_suggestions_for === 'pickup' && clientData.pickup_suggestions.length > 0 && (
            <div className="suggestions-list">
              {clientData.pickup_suggestions.map((item) => (
                <button
                  key={`pickup-${item.lat}-${item.lng}`}
                  type="button"
                  className="secondary suggestion"
                  onClick={() => selectAddressSuggestion('pickup', item)}
                >
                  {item.displayName}
                </button>
              ))}
            </div>
          )}

          <label htmlFor="dropoff_address">Куди їдете</label>
          <div className="input-row">
            <input
              id="dropoff_address"
              value={clientData.dropoff_address}
              onChange={(event) =>
                setClientData((prev) => ({
                  ...prev,
                  dropoff_address: event.target.value,
                  dropoff_lat: null,
                  dropoff_lng: null,
                  open_suggestions_for: 'dropoff',
                }))
              }
              placeholder="Вкажіть адресу призначення"
            />
            <button type="button" className="secondary compact" onClick={() => resolveAddress('dropoff')} disabled={clientData.geocodeLoading}>
              Знайти
            </button>
          </div>
          {clientData.open_suggestions_for === 'dropoff' && clientData.dropoff_suggestions.length > 0 && (
            <div className="suggestions-list">
              {clientData.dropoff_suggestions.map((item) => (
                <button
                  key={`dropoff-${item.lat}-${item.lng}`}
                  type="button"
                  className="secondary suggestion"
                  onClick={() => selectAddressSuggestion('dropoff', item)}
                >
                  {item.displayName}
                </button>
              ))}
            </div>
          )}
        </div>

        {clientMapUrl && (
          <iframe
            className="map-frame"
            src={clientMapUrl}
            title="Client route map"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        )}
        <h3>Класи авто і вартість</h3>
        <p>Вартість: Економ 25, Стандарт 35, Комфорт 35, Бізнес 50 грн/км.</p>
        {clientData.quote ? (
          <>
            <p>Відстань: <strong>{clientData.quote.distance_km} км</strong></p>
            <div className="class-grid">
              {CLASS_ORDER.map((carClass) => (
                <button
                  key={carClass}
                  type="button"
                  className={`class-card ${clientData.selected_class === carClass ? 'active' : ''}`}
                  onClick={() => {
                    setClientData((prev) => ({ ...prev, selected_class: carClass }));
                    createOrder(carClass);
                  }}
                  disabled={clientData.creatingOrder}
                >
                  <strong>{CLASS_LABELS[carClass]}</strong>
                  <span>{money(clientData.quote.prices[carClass])}</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <p>Вкажіть обидві адреси, щоб побачити тариф.</p>
        )}
        {clientData.pendingOrderConfirmation && (
          <div className="list-item">
            <p><strong>Підтвердити замовлення</strong></p>
            <p>Звідки: {shortAddress(clientData.pendingOrderConfirmation.pickup_address)}</p>
            <p>Куди: {shortAddress(clientData.pendingOrderConfirmation.dropoff_address)}</p>
            <div className="inline-actions">
              <button type="button" className="primary compact" onClick={confirmCreateOrder} disabled={clientData.creatingOrder}>
                Підтвердити
              </button>
              <button
                type="button"
                className="secondary compact"
                onClick={() => setClientData((prev) => ({ ...prev, pendingOrderConfirmation: null }))}
                disabled={clientData.creatingOrder}
              >
                Скасувати
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="panel-card wide">
        <h3>{clientData.ordersTab === 'active' ? 'Мої замовлення' : 'Моя історія поїздок'}</h3>
        <div className="inline-actions full-width-actions">
          <button
            type="button"
            className={`secondary compact ${clientData.ordersTab === 'active' ? 'active' : ''}`}
            onClick={() => setClientData((prev) => ({ ...prev, ordersTab: 'active' }))}
          >
            Мої замовлення
          </button>
          <button
            type="button"
            className={`secondary compact ${clientData.ordersTab === 'history' ? 'active' : ''}`}
            onClick={() => setClientData((prev) => ({ ...prev, ordersTab: 'history' }))}
          >
            Моя історія поїздок
          </button>
        </div>
        {(clientData.ordersTab === 'active'
          ? clientData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : clientData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).length === 0 && <p>{clientData.ordersTab === 'active' ? 'Активних замовлень немає' : 'Історія поїздок порожня'}</p>}
        {(clientData.ordersTab === 'active'
          ? clientData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : clientData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).map((order) => (
          <div key={order.id} className="list-item">
            <p><strong>Ваш №{order.client_order_number}</strong> | {ORDER_STATUS_LABELS[order.status] || order.status}</p>
            <p>{order.pickup_address} {'->'} {order.dropoff_address}</p>
            <p>{order.distance_km} км | {CLASS_LABELS[order.requested_comfort_class]}</p>
            <p>Вартість: {money(order.final_cost ?? order.estimated_cost)}</p>
            {['pending', 'assigned', 'driver_arrived'].includes(order.status) && (
              <button
                type="button"
                className="secondary compact"
                onClick={() => cancelOrderSearch(order.id)}
                disabled={clientData.cancellingOrder}
              >
                Відмінити пошук водія
              </button>
            )}
            {order.status === 'completed' && !order.review && (
              <div className="form-grid">
                <label htmlFor={`rating-${order.id}`}>Оцінка водія (0-5)</label>
                <input
                  id={`rating-${order.id}`}
                  type="number"
                  min="0"
                  max="5"
                  value={clientData.reviewDraftByOrder[order.id]?.rating ?? 5}
                  onChange={(event) => updateReviewDraft(order.id, 'rating', event.target.value)}
                />
                <label htmlFor={`comment-${order.id}`}>Відгук</label>
                <input
                  id={`comment-${order.id}`}
                  value={clientData.reviewDraftByOrder[order.id]?.comment ?? ''}
                  onChange={(event) => updateReviewDraft(order.id, 'comment', event.target.value)}
                  placeholder="Напишіть короткий коментар"
                />
                <button
                  type="button"
                  className="primary compact"
                  onClick={() => submitReview(order.id)}
                  disabled={clientData.creatingReview}
                >
                  Надіслати відгук
                </button>
              </div>
            )}
            {order.review && (
              <p>
                Ваша оцінка: {order.review.rating}/5 {order.review.comment ? `| "${order.review.comment}"` : ''}
              </p>
            )}
          </div>
        ))}
      </section>
    </div>
  );

  const renderDriverPanel = () => (
    <div className="dashboard-grid">
      <section className="panel-card wide">
        <div className="driver-top-actions">
          <button type="button" className="secondary compact" onClick={() => setDriverData((prev) => ({ ...prev, ownCarModalOpen: true }))}>
            Працювати на власному авто
          </button>
          <button
            type="button"
            className={`secondary compact ${driverData.ordersTab === 'history' ? 'active' : ''}`}
            onClick={() => setDriverData((prev) => ({ ...prev, ordersTab: prev.ordersTab === 'active' ? 'history' : 'active' }))}
          >
            Історія поїздок
          </button>
        </div>
      </section>
      <section className="panel-card">
        <h3>Профіль водія</h3>
        {!driverData.profile && <p>Завантаження...</p>}
        {driverData.profile && (
          <>
            <p><strong>Статус:</strong> {DRIVER_STATUS_LABELS[driverData.profile.status] || driverData.profile.status}</p>
            <p><strong>Підтверджений клас:</strong> {CLASS_LABELS[driverData.profile.approved_car_class]}</p>
            <p><strong>Доступні замовлення:</strong> {driverAllowedClasses.map((item) => CLASS_LABELS[item]).join(', ')}</p>
            <p><strong>Робота на власному авто:</strong> {driverData.profile.uses_own_car ? 'Так' : 'Ні'}</p>
            {driverData.profile.last_class_application_status && (
              <p>
                <strong>Остання заявка на клас авто:</strong> {driverData.profile.last_class_application_status}
                {driverData.profile.last_class_application_note ? ` | ${driverData.profile.last_class_application_note}` : ''}
              </p>
            )}

            {driverData.profile.assigned_company_car && (
              <div className="car-detail compact">
                <h4>Видане авто таксопарку</h4>
                <p>
                  {driverData.profile.assigned_company_car.make} {driverData.profile.assigned_company_car.model} ({driverData.profile.assigned_company_car.plate_number})
                </p>
                <p>Клас: {CLASS_LABELS[driverData.profile.assigned_company_car.comfort_class]}</p>
              </div>
            )}

            {driverData.profile.own_car && (
              <div className="car-detail compact">
                <h4>Моє авто</h4>
                <p>
                  {driverData.profile.own_car.make} {driverData.profile.own_car.model} ({driverData.profile.own_car.plate_number})
                </p>
              </div>
            )}

            <div className="inline-actions driver-status-actions">
              <button type="button" className="primary" onClick={() => setDriverStatus('free')} disabled={driverData.loadingStatus}>
                Почати роботу
              </button>
              <button type="button" className="secondary" onClick={() => setDriverStatus('break')} disabled={driverData.loadingStatus}>
                Пауза
              </button>
              <button type="button" className="secondary" onClick={() => setDriverStatus('inactive')} disabled={driverData.loadingStatus}>
                Завершити зміну
              </button>
            </div>

            <button type="button" className="secondary driver-gps-button" onClick={updateDriverLocation} disabled={driverData.loadingLocation}>
              {driverData.loadingLocation ? 'Оновлюємо геопозицію...' : 'Активувати GPS трекер'}
            </button>

            {driverMapUrl && (
              <iframe
                className="map-frame"
                src={driverMapUrl}
                title="Driver current location"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
            )}
          </>
        )}
      </section>

      {driverData.ownCarModalOpen && (
        <div className="modal-backdrop">
          <section className="panel-card modal-card">
            <h3>Працюю на своєму авто</h3>
            <form className="form-grid" onSubmit={submitDriverOwnCar}>
          <label htmlFor="make">Марка</label>
          <input id="make" name="make" value={driverData.ownCarForm.make} onChange={updateDriverOwnCarField} required />

          <label htmlFor="model">Модель</label>
          <input id="model" name="model" value={driverData.ownCarForm.model} onChange={updateDriverOwnCarField} required />

          <label htmlFor="production_year">Рік</label>
          <input
            id="production_year"
            name="production_year"
            type="number"
            min="1990"
            max="2026"
            value={driverData.ownCarForm.production_year}
            onChange={updateDriverOwnCarField}
            required
          />

          <label htmlFor="plate_number">Номер авто</label>
          <input id="plate_number" name="plate_number" value={driverData.ownCarForm.plate_number} onChange={updateDriverOwnCarField} required />

          <label htmlFor="engine">Двигун</label>
          <input id="engine" name="engine" value={driverData.ownCarForm.engine} onChange={updateDriverOwnCarField} required />

          <label htmlFor="transmission">Коробка</label>
          <select id="transmission" name="transmission" value={driverData.ownCarForm.transmission} onChange={updateDriverOwnCarField}>
            <option value="automatic">Automatic</option>
            <option value="manual">Manual</option>
          </select>

          <label htmlFor="requested_car_class">Клас, який запитуєте</label>
          <select
            id="requested_car_class"
            name="requested_car_class"
            value={driverData.ownCarForm.requested_car_class}
            onChange={updateDriverOwnCarField}
          >
            {CLASS_ORDER.map((carClass) => (
              <option key={carClass} value={carClass}>
                {CLASS_LABELS[carClass]}
              </option>
            ))}
          </select>

              <button type="submit" className="primary" disabled={driverData.loadingOwnCar}>
                {driverData.loadingOwnCar ? 'Відправка...' : 'Відправити на підтвердження'}
              </button>
              <button type="button" className="secondary" onClick={() => setDriverData((prev) => ({ ...prev, ownCarModalOpen: false }))}>
                Закрити
              </button>
            </form>
          </section>
        </div>
      )}

      <section className="panel-card">
        <h3>{driverData.ordersTab === 'active' ? 'Мої замовлення' : 'Історія поїздок'}</h3>
        {(driverData.ordersTab === 'active'
          ? driverData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : driverData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).length === 0 && <p>Поки що замовлень немає</p>}
        {(driverData.ordersTab === 'active'
          ? driverData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : driverData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).map((order) => (
          <div key={order.id} className="list-item">
            <p><strong>Замовлення #{order.id}</strong> | {ORDER_STATUS_LABELS[order.status] || order.status}</p>
            <p>{order.pickup_address} {'->'} {order.dropoff_address}</p>
            <p>Клас: {CLASS_LABELS[order.requested_comfort_class]} | Дистанція: {order.distance_km} км</p>
            <p>Оплата водію: {money(order.driver_payout)}</p>

            {order.status === 'pending' && (
              <div className="inline-actions">
                <button type="button" className="primary compact" onClick={() => driverOrderDecision(order.id, true)} disabled={driverData.loadingOrderAction}>
                  Прийняти
                </button>
                <button type="button" className="secondary compact" onClick={() => driverOrderDecision(order.id, false)} disabled={driverData.loadingOrderAction}>
                  Відхилити
                </button>
              </div>
            )}

            {order.status === 'assigned' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'driver_arrived')} disabled={driverData.loadingOrderAction}>
                Я прибув
              </button>
            )}

            {order.status === 'driver_arrived' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'in_progress')} disabled={driverData.loadingOrderAction}>
                Почати поїздку
              </button>
            )}

            {order.status === 'in_progress' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'completed')} disabled={driverData.loadingOrderAction}>
                Завершити поїздку
              </button>
            )}
          </div>
        ))}
      </section>

      <section className="panel-card wide">
        <h3>Відгуки клієнтів</h3>
        <input
          placeholder="Пошук відгуку"
          value={driverData.reviewsQuery}
          onChange={(event) => setDriverData((prev) => ({ ...prev, reviewsQuery: event.target.value }))}
        />
        {driverData.reviews.length === 0 && <p>Поки що відгуків немає</p>}
        {driverData.reviews
          .filter((review) =>
            [review.comment, review.rating, review.id].join(' ').toLowerCase().includes(driverData.reviewsQuery.trim().toLowerCase())
          )
          .slice(0, 12)
          .map((review) => (
          <div key={review.id} className="list-item">
            <p><strong>Оцінка:</strong> {review.rating}/5</p>
            <p>{review.comment || 'Без коментаря'}</p>
          </div>
          ))}
      </section>
    </div>
  );

  return (
    <main className="uklon-shell">
      <section className="landing-card">
        <div className="top-actions">
          <div className="brand">
            <span className="brand-dot" />
            <h1>Lviv Taxi</h1>
          </div>
          {user ? (
            <button type="button" className="secondary compact" onClick={logout}>
              Вийти
            </button>
          ) : null}
        </div>

        {message && <p className={`message ${messageType}`}>{message}</p>}

        {!user && (
          <div className="auth-layout">
            <form className="panel-card auth-card form-grid" onSubmit={submitAuth}>
              <h3>{mode === 'login' ? 'Вхід' : 'Реєстрація'}</h3>

              {mode === 'register' && (
                <div className="inline-actions">
                  <button type="button" className={`secondary compact ${selectedRole === 'client' ? 'active' : ''}`} onClick={() => setSelectedRole('client')}>
                    Клієнт
                  </button>
                  <button type="button" className={`secondary compact ${selectedRole === 'driver' ? 'active' : ''}`} onClick={() => setSelectedRole('driver')}>
                    Водій
                  </button>
                </div>
              )}

              {mode === 'register' && (
                <>
                  <label htmlFor="first_name">Ім'я</label>
                  <input id="first_name" name="first_name" value={form.first_name} onChange={updateField} required />

                  <label htmlFor="last_name">Прізвище</label>
                  <input id="last_name" name="last_name" value={form.last_name} onChange={updateField} required />

                  <label htmlFor="phone">Телефон</label>
                  <input id="phone" name="phone" value={form.phone} onChange={updateField} required />
                </>
              )}

              <label htmlFor="email">Email</label>
              <input id="email" name="email" type="email" value={form.email} onChange={updateField} required />

              <label htmlFor="password">Пароль</label>
              <input id="password" name="password" type="password" value={form.password} onChange={updateField} required />

              {mode === 'register' && selectedRole === 'driver' && (
                <>
                  <label htmlFor="license_series">Серія посвідчення</label>
                  <input id="license_series" name="license_series" value={form.license_series} onChange={updateField} required />

                  <label htmlFor="license_number">Номер посвідчення</label>
                  <input id="license_number" name="license_number" value={form.license_number} onChange={updateField} required />
                </>
              )}

              <button type="submit" className="primary" disabled={loading}>
                {loading ? 'Обробка...' : mode === 'login' ? 'Увійти' : 'Зареєструватись'}
              </button>

              <button
                type="button"
                className="secondary"
                onClick={() => setMode((prev) => (prev === 'login' ? 'register' : 'login'))}
                disabled={loading}
              >
                {mode === 'login' ? 'Ще немає акаунта?' : 'Вже є акаунт?'}
              </button>
            </form>
          </div>
        )}

        {user?.role === 'admin' && renderAdminPanel()}
        {user?.role === 'client' && renderClientPanel()}
        {user?.role === 'driver' && renderDriverPanel()}
      </section>
      {toastMessage && <div className="toast-message">{toastMessage}</div>}
    </main>
  );
}
