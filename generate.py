#!/usr/bin/env python3
"""
Felicity site generator (dev-time tool only).

The shipped site is plain static HTML/CSS/JS with no build step and no
runtime dependencies. This script exists purely so that ~19 near-identical
product pages and 6 category pages can be authored from one source of data
without hand-duplicating markup and letting titles/prices/specs drift out of
sync. Run it, commit the generated .html/.js/.xml files, and the site is
ready to deploy as-is to any static host.

Usage: python3 generate.py
"""
import json
import os
import re
import shutil
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://felicity.ua"  # placeholder domain - replace before launch

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

CATEGORIES = {
    "invertory": {
        "name": "Гібридні інвертори Felicity Solar",
        "meta_desc": "Гібридні інвертори Felicity Solar для сонячних електростанцій: від 3 до 125 кВт, однофазні та трифазні, доставка по Україні.",
        "intro": "Гібридні інвертори Felicity Solar перетворюють постійний струм від панелей та акумуляторів у змінний для живлення побутових приладів. У каталозі - моделі потужністю від 3 до 125 кВт, однофазні та трифазні, для приватних будинків і комерційних об'єктів.",
    },
    "akumulyatory": {
        "name": "Акумулятори LiFePO4",
        "meta_desc": "Літій-залізо-фосфатні акумулятори Felicity LiFePO4 для сонячних систем: 12V-51.2V, ресурс до 8000 циклів.",
        "intro": "Акумулятори Felicity на основі хімії LiFePO4 забезпечують безпечне накопичення енергії для домашніх сонячних електростанцій. Витримують тисячі циклів заряду-розряду та зберігають ємність протягом десятиліття експлуатації.",
    },
    "zaryadni-stantsii": {
        "name": "Зарядні станції",
        "meta_desc": "Портативні зарядні станції Felicity (power station) 500-2000 Вт для дому, дачі та подорожей. Швидка зарядка, тихий тепловідвід.",
        "intro": "Портативні зарядні станції Felicity - компактне джерело автономного живлення для дому, офісу чи виїзду на природу. Живлять техніку через розетку 220V, USB та DC-виходи навіть під час відключення електроенергії.",
    },
    "avr": {
        "name": "Автоматичні перемикачі АВР",
        "meta_desc": "Автоматичні вводи резерву (АВР) Felicity ATS для миттєвого перемикання між мережею та резервним живленням.",
        "intro": "Автоматичні перемикачі фаз (АВР/ATS) Felicity миттєво перемикають навантаження між основною мережею та резервним джерелом живлення, забезпечуючи безперебійну роботу обладнання при зникненні напруги.",
    },
    "powerbank": {
        "name": "PowerBank",
        "meta_desc": "Портативні павербанки Felicity 20000-30000 мАг для заряджання смартфонів, планшетів та іншої техніки в дорозі.",
        "intro": "Павербанки Felicity - компактні акумулятори для щоденного заряджання гаджетів у дорозі, під час подорожей чи відключень світла.",
    },
    "aksesuary": {
        "name": "Аксесуари",
        "meta_desc": "Аксесуари та комплектуючі Felicity для сонячних станцій: кабелі, MC4-конектори, кріплення для панелей.",
        "intro": "Комплектуючі та витратні матеріали для монтажу й обслуговування сонячних електростанцій Felicity: кабелі, конектори, кріплення та інше приладдя.",
    },
}

CATEGORY_ORDER = ["invertory", "akumulyatory"]

INVERTER_MODELS = [
    # (model code, power label, battery/DC voltage label, phase count, note)
    ("IVAM6048P1G1", "6 кВт", "48 В", 1, ""),
    ("IVAM8048P1G1", "8 кВт", "48 В", 1, ""),
    ("IVBM8048P1G1", "8 кВт", "48 В", 1, ""),
    ("IVBM10048P1G1", "10 кВт", "48 В", 1, ""),
    ("IVCM1012-2024-3024 PRO", "10-30 кВт", "24/48 В", 1, "Серія PRO з перемиканням потужності 10/20/30 кВт"),
    ("IVCM1012-2024-LV", "10-24 кВт", "24/48 В (LV)", 1, "Перемикання потужності"),
    ("IVCM1612P1G2-LV", "16 кВт", "48 В (LV)", 1, ""),
    ("IVCM2012-3224P1G2", "20-32 кВт", "24/48 В", 1, "Перемикання потужності"),
    ("IVEM3024-5048", "3-5 кВт", "24/48 В", 1, "Перемикання потужності"),
    ("IVEM3048-5048-LV", "3-5 кВт", "48 В (LV)", 1, "Перемикання потужності"),
    ("IVEM4024-II", "4 кВт", "24 В", 1, "Друге покоління серії EM"),
    ("IVEM5048-SALV", "5 кВт", "48 В (LV)", 1, "Версія SA"),
    ("IVEM6048", "6 кВт", "48 В", 1, ""),
    ("IVEM6048-II", "6 кВт", "48 В", 1, "Друге покоління серії EM"),
    ("IVEM6048-SAII", "6 кВт", "48 В", 1, "Версія SA, друге покоління"),
    ("IVEM4024-SAII", "4 кВт", "24 В", 1, "Версія SA, друге покоління"),
    ("IVEM8048", "8 кВт", "48 В", 1, ""),
    ("IVEM8048-II", "8 кВт", "48 В", 1, "Друге покоління серії EM"),
    ("IVEM12048-II", "12 кВт", "48 В", 1, "Друге покоління серії EM"),
    ("IVGM3~6KLP1G2", "3-6 кВт", "низька напруга (LV)", 3, ""),
    ("IVGM5~8KLP1G1", "5-8 кВт", "низька напруга (LV)", 3, ""),
    ("IVGM5~8KLP2G1", "5-8 кВт", "низька напруга (LV)", 3, ""),
    ("IVGM5-8KLP2G1-SA", "5-8 кВт", "низька напруга (LV)", 3, "Версія SA"),
    ("IVGM5K-6KLP1G1", "5-6 кВт", "низька напруга (LV)", 3, ""),
    ("IVGM8~25KHP3G3", "8-25 кВт", "висока напруга (HV)", 3, "Покоління 3"),
    ("IVGM8KLP2G1-SALL", "8 кВт", "низька напруга (LV)", 3, "Версія SA"),
    ("IVGM8KLP2G1-US", "8 кВт", "низька напруга (LV)", 3, "Версія US"),
    ("IVGM10~20KLP3G1", "10-20 кВт", "низька напруга (LV)", 3, ""),
    ("IVGM30KHP3G2", "30 кВт", "висока напруга (HV)", 3, "Покоління 2"),
    ("IVGM50KHP3G1", "50 кВт", "висока напруга (HV)", 3, ""),
    ("IVGM50KHP3G2", "50 кВт", "висока напруга (HV)", 3, "Покоління 2"),
    ("IVGM125KHP3G1", "125 кВт", "висока напруга (HV)", 3, "Промислова серія"),
    ("IVGM5048", "5 кВт", "48 В", 1, ""),
    ("T-REX-10KHP3G01", "10 кВт", "висока напруга (HV)", 3, "Серія T-REX"),
    ("T-REX-10KLP3G01", "10 кВт", "низька напруга (LV)", 3, "Серія T-REX"),
    ("T-REX-50KHP3G01", "50 кВт", "висока напруга (HV)", 3, "Серія T-REX"),
]


def _slugify(code):
    s = re.sub(r"[^a-z0-9]+", "-", code.lower())
    return s.strip("-")


def _power_kw(label):
    nums = [int(n) for n in re.findall(r"\d+", label)]
    return sum(nums) / len(nums) if nums else 5


PRODUCTS = []
for _i, (_code, _power, _voltage, _phase, _note) in enumerate(INVERTER_MODELS, start=1):
    _phase_label = "Трифазний" if _phase == 3 else "Однофазний"
    _ac_out = "380 В (3 фази)" if _phase == 3 else "220 В ±5%"
    _desc = (
        "Гібридний інвертор Felicity Solar %s потужністю %s для сонячних електростанцій. "
        "Поєднує роботу з мережею, акумулятором та сонячними панелями в одному пристрої."
        % (_code, _power)
    )
    if _note:
        _desc += " " + _note + "."
    PRODUCTS.append(dict(
        id=_i, sku="FLC-%03d" % _i, code=_code, slug="felicity-solar-%s" % _slugify(_code), category="invertory",
        name="Гібридний інвертор Felicity Solar %s" % _code,
        price=0, old_price=None, in_stock=True,
        desc=_desc,
        specs=[
            ("Тип", "Гібридний"), ("Бренд", "Felicity Solar"), ("Модель", _code),
            ("Номінальна потужність", _power), ("Напруга АКБ", _voltage),
            ("Вихідна напруга AC", _ac_out), ("Фаза", _phase_label),
        ],
    ))

BATTERY_MODELS = [
    # (raw folder code -> also used for photo slug, display model code, voltage, capacity, series family, note)
    ("FLA12100", "FLA12100", "12 В", "100 А·год", "FLA", ''),
    ("FLA12100PG2", "FLA12100PG2", "12 В", "100 А·год", "FLA", ''),
    ("FLA12171-EU", "FLA12171-EU", "12 В", "171 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA12200", "FLA12200", "12 В", "200 А·год", "FLA", ''),
    ("FLA12200PG2", "FLA12200PG2", "12 В", "200 А·год", "FLA", ''),
    ("FLA12300", "FLA12300", "12 В", "300 А·год", "FLA", ''),
    ("FLA12300PG2", "FLA12300PG2", "12 В", "300 А·год", "FLA", ''),
    ("FLA24100", "FLA24100", "24 В", "100 А·год", "FLA", ''),
    ("FLA24100-EU", "FLA24100-EU", "24 В", "100 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA24100PG2", "FLA24100PG2", "24 В", "100 А·год", "FLA", ''),
    ("FLA24100WG2", "FLA24100WG2", "24 В", "100 А·год", "FLA", ''),
    ("FLA24171-EU", "FLA24171-EU", "24 В", "171 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA24200", "FLA24200", "24 В", "200 А·год", "FLA", ''),
    ("FLA24200WG2", "FLA24200WG2", "24 В", "200 А·год", "FLA", ''),
    ("FLA24230-EU", "FLA24230-EU", "24 В", "230 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA24250", "FLA24250", "24 В", "250 А·год", "FLA", ''),
    ("FLA24250WG2", "FLA24250WG2", "24 В", "250 А·год", "FLA", ''),
    ("FLA24280-EU", "FLA24280-EU", "24 В", "280 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA24300", "FLA24300", "24 В", "300 А·год", "FLA", ''),
    ("FLA24300WG2", "FLA24300WG2", "24 В", "300 А·год", "FLA", ''),
    ("FLA24460-EU", "FLA24460-EU", "24 В", "460 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA24500", "FLA24500", "24 В", "500 А·год", "FLA", ''),
    ("FLA48100", "FLA48100", "48 В", "100 А·год", "FLA", ''),
    ("FLA48100-EU", "FLA48100-EU", "48 В", "100 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48100UG1", "FLA48100UG1", "48 В", "100 А·год", "FLA", ''),
    ("FLA48171-EU", "FLA48171-EU", "48 В", "171 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48200", "FLA48200", "48 В", "200 А·год", "FLA", ''),
    ("FLA48200-P", "FLA48200-P", "48 В", "200 А·год", "FLA", ''),
    ("FLA48230", "FLA48230", "48 В", "230 А·год", "FLA", ''),
    ("FLA48230-EU", "FLA48230-EU", "48 В", "230 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48250", "FLA48250", "48 В", "250 А·год", "FLA", ''),
    ("FLA48250-EU", "FLA48250-EU", "48 В", "250 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48280", "FLA48280", "48 В", "280 А·год", "FLA", ''),
    ("FLA48280-EU", "FLA48280-EU", "48 В", "280 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48300", "FLA48300", "48 В", "300 А·год", "FLA", ''),
    ("FLA48300-EU", "FLA48300-EU", "48 В", "300 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48300TG2", "FLA48300TG2", "48 В", "300 А·год", "FLA", ''),
    ("FLA48314-EU", "FLA48314-EU", "48 В", "314 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48314-PLUS", "FLA48314-PLUS", "48 В", "314 А·год", "FLA", ''),
    ("FLA48350TG2", "FLA48350TG2", "48 В", "350 А·год", "FLA", ''),
    ("FLA48460-EU", "FLA48460-EU", "48 В", "460 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48460TG2-EU", "FLA48460TG2-EU", "48 В", "460 А·год", "FLA", 'Версія для ринку ЄС.'),
    ("FLA48500", "FLA48500", "48 В", "500 А·год", "FLA", ''),
    ("FLA48500TG2", "FLA48500TG2", "48 В", "500 А·год", "FLA", ''),
    ("FLB24100WG1", "FLB24100WG1", "24 В", "100 А·год", "FLB", 'Стекована конструкція для нарощування ємності.'),
    ("FLB24205.24230WG1", "FLB24205-24230WG1", "24 В", "205–230 А·год", "FLB", 'Стекована конструкція для нарощування ємності.'),
    ("FLB48100WG1", "FLB48100WG1", "48 В", "100 А·год", "FLB", 'Стекована конструкція для нарощування ємності.'),
    ("FLB48205.48230WG1", "FLB48205-48230WG1", "48 В", "205–230 А·год", "FLB", 'Стекована конструкція для нарощування ємності.'),
    ("FLB48314TG1", "FLB48314TG1", "48 В", "314 А·год", "FLB", 'Стекована конструкція для нарощування ємності.'),
    ("FLH48100UG1", "FLH48100UG1", "48 В", "100 А·год", "FLH", 'Високовольтна стекована батарея для трифазних систем.'),
    ("FLH48100UG2", "FLH48100UG2", "48 В", "100 А·год", "FLH", 'Високовольтна стекована батарея для трифазних систем.'),
    ("FLH96050SG1", "FLH96050SG1", "96 В", "50 А·год", "FLH", 'Високовольтна стекована батарея для трифазних систем.'),
    ("FLH96050SG2", "FLH96050SG2", "96 В", "50 А·год", "FLH", 'Високовольтна стекована батарея для трифазних систем.'),
    ("FLH96050SG2-H", "FLH96050SG2-H", "96 В", "50 А·год", "FLH", 'Високовольтна стекована батарея для трифазних систем.'),
    ("FLS48050SG1", "FLS48050SG1", "48 В", "50 А·год", "FLS", 'Стекована батарея з вбудованим дисплеєм та моніторингом у реальному часі.'),
    ("FLS48100SG1", "FLS48100SG1", "48 В", "100 А·год", "FLS", 'Стекована батарея з вбудованим дисплеєм та моніторингом у реальному часі.'),
    ("FLS48100SG2", "FLS48100SG2", "48 В", "100 А·год", "FLS", 'Стекована батарея з вбудованим дисплеєм та моніторингом у реальному часі.'),
    ("LPBA12100WG1", "LPBA12100WG1", "12 В", "100 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA12200WG1", "LPBA12200WG1", "12 В", "200 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA24100WG1", "LPBA24100WG1", "24 В", "100 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA24200WG1", "LPBA24200WG1", "24 В", "200 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA48100-OL", "LPBA48100-OL", "48 В", "100 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA48100WG1", "LPBA48100WG1", "48 В", "100 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA48200WG1", "LPBA48200WG1", "48 В", "200 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA48300TG1", "LPBA48300TG1", "48 В", "300 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
    ("LPBA48350TG1", "LPBA48350TG1", "48 В", "350 А·год", "LPBA", 'Настінний монтаж, компактний форм-фактор.'),
]

_battery_start_id = len(PRODUCTS) + 1
for _i, (_folder_code, _code, _volt, _cap, _series, _note) in enumerate(BATTERY_MODELS, start=_battery_start_id):
    _desc = (
        "Акумулятор Felicity Solar %s на основі хімії LiFePO4, номінальна напруга %s, ємність %s. "
        "Безпечне накопичення енергії для домашньої сонячної електростанції з ресурсом до 8000 циклів заряду-розряду."
        % (_code, _volt, _cap)
    )
    if _note:
        _desc += " " + _note
    PRODUCTS.append(dict(
        id=_i, sku="FLC-%03d" % _i, code=_folder_code, slug="felicity-solar-%s" % _slugify(_folder_code), category="akumulyatory",
        name="Акумулятор Felicity Solar %s" % _code,
        price=0, old_price=None, in_stock=True,
        desc=_desc,
        specs=[
            ("Тип", "Літій-залізо-фосфатний (LiFePO4)"), ("Бренд", "Felicity Solar"), ("Модель", _code),
            ("Номінальна напруга", _volt), ("Ємність", _cap), ("Серія", _series),
            ("Ресурс", "до 8000 циклів"),
        ],
    ))

# ---------------------------------------------------------------------------
# Live price/stock sync from a published Google Sheet (CSV export)
# ---------------------------------------------------------------------------
# Publish the sheet as: File -> Share -> Publish to web -> CSV, then paste the
# resulting URL below. Expected columns (header row): Артикул, Модель, Назва,
# Ціна, В наявності. Rows are matched to products by "Артикул" (the FLC-###
# SKU) since it's short and typo-proof, unlike the raw model codes which
# contain spaces/tildes. If the URL is empty or unreachable, prices/stock
# stay at their current values (0 / in_stock=True) so the generator still
# works without the sheet.
PRICE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2gl9sSPX4koEtBUKTvYjQ0jfitbai1FLeDIWNYQX4HLrDeLGUoBm89UMXS0DpwlS8PzciVuok_NzX/pub?gid=1073870778&single=true&output=csv"

# ---------------------------------------------------------------------------
# Contact/checkout form submissions (Google Apps Script Web App)
# ---------------------------------------------------------------------------
# Create a Google Sheet -> Extensions -> Apps Script -> paste the doPost()
# script that appends form submissions to a "Leads" tab -> Deploy -> Web app
# (Execute as: me, Who has access: Anyone) -> paste the /exec URL below.
# If empty, forms show a local "sent" confirmation but nothing is recorded.
FORM_ENDPOINT_URL = "https://script.google.com/macros/s/AKfycbwgmhPQMiwIwOWqtV9H9sAOs8kt5eFWrfEZ67G2-Dk5hePdRmBZP00-ceyxWPg_oSdg/exec"


def load_price_sheet(url):
    if not url:
        return {}
    import csv
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8-sig")
    except Exception as e:
        print("Warning: could not fetch price sheet (%s) - keeping existing prices." % e)
        return {}
    rows = {}
    for row in csv.DictReader(text.splitlines()):
        sku = (row.get("Артикул") or "").strip()
        if not sku:
            continue
        def _num(key):
            v = (row.get(key) or "").strip().replace(" ", "").replace(",", ".")
            return float(v) if v else None
        price = _num("Ціна")
        old_price = _num("Стара ціна")
        in_stock_raw = (row.get("В наявності") or "").strip().lower()
        in_stock = in_stock_raw in ("так", "true", "1", "yes", "+") if in_stock_raw else None
        rows[sku] = {"price": price, "old_price": old_price, "in_stock": in_stock}
    return rows


_price_overrides = load_price_sheet(PRICE_SHEET_CSV_URL)
for p in PRODUCTS:
    override = _price_overrides.get(p["sku"])
    if not override:
        continue
    if override["price"] is not None:
        p["price"] = int(override["price"])
    if override["old_price"] is not None:
        p["old_price"] = int(override["old_price"])
    if override["in_stock"] is not None:
        p["in_stock"] = override["in_stock"]
if _price_overrides:
    print("Applied price/stock overrides from sheet for %d models." % len(_price_overrides))

# Discontinued models with no available product photos (not sold by the
# manufacturer on eu.felicitysolar.com; likely China-domestic-only SKUs).
# Filtered out here, after id/sku assignment, so remaining SKUs keep their
# existing numbers and don't disturb the Google Sheet mapping.
DISCONTINUED_CODES = {"IVCM1612P1G2-LV", "IVGM5-8KLP2G1-SA", "IVGM8KLP2G1-SALL", "IVGM5048"}
PRODUCTS = [p for p in PRODUCTS if p["code"] not in DISCONTINUED_CODES]

PRODUCT_PHOTOS_DIR = os.path.join(ROOT, "product-photos")

for p in PRODUCTS:
    p["url"] = "product/%s/" % p["slug"]
    photo_dir = os.path.join(PRODUCT_PHOTOS_DIR, p["slug"])
    real_photos = sorted(os.listdir(photo_dir)) if os.path.isdir(photo_dir) else []
    if real_photos:
        p["images"] = ["img/%s/%s" % (p["slug"], fn) for fn in real_photos]
    else:
        p["images"] = ["img/%s.svg" % p["slug"]]
    p["image"] = p["images"][0]
    if p["old_price"]:
        p["discount"] = round((p["old_price"] - p["price"]) / p["old_price"] * 100)
    else:
        p["discount"] = None

PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}

STATIC_PAGES = [
    ("about", "Про нас"),
    ("delivery", "Доставка"),
    ("payment", "Оплата"),
    ("partnership", "Партнерство"),
    ("contact", "Контакти"),
]

print("Loaded %d products across %d categories." % (len(PRODUCTS), len(CATEGORIES)))

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def prefix_for(depth):
    return {0: "", 1: "../", 2: "../../"}[depth]


def fmt_price(v):
    return "{:,}".format(v).replace(",", " ") + " ₴"


def abs_url(path):
    return BASE_URL + "/" + path.lstrip("/")


CART_SVG = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M3 4h2l2.4 12.2a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.6L21 8H6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="10" cy="21" r="1.4" fill="currentColor"/><circle cx="18" cy="21" r="1.4" fill="currentColor"/>'
    '</svg>'
)

SEARCH_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<circle cx="11" cy="11" r="7" stroke="#06210f" stroke-width="2"/><path d="M21 21l-4-4" stroke="#06210f" stroke-width="2" stroke-linecap="round"/>'
    '</svg>'
)


def nav_items():
    items = [("/", "Головна")]
    for slug in CATEGORY_ORDER:
        items.append(("/category/%s/" % slug, CATEGORIES[slug]["name"]))
    items.append(("/catalog/", "Всі товари"))
    return items


def render_header(depth, active_path=None):
    prefix = prefix_for(depth)
    home = prefix + "index.html"
    cart = prefix + "cart.html"

    nav_lis = []
    for href, label in nav_items():
        target = prefix + "index.html" if href == "/" else prefix + href.strip("/") + "/index.html"
        current = ' aria-current="page"' if active_path == href else ""
        nav_lis.append('<li><a href="%s"%s>%s</a></li>' % (target, current, label))

    search_results_id = "search-results"
    header = []
    header.append('<a href="skip-content-anchor" class="skip-link">Перейти до основного контенту</a>' .replace("skip-content-anchor", "#main-content"))
    header.append('<header class="site-header">')
    header.append('<div class="container header-top">')
    header.append('<a href="%s" class="logo" aria-label="Felicity - головна сторінка"><img src="%simg/logo.png" alt="Felicity Solar" class="logo-img"></a>' % (home, prefix))
    header.append('<div class="header-search" data-search-wrap>')
    header.append('<form role="search" action="%scatalog/index.html" method="get">' % prefix)
    header.append('<label class="visually-hidden" for="search-desktop">Пошук товарів</label>')
    header.append('<input type="search" id="search-desktop" name="q" data-search-input placeholder="Пошук по каталогу..." autocomplete="off">')
    header.append('<button type="submit" aria-label="Шукати">%s</button>' % SEARCH_SVG)
    header.append('</form>')
    header.append('<div class="search-suggestions" data-search-results></div>')
    header.append('</div>')
    header.append('<div class="header-actions">')
    header.append('<a class="header-partner" href="%spartnership.html">Стати партнером</a>' % prefix)
    header.append('<div class="header-phone"><span>Зателефонуйте нам</span><strong><a href="tel:+380000000000">+38 (0__) ___ __ __</a></strong></div>')
    header.append('<a class="cart-link" href="%s" aria-label="Кошик">%s<span class="cart-count" data-cart-count style="display:none">0</span></a>' % (cart, CART_SVG))
    header.append('<button class="burger" data-burger aria-label="Відкрити меню" aria-expanded="false"><span></span><span></span><span></span></button>')
    header.append('</div>')
    header.append('</div>')
    header.append('<nav class="main-nav" data-main-nav aria-label="Категорії каталогу">')
    header.append('<div class="container">')
    header.append('<div class="mobile-search" data-search-wrap>')
    header.append('<label class="visually-hidden" for="search-mobile">Пошук товарів</label>')
    header.append('<input type="search" id="search-mobile" data-search-input placeholder="Пошук по каталогу..." autocomplete="off">')
    header.append('<div class="search-suggestions" data-search-results></div>')
    header.append('</div>')
    header.append('<ul>%s</ul>' % "".join(nav_lis))
    header.append('</div>')
    header.append('</nav>')
    header.append('</header>')
    return "\n".join(header)


def render_footer(depth):
    prefix = prefix_for(depth)
    cat_links = "".join(
        '<li><a href="%scategory/%s/index.html">%s</a></li>' % (prefix, slug, CATEGORIES[slug]["name"])
        for slug in CATEGORY_ORDER
    )
    page_links = "".join(
        '<li><a href="%s%s.html">%s</a></li>' % (prefix, slug, label)
        for slug, label in STATIC_PAGES
    )
    return """
<footer class="site-footer">
  <div class="container footer-grid">
    <div class="footer-col">
      <a class="footer-phone" href="tel:+380000000000">+38 (0__) ___ __ __</a>
      <p>Felicity - обладнання Felicity Solar в Україні. Пн-Пт 9:00-18:00.</p>
    </div>
    <div class="footer-col">
      <h3>Каталог</h3>
      <ul>%s</ul>
    </div>
    <div class="footer-col">
      <h3>Інформація</h3>
      <ul>%s<li><a href="%scart.html">Кошик</a></li></ul>
    </div>
    <div class="footer-col">
      <h3>Про Felicity</h3>
      <p>Ми постачаємо обладнання Felicity Solar та надаємо підтримку по всій Україні.</p>
    </div>
  </div>
  <div class="container footer-bottom">
    <span>© %s Felicity. Усі права захищено.</span>
    <span>Ціни на сайті вказані в гривнях і не є публічною офертою.</span>
  </div>
</footer>
""" % (cat_links, page_links, prefix, "2026")


def json_ld(data):
    return '<script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False)


def organization_ld():
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Felicity",
        "url": BASE_URL + "/",
        "logo": abs_url("img/logo.png"),
        "description": "Felicity - обладнання Felicity Solar в Україні.",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+38-0__-___-__-__",
            "contactType": "customer service",
            "areaServed": "UA",
            "availableLanguage": ["Ukrainian"],
        },
    })


def local_business_ld():
    return json_ld({
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "Felicity",
        "url": BASE_URL + "/",
        "telephone": "+38-0__-___-__-__",
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "UA",
        },
        "openingHours": "Mo-Fr 09:00-18:00",
    })


def breadcrumb_ld(items):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": abs_url(url)}
            for i, (name, url) in enumerate(items)
        ],
    })


def bc_href(url, prefix):
    if url == "/":
        return prefix + "index.html"
    if url.endswith(".html"):
        return prefix + url.lstrip("/")
    return prefix + url.strip("/") + "/index.html"


def render_breadcrumbs(items, depth):
    prefix = prefix_for(depth)
    lis = []
    for i, (name, url) in enumerate(items):
        if i == len(items) - 1:
            lis.append('<li aria-current="page">%s</li>' % name)
        else:
            lis.append('<li><a href="%s">%s</a></li>' % (bc_href(url, prefix), name))
    return '<nav class="breadcrumbs container" aria-label="Хлібні крихти"><ol>%s</ol></nav>' % "".join(lis)


def page(title, meta_desc, canonical_path, depth, body_html, json_ld_blocks=None, og_image=None,
         robots="index, follow", extra_scripts=None):
    prefix = prefix_for(depth)
    canonical = abs_url(canonical_path)
    og_image_url = abs_url(og_image or "img/og-default.svg")
    ld_html = "\n".join(json_ld_blocks or [])
    extra_js_html = "\n".join('<script src="%sjs/%s"></script>' % (prefix, s) for s in (extra_scripts or []))
    return """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(meta_desc)s">
<meta name="robots" content="%(robots)s">
<link rel="canonical" href="%(canonical)s">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Felicity">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(meta_desc)s">
<meta property="og:image" content="%(og_image)s">
<meta property="og:url" content="%(canonical)s">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="%(prefix)simg/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="%(prefix)scss/style.css">
%(ld)s
</head>
<body data-depth="%(depth)s">
%(header)s
<main id="main-content">
%(body)s
</main>
%(footer)s
<script src="%(prefix)sjs/products.js"></script>
<script src="%(prefix)sjs/main.js"></script>
<script src="%(prefix)sjs/cart.js"></script>
%(extra_js)s
</body>
</html>
""" % {
        "title": title,
        "meta_desc": meta_desc,
        "robots": robots,
        "canonical": canonical,
        "og_image": og_image_url,
        "prefix": prefix,
        "ld": ld_html,
        "depth": depth,
        "header": render_header(depth, canonical_path if canonical_path in [h for h, _ in nav_items()] else None),
        "body": body_html,
        "footer": render_footer(depth),
        "extra_js": extra_js_html,
    }


def write_file(rel_path, content):
    full = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


print("Templating helpers loaded.")

# ---------------------------------------------------------------------------
# Product card + gallery placeholders
# ---------------------------------------------------------------------------

def product_card_html(p, depth, lazy=True):
    prefix = prefix_for(depth)
    badge = ""
    if not p["in_stock"]:
        badge = '<span class="badge badge-out">Розпродано</span>'
    elif p["discount"]:
        badge = '<span class="badge badge-sale">-%d%%</span>' % p["discount"]

    price_html = '<span class="price-current">%s</span>' % fmt_price(p["price"])
    if p["old_price"]:
        price_html += '<span class="price-old">%s</span>' % fmt_price(p["old_price"])

    btn_attrs = 'data-add-to-cart="%d"' % p["id"]
    btn_disabled = ""
    btn_label = "Додати в кошик"
    if not p["in_stock"]:
        btn_disabled = " disabled"
        btn_label = "Немає в наявності"

    loading_attr = ' loading="lazy"' if lazy else ""

    return """<article class="product-card" data-product-card data-price="%(price)s" data-instock="%(instock)s">
  %(badge)s
  <a class="product-media" href="%(prefix)s%(url)s" tabindex="-1" aria-hidden="true">
    <img src="%(prefix)s%(image)s" width="600" height="600" alt="%(name)s - %(cat)s Felicity"%(loading)s>
  </a>
  <p class="product-cat"><a href="%(prefix)scategory/%(cat_slug)s/">%(cat)s</a></p>
  <h3 class="product-title"><a href="%(prefix)s%(url)s">%(name)s</a></h3>
  <div class="product-price">%(price_html)s</div>
  <button type="button" class="btn btn-primary btn-block" %(btn_attrs)s%(btn_disabled)s>%(btn_label)s</button>
</article>""" % {
        "price": p["price"],
        "instock": "true" if p["in_stock"] else "false",
        "badge": badge,
        "prefix": prefix,
        "url": p["url"],
        "image": p["image"],
        "loading": loading_attr,
        "name": p["name"],
        "cat": CATEGORIES[p["category"]]["name"],
        "cat_slug": p["category"],
        "price_html": price_html,
        "btn_attrs": btn_attrs,
        "btn_disabled": btn_disabled,
        "btn_label": btn_label,
    }


def svg_placeholder(text, bg, accent):
    words = textwrap.wrap(text, width=18)[:4]
    lines = []
    start_y = 300 - (len(words) - 1) * 16
    for i, w in enumerate(words):
        lines.append('<text x="300" y="%d" font-family="Arial, sans-serif" font-size="24" fill="#1a2233" text-anchor="middle">%s</text>' % (start_y + i * 32, w))
    icon = '<circle cx="300" cy="180" r="60" fill="%s" opacity="0.18"/><path d="M312 140 L268 210 L296 210 L284 240 L332 172 L302 172 Z" fill="%s"/>' % (accent, accent)
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600" role="img" aria-label="%s">
<rect width="600" height="600" fill="%s"/>
%s
%s
</svg>""" % (text.replace('"', "'"), bg, icon, "\n".join(lines))


def generate_placeholder_images():
    real_photo_count = 0
    products_with_photos = 0
    for p in PRODUCTS:
        if p["images"][0].endswith(".svg"):
            svg = svg_placeholder(p["name"], "#eef2f7", "#ed6f20")
            write_file(p["image"], svg)
        else:
            src_dir = os.path.join(PRODUCT_PHOTOS_DIR, p["slug"])
            dst_dir = os.path.join(ROOT, "img", p["slug"])
            os.makedirs(dst_dir, exist_ok=True)
            for fn in os.listdir(src_dir):
                shutil.copyfile(os.path.join(src_dir, fn), os.path.join(dst_dir, fn))
            real_photo_count += len(p["images"])
            products_with_photos += 1
    write_file("img/og-default.svg", svg_placeholder("Felicity - сонячна енергетика", "#f7f9fc", "#ff8a3d"))
    write_file("img/favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="16" fill="#ed6f20"/><path d="M17.5 6 9 18h6l-1.5 8L23 14h-6l0.5-8z" fill="#06210f"/></svg>')
    print("Generated %d real product photos across %d products + %d placeholder images + favicon/og-default." % (
        real_photo_count, products_with_photos, len(PRODUCTS) - products_with_photos))


print("Card + image helpers loaded.")

# ---------------------------------------------------------------------------
# products.js (client-side data used by search, cart, catalog.js)
# ---------------------------------------------------------------------------

def gen_products_js():
    slim = []
    for p in PRODUCTS:
        slim.append({
            "id": p["id"], "sku": p["sku"], "slug": p["slug"], "name": p["name"], "category": p["category"],
            "categoryName": CATEGORIES[p["category"]]["name"], "price": p["price"],
            "oldPrice": p["old_price"], "discount": p["discount"], "inStock": p["in_stock"],
            "image": p["image"], "url": p["url"], "specs": p["specs"],
        })
    content = "/* Felicity - product catalog data, generated from generate.py. Do not hand-edit. */\n"
    content += "window.FELICITY_PRODUCTS = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    content += "window.FELICITY_FORM_ENDPOINT = " + json.dumps(FORM_ENDPOINT_URL) + ";\n"
    write_file("js/products.js", content)
    print("Wrote js/products.js")


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------

HERO_BANNERS = [
    "img/hero-banner-1.jpg",
    "img/hero-banner-2.jpg",
]


def gen_index():
    _cat_names = [CATEGORIES[s]["name"] for s in CATEGORY_ORDER]
    if len(_cat_names) > 1:
        cat_list_str = ", ".join(_cat_names[:-1]) + " та " + _cat_names[-1]
    else:
        cat_list_str = _cat_names[0] if _cat_names else "обладнання"

    banner_imgs = "\n      ".join(
        '<img class="hero-banner-img%s" src="%s" alt="" loading="%s">' % (
            " active" if i == 0 else "", src, "eager" if i == 0 else "lazy",
        )
        for i, src in enumerate(HERO_BANNERS)
    )

    sections = []
    for slug in CATEGORY_ORDER:
        cat = CATEGORIES[slug]
        # Static fallback = first 4 (SEO / no-JS). js/main.js reshuffles a random
        # 4 from the whole category on every page load via [data-home-grid].
        items = [p for p in PRODUCTS if p["category"] == slug][:4]
        cards = "\n".join(product_card_html(p, 0, lazy=True) for p in items)
        sections.append("""
<section class="section" aria-labelledby="home-%(slug)s">
  <div class="container">
    <div class="section-head">
      <h2 id="home-%(slug)s">%(name)s</h2>
      <a class="see-all" href="category/%(slug)s/index.html">Дивитись усі →</a>
    </div>
    <div class="product-grid" data-home-grid="%(slug)s" data-home-count="4">%(cards)s</div>
  </div>
</section>""" % {"slug": slug, "name": cat["name"], "cards": cards})

    body = """
<section class="hero" data-hero-banner>
  <div class="hero-banner-imgs">
      %(banner_imgs)s
  </div>
  <div class="hero-banner-overlay"></div>
  <div class="container hero-inner">
    <span class="hero-eyebrow">Сонячна енергетика Felicity</span>
    <h1>Обладнання Felicity Solar для автономного та резервного живлення дому</h1>
    <p>У каталозі: %(cat_list)s. Доставка по всій Україні.</p>
    <div class="hero-cta">
      <a class="btn btn-primary" href="catalog/index.html">Перейти в каталог</a>
      <a class="btn btn-outline" href="about.html">Про компанію</a>
    </div>
  </div>
</section>
%(sections)s
<section class="section" aria-labelledby="about-heading">
  <div class="container">
    <div class="about-block">
      <h2 id="about-heading">Про Felicity</h2>
      <p>Felicity постачає обладнання Felicity Solar в Україні. Ми постачаємо обладнання для автономних та резервних систем живлення приватних будинків, офісів і невеликих підприємств, надаємо консультації з підбору комплекту обладнання.</p>
      <div class="stat-row">
        <div class="stat"><strong>%(product_count)d+</strong><span>моделей обладнання</span></div>
        <div class="stat"><strong>24</strong><span>області доставки</span></div>
        <div class="stat"><strong>100%%</strong><span>оригінальне обладнання</span></div>
      </div>
    </div>
  </div>
</section>
""" % {"sections": "".join(sections), "product_count": len(PRODUCTS), "cat_list": cat_list_str, "banner_imgs": banner_imgs}

    html = page(
        title="Felicity - обладнання Felicity Solar в Україні | Інвертори та акумулятори",
        meta_desc="Felicity - обладнання Felicity Solar в Україні: гібридні інвертори та акумулятори LiFePO4. Доставка по всій країні.",
        canonical_path="/",
        depth=0,
        body_html=body,
        json_ld_blocks=[organization_ld()],
    )
    write_file("index.html", html)
    print("Wrote index.html")


# ---------------------------------------------------------------------------
# Category pages + catalog/all
# ---------------------------------------------------------------------------

def filters_html():
    return """<aside class="filters" aria-label="Фільтри товарів">
  <h2>Фільтри</h2>
  <div class="filter-group">
    <label for="price-min">Ціна, ₴</label>
    <div class="price-range">
      <input type="number" id="price-min" data-price-min placeholder="Від" min="0">
      <input type="number" id="price-max" data-price-max placeholder="До" min="0">
    </div>
  </div>
  <div class="filter-group">
    <label class="checkbox-row"><input type="checkbox" data-instock-only> Тільки в наявності</label>
  </div>
</aside>"""


def toolbar_html():
    return """<div class="catalog-toolbar">
  <p class="result-count"><span data-result-count>0</span> товарів знайдено</p>
  <label class="visually-hidden" for="sort-select">Сортування</label>
  <select id="sort-select" data-sort>
    <option value="default">За популярністю</option>
    <option value="price-asc">Спочатку дешевші</option>
    <option value="price-desc">Спочатку дорожчі</option>
  </select>
</div>"""


def gen_category_pages():
    for slug in CATEGORY_ORDER:
        cat = CATEGORIES[slug]
        items = [p for p in PRODUCTS if p["category"] == slug]
        cards = "\n".join(product_card_html(p, 2, lazy=True) for p in items)
        breadcrumbs = [("Головна", "/"), (cat["name"], "/category/%s/" % slug)]

        body = """
%(breadcrumbs)s
<div class="container">
  <h1>%(name)s</h1>
  <p>%(intro)s</p>
  <div class="catalog-layout">
    %(filters)s
    <div class="catalog-main">
      %(toolbar)s
      <div class="product-grid" data-product-grid>%(cards)s</div>
      <p class="empty-state" data-empty-state style="display:none">За вашим запитом товарів не знайдено. Спробуйте змінити фільтри.</p>
    </div>
  </div>
</div>""" % {
            "breadcrumbs": render_breadcrumbs(breadcrumbs, 2),
            "name": cat["name"], "intro": cat["intro"],
            "filters": filters_html(), "toolbar": toolbar_html(), "cards": cards,
        }

        item_list_ld = json_ld({
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": abs_url(p["url"]), "name": p["name"]}
                for i, p in enumerate(items)
            ],
        })

        html = page(
            title="%s - купити в Україні | Felicity" % cat["name"],
            meta_desc=cat["meta_desc"],
            canonical_path="/category/%s/" % slug,
            depth=2,
            body_html=body,
            json_ld_blocks=[breadcrumb_ld(breadcrumbs), item_list_ld],
            extra_scripts=["catalog.js"],
        )
        write_file("category/%s/index.html" % slug, html)
    print("Wrote %d category pages." % len(CATEGORY_ORDER))


def gen_catalog_all():
    cards = "\n".join(product_card_html(p, 1, lazy=True) for p in PRODUCTS)
    breadcrumbs = [("Головна", "/"), ("Всі товари", "/catalog/")]
    body = """
%(breadcrumbs)s
<div class="container">
  <h1>Всі товари Felicity</h1>
  <p>Каталог гібридних інверторів Felicity Solar в одному місці.</p>
  <div class="catalog-layout">
    %(filters)s
    <div class="catalog-main">
      %(toolbar)s
      <div class="product-grid" data-product-grid>%(cards)s</div>
      <p class="empty-state" data-empty-state style="display:none">За вашим запитом товарів не знайдено. Спробуйте змінити фільтри.</p>
    </div>
  </div>
</div>""" % {
        "breadcrumbs": render_breadcrumbs(breadcrumbs, 1),
        "filters": filters_html(), "toolbar": toolbar_html(), "cards": cards,
    }
    html = page(
        title="Всі товари - каталог Felicity Solar",
        meta_desc="Каталог обладнання Felicity Solar: гібридні інвертори та акумулятори LiFePO4.",
        canonical_path="/catalog/",
        depth=1,
        body_html=body,
        json_ld_blocks=[breadcrumb_ld(breadcrumbs)],
        extra_scripts=["catalog.js"],
    )
    write_file("catalog/index.html", html)
    print("Wrote catalog/index.html")


print("Page generators (index/category) loaded.")

# ---------------------------------------------------------------------------
# Product pages
# ---------------------------------------------------------------------------

def gen_product_pages():
    for p in PRODUCTS:
        cat = CATEGORIES[p["category"]]
        breadcrumbs = [("Головна", "/"), (cat["name"], "/category/%s/" % p["category"]), (p["name"], "/" + p["url"])]

        specs_rows = "\n".join('<tr><th>%s</th><td>%s</td></tr>' % (k, v) for k, v in p["specs"])

        if p["in_stock"]:
            stock_html = '<span class="stock-badge stock-in">В наявності</span>'
        else:
            stock_html = '<span class="stock-badge stock-out">Немає в наявності</span>'

        price_html = '<span class="price-current">%s</span>' % fmt_price(p["price"])
        if p["old_price"]:
            price_html += '<span class="price-old">%s</span>' % fmt_price(p["old_price"])
            price_html += '<span class="badge badge-sale">-%d%%</span>' % p["discount"]

        if p["in_stock"]:
            cta = """<div class="qty-row">
        <div class="qty-input" data-product-qty-wrap>
          <button type="button" data-qty-decr aria-label="Зменшити кількість">−</button>
          <input type="number" min="1" value="1" data-product-qty aria-label="Кількість">
          <button type="button" data-qty-incr aria-label="Збільшити кількість">+</button>
        </div>
        <button type="button" class="btn btn-primary" data-add-to-cart="%d">Додати в кошик</button>
      </div>""" % p["id"]
        else:
            cta = '<div class="qty-row"><button type="button" class="btn btn-primary" disabled>Немає в наявності</button></div>'

        extra_images = p["images"][1:]
        thumbs_html = ""
        nav_html = ""
        counter_html = ""
        if extra_images:
            thumbs = "\n".join(
                '<button type="button" class="gallery-thumb%(active)s" data-gallery-thumb data-src="../../%(img)s" aria-label="Фото %(i)d">'
                '<img src="../../%(img)s" loading="lazy" alt="%(name)s - фото %(i)d">'
                '</button>' % {"active": " active" if i == 1 else "", "img": img, "name": p["name"], "i": i}
                for i, img in enumerate(p["images"], start=1)
            )
            thumbs_html = '<div class="gallery-thumbs" data-gallery-thumbs>%s</div>' % thumbs
            nav_html = (
                '<button type="button" class="gallery-nav gallery-nav-prev" data-gallery-prev aria-label="Попереднє фото">‹</button>'
                '<button type="button" class="gallery-nav gallery-nav-next" data-gallery-next aria-label="Наступне фото">›</button>'
            )
            counter_html = '<span class="gallery-counter" data-gallery-counter>1 / %d</span>' % len(p["images"])

        body = """
%(breadcrumbs)s
<div class="container">
  <div class="product-page">
    <div class="gallery-col" data-gallery>
      <div class="gallery-main">
        <img src="%(image)s" width="600" height="600" alt="%(name)s - фото товару Felicity" data-gallery-main>
        %(nav)s
        %(counter)s
      </div>
      %(thumbs)s
    </div>
    <div class="product-info">
      <p class="product-cat"><a href="../../category/%(cat_slug)s/">%(cat_name)s</a></p>
      <h1>%(name)s</h1>
      <div class="product-meta">%(stock)s<span class="product-sku">Артикул: %(sku)s</span></div>
      <div class="price-block">%(price_html)s</div>
      %(cta)s
      <p>%(desc)s</p>
      <h2>Характеристики</h2>
      <table class="specs-table">%(specs)s</table>
    </div>
  </div>
</div>""" % {
            "breadcrumbs": render_breadcrumbs(breadcrumbs, 2),
            "image": "../../" + p["image"],
            "thumbs": thumbs_html, "nav": nav_html, "counter": counter_html,
            "name": p["name"], "cat_slug": p["category"], "cat_name": cat["name"],
            "stock": stock_html, "price_html": price_html, "cta": cta,
            "desc": p["desc"], "specs": specs_rows, "sku": p["sku"],
        }

        product_ld = json_ld({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p["name"],
            "description": p["desc"],
            "sku": p["sku"],
            "image": [abs_url(p["image"])],
            "brand": {"@type": "Brand", "name": "Felicity Solar"},
            "offers": {
                "@type": "Offer",
                "url": abs_url(p["url"]),
                "priceCurrency": "UAH",
                "price": str(p["price"]),
                "availability": "https://schema.org/InStock" if p["in_stock"] else "https://schema.org/OutOfStock",
                "itemCondition": "https://schema.org/NewCondition",
            },
        })

        html = page(
            title="%s купити в Україні - ціна %s | Felicity" % (p["name"], fmt_price(p["price"])),
            meta_desc="%s Ціна %s. %s" % (p["name"], fmt_price(p["price"]), p["desc"][:120]),
            canonical_path="/" + p["url"],
            depth=2,
            body_html=body,
            json_ld_blocks=[breadcrumb_ld(breadcrumbs), product_ld],
            og_image=p["image"],
        )
        write_file(p["url"] + "index.html", html)
    print("Wrote %d product pages." % len(PRODUCTS))


print("Product page generator loaded.")

# ---------------------------------------------------------------------------
# Static content pages
# ---------------------------------------------------------------------------

def gen_static_pages():
    pages = {}

    pages["about"] = dict(
        title="Про нас - Felicity | Сонячна енергетика в Україні",
        meta_desc="Felicity - обладнання Felicity Solar в Україні. Дізнайтеся більше про компанію.",
        h1="Про компанію Felicity",
        body="""
<div class="content-page">
  <p>Felicity постачає обладнання Felicity Solar в Україні. Ми постачаємо гібридні інвертори та акумулятори для приватних будинків, дач та невеликого бізнесу.</p>
  <h2>Чому обирають нас</h2>
  <div class="info-cards">
    <div class="info-card"><h3>Оригінальне обладнання</h3><p>Прямі поставки від виробника.</p></div>
    <div class="info-card"><h3>Консультація з підбору</h3><p>Допомагаємо розрахувати потужність та ємність системи під ваші потреби.</p></div>
    <div class="info-card"><h3>Доставка по Україні</h3><p>Відправляємо замовлення в будь-яке місто через основні служби доставки.</p></div>
  </div>
  <h2>Наша місія</h2>
  <p>Робити автономну та відновлювану енергетику доступною для кожного українського домогосподарства - від невеликого резервного живлення до повноцінної сонячної електростанції.</p>
</div>""",
    )

    pages["delivery"] = dict(
        title="Доставка - Felicity | Умови та терміни доставки",
        meta_desc="Умови доставки обладнання Felicity по Україні: Нова пошта, Укрпошта, кур'єрська доставка. Терміни та вартість.",
        h1="Доставка",
        body="""
<div class="content-page">
  <p>Ми відправляємо замовлення по всій Україні через провідні служби доставки протягом 1-2 робочих днів після підтвердження замовлення.</p>
  <h2>Способи доставки</h2>
  <ul>
    <li>Відділення «Нової пошти» - 1-3 дні залежно від регіону</li>
    <li>Кур'єром «Нової пошти» до дверей</li>
    <li>Укрпоштою - для віддалених населених пунктів</li>
  </ul>
  <h2>Вартість</h2>
  <p>Вартість доставки розраховується транспортною компанією за тарифами перевізника та оплачується отримувачем при отриманні, якщо інше не погоджено окремо.</p>
</div>""",
    )

    pages["payment"] = dict(
        title="Оплата - Felicity | Способи оплати замовлення",
        meta_desc="Способи оплати товарів Felicity: безготівковий розрахунок для юридичних осіб, оплата при отриманні.",
        h1="Оплата",
        body="""
<div class="content-page">
  <p>Ми пропонуємо кілька зручних способів оплати замовлень.</p>
  <h2>Доступні способи оплати</h2>
  <ul>
    <li>Безготівковий розрахунок для юридичних осіб (з ПДВ)</li>
    <li>Накладений платіж при отриманні (часткова передоплата)</li>
  </ul>
  <p>Усі платежі захищені та обробляються відповідно до стандартів безпеки платіжних систем.</p>
</div>""",
    )

    pages["partnership"] = dict(
        title="Партнерство - Felicity | Співпраця для монтажників та продавців",
        meta_desc="Партнерська програма Felicity: оптові поставки обладнання Felicity Solar для монтажних компаній та продавців. Заповніть анкету партнера.",
        h1="Партнерство",
        body="""
<div class="content-page">
  <p>Ми співпрацюємо з монтажними компаніями, магазинами та підприємцями, які працюють у сфері сонячної енергетики. Пропонуємо оптові умови на гібридні інвертори й акумулятори Felicity Solar, підтримку з підбору обладнання та гнучкі форми розрахунку.</p>
  <h2>Анкета партнера</h2>
  <p>Заповніть форму нижче - менеджер зв'яжеться з вами для обговорення умов співпраці.</p>
  <form class="form-grid" data-partner-form>
    <div class="form-field"><label for="pt-email">Ваша електронна пошта <span aria-hidden="true">*</span></label><input type="email" id="pt-email" name="email" required></div>
    <div class="form-field"><label for="pt-company">Найменування компанії <span aria-hidden="true">*</span></label><input type="text" id="pt-company" name="company" required></div>
    <div class="form-field"><label for="pt-edrpou">ЄДРПОУ / реєстраційний код</label><input type="text" id="pt-edrpou" name="edrpou"></div>
    <div class="form-field"><label for="pt-direction">Напрямок Вашої діяльності <span aria-hidden="true">*</span></label>
      <select id="pt-direction" name="direction" required>
        <option value="" disabled selected>- оберіть -</option>
        <option>Монтаж/установка обладнання</option>
        <option>Реалізація/продаж</option>
        <option>Монтаж і продаж одночасно</option>
        <option>Інше</option>
      </select>
    </div>
    <div class="form-field"><label for="pt-region">У якому регіоні Ви працюєте? <span aria-hidden="true">*</span></label><input type="text" id="pt-region" name="region" required></div>
    <div class="form-field"><label for="pt-website">Посилання на сайт компанії</label><input type="url" id="pt-website" name="website" placeholder="https://"></div>
    <div class="form-field"><label for="pt-manufacturers">З якими виробниками найчастіше працюєте? <span aria-hidden="true">*</span></label><input type="text" id="pt-manufacturers" name="manufacturers" placeholder="Напр.: Deye, Must, Felicity" required></div>
    <div class="form-field"><label for="pt-payment">Зручні для Вас форми розрахунку? <span aria-hidden="true">*</span></label><input type="text" id="pt-payment" name="payment" required></div>
    <div class="form-field"><label for="pt-volume">Орієнтовний обсяг закупівель на місяць <span aria-hidden="true">*</span></label><input type="text" id="pt-volume" name="volume" required></div>
    <div class="form-field"><label for="pt-experience">З ким із постачальників уже маєте досвід співпраці?</label><input type="text" id="pt-experience" name="experience"></div>
    <div class="form-field"><label for="pt-prepay">Розгляд знижки за умови передоплати та попереднього замовлення - цікавий для Вас варіант? <span aria-hidden="true">*</span></label>
      <select id="pt-prepay" name="prepay_discount" required>
        <option value="" disabled selected>- оберіть -</option>
        <option>Так</option>
        <option>Ні</option>
      </select>
    </div>
    <div class="form-field"><label for="pt-phone">Номер телефону для зв'язку <span aria-hidden="true">*</span></label><input type="tel" id="pt-phone" name="phone" required></div>
    <button type="submit" class="btn btn-primary">Надіслати анкету</button>
    <p class="form-note" data-form-success style="display:none">Дякуємо! Анкету надіслано, ми зв'яжемося з вами найближчим часом.</p>
  </form>
</div>""",
    )

    pages["contact"] = dict(
        title="Контакти - Felicity | Зв'яжіться з нами",
        meta_desc="Контактна інформація Felicity: телефон, email, форма зворотного зв'язку. Ми відповідаємо на запити з понеділка по п'ятницю.",
        h1="Контакти",
        body="""
<div class="content-page">
  <p>Залишились питання щодо підбору обладнання чи вашого замовлення? Зв'яжіться з нами будь-яким зручним способом.</p>
  <div class="info-cards">
    <div class="info-card"><h3>Телефон</h3><p><a href="tel:+380000000000">+38 (0__) ___ __ __</a><br>Пн-Пт, 9:00-18:00</p></div>
    <div class="info-card"><h3>Email</h3><p><a href="mailto:info@felicity.ua">info@felicity.ua</a></p></div>
    <div class="info-card"><h3>Офіс</h3><p>Україна<br>Доставка по всій країні</p></div>
  </div>
  <h2>Форма зворотного зв'язку</h2>
  <form class="form-grid" data-contact-form>
    <div class="form-field"><label for="c-name">Ім'я</label><input type="text" id="c-name" name="name" required></div>
    <div class="form-field"><label for="c-phone">Телефон</label><input type="tel" id="c-phone" name="phone" required></div>
    <div class="form-field"><label for="c-message">Повідомлення</label><textarea id="c-message" name="message" required></textarea></div>
    <button type="submit" class="btn btn-primary">Надіслати</button>
    <p class="form-note" data-form-success style="display:none">Дякуємо! Ваше повідомлення надіслано, ми зв'яжемося з вами найближчим часом.</p>
  </form>
</div>""",
        extra_ld=[local_business_ld()],
    )

    for slug, data in pages.items():
        breadcrumbs = [("Головна", "/"), (data["h1"], "/%s.html" % slug)]
        body = "%s\n<div class=\"container\"><h1>%s</h1>%s</div>" % (render_breadcrumbs(breadcrumbs, 0), data["h1"], data["body"])
        ld_blocks = [breadcrumb_ld(breadcrumbs)] + data.get("extra_ld", [])
        html = page(
            title=data["title"], meta_desc=data["meta_desc"], canonical_path="/%s.html" % slug,
            depth=0, body_html=body, json_ld_blocks=ld_blocks,
        )
        write_file("%s.html" % slug, html)
    print("Wrote %d static pages." % len(pages))


def gen_cart_page():
    breadcrumbs = [("Головна", "/"), ("Кошик", "/cart.html")]
    body = """
%(breadcrumbs)s
<div class="container">
  <h1>Кошик</h1>
  <div data-cart-root></div>
  <aside class="cart-summary" data-cart-summary style="display:none">
    <div class="cart-summary-row"><span>Товарів</span><span data-summary-items>0</span></div>
    <div class="cart-summary-row total"><span>Разом</span><span data-summary-total>0 ₴</span></div>
    <form data-checkout-form>
      <div class="form-field"><label for="ck-name">Ім'я</label><input type="text" id="ck-name" required></div>
      <div class="form-field"><label for="ck-phone">Телефон</label><input type="tel" id="ck-phone" required></div>
      <div class="form-field"><label for="ck-address">Адреса доставки</label><input type="text" id="ck-address" required></div>
      <button type="submit" class="btn btn-primary btn-block">Оформити замовлення</button>
      <p class="form-note">Це демонстраційна форма - реальна оплата не здійснюється.</p>
    </form>
  </aside>
</div>""" % {"breadcrumbs": render_breadcrumbs(breadcrumbs, 0)}
    html = page(
        title="Кошик - Felicity",
        meta_desc="Кошик покупок Felicity: перегляньте обрані товари, змініть кількість та оформіть замовлення.",
        canonical_path="/cart.html",
        depth=0,
        body_html=body,
        json_ld_blocks=[breadcrumb_ld(breadcrumbs)],
        robots="noindex, follow",
    )
    write_file("cart.html", html)
    print("Wrote cart.html")


# ---------------------------------------------------------------------------
# robots.txt + sitemap.xml
# ---------------------------------------------------------------------------

def gen_robots_sitemap():
    write_file("robots.txt", "User-agent: *\nAllow: /\nDisallow: /cart.html\n\nSitemap: %s/sitemap.xml\n" % BASE_URL)

    urls = ["/", "/catalog/"] + ["/category/%s/" % s for s in CATEGORY_ORDER]
    urls += ["/" + p["url"] for p in PRODUCTS]
    urls += ["/%s.html" % slug for slug, _ in STATIC_PAGES]

    entries = "\n".join(
        "  <url><loc>%s</loc><changefreq>%s</changefreq><priority>%s</priority></url>" % (
            abs_url(u),
            "daily" if u in ("/", "/catalog/") else "weekly",
            "1.0" if u == "/" else ("0.8" if u.startswith("/category/") or u.startswith("/product/") or u == "/catalog/" else "0.5"),
        )
        for u in urls
    )
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % entries
    write_file("sitemap.xml", sitemap)
    print("Wrote robots.txt and sitemap.xml with %d URLs." % len(urls))


def gen_price_sheet_template():
    import csv
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Артикул", "Модель", "Назва", "Ціна", "В наявності"])
    for p in PRODUCTS:
        writer.writerow([
            p["sku"], p["code"], p["name"],
            int(p["price"]) if p["price"] else 0,
            "так" if p["in_stock"] else "ні",
        ])
    write_file("price-sheet-template.csv", buf.getvalue())
    print("Wrote price-sheet-template.csv (%d rows) - import this into Google Sheets." % len(PRODUCTS))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    generate_placeholder_images()
    gen_products_js()
    gen_index()
    gen_category_pages()
    gen_catalog_all()
    gen_product_pages()
    gen_static_pages()
    gen_cart_page()
    gen_robots_sitemap()
    gen_price_sheet_template()
    print("\nDone. Site generated in", ROOT)


if __name__ == "__main__":
    main()
