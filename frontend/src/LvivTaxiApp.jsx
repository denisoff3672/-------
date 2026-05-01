import { useEffect, useMemo, useState } from 'react';
import { API_URL, apiRequest } from './api';

const CLASS_ORDER = ['economy', 'standard', 'comfort', 'business'];
const CLASS_LABELS = {
  uk: {
    economy: 'Економ',
    standard: 'Стандарт',
    comfort: 'Комфорт',
    business: 'Бізнес',
  },
  en: {
    economy: 'Economy',
    standard: 'Standard',
    comfort: 'Comfort',
    business: 'Business',
  },
  pl: {
    economy: 'Ekonomiczna',
    standard: 'Standard',
    comfort: 'Komfort',
    business: 'Biznes',
  },
};

const FIRST_NAMES_BY_LANG = {
  uk: ['Олександр', 'Андрій', 'Тарас', 'Іван', 'Василь', 'Дмитро', 'Максим', 'Роман', 'Богдан', 'Ярослав'],
  en: ['Alexander', 'Andrew', 'Taras', 'Ivan', 'Vasyl', 'Dmytro', 'Maksym', 'Roman', 'Bohdan', 'Yaroslav'],
  pl: ['Aleksander', 'Andrzej', 'Taras', 'Jan', 'Wasyl', 'Dmytro', 'Maksym', 'Roman', 'Bohdan', 'Jaroslaw'],
};
const LAST_NAMES_BY_LANG = {
  uk: ['Коваль', 'Шевченко', 'Мельник', 'Бондар', 'Ткачук', 'Кравченко', 'Олійник', 'Поліщук', 'Бойко', 'Савчук'],
  en: ['Koval', 'Shevchenko', 'Melnyk', 'Bondar', 'Tkachuk', 'Kravchenko', 'Oliinyk', 'Polishchuk', 'Boiko', 'Savchuk'],
  pl: ['Kowal', 'Szewczenko', 'Melnyk', 'Bondar', 'Tkaczuk', 'Krawczenko', 'Oliinyk', 'Poliszczuk', 'Bojko', 'Sawczuk'],
};
const UI_LANGUAGES = ['uk', 'en', 'pl'];
const UI_COPY = {
  uk: {
    language: 'Мова',
    translate: 'Автопереклад',
    approving: 'Одобрити',
    rejecting: 'Відхилити',
    adminComment: 'Коментар адміністратора',
    unknownDriver: 'Невідомий водій',
  },
  en: {
    language: 'Language',
    translate: 'Auto translate',
    approving: 'Approve',
    rejecting: 'Reject',
    adminComment: 'Admin comment',
    unknownDriver: 'Unknown driver',
  },
  pl: {
    language: 'Język',
    translate: 'Auto tłumaczenie',
    approving: 'Zatwierdź',
    rejecting: 'Odrzuć',
    adminComment: 'Komentarz administratora',
    unknownDriver: 'Nieznany kierowca',
  },
};
const STATIC_TRANSLATIONS = {
  'Панель адміністратора': { en: 'Administrator panel', pl: 'Panel administratora' },
  'Заявки': { en: 'Requests', pl: 'Wnioski' },
  'Логи подій': { en: 'Event logs', pl: 'Logi zdarzen' },
  'Статистика': { en: 'Statistics', pl: 'Statystyki' },
  'Автопарк': { en: 'Fleet', pl: 'Flota' },
  'Пошук': { en: 'Search', pl: 'Wyszukiwanie' },
  'Імпортувати дані': { en: 'Import data', pl: 'Importuj dane' },
  'Заявки водіїв': { en: 'Driver applications', pl: 'Wnioski kierowcow' },
  'Пошук заявки водія': { en: 'Search driver application', pl: 'Szukaj wniosku kierowcy' },
  'Немає заявок. Розділ готовий до нових звернень.': { en: 'No applications. Section is ready for new requests.', pl: 'Brak wnioskow. Sekcja gotowa na nowe zgloszenia.' },
  'Права': { en: 'License', pl: 'Prawo jazdy' },
  'Статус': { en: 'Status', pl: 'Status' },
  'Підтвердити': { en: 'Approve', pl: 'Zatwierdz' },
  'Відхилити': { en: 'Reject', pl: 'Odrzuc' },
  'Класи доступу водіїв': { en: 'Driver class access', pl: 'Klasy dostepu kierowcow' },
  'Пошук заявки на клас': { en: 'Search class request', pl: 'Szukaj wniosku o klase' },
  'Немає активних заявок. Очікуємо нові запити.': { en: 'No active requests. Waiting for new ones.', pl: 'Brak aktywnych wnioskow. Czekamy na nowe.' },
  'Клас заявки': { en: 'Requested class', pl: 'Klasa wniosku' },
  'Авто': { en: 'Car', pl: 'Auto' },
  'Логи замовлень': { en: 'Order logs', pl: 'Logi zamowien' },
  'Пошук логу замовлення': { en: 'Search order log', pl: 'Szukaj logu zamowienia' },
  'Повна вартість': { en: 'Total cost', pl: 'Calkowity koszt' },
  'Одобрення класу автомобіля (логи)': { en: 'Car class approvals (logs)', pl: 'Zatwierdzenia klasy auta (logi)' },
  'Пошук логу по класу авто': { en: 'Search class log', pl: 'Szukaj logu klasy auta' },
  'Коментар': { en: 'Comment', pl: 'Komentarz' },
  'Логи заявок водіїв': { en: 'Driver application logs', pl: 'Logi wnioskow kierowcow' },
  'Пошук логу заявки водія': { en: 'Search driver application log', pl: 'Szukaj logu wniosku kierowcy' },
  'Статистика водія': { en: 'Driver statistics', pl: 'Statystyki kierowcy' },
  "Пошук водія: ім'я / email / id": { en: 'Search driver: name / email / id', pl: 'Szukaj kierowcy: imie / email / id' },
  'поїздок': { en: 'trips', pl: 'przejazdow' },
  'Кількість поїздок': { en: 'Trips count', pl: 'Liczba przejazdow' },
  'Рейтинг': { en: 'Rating', pl: 'Ocena' },
  'Каса': { en: 'Revenue', pl: 'Przychod' },
  'Кількість замовлень': { en: 'Orders count', pl: 'Liczba zamowien' },
  'Кількість авто в автопарку': { en: 'Cars in fleet', pl: 'Liczba aut we flocie' },
  '1 день': { en: '1 day', pl: '1 dzien' },
  '1 тиждень': { en: '1 week', pl: '1 tydzien' },
  '1 місяць': { en: '1 month', pl: '1 miesiac' },
  '1 рік': { en: '1 year', pl: '1 rok' },
  'Відгуки клієнтів': { en: 'Client reviews', pl: 'Opinie klientow' },
  'Пошук конкретного відгуку': { en: 'Search specific review', pl: 'Szukaj konkretnej opinii' },
  'Оцінка': { en: 'Rating', pl: 'Ocena' },
  'Пошук (замовлення / водії)': { en: 'Search (orders / drivers)', pl: 'Wyszukiwanie (zamowienia / kierowcy)' },
  'Пошук за телефоном, номером поїздки, ПІБ клієнта/водія, email, номером авто.': { en: 'Search by phone, trip number, client/driver name, email, car plate.', pl: 'Szukaj po telefonie, numerze kursu, imieniu klienta/kierowcy, emailu, numerze auta.' },
  'Введіть запит': { en: 'Enter query', pl: 'Wpisz zapytanie' },
  'Пошук...': { en: 'Searching...', pl: 'Wyszukiwanie...' },
  'Знайти': { en: 'Find', pl: 'Znajdz' },
  'Знайдені замовлення': { en: 'Found orders', pl: 'Znalezione zamowienia' },
  'Клієнт': { en: 'Client', pl: 'Klient' },
  'Маршрут': { en: 'Route', pl: 'Trasa' },
  'Водій': { en: 'Driver', pl: 'Kierowca' },
  'Сума': { en: 'Amount', pl: 'Kwota' },
  'Знайдені водії': { en: 'Found drivers', pl: 'Znalezieni kierowcy' },
  'Індивідуальна статистика': { en: 'Personal statistics', pl: 'Statystyka indywidualna' },
  'Автопарк': { en: 'Fleet', pl: 'Flota' },
  'Пошук авто: водій / номер / марка / модель': { en: 'Search car: driver / plate / make / model', pl: 'Szukaj auta: kierowca / numer / marka / model' },
  'Клас': { en: 'Class', pl: 'Klasa' },
  'Зайняте': { en: 'Occupied', pl: 'Zajete' },
  'водій': { en: 'driver', pl: 'kierowca' },
  'Вільне': { en: 'Free', pl: 'Wolne' },
  'Номер': { en: 'Plate', pl: 'Numer' },
  'Рік': { en: 'Year', pl: 'Rok' },
  'Двигун': { en: 'Engine', pl: 'Silnik' },
  'Коробка': { en: 'Transmission', pl: 'Skrzynia' },
  'Не призначено': { en: 'Not assigned', pl: 'Nie przypisano' },
  'Оберіть водія': { en: 'Select driver', pl: 'Wybierz kierowce' },
  'Видати авто': { en: 'Assign car', pl: 'Przypisz auto' },
  'Імпорт даних': { en: 'Data import', pl: 'Import danych' },
  'Оберіть потрібний файл для імпорту даних.': { en: 'Choose a file to import data.', pl: 'Wybierz plik do importu danych.' },
  'Імпорт...': { en: 'Importing...', pl: 'Importowanie...' },
  'Імпортувати': { en: 'Import', pl: 'Importuj' },
  'Замовлення поїздки': { en: 'Ride order', pl: 'Zamowienie przejazdu' },
  'Визначаємо геолокацію...': { en: 'Detecting geolocation...', pl: 'Wykrywanie geolokalizacji...' },
  'Дозволити геопозицію': { en: 'Enable geolocation', pl: 'Wlacz geolokalizacje' },
  'Звідки їдете': { en: 'Pickup address', pl: 'Skad jedziesz' },
  'Вкажіть адресу відправлення': { en: 'Enter pickup address', pl: 'Podaj adres odbioru' },
  'Куди їдете': { en: 'Dropoff address', pl: 'Dokad jedziesz' },
  'Вкажіть адресу призначення': { en: 'Enter destination address', pl: 'Podaj adres docelowy' },
  'Класи авто і вартість': { en: 'Car classes and price', pl: 'Klasy aut i cena' },
  'Вартість: Економ 25, Стандарт 35, Комфорт 35, Бізнес 50 грн/км.': { en: 'Prices: Economy 25, Standard 35, Comfort 35, Business 50 UAH/km.', pl: 'Ceny: Ekonom 25, Standard 35, Komfort 35, Biznes 50 UAH/km.' },
  'Відстань': { en: 'Distance', pl: 'Dystans' },
  'Вкажіть обидві адреси, щоб побачити тариф.': { en: 'Enter both addresses to see the fare.', pl: 'Podaj oba adresy, aby zobaczyc taryfe.' },
  'Підтвердити замовлення': { en: 'Confirm order', pl: 'Potwierdz zamowienie' },
  'Звідки': { en: 'From', pl: 'Skad' },
  'Куди': { en: 'To', pl: 'Dokad' },
  'Скасувати': { en: 'Cancel', pl: 'Anuluj' },
  'Мої замовлення': { en: 'My orders', pl: 'Moje zamowienia' },
  'Моя історія поїздок': { en: 'My trip history', pl: 'Moja historia przejazdow' },
  'Історія поїздок': { en: 'Trip history', pl: 'Historia przejazdow' },
  'Активних замовлень немає': { en: 'No active orders', pl: 'Brak aktywnych zamowien' },
  'Історія поїздок порожня': { en: 'Trip history is empty', pl: 'Historia przejazdow jest pusta' },
  'Вартість': { en: 'Price', pl: 'Cena' },
  'Відмінити пошук водія': { en: 'Cancel driver search', pl: 'Anuluj szukanie kierowcy' },
  'Оцінка водія (0-5)': { en: 'Driver rating (0-5)', pl: 'Ocena kierowcy (0-5)' },
  'Відгук': { en: 'Review', pl: 'Opinia' },
  'Напишіть короткий коментар': { en: 'Write a short comment', pl: 'Napisz krotki komentarz' },
  'Надіслати відгук': { en: 'Submit review', pl: 'Wyslij opinie' },
  'Ваша оцінка': { en: 'Your rating', pl: 'Twoja ocena' },
  'Працювати на власному авто': { en: 'Work with own car', pl: 'Pracuj na wlasnym aucie' },
  'Профіль водія': { en: 'Driver profile', pl: 'Profil kierowcy' },
  'Завантаження...': { en: 'Loading...', pl: 'Ladowanie...' },
  'Підтверджений клас': { en: 'Approved class', pl: 'Zatwierdzona klasa' },
  'Доступні замовлення': { en: 'Available orders', pl: 'Dostepne zamowienia' },
  'Робота на власному авто': { en: 'Using own car', pl: 'Praca na wlasnym aucie' },
  'Так': { en: 'Yes', pl: 'Tak' },
  'Ні': { en: 'No', pl: 'Nie' },
  'Остання заявка на клас авто': { en: 'Last car class request', pl: 'Ostatni wniosek o klase auta' },
  'Видане авто таксопарку': { en: 'Assigned fleet car', pl: 'Przydzielone auto flotowe' },
  'Моє авто': { en: 'My car', pl: 'Moje auto' },
  'Почати роботу': { en: 'Start shift', pl: 'Rozpocznij zmiane' },
  'Пауза': { en: 'Break', pl: 'Przerwa' },
  'Завершити зміну': { en: 'End shift', pl: 'Zakoncz zmiane' },
  'Оновлюємо геопозицію...': { en: 'Updating geolocation...', pl: 'Aktualizacja geolokalizacji...' },
  'Активувати GPS трекер': { en: 'Activate GPS tracker', pl: 'Aktywuj GPS tracker' },
  'Працюю на своєму авто': { en: 'Working with my own car', pl: 'Pracuje na swoim aucie' },
  'Марка': { en: 'Make', pl: 'Marka' },
  'Модель': { en: 'Model', pl: 'Model' },
  'Номер авто': { en: 'Car plate', pl: 'Numer auta' },
  'Клас, який запитуєте': { en: 'Requested class', pl: 'Wnioskowana klasa' },
  'Відправка...': { en: 'Sending...', pl: 'Wysylanie...' },
  'Відправити на підтвердження': { en: 'Send for approval', pl: 'Wyslij do zatwierdzenia' },
  'Закрити': { en: 'Close', pl: 'Zamknij' },
  'Поки що замовлень немає': { en: 'No orders yet', pl: 'Na razie brak zamowien' },
  'Замовлення': { en: 'Order', pl: 'Zamowienie' },
  'Дистанція': { en: 'Distance', pl: 'Dystans' },
  'Оплата водію': { en: 'Driver payout', pl: 'Wyplata kierowcy' },
  'Прийняти': { en: 'Accept', pl: 'Przyjmij' },
  'Я прибув': { en: 'I arrived', pl: 'Juz jestem' },
  'Почати поїздку': { en: 'Start trip', pl: 'Rozpocznij przejazd' },
  'Завершити поїздку': { en: 'Finish trip', pl: 'Zakoncz przejazd' },
  'Пошук відгуку': { en: 'Search review', pl: 'Szukaj opinii' },
  'Поки що відгуків немає': { en: 'No reviews yet', pl: 'Na razie brak opinii' },
  'Вийти': { en: 'Log out', pl: 'Wyloguj' },
  'Вхід': { en: 'Sign in', pl: 'Logowanie' },
  'Реєстрація': { en: 'Registration', pl: 'Rejestracja' },
  'Ім\'я': { en: 'First name', pl: 'Imie' },
  'Прізвище': { en: 'Last name', pl: 'Nazwisko' },
  'Телефон': { en: 'Phone', pl: 'Telefon' },
  'Пароль': { en: 'Password', pl: 'Haslo' },
  'Серія посвідчення': { en: 'License series', pl: 'Seria prawa jazdy' },
  'Номер посвідчення': { en: 'License number', pl: 'Numer prawa jazdy' },
  'Обробка...': { en: 'Processing...', pl: 'Przetwarzanie...' },
  'Увійти': { en: 'Sign in', pl: 'Zaloguj sie' },
  'Зареєструватись': { en: 'Sign up', pl: 'Zarejestruj sie' },
  'Ще немає акаунта?': { en: 'No account yet?', pl: 'Nie masz jeszcze konta?' },
  'Вже є акаунт?': { en: 'Already have an account?', pl: 'Masz juz konto?' },
  'Сесію відновлено': { en: 'Session restored', pl: 'Sesja przywrocona' },
  'Вхід виконано': { en: 'Signed in successfully', pl: 'Logowanie udane' },
  'Заявку водія відправлено адміну': { en: 'Driver application sent to admin', pl: 'Wniosek kierowcy wyslany do administratora' },
  'Реєстрація успішна': { en: 'Registration successful', pl: 'Rejestracja udana' },
  'Ви вийшли з системи': { en: 'You have logged out', pl: 'Wylogowano z systemu' },
  'Заявку підтверджено': { en: 'Application approved', pl: 'Wniosek zatwierdzono' },
  'Заявку відхилено': { en: 'Application rejected', pl: 'Wniosek odrzucono' },
  'Вкажіть коментар (мінімум 3 символи)': { en: 'Provide a comment (minimum 3 characters)', pl: 'Podaj komentarz (minimum 3 znaki)' },
  'Заявку на клас авто підтверджено': { en: 'Car class request approved', pl: 'Wniosek o klase auta zatwierdzono' },
  'Заявку на клас авто відхилено': { en: 'Car class request rejected', pl: 'Wniosek o klase auta odrzucono' },
  'Оберіть водія для видачі авто': { en: 'Select a driver to assign a car', pl: 'Wybierz kierowce do przydzielenia auta' },
  'Авто видано водію': { en: 'Car assigned to driver', pl: 'Auto przydzielone kierowcy' },
  'Браузер не підтримує геолокацію': { en: 'Browser does not support geolocation', pl: 'Przegladarka nie obsluguje geolokalizacji' },
  'Сервіс працює тільки в межах Львова': { en: 'Service works only within Lviv', pl: 'Serwis dziala tylko na terenie Lwowa' },
  'Поточну адресу визначено': { en: 'Current address detected', pl: 'Biezacy adres wykryty' },
  'Не вдалося отримати геолокацію': { en: 'Failed to get geolocation', pl: 'Nie udalo sie pobrac geolokalizacji' },
  'Заповніть адреси поїздки': { en: 'Fill in trip addresses', pl: 'Uzupelnij adresy przejazdu' },
  'Потрібно визначити координати обох адрес': { en: 'Coordinates for both addresses are required', pl: 'Wymagane sa wspolrzedne obu adresow' },
  'Замовлення доступні тільки в межах Львова': { en: 'Orders are available only within Lviv', pl: 'Zamowienia dostepne tylko na terenie Lwowa' },
  'Пошук водія скасовано': { en: 'Driver search cancelled', pl: 'Wyszukiwanie kierowcy anulowano' },
  'Дякуємо за оцінку водія': { en: 'Thank you for rating the driver', pl: 'Dziekujemy za ocene kierowcy' },
  'Дані власного авто відправлені адміну': { en: 'Own car data sent to admin', pl: 'Dane wlasnego auta wyslane do administratora' },
  'Оновлення позиції доступне тільки в межах Львова': { en: 'Location update available only within Lviv', pl: 'Aktualizacja pozycji dostepna tylko na terenie Lwowa' },
  'Геопозицію водія оновлено': { en: 'Driver geolocation updated', pl: 'Geolokalizacja kierowcy zaktualizowana' },
  'Не вдалося отримати геопозицію': { en: 'Failed to get geolocation', pl: 'Nie udalo sie pobrac geolokalizacji' },
  'Замовлення прийнято': { en: 'Order accepted', pl: 'Zamowienie przyjete' },
  'Замовлення відхилено': { en: 'Order rejected', pl: 'Zamowienie odrzucone' },
  'Статус замовлення оновлено': { en: 'Order status updated', pl: 'Status zamowienia zaktualizowano' },
  'Вкажіть мінімум 2 символи для пошуку': { en: 'Enter at least 2 characters to search', pl: 'Wpisz co najmniej 2 znaki do wyszukiwania' },
  'Спочатку оберіть parquet файл': { en: 'Select a parquet file first', pl: 'Najpierw wybierz plik parquet' },
  'Parquet імпортовано. Додано замовлень': { en: 'Parquet imported. Orders added', pl: 'Parquet zaimportowano. Dodano zamowien' },
};

const DRIVER_STATUS_LABELS = {
  uk: {
    free: 'В роботі',
    on_order: 'На замовленні',
    break: 'Пауза',
    inactive: 'Неактивний',
  },
  en: {
    free: 'Working',
    on_order: 'On order',
    break: 'Break',
    inactive: 'Inactive',
  },
  pl: {
    free: 'W pracy',
    on_order: 'W kursie',
    break: 'Przerwa',
    inactive: 'Nieaktywny',
  },
};

const ORDER_STATUS_LABELS = {
  uk: {
    pending: 'Очікує підтвердження',
    assigned: 'Прийнято водієм',
    driver_arrived: 'Водій на місці',
    in_progress: 'Поїздка триває',
    completed: 'Виконано',
    cancelled: 'Скасовано',
  },
  en: {
    pending: 'Awaiting confirmation',
    assigned: 'Accepted by driver',
    driver_arrived: 'Driver arrived',
    in_progress: 'Trip in progress',
    completed: 'Completed',
    cancelled: 'Cancelled',
  },
  pl: {
    pending: 'Oczekuje potwierdzenia',
    assigned: 'Przyjęte przez kierowcę',
    driver_arrived: 'Kierowca na miejscu',
    in_progress: 'Przejazd trwa',
    completed: 'Zakończono',
    cancelled: 'Anulowano',
  },
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

function displayDriverName(name, driverId, language = 'uk') {
  if (!name) return 'Невідомий водій';
  if (!/driver\d+/i.test(name) && !/import/i.test(name)) return name;
  const firstNames = FIRST_NAMES_BY_LANG[language] || FIRST_NAMES_BY_LANG.uk;
  const lastNames = LAST_NAMES_BY_LANG[language] || LAST_NAMES_BY_LANG.uk;
  const base = Number(driverId) || name.length;
  const first = firstNames[base % firstNames.length];
  const last = lastNames[Math.floor(base / firstNames.length) % lastNames.length];
  return `${first} ${last}`;
}

async function autoTranslateText(text, sourceLang, targetLang) {
  const normalized = (text || '').trim();
  if (!normalized || sourceLang === targetLang) return normalized;
  const response = await fetch(
    `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceLang}&tl=${targetLang}&dt=t&q=${encodeURIComponent(
      normalized
    )}`
  );
  if (!response.ok) throw new Error('Не вдалося виконати переклад');
  const payload = await response.json();
  if (!Array.isArray(payload?.[0])) return normalized;
  return payload[0].map((chunk) => chunk?.[0] || '').join('').trim() || normalized;
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
  const [language, setLanguage] = useState('uk');
  const [selectedRole, setSelectedRole] = useState('client');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);
  const [toastMessage, setToastMessage] = useState('');
  const [translationLoading, setTranslationLoading] = useState(false);
  const [dbTranslationCache, setDbTranslationCache] = useState({});

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

  const t = (key) => UI_COPY[language]?.[key] || UI_COPY.uk[key] || key;
  const tr = (ukText) => {
    if (language === 'uk') return ukText;
    return STATIC_TRANSLATIONS[ukText]?.[language] || ukText;
  };
  const classLabel = (carClass) => CLASS_LABELS[language]?.[carClass] || CLASS_LABELS.uk[carClass] || carClass;
  const orderStatusLabel = (status) => ORDER_STATUS_LABELS[language]?.[status] || ORDER_STATUS_LABELS.uk[status] || status;
  const driverStatusLabel = (status) => DRIVER_STATUS_LABELS[language]?.[status] || DRIVER_STATUS_LABELS.uk[status] || status;
  const localizeDbText = (value, i18nMap) => {
    const normalized = (value || '').trim();
    if (!normalized) return '-';
    const fromI18n = i18nMap?.[language];
    if (fromI18n?.trim()) return fromI18n.trim();
    if (language === 'uk') return normalized;
    return dbTranslationCache[`${language}:${normalized}`] || normalized;
  };
  const localizePersonName = (name) => {
    const normalized = (name || '').trim();
    if (!normalized) return t('unknownDriver');
    if (language === 'uk') return normalized;
    return dbTranslationCache[`name:${language}:${normalized}`] || normalized;
  };
  const driverDisplayName = (name, driverId) => localizePersonName(displayDriverName(name, driverId, language));

  const driverNameById = useMemo(
    () =>
      adminData.drivers.reduce((acc, item) => {
        acc[item.id] = driverDisplayName(item.driver_name, item.id);
        return acc;
      }, {}),
    [adminData.drivers, language, dbTranslationCache]
  );

  useEffect(() => {
    if (language === 'uk') return;
    const sourceTexts = [
      ...adminData.classApplications.map((item) => item.review_note),
      ...adminData.logs.flatMap((item) => [item.pickup_address, item.dropoff_address]),
      ...adminData.reviews.map((item) => item.comment),
      ...clientData.orders.flatMap((item) => [item.pickup_address, item.dropoff_address, item.review?.comment]),
      ...driverData.orders.flatMap((item) => [item.pickup_address, item.dropoff_address]),
      ...driverData.reviews.map((item) => item.comment),
    ]
      .map((item) => (item || '').trim())
      .filter((item) => item.length > 1);

    const unique = [...new Set(sourceTexts)].slice(0, 120);
    const missing = unique.filter((text) => !dbTranslationCache[`${language}:${text}`]);
    if (!missing.length) return;

    let cancelled = false;
    const run = async () => {
      const translatedEntries = await Promise.all(
        missing.map(async (text) => {
          try {
            const translated = await autoTranslateText(text, 'auto', language);
            return [`${language}:${text}`, translated || text];
          } catch {
            return [`${language}:${text}`, text];
          }
        })
      );
      if (cancelled) return;
      setDbTranslationCache((prev) => ({
        ...prev,
        ...Object.fromEntries(translatedEntries),
      }));
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [language, adminData.classApplications, adminData.logs, adminData.reviews, clientData.orders, driverData.orders, driverData.reviews, dbTranslationCache]);

  useEffect(() => {
    if (language === 'uk') return;
    const personNames = [
      ...adminData.applications.map((item) => `${item.first_name || ''} ${item.last_name || ''}`),
      ...adminData.drivers.map((item) => driverDisplayName(item.driver_name, item.id)),
      ...adminData.driverStats.map((item) => driverDisplayName(item.driver_name, item.driver_id)),
      ...adminData.fleetCars.map((item) => item.assigned_driver_name),
      ...(adminData.searchResults?.orders || []).flatMap((item) => [item.client_name, item.driver_name]),
      ...(adminData.searchResults?.drivers || []).map((item) => item.driver_name),
      ...(adminData.selectedDriverDetails ? [adminData.selectedDriverDetails.driver_name] : []),
    ]
      .map((item) => (item || '').trim())
      .filter((item) => item.length > 1 && item !== t('unknownDriver'));

    const unique = [...new Set(personNames)].slice(0, 120);
    const missing = unique.filter((name) => !dbTranslationCache[`name:${language}:${name}`]);
    if (!missing.length) return;

    let cancelled = false;
    const run = async () => {
      const translatedEntries = await Promise.all(
        missing.map(async (name) => {
          try {
            const translated = await autoTranslateText(name, 'auto', language);
            return [`name:${language}:${name}`, translated || name];
          } catch {
            return [`name:${language}:${name}`, name];
          }
        })
      );
      if (cancelled) return;
      setDbTranslationCache((prev) => ({
        ...prev,
        ...Object.fromEntries(translatedEntries),
      }));
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [
    language,
    adminData.applications,
    adminData.drivers,
    adminData.driverStats,
    adminData.fleetCars,
    adminData.searchResults,
    adminData.selectedDriverDetails,
    dbTranslationCache,
  ]);

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
        setFlash('success', tr('Сесію відновлено'));
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
      showToast(tr('Вхід виконано'));
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

        setFlash('success', tr('Заявку водія відправлено адміну'));
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
      setFlash('success', tr('Реєстрація успішна'));
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
    showToast(tr('Ви вийшли з системи'));
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
      setFlash('success', approve ? tr('Заявку підтверджено') : tr('Заявку відхилено'));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const reviewDriverClassApplication = async (applicationId, approve) => {
    const note = (adminData.classReviewNoteById[applicationId] || '').trim();
    if (note.length < 3) {
      setFlash('error', tr('Вкажіть коментар (мінімум 3 символи)'));
      return;
    }

    try {
      setLoading(true);
      const [reviewNoteEn, reviewNotePl] = await Promise.all([
        autoTranslateText(note, 'uk', 'en'),
        autoTranslateText(note, 'uk', 'pl'),
      ]);
      await apiRequest(
        `/management/driver-class-applications/${applicationId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            approve,
            review_note: note,
            review_note_i18n: {
              uk: note,
              en: reviewNoteEn,
              pl: reviewNotePl,
            },
            approved_car_class: approve ? adminData.classApprovalByApplication[applicationId] || null : null,
          }),
        },
        token
      );
      await loadAdminData(token);
      setFlash('success', approve ? tr('Заявку на клас авто підтверджено') : tr('Заявку на клас авто відхилено'));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const translateClassReviewNote = async (applicationId) => {
    const source = (adminData.classReviewNoteById[applicationId] || '').trim();
    if (source.length < 3) {
      setFlash('error', tr('Вкажіть коментар (мінімум 3 символи)'));
      return;
    }
    try {
      setTranslationLoading(true);
      const [en, pl] = await Promise.all([
        autoTranslateText(source, 'uk', 'en'),
        autoTranslateText(source, 'uk', 'pl'),
      ]);
      setAdminData((prev) => ({
        ...prev,
        classReviewNoteById: {
          ...prev.classReviewNoteById,
          [applicationId]: source,
        },
      }));
      showToast(`EN: ${en} | PL: ${pl}`);
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setTranslationLoading(false);
    }
  };

  const assignFleetCarToDriver = async (carId) => {
    const driverId = Number(adminData.selectedDriverByCar[carId]);
    if (!driverId) {
      setFlash('error', tr('Оберіть водія для видачі авто'));
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
      setFlash('success', tr('Авто видано водію'));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setLoading(false);
    }
  };

  const detectMyLocation = () => {
    if (!navigator.geolocation) {
      setFlash('error', tr('Браузер не підтримує геолокацію'));
      return;
    }

    setClientData((prev) => ({ ...prev, geolocLoading: true }));

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        if (!isWithinLviv(lat, lng)) {
          setClientData((prev) => ({ ...prev, geolocLoading: false }));
          setFlash('error', tr('Сервіс працює тільки в межах Львова'));
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
          setFlash('success', tr('Поточну адресу визначено'));
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
        setFlash('error', error.message || tr('Не вдалося отримати геолокацію'));
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
      setFlash('error', tr('Сервіс працює тільки в межах Львова'));
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
      setFlash('error', tr('Заповніть адреси поїздки'));
      return;
    }
    if (
      clientData.pickup_lat === null ||
      clientData.pickup_lng === null ||
      clientData.dropoff_lat === null ||
      clientData.dropoff_lng === null
    ) {
      setFlash('error', tr('Потрібно визначити координати обох адрес'));
      return;
    }
    if (!isWithinLviv(clientData.pickup_lat, clientData.pickup_lng) || !isWithinLviv(clientData.dropoff_lat, clientData.dropoff_lng)) {
      setFlash('error', tr('Замовлення доступні тільки в межах Львова'));
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
      setFlash('success', `Замовлення створено (${classLabel(comfortClass)})`);
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
      setFlash('success', tr('Пошук водія скасовано'));
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
      const sourceComment = (draft.comment || '').trim();
      const [commentEn, commentPl] = sourceComment
        ? await Promise.all([autoTranslateText(sourceComment, 'uk', 'en'), autoTranslateText(sourceComment, 'uk', 'pl')])
        : ['', ''];
      await apiRequest(
        '/orders/review',
        {
          method: 'POST',
          body: JSON.stringify({
            order_id: orderId,
            rating: Number(draft.rating ?? 5),
            comment: sourceComment || null,
            comment_i18n: sourceComment
              ? {
                  uk: sourceComment,
                  en: commentEn,
                  pl: commentPl,
                }
              : null,
          }),
        },
        token
      );
      await loadClientData(token);
      setFlash('success', tr('Дякуємо за оцінку водія'));
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
      setFlash('success', tr('Дані власного авто відправлені адміну'));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingOwnCar: false }));
    }
  };

  const updateDriverLocation = () => {
    if (!navigator.geolocation) {
      setFlash('error', tr('Браузер не підтримує геолокацію'));
      return;
    }

    setDriverData((prev) => ({ ...prev, loadingLocation: true }));
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        if (!isWithinLviv(position.coords.latitude, position.coords.longitude)) {
          setDriverData((prev) => ({ ...prev, loadingLocation: false }));
          setFlash('error', tr('Оновлення позиції доступне тільки в межах Львова'));
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
          setFlash('success', tr('Геопозицію водія оновлено'));
        } catch (error) {
          setFlash('error', parseError(error));
        } finally {
          setDriverData((prev) => ({ ...prev, loadingLocation: false }));
        }
      },
      (error) => {
        setDriverData((prev) => ({ ...prev, loadingLocation: false }));
        setFlash('error', error.message || tr('Не вдалося отримати геопозицію'));
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
      setFlash('success', `Статус водія: ${driverStatusLabel(nextStatus)}`);
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
      setFlash('success', accept ? tr('Замовлення прийнято') : tr('Замовлення відхилено'));
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
      setFlash('success', tr('Статус замовлення оновлено'));
    } catch (error) {
      setFlash('error', parseError(error));
    } finally {
      setDriverData((prev) => ({ ...prev, loadingOrderAction: false }));
    }
  };

  const searchAdminEntities = async () => {
    const query = adminData.searchQuery.trim();
    if (query.length < 2) {
      setFlash('error', tr('Вкажіть мінімум 2 символи для пошуку'));
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
      setFlash('error', tr('Спочатку оберіть parquet файл'));
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
      showToast(`${tr('Parquet імпортовано. Додано замовлень')}: ${payload.records?.orders || 0}`);
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
        label: classLabel(carClass),
        value: analytics.orders_by_car_class?.[carClass] || 0,
      }));
    }
    const source = adminData.statsMetric === 'revenue' ? analytics.revenue_by_period : analytics.orders_count_by_period;
    const periodLabels = {
      day: tr('1 день'),
      week: tr('1 тиждень'),
      month: tr('1 місяць'),
      year: tr('1 рік'),
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
      [driver.driver_id, driverDisplayName(driver.driver_name, driver.driver_id), driver.email]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [adminData.driverStats, adminData.driverStatsQuery, language, dbTranslationCache]);

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
        <h3>{tr('Панель адміністратора')}</h3>
        <div className="inline-actions admin-tabs">
          <button type="button" className={`secondary compact ${adminData.activeView === 'requests' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'requests' }))}>
            {tr('Заявки')}
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'logs' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'logs' }))}>
            {tr('Логи подій')}
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'stats' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'stats' }))}>
            {tr('Статистика')}
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'fleet' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'fleet' }))}>
            {tr('Автопарк')}
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'search' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'search' }))}>
            {tr('Пошук')}
          </button>
          <button type="button" className={`secondary compact ${adminData.activeView === 'import' ? 'active' : ''}`} onClick={() => setAdminData((prev) => ({ ...prev, activeView: 'import' }))}>
            {tr('Імпортувати дані')}
          </button>
        </div>
      </section>

      {adminData.activeView === 'requests' && (
        <>
          <section className="panel-card admin-column">
            <h3>{tr('Заявки водіїв')}</h3>
            <input
              placeholder={tr('Пошук заявки водія')}
              value={adminData.applicationsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, applicationsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredApplications.length === 0 && <p className="muted">{tr('Немає заявок. Розділ готовий до нових звернень.')}</p>}
              {filteredApplications.map((application) => (
                <div key={application.id} className="list-item">
                  <p>
                    <strong>{localizePersonName(`${application.first_name} ${application.last_name}`)}</strong>
                  </p>
                  <p>{application.email}</p>
                  <p>{tr('Права')}: {application.license_series} {application.license_number}</p>
                  <p>{tr('Статус')}: {application.status}</p>
                  {application.status === 'pending' && (
                    <div className="inline-actions">
                      <button type="button" className="primary compact" onClick={() => reviewDriverApplication(application.id, true)}>
                        {tr('Підтвердити')}
                      </button>
                      <button type="button" className="secondary compact" onClick={() => reviewDriverApplication(application.id, false)}>
                        {tr('Відхилити')}
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>{tr('Класи доступу водіїв')}</h3>
            <input
              placeholder={tr('Пошук заявки на клас')}
              value={adminData.pendingClassQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, pendingClassQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredPendingClassApplications.length === 0 && <p className="muted">{tr('Немає активних заявок. Очікуємо нові запити.')}</p>}
              {filteredPendingClassApplications.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>{driverNameById[application.driver_id] || `${t('unknownDriver')} #${application.driver_id}`}</strong></p>
                  <p>{tr('Клас заявки')}: {classLabel(application.requested_car_class)}</p>
                  <p>
                    {tr('Авто')}: {application.own_car_make} {application.own_car_model} ({application.own_car_plate})
                  </p>
                  <div className="class-approval-form">
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
                        {classLabel(carClass)}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder={t('adminComment')}
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
                    <button type="button" className="secondary compact" onClick={() => translateClassReviewNote(application.id)} disabled={translationLoading}>
                      {translationLoading ? '...' : t('translate')}
                    </button>
                    <button type="button" className="primary compact" onClick={() => reviewDriverClassApplication(application.id, true)}>
                      {t('approving')}
                    </button>
                    <button type="button" className="secondary compact" onClick={() => reviewDriverClassApplication(application.id, false)}>
                      {t('rejecting')}
                    </button>
                  </div>
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
            <h3>{tr('Логи замовлень')}</h3>
            <input
              placeholder={tr('Пошук логу замовлення')}
              value={adminData.orderLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, orderLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredOrderLogs.map((log) => (
                <div key={log.order_id} className="list-item">
                  <p><strong>{tr('Замовлення')} #{log.order_id}</strong></p>
                  <p>{orderStatusLabel(log.status)}</p>
                  <p>{localizeDbText(log.pickup_address)} {'->'} {localizeDbText(log.dropoff_address)}</p>
                  <p>{log.distance_km} км | {tr('Повна вартість')}: {money(log.final_cost ?? log.estimated_cost)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>{tr('Одобрення класу автомобіля (логи)')}</h3>
            <input
              placeholder={tr('Пошук логу по класу авто')}
              value={adminData.classLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, classLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredClassLogs.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>{tr('Заявки')} #{application.id}</strong></p>
                  <p>{tr('Водій')}: #{application.driver_id}</p>
                  <p>{tr('Статус')}: {application.status}</p>
                  <p>{tr('Коментар')}: {localizeDbText(application.review_note, application.review_note_i18n)}</p>
                </div>
              ))}
            </div>
          </section>
          <section className="panel-card admin-column">
            <h3>{tr('Логи заявок водіїв')}</h3>
            <input
              placeholder={tr('Пошук логу заявки водія')}
              value={adminData.driverApplicationLogsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, driverApplicationLogsQuery: event.target.value }))}
            />
            <div className="scroll-list">
              {filteredDriverApplicationLogs.map((application) => (
                <div key={application.id} className="list-item">
                  <p><strong>{tr('Заявки')} #{application.id}</strong></p>
                  <p>{localizePersonName(`${application.first_name} ${application.last_name}`)}</p>
                  <p>{application.email} | {application.phone}</p>
                  <p>{tr('Статус')}: {application.status}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {adminData.activeView === 'stats' && (
        <>
          <section className="panel-card admin-column">
            <h3>{tr('Статистика водія')}</h3>
            <input
              placeholder={tr("Пошук водія: ім'я / email / id")}
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
                  {driverDisplayName(driver.driver_name, driver.driver_id)} | {driver.completed_orders} {tr('поїздок')}
                </button>
              ))}
              {adminData.selectedDriverDetails && (
                <div className="list-item">
                  <p><strong>{driverDisplayName(adminData.selectedDriverDetails.driver_name, adminData.selectedDriverDetails.driver_id)}</strong></p>
                  <p>Email: {adminData.selectedDriverDetails.email}</p>
                  <p>{tr('Кількість поїздок')}: {adminData.selectedDriverDetails.total_trips}</p>
                  <p>{tr('Авто')}: {adminData.selectedDriverDetails.active_car || '-'}</p>
                  <p>{tr('Рейтинг')}: {adminData.selectedDriverDetails.avg_rating}/5</p>
                </div>
              )}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>{tr('Статистика')}</h3>
            <select
              value={adminData.statsMetric}
              onChange={(event) => setAdminData((prev) => ({ ...prev, statsMetric: event.target.value }))}
            >
              <option value="revenue">{tr('Каса')}</option>
              <option value="orders">{tr('Кількість замовлень')}</option>
              <option value="fleet">{tr('Кількість авто в автопарку')}</option>
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
            <h3>{tr('Відгуки клієнтів')}</h3>
            <input
              placeholder={tr('Пошук конкретного відгуку')}
              value={adminData.adminReviewsQuery}
              onChange={(event) => setAdminData((prev) => ({ ...prev, adminReviewsQuery: event.target.value }))}
            />
            {filteredAdminReviews.slice(0, 12).map((review) => (
              <div key={review.id} className="list-item">
                <p><strong>{tr('Замовлення')} #{review.order_id}</strong> | {tr('Оцінка')}: {review.rating}/5</p>
                <p>{localizeDbText(review.comment, review.comment_i18n)}</p>
              </div>
            ))}
          </section>
        </>
      )}

      {adminData.activeView === 'search' && (
        <>
          <section className="panel-card wide">
            <h3>{tr('Пошук (замовлення / водії)')}</h3>
            <p className="muted">{tr('Пошук за телефоном, номером поїздки, ПІБ клієнта/водія, email, номером авто.')}</p>
            <div className="input-row">
              <input
                value={adminData.searchQuery}
                onChange={(event) => setAdminData((prev) => ({ ...prev, searchQuery: event.target.value }))}
                placeholder={tr('Введіть запит')}
              />
              <button type="button" className="primary compact" onClick={searchAdminEntities} disabled={adminData.searching}>
                {adminData.searching ? tr('Пошук...') : tr('Знайти')}
              </button>
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>{tr('Знайдені замовлення')}</h3>
            <div className="scroll-list">
              {(adminData.searchResults?.orders || []).map((order) => (
                <div key={order.order_id} className="list-item">
                  <p><strong>{tr('Замовлення')} #{order.order_id}</strong> ({order.status})</p>
                  <p>{tr('Клієнт')}: {localizePersonName(order.client_name)} | {order.client_phone}</p>
                  <p>{tr('Маршрут')}: {localizeDbText(order.pickup_address)} {'->'} {localizeDbText(order.dropoff_address)}</p>
                  <p>{tr('Водій')}: {order.driver_name ? localizePersonName(order.driver_name) : '-'} | {tr('Сума')}: {money(order.final_cost)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-card admin-column">
            <h3>{tr('Знайдені водії')}</h3>
            <div className="scroll-list">
              {(adminData.searchResults?.drivers || []).map((driver) => (
                <div key={driver.driver_id} className="list-item">
                  <p><strong>{driverDisplayName(driver.driver_name, driver.driver_id)}</strong> ({driver.status})</p>
                  <p>{driver.phone} | {driver.email}</p>
                  <p>{tr('Права')}: {driver.license_number}</p>
                  <p>{tr('Авто')}: {driver.active_car || '-'}</p>
                  <p>{tr('Індивідуальна статистика')}: {driver.completed_orders} {tr('поїздок')}, {tr('Рейтинг').toLowerCase()} {driver.avg_rating}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {adminData.activeView === 'fleet' && (
        <section className="panel-card wide">
          <h3>{tr('Автопарк')}</h3>
          <input
            placeholder={tr('Пошук авто: водій / номер / марка / модель')}
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
                <span>{tr('Клас')}: {classLabel(car.comfort_class)}</span>
                <span>{car.is_occupied ? `${tr('Зайняте')} (${car.assigned_driver_name ? localizePersonName(car.assigned_driver_name) : tr('водій')})` : tr('Вільне')}</span>
              </button>
            ))}
          </div>
          {selectedFleetCar && (
            <div className="car-detail">
              <h4>{selectedFleetCar.make} {selectedFleetCar.model}</h4>
              <p><strong>{tr('Номер')}:</strong> {selectedFleetCar.plate_number}</p>
              <p><strong>{tr('Рік')}:</strong> {selectedFleetCar.production_year}</p>
              <p><strong>{tr('Двигун')}:</strong> {selectedFleetCar.engine}</p>
              <p><strong>{tr('Коробка')}:</strong> {selectedFleetCar.transmission}</p>
              <p><strong>{tr('Водій')}:</strong> {selectedFleetCar.assigned_driver_name ? localizePersonName(selectedFleetCar.assigned_driver_name) : tr('Не призначено')}</p>

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
                    <option value="">{tr('Оберіть водія')}</option>
                    {adminData.drivers.map((driver) => (
                      <option key={driver.id} value={driver.id}>
                        {driverDisplayName(driver.driver_name, driver.id)} ({driver.status})
                      </option>
                    ))}
                  </select>
                  <button type="button" className="primary compact" onClick={() => assignFleetCarToDriver(selectedFleetCar.id)}>
                    {tr('Видати авто')}
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {adminData.activeView === 'import' && (
        <section className="panel-card wide">
          <h3>{tr('Імпорт даних')}</h3>
          <p className="muted">{tr('Оберіть потрібний файл для імпорту даних.')}</p>
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
              {adminData.importingParquet ? tr('Імпорт...') : tr('Імпортувати')}
            </button>
          </div>
        </section>
      )}
    </div>
  );

  const renderClientPanel = () => (
    <div className="dashboard-grid">
      <section className="panel-card wide">
        <h3>{tr('Замовлення поїздки')}</h3>
        <div className="form-grid">
          <button type="button" className="secondary" onClick={detectMyLocation} disabled={clientData.geolocLoading}>
            {clientData.geolocLoading ? tr('Визначаємо геолокацію...') : tr('Дозволити геопозицію')}
          </button>

          <label htmlFor="pickup_address">{tr('Звідки їдете')}</label>
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
              placeholder={tr('Вкажіть адресу відправлення')}
            />
            <button type="button" className="secondary compact" onClick={() => resolveAddress('pickup')} disabled={clientData.geocodeLoading}>
              {tr('Знайти')}
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

          <label htmlFor="dropoff_address">{tr('Куди їдете')}</label>
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
              placeholder={tr('Вкажіть адресу призначення')}
            />
            <button type="button" className="secondary compact" onClick={() => resolveAddress('dropoff')} disabled={clientData.geocodeLoading}>
              {tr('Знайти')}
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
        <h3>{tr('Класи авто і вартість')}</h3>
        <p>{tr('Вартість: Економ 25, Стандарт 35, Комфорт 35, Бізнес 50 грн/км.')}</p>
        {clientData.quote ? (
          <>
            <p>{tr('Відстань')}: <strong>{clientData.quote.distance_km} км</strong></p>
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
                  <strong>{classLabel(carClass)}</strong>
                  <span>{money(clientData.quote.prices[carClass])}</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <p>{tr('Вкажіть обидві адреси, щоб побачити тариф.')}</p>
        )}
        {clientData.pendingOrderConfirmation && (
          <div className="list-item">
            <p><strong>{tr('Підтвердити замовлення')}</strong></p>
            <p>{tr('Звідки')}: {shortAddress(clientData.pendingOrderConfirmation.pickup_address)}</p>
            <p>{tr('Куди')}: {shortAddress(clientData.pendingOrderConfirmation.dropoff_address)}</p>
            <div className="inline-actions">
              <button type="button" className="primary compact" onClick={confirmCreateOrder} disabled={clientData.creatingOrder}>
                {tr('Підтвердити')}
              </button>
              <button
                type="button"
                className="secondary compact"
                onClick={() => setClientData((prev) => ({ ...prev, pendingOrderConfirmation: null }))}
                disabled={clientData.creatingOrder}
              >
                {tr('Скасувати')}
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="panel-card wide">
        <h3>{clientData.ordersTab === 'active' ? tr('Мої замовлення') : tr('Моя історія поїздок')}</h3>
        <div className="inline-actions full-width-actions">
          <button
            type="button"
            className={`secondary compact ${clientData.ordersTab === 'active' ? 'active' : ''}`}
            onClick={() => setClientData((prev) => ({ ...prev, ordersTab: 'active' }))}
          >
            {tr('Мої замовлення')}
          </button>
          <button
            type="button"
            className={`secondary compact ${clientData.ordersTab === 'history' ? 'active' : ''}`}
            onClick={() => setClientData((prev) => ({ ...prev, ordersTab: 'history' }))}
          >
            {tr('Моя історія поїздок')}
          </button>
        </div>
        {(clientData.ordersTab === 'active'
          ? clientData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : clientData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).length === 0 && <p>{clientData.ordersTab === 'active' ? tr('Активних замовлень немає') : tr('Історія поїздок порожня')}</p>}
        {(clientData.ordersTab === 'active'
          ? clientData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : clientData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).map((order) => (
          <div key={order.id} className="list-item">
            <p><strong>{tr('Замовлення')} #{order.client_order_number}</strong> | {orderStatusLabel(order.status)}</p>
            <p>{localizeDbText(order.pickup_address)} {'->'} {localizeDbText(order.dropoff_address)}</p>
            <p>{order.distance_km} км | {classLabel(order.requested_comfort_class)}</p>
            <p>{tr('Вартість')}: {money(order.final_cost ?? order.estimated_cost)}</p>
            {['pending', 'assigned', 'driver_arrived'].includes(order.status) && (
              <button
                type="button"
                className="secondary compact"
                onClick={() => cancelOrderSearch(order.id)}
                disabled={clientData.cancellingOrder}
              >
                {tr('Відмінити пошук водія')}
              </button>
            )}
            {order.status === 'completed' && !order.review && (
              <div className="form-grid">
                <label htmlFor={`rating-${order.id}`}>{tr('Оцінка водія (0-5)')}</label>
                <input
                  id={`rating-${order.id}`}
                  type="number"
                  min="0"
                  max="5"
                  value={clientData.reviewDraftByOrder[order.id]?.rating ?? 5}
                  onChange={(event) => updateReviewDraft(order.id, 'rating', event.target.value)}
                />
                <label htmlFor={`comment-${order.id}`}>{tr('Відгук')}</label>
                <input
                  id={`comment-${order.id}`}
                  value={clientData.reviewDraftByOrder[order.id]?.comment ?? ''}
                  onChange={(event) => updateReviewDraft(order.id, 'comment', event.target.value)}
                  placeholder={tr('Напишіть короткий коментар')}
                />
                <button
                  type="button"
                  className="primary compact"
                  onClick={() => submitReview(order.id)}
                  disabled={clientData.creatingReview}
                >
                  {tr('Надіслати відгук')}
                </button>
              </div>
            )}
            {order.review && (
              <p>
                {tr('Ваша оцінка')}: {order.review.rating}/5 {order.review.comment ? `| "${localizeDbText(order.review.comment, order.review.comment_i18n)}"` : ''}
              </p>
            )}
          </div>
        ))}
      </section>
    </div>
  );

  const renderDriverPanel = () => (
    <div className="dashboard-grid driver-dashboard">
      <section className="panel-card wide">
        <h3>{tr('Профіль водія')}</h3>
        {!driverData.profile && <p>{tr('Завантаження...')}</p>}
        {driverData.profile && (
          <>
            <p><strong>{tr('Статус')}:</strong> {driverStatusLabel(driverData.profile.status)}</p>
            <p><strong>{tr('Підтверджений клас')}:</strong> {classLabel(driverData.profile.approved_car_class)}</p>
            <p><strong>{tr('Доступні замовлення')}:</strong> {driverAllowedClasses.map((item) => classLabel(item)).join(', ')}</p>
            <p><strong>{tr('Робота на власному авто')}:</strong> {driverData.profile.uses_own_car ? tr('Так') : tr('Ні')}</p>
            {driverData.profile.last_class_application_status && (
              <p>
                <strong>{tr('Остання заявка на клас авто')}:</strong> {driverData.profile.last_class_application_status}
                {driverData.profile.last_class_application_note
                  ? ` | ${localizeDbText(
                      driverData.profile.last_class_application_note,
                      driverData.profile.last_class_application_note_i18n
                    )}`
                  : ''}
              </p>
            )}

            {driverData.profile.assigned_company_car && (
              <div className="car-detail compact">
                <h4>{tr('Видане авто таксопарку')}</h4>
                <p>
                  {driverData.profile.assigned_company_car.make} {driverData.profile.assigned_company_car.model} ({driverData.profile.assigned_company_car.plate_number})
                </p>
                <p>{tr('Клас')}: {classLabel(driverData.profile.assigned_company_car.comfort_class)}</p>
              </div>
            )}

            {driverData.profile.own_car && (
              <div className="car-detail compact">
                <h4>{tr('Моє авто')}</h4>
                <p>
                  {driverData.profile.own_car.make} {driverData.profile.own_car.model} ({driverData.profile.own_car.plate_number})
                </p>
              </div>
            )}

            <div className="inline-actions driver-status-actions">
              <button type="button" className="primary" onClick={() => setDriverStatus('free')} disabled={driverData.loadingStatus}>
                {tr('Почати роботу')}
              </button>
              <button type="button" className="secondary" onClick={() => setDriverStatus('break')} disabled={driverData.loadingStatus}>
                {tr('Пауза')}
              </button>
              <button type="button" className="secondary" onClick={() => setDriverStatus('inactive')} disabled={driverData.loadingStatus}>
                {tr('Завершити зміну')}
              </button>
              <button type="button" className="secondary" onClick={() => setDriverData((prev) => ({ ...prev, ownCarModalOpen: true }))}>
                {tr('Працювати на власному авто')}
              </button>
            </div>

            <button type="button" className="secondary driver-gps-button" onClick={updateDriverLocation} disabled={driverData.loadingLocation}>
              {driverData.loadingLocation ? tr('Оновлюємо геопозицію...') : tr('Активувати GPS трекер')}
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
            <h3>{tr('Працюю на своєму авто')}</h3>
            <form className="form-grid" onSubmit={submitDriverOwnCar}>
          <label htmlFor="make">{tr('Марка')}</label>
          <input id="make" name="make" value={driverData.ownCarForm.make} onChange={updateDriverOwnCarField} required />

          <label htmlFor="model">{tr('Модель')}</label>
          <input id="model" name="model" value={driverData.ownCarForm.model} onChange={updateDriverOwnCarField} required />

          <label htmlFor="production_year">{tr('Рік')}</label>
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

          <label htmlFor="plate_number">{tr('Номер авто')}</label>
          <input id="plate_number" name="plate_number" value={driverData.ownCarForm.plate_number} onChange={updateDriverOwnCarField} required />

          <label htmlFor="engine">{tr('Двигун')}</label>
          <input id="engine" name="engine" value={driverData.ownCarForm.engine} onChange={updateDriverOwnCarField} required />

          <label htmlFor="transmission">{tr('Коробка')}</label>
          <select id="transmission" name="transmission" value={driverData.ownCarForm.transmission} onChange={updateDriverOwnCarField}>
            <option value="automatic">Automatic</option>
            <option value="manual">Manual</option>
          </select>

          <label htmlFor="requested_car_class">{tr('Клас, який запитуєте')}</label>
          <select
            id="requested_car_class"
            name="requested_car_class"
            value={driverData.ownCarForm.requested_car_class}
            onChange={updateDriverOwnCarField}
          >
            {CLASS_ORDER.map((carClass) => (
              <option key={carClass} value={carClass}>
                {classLabel(carClass)}
              </option>
            ))}
          </select>

              <button type="submit" className="primary" disabled={driverData.loadingOwnCar}>
                {driverData.loadingOwnCar ? tr('Відправка...') : tr('Відправити на підтвердження')}
              </button>
              <button type="button" className="secondary" onClick={() => setDriverData((prev) => ({ ...prev, ownCarModalOpen: false }))}>
                {tr('Закрити')}
              </button>
            </form>
          </section>
        </div>
      )}

      <section className="panel-card balanced-panel">
        <div className="driver-orders-header">
          <h3>{driverData.ordersTab === 'active' ? tr('Мої замовлення') : tr('Історія поїздок')}</h3>
          <button
            type="button"
            className={`secondary compact ${driverData.ordersTab === 'history' ? 'active' : ''}`}
            onClick={() => setDriverData((prev) => ({ ...prev, ordersTab: prev.ordersTab === 'active' ? 'history' : 'active' }))}
          >
            {tr('Історія поїздок')}
          </button>
        </div>
        {(driverData.ordersTab === 'active'
          ? driverData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : driverData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).length === 0 && <p>{tr('Поки що замовлень немає')}</p>}
        {(driverData.ordersTab === 'active'
          ? driverData.orders.filter((order) => ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
          : driverData.orders.filter((order) => !ACTIVE_CLIENT_ORDER_STATUSES.has(order.status))
        ).map((order) => (
          <div key={order.id} className="list-item">
            <p><strong>{tr('Замовлення')} #{order.id}</strong> | {orderStatusLabel(order.status)}</p>
            <p>{localizeDbText(order.pickup_address)} {'->'} {localizeDbText(order.dropoff_address)}</p>
            <p>{tr('Клас')}: {classLabel(order.requested_comfort_class)} | {tr('Дистанція')}: {order.distance_km} км</p>
            <p>{tr('Оплата водію')}: {money(order.driver_payout)}</p>

            {order.status === 'pending' && (
              <div className="inline-actions">
                <button type="button" className="primary compact" onClick={() => driverOrderDecision(order.id, true)} disabled={driverData.loadingOrderAction}>
                  {tr('Прийняти')}
                </button>
                <button type="button" className="secondary compact" onClick={() => driverOrderDecision(order.id, false)} disabled={driverData.loadingOrderAction}>
                  {tr('Відхилити')}
                </button>
              </div>
            )}

            {order.status === 'assigned' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'driver_arrived')} disabled={driverData.loadingOrderAction}>
                {tr('Я прибув')}
              </button>
            )}

            {order.status === 'driver_arrived' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'in_progress')} disabled={driverData.loadingOrderAction}>
                {tr('Почати поїздку')}
              </button>
            )}

            {order.status === 'in_progress' && (
              <button type="button" className="primary compact" onClick={() => updateOrderStatus(order.id, 'completed')} disabled={driverData.loadingOrderAction}>
                {tr('Завершити поїздку')}
              </button>
            )}
          </div>
        ))}
      </section>

      <section className="panel-card balanced-panel">
        <h3>{tr('Відгуки клієнтів')}</h3>
        <input
          placeholder={tr('Пошук відгуку')}
          value={driverData.reviewsQuery}
          onChange={(event) => setDriverData((prev) => ({ ...prev, reviewsQuery: event.target.value }))}
        />
        {driverData.reviews.length === 0 && <p>{tr('Поки що відгуків немає')}</p>}
        {driverData.reviews
          .filter((review) =>
            [review.comment, review.rating, review.id].join(' ').toLowerCase().includes(driverData.reviewsQuery.trim().toLowerCase())
          )
          .slice(0, 12)
          .map((review) => (
          <div key={review.id} className="list-item">
            <p><strong>{tr('Оцінка')}:</strong> {review.rating}/5</p>
            <p>{localizeDbText(review.comment, review.comment_i18n)}</p>
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
          <div className="inline-actions">
            <label htmlFor="ui-lang">{t('language')}</label>
            <select id="ui-lang" value={language} onChange={(event) => setLanguage(event.target.value)}>
              {UI_LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {lang.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          {user ? (
            <button type="button" className="secondary compact" onClick={logout}>
              {tr('Вийти')}
            </button>
          ) : null}
        </div>

        {message && <p className={`message ${messageType}`}>{message}</p>}

        {!user && (
          <div className="auth-layout">
            <form className="panel-card auth-card form-grid" onSubmit={submitAuth}>
              <h3>{mode === 'login' ? tr('Вхід') : tr('Реєстрація')}</h3>

              {mode === 'register' && (
                <div className="inline-actions">
                  <button type="button" className={`secondary compact ${selectedRole === 'client' ? 'active' : ''}`} onClick={() => setSelectedRole('client')}>
                    {tr('Клієнт')}
                  </button>
                  <button type="button" className={`secondary compact ${selectedRole === 'driver' ? 'active' : ''}`} onClick={() => setSelectedRole('driver')}>
                    {tr('Водій')}
                  </button>
                </div>
              )}

              {mode === 'register' && (
                <>
                  <label htmlFor="first_name">{tr("Ім'я")}</label>
                  <input id="first_name" name="first_name" value={form.first_name} onChange={updateField} required />

                  <label htmlFor="last_name">{tr('Прізвище')}</label>
                  <input id="last_name" name="last_name" value={form.last_name} onChange={updateField} required />

                  <label htmlFor="phone">{tr('Телефон')}</label>
                  <input id="phone" name="phone" value={form.phone} onChange={updateField} required />
                </>
              )}

              <label htmlFor="email">Email</label>
              <input id="email" name="email" type="email" value={form.email} onChange={updateField} required />

              <label htmlFor="password">{tr('Пароль')}</label>
              <input id="password" name="password" type="password" value={form.password} onChange={updateField} required />

              {mode === 'register' && selectedRole === 'driver' && (
                <>
                  <label htmlFor="license_series">{tr('Серія посвідчення')}</label>
                  <input id="license_series" name="license_series" value={form.license_series} onChange={updateField} required />

                  <label htmlFor="license_number">{tr('Номер посвідчення')}</label>
                  <input id="license_number" name="license_number" value={form.license_number} onChange={updateField} required />
                </>
              )}

              <button type="submit" className="primary" disabled={loading}>
                {loading ? tr('Обробка...') : mode === 'login' ? tr('Увійти') : tr('Зареєструватись')}
              </button>

              <button
                type="button"
                className="secondary"
                onClick={() => setMode((prev) => (prev === 'login' ? 'register' : 'login'))}
                disabled={loading}
              >
                {mode === 'login' ? tr('Ще немає акаунта?') : tr('Вже є акаунт?')}
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
