
-- 1. Т2. Получение сводных показателей дашборда
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM "Постояльцы") AS total_guests,
    (SELECT COALESCE(SUM("сумма"), 0) FROM "Счета" WHERE "статус_оплаты" = 'оплачен') AS total_revenue,
    (SELECT COUNT(*) FROM "Проживания" WHERE "дата_выезда" IS NULL) AS active_stays;

-- 2. Т7. Просмотр списка бронирований
CREATE OR REPLACE VIEW v_bookings_journal AS
SELECT
    b."ID_брони",
    g."фамилия" || ' ' || g."имя" AS "Гость",
    b."номер_комнаты",
    b."дата_заезда",
    b."дата_выезда",
    b."статус",
    b."организация"
FROM "Брони" b
JOIN "Постояльцы" g ON b."ID_постояльца" = g."ID_постояльца"
ORDER BY b."ID_брони" DESC;

-- 3. Т9. Просмотр текущих проживаний
CREATE OR REPLACE VIEW v_active_stays AS
SELECT
    s."ID_проживания",
    g."фамилия" || ' ' || g."имя" AS "Гость",
    s."номер_комнаты",
    s."дата_заезда",
    r."цена"
FROM "Проживания" s
JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца"
JOIN "Номера" r ON s."номер_комнаты" = r."номер_комнаты"
WHERE s."дата_выезда" IS NULL;

-- 4. Т13. Просмотр реестра счетов
CREATE OR REPLACE VIEW v_invoices_registry AS
SELECT
    i."ID_счета",
    g."фамилия" || ' ' || g."имя" AS "Гость",
    s."номер_комнаты",
    i."сумма",
    i."дата_выдачи",
    i."статус_оплаты"
FROM "Счета" i
JOIN "Проживания" st ON i."ID_проживания" = st."ID_проживания"
JOIN "Постояльцы" g ON st."ID_постояльца" = g."ID_постояльца"
JOIN "Номера" s ON st."номер_комнаты" = s."номер_комнаты"
ORDER BY i."ID_счета" DESC;

-- 5. Т15. Формирование отчета по выездам на сегодня и завтра
CREATE OR REPLACE VIEW v_upcoming_checkouts AS
SELECT
    s."ID_проживания",
    g."фамилия",
    s."номер_комнаты",
    s."дата_выезда"
FROM "Проживания" s
JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца"
WHERE s."дата_выезда" BETWEEN CURRENT_DATE AND CURRENT_DATE + 1;

-- 6. Т19. Расчет и начисление зарплаты сотрудника за месяц
CREATE OR REPLACE FUNCTION fn_calculate_salary(
    p_emp_id INTEGER,
    p_month VARCHAR(7),
    p_bonus NUMERIC(10, 2) DEFAULT 0,
    p_deduction NUMERIC(10, 2) DEFAULT 0
)
RETURNS NUMERIC(10, 2) AS $$
DECLARE
    v_salary NUMERIC(10, 2);
    v_days INTEGER;
    v_total NUMERIC(10, 2);
BEGIN
    SELECT "оклад" INTO v_salary
    FROM "Сотрудники"
    WHERE "ID_сотрудника" = p_emp_id;

    IF v_salary IS NULL THEN
        RAISE EXCEPTION 'Сотрудник с ID % не найден', p_emp_id;
    END IF;

    SELECT "отработано_дней" INTO v_days
    FROM "Табели_учета"
    WHERE "ID_сотрудника" = p_emp_id AND "месяц" = p_month;

    IF v_days IS NULL THEN
        v_days := 21;
    END IF;

    v_total := ROUND((v_salary / 21.0) * v_days + p_bonus - p_deduction, 2);

    INSERT INTO "Начисления_зарплаты" ("ID_сотрудника", "месяц", "премия", "вычет", "итого")
    VALUES (p_emp_id, p_month, p_bonus, p_deduction, v_total);

    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- 7. Т21. Расчет коэффициента загрузки номерного фонда за период (%)
CREATE OR REPLACE FUNCTION fn_hotel_occupancy(
    p_start DATE,
    p_end DATE
)
RETURNS NUMERIC(5, 2) AS $$
DECLARE
    v_total_rooms INTEGER;
    v_days INTEGER;
    v_stays INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_rooms FROM "Номера";
    v_days := (p_end - p_start) + 1;

    IF v_total_rooms = 0 OR v_days <= 0 THEN
        RETURN 0;
    END IF;

    SELECT COUNT(*) INTO v_stays
    FROM "Проживания"
    WHERE "дата_заезда" >= p_start AND "дата_заезда" <= p_end;

    RETURN ROUND((v_stays::NUMERIC / (v_total_rooms * v_days)) * 100, 2);
END;
$$ LANGUAGE plpgsql;

-- 8. Т22.1. Аналитический отчет: популярность доп. услуг и выручка
CREATE OR REPLACE VIEW v_report_services_revenue AS
SELECT
    u."название" AS "Услуга",
    SUM(ou."количество") AS "Кол-во",
    SUM(ou."количество" * u."цена") AS "Выручка"
FROM "Услуги" u
JOIN "Оказанные_услуги" ou ON u."ID_услуги" = ou."ID_услуги"
GROUP BY u."название"
ORDER BY "Выручка" DESC;

-- 9. Т22.2. Аналитический отчет: список гостей с задолженностью
CREATE OR REPLACE VIEW v_report_debtors AS
SELECT
    g."фамилия" AS "Фамилия",
    g."имя" AS "Имя",
    i."сумма" AS "Долг",
    i."дата_выдачи" AS "Дата счета"
FROM "Постояльцы" g
JOIN "Проживания" s ON g."ID_постояльца" = s."ID_постояльца"
JOIN "Счета" i ON s."ID_проживания" = i."ID_проживания"
WHERE i."статус_оплаты" = 'не оплачен';

-- 10. Т22.3. Аналитический отчет: рейтинг номеров по средним оценкам из отзывов
CREATE OR REPLACE VIEW v_report_rooms_rating AS
SELECT
    "номер_комнаты" AS "Номер",
    ROUND(AVG("оценка"), 1) AS "Средний балл"
FROM "Отзывы"
GROUP BY "номер_комнаты"
ORDER BY "Средний балл" DESC;
