# -*- coding: utf-8 -*-
"""
Belle Croissant Lyonnais — ДЕМОЭКЗАМЕН (Session 1, анализ данных)
=================================================================
Готовый скрипт под macOS и Python 3.9.

Выполняет ВСЕ задания критерия оценивания (1.1 – 1.10) и создаёт файлы-результаты:

  1.1  Session1_DataExploration.txt
  1.2  customers_cleaned.csv, sales_transactions_cleaned.csv
  1.3  Session1_SalesTrends.pdf
  1.4  Session1_ProductPerformance.pdf
  1.5  Session1_CustomerAnalysis.pdf
  1.6  Session1_SalesForecast.csv               (ARIMA, 30 дней)
  1.7  Session5_Segmentation_and_Recommendations.csv  (K-Means + рекомендации)
  1.8  Session5_Product_Performance.csv, Session5_Price_Analysis.csv (PED)
  1.9  Session1_CLTV.csv
  1.10 Session1_Churn_Analysis.csv

ЗАПУСК
------
1) Положите рядом со скриптом три файла:
       sales_transactions.csv
       products.csv
       customers.csv
2) Установите зависимости (один раз):
       pip3 install -r requirements.txt
   или вручную:
       pip3 install pandas numpy matplotlib statsmodels scikit-learn
3) Запустите:
       python3 belle_croissant_analysis.py

Проверить работу скрипта БЕЗ реальных данных (генерируется демо-набор):
       python3 belle_croissant_analysis.py --demo

Указать свои папки:
       python3 belle_croissant_analysis.py --input ./data --output ./output
"""

import os
import sys
import re
import argparse
import warnings

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")  # без графического окна — нужно для серверов и для надёжной записи в PDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

warnings.filterwarnings("ignore")

# Кириллица в графиках
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


# =============================================================================
# НАСТРОЙКИ
# =============================================================================
# Имена входных файлов
FILE_SALES = "sales_transactions.csv"
FILE_PRODUCTS = "products.csv"
FILE_CUSTOMERS = "customers.csv"

# Кандидаты имён столбцов (скрипт сам подберёт подходящий — регистр не важен).
# Если у вас столбцы названы иначе — просто допишите своё имя в нужный список.
COLUMN_CANDIDATES = {
    # sales_transactions
    "transaction_id": ["transaction_id", "trans_id", "id", "txn_id", "transactionid"],
    "customer_id":    ["customer_id", "cust_id", "client_id", "customerid", "custid"],
    "product_id":     ["product_id", "prod_id", "item_id", "productid", "prodid"],
    "date":           ["date", "transaction_date", "datetime", "order_date",
                       "purchase_date", "sale_date", "trans_date", "timestamp"],
    "quantity":       ["quantity", "qty", "amount", "count", "units", "units_sold"],
    "price":          ["price", "unit_price", "sale_price", "sales_price", "selling_price"],
    "promotion_id":   ["promotion_id", "promo_id", "promotion", "promotionid"],
    # products
    "name":           ["name", "product_name", "title", "productname"],
    "category":       ["category", "product_category", "type", "product_type"],
    "cost":           ["cost", "unit_cost", "production_cost", "cost_price", "costprice"],
    "product_date":   ["launch_date", "release_date", "date_released", "launch_dt",
                       "release", "launchdate", "releasedate", "introduced_date"],
    # customers
    "age":            ["age", "customer_age"],
    "gender":         ["gender", "sex"],
    "phone_number":   ["phone_number", "phone", "telephone", "mobile", "phonenumber"],
    "loyalty":        ["membership_status", "loyalty", "loyalty_tier", "member_status",
                       "membership", "loyalty_level", "tier", "loyalty_status"],
    "churn":          ["churn_status", "churn", "is_churned", "churned", "churnstatus"],
}

# Подсказки для НЕЧЁТКОГО поиска (если точное имя не найдено — ищем по части слова).
FUZZY_HINTS = {
    "transaction_id": ["transaction", "txn", "trans"],
    "customer_id":    ["customer", "client", "cust"],
    "product_id":     ["product", "item", "prod"],
    "date":           ["date", "time"],
    "quantity":       ["quant", "qty", "units"],
    "price":          ["price"],
    "promotion_id":   ["promo"],
    "name":           ["name", "title"],
    "category":       ["categor", "type"],
    "cost":           ["cost"],
    "product_date":   ["launch", "release", "introduc"],
    "age":            ["age"],
    "gender":         ["gender", "sex"],
    "phone_number":   ["phone", "mobile", "tel"],
    "loyalty":        ["loyal", "member", "tier"],
    "churn":          ["churn"],
}

# Ожидаемые значения категориальных столбцов (для задачи 1.1 — поиск аномалий)
EXPECTED_GENDER = {"M", "F"}
EXPECTED_LOYALTY = {"Basic", "Silver", "Gold"}

# Разумный диапазон дат (для поиска "недопустимых дат" в 1.1)
DATE_MIN = pd.Timestamp("2000-01-01")
DATE_MAX = pd.Timestamp("2035-12-31")

RNG_SEED = 42  # фиксированный seed -> воспроизводимость (требование экзамена)


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================
def log(msg):
    print(msg, flush=True)


def resolve_columns(df, needed):
    """Сопоставляет логические имена столбцов с реальными именами в df.
    Сначала по точному совпадению, затем по нечёткому (по части слова)."""
    lower = {c.lower().strip(): c for c in df.columns}
    used = set()
    mapping = {}
    # 1) точное совпадение по списку кандидатов
    for key in needed:
        found = None
        for cand in COLUMN_CANDIDATES.get(key, [key]):
            real = lower.get(cand.lower())
            if real is not None and real not in used:
                found = real
                break
        if found is not None:
            used.add(found)
        mapping[key] = found
    # 2) нечёткое совпадение для всего, что не нашлось
    for key in needed:
        if mapping.get(key) is not None:
            continue
        id_key = key.endswith("_id")
        for hint in FUZZY_HINTS.get(key, []):
            cands = [orig for low, orig in lower.items()
                     if hint in low and orig not in used]
            # для столбцов-идентификаторов имя обязано содержать "id"
            if id_key:
                cands = [c for c in cands if "id" in c.lower()]
            if cands:
                # самое короткое имя обычно самое точное
                best = sorted(cands, key=len)[0]
                mapping[key] = best
                used.add(best)
                break
    return mapping


def need(mapping, key, df_name):
    """Возвращает имя столбца или останавливает скрипт с понятной ошибкой."""
    col = mapping.get(key)
    if col is None:
        raise KeyError(
            "В файле '{}' не найден столбец для '{}'. "
            "Добавьте его имя в COLUMN_CANDIDATES['{}'].".format(df_name, key, key)
        )
    return col


def get(mapping, key):
    """Мягкий доступ: вернёт имя столбца или None, без ошибки."""
    return mapping.get(key)


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def parse_dates(series):
    return pd.to_datetime(series, errors="coerce")


# =============================================================================
# ЗАГРУЗКА ДАННЫХ
# =============================================================================
def load_data(input_dir):
    paths = {
        "sales": os.path.join(input_dir, FILE_SALES),
        "products": os.path.join(input_dir, FILE_PRODUCTS),
        "customers": os.path.join(input_dir, FILE_CUSTOMERS),
    }
    missing = [p for p in paths.values() if not os.path.isfile(p)]
    if missing:
        log("ОШИБКА: не найдены входные файлы:")
        for m in missing:
            log("   " + m)
        log("\nПоложите CSV рядом со скриптом или укажите --input <папка>,")
        log("либо запустите с --demo для проверки на сгенерированных данных.")
        sys.exit(1)

    sales = pd.read_csv(paths["sales"])
    products = pd.read_csv(paths["products"])
    customers = pd.read_csv(paths["customers"])
    log("Файлы загружены: sales={}, products={}, customers={}".format(
        sales.shape, products.shape, customers.shape))
    return sales, products, customers


# =============================================================================
# 1.1  ЗАГРУЗКА И ИЗУЧЕНИЕ ДАННЫХ  ->  Session1_DataExploration.txt
# =============================================================================
def task_1_1_exploration(sales, products, customers, out_dir):
    log("[1.1] Изучение данных ...")
    lines = []
    w = lines.append

    sm = resolve_columns(sales, ["customer_id", "product_id", "date", "quantity", "price"])
    pm = resolve_columns(products, ["product_id", "category"])
    cm = resolve_columns(customers, ["customer_id", "gender", "loyalty"])

    valid_products = set(products[need(pm, "product_id", "products")].astype(str))
    valid_customers = set(customers[need(cm, "customer_id", "customers")].astype(str))

    datasets = [("sales_transactions.csv", sales),
                ("products.csv", products),
                ("customers.csv", customers)]

    w("=" * 70)
    w("SESSION 1 — DATA EXPLORATION (Изучение данных)")
    w("=" * 70)

    for fname, df in datasets:
        w("\n" + "-" * 70)
        w("ФАЙЛ: {}   (строк: {}, столбцов: {})".format(fname, len(df), df.shape[1]))
        w("-" * 70)

        w("\nПервые 5 строк:")
        w(df.head().to_string())

        w("\nТипы данных по столбцам:")
        for col in df.columns:
            w("   {:<25} {}".format(col, str(df[col].dtype)))

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        non_num = [c for c in df.columns if c not in num_cols]
        w("\nНечисловые столбцы: " + (", ".join(non_num) if non_num else "нет"))

        w("\nПропущенные значения по столбцам:")
        miss = df.isnull().sum()
        for col in df.columns:
            w("   {:<25} {}".format(col, int(miss[col])))

        # Проблемы с форматированием: лишние пробелы в текстовых полях
        fmt_issues = 0
        for col in non_num:
            s = df[col].astype(str)
            fmt_issues += int((s != s.str.strip()).sum())
        w("\nПроблемы форматирования (строки с лишними пробелами): {}".format(fmt_issues))

    # --- Аномалии в sales_transactions ---
    w("\n" + "=" * 70)
    w("НЕСООТВЕТСТВИЯ И АНОМАЛИИ (sales_transactions.csv)")
    w("=" * 70)

    date_col = need(sm, "date", "sales")
    raw_dates = sales[date_col].astype(str)
    parsed = parse_dates(sales[date_col])
    bad_dates = int(parsed.isna().sum() +
                    ((parsed < DATE_MIN) | (parsed > DATE_MAX)).sum())
    w("Недопустимые даты (нераспознанные / вне диапазона {}..{}): {}".format(
        DATE_MIN.date(), DATE_MAX.date(), bad_dates))

    qty = to_numeric(sales[need(sm, "quantity", "sales")])
    price = to_numeric(sales[need(sm, "price", "sales")])
    neg_qty = int((qty < 0).sum())
    neg_price = int((price < 0).sum())
    w("Отрицательные количества: {}".format(neg_qty))
    w("Отрицательные цены: {}".format(neg_price))

    bad_prod = int((~sales[need(sm, "product_id", "sales")].astype(str)
                    .isin(valid_products)).sum())
    bad_cust = int((~sales[need(sm, "customer_id", "sales")].astype(str)
                    .isin(valid_customers)).sum())
    w("Недопустимые product_id (нет в products.csv): {}".format(bad_prod))
    w("Недопустимые customer_id (нет в customers.csv): {}".format(bad_cust))

    # Недопустимые даты выпуска в products.csv (если такой столбец есть)
    pdm = resolve_columns(products, ["product_date"])
    pd_col = get(pdm, "product_date")
    if pd_col is not None:
        pdates = parse_dates(products[pd_col])
        bad_pdates = int(pdates.isna().sum() +
                         ((pdates < DATE_MIN) | (pdates > DATE_MAX)).sum())
        w("\nНедопустимые даты выпуска products.{}: {}".format(pd_col, bad_pdates))
    else:
        w("\nСтолбец даты выпуска в products.csv не найден — проверка пропущена.")

    # --- Неожиданные категориальные значения в customers ---
    w("\nНеожиданные категориальные значения (customers.csv):")
    g_col = cm.get("gender")
    if g_col is not None:
        bad_g = int((~customers[g_col].astype(str).str.strip().isin(EXPECTED_GENDER)).sum())
        w("   gender вне {}: {}".format(sorted(EXPECTED_GENDER), bad_g))
    l_col = cm.get("loyalty")
    if l_col is not None:
        bad_l = int((~customers[l_col].astype(str).str.strip().isin(EXPECTED_LOYALTY)).sum())
        w("   loyalty вне {}: {}".format(sorted(EXPECTED_LOYALTY), bad_l))

    path = os.path.join(out_dir, "Session1_DataExploration.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("    -> " + path)


# =============================================================================
# 1.2  ОЧИСТКА И ПРЕОБРАЗОВАНИЕ  ->  *_cleaned.csv
# =============================================================================
def standardize_phone(value):
    """Удаляет всё, кроме цифр и '+'."""
    if pd.isna(value):
        return "0"
    s = re.sub(r"[^\d+]", "", str(value))
    return s if s else "0"


def add_random_time(dates, seed=RNG_SEED):
    """Добавляет случайное время 09:00–17:00 к датам без времени."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    seconds = rng.integers(0, 8 * 3600 + 1, size=n)  # 8 часов = 9:00..17:00
    offsets = pd.to_timedelta(seconds, unit="s") + pd.Timedelta(hours=9)
    base = dates.dt.normalize()
    return base + offsets


def task_1_2_cleaning(sales, products, customers, out_dir):
    log("[1.2] Очистка и преобразование ...")
    sm = resolve_columns(sales, ["date"])
    cm = resolve_columns(customers, ["age", "phone_number", "date"])

    sales = sales.copy()
    customers = customers.copy()

    # --- Пропущенные значения ---
    age_col = cm.get("age")
    if age_col is not None:
        customers[age_col] = to_numeric(customers[age_col])
        mean_age = round(float(customers[age_col].mean(skipna=True)))
        customers[age_col] = customers[age_col].fillna(mean_age)

    phone_col = cm.get("phone_number")
    if phone_col is not None:
        customers[phone_col] = customers[phone_col].apply(standardize_phone)

    for promo in ["promotion_id", "promo_id", "promotion"]:
        if promo in sales.columns:
            sales[promo] = sales[promo].fillna(0)
            break

    # --- Даты -> datetime + случайное время ---
    sd = sm.get("date")
    if sd is not None:
        d = parse_dates(sales[sd])
        sales[sd] = add_random_time(d, seed=RNG_SEED)

    # join_date / last_purchase_date в customers -> datetime
    for c in customers.columns:
        if "date" in c.lower():
            customers[c] = parse_dates(customers[c])

    p1 = os.path.join(out_dir, "customers_cleaned.csv")
    p2 = os.path.join(out_dir, "sales_transactions_cleaned.csv")
    customers.to_csv(p1, index=False)
    sales.to_csv(p2, index=False)
    log("    -> " + p1)
    log("    -> " + p2)
    return sales, customers  # очищенные версии для дальнейших задач


# =============================================================================
# Общая подготовка: "обогащённые" транзакции (revenue, дата, продукт)
# =============================================================================
def build_enriched(sales, products):
    sm = resolve_columns(sales, ["customer_id", "product_id", "date", "quantity", "price"])
    pm = resolve_columns(products, ["product_id", "name", "category", "price", "cost"])

    s = sales.copy()
    s["_date"] = parse_dates(s[need(sm, "date", "sales")])
    s["_qty"] = to_numeric(s[need(sm, "quantity", "sales")]).fillna(0)
    s["_price"] = to_numeric(s[need(sm, "price", "sales")]).fillna(0)
    s["_revenue"] = s["_qty"] * s["_price"]
    s["_pid"] = s[need(sm, "product_id", "sales")].astype(str)
    s["_cid"] = s[need(sm, "customer_id", "sales")].astype(str)

    p = products.copy()
    p["_pid"] = p[need(pm, "product_id", "products")].astype(str)
    p["_name"] = p[pm["name"]].astype(str) if pm.get("name") else p["_pid"]
    p["_category"] = p[pm["category"]].astype(str) if pm.get("category") else "N/A"
    p["_cost"] = to_numeric(p[pm["cost"]]) if pm.get("cost") else np.nan

    return s, p


def render_table(ax, df, title):
    """Рисует таблицу на странице PDF."""
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    tbl = ax.table(cellText=df.values, colLabels=df.columns,
                   cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.6)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#7B3F00")
            cell.set_text_props(color="white", fontweight="bold")


# =============================================================================
# 1.3  АНАЛИЗ ТЕНДЕНЦИЙ ПРОДАЖ  ->  Session1_SalesTrends.pdf
# =============================================================================
def task_1_3_sales_trends(sales, products, out_dir):
    log("[1.3] Тенденции продаж ...")
    s, _ = build_enriched(sales, products)
    s = s.dropna(subset=["_date"])
    s["_month"] = s["_date"].dt.to_period("M").dt.to_timestamp()

    monthly = s.groupby("_month").agg(
        revenue=("_revenue", "sum"),
        transactions=("_revenue", "count"),
    )
    monthly["avg_order"] = monthly["revenue"] / monthly["transactions"]

    top3 = monthly.sort_values("revenue", ascending=False).head(3).reset_index()
    top3_tbl = pd.DataFrame({
        "Month": top3["_month"].dt.strftime("%Y-%m"),
        "Total Revenue": top3["revenue"].round(2),
    })

    path = os.path.join(out_dir, "Session1_SalesTrends.pdf")
    with PdfPages(path) as pdf:
        for col, title, color in [
            ("revenue", "Общий доход от продаж за месяц", "#7B3F00"),
            ("transactions", "Количество транзакций за месяц", "#C8862B"),
            ("avg_order", "Средняя стоимость заказа за месяц", "#4E843D"),
        ]:
            fig, ax = plt.subplots(figsize=(11, 6))
            ax.plot(monthly.index, monthly[col], marker="o", color=color)
            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.set_xlabel("Месяц")
            ax.set_ylabel(title)
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()
            pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        render_table(ax, top3_tbl, "Топ-3 месяца по выручке")
        pdf.savefig(fig); plt.close(fig)
    log("    -> " + path)


# =============================================================================
# 1.4  ЭКСПЛУАТАЦИОННЫЕ ХАРАКТЕРИСТИКИ ПРОДУКТА  ->  Session1_ProductPerformance.pdf
# =============================================================================
def task_1_4_product_performance(sales, products, out_dir):
    log("[1.4] Характеристики продукта ...")
    s, p = build_enriched(sales, products)

    by_prod = s.groupby("_pid").agg(
        qty=("_qty", "sum"),
        revenue=("_revenue", "sum"),
    ).reset_index()
    by_prod = by_prod.merge(p[["_pid", "_name", "_category", "_cost"]], on="_pid", how="left")

    by_cat = by_prod.groupby("_category")["revenue"].sum().sort_values(ascending=False)

    top3 = by_prod.sort_values("qty", ascending=False).head(3)
    top3_tbl = pd.DataFrame({
        "Product": top3["_name"],
        "Total Qty": top3["qty"].astype(int),
        "Total Revenue": top3["revenue"].round(2),
    })

    path = os.path.join(out_dir, "Session1_ProductPerformance.pdf")
    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.bar(by_cat.index.astype(str), by_cat.values, color="#7B3F00")
        ax.set_title("Общий доход по категориям продуктов", fontsize=14, fontweight="bold")
        ax.set_xlabel("Категория"); ax.set_ylabel("Выручка")
        ax.grid(True, axis="y", alpha=0.3)
        fig.autofmt_xdate()
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 4))
        render_table(ax, top3_tbl, "Топ-3 самых продаваемых продукта")
        pdf.savefig(fig); plt.close(fig)
    log("    -> " + path)


# =============================================================================
# 1.5  АНАЛИЗ ЗАКАЗЧИКОВ  ->  Session1_CustomerAnalysis.pdf
# =============================================================================
def task_1_5_customer_analysis(customers, out_dir):
    log("[1.5] Анализ заказчиков ...")
    cm = resolve_columns(customers, ["age", "gender", "loyalty"])
    c = customers.copy()

    age = to_numeric(c[need(cm, "age", "customers")])
    bins = [0, 24, 34, 44, 200]
    labels = ["18-24", "25-34", "35-44", "45+"]
    age_groups = pd.cut(age, bins=bins, labels=labels, right=True)
    age_dist = age_groups.value_counts().reindex(labels).fillna(0).astype(int)

    g_col = cm.get("gender")
    if g_col is not None:
        g = c[g_col].astype(str).str.strip()
        gender_pct = (g.value_counts(normalize=True) * 100).round(2)
        gender_tbl = pd.DataFrame({
            "Gender": gender_pct.index,
            "Percentage (%)": gender_pct.values,
        })
    else:
        gender_tbl = pd.DataFrame({"Gender": ["N/A"], "Percentage (%)": [0]})

    # средние расходы по уровням лояльности
    l_col = cm.get("loyalty")
    spend_col = None
    for cand in ["total_spent", "total_spending", "total_spend"]:
        if cand in c.columns:
            spend_col = cand
            break
    if l_col is not None and spend_col is not None:
        loyalty_avg = c.groupby(c[l_col].astype(str).str.strip())[spend_col].mean().round(2)
        loyalty_tbl = pd.DataFrame({
            "Loyalty": loyalty_avg.index,
            "Avg Spending": loyalty_avg.values,
        })
    else:
        loyalty_tbl = pd.DataFrame({"Loyalty": ["N/A"], "Avg Spending": [0]})

    path = os.path.join(out_dir, "Session1_CustomerAnalysis.pdf")
    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.bar(age_dist.index.astype(str), age_dist.values, color="#C8862B")
        ax.set_title("Распределение заказчиков по возрастным группам",
                     fontsize=14, fontweight="bold")
        ax.set_xlabel("Возрастная группа"); ax.set_ylabel("Кол-во заказчиков")
        ax.grid(True, axis="y", alpha=0.3)
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 3))
        render_table(ax, gender_tbl, "Распределение по полу (%)")
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 3))
        render_table(ax, loyalty_tbl, "Средние расходы по уровням лояльности")
        pdf.savefig(fig); plt.close(fig)
    log("    -> " + path)


# =============================================================================
# 1.6  ПРОГНОЗ ВРЕМЕННЫХ РЯДОВ (ARIMA)  ->  Session1_SalesForecast.csv
# =============================================================================
def task_1_6_forecast(sales, products, out_dir):
    log("[1.6] Прогноз ARIMA (30 дней) ...")
    from statsmodels.tsa.arima.model import ARIMA

    s, _ = build_enriched(sales, products)
    s = s.dropna(subset=["_date"])
    daily = (s.set_index("_date")["_revenue"]
               .resample("D").sum()
               .asfreq("D").fillna(0.0))

    if len(daily) < 30:
        log("    ВНИМАНИЕ: мало данных для надёжного прогноза.")

    order = (5, 1, 0)  # стартовый порядок; при сбое подбираются простые варианты
    mae = float("nan")

    # MAE на отложенной выборке (последние 30 дней)
    try:
        if len(daily) > 40:
            train, test = daily.iloc[:-30], daily.iloc[-30:]
            m = ARIMA(train, order=order).fit()
            pred = m.forecast(steps=30)
            mae = float(np.mean(np.abs(np.asarray(test) - np.asarray(pred))))
    except Exception as e:
        log("    (MAE через ARIMA не получился: {} — пробую запасной вариант)".format(e))

    # Финальная модель на всех данных -> прогноз на 30 дней
    forecast = None
    for od in [order, (2, 1, 2), (1, 1, 1), (1, 1, 0), (0, 1, 1)]:
        try:
            model = ARIMA(daily, order=od).fit()
            forecast = model.forecast(steps=30)
            order = od
            break
        except Exception:
            continue

    if forecast is None:
        # запасной вариант: скользящее среднее
        log("    ARIMA не сошлась — использую среднее за последние 30 дней.")
        last_mean = float(daily.tail(30).mean())
        idx = pd.date_range(daily.index[-1] + pd.Timedelta(days=1), periods=30, freq="D")
        forecast = pd.Series([last_mean] * 30, index=idx)

    if np.isnan(mae):
        # запасной MAE: in-sample на хвосте
        try:
            mae = float(np.mean(np.abs(np.asarray(daily.tail(30)) -
                                       float(daily.tail(30).mean()))))
        except Exception:
            mae = 0.0

    out = pd.DataFrame({
        "Date": pd.to_datetime(forecast.index).strftime("%Y-%m-%d"),
        "Predicted_Sales": np.round(np.asarray(forecast, dtype=float), 2),
    })
    path = os.path.join(out_dir, "Session1_SalesForecast.csv")
    out.to_csv(path, index=False)
    log("    ARIMA order={}, MAE={:.2f}".format(order, mae))
    log("    -> " + path)


# =============================================================================
# 1.7  СЕГМЕНТАЦИЯ (K-Means) + РЕКОМЕНДАЦИИ  ->  Session5_Segmentation_and_Recommendations.csv
# =============================================================================
def task_1_7_segmentation(sales, products, customers, out_dir):
    log("[1.7] Сегментация K-Means + рекомендации ...")
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    s, _ = build_enriched(sales, products)
    cm = resolve_columns(customers, ["customer_id"])
    cust_ids = customers[need(cm, "customer_id", "customers")].astype(str)

    # признаки заказчика
    per_cust = s.groupby("_cid").agg(
        total_purchases=("_revenue", "count"),
        avg_purchase_value=("_revenue", "mean"),
    )
    feats = pd.DataFrame({"_cid": cust_ids}).merge(
        per_cust, left_on="_cid", right_index=True, how="left"
    ).fillna(0.0)

    X = StandardScaler().fit_transform(feats[["total_purchases", "avg_purchase_value"]])
    km = KMeans(n_clusters=3, random_state=RNG_SEED, n_init=10)
    feats["cluster_label"] = km.fit_predict(X) + 1  # метки 1,2,3

    # что покупал каждый заказчик
    bought = s.groupby("_cid")["_pid"].apply(set).to_dict()

    # популярность продуктов внутри сегмента
    seg_map = dict(zip(feats["_cid"], feats["cluster_label"]))
    s["_cluster"] = s["_cid"].map(seg_map)
    seg_pop = (s.dropna(subset=["_cluster"])
                 .groupby(["_cluster", "_pid"])["_qty"].sum())

    seg_ranked = {}
    for cl in feats["cluster_label"].unique():
        try:
            ser = seg_pop.loc[cl].sort_values(ascending=False)
            seg_ranked[cl] = list(ser.index)
        except KeyError:
            seg_ranked[cl] = []

    def recommend(cid, cluster):
        owned = bought.get(cid, set())
        recs = [pid for pid in seg_ranked.get(cluster, []) if pid not in owned]
        recs = recs[:3]
        while len(recs) < 3:
            recs.append("")  # дополняем пустыми, если рекомендаций меньше 3
        return recs

    rows = []
    for _, r in feats.iterrows():
        r1, r2, r3 = recommend(r["_cid"], r["cluster_label"])
        rows.append([r["_cid"], int(r["cluster_label"]), r1, r2, r3])

    out = pd.DataFrame(rows, columns=[
        "customer_id", "cluster_label",
        "recommended_product_1", "recommended_product_2", "recommended_product_3",
    ])
    path = os.path.join(out_dir, "Session5_Segmentation_and_Recommendations.csv")
    out.to_csv(path, index=False)
    log("    -> " + path)


# =============================================================================
# 1.8  ХАРАКТЕРИСТИКИ ПРОДУКТА + ОПТИМИЗАЦИЯ ЦЕН (PED)
#       ->  Session5_Product_Performance.csv, Session5_Price_Analysis.csv
# =============================================================================
def task_1_8_price_optimization(sales, products, out_dir):
    log("[1.8] Производительность продукта + ценовая эластичность ...")
    s, p = build_enriched(sales, products)
    s = s.dropna(subset=["_date"])

    # --- Product performance ---
    perf = s.groupby("_pid").agg(
        total_quantity_sold=("_qty", "sum"),
        total_revenue=("_revenue", "sum"),
    ).reset_index()
    perf = perf.merge(p[["_pid", "_cost"]], on="_pid", how="left")
    perf["total_cost"] = perf["total_quantity_sold"] * perf["_cost"].fillna(0)
    perf["profit_margin"] = np.where(
        perf["total_revenue"] > 0,
        (perf["total_revenue"] - perf["total_cost"]) / perf["total_revenue"],
        0.0,
    ).round(4)
    perf_out = perf[["_pid", "total_quantity_sold", "total_revenue", "profit_margin"]].copy()
    perf_out.columns = ["product_id", "total_quantity_sold", "total_revenue", "profit_margin"]
    perf_out["total_revenue"] = perf_out["total_revenue"].round(2)
    perf_out = perf_out.sort_values("total_revenue", ascending=False)

    p1 = os.path.join(out_dir, "Session5_Product_Performance.csv")
    perf_out.to_csv(p1, index=False)
    log("    -> " + p1)

    # --- Price elasticity of demand (PED) методом % изменений по месяцам ---
    s["_month"] = s["_date"].dt.to_period("M")
    monthly = s.groupby(["_pid", "_month"]).agg(
        qty=("_qty", "sum"),
        avg_price=("_price", "mean"),
    ).reset_index()

    ped_rows = []
    for pid, grp in monthly.groupby("_pid"):
        grp = grp.sort_values("_month")
        q = grp["qty"].values.astype(float)
        pr = grp["avg_price"].values.astype(float)
        peds = []
        for i in range(1, len(grp)):
            if pr[i - 1] == 0 or q[i - 1] == 0:
                continue
            dpr = (pr[i] - pr[i - 1]) / pr[i - 1]
            if dpr == 0:
                continue
            dq = (q[i] - q[i - 1]) / q[i - 1]
            peds.append(dq / dpr)
        ped = float(np.mean(peds)) if peds else 0.0
        ped_rows.append((pid, round(ped, 4)))

    ped_df = pd.DataFrame(ped_rows, columns=["product_id", "price_elasticity_of_demand"])

    def suggest_change(ped):
        a = abs(ped)
        if a > 1.0:        # эластичный спрос -> снизить цену
            return "-5%"
        elif a < 1.0 and a > 0:  # неэластичный -> поднять цену
            return "+5%"
        return "0%"

    ped_df["suggested_price_change"] = ped_df["price_elasticity_of_demand"].apply(suggest_change)

    p2 = os.path.join(out_dir, "Session5_Price_Analysis.csv")
    ped_df.to_csv(p2, index=False)
    log("    -> " + p2)


# =============================================================================
# 1.9  CLTV  ->  Session1_CLTV.csv
# =============================================================================
def compute_cltv(sales, products):
    s, _ = build_enriched(sales, products)
    s = s.dropna(subset=["_date"])

    grp = s.groupby("_cid")
    avg_value = grp["_revenue"].mean()
    n_tx = grp["_revenue"].count()
    span_days = (grp["_date"].max() - grp["_date"].min()).dt.days.clip(lower=1)
    months = (span_days / 30.0).clip(lower=1.0)
    freq_per_month = n_tx / months

    cltv = (avg_value * freq_per_month * 36).round(2)
    return cltv  # Series индекс = customer_id (str)


def task_1_9_cltv(sales, products, out_dir):
    log("[1.9] CLTV ...")
    cltv = compute_cltv(sales, products)
    out = pd.DataFrame({"customer_id": cltv.index, "cltv": cltv.values})
    # customer_id как int, если возможно
    try:
        out["customer_id"] = out["customer_id"].astype(float).astype(int)
    except Exception:
        pass
    path = os.path.join(out_dir, "Session1_CLTV.csv")
    out.to_csv(path, index=False)
    log("    -> " + path)
    return cltv


# =============================================================================
# 1.10  АНАЛИЗ ОТТОКА  ->  Session1_Churn_Analysis.csv
# =============================================================================
def task_1_10_churn(sales, products, customers, out_dir, cltv=None):
    log("[1.10] Анализ оттока ...")
    if cltv is None:
        cltv = compute_cltv(sales, products)

    cm = resolve_columns(customers, ["customer_id", "churn"])
    cid_col = need(cm, "customer_id", "customers")
    churn_col = cm.get("churn")

    c = customers.copy()
    c["_cid"] = c[cid_col].astype(str)

    if churn_col is None:
        log("    ВНИМАНИЕ: столбец churn не найден — отток считается нулевым.")
        c["_churn"] = 0
    else:
        # приводим к 0/1 из True/False/'Yes'/'1' и т.п.
        raw = c[churn_col].astype(str).str.strip().str.lower()
        c["_churn"] = raw.isin(["1", "true", "yes", "y", "churned", "да"]).astype(int)

    churn_rate = round(float(c["_churn"].mean()) * 100, 2)

    c["_cltv"] = c["_cid"].map(cltv).fillna(0.0)
    avg_churned = round(float(c.loc[c["_churn"] == 1, "_cltv"].mean()), 2) \
        if (c["_churn"] == 1).any() else 0.0
    avg_active = round(float(c.loc[c["_churn"] == 0, "_cltv"].mean()), 2) \
        if (c["_churn"] == 0).any() else 0.0

    out = pd.DataFrame([{
        "churn_rate": churn_rate,
        "avg_cltv_churned": avg_churned,
        "avg_cltv_active": avg_active,
    }])
    path = os.path.join(out_dir, "Session1_Churn_Analysis.csv")
    out.to_csv(path, index=False)
    log("    churn_rate={}%  avg_cltv_churned={}  avg_cltv_active={}".format(
        churn_rate, avg_churned, avg_active))
    log("    -> " + path)


# =============================================================================
# ГЕНЕРАТОР ДЕМО-ДАННЫХ  (--demo) — чтобы проверить, что скрипт запускается
# =============================================================================
def generate_demo_data(input_dir):
    log("Генерация демо-данных в " + input_dir + " ...")
    rng = np.random.default_rng(RNG_SEED)
    os.makedirs(input_dir, exist_ok=True)

    n_products = 12
    categories = ["Pastry", "Bread", "Tart"]
    products = pd.DataFrame({
        "product_id": range(1, n_products + 1),
        "name": ["Product_{}".format(i) for i in range(1, n_products + 1)],
        "category": [categories[i % 3] for i in range(n_products)],
        "price": np.round(rng.uniform(2, 12, n_products), 2),
        "cost": np.round(rng.uniform(1, 6, n_products), 2),
    })

    n_customers = 200
    customers = pd.DataFrame({
        "customer_id": range(1, n_customers + 1),
        "name": ["Customer_{}".format(i) for i in range(1, n_customers + 1)],
        "age": rng.integers(18, 70, n_customers).astype(float),
        "gender": rng.choice(["M", "F"], n_customers),
        "phone_number": ["+1 (555) {:03d}-{:04d}".format(rng.integers(0, 999),
                                                          rng.integers(0, 9999))
                         for _ in range(n_customers)],
        "membership_status": rng.choice(["Basic", "Silver", "Gold"], n_customers),
        "join_date": pd.to_datetime("2022-01-01") +
                     pd.to_timedelta(rng.integers(0, 700, n_customers), unit="D"),
        "total_spent": np.round(rng.uniform(50, 2000, n_customers), 2),
        "churn_status": rng.choice([0, 1], n_customers, p=[0.8, 0.2]),
    })
    # внесём пропуски, чтобы проверить очистку
    customers.loc[rng.choice(n_customers, 10, replace=False), "age"] = np.nan
    customers.loc[rng.choice(n_customers, 8, replace=False), "phone_number"] = np.nan

    n_tx = 4000
    dates = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 365, n_tx), unit="D")
    sales = pd.DataFrame({
        "transaction_id": range(1, n_tx + 1),
        "customer_id": rng.integers(1, n_customers + 1, n_tx),
        "date": dates.strftime("%Y-%m-%d"),
        "product_id": rng.integers(1, n_products + 1, n_tx),
        "quantity": rng.integers(1, 6, n_tx),
        "price": np.round(rng.uniform(2, 12, n_tx), 2),
        "promotion_id": rng.choice([np.nan, 1, 2, 3], n_tx, p=[0.7, 0.1, 0.1, 0.1]),
    })

    products.to_csv(os.path.join(input_dir, FILE_PRODUCTS), index=False)
    customers.to_csv(os.path.join(input_dir, FILE_CUSTOMERS), index=False)
    sales.to_csv(os.path.join(input_dir, FILE_SALES), index=False)
    log("Демо-данные созданы.")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Belle Croissant — Session 1 analysis")
    parser.add_argument("--input", default=".", help="папка с входными CSV (по умолчанию: текущая)")
    parser.add_argument("--output", default="./output", help="папка для результатов")
    parser.add_argument("--demo", action="store_true", help="сгенерировать демо-данные и прогнать")
    args = parser.parse_args()

    input_dir = args.input
    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    if args.demo:
        input_dir = os.path.join(out_dir, "_demo_data")
        generate_demo_data(input_dir)

    log("\n" + "=" * 70)
    log("BELLE CROISSANT LYONNAIS — SESSION 1 (АНАЛИЗ ДАННЫХ)")
    log("Вход: {}   Выход: {}".format(os.path.abspath(input_dir), os.path.abspath(out_dir)))
    log("=" * 70)

    sales, products, customers = load_data(input_dir)

    # Показать, какие столбцы скрипт распознал (для проверки)
    log("\nРаспознанные столбцы:")
    sm = resolve_columns(sales, ["transaction_id", "customer_id", "product_id",
                                 "date", "quantity", "price", "promotion_id"])
    pm = resolve_columns(products, ["product_id", "name", "category", "cost", "product_date"])
    cm = resolve_columns(customers, ["customer_id", "age", "gender", "phone_number",
                                     "loyalty", "churn"])
    log("  sales:     " + ", ".join("{}={}".format(k, v) for k, v in sm.items() if v))
    log("  products:  " + ", ".join("{}={}".format(k, v) for k, v in pm.items() if v))
    log("  customers: " + ", ".join("{}={}".format(k, v) for k, v in cm.items() if v))

    # 1.1 изучение (на сырых данных)
    task_1_1_exploration(sales, products, customers, out_dir)

    # 1.2 очистка -> используем очищенные данные дальше
    sales_c, customers_c = task_1_2_cleaning(sales, products, customers, out_dir)

    # 1.3–1.5 отчёты
    task_1_3_sales_trends(sales_c, products, out_dir)
    task_1_4_product_performance(sales_c, products, out_dir)
    task_1_5_customer_analysis(customers_c, out_dir)

    # 1.6 прогноз
    task_1_6_forecast(sales_c, products, out_dir)

    # 1.7 сегментация + рекомендации
    task_1_7_segmentation(sales_c, products, customers_c, out_dir)

    # 1.8 цены
    task_1_8_price_optimization(sales_c, products, out_dir)

    # 1.9 CLTV
    cltv = task_1_9_cltv(sales_c, products, out_dir)

    # 1.10 отток
    task_1_10_churn(sales_c, products, customers_c, out_dir, cltv=cltv)

    log("\n" + "=" * 70)
    log("ГОТОВО. Все файлы-результаты — в папке: {}".format(os.path.abspath(out_dir)))
    log("=" * 70)


if __name__ == "__main__":
    main()
