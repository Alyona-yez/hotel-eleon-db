-- Гостиница «Элеон». Схема PostgreSQL.

-- Очистка (если таблицы уже есть)
DROP TABLE IF EXISTS "Отзывы" CASCADE;
DROP TABLE IF EXISTS "Начисления_зарплаты" CASCADE;
DROP TABLE IF EXISTS "Табели_учета" CASCADE;
DROP TABLE IF EXISTS "Платежи" CASCADE;
DROP TABLE IF EXISTS "Счета" CASCADE;
DROP TABLE IF EXISTS "Оказанные_услуги" CASCADE;
DROP TABLE IF EXISTS "Услуги" CASCADE;
DROP TABLE IF EXISTS "Проживания" CASCADE;
DROP TABLE IF EXISTS "Брони" CASCADE;
DROP TABLE IF EXISTS "Сотрудники" CASCADE;
DROP TABLE IF EXISTS "Постояльцы" CASCADE;
DROP TABLE IF EXISTS "Номера" CASCADE;
DROP TABLE IF EXISTS "Категории_номеров" CASCADE;

-- 1. Категории номеров
CREATE TABLE "Категории_номеров" (
    "ID_категории" SERIAL PRIMARY KEY,
    "название" VARCHAR(50) NOT NULL UNIQUE,
    "количество_мест" INTEGER NOT NULL CHECK ("количество_мест" > 0),
    "базовая_цена" NUMERIC(10, 2) NOT NULL CHECK ("базовая_цена" >= 0),
    "описание" TEXT
);

-- 2. Номера
CREATE TABLE "Номера" (
    "номер_комнаты" VARCHAR(10) PRIMARY KEY,
    "ID_категории" INTEGER NOT NULL REFERENCES "Категории_номеров"("ID_категории") ON DELETE RESTRICT,
    "количество_мест" INTEGER NOT NULL CHECK ("количество_мест" > 0),
    "цена" NUMERIC(10, 2) NOT NULL CHECK ("цена" >= 0),
    "описание" TEXT,
    "статус" VARCHAR(20) NOT NULL DEFAULT 'доступен' CHECK ("статус" IN ('доступен', 'уборка', 'ремонт', 'занят'))
);

-- 3. Постояльцы (добавлены телефон и отчество)
CREATE TABLE "Постояльцы" (
    "ID_постояльца" SERIAL PRIMARY KEY,
    "фамилия" VARCHAR(100) NOT NULL,
    "имя" VARCHAR(100) NOT NULL,
    "отчество" VARCHAR(100),
    "паспорт" VARCHAR(20) NOT NULL UNIQUE,
    "телефон" VARCHAR(20)
);

-- 4. Сотрудники (добавлены оклад, телефон, отчество)
CREATE TABLE "Сотрудники" (
    "ID_сотрудника" SERIAL PRIMARY KEY,
    "фамилия" VARCHAR(100) NOT NULL,
    "имя" VARCHAR(100) NOT NULL,
    "отчество" VARCHAR(100),
    "должность" VARCHAR(100) NOT NULL,
    "телефон" VARCHAR(20),
    "оклад" NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK ("оклад" >= 0)
);

-- 5. Брони (добавлены дата выезда, статус, организация)
CREATE TABLE "Брони" (
    "ID_брони" SERIAL PRIMARY KEY,
    "ID_постояльца" INTEGER NOT NULL REFERENCES "Постояльцы"("ID_постояльца") ON DELETE RESTRICT,
    "номер_комнаты" VARCHAR(10) NOT NULL REFERENCES "Номера"("номер_комнаты") ON DELETE RESTRICT,
    "ID_сотрудника" INTEGER REFERENCES "Сотрудники"("ID_сотрудника") ON DELETE SET NULL,
    "дата_бронирования" DATE NOT NULL DEFAULT CURRENT_DATE,
    "дата_заезда" DATE NOT NULL,
    "дата_выезда" DATE NOT NULL,
    "статус" VARCHAR(20) NOT NULL DEFAULT 'активна' CHECK ("статус" IN ('активна', 'отменена', 'завершена')),
    "организация" VARCHAR(100),
    CHECK ("дата_выезда" > "дата_заезда")
);

-- 6. Проживания
CREATE TABLE "Проживания" (
    "ID_проживания" SERIAL PRIMARY KEY,
    "ID_брони" INTEGER UNIQUE REFERENCES "Брони"("ID_брони") ON DELETE SET NULL,
    "ID_постояльца" INTEGER NOT NULL REFERENCES "Постояльцы"("ID_постояльца") ON DELETE RESTRICT,
    "номер_комнаты" VARCHAR(10) NOT NULL REFERENCES "Номера"("номер_комнаты") ON DELETE RESTRICT,
    "дата_заезда" DATE NOT NULL,
    "дата_выезда" DATE,
    CHECK ("дата_выезда" IS NULL OR "дата_выезда" >= "дата_заезда")
);

-- 7. Услуги
CREATE TABLE "Услуги" (
    "ID_услуги" SERIAL PRIMARY KEY,
    "название" VARCHAR(100) NOT NULL UNIQUE,
    "цена" NUMERIC(10, 2) NOT NULL CHECK ("цена" >= 0),
    "описание" TEXT,
    "категория" VARCHAR(50) NOT NULL CHECK ("категория" IN ('питание', 'быт', 'транспорт'))
);

-- 8. Оказанные услуги (ПРИВЯЗАНЫ К ПОСТОЯЛЬЦУ, как просил преподаватель)
CREATE TABLE "Оказанные_услуги" (
    "ID_записи" SERIAL PRIMARY KEY,
    "ID_постояльца" INTEGER NOT NULL REFERENCES "Постояльцы"("ID_постояльца") ON DELETE CASCADE,
    "ID_услуги" INTEGER NOT NULL REFERENCES "Услуги"("ID_услуги") ON DELETE RESTRICT,
    "дата" DATE NOT NULL DEFAULT CURRENT_DATE,
    "количество" INTEGER NOT NULL DEFAULT 1 CHECK ("количество" > 0)
);

-- 9. Счета
CREATE TABLE "Счета" (
    "ID_счета" SERIAL PRIMARY KEY,
    "ID_проживания" INTEGER NOT NULL UNIQUE REFERENCES "Проживания"("ID_проживания") ON DELETE CASCADE,
    "ID_сотрудника" INTEGER REFERENCES "Сотрудники"("ID_сотрудника") ON DELETE SET NULL,
    "сумма" NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK ("сумма" >= 0),
    "дата_выдачи" DATE NOT NULL DEFAULT CURRENT_DATE,
    "статус_оплаты" VARCHAR(50) NOT NULL DEFAULT 'не оплачен' CHECK ("статус_оплаты" IN ('не оплачен', 'частично оплачен', 'оплачен'))
);

-- 10. Платежи
CREATE TABLE "Платежи" (
    "ID_платежа" SERIAL PRIMARY KEY,
    "ID_счета" INTEGER NOT NULL REFERENCES "Счета"("ID_счета") ON DELETE CASCADE,
    "сумма" NUMERIC(10, 2) NOT NULL CHECK ("сумма" > 0),
    "дата_платежа" DATE NOT NULL DEFAULT CURRENT_DATE,
    "способ_оплаты" VARCHAR(50) NOT NULL CHECK ("способ_оплаты" IN ('наличные', 'карта', 'перевод'))
);

-- 11. Табели учета
CREATE TABLE "Табели_учета" (
    "ID_записи" SERIAL PRIMARY KEY,
    "ID_сотрудника" INTEGER NOT NULL REFERENCES "Сотрудники"("ID_сотрудника") ON DELETE CASCADE,
    "месяц" VARCHAR(7) NOT NULL CHECK ("месяц" ~ '^\d{4}-\d{2}$'),
    "отработано_дней" INTEGER NOT NULL DEFAULT 0 CHECK ("отработано_дней" BETWEEN 0 AND 31),
    "отработано_часов" NUMERIC(5, 1) NOT NULL DEFAULT 0 CHECK ("отработано_часов" >= 0),
    UNIQUE ("ID_сотрудника", "месяц")
);

-- 12. Начисления зарплаты (УБРАНА ОШИБКА С UNIQUE!)
CREATE TABLE "Начисления_зарплаты" (
    "ID_начисления" SERIAL PRIMARY KEY,
    "ID_сотрудника" INTEGER NOT NULL REFERENCES "Сотрудники"("ID_сотрудника") ON DELETE CASCADE,
    "месяц" VARCHAR(7) NOT NULL CHECK ("месяц" ~ '^\d{4}-\d{2}$'),
    "премия" NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK ("премия" >= 0),
    "вычет" NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK ("вычет" >= 0),
    "итого" NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK ("итого" >= 0),
    UNIQUE ("ID_сотрудника", "месяц")
);

-- 13. Отзывы
CREATE TABLE "Отзывы" (
    "ID_отзыва" SERIAL PRIMARY KEY,
    "ID_постояльца" INTEGER NOT NULL UNIQUE REFERENCES "Постояльцы"("ID_постояльца") ON DELETE CASCADE,
    "номер_комнаты" VARCHAR(10) NOT NULL REFERENCES "Номера"("номер_комнаты") ON DELETE CASCADE,
    "текст_отзыва" TEXT,
    "дата" DATE NOT NULL DEFAULT CURRENT_DATE,
    "оценка" INTEGER NOT NULL CHECK ("оценка" BETWEEN 1 AND 5)
);

CREATE INDEX idx_bookings_room_dates ON "Брони"("номер_комнаты", "дата_заезда", "дата_выезда");
CREATE INDEX idx_stays_room_dates ON "Проживания"("номер_комнаты", "дата_заезда", "дата_выезда");