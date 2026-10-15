import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).with_name("avtoservis.db")


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            plate_number TEXT NOT NULL UNIQUE,
            year INTEGER NOT NULL CHECK(year BETWEEN 1950 AND 2100),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL CHECK(price >= 0)
        );
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Новая', 'В работе', 'Завершена', 'Отменена')),
            description TEXT NOT NULL,
            FOREIGN KEY(car_id) REFERENCES cars(id),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS work_order_services (
            work_order_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
            PRIMARY KEY(work_order_id, service_id),
            FOREIGN KEY(work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
            FOREIGN KEY(service_id) REFERENCES services(id)
        );
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY(work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE
        );
        CREATE VIEW IF NOT EXISTS order_summary AS
        SELECT w.id AS order_id, c.brand, c.model, c.plate_number,
               cl.full_name AS client, e.full_name AS employee,
               w.created_at, w.status, w.description,
               COALESCE(SUM(s.price * ws.quantity), 0) AS total_price
        FROM work_orders w
        JOIN cars c ON c.id = w.car_id
        JOIN clients cl ON cl.id = c.client_id
        JOIN employees e ON e.id = w.employee_id
        LEFT JOIN work_order_services ws ON ws.work_order_id = w.id
        LEFT JOIN services s ON s.id = ws.service_id
        GROUP BY w.id;
        """)
        count = db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        if count == 0:
            db.executemany("INSERT INTO clients(full_name, phone) VALUES (?, ?)", [
                ("Иванов Иван Иванович", "+7-900-111-22-33"),
                ("Петрова Анна Сергеевна", "+7-900-222-33-44")
            ])
            db.executemany("INSERT INTO employees(full_name, position) VALUES (?, ?)", [
                ("Смирнов Алексей", "Автомеханик"),
                ("Кузнецов Павел", "Мастер-приёмщик")
            ])
            db.executemany("INSERT INTO cars(client_id, brand, model, plate_number, year) VALUES (?, ?, ?, ?, ?)", [
                (1, "Toyota", "Camry", "А123АА777", 2018),
                (2, "Kia", "Rio", "В456ВВ777", 2020)
            ])
            db.executemany("INSERT INTO services(name, price) VALUES (?, ?)", [
                ("Замена масла", 2500),
                ("Диагностика двигателя", 1800),
                ("Замена тормозных колодок", 4200),
                ("Шиномонтаж", 3000)
            ])
            db.execute("INSERT INTO work_orders(car_id, employee_id, created_at, status, description) VALUES (1, 1, ?, 'Новая', 'Плановое обслуживание')", (date.today().isoformat(),))
            db.execute("INSERT INTO work_order_services(work_order_id, service_id, quantity) VALUES (1, 1, 1)")


def read_int(prompt, minimum=1):
    while True:
        value = input(prompt).strip()
        try:
            number = int(value)
            if number < minimum:
                raise ValueError
            return number
        except ValueError:
            print(f"Введите целое число не меньше {minimum}.")


def read_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Поле не должно быть пустым.")


def show_rows(rows):
    if not rows:
        print("Записей нет.")
        return
    for row in rows:
        print(" | ".join(f"{key}: {row[key]}" for key in row.keys()))


def list_clients():
    with connect_db() as db:
        show_rows(db.execute("SELECT * FROM clients ORDER BY id").fetchall())


def add_client():
    name = read_text("ФИО клиента: ")
    phone = read_text("Телефон: ")
    try:
        with connect_db() as db:
            db.execute("INSERT INTO clients(full_name, phone) VALUES (?, ?)", (name, phone))
        print("Клиент добавлен.")
    except sqlite3.IntegrityError as error:
        print(f"Не удалось добавить клиента: {error}")


def list_cars():
    with connect_db() as db:
        rows = db.execute("""
            SELECT cars.id, clients.full_name AS client, cars.brand, cars.model,
                   cars.plate_number, cars.year
            FROM cars JOIN clients ON clients.id = cars.client_id ORDER BY cars.id
        """).fetchall()
        show_rows(rows)


def add_car():
    list_clients()
    client_id = read_int("ID клиента: ")
    brand = read_text("Марка автомобиля: ")
    model = read_text("Модель: ")
    plate = read_text("Госномер: ")
    year = read_int("Год выпуска: ", 1950)
    if year > 2100:
        print("Некорректный год выпуска.")
        return
    try:
        with connect_db() as db:
            db.execute("INSERT INTO cars(client_id, brand, model, plate_number, year) VALUES (?, ?, ?, ?, ?)",
                       (client_id, brand, model, plate, year))
        print("Автомобиль добавлен.")
    except sqlite3.IntegrityError as error:
        print(f"Не удалось добавить автомобиль: {error}")


def list_services():
    with connect_db() as db:
        show_rows(db.execute("SELECT * FROM services ORDER BY id").fetchall())


def add_service():
    name = read_text("Название услуги: ")
    while True:
        try:
            price = float(input("Цена услуги: ").strip().replace(",", "."))
            if price < 0:
                raise ValueError
            break
        except ValueError:
            print("Введите число не меньше нуля.")
    try:
        with connect_db() as db:
            db.execute("INSERT INTO services(name, price) VALUES (?, ?)", (name, price))
        print("Услуга добавлена.")
    except sqlite3.IntegrityError as error:
        print(f"Не удалось добавить услугу: {error}")


def list_employees():
    with connect_db() as db:
        show_rows(db.execute("SELECT * FROM employees ORDER BY id").fetchall())


def add_order():
    list_cars()
    car_id = read_int("ID автомобиля: ")
    list_employees()
    employee_id = read_int("ID сотрудника: ")
    description = read_text("Описание неисправности или работ: ")
    try:
        with connect_db() as db:
            cursor = db.execute("""INSERT INTO work_orders(car_id, employee_id, created_at, status, description)
                                  VALUES (?, ?, ?, 'Новая', ?)""",
                                (car_id, employee_id, date.today().isoformat(), description))
            order_id = cursor.lastrowid
            print("Доступные услуги:")
            show_rows(db.execute("SELECT * FROM services ORDER BY id").fetchall())
            raw_service = input("Введите ID услуги или нажмите Enter, чтобы пропустить: ").strip()
            if raw_service:
                service_id = int(raw_service)
                quantity = read_int("Количество: ")
                db.execute("INSERT INTO work_order_services(work_order_id, service_id, quantity) VALUES (?, ?, ?)",
                           (order_id, service_id, quantity))
        print(f"Заказ №{order_id} создан.")
    except (sqlite3.IntegrityError, ValueError) as error:
        print(f"Не удалось создать заказ: {error}")


def list_orders():
    with connect_db() as db:
        show_rows(db.execute("SELECT * FROM order_summary ORDER BY order_id DESC").fetchall())


def change_order_status():
    list_orders()
    order_id = read_int("ID заказа: ")
    statuses = ["Новая", "В работе", "Завершена", "Отменена"]
    print("Статусы: " + ", ".join(statuses))
    status = read_text("Новый статус: ")
    if status not in statuses:
        print("Такого статуса нет.")
        return
    with connect_db() as db:
        row = db.execute("SELECT status FROM work_orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            print("Заказ не найден.")
            return
        db.execute("UPDATE work_orders SET status = ? WHERE id = ?", (status, order_id))
        db.execute("INSERT INTO status_history(work_order_id, old_status, new_status, changed_at) VALUES (?, ?, ?, ?)",
                   (order_id, row["status"], status, date.today().isoformat()))
    print("Статус заказа изменён.")


def delete_order():
    list_orders()
    order_id = read_int("ID заказа для удаления: ")
    with connect_db() as db:
        cursor = db.execute("DELETE FROM work_orders WHERE id = ?", (order_id,))
        if cursor.rowcount:
            print("Заказ удалён.")
        else:
            print("Заказ не найден.")


def search_orders():
    query = read_text("Введите госномер, марку, модель или ФИО клиента: ")
    pattern = f"%{query}%"
    with connect_db() as db:
        rows = db.execute("""
            SELECT * FROM order_summary
            WHERE plate_number LIKE ? OR brand LIKE ? OR model LIKE ? OR client LIKE ?
            ORDER BY order_id DESC
        """, (pattern, pattern, pattern, pattern)).fetchall()
        show_rows(rows)


def show_statistics():
    with connect_db() as db:
        print("Количество клиентов:", db.execute("SELECT COUNT(*) FROM clients").fetchone()[0])
        print("Количество автомобилей:", db.execute("SELECT COUNT(*) FROM cars").fetchone()[0])
        print("Количество заказов:", db.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0])
        print("Завершённых заказов:", db.execute("SELECT COUNT(*) FROM work_orders WHERE status = 'Завершена'").fetchone()[0])
        print("Общая стоимость услуг по заказам:", db.execute("SELECT COALESCE(SUM(total_price), 0) FROM order_summary").fetchone()[0], "руб.")
        print("Заказы по статусам:")
        show_rows(db.execute("SELECT status, COUNT(*) AS count FROM work_orders GROUP BY status ORDER BY status").fetchall())


def show_history():
    with connect_db() as db:
        show_rows(db.execute("""
            SELECT status_history.id, status_history.work_order_id, status_history.old_status,
                   status_history.new_status, status_history.changed_at
            FROM status_history ORDER BY status_history.id DESC
        """).fetchall())


def menu():
    actions = {
        "1": ("Показать клиентов", list_clients),
        "2": ("Добавить клиента", add_client),
        "3": ("Показать автомобили", list_cars),
        "4": ("Добавить автомобиль", add_car),
        "5": ("Показать услуги", list_services),
        "6": ("Добавить услугу", add_service),
        "7": ("Показать сотрудников", list_employees),
        "8": ("Создать заказ", add_order),
        "9": ("Показать заказы", list_orders),
        "10": ("Изменить статус заказа", change_order_status),
        "11": ("Удалить заказ", delete_order),
        "12": ("Поиск заказов", search_orders),
        "13": ("Статистика", show_statistics),
        "14": ("История статусов", show_history)
    }
    while True:
        print("\n=== АВТОСЕРВИС ===")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()
        if choice == "0":
            print("Работа программы завершена.")
            break
        action = actions.get(choice)
        if action:
            try:
                action[1]()
            except sqlite3.Error as error:
                print(f"Ошибка базы данных: {error}")
        else:
            print("Нет такого пункта меню.")


if __name__ == "__main__":
    create_database()
    menu()
