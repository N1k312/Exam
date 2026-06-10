# -*- coding: utf-8 -*-


import os
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, FancyArrowPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

BROWN = "#7B3F00"
GOLD = "#C8862B"
GREEN = "#4E843D"
LIGHT = "#F3E9DC"


def new_canvas(w=14, h=9, title=""):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    if title:
        ax.text(50, 97, title, ha="center", va="top",
                fontsize=16, fontweight="bold", color=BROWN)
    return fig, ax


def box(ax, x, y, w, h, text, fc=LIGHT, ec=BROWN, fontsize=9, bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=2",
                       fc=fc, ec=ec, lw=1.5)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight="bold" if bold else "normal",
            wrap=True, color="#222222")


def rect(ax, x, y, w, h, fc="white", ec="#555555", lw=1.2):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw))


def ellipse(ax, x, y, w, h, text, fc="white", ec=GOLD, fontsize=8):
    e = Ellipse((x, y), w, h, fc=fc, ec=ec, lw=1.5)
    ax.add_patch(e)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, color="#222222")


def actor(ax, x, y, label):
    """Простая фигурка 'человечек' (актор UML)."""
    ax.add_patch(plt.Circle((x, y + 6), 1.6, fc="white", ec=BROWN, lw=1.5))
    ax.plot([x, x], [y + 4.4, y - 1], color=BROWN, lw=1.5)          # туловище
    ax.plot([x - 2.5, x + 2.5], [y + 2.5, y + 2.5], color=BROWN, lw=1.5)  # руки
    ax.plot([x, x - 2], [y - 1, y - 5], color=BROWN, lw=1.5)        # нога
    ax.plot([x, x + 2], [y - 1, y - 5], color=BROWN, lw=1.5)        # нога
    ax.text(x, y - 7.5, label, ha="center", va="top", fontsize=9,
            fontweight="bold", color=BROWN)


def line(ax, x1, y1, x2, y2, style="-", color="#555555", arrow=False):
    if arrow:
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                     arrowstyle="-|>", mutation_scale=12,
                     color=color, lw=1.2, linestyle=style))
    else:
        ax.plot([x1, x2], [y1, y2], linestyle=style, color=color, lw=1.2)


# 2.1 Session2_UseCaseDiagram.pdf

def task_2_1_use_case(out_dir):
    print("[2.1] Use Case Diagram ...")
    fig, ax = new_canvas(title="Session 2.1 — Use Case Diagram (Belle Croissant Lyonnais)")

    # граница системы
    rect(ax, 30, 8, 40, 80, fc="#FBF6EF", ec=BROWN, lw=2)
    ax.text(50, 86, "Bakery Management System", ha="center", va="center",
            fontsize=11, fontweight="bold", color=BROWN)

    # акторы
    actor(ax, 12, 70, "Staff\n(Персонал)")
    actor(ax, 12, 35, "Manager\n(Менеджер)")
    actor(ax, 88, 60, "Customer\n(Заказчик)")
    actor(ax, 88, 22, "Payment\nSystem")

    # варианты использования (эллипсы)
    use_cases_left = [
        (50, 78, "Управление\nзаказами"),
        (50, 68, "Управление\nзапасами"),
        (50, 58, "Управление\nзаказчиками"),
        (50, 48, "Просмотр\nотчётов"),
        (50, 38, "Управление\nакциями"),
    ]
    use_cases_right = [
        (50, 30, "Просмотр\nпродуктов"),
        (50, 21, "Оформление\nзаказа онлайн"),
        (50, 12, "Оплата\nзаказа"),
    ]
    coords = {}
    for x, y, t in use_cases_left + use_cases_right:
        ellipse(ax, x, y, 18, 7, t)
        coords[t] = (x, y)

    # связи акторов с вариантами использования
    staff_uc = ["Управление\nзаказами", "Управление\nзапасами", "Управление\nзаказчиками"]
    for t in staff_uc:
        line(ax, 16, 68, coords[t][0] - 9, coords[t][1])
    mgr_uc = ["Просмотр\nотчётов", "Управление\nакциями"]
    for t in mgr_uc:
        line(ax, 16, 36, coords[t][0] - 9, coords[t][1])
    cust_uc = ["Просмотр\nпродуктов", "Оформление\nзаказа онлайн", "Оплата\nзаказа"]
    for t in cust_uc:
        line(ax, 84, 58, coords[t][0] + 9, coords[t][1])
    # внешняя система
    line(ax, 84, 22, coords["Оплата\nзаказа"][0] + 9, coords["Оплата\nзаказа"][1])

    # <<include>> Оформление заказа -> Оплата
    line(ax, coords["Оформление\nзаказа онлайн"][0],
         coords["Оформление\nзаказа онлайн"][1] - 3,
         coords["Оплата\nзаказа"][0], coords["Оплата\nзаказа"][1] + 3,
         style="--", color=GREEN, arrow=True)
    ax.text(58, 15, "<<include>>", fontsize=7, color=GREEN, rotation=0)

    path = os.path.join(out_dir, "Session2_UseCaseDiagram.pdf")
    with PdfPages(path) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    print("    -> " + path)


# 2.2 Session2_ERD.pdf

def task_2_2_erd(out_dir):
    print("[2.2] ERD ...")
    fig, ax = new_canvas(title="Session 2.2 — Entity-Relationship Diagram (3NF)")

    def entity(ax, x, y, name, attrs):
        w, h = 22, 4 + len(attrs) * 3.2
        rect(ax, x, y - h, w, h, fc="white", ec=BROWN, lw=1.8)
        rect(ax, x, y - 4, w, 4, fc=BROWN, ec=BROWN)
        ax.text(x + w / 2, y - 2, name, ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        for i, a in enumerate(attrs):
            ax.text(x + 1.5, y - 6.2 - i * 3.2, a, ha="left", va="center",
                    fontsize=7, color="#222222")
        return (x, y, w, h)

    cat = entity(ax, 6, 88, "Category",
                 ["PK category_id", "category_name"])
    prod = entity(ax, 6, 64, "Product",
                  ["PK product_id", "FK category_id", "name", "price", "cost",
                   "seasonal", "active", "release_date"])
    promo = entity(ax, 72, 88, "Promotion",
                   ["PK promotion_id", "description", "discount",
                    "start_date", "end_date"])
    cust = entity(ax, 72, 60, "Customer",
                  ["PK customer_id", "name", "age", "gender", "zip_code",
                   "email", "phone_number", "membership_status",
                   "join_date", "churn_status"])
    order = entity(ax, 39, 64, "Order",
                   ["PK transaction_id", "FK customer_id",
                    "FK promotion_id", "order_date"])
    item = entity(ax, 39, 30, "OrderItem",
                  ["PK,FK transaction_id", "PK,FK product_id",
                   "quantity", "price"])

    # связи (crow's foot — упрощённо линиями с подписями кардинальностей)
    def rel(a, b, label):
        ax1 = a[0] + a[2] / 2
        ay1 = a[1] - a[3] / 2
        bx1 = b[0] + b[2] / 2
        by1 = b[1] - b[3] / 2
        line(ax, ax1, ay1, bx1, by1, color=GOLD)
        ax.text((ax1 + bx1) / 2, (ay1 + by1) / 2 + 1, label,
                fontsize=7, color=GREEN, ha="center")

    rel(cat, prod, "1 : N")
    rel(cust, order, "1 : N")
    rel(promo, order, "0..1 : N")
    rel(order, item, "1 : N")
    rel(prod, item, "1 : N")

    ax.text(50, 6,
            "Связь M:N между Order и Product разрешена через OrderItem. "
            "Category вынесена отдельной сущностью (3NF).",
            ha="center", fontsize=8, color="#555555")

    path = os.path.join(out_dir, "Session2_ERD.pdf")
    with PdfPages(path) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    print("    -> " + path)



# 2.3 Session2_Wireframes_Staff.pdf
def _wire_header(ax, title):
    rect(ax, 4, 84, 92, 7, fc=BROWN, ec=BROWN)
    ax.text(7, 87.5, "Belle Croissant Lyonnais — Staff", color="white",
            fontsize=10, fontweight="bold", va="center")
    ax.text(93, 87.5, title, color="white", fontsize=9, va="center", ha="right")
    # левое меню
    rect(ax, 4, 10, 16, 72, fc="#EFE6D8", ec="#999999")
    for i, m in enumerate(["Dashboard", "Orders", "Inventory", "Customers", "Reports"]):
        ax.text(12, 78 - i * 6, m, fontsize=8, ha="center", color=BROWN)


def task_2_3_wireframes(out_dir):
    print("[2.3] Wireframes (Staff) ...")
    path = os.path.join(out_dir, "Session2_Wireframes_Staff.pdf")
    with PdfPages(path) as pdf:

        #Экран 1: Dashboard
        fig, ax = new_canvas(title="Session 2.3 — Wireframe: Dashboard")
        _wire_header(ax, "Dashboard")
        for i, kpi in enumerate(["Выручка\nза месяц", "Заказы\nсегодня",
                                 "Низкий\nзапас", "Новые\nзаказчики"]):
            box(ax, 24 + i * 18, 74, 15, 10, kpi, fc="white", ec=GOLD, fontsize=8)
        rect(ax, 24, 40, 33, 28, fc="white"); ax.text(40, 66, "График продаж", fontsize=8, ha="center")
        rect(ax, 60, 40, 33, 28, fc="white"); ax.text(76, 66, "Топ продуктов", fontsize=8, ha="center")
        rect(ax, 24, 12, 69, 24, fc="white"); ax.text(58, 34, "Последние заказы (таблица)", fontsize=8, ha="center")
        pdf.savefig(fig); plt.close(fig)

        #Экран 2: Order Management
        fig, ax = new_canvas(title="Session 2.3 — Wireframe: Order Management")
        _wire_header(ax, "Orders")
        box(ax, 24, 78, 18, 7, "+ Новый заказ", fc=GREEN, ec=GREEN, fontsize=8, bold=True)
        rect(ax, 45, 78, 30, 7, fc="white"); ax.text(60, 81.5, "Поиск / фильтр", fontsize=8, ha="center")
        rect(ax, 24, 14, 69, 60, fc="white")
        for i in range(6):
            ax.plot([24, 93], [70 - i * 9, 70 - i * 9], color="#cccccc", lw=0.8)
        ax.text(58, 72, "Список заказов: №, заказчик, дата, статус, сумма, [Изменить]",
                fontsize=8, ha="center")
        pdf.savefig(fig); plt.close(fig)

        #Экран 3: Inventory Management
        fig, ax = new_canvas(title="Session 2.3 — Wireframe: Inventory Management")
        _wire_header(ax, "Inventory")
        rect(ax, 24, 60, 69, 24, fc="white")
        ax.text(58, 82, "Уровни запасов по ингредиентам (таблица + индикаторы)",
                fontsize=8, ha="center")
        rect(ax, 24, 32, 33, 24, fc="white"); ax.text(40, 54, "График расхода", fontsize=8, ha="center")
        rect(ax, 60, 32, 33, 24, fc="white"); ax.text(76, 54, "Отчёт по запасам", fontsize=8, ha="center")
        box(ax, 24, 14, 22, 8, "Обновить запас", fc=GOLD, ec=GOLD, fontsize=8, bold=True)
        pdf.savefig(fig); plt.close(fig)

        #Экран 4: Customer Management 
        fig, ax = new_canvas(title="Session 2.3 — Wireframe: Customer Management")
        _wire_header(ax, "Customers")
        rect(ax, 24, 14, 30, 70, fc="white"); ax.text(39, 80, "Список\nзаказчиков", fontsize=8, ha="center")
        rect(ax, 57, 50, 36, 34, fc="white"); ax.text(75, 80, "Профиль заказчика", fontsize=8, ha="center")
        ax.text(59, 72, "Имя, контакты, статус лояльности", fontsize=7, ha="left")
        rect(ax, 57, 14, 36, 32, fc="white"); ax.text(75, 42, "История покупок", fontsize=8, ha="center")
        pdf.savefig(fig); plt.close(fig)

    print("    -> " + path)


# 2.4 Session2_CustomerAPI_Design.txt

API_DESIGN = """\

SESSION 2.4 — RESTful API DESIGN
Belle Croissant Lyonnais — Customer Management Endpoint



RESOURCE
    /customers

Конечная точка управления заказчиками. Поддерживает операции CRUD
(создание, чтение, обновление, удаление) в соответствии с принципами REST.


МОДЕЛЬ ДАННЫХ (Customer)

    customer_id        integer   (генерируется сервером, только для чтения)
    name               string    обязательное, 1..100 символов
    age                integer   необязательное, 0..120
    gender             string    необязательное, одно из: "M", "F"
    zip_code           string    необязательное
    email              string    обязательное, валидный e-mail, уникальный
    phone_number       string    необязательное, формат +<цифры>
    membership_status  string    необязательное, одно из: "Basic","Silver","Gold"
                                  (по умолчанию "Basic")
    join_date          string    дата ISO 8601 (YYYY-MM-DD), только для чтения
    churn_status       integer   0 или 1 (по умолчанию 0)

1) GET /customers
   Описание: получить список заказчиков (с пагинацией и фильтрацией).
   Параметры запроса (query, необязательные):
       page             integer  >= 1            (по умолчанию 1)
       limit            integer  1..100          (по умолчанию 20)
       membership       string   Basic|Silver|Gold
       churn            integer  0|1
   Ответ 200 OK (application/json):
   {
       "page": 1,
       "limit": 20,
       "total": 350,
       "data": [
           {
               "customer_id": 101,
               "name": "Marie Dubois",
               "age": 34,
               "gender": "F",
               "email": "marie@example.com",
               "phone_number": "+33123456789",
               "membership_status": "Gold",
               "join_date": "2023-02-14",
               "churn_status": 0
           }
       ]
   }

2) GET /customers/{customer_id}
   Описание: получить одного заказчика по идентификатору.
   Параметр пути:
       customer_id      integer  обязательный
   Ответ 200 OK:
   {
       "customer_id": 101,
       "name": "Marie Dubois",
       "age": 34,
       "gender": "F",
       "email": "marie@example.com",
       "phone_number": "+33123456789",
       "membership_status": "Gold",
       "join_date": "2023-02-14",
       "churn_status": 0
   }
   Ошибка 404 Not Found:
   { "error": "Customer not found", "customer_id": 101 }

3) POST /customers
   Описание: создать нового заказчика.
   Тело запроса (application/json):
   {
       "name": "Jean Martin",          // обязательно
       "email": "jean@example.com",    // обязательно, уникально
       "age": 28,                      // необязательно
       "gender": "M",                  // необязательно: M|F
       "phone_number": "+33611223344", // необязательно
       "membership_status": "Basic"    // необязательно
   }
   Ответ 201 Created:
   {
       "customer_id": 351,
       "name": "Jean Martin",
       "email": "jean@example.com",
       "membership_status": "Basic",
       "join_date": "2025-06-04",
       "churn_status": 0
   }
   Ошибки:
       400 Bad Request   — нарушены правила валидации
                           { "error": "Validation failed",
                             "fields": { "email": "invalid format" } }
       409 Conflict      — e-mail уже существует
                           { "error": "Email already exists" }


4) PUT /customers/{customer_id}
   Описание: обновить данные заказчика (полное обновление изменяемых полей).
   Параметр пути: customer_id (integer, обязательный)
   Тело запроса: те же поля, что и в POST (customer_id, join_date неизменяемы).
   Ответ 200 OK: обновлённый объект Customer.
   Ошибки: 400 (валидация), 404 (не найден).


5) DELETE /customers/{customer_id}
   Описание: удалить заказчика.
   Параметр пути: customer_id (integer, обязательный)
   Ответ 204 No Content (тело пустое).
   Ошибка 404 Not Found: { "error": "Customer not found" }


ОБЩИЕ СОГЛАШЕНИЯ

- Формат данных: JSON (Content-Type: application/json).
- Коды состояния HTTP используются по назначению:
      200 OK, 201 Created, 204 No Content,
      400 Bad Request, 404 Not Found, 409 Conflict.
- Идентификатор customer_id и join_date назначаются сервером и доступны
  только для чтения
- Все даты — в формате ISO 8601 (YYYY-MM-DD).
- Список поддерживает пагинацию (page, limit) и фильтрацию.
"""


def task_2_4_api(out_dir):
    print("[2.4] API Design ...")
    path = os.path.join(out_dir, "Session2_CustomerAPI_Design.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(API_DESIGN)
    print("    -> " + path)


def main():
    parser = argparse.ArgumentParser(description="Belle Croissant — Session 2 deliverables")
    parser.add_argument("--output", default="./output", help="папка для результатов")
    args = parser.parse_args()

    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    
    print("BELLE CROISSANT LYONNAIS — SESSION 2 (ПРОЕКТИРОВАНИЕ)")
    print("Выход: {}".format(os.path.abspath(out_dir)))
    

    task_2_1_use_case(out_dir)
    task_2_2_erd(out_dir)
    task_2_3_wireframes(out_dir)
    task_2_4_api(out_dir)

    
    print("ГОТОВО. Файлы Session 2 — в папке: {}".format(os.path.abspath(out_dir)))
    


if __name__ == "__main__":
    main()
