import psycopg2
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "eleon_secret_key"

DB_HOST = "localhost"
DB_NAME = "hotel_eleon"
DB_USER = "postgres"
DB_PASS = "123456"

def get_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, client_encoding='utf8')

# --- СТРАНИЦЫ ---
@app.route('/')
def dashboard():
    if 'role' not in session: session['role'] = 'admin'
    return render_template('dashboard.html', role=session['role'])

@app.route('/free_rooms')
def free_rooms(): return render_template('free_rooms.html', role=session['role'])

@app.route('/guests')
def guests_page():
    if session.get('role') not in ['admin', 'manager']: return render_template('access_denied.html', role=session.get('role')), 403
    return render_template('guests.html', role=session['role'])

@app.route('/bookings')
def bookings_page():
    if session.get('role') not in ['admin', 'manager']: return render_template('access_denied.html', role=session.get('role')), 403
    return render_template('bookings.html', role=session['role'])

@app.route('/stays')
def stays_page():
    if session.get('role') not in ['admin', 'manager']: return render_template('access_denied.html', role=session.get('role')), 403
    return render_template('stays.html', role=session['role'])

@app.route('/invoices')
def invoices_page():
    if session.get('role') not in ['admin', 'accountant']: return render_template('access_denied.html', role=session.get('role')), 403
    return render_template('invoices.html', role=session['role'])

@app.route('/reports')
def reports_page(): return render_template('reports.html', role=session['role'])

@app.route('/set_role/<role>')
def set_role(role):
    pwd = request.args.get('pwd')
    valid_passwords = {'admin': '1', 'manager': '2', 'accountant': '3'}
    if role in valid_passwords and pwd == valid_passwords[role]: session['role'] = role
    return redirect(request.referrer or url_for('dashboard'))

# --- API ---
@app.route('/api/analytics')
def api_analytics():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM "Постояльцы"'); g = cur.fetchone()[0]
        cur.execute('SELECT SUM("сумма") FROM "Счета" WHERE "статус_оплаты" = \'оплачен\''); r = cur.fetchone()[0] or 0
        cur.execute('SELECT COUNT(*) FROM "Проживания" WHERE "дата_выезда" IS NULL'); s = cur.fetchone()[0]
        return jsonify({"guests": g, "revenue": float(r), "active_stays": s})
    finally: cur.close(); conn.close()

@app.route('/api/guests', methods=['GET', 'POST'])
def api_guests():
    conn = get_connection(); cur = conn.cursor()
    if request.method == 'GET':
        try:
            cur.execute('SELECT "ID_постояльца", "фамилия", "имя", "отчество", "паспорт", "телефон" FROM "Постояльцы" ORDER BY "ID_постояльца"')
            columns = [d[0] for d in cur.description]; rows = cur.fetchall()
            return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
        finally: cur.close(); conn.close()
    if request.method == 'POST':
        data = request.json
        try:
            cur.execute('INSERT INTO "Постояльцы" ("фамилия", "имя", "отчество", "паспорт", "телефон") VALUES (%s, %s, %s, %s, %s)',
                (data['last_name'], data['first_name'], data.get('middle_name', ''), data['passport'], data.get('phone', '')))
            conn.commit(); return jsonify({"status": "Гость добавлен!"})
        except Exception as e:
            conn.rollback()
            if "unique" in str(e).lower(): return jsonify({"error": "Паспорт уже существует!"}), 400
            return jsonify({"error": str(e)}), 400
        finally: cur.close(); conn.close()

@app.route('/api/guests/<int:guest_id>', methods=['DELETE'])
def api_delete_guest(guest_id):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT 1 FROM "Брони" WHERE "ID_постояльца" = %s', (guest_id,))
        if cur.fetchone(): return jsonify({"error": "Нельзя удалить, есть история!"}), 400
        cur.execute('DELETE FROM "Постояльцы" WHERE "ID_постояльца" = %s', (guest_id,)); conn.commit()
        return jsonify({"status": "Гость удален."})
    except Exception as e: 
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

@app.route('/api/bookings', methods=['GET', 'POST'])
def api_bookings():
    conn = get_connection(); cur = conn.cursor()
    if request.method == 'GET':
        try:
            sql = '''SELECT b."ID_брони", g."фамилия" || ' ' || g."имя", b."номер_комнаты", b."дата_заезда", b."дата_выезда", b."статус", b."организация" FROM "Брони" b JOIN "Постояльцы" g ON b."ID_постояльца" = g."ID_постояльца" ORDER BY b."ID_брони" DESC'''
            cur.execute(sql); columns = [d[0] for d in cur.description]; rows = cur.fetchall()
            return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
        finally: cur.close(); conn.close()
    if request.method == 'POST':
        data = request.json
        try:
            cur.execute('INSERT INTO "Брони" ("ID_постояльца", "номер_комнаты", "ID_сотрудника", "дата_заезда", "дата_выезда", "статус", "организация") VALUES (%s, %s, 2, %s, %s, \'активна\', %s)',
                (data['guest_id'], data['room_number'], data['check_in'], data['check_out'], data.get('organization', '')))
            conn.commit(); return jsonify({"status": "Бронь оформлена!"})
        except Exception as e: 
            conn.rollback(); return jsonify({"error": str(e)}), 400
        finally: cur.close(); conn.close()

@app.route('/api/stays', methods=['GET', 'POST'])
def api_stays():
    conn = get_connection(); cur = conn.cursor()
    if request.method == 'GET':
        try:
            sql = '''SELECT s."ID_проживания", g."фамилия" || ' ' || g."имя", s."номер_комнаты", s."дата_заезда", r."цена" FROM "Проживания" s JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца" JOIN "Номера" r ON s."номер_комнаты" = r."номер_комнаты" WHERE s."дата_выезда" IS NULL'''
            cur.execute(sql); columns = [d[0] for d in cur.description]; rows = cur.fetchall()
            return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
        finally: cur.close(); conn.close()
    if request.method == 'POST':
        data = request.json
        try:
            cur.execute('INSERT INTO "Проживания" ("ID_постояльца", "номер_комнаты", "дата_заезда") VALUES (%s, %s, CURRENT_DATE)', (data['guest_id'], data['room_number']))
            cur.execute('UPDATE "Номера" SET "статус" = \'занят\' WHERE "номер_комнаты" = %s', (data['room_number'],))
            conn.commit(); return jsonify({"status": "Гость заселен!"})
        except Exception as e: 
            conn.rollback(); return jsonify({"error": str(e)}), 400
        finally: cur.close(); conn.close()

@app.route('/api/checkout/<int:stay_id>', methods=['POST'])
def api_checkout(stay_id):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT "номер_комнаты", "дата_заезда", "ID_постояльца" FROM "Проживания" WHERE "ID_проживания" = %s', (stay_id,))
        stay = cur.fetchone()
        room, check_in, guest_id = stay[0], stay[1], stay[2]
        
        cur.execute('SELECT CURRENT_DATE - %s::date', (check_in,)); days = max(1, cur.fetchone()[0])
        cur.execute('SELECT "цена" FROM "Номера" WHERE "номер_комнаты" = %s', (room,)); price = cur.fetchone()[0]
        
        # Считаем услуги ПО ПОСТОЯЛЬЦУ (как в новой схеме)
        cur.execute('SELECT COALESCE(SUM(ou."количество" * u."цена"), 0) FROM "Оказанные_услуги" ou JOIN "Услуги" u ON ou."ID_услуги" = u."ID_услуги" WHERE ou."ID_постояльца" = %s', (guest_id,))
        services_cost = cur.fetchone()[0]
        total = (days * price) + services_cost

        cur.execute('UPDATE "Проживания" SET "дата_выезда" = CURRENT_DATE WHERE "ID_проживания" = %s', (stay_id,))
        cur.execute('INSERT INTO "Счета" ("ID_проживания", "ID_сотрудника", "сумма", "статус_оплаты") VALUES (%s, 4, %s, \'не оплачен\')', (stay_id, total))
        cur.execute('UPDATE "Номера" SET "статус" = \'уборка\' WHERE "номер_комнаты" = %s', (room,))
        conn.commit(); return jsonify({"status": f"Выселен. Счет на {total} руб. создан!"})
    except Exception as e: 
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

@app.route('/api/select_data')
def api_select_data():
    conn = get_connection(); cur = conn.cursor()
    cur.execute('SELECT "ID_постояльца", "фамилия" || \' \' || "имя" FROM "Постояльцы" ORDER BY "фамилия"')
    guests = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    cur.execute('SELECT "номер_комнаты" FROM "Номера" WHERE "статус" = \'доступен\' ORDER BY "номер_комнаты"')
    rooms = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify({"guests": guests, "rooms": rooms})

@app.route('/api/free_rooms', methods=['POST'])
def api_free_rooms():
    data = request.json
    sql = '''SELECT r."номер_комнаты" AS "Номер", rc."название" AS "Категория", r."количество_мест" AS "Мест", r."цена" AS "Цена", r."описание"
    FROM "Номера" r JOIN "Категории_номеров" rc ON r."ID_категории" = rc."ID_категории"
    WHERE r."статус" != \'ремонт\'
      AND NOT EXISTS (SELECT 1 FROM "Проживания" s WHERE s."номер_комнаты" = r."номер_комнаты" AND %s::date >= s."дата_заезда" AND %s::date < COALESCE(s."дата_выезда", '9999-12-31'::date))
      AND NOT EXISTS (SELECT 1 FROM "Брони" b WHERE b."номер_комнаты" = r."номер_комнаты" AND b."статус" = \'активна\' AND %s::date >= b."дата_заезда" AND %s::date < b."дата_выезда")
      AND (%s = '' OR rc."название" = %s)
      AND (%s = '' OR r."количество_мест" = CAST(NULLIF(%s, '') AS integer))
    ORDER BY rc."название", r."номер_комнаты"'''
    try:
        conn = get_connection(); cur = conn.cursor()
        places = data.get('places', '')
        cur.execute(sql, (data['date'], data['date'], data['date'], data['date'], data['category'], data['category'], places, places))
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows], "status": f"Найдено: {len(rows)}"})
    except Exception as e: return jsonify({"error": str(e)}), 400
    finally:
        if 'conn' in locals(): cur.close(); conn.close()

@app.route('/api/invoices', methods=['GET'])
def api_invoices():
    conn = get_connection(); cur = conn.cursor()
    try:
        sql = '''SELECT i."ID_счета", g."фамилия" || ' ' || g."имя", s."номер_комнаты", i."сумма", i."дата_выдачи", i."статус_оплаты"
                 FROM "Счета" i JOIN "Проживания" st ON i."ID_проживания" = st."ID_проживания"
                 JOIN "Постояльцы" g ON st."ID_постояльца" = g."ID_постояльца"
                 JOIN "Номера" s ON st."номер_комнаты" = s."номер_комнаты" ORDER BY i."ID_счета" DESC'''
        cur.execute(sql); columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    except Exception as e: return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

@app.route('/api/invoices/<int:invoice_id>/pay', methods=['POST'])
def api_pay_invoice(invoice_id):
    data = request.json; method = data.get('method', 'карта')
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT "сумма", "статус_оплаты" FROM "Счета" WHERE "ID_счета" = %s', (invoice_id,))
        inv = cur.fetchone()
        if not inv or inv[1] == 'оплачен': return jsonify({"error": "Счет оплачен или не найден"}), 400
        cur.execute('INSERT INTO "Платежи" ("ID_счета", "сумма", "способ_оплаты") VALUES (%s, %s, %s)', (invoice_id, inv[0], method))
        cur.execute('UPDATE "Счета" SET "статус_оплаты" = \'оплачен\' WHERE "ID_счета" = %s', (invoice_id,))
        conn.commit(); return jsonify({"status": f"Счет на {inv[0]} руб. оплачен!"})
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

# --- ОТЧЕТЫ ---
@app.route('/api/reports/checkouts')
def api_report_checkouts():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT s."ID_проживания", g."фамилия", s."номер_комнаты", s."дата_выезда" FROM "Проживания" s JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца" WHERE s."дата_выезда" BETWEEN CURRENT_DATE AND CURRENT_DATE + 1')
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/reports/archive')
def api_report_archive():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT s."ID_проживания", g."фамилия", s."номер_комнаты", s."дата_заезда", s."дата_выезда" FROM "Проживания" s JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца" WHERE s."дата_выезда" >= CURRENT_DATE - INTERVAL \'1 year\' ORDER BY s."дата_выезда" DESC')
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/reports/search_booking')
def api_report_search_booking():
    query = request.args.get('q', '').strip()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT b."ID_брони", g."фамилия", b."организация", b."номер_комнаты", b."дата_заезда", b."дата_выезда", b."статус" FROM "Брони" b JOIN "Постояльцы" g ON b."ID_постояльца" = g."ID_постояльца" WHERE LOWER(g."фамилия") LIKE LOWER(%s) OR LOWER(b."организация") LIKE LOWER(%s)', (f"%{query}%", f"%{query}%"))
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/reports/room_info')
def api_report_room_info():
    room = request.args.get('room_number', '')
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT r."номер_комнаты", rc."название", r."количество_мест", r."цена", r."описание", r."статус", (SELECT g."фамилия" FROM "Проживания" s JOIN "Постояльцы" g ON s."ID_постояльца" = g."ID_постояльца" WHERE s."номер_комнаты" = r."номер_комнаты" AND s."дата_выезда" IS NULL LIMIT 1) FROM "Номера" r JOIN "Категории_номеров" rc ON r."ID_категории" = rc."ID_категории" WHERE r."номер_комнаты" = %s', (room,))
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/reports/reviews')
def api_report_reviews():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT r."ID_отзыва", g."фамилия", r."номер_комнаты", r."оценка", r."дата", r."текст_отзыва" FROM "Отзывы" r JOIN "Постояльцы" g ON r."ID_постояльца" = g."ID_постояльца" ORDER BY r."дата" DESC')
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/reports/salary')
def api_report_salary():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT e."фамилия", e."должность", sa."месяц", sa."премия", sa."вычет", sa."итого" FROM "Начисления_зарплаты" sa JOIN "Сотрудники" e ON sa."ID_сотрудника" = e."ID_сотрудника" ORDER BY sa."месяц" DESC')
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    finally: cur.close(); conn.close()

@app.route('/api/salary', methods=['POST'])
def api_add_salary():
    data = request.json; emp_id = data['employee_id']; month = data['month']
    bonus = float(data['bonus']); deduction = float(data['deduction'])
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute('SELECT "оклад" FROM "Сотрудники" WHERE "ID_сотрудника" = %s', (emp_id,)); salary = float(cur.fetchone()[0])
        cur.execute('SELECT "отработано_дней" FROM "Табели_учета" WHERE "ID_сотрудника" = %s AND "месяц" = %s', (emp_id, month))
        ts = cur.fetchone(); days = ts[0] if ts else 21
        total = (salary / 21.0) * days + bonus - deduction
        cur.execute('INSERT INTO "Начисления_зарплаты" ("ID_сотрудника", "месяц", "премия", "вычет", "итого") VALUES (%s, %s, %s, %s, %s)', (emp_id, month, bonus, deduction, total))
        conn.commit(); return jsonify({"status": f"Зарплата рассчитана! Итого: {total:.2f} руб."})
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

@app.route('/api/select_employees')
def api_select_employees():
    conn = get_connection(); cur = conn.cursor()
    cur.execute('SELECT "ID_сотрудника", "фамилия" || \' \' || "имя" FROM "Сотрудники"')
    emps = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close(); return jsonify({"employees": emps})

@app.route('/api/analytics/report/<int:report_id>')
def get_analytical_report(report_id):
    queries = {
        4: '''SELECT "фамилия" AS "Фамилия", "имя" AS "Имя", "должность" AS "Должность", "оклад" AS "Оклад" FROM "Сотрудники" WHERE "оклад" > (SELECT AVG("оклад") FROM "Сотрудники");''',
        5: '''SELECT u."название" AS "Услуга", SUM(ou."количество") AS "Кол-во", SUM(ou."количество" * u."цена") AS "Выручка" FROM "Услуги" u JOIN "Оказанные_услуги" ou ON u."ID_услуги" = ou."ID_услуги" GROUP BY u."название" ORDER BY "Выручка" DESC;''',
        6: '''SELECT TO_CHAR("дата_выдачи", 'YYYY-MM') AS "Месяц", ROUND(AVG("сумма"), 2) AS "Средний чек", SUM("сумма") AS "Выручка" FROM "Счета" WHERE "статус_оплаты" = 'оплачен' GROUP BY "Месяц" ORDER BY "Месяц";''',
        7: '''SELECT g."фамилия" AS "Фамилия", g."имя" AS "Имя", i."сумма" AS "Долг", i."дата_выдачи" AS "Дата счета" FROM "Постояльцы" g JOIN "Проживания" s ON g."ID_постояльца" = s."ID_постояльца" JOIN "Счета" i ON s."ID_проживания" = i."ID_проживания" WHERE i."статус_оплаты" = 'не оплачен';''',
        8: '''SELECT rc."название" AS "Категория", ROUND(AVG(s."дата_выезда" - s."дата_заезда"), 1) AS "Ср. длительность (дней)" FROM "Проживания" s JOIN "Номера" r ON s."номер_комнаты" = r."номер_комнаты" JOIN "Категории_номеров" rc ON r."ID_категории" = rc."ID_категории" WHERE s."дата_выезда" IS NOT NULL GROUP BY rc."название";''',
        9: '''SELECT "номер_комнаты" AS "Номер", ROUND(AVG("оценка"), 1) AS "Средний балл" FROM "Отзывы" GROUP BY "номер_комнаты" ORDER BY "Средний балл" DESC;''',
        10: '''SELECT "способ_оплаты" AS "Способ оплаты", COUNT(*) AS "Количество", SUM("сумма") AS "Сумма" FROM "Платежи" GROUP BY "способ_оплаты";'''
    }
    sql = queries.get(report_id)
    if not sql: return jsonify({"error": "Отчет не найден"}), 404
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(sql); columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    except Exception as e: return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

@app.route('/api/analytics/load_report')
def api_load_report():
    start = request.args.get('start'); end = request.args.get('end')
    conn = get_connection(); cur = conn.cursor()
    try:
        sql = '''SELECT ROUND((COUNT(s."ID_проживания")::numeric / NULLIF(((SELECT COUNT(*) FROM "Номера") * (%s::date - %s::date + 1)), 0)) * 100, 2) AS "Загрузка %" FROM "Проживания" s WHERE s."дата_заезда" >= %s::date AND s."дата_заезда" <= %s::date'''
        cur.execute(sql, (end, start, start, end))
        columns = [d[0] for d in cur.description]; rows = cur.fetchall()
        return jsonify({"columns": columns, "rows": [[str(v) if v is not None else "" for v in r] for r in rows]})
    except Exception as e: return jsonify({"error": str(e)}), 400
    finally: cur.close(); conn.close()

if __name__ == '__main__':
    app.run(debug=True)