import streamlit as st
import pandas as pd
from datetime import date,  timedelta
import time
import zipfile
import io
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode





# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Milk Accounting Pro", layout="wide", initial_sidebar_state="expanded")
if "css_loaded" not in st.session_state:
    st.session_state["css_loaded"] = True
    st.markdown("""
<style>
:root{
  --bg: #F6F7FB;
  --card: rgba(255,255,255,0.92);
  --text: #0F172A;
  --muted: #64748B;
  --border: rgba(15, 23, 42, 0.10);
  --shadow: 0 10px 30px rgba(2, 6, 23, 0.08);
  --shadow2: 0 6px 18px rgba(2, 6, 23, 0.08);
  --radius: 18px;
  --primary: #22C55E;
  --primary2: #16A34A;
}

.stApp {
  background: radial-gradient(1000px 600px at 10% 0%, rgba(34,197,94,0.10), transparent 55%),
              radial-gradient(900px 500px at 90% 10%, rgba(59,130,246,0.08), transparent 55%),
              linear-gradient(180deg, var(--bg) 0%, #EEF2FF 120%);
}

.block-container { padding-top: 1.2rem !important; padding-bottom: 2.5rem !important; }

section[data-testid="stSidebar"]{
  background: rgba(255,255,255,0.75) !important;
  backdrop-filter: blur(10px);
  border-right: 1px solid var(--border);
}

h1,h2,h3,h4 { letter-spacing: -0.02em !important; }
h1 { font-weight: 900 !important; }
h2 { font-weight: 800 !important; }
h3 { color: var(--muted) !important; font-weight: 700 !important; }

.stButton>button{
  background: linear-gradient(180deg, var(--primary) 0%, var(--primary2) 100%) !important;
  color:#fff !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  border-radius: 12px !important;
  padding: 0.65rem 1.05rem !important;
  font-weight: 800 !important;
  box-shadow: 0 10px 18px rgba(34,197,94,0.18) !important;
  transition: transform 0.08s ease, filter 0.12s ease !important;
}
.stButton>button:hover{ filter: brightness(1.03); transform: translateY(-1px); }
.stButton>button:active{ transform: translateY(0px); }

div[data-baseweb="input"]>div,
div[data-baseweb="select"]>div,
div[data-baseweb="textarea"]>div{
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,0.85) !important;
  box-shadow: none !important;
}
label { color: var(--muted) !important; font-weight: 700 !important; }

.stTabs [data-baseweb="tab-list"]{ gap:10px; }
.stTabs [data-baseweb="tab"]{
  background: rgba(255,255,255,0.55) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  padding: 10px 14px !important;
  font-weight: 800 !important;
  color: var(--muted) !important;
}
.stTabs [aria-selected="true"]{
  background: rgba(34,197,94,0.12) !important;
  border: 1px solid rgba(34,197,94,0.35) !important;
  color: var(--text) !important;
}

div[data-testid="stMetric"]{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 16px !important;
  box-shadow: var(--shadow2) !important;
}
div[data-testid="stMetric"] label{ color: var(--muted) !important; font-weight: 800 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"]{
  font-size: 1.65rem !important;
  font-weight: 950 !important;
}

div[data-testid="stDataEditor"]{
  background: var(--card) !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow) !important;
  overflow: hidden !important;
}

details[data-testid="stExpander"]{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow2) !important;
  overflow: hidden !important;
}


hr { border-color: rgba(15,23,42,0.08) !important; }

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
/* DON'T hide the header; it contains the sidebar toggle */
/* header {visibility:hidden;} */

</style>
""", unsafe_allow_html=True)


# Keep same "file names" so your app code doesn't change
RETAILERS_FILE = "data/retailers.csv"
CATEGORIES_FILE = "data/categories.csv"
PRICES_FILE = "data/prices.csv"
ENTRIES_FILE = "data/entries.csv"
PAYMENTS_FILE = "data/payments.csv"
DISTRIBUTORS_FILE = "data/distributors.csv"
DISTRIBUTOR_PURCHASES_FILE = "data/distributor_purchases.csv"
DISTRIBUTOR_PAYMENTS_FILE = "data/distributor_payments.csv"
DISTRIBUTOR_CATEGORY_MAP_FILE = "data/distributor_category_map.csv"
WASTAGE_FILE = "data/wastage.csv"
EXPENSES_FILE = "data/expenses.csv"

GLOBAL_RETAILER_ID = 0

FILE_TO_TABLE = {
    RETAILERS_FILE: ("retailers", "retailer_id"),
    CATEGORIES_FILE: ("categories", "category_id"),
    PRICES_FILE: ("prices", "price_id"),
    ENTRIES_FILE: ("entries", "entry_id"),
    PAYMENTS_FILE: ("payments", "payment_id"),
    DISTRIBUTORS_FILE: ("distributors", "distributor_id"),
    DISTRIBUTOR_PURCHASES_FILE: ("distributor_purchases", "purchase_id"),
    DISTRIBUTOR_PAYMENTS_FILE: ("distributor_payments", "payment_id"),
    DISTRIBUTOR_CATEGORY_MAP_FILE: ("distributor_category_map", "map_id"),
    WASTAGE_FILE: ("wastage", "wastage_id"),
    EXPENSES_FILE: ("expenses", "expense_id"),
}

@st.cache_resource
def get_sb():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

    return create_client(url, key)

if st.sidebar.button("🔌 Test DB Connection"):
    try:
        sb.table("retailers").select("retailer_id").limit(1).execute()
        st.sidebar.success("Supabase connected ✅")
    except Exception as e:
        st.sidebar.error(f"Connection failed ❌\n{e}")



# ================== CACHE INVALIDATION (PERFORMANCE) ==================
st.session_state.setdefault("data_version", 0)
st.session_state.setdefault("daily_save_lock", False)
def invalidate_data_cache():
    st.session_state["data_version"] += 1

def make_range_backup_csv(
    start_date,
    end_date,
    retailers,
    categories,
    entries,
    payments,
    dist_purchases,
    dist_payments,
    distributors,
):
    """
    SAFE VERSION
    - Uses csv.writer (fixes corrupted CSV structure)
    - Prevents bad IDs becoming 0
    - Properly escapes commas/quotes/newlines
    - Stable Excel-compatible export
    """

    import io
    import csv
    import pandas as pd

    output = io.StringIO()
    writer = csv.writer(output)

    PAYMENT_MODES = ["Cash", "UPI", "Bank", "Cheque", "Other"]

    # FIX: payment_mode strings in the DB use mixed case (e.g. "UPI", "upi",
    # "Cash", "BANK", …). The original code used `.str.title()` which turned
    # "UPI" into "Upi" — that no longer matched the `PAYMENT_MODES` keys, so
    # everything fell through to the Cash bucket. Use a case-insensitive map
    # against an uppercase canonical key.
    _PM_CANON = {m.upper(): m for m in PAYMENT_MODES}

    def _canon_mode(v):
        s = str(v or "").strip().upper()
        return _PM_CANON.get(s, "Cash")

    # =========================================================
    # HELPERS
    # =========================================================

    def _to_date(df, col="date"):
        if df is None or df.empty or col not in df.columns:
            return pd.DataFrame()

        df = df.copy()
        # FIX: force string format so comparisons with `d` (also string) always work.
        df[col] = (
            pd.to_datetime(df[col], errors="coerce")
            .dt.strftime("%Y-%m-%d")
        )
        return df

    def _num(df, cols):
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()

        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(
                    df[c],
                    errors="coerce"
                ).fillna(0.0)

        return df

    # =========================================================
    # NORMALIZE INPUTS
    # =========================================================

    entries = _to_date(entries)
    payments = _to_date(payments)
    dist_purchases = _to_date(dist_purchases)
    dist_payments = _to_date(dist_payments)

    if not entries.empty:
        entries = _num(
            entries,
            ["retailer_id", "category_id", "qty", "amount"]
        )

    if not payments.empty:
        payments = _num(
            payments,
            ["retailer_id", "amount"]
        )

    if not dist_purchases.empty:
        dist_purchases = _num(
            dist_purchases,
            ["distributor_id", "category_id", "qty", "amount"]
        )

    if not dist_payments.empty:
        dist_payments = _num(
            dist_payments,
            ["distributor_id", "amount"]
        )

        if "payment_mode" in dist_payments.columns:
            # FIX: use case-insensitive canonical mapping (was .str.title() which
            # broke "UPI" → "Upi" and silently routed UPI/Bank/Cheque to "Cash").
            dist_payments["payment_mode"] = (
                dist_payments["payment_mode"]
                .fillna("Cash")
                .astype(str)
                .map(_canon_mode)
            )

    # =========================================================
    # RETAILERS
    # =========================================================

    retailers = retailers.copy()

    retailers["retailer_id"] = pd.to_numeric(
        retailers["retailer_id"],
        errors="coerce"
    )

    retailers = retailers.dropna(subset=["retailer_id"])

    retailers["retailer_id"] = retailers["retailer_id"].astype(int)

    retailers["name"] = (
        retailers["name"]
        .fillna("")
        .astype(str)
    )

    retailer_list = (
        retailers[["retailer_id", "name"]]
        .drop_duplicates("retailer_id")
        .values
        .tolist()
    )

    rid_to_name = {
        int(r[0]): str(r[1])
        for r in retailer_list
    }

    all_rids = [
        int(r[0])
        for r in retailer_list
    ]

    # =========================================================
    # CATEGORIES
    # =========================================================

    categories = categories.copy()

    categories["category_id"] = pd.to_numeric(
        categories["category_id"],
        errors="coerce"
    )

    categories = categories.dropna(subset=["category_id"])

    categories["category_id"] = (
        categories["category_id"]
        .astype(int)
    )

    categories["name"] = (
        categories["name"]
        .fillna("")
        .astype(str)
    )

    cat_list = (
        categories[["category_id", "name"]]
        .drop_duplicates("category_id")
        .values
        .tolist()
    )

    cid_to_name = {
        int(c[0]): str(c[1]).upper()
        for c in cat_list
    }

    all_cids = [
        int(c[0])
        for c in cat_list
    ]

    cat_names = [
        cid_to_name[c]
        for c in all_cids
    ]

    # =========================================================
    # DISTRIBUTORS
    # =========================================================

    distributors = distributors.copy()

    distributors["distributor_id"] = pd.to_numeric(
        distributors["distributor_id"],
        errors="coerce"
    )

    distributors = distributors.dropna(
        subset=["distributor_id"]
    )

    distributors["distributor_id"] = (
        distributors["distributor_id"]
        .astype(int)
    )

    distributors["name"] = (
        distributors["name"]
        .fillna("")
        .astype(str)
    )

    dist_list = (
        distributors[["distributor_id", "name"]]
        .drop_duplicates("distributor_id")
        .values
        .tolist()
    )

    did_to_name = {
        int(d[0]): str(d[1]).upper()
        for d in dist_list
    }

    all_dids = [
        int(d[0])
        for d in dist_list
    ]

    # =========================================================
    # DATE RANGE
    # =========================================================

    # FIX: keep dates as strings so they match the strftime'd `date` columns above.
    _start_str = pd.to_datetime(start_date, errors="coerce").strftime("%Y-%m-%d")
    _end_str = pd.to_datetime(end_date, errors="coerce").strftime("%Y-%m-%d")

    all_dates = pd.date_range(
        start_date,
        end_date,
        freq="D"
    ).strftime("%Y-%m-%d")

    # =========================================================
    # OPENING BALANCES
    # =========================================================

    def _opening_retailer(rid):

        e_before = (
            entries.loc[
                (
                    entries["retailer_id"].astype(int) == rid
                )
                &
                (
                    entries["date"] < _start_str
                ),
                "amount"
            ].sum()
            if not entries.empty
            else 0.0
        )

        p_before = (
            payments.loc[
                (
                    payments["retailer_id"].astype(int) == rid
                )
                &
                (
                    payments["date"] < _start_str
                ),
                "amount"
            ].sum()
            if not payments.empty
            else 0.0
        )

        return round(
            float(e_before - p_before),
            2
        )

    def _opening_distributor(did):

        d_before = (
            dist_purchases.loc[
                (
                    dist_purchases["distributor_id"].astype(int) == did
                )
                &
                (
                    dist_purchases["date"] < _start_str
                ),
                "amount"
            ].sum()
            if not dist_purchases.empty
            else 0.0
        )

        p_before = (
            dist_payments.loc[
                (
                    dist_payments["distributor_id"].astype(int) == did
                )
                &
                (
                    dist_payments["date"] < _start_str
                ),
                "amount"
            ].sum()
            if not dist_payments.empty
            else 0.0
        )

        return round(
            float(d_before - p_before),
            2
        )

    retailer_running = {
        rid: _opening_retailer(rid)
        for rid in all_rids
    }

    dist_running = {
        did: _opening_distributor(did)
        for did in all_dids
    }

    # =========================================================
    # HEADERS
    # =========================================================

    r_header = (
        ["Retailer"]
        + cat_names
        + ["Total L", "Total ₹"]
        + PAYMENT_MODES
        + ["Previous", "Ledger"]
    )

    d_header = (
        ["Distributor"]
        + cat_names
        + ["Total L", "Total ₹", "Payment", "Previous", "Ledger"]
    )

    gap = ["", ""]

    full_header = r_header + gap + d_header

    # =========================================================
    # MAIN LOOP
    # =========================================================

    for d in all_dates:

        writer.writerow([f"DATE : {d}"])
        writer.writerow([])

        writer.writerow(full_header)

        e_day = (
            entries.loc[entries["date"] == d].copy()
            if not entries.empty
            else pd.DataFrame()
        )

        p_day = (
            payments.loc[payments["date"] == d].copy()
            if not payments.empty
            else pd.DataFrame()
        )

        dp_day = (
            dist_purchases.loc[
                dist_purchases["date"] == d
            ].copy()
            if not dist_purchases.empty
            else pd.DataFrame()
        )

        dpay_day = (
            dist_payments.loc[
                dist_payments["date"] == d
            ].copy()
            if not dist_payments.empty
            else pd.DataFrame()
        )

        # =====================================================
        # RETAILERS
        # =====================================================

        retailer_rows = []

        for rid in all_rids:

            rname = rid_to_name.get(rid, str(rid))

            cat_qtys = []
            total_l = 0.0

            for cid in all_cids:

                if e_day.empty:
                    qty = 0.0
                else:
                    sub = e_day.loc[
                        (
                            e_day["retailer_id"].astype(int) == rid
                        )
                        &
                        (
                            e_day["category_id"].astype(int) == cid
                        )
                    ]

                    qty = (
                        round(float(sub["qty"].sum()), 3)
                        if not sub.empty
                        else 0.0
                    )

                cat_qtys.append(qty)
                total_l += qty

            total_l = round(total_l, 3)

            total_rs = (
                round(
                    float(
                        e_day.loc[
                            e_day["retailer_id"].astype(int) == rid,
                            "amount"
                        ].sum()
                    ),
                    2
                )
                if not e_day.empty
                else 0.0
            )

            mode_amts = {
                m: 0.0
                for m in PAYMENT_MODES
            }

            if not p_day.empty:

                r_pay = p_day.loc[
                    p_day["retailer_id"].astype(int) == rid
                ].copy()

                if not r_pay.empty:

                    # FIX: case-insensitive canonical mapping (see _canon_mode
                    # at top of function). The previous .str.title() call
                    # converted "UPI" → "Upi" which never matched the
                    # PAYMENT_MODES keys, so all non-Cash modes were silently
                    # added to the Cash bucket.
                    r_pay["payment_mode"] = (
                        r_pay.get(
                            "payment_mode",
                            pd.Series(dtype=str)
                        )
                        .fillna("Cash")
                        .astype(str)
                        .map(_canon_mode)
                    )

                    for _, row in r_pay.iterrows():

                        pm = _canon_mode(row.get("payment_mode", "Cash"))

                        amt = round(
                            float(
                                row.get("amount", 0.0)
                            ),
                            2
                        )

                        # pm is always a valid key thanks to _canon_mode.
                        mode_amts[pm] += amt

            total_pay = round(
                sum(mode_amts.values()),
                2
            )

            prev_ledger = round(
                float(retailer_running[rid]),
                2
            )

            close_ledger = round(
                prev_ledger + total_rs - total_pay,
                2
            )

            retailer_running[rid] = close_ledger

            retailer_rows.append(
                [rname]
                + cat_qtys
                + [
                    total_l,
                    total_rs
                ]
                + [
                    mode_amts[m]
                    for m in PAYMENT_MODES
                ]
                + [
                    prev_ledger,
                    close_ledger
                ]
            )

        # =====================================================
        # DISTRIBUTORS
        # =====================================================

        dist_rows = []

        for did in all_dids:

            dname = did_to_name.get(did, str(did))

            cat_qtys = []
            total_l = 0.0

            for cid in all_cids:

                if dp_day.empty:
                    qty = 0.0
                else:
                    sub = dp_day.loc[
                        (
                            dp_day["distributor_id"].astype(int) == did
                        )
                        &
                        (
                            dp_day["category_id"].astype(int) == cid
                        )
                    ]

                    qty = (
                        round(float(sub["qty"].sum()), 3)
                        if not sub.empty
                        else 0.0
                    )

                cat_qtys.append(qty)
                total_l += qty

            total_l = round(total_l, 3)

            total_rs = (
                round(
                    float(
                        dp_day.loc[
                            dp_day["distributor_id"].astype(int) == did,
                            "amount"
                        ].sum()
                    ),
                    2
                )
                if not dp_day.empty
                else 0.0
            )

            total_pay = (
                round(
                    float(
                        dpay_day.loc[
                            dpay_day["distributor_id"].astype(int) == did,
                            "amount"
                        ].sum()
                    ),
                    2
                )
                if not dpay_day.empty
                else 0.0
            )

            prev_ledger = round(
                float(dist_running[did]),
                2
            )

            close_ledger = round(
                prev_ledger + total_rs - total_pay,
                2
            )

            dist_running[did] = close_ledger

            dist_rows.append(
                [dname]
                + cat_qtys
                + [
                    total_l,
                    total_rs,
                    total_pay,
                    prev_ledger,
                    close_ledger
                ]
            )

        # =====================================================
        # WRITE ROWS
        # =====================================================

        max_rows = max(
            len(retailer_rows),
            len(dist_rows)
        )

        empty_r = [""] * len(r_header)
        empty_d = [""] * len(d_header)

        for i in range(max_rows):

            r_row = (
                retailer_rows[i]
                if i < len(retailer_rows)
                else empty_r
            )

            d_row = (
                dist_rows[i]
                if i < len(dist_rows)
                else empty_d
            )

            combined = r_row + gap + d_row

            writer.writerow(combined)

        writer.writerow([])
        writer.writerow([])

    return output.getvalue().encode("utf-8")
    
def make_full_backup_zip(data_version: int) -> bytes:
    """
    FIXED: Uses same processed pipeline as app
    DOES NOT break existing structure
    """

    _ = data_version

    # ✅ USE CENTRAL DATA LOADER (already used in app)
    (
        retailers,
        categories,
        prices,
        entries,
        payments,
        distributors,
        dist_purchases,
        dist_payments,
        dist_cat_map,
        wastage,
        expenses,
    ) = load_all_data(data_version)

    # ✅ ADD LEDGER (missing earlier)
    ledger_df = compute_ledger_fast(entries, payments)

    # ✅ KEEP SAME TABLE NAMES (no break)
    tables = {
        "retailers": retailers,
        "categories": categories,
        "prices": prices,
        "entries": entries,
        "payments": payments,
        "distributors": distributors,
        "distributor_purchases": dist_purchases,
        "distributor_payments": dist_payments,
        "distributor_category_map": dist_cat_map,
        "wastage": wastage,
        "expenses": expenses,
        "ledger": ledger_df,  # ✅ NEW (safe addition)
    }

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, df in tables.items():
            if isinstance(df, pd.DataFrame):
                zf.writestr(
                    f"{name}.csv",
                    df.to_csv(index=False).encode("utf-8")
                )

    return buf.getvalue()

def _secret_bool(key: str, default: bool = False) -> bool:
    try:
        raw = st.secrets["supabase"].get(key, default)
    except Exception:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(raw)

# Toggle DB-assigned IDs and server-side filtering via secrets if desired.
USE_DB_IDS = False
USE_SERVER_FILTERS = True
if not USE_SERVER_FILTERS:
    st.warning('⚠️ App is running in LOCAL CSV mode. If you delete data in Supabase, it will not reflect here. Turn on Supabase mode in secrets (use_server_filters=True).')
# ================== SCHEMAS ==================
CSV_SCHEMAS = {
    RETAILERS_FILE: ["retailer_id", "name", "contact", "address", "zone", "is_active"],
    CATEGORIES_FILE: ["category_id", "name", "description", "default_price", "is_active"],
    PRICES_FILE: ["price_id", "retailer_id", "category_id", "price", "effective_date"],
    ENTRIES_FILE: ["entry_id", "date", "retailer_id", "category_id", "qty", "rate", "amount"],
    PAYMENTS_FILE: ["payment_id", "date", "retailer_id", "amount", "payment_mode", "note"],
    DISTRIBUTORS_FILE: ["distributor_id", "name", "contact", "address", "is_active"],
    DISTRIBUTOR_PURCHASES_FILE: ["purchase_id", "date", "distributor_id", "category_id", "qty", "rate", "amount"],
    DISTRIBUTOR_PAYMENTS_FILE: ["payment_id", "date", "distributor_id", "amount", "payment_mode", "note"],
    DISTRIBUTOR_CATEGORY_MAP_FILE: ["map_id", "distributor_id", "category_id", "is_active"],
    WASTAGE_FILE: ["wastage_id", "date", "category_id", "qty", "reason", "estimated_loss"],
    EXPENSES_FILE: ["expense_id", "date", "category", "description", "amount", "payment_mode", "paid"],
}

# legacy columns allowed to be missing in old CSVs (in-memory only, no write on startup)
ALLOWED_LEGACY_MISSING = {
    RETAILERS_FILE: {"zone", "is_active", "contact", "address"},
    CATEGORIES_FILE: {"description", "default_price", "is_active"},
    DISTRIBUTORS_FILE: {"contact", "address", "is_active"},
}

# ================== HELPERS ==================
def _is_missingish(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() in ("nan", "none", "-", "–")

def _disp_2dec_or_dash(v, dash="–") -> str:
    """Show number with 2 decimals, else dash. 0 => dash (matches your UI logic)."""
    if _is_missingish(v):
        return dash
    try:
        fv = float(v)
        return dash if fv == 0 else f"{fv:.2f}"
    except Exception:
        return dash

def _disp_rate_or_dash(v, dash="–") -> str:
    """Rate display: 2 decimals, but keep dash for missing. 0 => dash."""
    return _disp_2dec_or_dash(v, dash=dash)
# ================== DB WRITE HELPERS (SAFE, TARGETED) ==================
def sb_table_for_path(path: str) -> tuple[str, str]:
    if path not in FILE_TO_TABLE:
        raise ValueError(f"Unknown mapping for: {path}")
    return FILE_TO_TABLE[path]


def sb_next_id(table: str, pk: str) -> int:
    """
    Get next integer ID safely from DB (max(pk)+1).
    Prevents collisions across multiple sessions/users.
    """
    sb = get_sb()
    resp = sb.table(table).select(pk).order(pk, desc=True).limit(1).execute()
    data = resp.data or []
    if not data:
        return 1
    try:
        return int(data[0][pk]) + 1
    except Exception:
        return 1


def sb_new_id(table: str, pk: str):
    return sb_next_id(table, pk) if USE_DB_IDS else None


def _safe_dt(s):
    return pd.to_datetime(s, errors="coerce")

def build_entries_view(
    df: pd.DataFrame,
    retailers_df: pd.DataFrame,
    categories_df: pd.DataFrame,
    want_milk_type_col: bool = False,
) -> pd.DataFrame:
    """
    Clean UI-ready entries view.
    NO global dependencies.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "entry_id",
                "date",
                "zone",
                "Retailer",
                "Category",
                "qty",
                "rate",
                "amount",
            ]
        )

    out = df.copy()

    # --- DATE ---
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # --- IDS ---
    out["retailer_id"] = pd.to_numeric(out.get("retailer_id"), errors="coerce").fillna(0).astype(int)
    out["category_id"] = pd.to_numeric(out.get("category_id"), errors="coerce").fillna(0).astype(int)

    # --- RETAILER JOIN ---
    if retailers_df is not None and not retailers_df.empty:
        rmap = retailers_df[["retailer_id", "name", "zone"]].copy()

        rmap["retailer_id"] = pd.to_numeric(rmap["retailer_id"], errors="coerce").fillna(0).astype(int)
        rmap["zone"] = rmap["zone"].fillna("Default").astype(str).apply(_norm_zone)

        out = out.merge(rmap, on="retailer_id", how="left")
        out = out.rename(columns={"name": "Retailer"})
    else:
        out["Retailer"] = "-"
        out["zone"] = "Default"

    # --- CATEGORY JOIN ---
    if categories_df is not None and not categories_df.empty:
        cmap = categories_df[["category_id", "name"]].copy()

        cmap["category_id"] = pd.to_numeric(cmap["category_id"], errors="coerce").fillna(0).astype(int)

        out = out.merge(cmap, on="category_id", how="left")
        out = out.rename(columns={"name": "Category"})
    else:
        out["Category"] = "-"

    # --- CLEAN FALLBACKS ---
    out["Retailer"] = out.get("Retailer", "-").fillna("-").astype(str)
    out["Category"] = out.get("Category", "-").fillna("-").astype(str)

    if "zone" not in out.columns:
        out["zone"] = "Default"

    out["zone"] = out["zone"].fillna("Default").astype(str).apply(_norm_zone)

    # --- NUMERIC ---
    for c in ["qty", "rate", "amount"]:
        out[c] = pd.to_numeric(out.get(c, 0), errors="coerce").fillna(0.0).astype(float)

    # --- FINAL COLUMNS ---
    cols = [
        "entry_id",
        "date",
        "zone",
        "Retailer",
        "Category",
        "qty",
        "rate",
        "amount",
    ]

    for c in cols:
        if c not in out.columns:
            out[c] = "-" if c in ["zone", "Retailer", "Category", "date"] else 0

    return out[cols]


@st.cache_data(show_spinner="Loading data from Supabase…")
def load_all_data(data_version):
    import time as _t
    _ = data_version
    data = {}

    def _timed(label, fn):
        t0 = _t.time()
        out = fn()
        dt = _t.time() - t0
        rows = len(out) if hasattr(out, "__len__") else "?"
        print(f"[load_all_data] {label:30s} {rows:>7} rows  {dt:6.2f}s", flush=True)
        return out

    data["retailers"]     = _timed("retailers",     lambda: sb_fetch_all(RETAILERS_FILE,  CSV_SCHEMAS[RETAILERS_FILE]))
    data["categories"]    = _timed("categories",    lambda: sb_fetch_all(CATEGORIES_FILE, CSV_SCHEMAS[CATEGORIES_FILE]))
    data["prices"]        = _timed("prices",        lambda: sb_fetch_all(PRICES_FILE,     CSV_SCHEMAS[PRICES_FILE]))
    data["distributors"]  = _timed("distributors",  lambda: sb_fetch_all(DISTRIBUTORS_FILE, CSV_SCHEMAS[DISTRIBUTORS_FILE]))
    data["dist_cat_map"]  = _timed("dist_cat_map",  lambda: sb_fetch_all(DISTRIBUTOR_CATEGORY_MAP_FILE, CSV_SCHEMAS[DISTRIBUTOR_CATEGORY_MAP_FILE]))
    data["entries"]       = _timed("entries",       lambda: sb_fetch_all(ENTRIES_FILE,   CSV_SCHEMAS[ENTRIES_FILE]))
    data["payments"]      = _timed("payments",      lambda: sb_fetch_all(PAYMENTS_FILE,  CSV_SCHEMAS[PAYMENTS_FILE]))
    data["dist_purchases"]= _timed("dist_purchases",lambda: sb_fetch_all(DISTRIBUTOR_PURCHASES_FILE, CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE]))
    data["dist_payments"] = _timed("dist_payments", lambda: sb_fetch_all(DISTRIBUTOR_PAYMENTS_FILE, CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE]))
    data["wastage"]       = _timed("wastage",       lambda: sb_fetch_all(WASTAGE_FILE,   CSV_SCHEMAS[WASTAGE_FILE]))
    data["expenses"]      = _timed("expenses",      lambda: sb_fetch_all(EXPENSES_FILE,  CSV_SCHEMAS[EXPENSES_FILE]))

    return (
        data["retailers"], data["categories"], data["prices"],
        data["entries"], data["payments"],
        data["distributors"], data["dist_purchases"], data["dist_payments"],
        data["dist_cat_map"], data["wastage"], data["expenses"],
    )


@st.cache_data(show_spinner=False)
def build_entries_view_cached(
    df,
    data_version,
    want_milk_type_col=False,
):
    _ = data_version
    # Pass global retailers/categories — safe because data_version busts cache on changes
    return build_entries_view(
        df,
        retailers_df=retailers,
        categories_df=categories,
        want_milk_type_col=want_milk_type_col,
    )


def _norm_zone(z: str) -> str:
    z = "" if z is None else str(z).strip()
    return "Default" if not z else " ".join(z.split()).title()

# ================== SAFE PIVOT HELPERS ==================

def safe_scalar_sum(series_or_df) -> float:
    """Always returns a float scalar, handles Series/DataFrame/scalar."""
    if series_or_df is None:
        return 0.0
    try:

        val = series_or_df
        if isinstance(val, pd.DataFrame):
            return float(val.values.sum())
        if isinstance(val, pd.Series):
            return float(val.sum())
        return float(val)
    except Exception:
        return 0.0


def safe_pivot(df: pd.DataFrame, index: str, columns: str, values: str) -> pd.DataFrame:
    """
    Always returns a flat DataFrame (no MultiIndex).
    Columns are category names (strings).
    Index is reset to a plain column.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    try:
        pivot = pd.pivot_table(
            df,
            index=index,
            columns=columns,
            values=values,
            aggfunc="sum",
            fill_value=0.0,
        )
        # Flatten MultiIndex columns if present
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [str(c[-1]) if isinstance(c, tuple) else str(c) for c in pivot.columns]
        else:
            pivot.columns = [str(c) for c in pivot.columns]
        pivot.columns.name = None
        pivot.index.name = None
        return pivot
    except Exception:
        return pd.DataFrame()


def safe_group_sum(df: pd.DataFrame, group_col: str, value_col: str) -> pd.Series:
    """Returns a Series {group_value: float_sum}, always scalar-safe."""
    if df is None or df.empty or group_col not in df.columns or value_col not in df.columns:
        return pd.Series(dtype=float)
    try:
        result = df.groupby(group_col)[value_col].sum()
        return result.astype(float)
    except Exception:
        return pd.Series(dtype=float)

def parse_boolish_active(v) -> bool:
    if v is None:
        return True
    s = str(v).strip().lower()
    if s in ("false", "0", "no", "n", "inactive", "off"):
        return False
    if s in ("true", "1", "yes", "y", "active", "on"):
        return True
    try:
        return bool(int(float(s)))
    except Exception:
        return True  # default active

def fmt_zero_dash(x) -> str:
    """Format numeric values; show en-dash for zero/blank/invalid."""
    if x in (None, "", "–", "-", "—"):
        v = 0.0
    else:
        try:
            v = float(x)
        except Exception:
            v = 0.0
    return "–" if v == 0.0 else f"{v:.2f}"


def highlight_cell(v):
    try:
        x = float(v)
    except:
        return f"<td>{v}</td>"

    if x == 0:
        return "<td style='color:#bbb'>0.0</td>"
    else:
        return f"<td style='font-weight:700;background:#e8ffe8'>{x:.2f}</td>"


def parse_boolish_paid(v) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y", "paid", "on"):
        return True
    if s in ("false", "0", "no", "n", "unpaid", "off"):
        return False
    try:
        return bool(int(float(s)))
    except Exception:
        return False

def next_id_from_df(df: pd.DataFrame, id_col: str) -> int:
    if df is None or df.empty or id_col not in df.columns:
        return 1
    s = pd.to_numeric(df[id_col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

def _fmt_money(x) -> str:
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return "₹0.00"

def display_or_dash(v, dash="–") -> str:
    s = "" if v is None else str(v).strip()
    return dash if not s else s

def df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make df safe for Streamlit (Arrow) display:
    - convert bytes -> str
    - ensure object columns are consistent (string)
    - replace None/NaN with "–"
    """
    if df is None:
        return pd.DataFrame()

    out = df.copy()

    # Replace None/NaN first
    out = out.replace({None: "–"}).fillna("–")

    # Fix Arrow crash: object columns containing mixed bytes/float/etc.
    for col in out.columns:
        if out[col].dtype == "object":
            def _norm(v):
                if v is None:
                    return "–"
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-8", errors="ignore")
                    except Exception:
                        return str(v)
                return str(v)
            out[col] = out[col].map(_norm)

    return out

def sb_fetch_all(path: str, cols="*", page_size: int = 1000, max_retries: int = 5):
    """Fetch all rows from a Supabase table with correct pagination.

    Fixes:
    1. Supabase PostgREST caps responses at 1000 rows. Using page_size > 1000
       caused silent truncation: the server returned only 1000 rows, and the
       `if len(batch) < page_size: break` check then exited the loop before
       fetching subsequent pages. This dropped most entries/payments and made
       later dates appear empty in the backup CSV. page_size is now pinned to
       1000 to match the server cap.
    2. On empty/flaky queries the original had an infinite while-True loop.
    """
    sb = get_sb()
    if path in FILE_TO_TABLE:
        table, _ = FILE_TO_TABLE[path]
    else:
        table = path
    if isinstance(cols, list):
        cols = ",".join(cols)

    out = []
    offset = 0
    while True:
        batch = None
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = (
                    sb.table(table)
                    .select(cols)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                batch = resp.data or []
                last_exc = None
                break
            except Exception as e:
                last_exc = e
                time.sleep(0.05 * attempt)
        if last_exc is not None:
            raise last_exc
        if not batch:
            break                      # no more rows → exit outer while
        out.extend(batch)
        if len(batch) < page_size:
            break                      # last page → exit outer while
        offset += page_size
    return pd.DataFrame(out)

@st.cache_data(show_spinner=False)
def cached_groupby_sum(df, cols, value, data_version):

    _ = data_version

    if df is None or df.empty:
        return pd.DataFrame()

    return (
        df.groupby(cols)[value]
        .sum()
        .reset_index()
    )

def normalize_date_cols(df: pd.DataFrame, cols=("date",)) -> pd.DataFrame:
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df

@st.cache_data(show_spinner=False)
def cached_fetch_entries(day, rids, version):
    return fetch_entries_filtered(
        day,
        day,
        rids,
        version,
    )

@st.cache_data(show_spinner=False)
def cached_fetch_payments(day, rids, version):
    return fetch_payments_filtered(
        day,
        day,
        rids,
        version,
    )

def compute_ledger_fast(entries, payments):

    def _norm(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "retailer_id", "amount"])
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["retailer_id"] = pd.to_numeric(df["retailer_id"], errors="coerce").fillna(0).astype(int)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        return df

    e = _norm(entries)
    p = _norm(payments)

    e["delta"] = e["amount"]
    p["delta"] = -p["amount"]

    all_df = pd.concat([e, p], ignore_index=True)
    all_df = all_df.sort_values(["retailer_id", "date"])

    result = []
    for rid, grp in all_df.groupby("retailer_id"):
        running = 0
        for _, row in grp.iterrows():
            running += row["delta"]
            result.append({
                "date": row["date"],
                "retailer_id": rid,
                "balance": round(running, 2)
            })

    return pd.DataFrame(result)

@st.cache_data(show_spinner=False)
def cached_pivot(
    df,
    index,
    columns,
    values,
    data_version,
):

    _ = data_version

    if df is None or df.empty:
        return pd.DataFrame()

    return pd.pivot_table(
        df,
        index=index,
        columns=columns,
        values=values,
        aggfunc="sum",
        fill_value=0,
    )


@st.cache_data(show_spinner=False)
def fetch_entries_filtered(
    start_date,
    end_date,
    retailer_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date","gte",str(start_date)))

    if end_date is not None:
        filters.append(("date","lte",str(end_date)))

    if retailer_ids:
        filters.append(("retailer_id","in",retailer_ids))

    return sb_fetch_df(
        ENTRIES_FILE,
        CSV_SCHEMAS[ENTRIES_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def fetch_payments_filtered(
    start_date,
    end_date,
    retailer_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date","gte",str(start_date)))

    if end_date is not None:
        filters.append(("date","lte",str(end_date)))

    if retailer_ids:
        filters.append(("retailer_id","in",retailer_ids))

    return sb_fetch_df(
        PAYMENTS_FILE,
        CSV_SCHEMAS[PAYMENTS_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def fetch_purchases_filtered(
    start_date,
    end_date,
    distributor_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date","gte",str(start_date)))

    if end_date is not None:
        filters.append(("date","lte",str(end_date)))

    if distributor_ids:
        filters.append(("distributor_id","in",distributor_ids))

    return sb_fetch_df(
        DISTRIBUTOR_PURCHASES_FILE,
        CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def cached_distributor_balance(
    did,
    d,
    version,
):

    _ = version

    return distributor_balance_before(
        did,
        d,
    )



def _normalize_df_from_rows(path: str, columns: list[str], rows: list[dict]) -> pd.DataFrame:
    if not rows:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(rows)

    # Ensure schema columns exist (create missing as blank/None)
    for c in columns:
        if c not in df.columns:
            df[c] = None

    # Allow legacy missing columns without crashing
    legacy_ok = ALLOWED_LEGACY_MISSING.get(path, set())
    for c in legacy_ok:
        if c not in df.columns:
            df[c] = None

    # Keep only schema columns (and legacy allowed ones if they are in schema)
    keep = [c for c in columns if c in df.columns]
    return df[keep].copy()


def sb_fetch_where(table: str, cols: str = "*", filters: list[tuple] | None = None, page_size: int = 1000, in_chunk: int = 500) -> list[dict]:
    """
    Fetch rows from Supabase table with server-side filters.
    Supported ops: eq, lt, lte, gt, gte, in

    NOTE: page_size pinned to 1000 — Supabase PostgREST hard-caps responses at
    1000 rows. Using a larger page_size made the loop's
    `if len(batch) < page_size: break` exit after the first page, silently
    truncating filtered fetches (same root cause as sb_fetch_all).
    """
    sb = get_sb()
    filters = filters or []
    base = sb.table(table).select(cols)

    in_filters = []
    for col, op, val in filters:
        if op == "in":
            vals = list(val) if isinstance(val, (list, tuple, set)) else [val]
            in_filters.append((col, vals))
        elif op == "eq":
            base = base.eq(col, val)
        elif op == "lt":
            base = base.lt(col, val)
        elif op == "lte":
            base = base.lte(col, val)
        elif op == "gt":
            base = base.gt(col, val)
        elif op == "gte":
            base = base.gte(col, val)
        else:
            raise ValueError(f"Unsupported op: {op}")

    def _fetch(q):
        out = []
        offset = 0
        while True:
            resp = q.range(offset, offset + page_size - 1).execute()
            batch = resp.data or []
            out.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return out

    if not in_filters:
        return _fetch(base)

    first_col, first_vals = in_filters[0]
    rest_in = in_filters[1:]

    out = []
    for i in range(0, len(first_vals), in_chunk):
        q = base.in_(first_col, first_vals[i:i + in_chunk])
        for col, vals in rest_in:
            q = q.in_(col, vals)
        out.extend(_fetch(q))
    return out


def sb_fetch_df(path: str, columns: list[str], filters: list[tuple] | None = None) -> pd.DataFrame:
    """Fetch a dataframe from Supabase.

    IMPORTANT (data integrity): if server-side filtered fetch fails, we return an EMPTY dataframe
    with the correct schema. We NEVER fall back to an unfiltered full-table read because that
    causes cross-date contamination in transactional pages.
    """
    if not filters:
        return safe_read_csv(path, columns)
    if path not in FILE_TO_TABLE:
        return pd.DataFrame(columns=columns)
    table, _ = FILE_TO_TABLE[path]
    try:
        rows = sb_fetch_where(table, cols="*", filters=filters)
        return _normalize_df_from_rows(path, columns, rows)
    except Exception as e:
        print("sb_fetch_df error:", e)
        # FAIL CLOSED: empty-with-schema, not unfiltered data.
        return _normalize_df_from_rows(path, columns, [])


def _prepare_df_for_write(df: pd.DataFrame, path: str) -> pd.DataFrame:
    df = df.copy() if df is not None else pd.DataFrame()
    df = df.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
    expected_cols = CSV_SCHEMAS.get(path, [])
    if not expected_cols:
        table, _ = FILE_TO_TABLE[path]
        raise RuntimeError(f"{table}: missing schema definition for {path}")

    # Drop any unexpected columns to avoid Supabase "column does not exist" errors.
    extra_cols = [c for c in df.columns if c not in expected_cols]
    if extra_cols:
        df = df.drop(columns=extra_cols, errors="ignore")

    # Ensure all expected columns exist (missing columns become NULLs).
    for c in expected_cols:
        if c not in df.columns:
            df[c] = None

    # Keep stable column order to match schema.
    return df[expected_cols]

def sb_insert_df(df: object, path: str) -> None:
    """
    Clean insert helper.

    - Always treats input as NEW rows
    - NEVER trusts client-side primary keys
    - Assigns explicit IDs (max(pk)+1) to avoid:
        * null PK constraint errors (re-added by schema enforcement)
        * IDENTITY sequence drift causing duplicate pkey errors
    - Handles dict / list / DataFrame
    """

    # Normalize input
    if isinstance(df, dict):
        df = pd.DataFrame([df])
    elif isinstance(df, list):
        df = pd.DataFrame(df)

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"sb_insert_df expects DataFrame/dict/list[dict], got {type(df)}")

    if df.empty:
        return

    table, pk = FILE_TO_TABLE[path]

    # 🚨 CRITICAL: NEVER send primary key from UI
    if pk in df.columns:
        df = df.drop(columns=[pk])

    # Clean + enforce schema
    df = _prepare_df_for_write(df, path)

    # 🚨 _prepare_df_for_write re-adds the pk column as None to match schema.
    # Drop it again so we can either omit it OR assign fresh IDs explicitly.
    if pk in df.columns:
        df = df.drop(columns=[pk])

    # Assign explicit IDs based on current max(pk)+1.
    # This avoids both null-PK errors AND IDENTITY sequence drift duplicates.
    try:
        next_id = sb_next_id(table, pk)
        df.insert(0, pk, list(range(next_id, next_id + len(df))))
    except Exception as _id_err:
        # If we can't compute next id, fall back to letting DB generate.
        print(f"[sb_insert_df] sb_next_id failed for {table}.{pk}: {_id_err}")

    # Convert NaN → None (required for Supabase)
    records = df.where(pd.notna(df), None).to_dict(orient="records")

    # Insert in chunks
    for i in range(0, len(records), 500):
        resp = sb.table(table).insert(records[i:i+500]).execute()
        if not resp or getattr(resp, "data", None) is None:
            raise RuntimeError(f"{table}: insert failed")

    # Refresh app state
    st.session_state["data_version"] += 1
    st.cache_data.clear()

def sb_delete_by_pk(table: str, pk: str, ids: list[int], chunk: int = 1000) -> None:
    sb = get_sb()
    ids = [int(x) for x in ids if x is not None]
    if not ids:
        return
    for i in range(0, len(ids), chunk):
        sb.table(table).delete().in_(pk, ids[i:i+chunk]).execute()



def sb_delete_where(table: str, filters: list[tuple], in_chunk: int = 500) -> None:
    """
    FIXED: preserves ALL filters even when using IN().
    filters: list of tuples like:
      ("date","eq","2026-02-05")
      ("retailer_id","in",[1,2,3])
    Supported ops: eq, lt, lte, gt, gte, in
    """
    sb = get_sb()
    base = sb.table(table).delete()

    in_filters = []
    for col, op, val in filters:
        if op == "in":
            vals = list(val) if isinstance(val, (list, tuple, set)) else [val]
            in_filters.append((col, vals))
        elif op == "eq":
            base = base.eq(col, val)
        elif op == "lt":
            base = base.lt(col, val)
        elif op == "lte":
            base = base.lte(col, val)
        elif op == "gt":
            base = base.gt(col, val)
        elif op == "gte":
            base = base.gte(col, val)
        else:
            raise ValueError(f"Unsupported op: {op}")

    if not in_filters:
        base.execute()
        return

    first_col, first_vals = in_filters[0]
    rest_in = in_filters[1:]

    for i in range(0, len(first_vals), in_chunk):
        q = base.in_(first_col, first_vals[i:i + in_chunk])
        for col, vals in rest_in:
            q = q.in_(col, vals)
        q.execute()


def safe_write_csv(df: pd.DataFrame, path: str, allow_empty: bool = False) -> None:
    """
    DB MODE:
    - Upsert rows only (NO implicit deletes).
    - Deletions must be explicit via sb_delete_* helpers.
    """
    if path not in FILE_TO_TABLE:
        raise ValueError(f"Unknown mapping for: {path}")

    table, pk = FILE_TO_TABLE[path]
    df = _prepare_df_for_write(df, path)

    if df.empty and not allow_empty:
        raise RuntimeError(
            f"Refusing to write EMPTY dataframe to {table}. "
            f"Pass allow_empty=True only if you truly want to write nothing."
        )
    if df.empty:
        return

    # If PK is entirely NULL, treat it as "DB-generated IDs": INSERT (not UPSERT).
    # (Your caller should usually use sb_insert_df for this case, but this makes it safe.)
    if pk in df.columns and df[pk].isna().all():
        payload = df.drop(columns=[pk], errors="ignore")
        records = payload.where(pd.notna(payload), None).to_dict(orient="records")
        chunk = 500
        for i in range(0, len(records), chunk):
            sb.table(table).insert(records[i:i+chunk]).execute()
    
        return

    # Mixed NULL/non-NULL PK is dangerous (can create duplicates).
    if pk in df.columns and df[pk].isna().any():
        raise RuntimeError(f"{table}: mixed NULL/non-NULL primary keys")

    # Defensive: PK must exist for UPSERT
    if pk not in df.columns:
        raise RuntimeError(f"{table}: missing primary key column '{pk}' for upsert")

    if df[pk].duplicated().any():
        dups = df[df[pk].duplicated(keep=False)][pk].tolist()[:10]
        raise RuntimeError(f"{table}: duplicate primary keys in dataframe (sample): {dups}")

    records = df.where(pd.notna(df), None).to_dict(orient="records")
    chunk = 500
    for i in range(0, len(records), chunk):
        sb.table(table).upsert(records[i:i+chunk], on_conflict=pk).execute()

    invalidate_data_cache()



def safe_write_two_csvs(df1: pd.DataFrame, path1: str, df2: pd.DataFrame, path2: str) -> None:
    safe_write_csv(df1, path1, allow_empty=True)
    safe_write_csv(df2, path2, allow_empty=True)

# ================== DISTRIBUTOR LEDGER + BILL HELPERS ==================

def safe_read_csv(path: str, columns: list[str]) -> pd.DataFrame:
    """
    DB MODE:
    - Reads from Supabase tables (NOT local CSV).
    - Returns a DataFrame with exactly the expected schema columns (plus allowed legacy missing columns).
    """
    if path not in FILE_TO_TABLE:
        # fallback: return empty with the requested columns
        return pd.DataFrame(columns=columns)

    table, pk = FILE_TO_TABLE[path]

    table, _ = FILE_TO_TABLE[path]
    df = sb_fetch_all(path, columns)
    if df is None or df.empty:
        df = pd.DataFrame(columns=columns)

    # Ensure schema columns exist (create missing as blank/None)
    for c in columns:
        if c not in df.columns:
            df[c] = None

    # Allow legacy missing columns without crashing
    legacy_ok = ALLOWED_LEGACY_MISSING.get(path, set())
    for c in legacy_ok:
        if c not in df.columns:
            df[c] = None

    # Keep only schema columns (and legacy allowed ones if they are in schema)
    keep = [c for c in columns if c in df.columns]
    df = df[keep].copy()

    return df


def distributor_balance_before(distributor_id: int, start_day: date) -> float:
    """
    Due before start_day = (purchases before) - (payments before)
    Positive => you owe distributor.
    """
    if USE_SERVER_FILTERS:
        dp = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "lt", str(start_day)),
            ],
        )
        pay = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "lt", str(start_day)),
            ],
        )
    else:
        dp = dist_purchases.copy()
        pay = dist_payments.copy()

    purchases_amt = 0.0
    paid_amt = 0.0

    if not dp.empty:
        dp["date"] = pd.to_datetime(dp["date"], errors="coerce").dt.date

        dp = dp.loc[
            (dp["distributor_id"].astype(int) == int(distributor_id)) &
            (dp["date"] < start_day)
        ].copy()
        if not dp.empty:
            # trust stored amount but normalize if missing
            if "amount" in dp.columns:
                purchases_amt = float(pd.to_numeric(dp["amount"], errors="coerce").fillna(0).sum())
            else:
                purchases_amt = float((pd.to_numeric(dp["qty"], errors="coerce").fillna(0) * pd.to_numeric(dp["rate"], errors="coerce").fillna(0)).sum())

    if not pay.empty:
        pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
        pay = pay.loc[
            (pay["distributor_id"].astype(int) == int(distributor_id)) &
            (pay["date"] < start_day)
        ].copy()
        if not pay.empty:
            paid_amt = float(pd.to_numeric(pay["amount"], errors="coerce").fillna(0).sum())

    return float(purchases_amt - paid_amt)


def build_distributor_daily_grid(distributor_id: int, start_day: date, end_day: date, cat_names: list[str]) -> pd.DataFrame:
    """
    One row per date.
    Columns:
      Date,
      for each category: "<cat> Qty", "<cat> Rate",
      Total Milk (L), Purchases (₹), Payment (₹), Running Due (₹)
    Rate shown = weighted avg rate for that day+category (amount/qty) if multiple lines exist.
    """
    days = pd.date_range(start=start_day, end=end_day, freq="D").date

    if USE_SERVER_FILTERS:
        dp = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        dp = dist_purchases.copy()
    if not dp.empty:
        dp["date"] = pd.to_datetime(dp["date"], errors="coerce").dt.date
        dp = dp.loc[
            (dp["distributor_id"].astype(int) == int(distributor_id)) &
            (dp["date"] >= start_day) &
            (dp["date"] <= end_day)
        ].copy()

    if not dp.empty:
        dp["qty"] = pd.to_numeric(dp["qty"], errors="coerce").fillna(0.0).astype(float)
        dp["rate"] = pd.to_numeric(dp["rate"], errors="coerce").fillna(0.0).astype(float)
        dp["amount"] = pd.to_numeric(dp.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)

        # attach category names
        dp = dp.merge(categories[["category_id", "name"]], on="category_id", how="left").rename(columns={"name": "Category"})
        dp["Category"] = dp["Category"].fillna("").astype(str)

    if USE_SERVER_FILTERS:
        pay = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        pay = dist_payments.copy()
    if not pay.empty:
        pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
        pay = pay.loc[
            (pay["distributor_id"].astype(int) == int(distributor_id)) &
            (pay["date"] >= start_day) &
            (pay["date"] <= end_day)
        ].copy()
        pay["amount"] = pd.to_numeric(pay["amount"], errors="coerce").fillna(0.0).astype(float)

    pay_by_day = pay.groupby("date")["amount"].sum().to_dict() if not pay.empty else {}

    opening_due = distributor_balance_before(distributor_id, start_day)
    running = float(opening_due)

    rows = []
    for d in days:
        row = {"Date": str(d)}
        total_milk = 0.0
        day_amt = 0.0

        if dp.empty:
            dp_day = pd.DataFrame(columns=["Category", "qty", "amount"])
        else:
            dp_day = dp.loc[dp["date"] == d].copy()

        for cat in cat_names:
            qcol = f"{cat} Qty"
            rcol = f"{cat} Rate"

            if dp_day.empty:
                qty = 0.0
                amt = 0.0
            else:
                sub = dp_day.loc[dp_day["Category"] == cat].copy()
                qty = float(sub["qty"].sum()) if not sub.empty else 0.0
                amt = float(sub["amount"].sum()) if not sub.empty else 0.0

            if qty > 0:
                # Weighted avg rate
                rate = (amt / qty) if qty > 0 else 0.0
                row[qcol] = qty
                row[rcol] = rate if rate > 0 else "-"
                total_milk += qty
                day_amt += amt
            else:
                row[qcol] = "-"
                row[rcol] = "-"

        pay_amt = float(pay_by_day.get(d, 0.0))
        running = float(running + day_amt - pay_amt)

        row["Total Milk (L)"] = round(float(total_milk), 2)
        row["Purchases (₹)"] = round(float(day_amt), 2)
        row["Payment (₹)"] = round(float(pay_amt), 2)
        row["Running Due (₹)"] = round(float(running), 2)

        rows.append(row)

    return pd.DataFrame(rows)


def distributor_pay_mode_totals(distributor_id: int, start_day: date, end_day: date) -> pd.DataFrame:
    pay = dist_payments.copy()
    if pay.empty:
        return pd.DataFrame(columns=["Mode", "Total (₹)"])

    pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
    pay = pay.loc[
        (pay["distributor_id"].astype(int) == int(distributor_id)) &
        (pay["date"] >= start_day) &
        (pay["date"] <= end_day)
    ].copy()
    if pay.empty:
        return pd.DataFrame(columns=["Mode", "Total (₹)"])

    pay["payment_mode"] = pay["payment_mode"].fillna("Cash").astype(str)
    pay["amount"] = pd.to_numeric(pay["amount"], errors="coerce").fillna(0.0).astype(float)

    out = (
        pay.groupby("payment_mode", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
    )
    return out


def build_distributor_bill_html(
    distributor_row: dict,
    start_day: date,
    end_day: date,
    grid: pd.DataFrame,
    pay_mode_totals: pd.DataFrame,
    cat_names: list[str],
) -> str:
    shop_name = "RANJIT BHIMRAO KAWLE MILK SUPPLIER"

    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def safe_meta(v):
        v = "" if v is None else str(v)
        v = v.strip()
        return v if v else "-"

    def fmt_money(x) -> str:
        try:
            return f"₹{float(x):,.2f}"
        except Exception:
            return "₹0.00"

    def fmt_num(x) -> str:
        try:
            return f"{float(x):.2f}"
        except Exception:
            return "-"

    vendor = safe_meta(distributor_row.get("name"))
    contact = safe_meta(distributor_row.get("contact"))
    address = safe_meta(distributor_row.get("address"))

    df = grid.copy() if grid is not None else pd.DataFrame()

    total_qty_by_cat = {cat: 0.0 for cat in cat_names}
    total_amt = 0.0
    total_pay = 0.0
    closing_due = 0.0

    if not df.empty:
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol in df.columns:
                s = 0.0
                for v in df[qcol].tolist():
                    try:
                        s += float(v)
                    except Exception:
                        pass
                total_qty_by_cat[cat] = float(s)

        if "Purchases (₹)" in df.columns:
            total_amt = float(pd.to_numeric(df["Purchases (₹)"], errors="coerce").fillna(0).sum())
        if "Payment (₹)" in df.columns:
            total_pay = float(pd.to_numeric(df["Payment (₹)"], errors="coerce").fillna(0).sum())
        if "Running Due (₹)" in df.columns and len(df) > 0:
            closing_due = float(pd.to_numeric(df["Running Due (₹)"], errors="coerce").fillna(0).iloc[-1])

    pay_rows_html = ""
    if pay_mode_totals is not None and not pay_mode_totals.empty:
        pm = pay_mode_totals.copy()
        for _, r in pm.iterrows():
            mode = esc(r.get("Mode", "-"))
            amt = fmt_money(r.get("Total (₹)", 0.0))
            pay_rows_html += f"<tr><td>{mode}</td><td style='text-align:right'>{amt}</td></tr>"
    else:
        pay_rows_html = "<tr><td colspan='2' style='text-align:center;color:#666'>No payments in this period</td></tr>"

    th = "<th>Date</th>"
    for cat in cat_names:
        th += f"<th>{esc(cat)} Qty</th><th>{esc(cat)} Rate</th>"
    th += "<th>Total Milk (L)</th><th>Purchases (₹)</th><th>Payment (₹)</th><th>Running Due (₹)</th>"

    body_rows = ""
    for _, r in df.iterrows():
        tds = f"<td>{esc(r.get('Date','-'))}</td>"
        for cat in cat_names:
            qcol = f"{cat} Qty"
            rcol = f"{cat} Rate"
            qv = r.get(qcol, "-")
            rv = r.get(rcol, "-")

            if qv == "-" or qv is None:
                qdisp = "-"
            else:
                try:
                    qdisp = f"{float(qv):.2f}" if float(qv) != 0 else "-"
                except Exception:
                    qdisp = "-"

            if rv == "-" or rv is None:
                rdisp = "-"
            else:
                try:
                    rdisp = f"{float(rv):.2f}" if float(rv) != 0 else "-"
                except Exception:
                    rdisp = "-"

            tds += f"<td style='text-align:right'>{qdisp}</td><td style='text-align:right'>{rdisp}</td>"

        tds += f"<td style='text-align:right'>{fmt_num(r.get('Total Milk (L)', 0.0))}</td>"
        tds += f"<td style='text-align:right'>{fmt_money(r.get('Purchases (₹)', 0.0))}</td>"
        tds += f"<td style='text-align:right'>{fmt_money(r.get('Payment (₹)', 0.0))}</td>"
        tds += f"<td style='text-align:right'>{fmt_money(r.get('Running Due (₹)', 0.0))}</td>"
        body_rows += f"<tr>{tds}</tr>"

    total_row = "<td><b>TOTAL</b></td>"
    for cat in cat_names:
        total_row += f"<td style='text-align:right'><b>{total_qty_by_cat[cat]:.2f}</b></td><td style='text-align:right'><b>-</b></td>"
    total_milk_all = float(sum(total_qty_by_cat.values()))
    total_row += f"<td style='text-align:right'><b>{total_milk_all:.2f}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(total_amt)}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(total_pay)}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(closing_due)}</b></td>"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Distributor Statement</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #111; }}
  .topbar {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
  h1 {{ margin: 0; font-size: 28px; letter-spacing: 1px; }}
  .meta {{ border:1px solid #333; padding:12px; border-radius:8px; margin-top:10px; }}
  .meta b {{ display:inline-block; min-width: 140px; }}
  .btns {{ margin: 12px 0 18px 0; }}
  button {{ padding: 8px 14px; border: 1px solid #333; background: #f2f2f2; cursor:pointer; border-radius: 6px; }}
  button:hover {{ background:#e8e8e8; }}
  table {{ width:100%; border-collapse: collapse; margin-top: 10px; }}
  th, td {{ border:1px solid #333; padding: 6px 8px; font-size: 12.5px; }}
  th {{ background: #efefef; }}
  .section-title {{ font-size: 18px; margin-top: 14px; font-weight: 700; }}
  .summarybox {{ border:1px solid #333; padding:12px; border-radius:8px; margin-top:10px; }}
  .sign {{ margin-top: 34px; display:flex; justify-content:space-between; gap:20px; }}
  .sign .line {{ border-top:1px solid #333; width: 260px; margin-top: 36px; }}
  .muted {{ color:#444; font-size: 12px; }}
  @media print {{
    .btns {{ display: none; }}
    body {{ margin: 8mm; }}
    th {{ background: #eee !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1>{esc(shop_name)}</h1>
    <div class="muted">Distributor Statement / Incoming Milk Ledger</div>
  </div>
  <div class="btns">
    <button onclick="window.print()">🖨️ Print</button>
  </div>
</div>

<div class="meta">
  <div><b>Distributor:</b> {esc(vendor)}</div>
  <div><b>Contact:</b> {esc(contact)}</div>
  <div><b>Address:</b> {esc(address)}</div>
  <div><b>Period:</b> {esc(str(start_day))} to {esc(str(end_day))}</div>
</div>

<div class="section-title">Incoming Milk Details</div>
<table>
  <thead><tr>{th}</tr></thead>
  <tbody>
    {body_rows}
    <tr>{total_row}</tr>
  </tbody>
</table>

<div class="section-title">Summary</div>
<div class="summarybox">
  <div><b>Total Purchases:</b> {fmt_money(total_amt)}</div>
  <div><b>Total Payments:</b> {fmt_money(total_pay)}</div>
  <div><b>Closing Due:</b> {fmt_money(closing_due)}</div>
</div>

<div class="section-title">Payment Mode Totals (This Period)</div>
<table style="width: 420px; max-width:100%;">
  <thead><tr><th>Mode</th><th style="text-align:right">Total (₹)</th></tr></thead>
  <tbody>{pay_rows_html}</tbody>
</table>

<div class="sign">
  <div>
    <div class="line"></div>
    <div><b>Distributor Signature</b></div>
  </div>
  <div style="text-align:right;">
    <div class="line"></div>
    <div><b>Proprietor (Verified)</b></div>
    <div class="muted">{esc(shop_name)}</div>
  </div>
</div>

</body>
</html>
"""
    return html

def build_daily_report_html(
    report_day,
    retailer_table,
    retailer_totals,
    retailer_pay_modes,
    distributor_table,
    distributor_totals,
    purchased_qty,
    purchased_amt,
    sold_qty,
    sold_amt,
    waste_qty=0.0,
    waste_loss=0.0,
    show_cards=True,
):

    import pandas as pd

    def esc(x):
        if pd.isna(x):
            return ""
        return str(x)

    def fmt_num(x):
        try:
            return f"{float(x):.2f}"
        except:
            return "0.00"

    def fmt_money(x):
        try:
            return f"₹{float(x):,.2f}"
        except:
            return "₹0.00"

    def df_to_html(df, title):
        if df is None or df.empty:
            return f"<h3>{title}</h3><p>No data</p>"

        head = "".join(f"<th>{c}</th>" for c in df.columns)

        rows = ""
        for _, r in df.iterrows():
            rows += "<tr>" + "".join(
                highlight_cell(r[c]) for c in df.columns
            ) + "</tr>"

        return f"""
        <h3>{title}</h3>
        <table>
            <thead><tr>{head}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    net_profit = float(sold_amt) - float(purchased_amt) - float(waste_loss)

    summary_cards = f"""
    <div class="cards">
        <div class="card"><b>Purchased</b><br>{fmt_num(purchased_qty)} L</div>
        <div class="card"><b>Purchase Amt</b><br>{fmt_money(purchased_amt)}</div>
        <div class="card"><b>Sold</b><br>{fmt_num(sold_qty)} L</div>
        <div class="card"><b>Sales</b><br>{fmt_money(sold_amt)}</div>
        <div class="card"><b>Wastage</b><br>{fmt_num(waste_qty)} L</div>
        <div class="card"><b>Net Profit</b><br>{fmt_money(net_profit)}</div>
    </div>
    """

    cards_html = summary_cards if show_cards else ""

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Milk Report</title>

<style>

body {{
    font-family: Arial;
    margin:20px;
}}

.header {{
    text-align:center;
}}

.cards {{
    display:flex;
    justify-content:space-between;
    margin-top:20px;
    flex-wrap:wrap;
}}

.card {{
    flex:1;
    min-width:160px;
    margin:5px;
    padding:10px;
    border:1px solid #000;
    text-align:center;
    font-size:13px;
}}

table {{
    width:100%;
    border-collapse:collapse;
    margin-top:10px;
    font-size:12px;
}}

th, td {{
    border:1px solid #000;
    padding:5px;
    text-align:center;
}}

th {{
    background:#f0f0f0;
}}

.section {{
    margin-top:25px;
}}

.print-btn {{
    margin-bottom:15px;
}}

@media print {{
    .print-btn {{
        display:none;
    }}
}}

</style>
</head>

<body>

<div class="print-btn">
<button onclick="window.print()">Print Report</button>
</div>

<div class="header">
<h2>RANJIT BHIMRAO KAWLE MILK</h2>
<h4>Daily Business Summary</h4>
<p>Date: {report_day}</p>
</div>

{cards_html}

<div class="section">
{df_to_html(retailer_table, "Retailers / Zones Summary")}
</div>

<div class="section">
{df_to_html(retailer_pay_modes, "Payments by Mode")}
</div>

{"<div class='section'>" + df_to_html(distributor_table, "Distributors Summary") + "</div>" if show_cards else ""}

</body>
</html>
"""
    return html

# ================== AUDIT PATCH HELPERS (added by production audit) =========
# PATCH 1: batched opening-balance helper (fixes "previous ledger = 0" bug).
@st.cache_data(show_spinner=False, ttl=300)
def cached_opening_balances(retailer_ids: tuple, as_of_day, data_version: int) -> dict:
    """{retailer_id: sales_before(day) - payments_before(day)}  — ONE query per table."""
    _ = data_version
    if not retailer_ids:
        return {}
    rids = sorted({int(r) for r in retailer_ids})

    e = sb_fetch_df(
        ENTRIES_FILE, CSV_SCHEMAS[ENTRIES_FILE],
        filters=[("retailer_id", "in", rids), ("date", "lt", str(as_of_day))],
    )
    p = sb_fetch_df(
        PAYMENTS_FILE, CSV_SCHEMAS[PAYMENTS_FILE],
        filters=[("retailer_id", "in", rids), ("date", "lt", str(as_of_day))],
    )

    if e.empty:
        sales = pd.Series(dtype=float)
    else:
        e2 = e.copy()
        e2["retailer_id"] = pd.to_numeric(e2["retailer_id"], errors="coerce").fillna(0).astype(int)
        e2["amount"] = pd.to_numeric(e2["amount"], errors="coerce").fillna(0.0)
        sales = e2.groupby("retailer_id")["amount"].sum()

    if p.empty:
        paid = pd.Series(dtype=float)
    else:
        p2 = p.copy()
        p2["retailer_id"] = pd.to_numeric(p2["retailer_id"], errors="coerce").fillna(0).astype(int)
        p2["amount"] = pd.to_numeric(p2["amount"], errors="coerce").fillna(0.0)
        paid = p2.groupby("retailer_id")["amount"].sum()

    bal = sales.subtract(paid, fill_value=0.0)
    return {int(r): float(bal.get(r, 0.0)) for r in rids}


# PATCH 5: batched distributor opening balance.
@st.cache_data(show_spinner=False, ttl=300)
def cached_distributor_openings(dist_ids: tuple, as_of_day, data_version: int) -> dict:
    _ = data_version
    if not dist_ids:
        return {}
    dids = sorted({int(d) for d in dist_ids})
    dp = sb_fetch_df(
        DISTRIBUTOR_PURCHASES_FILE, CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
        filters=[("distributor_id", "in", dids), ("date", "lt", str(as_of_day))],
    )
    dpay = sb_fetch_df(
        DISTRIBUTOR_PAYMENTS_FILE, CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
        filters=[("distributor_id", "in", dids), ("date", "lt", str(as_of_day))],
    )
    if dp.empty:
        pur = pd.Series(dtype=float)
    else:
        t = dp.copy()
        t["distributor_id"] = pd.to_numeric(t["distributor_id"], errors="coerce").fillna(0).astype(int)
        t["amount"] = pd.to_numeric(t.get("amount", 0.0), errors="coerce").fillna(0.0)
        pur = t.groupby("distributor_id")["amount"].sum()
    if dpay.empty:
        paid = pd.Series(dtype=float)
    else:
        t = dpay.copy()
        t["distributor_id"] = pd.to_numeric(t["distributor_id"], errors="coerce").fillna(0).astype(int)
        t["amount"] = pd.to_numeric(t.get("amount", 0.0), errors="coerce").fillna(0.0)
        paid = t.groupby("distributor_id")["amount"].sum()
    bal = pur.subtract(paid, fill_value=0.0)
    return {int(d): float(bal.get(d, 0.0)) for d in dids}


# PATCH 4: pre-computed price lookup for a day (replaces N calls to
# get_price_for_date in report/daily-posting loops).
@st.cache_data(show_spinner=False, ttl=600)
def price_lookup_for_day(day, data_version: int) -> dict:
    _ = data_version
    if prices.empty:
        pr = pd.DataFrame(columns=["retailer_id", "category_id", "price", "effective_date"])
    else:
        pr = prices.copy()
    pr["effective_date"] = pd.to_datetime(pr["effective_date"], errors="coerce").dt.date
    pr = pr.dropna(subset=["effective_date"])
    pr = pr[pr["effective_date"] <= day]
    pr = pr.sort_values("effective_date")
    pr["retailer_id"] = pd.to_numeric(pr["retailer_id"], errors="coerce").fillna(0).astype(int)
    pr["category_id"] = pd.to_numeric(pr["category_id"], errors="coerce").fillna(0).astype(int)
    pr["price"] = pd.to_numeric(pr["price"], errors="coerce").fillna(0.0)

    latest = pr.groupby(["retailer_id", "category_id"], as_index=False).tail(1)
    specific = {(int(r.retailer_id), int(r.category_id)): float(r.price)
                for r in latest.itertuples() if float(r.price) > 0}
    global_price = {k[1]: v for k, v in specific.items() if k[0] == GLOBAL_RETAILER_ID}

    cat_default = {}
    if not categories.empty and "default_price" in categories.columns:
        for c in categories.itertuples():
            dp = getattr(c, "default_price", None)
            if dp is not None and not pd.isna(dp) and float(dp) > 0:
                cat_default[int(c.category_id)] = float(dp)

    return {"specific": specific, "global": global_price, "default": cat_default}


def resolve_price(price_map: dict, rid: int, cid: int) -> float:
    rid, cid = int(rid), int(cid)
    v = price_map["specific"].get((rid, cid))
    if v and v > 0:
        return v
    v = price_map["global"].get(cid)
    if v and v > 0:
        return v
    return float(price_map["default"].get(cid, 0.0))
# ================== END AUDIT PATCH HELPERS =================================

    # ================== INITIAL DATA LOAD ==================
(
    retailers,
    categories,
    prices,
    entries,
    payments,
    distributors,
    dist_purchases,
    dist_payments,
    dist_cat_map,
    wastage,
    expenses,
) = load_all_data(st.session_state["data_version"])

entries = normalize_date_cols(entries)
payments = normalize_date_cols(payments)
dist_purchases = normalize_date_cols(dist_purchases)
dist_payments = normalize_date_cols(dist_payments)



# ================== ZONE HELPERS ==================
def get_all_zones() -> list[str]:
    if retailers.empty:
        return ["Default"]
    rz = retailers.copy()
    rz["zone"] = rz["zone"].apply(_norm_zone)
    zones = sorted(set(rz["zone"].tolist()))
    return zones if zones else ["Default"]


def build_fast_report(start_date, end_date, *args, **kwargs):
    # args/kwargs ignored — data fetched fresh from DBdef build_fast_report(start_date, end_date):

    entries = fetch_entries_filtered(start_date, end_date, [], st.session_state["data_version"])
    payments = fetch_payments_filtered(start_date, end_date, [], st.session_state["data_version"])
    purchases = fetch_purchases_filtered(start_date, end_date, [], st.session_state["data_version"])

    # ---- AGGREGATION ----
    sales = entries.groupby("date")["amount"].sum().reset_index()
    pay = payments.groupby("date")["amount"].sum().reset_index()
    purchase = purchases.groupby("date")["amount"].sum().reset_index()

    return sales, pay, purchase

def get_zone_retailer_ids(selected_zone: str) -> list[int]:
    if retailers.empty:
        return []
    if selected_zone == "All Zones":
        return retailers["retailer_id"].astype(int).tolist()

    # Main zone: retailers maintained in Main book (mapping table).
    if selected_zone == MAIN_ZONE:
        main_ids = set(get_main_retailer_ids())
        # Backward compatibility: also include retailers whose zone is literally "Main"
        rz = retailers.copy()
        rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
        main_ids |= set(rz.loc[rz["zone"] == _norm_zone(MAIN_ZONE), "retailer_id"].astype(int).tolist())
        return sorted(main_ids)

    z = _norm_zone(selected_zone)
    rz = retailers.copy()
    rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
    return rz.loc[rz["zone"] == z, "retailer_id"].astype(int).tolist()
def filter_by_zone(df: pd.DataFrame, retailer_id_col: str, selected_zone: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if selected_zone == "All Zones":
        return df.copy()
    ids = set(get_zone_retailer_ids(selected_zone))
    if not ids:
        return df.iloc[0:0].copy()
    return df.loc[df[retailer_id_col].astype(int).isin(ids)].copy()

# ================== MAIN BOOK RETAILERS (MAPPING) ==================
# Main book retailers are "normal" retailers, but maintained in the Main book for overview.
# They are defined by the mapping table `public.main_retailers` (retailer_id primary key).
MAIN_ZONE = "Main"
MAIN_RETAILERS_TABLE = "main_retailers"

def _main_table_exists() -> bool:
    try:
        get_sb().table(MAIN_RETAILERS_TABLE).select("retailer_id").limit(1).execute()
        return True
    except Exception:
        return False

def get_main_retailer_ids() -> list[int]:
    """Return retailer_ids configured for Main book (no caching; single-user friendly)."""
    if not _main_table_exists():
        return []
    try:
        rows = sb_fetch_all(MAIN_RETAILERS_TABLE, cols="retailer_id") or []
        out: list[int] = []
        for r in rows:
            try:
                out.append(int(r.get("retailer_id")))
            except Exception:
                pass
        # stable order
        return sorted(set(out))
    except Exception:
        return []

def add_main_retailers(retailer_ids: list[int]) -> None:
    if not _main_table_exists():
        raise RuntimeError("Missing DB table 'main_retailers'. Create it in Supabase SQL editor.")
    ids = sorted({int(x) for x in retailer_ids if x is not None})
    if not ids:
        return
    records = [{"retailer_id": int(rid)} for rid in ids]
    get_sb().table(MAIN_RETAILERS_TABLE).insert(records).execute()
    invalidate_data_cache()

def remove_main_retailers(retailer_ids: list[int]) -> None:
    if not _main_table_exists():
        raise RuntimeError("Missing DB table 'main_retailers'. Create it in Supabase SQL editor.")
    ids = sorted({int(x) for x in retailer_ids if x is not None})
    if not ids:
        return
    get_sb().table(MAIN_RETAILERS_TABLE).delete().in_("retailer_id", ids).execute()
    invalidate_data_cache()
# ================== PRICING HELPERS ==================
def _get_effective_price(price_df: pd.DataFrame, entry_dt: pd.Timestamp) -> float | None:
    if price_df.empty:
        return None
    df = price_df.copy()
    df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce").dt.normalize()
    entry_dt = pd.to_datetime(entry_dt, errors="coerce").normalize()
    df = df.loc[df["effective_date"].notna()]
    df = df.loc[df["effective_date"] <= entry_dt]
    if df.empty:
        return None
    df = df.sort_values("effective_date", ascending=False)
    return float(df.iloc[0]["price"])

def get_price_for_date(retailer_id: int, category_id: int, entry_date) -> float | None:
    entry_dt = pd.to_datetime(entry_date)

    if not prices.empty:
        rs = prices.loc[(prices["retailer_id"] == int(retailer_id)) & (prices["category_id"] == int(category_id))].copy()
        p = _get_effective_price(rs, entry_dt)
        if p is not None and p > 0:
            return float(p)

        gs = prices.loc[(prices["retailer_id"] == GLOBAL_RETAILER_ID) & (prices["category_id"] == int(category_id))].copy()
        p = _get_effective_price(gs, entry_dt)
        if p is not None and p > 0:
            return float(p)

    if not categories.empty and "default_price" in categories.columns:
        cat_row = categories.loc[categories["category_id"] == int(category_id)]
        if not cat_row.empty:
            default_price = cat_row.iloc[0].get("default_price", 0.0)
            if pd.notna(default_price) and float(default_price) > 0:
                return float(default_price)

    return None

def get_retailer_balance(retailer_id: int) -> float:
    e = normalize_date_cols(entries)
    p = normalize_date_cols(payments)

    if e is None or e.empty:
        total_sales = 0.0
    else:
        e["retailer_id"] = pd.to_numeric(e["retailer_id"], errors="coerce").fillna(0).astype(int)
        e["amount"] = pd.to_numeric(e["amount"], errors="coerce").fillna(0.0).astype(float)
        total_sales = float(e.loc[e["retailer_id"] == int(retailer_id), "amount"].sum())

    if p is None or p.empty:
        total_payments = 0.0
    else:
        p["retailer_id"] = pd.to_numeric(p["retailer_id"], errors="coerce").fillna(0).astype(int)
        p["amount"] = pd.to_numeric(p["amount"], errors="coerce").fillna(0.0).astype(float)
        total_payments = float(p.loc[p["retailer_id"] == int(retailer_id), "amount"].sum())

    return float(total_sales - total_payments)

def retailer_ledger_as_of(retailer_id: int, as_of_day: date) -> float:
    e = normalize_date_cols(entries)
    p = normalize_date_cols(payments)

    if e is None or e.empty and p is None or p.empty:
        return 0.0

    if e is not None and not e.empty:
        e["retailer_id"] = pd.to_numeric(e["retailer_id"], errors="coerce").fillna(0).astype(int)
        e["amount"] = pd.to_numeric(e["amount"], errors="coerce").fillna(0.0).astype(float)
    if p is not None and not p.empty:
        p["retailer_id"] = pd.to_numeric(p["retailer_id"], errors="coerce").fillna(0).astype(int)
        p["amount"] = pd.to_numeric(p["amount"], errors="coerce").fillna(0.0).astype(float)

    sales = e.loc[(e["retailer_id"] == int(retailer_id)) & (e["date"] <= as_of_day), "amount"].sum() if e is not None and not e.empty else 0.0
    paid = p.loc[(p["retailer_id"] == int(retailer_id)) & (p["date"] <= as_of_day), "amount"].sum() if p is not None and not p.empty else 0.0
    return float(sales - paid)

def retailer_ledger_as_of(retailer_id: int, as_of_day: date) -> float:
    if entries.empty and payments.empty:
        return 0.0
    e = entries.copy()
    p = payments.copy()
    if not e.empty:
        e["date"] = pd.to_datetime(e["date"], errors="coerce").dt.date
    if not p.empty:
        p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.date

    sales = e.loc[(e["retailer_id"] == int(retailer_id)) & (e["date"] <= as_of_day), "amount"].sum() if not e.empty else 0.0
    paid = p.loc[(p["retailer_id"] == int(retailer_id)) & (p["date"] <= as_of_day), "amount"].sum() if not p.empty else 0.0
    return float(sales - paid)

def is_retailer_referenced(retailer_id: int) -> bool:
    rid = int(retailer_id)
    if (not entries.empty) and (rid in set(entries["retailer_id"].astype(int))):
        return True
    if (not payments.empty) and (rid in set(payments["retailer_id"].astype(int))):
        return True
    if (not prices.empty) and (rid in set(prices["retailer_id"].astype(int))):
        return True
    return False

def is_category_referenced(category_id: int) -> bool:
    cid = int(category_id)
    if (not entries.empty) and (cid in set(entries["category_id"].astype(int))):
        return True
    if (not prices.empty) and (cid in set(prices["category_id"].astype(int))):
        return True
    if (not dist_purchases.empty) and (cid in set(dist_purchases["category_id"].astype(int))):
        return True
    if (not wastage.empty) and (cid in set(wastage["category_id"].astype(int))):
        return True
    return False

def is_distributor_referenced(distributor_id: int) -> bool:
    did = int(distributor_id)
    if (not dist_purchases.empty) and (did in set(dist_purchases["distributor_id"].astype(int))):
        return True
    if (not dist_payments.empty) and (did in set(dist_payments["distributor_id"].astype(int))):
        return True
    return False

# ================== DAILY SHEET HELPERS ==================

def _retailer_ids_for_zone(zone: str) -> list[int]:
    """Returns retailer_ids for the given zone (or all if 'All Zones').

    NOTE: uses the canonical `retailers` dataframe loaded from Supabase.
    Do NOT rely on a global `retailers_active` from some page scope.
    """
    try:
        rz = retailers.copy() if isinstance(retailers, pd.DataFrame) else pd.DataFrame()
        if rz.empty:
            return []
        rz = rz.copy()
        rz["zone"] = rz.get("zone", "").astype(str).apply(_norm_zone)
        # if is_active exists, use it
        if "is_active" in rz.columns:
            rz["is_active"] = rz["is_active"].apply(parse_boolish_active)
            rz = rz.loc[rz["is_active"] == True].copy()
        if zone == "All Zones":
            return rz["retailer_id"].astype(int).tolist()
        return rz.loc[rz["zone"] == _norm_zone(zone), "retailer_id"].astype(int).tolist()
    except Exception:
        return []

def _day_entries_for_zone(day: date, zone: str) -> pd.DataFrame:
    """Always fetches fresh transactional data for the selected day (+ zone filter)."""
    if USE_SERVER_FILTERS:
        rids = _retailer_ids_for_zone(zone)
        if not rids:
            return pd.DataFrame(columns=CSV_SCHEMAS[ENTRIES_FILE])
        df = sb_fetch_df(
            ENTRIES_FILE,
            CSV_SCHEMAS[ENTRIES_FILE],
            filters=[("date", "eq", str(day)), ("retailer_id", "in", rids)],
        )
        return df
    # CSV / local fallback
    df = entries.copy()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == day].copy()
    df = filter_by_zone(df, "retailer_id", zone)
    return df



def _day_payments_for_zone(day: date, zone: str) -> pd.DataFrame:

    if USE_SERVER_FILTERS:

        rids = _retailer_ids_for_zone(zone)

        if not rids:
            return pd.DataFrame(columns=CSV_SCHEMAS[PAYMENTS_FILE])

        df = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("date", "eq", str(day)),
                ("retailer_id", "in", rids),
            ],
        )

    else:

        df = payments.copy()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    df = df.loc[df["date"] == day].copy()

    df = filter_by_zone(df, "retailer_id", zone)

    return df
PAYMENT_MODES = ["CASH", "UPI","CHEQUE"]


def _day_fetch_strict(path: str, day: date, zone: str) -> pd.DataFrame:
    """Strict day fetch: if Supabase query fails, STOP instead of showing wrong/empty data."""
    try:
        if path == ENTRIES_FILE:
            return _day_entries_for_zone(day, zone)
        if path == PAYMENTS_FILE:
            return _day_payments_for_zone(day, zone)
        raise ValueError("Unknown path")
    except Exception as e:
        st.error(f"❌ Failed to load day data from Supabase for {day} / {zone}.\n\n{e}")
        st.stop()

def build_daily_posting_grid(day: date, zone: str, retailers_active: pd.DataFrame, categories_active: pd.DataFrame):
    """Builds the Daily Posting Sheet grid.

    Data-integrity rules:
    - All joins/pivots are by retailer_id and category_id (NOT names).
    - Display columns include the category_id to make the mapping unambiguous.
    - The returned `cat_cols` is a list of dicts: {col, category_id, name}.
    """
    rz = retailers_active.copy()
    rz["zone"] = rz.get("zone", "").astype(str).apply(_norm_zone)
    if zone != "All Zones":
        rz = rz.loc[rz["zone"] == _norm_zone(zone)].copy()

    cats = categories_active.copy()
    cats["category_id"] = pd.to_numeric(cats["category_id"], errors="coerce").fillna(0).astype(int)
    cats["name"] = cats.get("name", "").fillna("").astype(str)
    cats = cats.loc[cats["category_id"] > 0].copy()

    # Category display columns: include ID to prevent duplicate-name ambiguity.
    cat_cols = []
    for _, c in cats.iterrows():
        cid = int(c["category_id"])
        nm = str(c["name"]).strip()
        col = f"CID:{cid} — {nm}" if nm else f"CID:{cid}"
        cat_cols.append({"col": col, "category_id": cid, "name": nm})

    # Fresh day data (fail closed)
    day_p = _day_fetch_strict(PAYMENTS_FILE, day, zone)
    day_e = _day_fetch_strict(ENTRIES_FILE, day, zone)

    # Payments pivot: retailer_id x payment_mode
    pay_by_mode = pd.DataFrame()
    if day_p is not None and not day_p.empty:
        tmp = day_p.copy()
        tmp["retailer_id"] = pd.to_numeric(tmp.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
        tmp["payment_mode"] = tmp.get("payment_mode", "Cash").fillna("Cash").astype(str).str.strip().str.upper()
        tmp["amount"] = pd.to_numeric(tmp.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)
        pay_by_mode = (
            tmp.pivot_table(index="retailer_id", columns="payment_mode", values="amount", aggfunc="sum", fill_value=0.0)
            .reindex(columns=PAYMENT_MODES, fill_value=0.0)
        )

    # Entries pivot: retailer_id x category_id
    qty_by_rid_cid = pd.DataFrame()
    if day_e is not None and not day_e.empty:
        e = day_e.copy()
        e["retailer_id"] = pd.to_numeric(e.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
        e["category_id"] = pd.to_numeric(e.get("category_id", 0), errors="coerce").fillna(0).astype(int)
        e["qty"] = pd.to_numeric(e.get("qty", 0.0), errors="coerce").fillna(0.0).astype(float)
        qty_by_rid_cid = pd.pivot_table(
            e, index="retailer_id", columns="category_id", values="qty", aggfunc="sum", fill_value=0.0
        )

    rows = []
    for _, r in rz.iterrows():
        rid = int(r["retailer_id"])
        retailer_name = str(r.get("name", ""))

        row = {"ID": rid, "Retailer": retailer_name}

        for m in PAYMENT_MODES:

            col = f"{m} ₹"

            val = 0.0

            if not pay_by_mode.empty:

                modes = [
                    str(x).strip().upper()
                    for x in pay_by_mode.columns
                ]

                if str(m).strip().upper() in modes:

                    real_col = pay_by_mode.columns[
                        modes.index(
                            str(m).strip().upper()
                        )
                    ]

                    if rid in pay_by_mode.index:

                        val = float(
                            pay_by_mode.loc[rid, real_col]
                        )

            row[col] = float(val)

        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = 0.0
            if (not qty_by_rid_cid.empty) and (rid in qty_by_rid_cid.index) and (cid in qty_by_rid_cid.columns):
                qty = float(qty_by_rid_cid.loc[rid, cid])
            row[col] = float(qty)

        rows.append(row)

    grid = pd.DataFrame(rows)
    return grid, cat_cols

def compute_today_sales_amount_for_row(rid: int, day: date, row: pd.Series, cat_name_list: list[str], categories_active: pd.DataFrame) -> float:
    amt = 0.0
    for cat_name in cat_name_list:
        qty = float(row.get(cat_name, 0.0) or 0.0)
        if qty <= 0:
            continue
        cid = int(categories_active.loc[categories_active["name"] == cat_name, "category_id"].iloc[0])
        rate = get_price_for_date(rid, cid, day)
        if rate is None or rate <= 0:
            raise ValueError(f"Price missing for Retailer ID {rid} / {cat_name} on {day}")
        amt += qty * float(rate)
    return float(amt)

def zone_category_pivot_for_day(day: date) -> pd.DataFrame:
    df = entries.copy()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == day].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.merge(retailers[["retailer_id", "zone"]], on="retailer_id", how="left")
    df["zone"] = df["zone"].apply(_norm_zone)

    df = df.merge(categories[["category_id", "name"]], on="category_id", how="left").rename(columns={"name": "Category"})
    df["Category"] = df["Category"].fillna("").astype(str)

    pivot = safe_pivot(df, index="zone", columns="Category", values="qty")
    if pivot.empty:
        return pd.DataFrame()

    pivot = pivot.sort_index()
    pivot["TOTAL (L)"] = pivot.sum(axis=1).astype(float)
    pivot = pivot.reset_index().rename(columns={"index": "Zone", "zone": "Zone"})
    if "Zone" not in pivot.columns and pivot.index.name:
        pivot = pivot.reset_index().rename(columns={pivot.index.name: "Zone"})
    return pivot

# ================== BILL / STATEMENT HELPERS ==================
def retailer_balance_before(retailer_id: int, start_day: date) -> float:
    """Single-retailer wrapper over the batch helper (patched)."""
    return cached_opening_balances(
        (int(retailer_id),), start_day, st.session_state["data_version"]
    ).get(int(retailer_id), 0.0)

def _rate_from_entries_or_price(retailer_id: int, cid: int, d: date, e_day_cat: pd.DataFrame) -> float | None:
    # Prefer stored entry rates (history-safe). If missing/zero, fallback to price table.
    if e_day_cat is not None and not e_day_cat.empty:
        rates = pd.to_numeric(e_day_cat["rate"], errors="coerce").fillna(0.0)
        rates = rates[rates > 0]
        if not rates.empty:
            # if multiple rates, show average for display but sales uses amount anyway
            return float(rates.mean())
    return get_price_for_date(int(retailer_id), int(cid), d)

def build_bill_daily_grid(retailer_id: int, start_day: date, end_day: date, cat_names: list[str]) -> pd.DataFrame:
    """
    SINGLE authoritative bill grid. No duplicates.
    Logic:
      opening_due = balance before start_day
      daily_sales = sum(qty * rate) using stored entries (amount) primarily
      payments
      running_due
    Columns:
      Date,
      per category: "<cat> Qty", "<cat> Rate",
      Total Milk (L), Sales (₹), Payment (₹), Running Due (₹)
    """
    days = pd.date_range(start=start_day, end=end_day, freq="D").date

    if USE_SERVER_FILTERS:
        e = sb_fetch_df(
            ENTRIES_FILE,
            CSV_SCHEMAS[ENTRIES_FILE],
            filters=[
                ("retailer_id", "eq", int(retailer_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        e = entries.copy()
    if not e.empty:
        e["date"] = _safe_dt(e["date"]).dt.date
        e = e.loc[
            (e["retailer_id"].astype(int) == int(retailer_id)) &
            (e["date"] >= start_day) &
            (e["date"] <= end_day)
        ].copy()

    if not e.empty:
        e = e.merge(categories[["category_id", "name"]], on="category_id", how="left").rename(columns={"name": "Category"})
        e["Category"] = e["Category"].fillna("").astype(str)

    if USE_SERVER_FILTERS:
        p = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("retailer_id", "eq", int(retailer_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        p = payments.copy()
    if not p.empty:
        p["date"] = _safe_dt(p["date"]).dt.date
        p = p.loc[
            (p["retailer_id"].astype(int) == int(retailer_id)) &
            (p["date"] >= start_day) &
            (p["date"] <= end_day)
        ].copy()

    pay_by_day = p.groupby("date")["amount"].sum().to_dict() if not p.empty else {}

    opening_due = retailer_balance_before(int(retailer_id), start_day)
    running = float(opening_due)

    rows = []
    for d in days:
        row = {"Date": str(d)}

        e_day = e.loc[e["date"] == d].copy() if (e is not None and not e.empty) else pd.DataFrame(columns=["Category", "qty", "rate", "amount"])

        total_milk = 0.0
        day_sales = 0.0

        for cat in cat_names:
            qcol = f"{cat} Qty"
            rcol = f"{cat} Rate"

            e_day_cat = e_day.loc[e_day["Category"] == str(cat)].copy() if not e_day.empty else pd.DataFrame()
            qty = float(pd.to_numeric(e_day_cat["qty"], errors="coerce").fillna(0.0).sum()) if not e_day_cat.empty else 0.0

            if qty > 0:
                # Prefer stored amounts (history-safe)
                amt = float(pd.to_numeric(e_day_cat["amount"], errors="coerce").fillna(0.0).sum()) if not e_day_cat.empty else 0.0
                # If amount not reliable, compute qty*rate
                if amt <= 0:
                    cat_row = categories.loc[categories["name"].astype(str) == str(cat)]
                    cid = int(cat_row.iloc[0]["category_id"]) if not cat_row.empty else None
                    rate = _rate_from_entries_or_price(int(retailer_id), int(cid), d, e_day_cat) if cid is not None else None
                    if rate is not None and float(rate) > 0:
                        amt = qty * float(rate)
                day_sales += float(amt)

                # Rate display
                cat_row = categories.loc[categories["name"].astype(str) == str(cat)]
                cid = int(cat_row.iloc[0]["category_id"]) if not cat_row.empty else None
                rate_disp = _rate_from_entries_or_price(int(retailer_id), int(cid), d, e_day_cat) if cid is not None else None

                row[qcol] = qty
                row[rcol] = float(rate_disp) if (rate_disp is not None and float(rate_disp) > 0) else "-"
            else:
                row[qcol] = "-"
                row[rcol] = "-"

            total_milk += qty

        pay = float(pay_by_day.get(d, 0.0))
        running = float(running + day_sales - pay)

        row["Total Milk (L)"] = round(float(total_milk), 2)
        row["Sales (₹)"] = round(float(day_sales), 2)
        row["Payment (₹)"] = round(float(pay), 2)
        row["Running Due (₹)"] = round(float(running), 2)

        rows.append(row)

    return pd.DataFrame(rows)

def build_bill_html(
    retailer_row: dict,
    start_day: date,
    end_day: date,
    grid: pd.DataFrame,
    pay_mode_totals: pd.DataFrame,
    cat_names: list[str],
    opening_due: float,
) -> str:
    shop_name = "RANJIT BHIMRAO KAWLE MILK SUPPLIER"
    cust = display_or_dash(retailer_row.get("name"))
    zone = display_or_dash(retailer_row.get("zone"))
    contact = display_or_dash(retailer_row.get("contact"))
    address = display_or_dash(retailer_row.get("address"))

    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def fmt_money(x) -> str:
        return _fmt_money(x)

    def fmt_num(x) -> str:
        try:
            return f"{float(x):.2f}"
        except Exception:
            return "–"

    df = grid.copy() if grid is not None else pd.DataFrame()

    total_qty_by_cat = {cat: 0.0 for cat in cat_names}
    total_sales = 0.0
    total_pay = 0.0
    closing_due = float(opening_due)

    if df is not None and not df.empty:
        # Totals by category qty
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol in df.columns:
                s = 0.0
                for v in df[qcol].tolist():
                    try:
                        s += float(v)
                    except Exception:
                        pass
                total_qty_by_cat[cat] = float(s)

        # Period totals
        if "Sales (₹)" in df.columns:
            total_sales = float(pd.to_numeric(df["Sales (₹)"], errors="coerce").fillna(0).sum())
        if "Payment (₹)" in df.columns:
            total_pay = float(pd.to_numeric(df["Payment (₹)"], errors="coerce").fillna(0).sum())

        # Closing due = last running due (if present)
        if "Running Due (₹)" in df.columns and not df.empty:
            closing_due = float(
                pd.to_numeric(df["Running Due (₹)"], errors="coerce")
                .fillna(opening_due)
                .iloc[-1]
            )

    # Payment mode totals rows
    pay_rows_html = ""
    if pay_mode_totals is not None and not pay_mode_totals.empty:
        pm = pay_mode_totals.copy()
        for _, r in pm.iterrows():
            mode = esc(r.get("Mode", "-"))
            amt = fmt_money(r.get("Total (₹)", 0.0))
            pay_rows_html += f"<tr><td>{mode}</td><td style='text-align:right'>{amt}</td></tr>"
    else:
        pay_rows_html = "<tr><td colspan='2' style='text-align:center;color:#666'>No payments in this period</td></tr>"

    # ========= TABLE HEADER (Rate removed) =========
    th = "<th>Date</th>"
    for cat in cat_names:
        th += f"<th>{esc(cat)} Qty</th>"
    th += "<th>Total Milk (L)</th><th>Sales (₹)</th><th>Payment (₹)</th><th>Running Due (₹)</th>"

    # ========= TABLE BODY (Rate removed) =========
    body_rows = ""
    for _, r in df.iterrows() if df is not None else []:
        tds = f"<td>{esc(r.get('Date','-'))}</td>"

        for cat in cat_names:
            qcol = f"{cat} Qty"
            qv = r.get(qcol, "-")

            if qv == "-" or qv is None:
                qdisp = "-"
            else:
                try:
                    fq = float(qv)
                    qdisp = "-" if fq == 0 else f"{fq:.2f}"
                except Exception:
                    qdisp = "-"

            tds += highlight_cell(qdisp)

        tds += highlight_cell(r.get("Total Milk (L)",0.0))
        tds += highlight_cell(r.get("Sales (₹)",0.0))
        tds += highlight_cell(r.get("Payment (₹)",0.0))
        tds += f"<td style='text-align:right'>{fmt_money(r.get('Running Due (₹)', 0.0))}</td>"
        body_rows += f"<tr>{tds}</tr>"

    # ========= TOTAL ROW (Rate removed) =========
    total_row = "<td><b>TOTAL</b></td>"
    for cat in cat_names:
        total_row += f"<td style='text-align:right'><b>{total_qty_by_cat[cat]:.2f}</b></td>"

    total_milk_all = float(sum(total_qty_by_cat.values()))
    total_row += f"<td style='text-align:right'><b>{total_milk_all:.2f}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(total_sales)}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(total_pay)}</b></td>"
    total_row += f"<td style='text-align:right'><b>{fmt_money(closing_due)}</b></td>"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Milk Bill</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #111; }}
  .topbar {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
  h1 {{ margin: 0; font-size: 28px; letter-spacing: 1px; }}
  .meta {{ border:1px solid #333; padding:12px; border-radius:8px; margin-top:10px; }}
  .meta b {{ display:inline-block; min-width: 120px; }}
  .btns {{ margin: 12px 0 18px 0; }}
  button {{ padding: 8px 14px; border: 1px solid #333; background: #f2f2f2; cursor:pointer; border-radius: 6px; }}
  button:hover {{ background:#e8e8e8; }}
  table {{ width:100%; border-collapse: collapse; margin-top: 10px; }}
  th, td {{ border:1px solid #333; padding: 6px 8px; font-size: 12.5px; }}
  th {{ background: #efefef; }}
  .section-title {{ font-size: 18px; margin-top: 14px; font-weight: 700; }}
  .summarybox {{ border:1px solid #333; padding:12px; border-radius:8px; margin-top:10px; }}
  .sign {{ margin-top: 34px; display:flex; justify-content:space-between; gap:20px; }}
  .sign .line {{ border-top:1px solid #333; width: 260px; margin-top: 36px; }}
  .muted {{ color:#444; font-size: 12px; }}
  @media print {{
    .btns {{ display: none; }}
    body {{ margin: 8mm; }}
    th {{ background: #eee !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1>{esc(shop_name)}</h1>
    <div class="muted">Professional Statement / Bill</div>
  </div>
  <div class="btns">
    <button onclick="window.print()">🖨️ Print</button>
  </div>
</div>

<div class="meta">
  <div><b>Customer:</b> {esc(cust)}</div>
  <div><b>Zone:</b> {esc(zone)}</div>
  <div><b>Contact:</b> {esc(contact)}</div>
  <div><b>Address:</b> {esc(address)}</div>
  <div><b>Period:</b> {esc(str(start_day))} to {esc(str(end_day))}</div>
</div>

<div class="section-title">Summary</div>
<div class="summarybox">
  <div><b>Opening Due:</b> {fmt_money(opening_due)}</div>
  <div><b>Total Sales:</b> {fmt_money(total_sales)}</div>
  <div><b>Total Payments:</b> {fmt_money(total_pay)}</div>
  <div><b>Closing Due:</b> {fmt_money(closing_due)}</div>
</div>

<div class="section-title">Bill Details</div>
<table>
  <thead><tr>{th}</tr></thead>
  <tbody>
    {body_rows}
    <tr>{total_row}</tr>
  </tbody>
</table>

<div class="section-title">Payment Mode Totals (This Period)</div>
<table style="width: 420px; max-width:100%;">
  <thead><tr><th>Mode</th><th style="text-align:right">Total (₹)</th></tr></thead>
  <tbody>{pay_rows_html}</tbody>
</table>

<div class="sign">
  <div>
    <div class="line"></div>
    <div><b>Customer Signature</b></div>
  </div>
  <div style="text-align:right;">
    <div class="line"></div>
    <div><b>Proprietor (Verified)</b></div>
    <div class="muted">{esc(shop_name)}</div>
  </div>
</div>

</body>
</html>
"""
    return html
# PDF generation intentionally disabled.
# HTML is the single source of truth for printing.

def bill_pdf_bytes_from_html(html: str):
    return None


# ================== SIDEBAR: ZONE CONTEXT ==================
zones = get_all_zones()
if MAIN_ZONE not in zones:
    zones = [MAIN_ZONE] + zones
selected_zone = st.sidebar.selectbox("Zone Context", ["All Zones"] + zones, index=0)

retailers_active = retailers.loc[retailers.get("is_active", True).apply(parse_boolish_active)].copy() if not retailers.empty else retailers.copy()
categories_active = categories.loc[categories.get("is_active", True).apply(parse_boolish_active)].copy() if not categories.empty else categories.copy()

entries_z = filter_by_zone(entries.copy(), "retailer_id", selected_zone) if not entries.empty else pd.DataFrame(columns=entries.columns)
payments_z = filter_by_zone(payments.copy(), "retailer_id", selected_zone) if not payments.empty else pd.DataFrame(columns=payments.columns)

# ================== UI ==================
st.title("🥛 RANJIT BHIMRAO KAWLE MILK SUPPLIER")
if "css_loaded" not in st.session_state:
    st.session_state["css_loaded"] = True
    st.markdown(f"""
<div style="
  display:flex; align-items:center; justify-content:space-between;
  padding:18px 20px; margin-bottom:14px;
  background: rgba(255,255,255,0.72);
  border:1px solid rgba(15,23,42,0.10);
  border-radius:18px;
  box-shadow: 0 10px 30px rgba(2,6,23,0.08);
  backdrop-filter: blur(10px);
">
  <div>
    <div style="font-size:28px; font-weight:950; letter-spacing:-0.02em;">🥛 RANJIT BHIMRAO KAWLE MILK SUPPLIER</div>
    <div style="color:#64748B; font-weight:750; margin-top:2px;">Milk Accounting Pro • Clean ledgers • Fast billing</div>
  </div>
  <div style="text-align:right;">
    <div style="color:#64748B; font-weight:800; font-size:12px;">Today</div>
    <div style="font-weight:950; font-size:16px;">{date.today().strftime("%d %b %Y")}</div>
  </div>
</div>
""", unsafe_allow_html=True)



# ---- Production safety: always allow manual refresh ----
if st.sidebar.button("🔄 Refresh (force latest data)", use_container_width=True):
    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    st.rerun()

menu = st.sidebar.radio(
    "📋 Navigation",
    [
        "📊 Dashboard",
        "📝 Daily Posting Sheet (Excel)",
        "📅 Date + Zone View",
        "📍 Zone-wise Summary",
        "✏️ Edit (Single Entry)",
        "🥛 Milk Categories",
        "🏪 Retailers",
        "💰 Price Management",
        "🧾 Retailers Bill",
        "📒 Ledger",
        "🔍 Filters & Reports",
        "🚚 Distributors",
        "🧩 Distributor Category Mapping",
        "📒 Distributor Ledger",
        "🧾 Distributor Bill",
        "💼 Expenses",
        "🛡️ Data Health & Backup",
    ],
)
# ================== DASHBOARD ==================
if menu == "📊 Dashboard":
    st.header(f"📊 Business Overview — {selected_zone}")
    version = st.session_state["data_version"]
    col1, col2, col3, col4 = st.columns(4)
    # Use GLOBAL entries/payments (not zone-filtered) for lifetime dashboard totals
    # Round to 2 decimal places to eliminate float drift
    total_milk = round(float(pd.to_numeric(entries["qty"], errors="coerce").fillna(0.0).sum()), 2) if not entries.empty else 0.0
    total_sales = round(float(pd.to_numeric(entries["amount"], errors="coerce").fillna(0.0).sum()), 2) if not entries.empty else 0.0
    total_payments = round(float(pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0).sum()), 2) if not payments.empty else 0.0
    outstanding = round(total_sales - total_payments, 2)


    with col1:
        st.metric("Total Milk Sold", f"{float(total_milk):.2f} L", delta="Lifetime")
    with col2:
        st.metric("Total Sales", f"₹{float(total_sales):.2f}")
    with col3:
        st.metric("Total Payments", f"₹{float(total_payments):.2f}")
    with col4:
        st.metric("Outstanding", f"₹{float(outstanding):.2f}", delta=f"₹{float(outstanding):.2f}" if outstanding > 0 else "Settled")

    st.divider()

    st.subheader("📅 Daily Summary Sheet (Zones + Main Book Retailers)")
    dash_day = st.date_input("Select Date", value=date.today(), key="dash_day_summary")
    version = st.session_state["data_version"]


    # Categories (active only)
    cat_df = categories.copy()
    if not cat_df.empty and "is_active" in cat_df.columns:
        cat_df = cat_df.loc[cat_df["is_active"].apply(parse_boolish_active) == True].copy()
    cat_df["category_id"] = pd.to_numeric(cat_df.get("category_id", 0), errors="coerce").fillna(0).astype(int)
    cat_df["name"] = cat_df.get("name", "").fillna("").astype(str)
    cat_names = [c for c in cat_df["name"].tolist() if str(c).strip()]
    cat_id_to_name = dict(zip(cat_df["category_id"].tolist(), cat_df["name"].tolist()))

    # Day entries/payments (ALL zones)
    if USE_SERVER_FILTERS:

        rids = None
        if selected_zone != "All Zones":
            rids = _retailer_ids_for_zone(selected_zone)

        e_day = cached_fetch_entries(
            dash_day,
            rids or [],
            version,
        )

        p_day = cached_fetch_payments(
            dash_day,
            rids or [],
            version,
        )

    else:

        e_day = entries.copy()
        p_day = payments.copy()

    if not e_day.empty:
        e_day["date"] = pd.to_datetime(e_day["date"], errors="coerce").dt.date
        e_day = e_day.loc[e_day["date"] == dash_day].copy()
        e_day["retailer_id"] = pd.to_numeric(e_day.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
        e_day["category_id"] = pd.to_numeric(e_day.get("category_id", 0), errors="coerce").fillna(0).astype(int)
        e_day["qty"] = pd.to_numeric(e_day.get("qty", 0.0), errors="coerce").fillna(0.0).astype(float)
        e_day["amount"] = pd.to_numeric(e_day.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)
        e_day["Category"] = e_day["category_id"].map(cat_id_to_name).fillna("").astype(str)
    else:
        e_day = pd.DataFrame(columns=["retailer_id", "category_id", "qty", "amount", "Category"])

    if not p_day.empty:
        p_day["date"] = pd.to_datetime(p_day["date"], errors="coerce").dt.date
        p_day = p_day.loc[p_day["date"] == dash_day].copy()
        p_day["retailer_id"] = pd.to_numeric(p_day.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
        p_day["amount"] = pd.to_numeric(p_day.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)
        p_day["payment_mode"] = (
            p_day.get("payment_mode", "Cash")
            .fillna("Cash")
            .astype(str)
            .str.strip()
            .str.upper()
        )
    else:
        p_day = pd.DataFrame(columns=["retailer_id", "amount", "payment_mode"])

    # Retailer lookup
    rmap = retailers.copy()
    if not rmap.empty:
        rmap["retailer_id"] = pd.to_numeric(rmap.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
        rmap["name"] = rmap.get("name", "").fillna("").astype(str)
        rmap["zone"] = rmap.get("zone", "Default").fillna("Default").astype(str).apply(_norm_zone)

    # ---- Zone rows ----
    zone_pivot = pd.DataFrame()
    zone_sales = pd.Series(dtype=float)
    zone_pay = pd.Series(dtype=float)

    if (not e_day.empty) and (not rmap.empty):
        e_zone = e_day.merge(rmap[["retailer_id", "zone"]], on="retailer_id", how="left")
        e_zone["zone"] = e_zone["zone"].fillna("Default").astype(str).apply(_norm_zone)
        e_zone = e_zone.loc[e_zone["Category"].astype(str).str.len() > 0].copy()
        if not e_zone.empty:
            zone_pivot = safe_pivot(e_zone, index="zone", columns="Category", values="qty")
            zone_sales = safe_group_sum(e_zone, "zone", "amount")

    if (not p_day.empty) and (not rmap.empty):
        p_zone = p_day.merge(rmap[["retailer_id", "zone"]], on="retailer_id", how="left")
        p_zone["zone"] = p_zone["zone"].fillna("Default").astype(str).apply(_norm_zone)
        if not p_zone.empty:
            zone_pay = safe_group_sum(p_zone, "zone", "amount")

    # Normalize zone_pivot columns
    if not zone_pivot.empty:
        for c in cat_names:
            if c not in zone_pivot.columns:
                zone_pivot[c] = 0.0
        zone_pivot = zone_pivot.reindex(columns=cat_names, fill_value=0.0)
        zone_pivot["TOTAL (L)"] = zone_pivot[cat_names].sum(axis=1).astype(float)

    # ---- Main book retailer rows ----
    main_ids = set(get_main_retailer_ids())
    main_pivot = pd.DataFrame()
    main_sales_map = {}
    main_pay_map = {}
    main_r = pd.DataFrame(columns=["retailer_id", "name"])

    if main_ids and (not rmap.empty):
        main_r = rmap.loc[rmap["retailer_id"].astype(int).isin(list(main_ids))].copy()

        if not main_r.empty and not e_day.empty:
            e_main = e_day.loc[e_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))].copy()
            e_main = e_main.merge(main_r[["retailer_id", "name"]], on="retailer_id", how="left").rename(columns={"name": "Retailer"})
            e_main = e_main.loc[e_main["Category"].astype(str).str.len() > 0].copy()
            if not e_main.empty:
                main_pivot = safe_pivot(e_main, index="Retailer", columns="Category", values="qty")
                main_sales_map = safe_group_sum(e_main, "Retailer", "amount").to_dict()

        if not p_day.empty and not main_r.empty:
            p_main = p_day.loc[p_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))].copy()
            if not p_main.empty:
                p_main = p_main.merge(main_r[["retailer_id", "name"]], on="retailer_id", how="left")
                main_pay_map = safe_group_sum(p_main, "name", "amount").to_dict()

    if not main_pivot.empty:
        for c in cat_names:
            if c not in main_pivot.columns:
                main_pivot[c] = 0.0
        main_pivot = main_pivot.reindex(columns=cat_names, fill_value=0.0)
        main_pivot["TOTAL (L)"] = main_pivot[cat_names].sum(axis=1).astype(float)

    # ---- Main book retailer rows ----
    main_ids = set(get_main_retailer_ids())
    main_pivot = pd.DataFrame()
    main_sales_map = {}
    main_pay_map = {}
    main_r = pd.DataFrame(columns=["retailer_id", "name"])

    if main_ids and (not rmap.empty):
        main_r = rmap.loc[rmap["retailer_id"].astype(int).isin(list(main_ids))].copy()

        if not main_r.empty and not e_day.empty:
            e_main = e_day.loc[e_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))].copy()
            e_main = e_main.merge(main_r[["retailer_id", "name"]], on="retailer_id", how="left").rename(columns={"name": "Retailer"})
            e_main = e_main.loc[e_main["Category"].astype(str).str.len() > 0].copy()
            if not e_main.empty:
                main_pivot = cached_pivot(
                    e_main,
                    index="Retailer",
                    columns="Category",
                    values="qty",
                    data_version=version,
                )
                tmp = cached_groupby_sum(
                    e_main,
                    ["Retailer"],
                    "amount",
                    version,
                )
                main_sales_map = dict(zip(tmp["Retailer"], tmp["amount"]))

        if not p_day.empty and not main_r.empty:
            p_main = p_day.loc[p_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))].copy()
            if not p_main.empty:
                p_main = p_main.merge(main_r[["retailer_id", "name"]], on="retailer_id", how="left")
                tmp = cached_groupby_sum(
                    p_main,
                    ["name"],
                    "amount",
                    version,
                )
                main_pay_map = dict(zip(tmp["name"], tmp["amount"]))
    if not main_pivot.empty:
        for c in cat_names:
            if c not in main_pivot.columns:
                main_pivot[c] = 0.0
        main_pivot = main_pivot.reindex(columns=cat_names, fill_value=0.0)
        main_pivot["TOTAL (L)"] = main_pivot.sum(axis=1)

    # ---- Ledgers ----
    opening_by_rid = {}
    if not rmap.empty:
        rid_list = sorted(
            set(
                rmap["retailer_id"]
                .astype(int)
                .tolist()
            )
        )

        opening_by_rid = cached_opening_balances(
            tuple(rid_list),
            dash_day,
            version,
        )

    zone_opening = pd.Series(dtype=float)
    if not rmap.empty and opening_by_rid:
        _tmp = rmap[["retailer_id", "zone"]].copy()
        _tmp["opening"] = _tmp["retailer_id"].map(opening_by_rid).fillna(0.0).astype(float)
        tmp = cached_groupby_sum(
            _tmp,
            ["zone"],
            "opening",
            version,
        )
        zone_opening = tmp.set_index("zone")["opening"].astype(float)
        
    opening_by_name = {}
    if not main_r.empty:
        for _, rr in main_r[["retailer_id", "name"]].drop_duplicates().iterrows():
            opening_by_name[str(rr["name"])] = float(opening_by_rid.get(int(rr["retailer_id"]), 0.0))

    # ---- Dashboard display table (existing style: liters + payment only) ----
    out_cols = ["Name"] + cat_names + ["TOTAL (L)", "Payment (₹)"]
    frames = []

    if not zone_pivot.empty:
        zdf = zone_pivot.copy().sort_index()
        zdf["Payment (₹)"] = zone_pay.reindex(zdf.index).fillna(0.0).astype(float)
        zdf.insert(0, "Name", zdf.index.astype(str))
        zdf = zdf.reset_index(drop=True)
        frames.append(zdf[out_cols])

    if (not main_pivot.empty) and frames:
        frames.append(pd.DataFrame([{c: "–" for c in out_cols}]))

    pass

    if not zone_pivot.empty:
        grand = {"Name": "GRAND TOTAL"}
        for c in cat_names:
            col_data = zone_pivot[c] if c in zone_pivot.columns else pd.Series([0.0])
            grand[c] = safe_scalar_sum(col_data)
        grand["TOTAL (L)"] = safe_scalar_sum(zone_pivot["TOTAL (L)"] if "TOTAL (L)" in zone_pivot.columns else 0.0)
        grand["Payment (₹)"] = safe_scalar_sum(zone_pay)
        frames.append(pd.DataFrame([grand])[out_cols])

    if not frames:
        st.info("No entries/payments found for this date.")
    else:
        out = pd.concat(frames, ignore_index=True)
        disp = out.copy()
        for c in cat_names + ["TOTAL (L)"]:
            disp[c] = disp[c].apply(fmt_zero_dash)
        disp["Payment (₹)"] = disp["Payment (₹)"].apply(fmt_zero_dash)
        st.dataframe(df_for_display(disp), width="stretch")

    # ---------------- Distributors table (daily) ----------------
    st.subheader("🚚 Distributors — Daily Summary")
    dp_day = dist_purchases.copy()
    dpay_day = dist_payments.copy()
    dmap = distributors.copy()

    if not dp_day.empty:
        dp_day["date"] = pd.to_datetime(dp_day["date"], errors="coerce").dt.date
        dp_day = dp_day.loc[dp_day["date"] == dash_day].copy()
        dp_day["distributor_id"] = pd.to_numeric(dp_day.get("distributor_id", 0), errors="coerce").fillna(0).astype(int)
        dp_day["category_id"] = pd.to_numeric(dp_day.get("category_id", 0), errors="coerce").fillna(0).astype(int)
        dp_day["qty"] = pd.to_numeric(dp_day.get("qty", 0.0), errors="coerce").fillna(0.0).astype(float)
        dp_day["amount"] = pd.to_numeric(dp_day.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)
        dp_day["Category"] = dp_day["category_id"].map(cat_id_to_name).fillna("").astype(str)
    else:
        dp_day = pd.DataFrame(columns=["distributor_id", "category_id", "qty", "amount", "Category"])

    if not dpay_day.empty:
        dpay_day["date"] = pd.to_datetime(dpay_day["date"], errors="coerce").dt.date
        dpay_day = dpay_day.loc[dpay_day["date"] == dash_day].copy()
        dpay_day["distributor_id"] = pd.to_numeric(dpay_day.get("distributor_id", 0), errors="coerce").fillna(0).astype(int)
        dpay_day["amount"] = pd.to_numeric(dpay_day.get("amount", 0.0), errors="coerce").fillna(0.0).astype(float)
    else:
        dpay_day = pd.DataFrame(columns=["distributor_id", "amount"])

    if not dmap.empty:
        dmap["distributor_id"] = pd.to_numeric(dmap.get("distributor_id", 0), errors="coerce").fillna(0).astype(int)
        dmap["name"] = dmap.get("name", "").fillna("").astype(str)

    dsum = pd.DataFrame()
    if dp_day.empty and dpay_day.empty:
        st.info("No distributor purchases/payments for this date.")
    else:
        pur = dp_day.groupby("distributor_id").agg({"qty": "sum", "amount": "sum"}).rename(columns={"qty": "Purchased (L)", "amount": "Purchase Amount (₹)"})
        pay = dpay_day.groupby("distributor_id").agg({"amount": "sum"}).rename(columns={"amount": "Paid (₹)"})
        dsum = pur.join(pay, how="outer").fillna(0.0)

        if not dmap.empty:
            dsum = dsum.reset_index().merge(dmap[["distributor_id", "name"]], on="distributor_id", how="left").rename(columns={"name": "Distributor"})
        else:
            dsum = dsum.reset_index()
            dsum["Distributor"] = dsum["distributor_id"].astype(str)

        dsum["Outstanding (₹)"] = pd.to_numeric(dsum["Purchase Amount (₹)"], errors="coerce").fillna(0.0) - pd.to_numeric(dsum["Paid (₹)"], errors="coerce").fillna(0.0)
        dsum = dsum[["Distributor", "Purchased (L)", "Purchase Amount (₹)", "Paid (₹)", "Outstanding (₹)"]].sort_values("Purchase Amount (₹)", ascending=False)

        st.dataframe(
            dsum.style.format({"Purchased (L)": "{:.2f}", "Purchase Amount (₹)": "₹{:.2f}", "Paid (₹)": "₹{:.2f}", "Outstanding (₹)": "₹{:.2f}"}),
            width="stretch",
        )

    # ---- Build HTML report + Download ----
    pay_modes = pd.DataFrame(columns=["Mode", "Total (₹)"])
    if not p_day.empty:
        pay_modes = (
            p_day.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

    report_rows = []

    # Zone rows
    if not zone_pivot.empty:
        for z in zone_pivot.index.tolist():
            row = {"Name": str(z)}
            for c in cat_names:
                row[c] = float(pd.to_numeric(zone_pivot.loc[z].get(c, 0.0), errors="coerce") or 0.0)
            row["TOTAL (L)"] = float(pd.to_numeric(zone_pivot.loc[z].get("TOTAL (L)", 0.0), errors="coerce") or 0.0)
            today_sales = float(pd.to_numeric(zone_sales.get(z, 0.0), errors="coerce") or 0.0)
            prev_ledger = float(pd.to_numeric(zone_opening.get(z, 0.0), errors="coerce") or 0.0)
            paid = float(pd.to_numeric(zone_pay.get(z, 0.0), errors="coerce") or 0.0)
            row["Total Purchase Cost (₹)"] = today_sales
            row["Previous Ledger (₹)"] = prev_ledger
            row["Payment Given (₹)"] = paid
            row["Total Ledger (₹)"] = prev_ledger + today_sales - paid
            report_rows.append(row)

    # Divider row
    if report_rows and (not main_pivot.empty):
        report_rows.append({"Name": "—"})

    # Main retailer rows
    if not main_pivot.empty:
        for nm in main_pivot.index.tolist():
            row = {"Name": str(nm)}
            for c in cat_names:
                row[c] = float(pd.to_numeric(main_pivot.loc[nm].get(c, 0.0), errors="coerce") or 0.0)
            row["TOTAL (L)"] = float(pd.to_numeric(main_pivot.loc[nm].get("TOTAL (L)", 0.0), errors="coerce") or 0.0)
            today_sales = float(pd.to_numeric(main_sales_map.get(nm, 0.0), errors="coerce") or 0.0)
            prev_ledger = float(pd.to_numeric(opening_by_name.get(nm, 0.0), errors="coerce") or 0.0)
            paid = float(pd.to_numeric(main_pay_map.get(nm, 0.0), errors="coerce") or 0.0)
            row["Total Purchase Cost (₹)"] = today_sales
            row["Previous Ledger (₹)"] = prev_ledger
            row["Payment Given (₹)"] = paid
            row["Total Ledger (₹)"] = prev_ledger + today_sales - paid
            report_rows.append(row)

    retailer_totals = {
        "total_milk": float(pd.to_numeric(zone_pivot.get("TOTAL (L)", 0.0), errors="coerce").fillna(0.0).sum()) if not zone_pivot.empty else 0.0,
        "sales_amt": float(pd.to_numeric(zone_sales, errors="coerce").fillna(0.0).sum()) if not zone_sales.empty else 0.0,
        "paid_amt": float(pd.to_numeric(zone_pay, errors="coerce").fillna(0.0).sum()) if not zone_pay.empty else 0.0,
        "closing_ledger": float(pd.to_numeric(zone_opening, errors="coerce").fillna(0.0).sum()) + float(pd.to_numeric(zone_sales, errors="coerce").fillna(0.0).sum()) - float(pd.to_numeric(zone_pay, errors="coerce").fillna(0.0).sum()),
    }

    report_cols = [
        "Name",
    ] + cat_names + [
        "TOTAL (L)",
        "Total Purchase Cost (₹)",
        "Previous Ledger (₹)",
        "Payment Given (₹)",
        "Total Ledger (₹)",
    ]
    retailer_report_df = pd.DataFrame(report_rows)
    for c in report_cols:
        if c not in retailer_report_df.columns:
            retailer_report_df[c] = ""
    retailer_report_df = retailer_report_df[report_cols]
    # ---- TOTAL ROW ----

    tot = {"Name": "TOTAL"}

    for c in report_cols:

        if c == "Name":
            continue

        vals = pd.to_numeric(
            retailer_report_df[c],
            errors="coerce"
        ).fillna(0)

        tot[c] = vals.sum()

    retailer_report_df.loc[len(retailer_report_df)] = tot



    for c in cat_names + ["TOTAL (L)"]:
        retailer_report_df[c] = pd.to_numeric(retailer_report_df[c], errors="coerce").fillna(0.0).apply(lambda x: f"{float(x):.2f}" if float(x) != 0.0 else "–")
    for c in ["Total Purchase Cost (₹)", "Previous Ledger (₹)", "Payment Given (₹)", "Total Ledger (₹)"]:
        retailer_report_df[c] = pd.to_numeric(retailer_report_df[c], errors="coerce").fillna(0.0).apply(lambda x: _fmt_money(float(x)) if float(x) != 0.0 else "–")

    # Distributor report table with category columns
    dist_opening = {}
    if not dmap.empty:
        for did in sorted(set(dmap["distributor_id"].astype(int).tolist())):
            if int(did) <= 0:
                continue
            try:
                dist_opening[int(did)] = float(distributor_balance_before(int(did), dash_day))
            except Exception:
                dist_opening[int(did)] = 0.0

    dist_pivot = pd.DataFrame()
    if not dp_day.empty:
        dp_ok = dp_day.loc[dp_day["Category"].astype(str).str.len() > 0].copy()
        if not dp_ok.empty:
            dist_pivot = pd.pivot_table(
                dp_ok,
                index="distributor_id",
                columns="Category",
                values="qty",
                aggfunc="sum",
                fill_value=0.0,
            )

    dist_names = {}
    if not dmap.empty:
        dist_names = dict(zip(dmap["distributor_id"].astype(int).tolist(), dmap["name"].astype(str).tolist()))

    dist_rows = []
    all_dids = set(dist_names.keys()) | (set(dist_pivot.index.astype(int).tolist()) if not dist_pivot.empty else set())
    for did in sorted(all_dids):
        if int(did) <= 0:
            continue
        row = {"Name": dist_names.get(int(did), str(did))}
        for c in cat_names:
            row[c] = float(dist_pivot.loc[did].get(c, 0.0)) if (not dist_pivot.empty and did in dist_pivot.index) else 0.0
        row["TOTAL (L)"] = float(sum([row.get(c, 0.0) for c in cat_names]))
        today_purchase = float(pd.to_numeric(dp_day.loc[dp_day["distributor_id"] == int(did), "amount"], errors="coerce").fillna(0.0).sum()) if not dp_day.empty else 0.0
        prev_ledger = float(dist_opening.get(int(did), 0.0))
        paid = float(pd.to_numeric(dpay_day.loc[dpay_day["distributor_id"] == int(did), "amount"], errors="coerce").fillna(0.0).sum()) if not dpay_day.empty else 0.0
        row["Total Purchase Cost (₹)"] = today_purchase
        row["Previous Ledger (₹)"] = prev_ledger
        row["Payment Given (₹)"] = paid
        row["Total Ledger (₹)"] = prev_ledger + today_purchase - paid
        dist_rows.append(row)

    dist_report_df = pd.DataFrame(dist_rows)
    for c in report_cols:
        if c not in dist_report_df.columns:
            dist_report_df[c] = ""
    dist_report_df = dist_report_df[report_cols]
    # ---- TOTAL ROW ----

    tot = {"Name": "TOTAL"}

    for c in report_cols:

        if c == "Name":
            continue

        vals = pd.to_numeric(
            dist_report_df[c],
            errors="coerce"
        ).fillna(0)

        tot[c] = vals.sum()

    dist_report_df.loc[len(dist_report_df)] = tot


    for c in cat_names + ["TOTAL (L)"]:
        dist_report_df[c] = pd.to_numeric(dist_report_df[c], errors="coerce").fillna(0.0).apply(lambda x: f"{float(x):.2f}" if float(x) != 0.0 else "–")
    for c in ["Total Purchase Cost (₹)", "Previous Ledger (₹)", "Payment Given (₹)", "Total Ledger (₹)"]:
        dist_report_df[c] = pd.to_numeric(dist_report_df[c], errors="coerce").fillna(0.0).apply(lambda x: _fmt_money(float(x)) if float(x) != 0.0 else "–")

    distributor_totals = {
        "total_milk": float(pd.to_numeric(dp_day.get("qty", 0.0), errors="coerce").fillna(0.0).sum()) if not dp_day.empty else 0.0,
        "purchase_amt": float(pd.to_numeric(dp_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) if not dp_day.empty else 0.0,
        "paid_amt": float(pd.to_numeric(dpay_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) if not dpay_day.empty else 0.0,
        "closing_ledger": float(sum(dist_opening.values())) + float(pd.to_numeric(dp_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) - float(pd.to_numeric(dpay_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()),
    }

    purchased_qty = float(pd.to_numeric(dp_day.get("qty", 0.0), errors="coerce").fillna(0.0).sum()) if not dp_day.empty else 0.0
    purchased_amt = float(pd.to_numeric(dp_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) if not dp_day.empty else 0.0
    sold_qty = float(pd.to_numeric(e_day.get("qty", 0.0), errors="coerce").fillna(0.0).sum()) if not e_day.empty else 0.0
    sold_amt = float(pd.to_numeric(e_day.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) if not e_day.empty else 0.0

    wz = wastage.copy()
    waste_qty = 0.0
    waste_loss = 0.0
    if not wz.empty:
        wz["date"] = pd.to_datetime(wz.get("date"), errors="coerce").dt.date
        wz_day = wz.loc[wz["date"] == dash_day].copy()
        if not wz_day.empty:
            waste_qty = float(pd.to_numeric(wz_day.get("qty", 0.0), errors="coerce").fillna(0.0).sum())
            waste_loss = float(pd.to_numeric(wz_day.get("estimated_loss", 0.0), errors="coerce").fillna(0.0).sum())

    
    html_report = None

    try:
        html_report = build_daily_report_html(
            report_day=dash_day,
            retailer_table=retailer_report_df,
            retailer_totals=retailer_totals,
            retailer_pay_modes=pay_modes,
            distributor_table=dist_report_df,
            distributor_totals=distributor_totals,
            purchased_qty=purchased_qty,
            purchased_amt=purchased_amt,
            sold_qty=sold_qty,
            sold_amt=sold_amt,
            waste_qty=waste_qty,
            waste_loss=waste_loss,
            show_cards=True,
        )

    except Exception as _e:
        st.error(f"Daily report generation failed: {_e}")

    if html_report:
        st.download_button(
            label="⬇ Download Daily Report (HTML)",
            data=html_report.encode("utf-8"),
            file_name=f"Milk_Report_{dash_day}.html",
            mime="text/html",
            use_container_width=True,
        )
        st.caption("Open the downloaded HTML and press Ctrl+P to print / save as PDF.")



        # ===== ZONE SUMMARY (FINAL PREVIEW STYLE) =====

        html_all = ""

        zones = get_all_zones()

        for z in zones:

            rids = get_zone_retailer_ids(z)

            if not rids:
                continue

            # ---------------- PREVIEW GRID ----------------

            grid_df, cat_cols = build_daily_posting_grid(
                dash_day,
                z,
                retailers_active,
                categories_active,
            )

            if grid_df is None or grid_df.empty:
                continue

            preview_df = grid_df.copy()

            rid_list = preview_df["ID"].astype(int).tolist()

            ledger_map = cached_opening_balances(
                tuple(rid_list),
                dash_day,
                st.session_state["data_version"],
            )

            today_sales_list = []
            prev_ledger_list = []
            total_ledger_list = []

            for _, row in preview_df.iterrows():

                rid = int(row["ID"])

                prev_ledger = ledger_map.get(rid, 0.0)

                today_sales = 0.0

                for meta in cat_cols:

                    col = meta["col"]
                    cid = int(meta["category_id"])

                    qty = float(row.get(col, 0.0) or 0.0)

                    if qty <= 0:
                        continue

                    rate = get_price_for_date(
                        rid,
                        cid,
                        dash_day,
                    ) or 0.0

                    today_sales += qty * float(rate)

                today_pay = 0.0

                for m in PAYMENT_MODES:
                    today_pay += float(
                        row.get(f"{m} ₹", 0.0) or 0.0
                    )

                total_ledger = (
                    prev_ledger
                    + today_sales
                    - today_pay
                )

                prev_ledger_list.append(prev_ledger)
                today_sales_list.append(today_sales)
                total_ledger_list.append(total_ledger)

            preview_df["Previous Ledger ₹"] = prev_ledger_list
            preview_df["Today Sales ₹"] = today_sales_list
            preview_df["Total Ledger ₹"] = total_ledger_list

            # ---------- ADD TOTAL ROW ----------

            total_row = {}

            for col in preview_df.columns:

                if col in ["Retailer", "Name", "ID"]:
                    total_row[col] = "TOTAL"
                    continue

                vals = pd.to_numeric(
                    preview_df[col],
                    errors="coerce"
                ).fillna(0.0)

                total_row[col] = float(vals.sum())

            preview_df = pd.concat(
                [preview_df, pd.DataFrame([total_row])],
                ignore_index=True
            )


            # ---------------- FILTER DAY DATA ----------------

            ez = e_day[e_day["retailer_id"].isin(rids)].copy()
            pz = p_day[p_day["retailer_id"].isin(rids)].copy()

            sold_qty = float(ez["qty"].sum()) if not ez.empty else 0.0
            sold_amt = float(ez["amount"].sum()) if not ez.empty else 0.0

            purchased_qty = float(dp_day["qty"].sum()) if not dp_day.empty else 0.0
            purchased_amt = float(dp_day["amount"].sum()) if not dp_day.empty else 0.0

            # ---------------- PAYMENT MODES ----------------

            if not pz.empty:

                pay_modes = (
                    pz.groupby("payment_mode")["amount"]
                    .sum()
                    .reset_index()
                )

            else:

                pay_modes = pd.DataFrame(
                    columns=["payment_mode", "amount"]
                )

            # ---------------- HTML ----------------
            
            
            
            # ----- FIX COLUMN ORDER FOR HTML -----
            base_cols = [c for c in ["ID", "Retailer", "Name"] if c in preview_df.columns]
            category_cols = [
                c for c in preview_df.columns
                if c not in base_cols
                and "₹" not in c
                and "Ledger" not in c
                and "Total" not in c
            ]
            sales_cols = [c for c in preview_df.columns if "TOTAL" in c or "Sales" in c]
            
            prev_cols = [c for c in preview_df.columns if "Previous Ledger" in c]
            
            payment_cols = [c for c in preview_df.columns if "₹" in c and "Ledger" not in c and "Sales" not in c]
            
            ledger_cols = [c for c in preview_df.columns if "Total Ledger" in c]
            
            new_order = (
                base_cols
                + category_cols
                + sales_cols
                + prev_cols
                + payment_cols
                + ledger_cols
            )
            
            preview_df = preview_df[new_order]
            
            html_zone = build_daily_report_html(
                report_day=dash_day,
                retailer_table=preview_df,
                retailer_totals=None,
                retailer_pay_modes=pay_modes,
                distributor_table=pd.DataFrame(),
                distributor_totals={},
                purchased_qty=purchased_qty,
                purchased_amt=purchased_amt,
                sold_qty=sold_qty,
                sold_amt=sold_amt,
                waste_qty=waste_qty,
                waste_loss=waste_loss,
                show_cards=False,
            )

            html_zone = html_zone.replace(
                "Daily Business Summary",
                f"Zone Summary — {z}",
            )

            html_all += html_zone
            html_all += '<div style="page-break-after:always"></div>'

        if html_all:    
            st.download_button(
                label="⬇ Download Zone Summary (HTML)",
                data=html_all,
                file_name=f"Zone_Summary_{dash_day}.html",
                 mime="text/html",
                key=f"zone_dl_{z}"
            )
        
            st.divider()

        st.subheader("📅 Daily Business Overview")
  
        day = st.date_input("Select Day", value=date.today(), key="daily_overview_day")

        dp = dist_purchases.copy()
        if not dp.empty:
            dp["date"] = pd.to_datetime(dp["date"], errors="coerce")
            dp_day = dp.loc[dp["date"].dt.date == day].copy()
            purchased_qty = float(dp_day["qty"].sum()) if not dp_day.empty else 0.0
            purchased_amt = float(dp_day["amount"].sum()) if not dp_day.empty else 0.0
        else:
            purchased_qty, purchased_amt = 0.0, 0.0

        ez = entries_z.copy()
        if not ez.empty:
            ez["date"] = pd.to_datetime(ez["date"], errors="coerce")
            ez_day = ez.loc[ez["date"].dt.date == day].copy()
            sold_qty = float(ez_day["qty"].sum()) if not ez_day.empty else 0.0
            sold_amt = float(ez_day["amount"].sum()) if not ez_day.empty else 0.0
        else:
            sold_qty, sold_amt = 0.0, 0.0

        wz = wastage.copy()
        if not wz.empty:
            wz["date"] = pd.to_datetime(wz["date"], errors="coerce")
            wz_day = wz.loc[wz["date"].dt.date == day].copy()
            waste_qty = float(wz_day["qty"].sum()) if not wz_day.empty else 0.0
            waste_loss = float(wz_day["estimated_loss"].sum()) if not wz_day.empty else 0.0
        else:
            waste_qty, waste_loss = 0.0, 0.0

        net_movement = purchased_qty - sold_qty - waste_qty

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Purchased (L)", f"{purchased_qty:.2f}")
        c2.metric("Purchase (₹)", f"₹{purchased_amt:.2f}")
        c3.metric("Sold (L)", f"{sold_qty:.2f}")
        c4.metric("Sales (₹)", f"₹{sold_amt:.2f}")
        c5.metric("Wastage (L)", f"{waste_qty:.2f}")
        c6.metric("Net Movement (L)", f"{net_movement:.2f}")

        if net_movement < 0:
            st.warning("Net Movement is negative. Purchases might be missing for the day, or you sold from opening stock (not tracked).")

        st.caption("Sales are zone-filtered. Purchases/wastage are not zone-filtered in current model.")

        st.divider()
    

elif menu == "📝 Daily Posting Sheet (Excel)":
    st.header("📝 Daily Posting Sheet — Retailers + Distributors + Wastage (Single Save)")

    if retailers_active.empty or categories_active.empty:
        st.warning("⚠️ Please add active retailers and categories first")
        st.stop()

    posting_date = st.date_input("Posting Date", value=date.today(), key="posting_date")
    report_day = posting_date
    zone_choices = ["All Zones"] + get_all_zones()
    default_idx = zone_choices.index(selected_zone) if selected_zone in zone_choices else 0
    posting_zone = st.selectbox("Posting Zone", zone_choices, index=default_idx, key="posting_zone")

    # ================== DRAFT STATE (per date + zone) ==================
    def _ctx_key(d: date, z: str) -> str:
        return f"{str(d)}|{_norm_zone(z)}"

    ctx = _ctx_key(posting_date, posting_zone)
    st.session_state.setdefault("daily_drafts", {})
    st.session_state.setdefault("daily_meta", {})
    st.session_state.setdefault("daily_loaded_ctx", None)
    st.session_state.setdefault("daily_save_lock", False)
    st.session_state.setdefault("dist_flat_grid", pd.DataFrame())
    st.session_state.setdefault("dist_flat_payments", pd.DataFrame())

    # Load from DB when context changes
    if st.session_state.get("daily_loaded_ctx") != ctx or ctx not in st.session_state["daily_drafts"]:
        grid_df, cat_cols = build_daily_posting_grid(posting_date, posting_zone, retailers_active, categories_active)
        if grid_df is None or grid_df.empty:
            st.warning("No retailers found for selected zone.")
            st.stop()

        rz = retailers_active.copy()
        rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
        if posting_zone != "All Zones":
            rz = rz.loc[rz["zone"] == _norm_zone(posting_zone)].copy()
        affected_rids = sorted(set(rz["retailer_id"].astype(int).tolist()))

        st.session_state["daily_drafts"][ctx] = grid_df.copy()
        st.session_state["daily_meta"][ctx] = {"cat_cols": cat_cols, "affected_rids": affected_rids}
        st.session_state["daily_loaded_ctx"] = ctx

    cat_cols = (st.session_state["daily_meta"].get(ctx, {}) or {}).get("cat_cols", [])
    affected_rids = (st.session_state["daily_meta"].get(ctx, {}) or {}).get("affected_rids", [])

    draft_df = st.session_state["daily_drafts"].get(ctx)
    if draft_df is None or draft_df.empty:
        st.warning("Draft is empty. Please refresh.")
        st.stop()

    cat_col_names = [m["col"] for m in cat_cols if m.get("col") in draft_df.columns]
    pay_cols = [f"{m} ₹" for m in PAYMENT_MODES if f"{m} ₹" in draft_df.columns]

    ordered_cols = [c for c in ["ID", "Retailer"] if c in draft_df.columns] + cat_col_names + pay_cols
    extras = [c for c in draft_df.columns if c not in ordered_cols]
    draft_df = draft_df[ordered_cols + extras]

    # ================== SAVE HELPERS ==================
    def _sb_insert_records(table: str, records: list[dict], chunk: int = 500) -> None:
        if not records:
            return
        sb = get_sb()
        for i in range(0, len(records), chunk):
            sb.table(table).insert(records[i:i + chunk]).execute()

    def _sb_delete_day_zone(table: str, d: date, rids: list[int], chunk: int = 500) -> None:
        if not rids:
            return
        sb = get_sb()
        for i in range(0, len(rids), chunk):
            sb.table(table).delete().eq("date", str(d)).in_("retailer_id", rids[i:i + chunk]).execute()

    def _safe_replace_entries_payments(d: date, z: str, edited_df: pd.DataFrame) -> None:
        if not affected_rids:
            raise RuntimeError("No retailers found for selected zone.")

        old_e = _day_entries_for_zone(d, z)
        old_p = _day_payments_for_zone(d, z)

        new_entries = []
        new_payments = []
        col_to_cid = {m["col"]: int(m["category_id"]) for m in cat_cols}

        for _, row in edited_df.iterrows():
            rid_val = row.get("ID", "")
            if str(rid_val).strip() in ("", "GRAND TOTAL"):
                continue
            try:
                rid = int(rid_val)
            except Exception:
                continue
            if rid not in set(affected_rids):
                continue

            for col, cid in col_to_cid.items():
                qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
                if qty <= 0:
                    continue
                rate = get_price_for_date(rid, cid, d)
                if rate is None or float(rate) <= 0:
                    raise RuntimeError(f"Missing price for Retailer ID {rid} / Category ID {cid} on {d}")
                rate = float(rate)
                amt = round(float(qty * rate), 2)
                new_entries.append({
                    "date": str(d),
                    "retailer_id": rid,
                    "category_id": cid,
                    "qty": round(qty, 4),
                    "rate": round(rate, 4),
                    "amount": amt,
                })

            for m in PAYMENT_MODES:
                pamt = float(pd.to_numeric(row.get(f"{m} ₹", 0.0), errors="coerce") or 0.0)
                if pamt <= 0:
                    continue
                new_payments.append({
                    "date": str(d),
                    "retailer_id": rid,
                    "amount": round(pamt, 2),
                    "payment_mode": str(m).strip().upper(),
                    "note": "",
                })

        if USE_DB_IDS:
            next_eid = sb_next_id("entries", "entry_id")
            for rec in new_entries:
                rec["entry_id"] = next_eid
                next_eid += 1
            next_pid = sb_next_id("payments", "payment_id")
            for rec in new_payments:
                rec["payment_id"] = next_pid
                next_pid += 1
        else:
            for rec in new_entries:
                rec.pop("entry_id", None)
            for rec in new_payments:
                rec.pop("payment_id", None)

        try:
            _sb_delete_day_zone("entries", d, affected_rids)
            _sb_delete_day_zone("payments", d, affected_rids)
            _sb_insert_records("entries", new_entries)
            _sb_insert_records("payments", new_payments)
            invalidate_data_cache()
        except Exception as e:
            try:
                _sb_delete_day_zone("entries", d, affected_rids)
                _sb_delete_day_zone("payments", d, affected_rids)
                if old_e is not None and not old_e.empty:
                    recs = old_e.where(pd.notna(old_e), None).to_dict(orient="records")
                    if not USE_DB_IDS:
                        for r in recs:
                            r.pop("entry_id", None)
                    _sb_insert_records("entries", recs)
                if old_p is not None and not old_p.empty:
                    recs = old_p.where(pd.notna(old_p), None).to_dict(orient="records")
                    if not USE_DB_IDS:
                        for r in recs:
                            r.pop("payment_id", None)
                    _sb_insert_records("payments", recs)
            except Exception:
                pass
            raise e

    # ================== RETAILER GRID (AG Grid form) ==================
    lock = bool(st.session_state.get("daily_save_lock", False))
    if lock:
        st.info("⏳ Saving… please do not interact with the page.")

    form_key = f"daily_form_{ctx}"
    rows_count = len(draft_df) if draft_df is not None else 1
    table_height = min(900, 120 + rows_count * 42)

    with st.form(form_key, clear_on_submit=False):
        gb = GridOptionsBuilder.from_dataframe(draft_df)

        numeric_editor = JsCode("""
        class NumericEditor {
            init(params) {
                this.eInput = document.createElement('input');
                this.eInput.type = 'number';
                this.eInput.step = '0.25';
                this.eInput.min = '0';
                this.eInput.style.width = '100%';
                this.eInput.value = params.value || 0;
            }
            getGui() { return this.eInput; }
            afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
            getValue() { return parseFloat(this.eInput.value) || 0; }
        }
        """)

        for col in cat_col_names + pay_cols:
            if col in draft_df.columns:
                gb.configure_column(col, editable=True, valueParser="Number(newValue)", cellEditor=numeric_editor)

        gb.configure_default_column(editable=True, sortable=False, filter=False, resizable=True, minWidth=60, singleClickEdit=True)
        gb.configure_column("ID", pinned="left", editable=False, width=80)
        gb.configure_column("Retailer", pinned="left", editable=False, minWidth=220, maxWidth=350)

        for col in draft_df.columns:
            gb.configure_column(col, wrapHeaderText=True, autoHeaderHeight=True)

        gb.configure_grid_options(
            domLayout="normal",
            suppressMovableColumns=True,
            alwaysShowHorizontalScroll=True,
            alwaysShowVerticalScroll=True,
            headerHeight=42,
            rowHeight=42,
            singleClickEdit=True,
            stopEditingWhenCellsLoseFocus=True,
            enterMovesDown=True,
            enterMovesDownAfterEdit=True,
        )

        grid_options = gb.build()
        grid_options["onFirstDataRendered"] = JsCode("""
        function(params) {
            setTimeout(function() {
                var allColumnIds = [];
                params.columnApi.getColumns().forEach(function(col) { allColumnIds.push(col.getId()); });
                params.columnApi.autoSizeColumns(allColumnIds, false);
            }, 300);
        }
        """)

        ag_result = AgGrid(
            draft_df,
            gridOptions=grid_options,
            update_mode="MODEL_CHANGED",
            height=table_height,
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True,
            theme="streamlit",
            use_container_width=True,
        )

        edited = pd.DataFrame(ag_result["data"])
        do_save_all = st.form_submit_button("💾 Save All (Retailers + Distributors + Wastage)", type="primary", disabled=lock)

    # Persist edited grid into draft state immediately
    if isinstance(edited, pd.DataFrame) and not edited.empty:
        st.session_state["daily_drafts"][ctx] = edited.copy()

    # ================== RETAILER PREVIEW (computed once, used everywhere) ==================
    _draft = st.session_state["daily_drafts"][ctx].copy()
    rid_list = [int(x) for x in _draft["ID"].tolist() if str(x).strip() not in ("", "nan")]

    ledger_map = cached_opening_balances(
        tuple(rid_list),
        report_day,
        st.session_state["data_version"],
    )

    # Build preview with ledger columns (single computation, no duplication)
    today_sales_list, prev_ledger_list, total_ledger_list = [], [], []
    for _, row in _draft.iterrows():
        rid_val = row.get("ID", "")
        try:
            rid = int(rid_val)
        except Exception:
            today_sales_list.append(0.0)
            prev_ledger_list.append(0.0)
            total_ledger_list.append(0.0)
            continue

        prev_ledger = float(ledger_map.get(rid, 0.0))
        today_sales = 0.0
        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
            if qty <= 0:
                continue
            rate = get_price_for_date(rid, cid, posting_date) or 0.0
            today_sales += float(qty) * float(rate)
        today_pay = sum(float(pd.to_numeric(row.get(f"{m} ₹", 0.0), errors="coerce") or 0.0) for m in PAYMENT_MODES)
        total_ledger = prev_ledger + today_sales - today_pay
        today_sales_list.append(today_sales)
        prev_ledger_list.append(prev_ledger)
        total_ledger_list.append(total_ledger)

    preview = _draft.copy()
    preview["Today Sales ₹"] = today_sales_list
    preview["Previous Ledger ₹"] = prev_ledger_list
    preview["Total Ledger ₹"] = total_ledger_list

    # Grand total row (exclude it from totals computation later)
    _grand = {"ID": "", "Retailer": "GRAND TOTAL"}
    for col in preview.columns:
        if col in ("ID", "Retailer"):
            continue
        _grand[col] = safe_scalar_sum(pd.to_numeric(preview[col], errors="coerce").fillna(0.0))
    preview = pd.concat([preview, pd.DataFrame([_grand])], ignore_index=True)

    # Column order
    _ordered = (
        [c for c in ["ID", "Retailer"] if c in preview.columns]
        + cat_col_names
        + ["Today Sales ₹", "Previous Ledger ₹"]
        + [f"{m} ₹" for m in PAYMENT_MODES if f"{m} ₹" in preview.columns]
        + ["Total Ledger ₹"]
    )
    _extras = [c for c in preview.columns if c not in _ordered]
    preview = preview[[c for c in _ordered + _extras if c in preview.columns]]

    # ================== STYLED HTML PREVIEW TABLE ==================
    st.subheader("📌 Retailer Preview")

    def _build_grouped_html(df: pd.DataFrame, _cat_col_names: list, _pay_modes: list, grand_label="GRAND TOTAL") -> str:
        _money_cols = {"Today Sales ₹", "Previous Ledger ₹", "Total Ledger ₹"} | {f"{m} ₹" for m in _pay_modes}

        def _fmt(col, val):
            try:
                fv = float(val)
            except Exception:
                s = str(val)
                return "–" if s in ("nan", "None", "", "0.0") else s
            if fv == 0.0:
                return "–"
            return f"₹{fv:,.2f}" if col in _money_cols else f"{fv:.2f}"

        cols = [c for c in df.columns if c != "ID"]
        header = "".join(f"<th style='padding:8px 10px;text-align:{'left' if c == 'Retailer' else 'right'};white-space:nowrap;'>{c}</th>" for c in cols)
        rows_html = ""
        for i, (_, row) in enumerate(df.iterrows()):
            is_total = str(row.get("Retailer", "")) == grand_label
            bg = "#1a472a" if is_total else ("#f0fdf4" if i % 2 == 0 else "#ffffff")
            fg = "#ffffff" if is_total else "#0f172a"
            fw = "900" if is_total else "400"
            cells = ""
            for c in cols:
                val = row.get(c, "")
                display = str(val) if (is_total and c == "Retailer") else _fmt(c, val)
                align = "left" if c == "Retailer" else "right"
                cells += (
                    f"<td style='padding:6px 10px;text-align:{align};font-weight:{fw};"
                    f"border-bottom:1px solid #e2e8f0;'>{display}</td>"
                )
            rows_html += f"<tr style='background:{bg};color:{fg};'>{cells}</tr>"

        return (
            f"<div style='overflow-x:auto;border-radius:12px;border:1px solid #e2e8f0;"
            f"box-shadow:0 4px 12px rgba(0,0,0,0.06);margin-bottom:16px;'>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px;font-family:system-ui,sans-serif;'>"
            f"<thead><tr style='background:#1e293b;color:#fff;'>{header}</tr></thead>"
            f"<tbody>{rows_html}</tbody></table></div>"
        )

    st.markdown(
        _build_grouped_html(preview, cat_col_names, PAYMENT_MODES),
        unsafe_allow_html=True,
    )

    st.subheader("🧾 Daily Totals")

    # ✅ ALWAYS compute from RAW draft (numeric), never from formatted preview
    _totals_src_raw = st.session_state["daily_drafts"][ctx].copy()
    # Exclude any sentinel/grand-total rows
    _totals_src_raw = _totals_src_raw[~_totals_src_raw.get("Retailer", pd.Series(dtype=str)).astype(str).isin(["GRAND TOTAL", ""])]

    cat_qty_totals = {}
    for meta in cat_cols:
        col = meta["col"]
        label = meta.get("name") or col
        if col in _totals_src_raw.columns:
            cat_qty_totals[label] = round(
                float(pd.to_numeric(_totals_src_raw[col], errors="coerce").fillna(0.0).sum()), 3
            )

    grand_qty = round(float(sum(cat_qty_totals.values())), 3)

    # Sales: compute from qty × price_lookup (raw numeric, not formatted strings)
    grand_sales = 0.0
    for _, row in _totals_src_raw.iterrows():
        rid_val = row.get("ID", "")
        try:
            rid = int(rid_val)
        except Exception:
            continue
        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
            if qty <= 0:
                continue
            rate = get_price_for_date(rid, cid, posting_date) or 0.0
            grand_sales += qty * float(rate)
    grand_sales = round(grand_sales, 2)

    pay_mode_totals_dict = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in _totals_src_raw.columns:
            pay_mode_totals_dict[m] = round(
                float(pd.to_numeric(_totals_src_raw[pcol], errors="coerce").fillna(0.0).sum()), 2
            )

    grand_pay = round(float(sum(pay_mode_totals_dict.values())), 2)

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Milk Distributed (L)", f"{grand_qty:.2f}")
    mc2.metric("Today Sales (₹)", _fmt_money(grand_sales))
    mc3.metric("Payments Collected (₹)", _fmt_money(grand_pay))

    if cat_qty_totals:
        _tot_row = {"": "Qty (L)", **{k: f"{v:.2f}" if v > 0 else "–" for k, v in cat_qty_totals.items()}, "TOTAL": f"{grand_qty:.2f}"}
        st.dataframe(df_for_display(pd.DataFrame([_tot_row])), use_container_width=True)

    if pay_mode_totals_dict:
        _pay_row = {"": "Payment (₹)", **{k: _fmt_money(v) if v > 0 else "–" for k, v in pay_mode_totals_dict.items()}, "TOTAL": _fmt_money(grand_pay)}
        st.dataframe(df_for_display(pd.DataFrame([_pay_row])), use_container_width=True)

    # ================== DISTRIBUTOR DAILY ENTRY (flat grid) ==================
    st.divider()
    st.subheader("📦 Distributor Daily Entry")

    distributors_active = distributors.copy()
    if not distributors_active.empty and "is_active" in distributors_active.columns:
        distributors_active["is_active"] = distributors_active["is_active"].apply(parse_boolish_active)
        distributors_active = distributors_active.loc[distributors_active["is_active"] == True].copy()

    if distributors_active.empty:
        st.info("No active distributors. Add distributors first.")
        st.session_state["dist_flat_grid"] = pd.DataFrame()
        st.session_state["dist_flat_payments"] = pd.DataFrame()
    else:
        # Build mapping-driven (distributor, category) grid rows
        _m = dist_cat_map.copy() if dist_cat_map is not None else pd.DataFrame()
        if not _m.empty:
            _m["distributor_id"] = pd.to_numeric(_m["distributor_id"], errors="coerce").fillna(0).astype(int)
            _m["category_id"] = pd.to_numeric(_m["category_id"], errors="coerce").fillna(0).astype(int)
            _m["is_active"] = _m.get("is_active", True).apply(parse_boolish_active)
            _m = _m.loc[_m["is_active"] == True, ["distributor_id", "category_id"]]

        _d_lookup = dict(zip(distributors_active["distributor_id"].astype(int), distributors_active["name"].astype(str)))
        _c_lookup = dict(zip(categories_active["category_id"].astype(int), categories_active["name"].astype(str)))

        _grid_rows = []
        for _, _row in _m.iterrows():
            _did = int(_row["distributor_id"])
            _cid = int(_row["category_id"])
            if _did not in _d_lookup or _cid not in _c_lookup:
                continue
            _grid_rows.append({"DID": _did, "CID": _cid, "Distributor": _d_lookup[_did], "Category": _c_lookup[_cid], "Qty A": 0.0, "Rate A": 0.0, "Qty B": 0.0, "Rate B": 0.0})

        _dist_grid_df = pd.DataFrame(_grid_rows).sort_values(["Distributor", "Category"]).reset_index(drop=True)

        if _dist_grid_df.empty:
            st.warning("⚠️ No distributor-category mappings found. Go to '🧩 Distributor Category Mapping'.")
            st.session_state["dist_flat_grid"] = pd.DataFrame()
            st.session_state["dist_flat_payments"] = pd.DataFrame()
        else:
            # Prefill from today's saved purchases
            _today_dp = sb_fetch_df(
                DISTRIBUTOR_PURCHASES_FILE, CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
                filters=[("date", "eq", str(posting_date))],
            )
            if not _today_dp.empty:
                _t = _today_dp.copy()
                _t["distributor_id"] = pd.to_numeric(_t["distributor_id"], errors="coerce").fillna(0).astype(int)
                _t["category_id"] = pd.to_numeric(_t["category_id"], errors="coerce").fillna(0).astype(int)
                _t["qty"] = pd.to_numeric(_t["qty"], errors="coerce").fillna(0.0)
                _t["rate"] = pd.to_numeric(_t["rate"], errors="coerce").fillna(0.0)
                for (_did, _cid), _grp in _t.groupby(["distributor_id", "category_id"]):
                    _mask = (_dist_grid_df["DID"] == _did) & (_dist_grid_df["CID"] == _cid)
                    if _mask.any():
                        _idx = _dist_grid_df.index[_mask][0]
                        _sorted_rows = _grp.sort_values("rate").reset_index(drop=True)
                        if len(_sorted_rows) >= 1:
                            _dist_grid_df.loc[_idx, "Qty A"] = float(_sorted_rows.iloc[0]["qty"])
                            _dist_grid_df.loc[_idx, "Rate A"] = float(_sorted_rows.iloc[0]["rate"])
                        if len(_sorted_rows) >= 2:
                            _dist_grid_df.loc[_idx, "Qty B"] = float(_sorted_rows.iloc[1]["qty"])
                            _dist_grid_df.loc[_idx, "Rate B"] = float(_sorted_rows.iloc[1]["rate"])

            # Compute line totals for display
            _display_df = _dist_grid_df.drop(columns=["DID", "CID"]).copy()
            _display_df["Line Total ₹"] = (
                _display_df["Qty A"].astype(float) * _display_df["Rate A"].astype(float)
                + _display_df["Qty B"].astype(float) * _display_df["Rate B"].astype(float)
            ).round(2)

            _gb = GridOptionsBuilder.from_dataframe(_display_df)
            _num_ed = JsCode("""
            class NumericEditor {
                init(params) {
                    this.eInput = document.createElement('input');
                    this.eInput.type = 'number'; this.eInput.step = '0.25'; this.eInput.min = '0';
                    this.eInput.style.width = '100%'; this.eInput.value = params.value || 0;
                }
                getGui() { return this.eInput; }
                afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
                getValue() { return parseFloat(this.eInput.value) || 0; }
            }
            """)
            for _c in ["Qty A", "Rate A", "Qty B", "Rate B"]:
                _gb.configure_column(_c, editable=True, cellEditor=_num_ed, width=100)
            _gb.configure_column("Distributor", pinned="left", editable=False, minWidth=140)
            _gb.configure_column("Category", pinned="left", editable=False, minWidth=130)
            _gb.configure_column("Line Total ₹", editable=False, width=130,
                                 valueFormatter=JsCode("function(p){return '₹'+(Number(p.value)||0).toFixed(2);}"))
            _gb.configure_default_column(sortable=False, filter=False, resizable=True, singleClickEdit=True)
            _gb.configure_grid_options(
                singleClickEdit=True, stopEditingWhenCellsLoseFocus=True,
                headerHeight=40, rowHeight=40, enterMovesDown=True, enterMovesDownAfterEdit=True,
            )
            _grid_opts = _gb.build()
            _grid_opts["onCellValueChanged"] = JsCode("""
            function(params) {
                var d = params.data;
                var total = (parseFloat(d['Qty A'])||0)*(parseFloat(d['Rate A'])||0)
                          + (parseFloat(d['Qty B'])||0)*(parseFloat(d['Rate B'])||0);
                d['Line Total ₹'] = Math.round(total*100)/100;
                params.api.refreshCells({rowNodes:[params.node], columns:['Line Total ₹']});
            }
            """)

            _dist_result = AgGrid(
                _display_df,
                gridOptions=_grid_opts,
                update_mode="MODEL_CHANGED",
                height=min(120 + len(_display_df) * 42, 600),
                fit_columns_on_grid_load=False,
                allow_unsafe_jscode=True,
                theme="streamlit",
                use_container_width=True,
                key=f"dist_grid_{posting_date}",
            )

            _dist_edited = pd.DataFrame(_dist_result["data"])
            _dist_edited["DID"] = _dist_grid_df["DID"].values
            _dist_edited["CID"] = _dist_grid_df["CID"].values
            st.session_state["dist_flat_grid"] = _dist_edited.copy()

            # Distributor payments table (one row per distributor)
            st.markdown("**💳 Distributor Payments Today**")
            _today_dpay = sb_fetch_df(
                DISTRIBUTOR_PAYMENTS_FILE, CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
                filters=[("date", "eq", str(posting_date))],
            )
            _pay_by_did = {}
            if not _today_dpay.empty:
                for _, _pr in _today_dpay.iterrows():
                    _did_ = int(_pr["distributor_id"])
                    _pay_by_did[_did_] = {
                        "amt": float(_pr.get("amount", 0.0) or 0.0),
                        "mode": str(_pr.get("payment_mode", "Cash") or "Cash"),
                        "note": str(_pr.get("note", "") or ""),
                    }

            _pay_rows = []
            for _, _drow in distributors_active.sort_values("name").iterrows():
                _did_ = int(_drow["distributor_id"])
                _prev_due = float(distributor_balance_before(_did_, posting_date))
                _p = _pay_by_did.get(_did_, {})
                _pay_rows.append({
                    "DID": _did_,
                    "Distributor": str(_drow["name"]),
                    "Previous Due ₹": round(_prev_due, 2),
                    "Amount ₹": _p.get("amt", 0.0),
                    "Mode": _p.get("mode", "Cash"),
                    "Note": _p.get("note", ""),
                })
            _pay_df = pd.DataFrame(_pay_rows)

            _pay_edit = st.data_editor(
                _pay_df.drop(columns=["DID"]),
                column_config={
                    "Distributor":    st.column_config.TextColumn("Distributor", disabled=True),
                    "Previous Due ₹": st.column_config.NumberColumn("Previous Due ₹", disabled=True, format="₹%.2f"),
                    "Amount ₹":       st.column_config.NumberColumn("Amount ₹", min_value=0.0, step=50.0, format="%.2f"),
                    "Mode":           st.column_config.SelectboxColumn("Mode", options=["Cash", "UPI", "Bank", "Cheque", "Other"]),
                    "Note":           st.column_config.TextColumn("Note"),
                },
                num_rows="fixed",
                hide_index=True,
                use_container_width=True,
                key=f"dist_pay_editor_{posting_date}",
            )
            _pay_edit_out = _pay_edit.copy()
            _pay_edit_out["DID"] = _pay_df["DID"].values
            st.session_state["dist_flat_payments"] = _pay_edit_out.copy()

    # ================== DISTRIBUTOR DAILY TOTALS ==================
    st.subheader("🧾 Distributor Daily Totals")

    _dist_grid_data_preview = st.session_state.get("dist_flat_grid", pd.DataFrame())
    _dist_pay_data_preview  = st.session_state.get("dist_flat_payments", pd.DataFrame())

    _dist_total_milk = 0.0
    _dist_total_purchase = 0.0

    if isinstance(_dist_grid_data_preview, pd.DataFrame) and not _dist_grid_data_preview.empty:
        for _, _dr in _dist_grid_data_preview.iterrows():
            _qa = float(pd.to_numeric(_dr.get("Qty A", 0.0), errors="coerce") or 0.0)
            _ra = float(pd.to_numeric(_dr.get("Rate A", 0.0), errors="coerce") or 0.0)
            _qb = float(pd.to_numeric(_dr.get("Qty B", 0.0), errors="coerce") or 0.0)
            _rb = float(pd.to_numeric(_dr.get("Rate B", 0.0), errors="coerce") or 0.0)
            _dist_total_milk += _qa + _qb
            _dist_total_purchase += (_qa * _ra) + (_qb * _rb)

    _dist_total_milk     = round(_dist_total_milk, 2)
    _dist_total_purchase = round(_dist_total_purchase, 2)

    _dist_total_payment = 0.0
    if isinstance(_dist_pay_data_preview, pd.DataFrame) and not _dist_pay_data_preview.empty and "Amount ₹" in _dist_pay_data_preview.columns:
        _dist_total_payment = round(
             float(pd.to_numeric(_dist_pay_data_preview["Amount ₹"], errors="coerce").fillna(0.0).sum()), 2
        )

    _dc1, _dc2, _dc3 = st.columns(3)
    _dc1.metric("Total Incoming Milk (L)", f"{_dist_total_milk:.2f}")
    _dc2.metric("Total Purchase Amount (₹)", _fmt_money(_dist_total_purchase))
    _dc3.metric("Total Payments Made (₹)", _fmt_money(_dist_total_payment))

    # ================== WASTAGE ENTRY ==================
    st.divider()
    st.subheader("🗑️ Wastage Entry")

    waste_base = pd.DataFrame({
        "category_id": categories_active["category_id"].astype(int),
        "Category": categories_active["name"].astype(str),
        "Qty Wasted (L)": 0.0,
        "Estimated Loss (₹)": 0.0,
        "Reason": "",
    }).sort_values("Category").reset_index(drop=True)

    if wastage is not None and not wastage.empty:
        _wz = wastage.copy()
        _wz["date"] = _safe_dt(_wz.get("date")).dt.date
        _wz["category_id"] = pd.to_numeric(_wz.get("category_id", 0), errors="coerce").fillna(0).astype(int)
        _wz["qty"] = pd.to_numeric(_wz.get("qty", 0.0), errors="coerce").fillna(0.0).astype(float)
        _wz["estimated_loss"] = pd.to_numeric(_wz.get("estimated_loss", 0.0), errors="coerce").fillna(0.0).astype(float)
        _wz["reason"] = _wz.get("reason", "").fillna("").astype(str)
        _wz_today = _wz.loc[_wz["date"] == posting_date].copy()
        if not _wz_today.empty:
            for _cid, _grp in _wz_today.groupby("category_id"):
                if _cid in set(waste_base["category_id"].tolist()):
                    _idx = int(waste_base.index[waste_base["category_id"] == int(_cid)][0])
                    _r0 = _grp.iloc[0]
                    waste_base.loc[_idx, "Qty Wasted (L)"] = float(_r0["qty"])
                    waste_base.loc[_idx, "Estimated Loss (₹)"] = float(_r0["estimated_loss"])
                    waste_base.loc[_idx, "Reason"] = str(_r0["reason"])

    waste_edit = st.data_editor(
        waste_base[["Category", "Qty Wasted (L)", "Estimated Loss (₹)", "Reason"]],
        num_rows="fixed",
        use_container_width=True,
        key=f"waste_editor_{posting_date}",
    )

    # ================== SINGLE SAVE (validate → delete → insert) ==================
    st.divider()
    if do_save_all:

        if st.session_state.get("daily_save_lock", False):
            st.warning("⚠️ Save already in progress. Please wait.")
            st.stop()

        st.session_state["daily_save_lock"] = True

        try:
            # ---- STEP 1: Wipe-out guard ----
            _db_e = _day_entries_for_zone(posting_date, posting_zone)
            _db_p = _day_payments_for_zone(posting_date, posting_zone)
            _has_db = (_db_e is not None and not _db_e.empty) or (_db_p is not None and not _db_p.empty)

            _screen_qty = sum(
                safe_scalar_sum(pd.to_numeric(_draft[meta["col"]], errors="coerce").fillna(0.0))
                for meta in cat_cols if meta["col"] in _draft.columns
            )
            _screen_pay = sum(
                safe_scalar_sum(pd.to_numeric(_draft[f"{m} ₹"], errors="coerce").fillna(0.0))
                for m in PAYMENT_MODES if f"{m} ₹" in _draft.columns
            )

            if _has_db and _screen_qty == 0.0 and _screen_pay == 0.0:
                st.error(
                    "❌ Save blocked: DB has data for this date/zone but your grid shows all zeros.\n\n"
                    "This likely means the grid did not load correctly. Refresh and try again."
                )
                st.stop()

            # ---- STEP 2: Save retailers (delete + insert with rollback) ----
            _safe_replace_entries_payments(posting_date, posting_zone, _draft)

            # ---- STEP 3: Save distributors (flat grid) ----
            _dist_grid_data = st.session_state.get("dist_flat_grid")
            _dist_pay_data  = st.session_state.get("dist_flat_payments")

            _dist_ids_to_save = []
            if isinstance(_dist_grid_data, pd.DataFrame) and not _dist_grid_data.empty and "DID" in _dist_grid_data.columns:
                _dist_ids_to_save = sorted({int(x) for x in _dist_grid_data["DID"].dropna().tolist()})

            # Only run distributor save if there are distributor IDs — skip silently if none
            if _dist_ids_to_save:
                sb_delete_where("distributor_purchases", [
                    ("date", "eq", str(posting_date)),
                    ("distributor_id", "in", _dist_ids_to_save),
                ])
                sb_delete_where("distributor_payments", [
                    ("date", "eq", str(posting_date)),
                    ("distributor_id", "in", _dist_ids_to_save),
                ])

                # Build distributor purchases
                _new_dp = []
                for _, _r in _dist_grid_data.iterrows():
                    _did = int(_r["DID"])
                    _cid = int(_r["CID"])
                    _qa = float(pd.to_numeric(_r.get("Qty A",  0.0), errors="coerce") or 0.0)
                    _ra = float(pd.to_numeric(_r.get("Rate A", 0.0), errors="coerce") or 0.0)
                    _qb = float(pd.to_numeric(_r.get("Qty B",  0.0), errors="coerce") or 0.0)
                    _rb = float(pd.to_numeric(_r.get("Rate B", 0.0), errors="coerce") or 0.0)

                    if _qa > 0 and _ra > 0:
                        _new_dp.append({
                            "date":           str(posting_date),
                            "distributor_id": _did,
                            "category_id":    _cid,
                            "qty":            round(_qa, 4),
                            "rate":           round(_ra, 4),
                            "amount":         round(_qa * _ra, 2),
                        })
                    if _qb > 0 and _rb > 0:
                        _new_dp.append({
                            "date":           str(posting_date),
                            "distributor_id": _did,
                            "category_id":    _cid,
                            "qty":            round(_qb, 4),
                            "rate":           round(_rb, 4),
                            "amount":         round(_qb * _rb, 2),
                        })

                # Build distributor payments
                _new_dpay = []
                if isinstance(_dist_pay_data, pd.DataFrame) and not _dist_pay_data.empty and "DID" in _dist_pay_data.columns:
                    for _, _r in _dist_pay_data.iterrows():
                        _did = int(_r["DID"])
                        _amt = float(pd.to_numeric(_r.get("Amount ₹", 0.0), errors="coerce") or 0.0)
                        if _amt <= 0:
                            continue
                        _new_dpay.append({
                            "date":           str(posting_date),
                            "distributor_id": _did,
                            "amount":         round(_amt, 2),
                            "payment_mode":   str(_r.get("Mode", "Cash") or "Cash"),
                            "note":           str(_r.get("Note", "") or "").strip(),
                        })

                # Validation: payment cannot exceed opening_due + today_purchases
                _dp_sum  = {}
                for _r in _new_dp:
                    _did = int(_r["distributor_id"])
                    _dp_sum[_did] = _dp_sum.get(_did, 0.0) + float(_r["amount"])

                _pay_sum = {}
                for _r in _new_dpay:
                    _did = int(_r["distributor_id"])
                    _pay_sum[_did] = _pay_sum.get(_did, 0.0) + float(_r["amount"])

                for _did, _pay_amt in _pay_sum.items():
                    _opening_due = distributor_balance_before(_did, posting_date)
                    _allowed     = round(_opening_due + _dp_sum.get(_did, 0.0), 2)
                    if _pay_amt > _allowed + 0.01:
                        raise RuntimeError(
                            f"Distributor ID {_did}: payment ₹{_pay_amt} exceeds "
                            f"allowed ₹{_allowed} (opening ₹{_opening_due} + today ₹{_dp_sum.get(_did,0.0)})"
                        )

                # Insert purchases — use sb_insert_df so explicit IDs are
                # assigned (avoids IDENTITY sequence drift duplicates) and cache
                # is cleared after write.
                if _new_dp:
                    sb_insert_df(pd.DataFrame(_new_dp), DISTRIBUTOR_PURCHASES_FILE)

                # Insert payments — same reasoning as above.
                if _new_dpay:
                    sb_insert_df(pd.DataFrame(_new_dpay), DISTRIBUTOR_PAYMENTS_FILE)

                # Force complete cache refresh after distributor writes.
                st.cache_data.clear()
                invalidate_data_cache()

            # ---- STEP 4: Save wastage (delete + insert for this date) ----
            sb_delete_where("wastage", [("date", "eq", str(posting_date))])

            _new_w = []
            _waste_map = waste_base[["Category", "category_id"]].copy().reset_index(drop=True)
            for _i in range(len(waste_edit)):
                _cid  = int(_waste_map.loc[_i, "category_id"])
                _q    = float(pd.to_numeric(waste_edit.loc[_i, "Qty Wasted (L)"],     errors="coerce") or 0.0)
                _loss = float(pd.to_numeric(waste_edit.loc[_i, "Estimated Loss (₹)"], errors="coerce") or 0.0)
                _rsn  = str(waste_edit.loc[_i, "Reason"] or "").strip()
                if _q <= 0 and _loss <= 0 and not _rsn:
                    continue
                _new_w.append({
                    "date":           str(posting_date),
                    "category_id":    int(_cid),
                    "qty":            round(_q, 4),
                    "reason":         _rsn,
                    "estimated_loss": round(_loss, 2),
                })

            if _new_w:
                sb_insert_df(pd.DataFrame(_new_w), WASTAGE_FILE)
                invalidate_data_cache()

            # ---- STEP 5: Done ----
            st.success("✅ All saved: Retailers · Distributors · Wastage")
            invalidate_data_cache()

            # Clear draft so next load fetches fresh data from DB
            for _k in list(st.session_state.get("daily_drafts", {}).keys()):
                if _k == ctx:
                    del st.session_state["daily_drafts"][_k]
            if ctx in st.session_state.get("daily_meta", {}):
                del st.session_state["daily_meta"][ctx]
            st.session_state["daily_loaded_ctx"] = None
            st.session_state["dist_flat_grid"] = pd.DataFrame()
            st.session_state["dist_flat_payments"] = pd.DataFrame()
            st.rerun()

        except Exception as _save_err:
            st.error(f"❌ Save failed. Retailer entries are rollback-protected.\n\nError: {_save_err}")

        finally:
            st.session_state["daily_save_lock"] = False
elif menu == "📅 Date + Zone View":
    st.header("📅 View All Data for a Specific Date + Zone")

    view_date = st.date_input("Select Date", value=date.today(), key="view_date")
    view_zone = st.selectbox("Select Zone", ["All Zones"] + get_all_zones(), key="view_zone")

    e_day = _day_entries_for_zone(view_date, view_zone)
    if e_day.empty:
        st.info("No entries for this date/zone.")
    else:
        e_view = build_entries_view_cached(e_day, st.session_state["data_version"], want_milk_type_col=False)

        pivot = pd.pivot_table(
            e_view,
            index="Retailer",
            columns="Category",
            values="qty",
            aggfunc="sum",
            fill_value=0.0
        )

        display = pivot.copy()
        for c in display.columns:
            vals = pd.to_numeric(display[c], errors="coerce").fillna(0.0)
            display[c] = vals.apply(lambda v: "–" if float(v) == 0.0 else f"{float(v):.2f}")
        display["TOTAL (L)"] = pivot.sum(axis=1).apply(lambda x: f"{float(x):.2f}")

        totals = {c: float(pivot[c].sum()) for c in pivot.columns}
        totals["TOTAL (L)"] = float(pivot.values.sum())
        totals_row = {k: (f"{float(v):.2f}" if k != "TOTAL (L)" else f"{float(v):.2f}") for k, v in totals.items()}
        display = pd.concat([display, pd.DataFrame([totals_row], index=["GRAND TOTAL"])])

        st.subheader("🥛 Retailer × Category (Liters)")
        st.dataframe(df_for_display(display), width="stretch")

    p_day = _day_payments_for_zone(view_date, view_zone)
    st.subheader("💳 Payments (This Date + Zone)")
    if p_day.empty:
        st.info("No payments for this date/zone.")
    else:
        pv = p_day.merge(
            retailers[["retailer_id", "name", "zone"]],
            on="retailer_id",
            how="left"
        ).rename(columns={"name": "Retailer"})
        pv["zone"] = pv["zone"].apply(_norm_zone)

        st.dataframe(
            pv[["date", "zone", "Retailer", "amount", "payment_mode", "note"]],
            width="stretch"
        )

        mode_totals = (
            pv.groupby("payment_mode", as_index=False)["amount"]
              .sum()
              .sort_values("amount", ascending=False)
              .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

        st.subheader("💳 Payment Totals by Mode")
        st.dataframe(
            mode_totals.style.format({"Total (₹)": "₹{:.2f}"}),
            width="stretch"
        )

# ================== ZONE-WISE SUMMARY ==================
elif menu == "📍 Zone-wise Summary":
    st.header("📍 Zone-wise Summary (Category Columns + Payment Mode Totals)")

    s_date = st.date_input("Select Date", value=date.today(), key="zone_sum_date")

    pivot = zone_category_pivot_for_day(s_date)

    st.subheader("🥛 Milk Sent — Zone × Category (Liters)")
    if pivot.empty:
        st.info("No entries on this date.")
    else:
        display = pivot.copy()

        for c in display.columns:
            if c in ("Zone", "TOTAL (L)"):
                continue
            display[c] = display[c].apply(fmt_zero_dash)

        numeric_cols = [c for c in pivot.columns if c != "Zone"]
        grand = {"Zone": "GRAND TOTAL"}
        for c in numeric_cols:
            grand[c] = float(pivot[c].sum())
        display = pd.concat([display, pd.DataFrame([grand])], ignore_index=True)

        st.dataframe(df_for_display(display), width="stretch")

    st.subheader("💳 Payments Collected — Totals by Mode (Zone-aware)")
    p_day = _day_payments_for_zone(s_date, "All Zones")
    if p_day.empty:
        st.info("No payments recorded on this date.")
    else:
        pv = p_day.merge(retailers[["retailer_id", "zone"]], on="retailer_id", how="left")
        pv["zone"] = pv["zone"].apply(_norm_zone)

        mode_totals = (
            pv.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

        mode_zone = (
            pv.groupby(["zone", "payment_mode"], as_index=False)["amount"]
            .sum()
            .rename(columns={"zone": "Zone", "payment_mode": "Mode", "amount": "Total (₹)"})
            .sort_values(["Zone", "Total (₹)"], ascending=[True, False])
        )

        st.caption("Overall totals (all zones combined):")
        st.dataframe(mode_totals.style.format({"Total (₹)": "₹{:.2f}"}), width="stretch")

        st.caption("Zone-wise totals by mode:")
        st.dataframe(mode_zone.style.format({"Total (₹)": "₹{:.2f}"}), width="stretch")

# ================== EDIT SINGLE ENTRY ==================
elif menu == "✏️ Edit (Single Entry)":
    st.header("✏️ Edit / Delete Single Entry (Rate is preserved)")

    if entries.empty:
        st.info("No entries yet.")
        st.stop()

    f_date = st.date_input("Filter Date", value=date.today(), key="single_edit_date")
    f_zone = st.selectbox("Filter Zone", ["All Zones"] + get_all_zones(), key="single_edit_zone")

    df = entries.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == f_date].copy()
    df = filter_by_zone(df, "retailer_id", f_zone)

    if df.empty:
        st.info("No entries for this date/zone.")
        st.stop()

    view = build_entries_view_cached(df, st.session_state["data_version"], want_milk_type_col=False)
    st.dataframe(
        view[["entry_id", "date", "zone", "Retailer", "Category", "qty", "rate", "amount"]],
        width="stretch"
    )

    entry_id = st.number_input("Entry ID", min_value=1, step=1, key="single_entry_id")
    if int(entry_id) not in set(entries["entry_id"].astype(int).tolist()):
        st.warning("Entry ID not found.")
        st.stop()

    row = entries.loc[entries["entry_id"] == int(entry_id)].iloc[0]
    new_qty = st.number_input("New Quantity (L)", min_value=0.0, step=0.5, format="%g", value=float(row["qty"]), key="single_new_qty")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Qty", key="single_update_btn"):
            rate = float(row["rate"])
            new_amt = float(new_qty) * rate
            entries.loc[entries["entry_id"] == int(entry_id), ["qty", "amount"]] = [float(new_qty), float(new_amt)]
            # DB write only the changed row
            updated_row = entries.loc[entries["entry_id"] == int(entry_id)].copy()
            safe_write_csv(updated_row, ENTRIES_FILE, allow_empty=False)
            
            st.success("Updated quantity (stored rate preserved).")
            st.rerun()

    with col2:
        confirm = st.text_input("Type DELETE to delete this entry", key="single_delete_confirm")
        if st.button("Delete Entry", key="single_delete_btn"):
            if confirm != "DELETE":
                st.warning("Type DELETE to confirm.")
            else:
                sb_delete_by_pk("entries", "entry_id", [int(entry_id)])
                entries = entries.loc[entries["entry_id"].astype(int) != int(entry_id)].copy()
                st.success("Deleted.")
                st.rerun()



# ================== MILK CATEGORIES ==================
elif menu == "🥛 Milk Categories":
    st.header("🥛 Milk Categories Management")
    tab1, tab2 = st.tabs(["➕ Add Category", "✏️ Edit Categories"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Category Name", key="cat_add_name")
        with col2:
            description = st.text_input("Description (optional)", key="cat_add_desc")
        with col3:
            default_price = st.number_input("Default Price per Liter (₹)", min_value=0.0, step=0.5, format="%g", key="cat_add_price")

        if st.button("Add Category", type="primary", key="cat_add_btn"):
            if not name.strip():
                st.error("Category name is required.")
                st.stop()
                
            if default_price <= 0:
                st.error("Default price must be greater than 0.")
                st.stop()
                
            # OPTION B: DB auto-generates category_id
            table, pk = FILE_TO_TABLE[CATEGORIES_FILE]
            
            new_row = pd.DataFrame([{
                "name": name.strip(),
                "description": description.strip() if description else "",
                "default_price": float(default_price),
                "is_active": True,
            }])
            
            sb_insert_df(new_row, CATEGORIES_FILE)

            st.success("Category added.")
            st.rerun()




    with tab2:
        if categories.empty:
            st.info("No categories yet.")
        else:
            st.dataframe(categories, width="stretch")

            edit_cat = st.selectbox("Select category to edit", categories["name"].tolist(), key="cat_edit_sel")
            cat_data = categories.loc[categories["name"] == edit_cat].iloc[0]
            cid = int(cat_data["category_id"])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_name = st.text_input("New name", value=str(cat_data["name"]), key="cat_new_name")
            with col2:
                new_desc = st.text_input("New description", value=str(cat_data.get("description", "")), key="cat_new_desc")
            with col3:
                new_default_price = st.number_input(
                    "Default Price (₹/L)",
                    value=float(cat_data.get("default_price", 0.0)),
                    min_value=0.0,
                    step=0.5,
                    format="%g",
                    key="cat_new_price",
                )
            with col4:
                new_active = st.checkbox("Active", value=bool(cat_data.get("is_active", True)), key="cat_new_active")

            colA, colB, colC = st.columns(3)
            
            
            with colA:
                if st.button("Update Category", key="cat_update_btn"):
                    mask = categories["category_id"].astype(int) == int(cid)
                    
                    categories.loc[mask, ["name", "description", "default_price", "is_active"]] = [
                        new_name.strip(),
                        new_desc,
                        float(new_default_price),
                        bool(new_active),
                    ]
                    updated_row = categories.loc[mask].copy()
                    safe_write_csv(updated_row, CATEGORIES_FILE, allow_empty=False)
                    
                    st.success("Updated!")
                    st.rerun()


            with colB:
                if st.button("Deactivate Category (Safe)", key="cat_deactivate_btn"):
                    mask = categories["category_id"].astype(int) == int(cid)
                    categories.loc[mask, "is_active"] = False
                    
                    updated_row = categories.loc[mask].copy()
                    safe_write_csv(updated_row, CATEGORIES_FILE, allow_empty=False)
                    
                    st.success("Category deactivated (history preserved).")
                    st.rerun()


            with colC:
                st.caption("Hard delete is blocked if referenced.")
                confirm = st.text_input("Type DELETE to hard delete category", key="cat_delete_confirm")
                if st.button("🗑️ Hard Delete Category", type="secondary", key="cat_delete_btn"):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_category_referenced(cid):
                        st.error("Blocked: Category is referenced in history. Deactivate instead.")
                    else:
                        sb_delete_by_pk("categories", "category_id", [cid])
                        st.success("Hard deleted.")
                        st.rerun()

# ================== RETAILERS ==================
elif menu == "🏪 Retailers":
    st.header("🏪 Retailer Management (with Zones)")
    tab1, tab2, tab3 = st.tabs(["➕ Add Retailer", "✏️ Edit Retailers", "🏠 Main Book Retailers"])

    all_zones = get_all_zones()

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Retailer Name", key="ret_add_name")
            contact = st.text_input("Contact Number", key="ret_add_contact")
        with col2:
            address = st.text_area("Address", key="ret_add_address")
        with col3:
            zone_mode = st.radio("Zone", ["Select Existing", "Create New"], horizontal=True, key="ret_add_zone_mode")
            if zone_mode == "Select Existing":
                zone = st.selectbox("Select Zone", ["Default"] + all_zones, key="ret_add_zone_sel")
            else:
                zone = st.text_input("New Zone Name", value="", key="ret_add_zone_new")

        if st.button("Add Retailer", type="primary", key="ret_add_btn"):
            if not name.strip():
                st.warning("Retailer name required")
            else:
                z = _norm_zone(zone)

                new_row = pd.DataFrame([{
                    "name": name.strip(),
                    "contact": contact,
                    "address": address,
                    "zone": z,
                    "is_active": True
                }])

            sb_insert_df(new_row, RETAILERS_FILE)

            st.success(f"✅ Retailer '{name}' added to zone '{z}'!")
            st.rerun()


    with tab2:
        if retailers.empty:
            st.info("No retailers yet.")
        else:
            st.dataframe(retailers, width="stretch")

            edit_ret = st.selectbox("Select retailer to edit", retailers["name"].tolist(), key="ret_edit_sel")
            ret_data = retailers.loc[retailers["name"] == edit_ret].iloc[0]
            rid = int(ret_data["retailer_id"])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_name = st.text_input("New name", value=str(ret_data["name"]), key="ret_new_name")
                new_contact = st.text_input("New contact", value=str(ret_data.get("contact", "")), key="ret_new_contact")
            with col2:
                new_address = st.text_area("New address", value=str(ret_data.get("address", "")), key="ret_new_address")
            with col3:
                zone_mode2 = st.radio("Zone Update", ["Select Existing", "Create New"], horizontal=True, key="ret_zone_update_mode")
                if zone_mode2 == "Select Existing":
                    choices = ["Default"] + all_zones
                    current = _norm_zone(ret_data.get("zone", "Default"))
                    idx = choices.index(current) if current in choices else 0
                    new_zone = st.selectbox("Select Zone", choices, index=idx, key="ret_new_zone_sel")
                else:
                    new_zone = st.text_input("New Zone Name", value="", key="ret_new_zone_new")
            with col4:
                new_active = st.checkbox("Active", value=bool(ret_data.get("is_active", True)), key="ret_new_active")

            colA, colB, colC = st.columns(3)
            
            
            with colA:
                if st.button("Update Retailer", key="ret_update_btn"):
                    z = _norm_zone(new_zone)
                    mask = retailers["retailer_id"].astype(int) == int(rid)
                    
                    retailers.loc[mask, ["name", "contact", "address", "zone", "is_active"]] = [
                        new_name.strip(),
                        new_contact,
                        new_address,
                        z,
                        bool(new_active),
                    ]
                    
                    updated_row = retailers.loc[mask].copy()
                    safe_write_csv(updated_row, RETAILERS_FILE, allow_empty=False)
                    
                    st.success("Updated!")
                    st.rerun()


            with colB:
                if st.button("Deactivate Retailer (Safe)", key="ret_deactivate_btn"):
                    mask = retailers["retailer_id"].astype(int) == int(rid)
                    retailers.loc[mask, "is_active"] = False
                    
                    updated_row = retailers.loc[mask].copy()
                    safe_write_csv(updated_row, RETAILERS_FILE, allow_empty=False)
                    
                    st.success("Retailer deactivated (history preserved).")
                    st.rerun()


            with colC:
                st.caption("Hard delete is blocked if referenced.")
                confirm = st.text_input("Type DELETE to hard delete retailer", key="ret_delete_confirm")
                if st.button("🗑️ Hard Delete Retailer", type="secondary", key="ret_delete_btn"):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_retailer_referenced(rid):
                        st.error("Blocked: Retailer is referenced in history. Deactivate instead.")
                    else:
                        sb_delete_by_pk("retailers", "retailer_id", [rid])
                        st.success("Hard deleted.")
                        st.rerun()

    with tab3:
        st.subheader("🏠 Main Book Retailers")
        st.caption("These are normal retailers maintained in the Main book for dashboard overview. This does not change their zone.")
        if not _main_table_exists():
            st.error("Create the 'main_retailers' table first (SQL below).")
            st.code("""create table if not exists public.main_retailers (
  retailer_id bigint primary key references public.retailers(retailer_id) on delete cascade
);""")
        elif retailers.empty:
            st.info("No retailers available.")
        else:
            # Current selection
            current_ids = set(get_main_retailer_ids())
            rtmp = retailers.copy()
            rtmp["retailer_id"] = pd.to_numeric(rtmp.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
            rtmp["name"] = rtmp.get("name", "").fillna("").astype(str)

            id_to_name = dict(zip(rtmp["retailer_id"].tolist(), rtmp["name"].tolist()))
            name_to_id = {v: k for k, v in id_to_name.items() if v}

            current_names = [id_to_name.get(rid, str(rid)) for rid in sorted(current_ids) if rid in id_to_name]

            options = sorted(rtmp["name"].dropna().astype(str).tolist())
            selected_names = st.multiselect("Retailers in Main book", options=options, default=current_names, key="main_retailers_select")

            if st.button("Save Main Book Retailers", type="primary", key="main_retailers_save"):
                new_ids = {int(name_to_id[n]) for n in selected_names if n in name_to_id}
                to_add = sorted(new_ids - current_ids)
                to_remove = sorted(current_ids - new_ids)

                try:
                    if to_add:
                        add_main_retailers(to_add)
                    if to_remove:
                        remove_main_retailers(to_remove)
                    st.success("Saved Main book retailers.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save Main book retailers: {e}")

elif menu == "💰 Price Management":

    st.header("💰 Price Management")

    if retailers_active.empty:
        st.warning("Please add retailers first")
        st.stop()

    if categories_active.empty:
        st.warning("Please add categories first")
        st.stop()

    eff_date = st.date_input(
        "Effective Date",
        date.today(),
        key="price_matrix_date"
    )

    retailer_list = (
        retailers_active
        .assign(zone_order=retailers_active["zone"].str.extract(r'(\d+)').astype(float))
        .sort_values(["zone_order", "name"])
    )
    category_list = categories_active.sort_values("name")

    matrix_rows = []

    for _, r in retailer_list.iterrows():

        rid = int(r["retailer_id"])

        row = {
            "Retailer": r["name"],
            "retailer_id": rid
        }

        for _, c in category_list.iterrows():

            cid = int(c["category_id"])

            p = get_price_for_date(
                rid,
                cid,
                eff_date
            )

            if p is None:
                p = float(c.get("default_price", 0.0) or 0.0)

            row[c["name"]] = float(p)

        matrix_rows.append(row)

    price_matrix_df = pd.DataFrame(matrix_rows)

    display_df = price_matrix_df.drop(columns=["retailer_id"])

    st.subheader("Price Matrix")

    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="fixed",
        key="price_matrix_editor"
    )

    if st.button("💾 Save Price Changes", type="primary"):

        updates = []

        for i, row in edited_df.iterrows():

            rid = int(price_matrix_df.iloc[i]["retailer_id"])

            for _, c in category_list.iterrows():

                cid = int(c["category_id"])
                col = c["name"]

                new_price = float(row[col] or 0.0)

                old_price = get_price_for_date(
                    rid,
                    cid,
                    eff_date
                )

                if old_price is None:
                    old_price = 0.0

                if float(new_price) != float(old_price):

                    updates.append({
                        "retailer_id": rid,
                        "category_id": cid,
                        "price": float(new_price),
                        "effective_date": str(eff_date)
                    })

        if updates:

            df_updates = pd.DataFrame(updates)

            sb.table("prices").upsert(
                df_updates.to_dict(orient="records"),
                on_conflict="retailer_id,category_id"
            ).execute()

            st.success(f"{len(updates)} prices updated")

            st.rerun()

        else:
            st.info("No changes detected")
# ================== LEDGER ==================
elif menu == "📒 Ledger":
    st.header(f"📒 Ledger (Grid View) — {selected_zone}")

    if entries_z.empty:
        st.info("No entries in this zone context.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        d_from = st.date_input("From Date", value=date.today() - timedelta(days=30), key="ledger_from")
    with col2:
        d_to = st.date_input("To Date", value=date.today(), key="ledger_to")

    if d_from > d_to:
        st.error("From Date cannot be after To Date.")
        st.stop()

    v = build_entries_view_cached(entries_z, st.session_state["data_version"], want_milk_type_col=False)
    v["date"] = pd.to_datetime(v["date"], errors="coerce").dt.date
    v = v.loc[(v["date"] >= d_from) & (v["date"] <= d_to)].copy()

    if v.empty:
        st.info("No entries in this date range.")
        st.stop()

    pivot = pd.pivot_table(
        v,
        index="Retailer",
        columns="Category",
        values="qty",
        aggfunc="sum",
        fill_value=0.0
    )

    display = pivot.copy()
    for c in display.columns:
        display[c] = display[c].apply(fmt_zero_dash)

    display["TOTAL (L)"] = pivot.sum(axis=1).apply(lambda x: f"{float(x):.2f}")

    grand = {"TOTAL (L)": float(pivot.values.sum())}
    for c in pivot.columns:
        grand[c] = float(pivot[c].sum())
    grand_disp = {k: (f"{float(v):.2f}" if k != "TOTAL (L)" else f"{float(v):.2f}") for k, v in grand.items()}
    display = pd.concat([display, pd.DataFrame([grand_disp], index=["GRAND TOTAL"])])

    st.subheader("🥛 Retailer × Category Grid (Liters)")
    st.dataframe(df_for_display(display), width="stretch")

    st.subheader("📌 Category Totals (Liters)")
    cat_totals = pivot.sum(axis=0).reset_index()
    cat_totals.columns = ["Category", "Total (L)"]
    cat_totals = cat_totals.sort_values("Total (L)", ascending=False)
    st.dataframe(cat_totals, width="stretch")

# ================== FILTERS & REPORTS ==================
elif menu == "🔍 Filters & Reports":
    st.header(f"🔍 Filters & Detailed Reports — {selected_zone}")

    if selected_zone == "All Zones":
        zone_filter = st.multiselect("Zone Filter", ["All"] + zones, default=["All"], key="rep_zone_filter")
    else:
        zone_filter = [selected_zone]

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_retailer = st.multiselect("Select Retailer(s)", ["All"] + retailers["name"].tolist(), default=["All"], key="rep_retailer_filter")
    with col2:
        filter_category = st.multiselect("Select Category(s)", ["All"] + categories["name"].tolist(), default=["All"], key="rep_cat_filter")
    with col3:
        date_range = st.date_input("Date Range", value=[], key="rep_date_range")

    filtered_entries = entries.copy()
    filtered_entries = filter_by_zone(filtered_entries, "retailer_id", selected_zone)

    if selected_zone == "All Zones" and "All" not in zone_filter and not retailers.empty:
        rz = retailers.copy()
        rz["zone"] = rz["zone"].apply(_norm_zone)
        allowed_rids = rz.loc[rz["zone"].isin([_norm_zone(z) for z in zone_filter]), "retailer_id"].astype(int).tolist()
        filtered_entries = filtered_entries.loc[filtered_entries["retailer_id"].astype(int).isin(allowed_rids)].copy()

    if not filtered_entries.empty:
        if "All" not in filter_retailer and not retailers.empty:
            rid_list = retailers.loc[retailers["name"].isin(filter_retailer), "retailer_id"].astype(int).tolist()
            filtered_entries = filtered_entries.loc[filtered_entries["retailer_id"].astype(int).isin(rid_list)].copy()

        if "All" not in filter_category and not categories.empty:
            cid_list = categories.loc[categories["name"].isin(filter_category), "category_id"].astype(int).tolist()
            filtered_entries = filtered_entries.loc[filtered_entries["category_id"].astype(int).isin(cid_list)].copy()

        if len(date_range) == 2:
            filtered_entries["date"] = pd.to_datetime(filtered_entries["date"], errors="coerce")
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            filtered_entries = filtered_entries.loc[(filtered_entries["date"] >= start) & (filtered_entries["date"] <= end)].copy()

    if filtered_entries.empty:
        st.info("No data matching the filters")
    else:
        result_view = build_entries_view_cached(filtered_entries, st.session_state["data_version"], want_milk_type_col=False)
        st.dataframe(
            result_view[["date", "zone", "Retailer", "Category", "qty", "rate", "amount"]],
            width="stretch",
        )

# ================== DISTRIBUTORS ==================
elif menu == "🚚 Distributors":
    st.header("🚚 Distributor Management")
    tab1, tab2 = st.tabs(["➕ Add Distributor", "✏️ Edit Distributors"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Distributor Name", key="dist_add_name")
            contact = st.text_input("Contact Number", key="dist_add_contact")
        with col2:
            address = st.text_area("Address", key="dist_add_address")

        if st.button("Add Distributor", type="primary", key="dist_add_btn"):
            if not name.strip():
                st.warning("Distributor name required.")
            else:
                did = sb_new_id("distributors", "distributor_id")
                new_row = pd.DataFrame(
                    [[did, name.strip(), contact.strip(), address.strip(), True]],
                    columns=CSV_SCHEMAS[DISTRIBUTORS_FILE]
                )
                distributors = pd.concat([distributors, new_row], ignore_index=True)
                sb_insert_df(new_row, DISTRIBUTORS_FILE)
                st.success("✅ Distributor added!")
                st.rerun()

    with tab2:
        if distributors.empty:
            st.info("No distributors yet.")
        else:
            st.dataframe(df_for_display(distributors), width="stretch")

            edit_dis = st.selectbox("Select distributor", distributors["name"].tolist(), key="dist_edit_sel")
            dis_data = distributors.loc[distributors["name"] == edit_dis].iloc[0]
            did = int(dis_data["distributor_id"])

            col1, col2, col3 = st.columns(3)
            with col1:
                new_name = st.text_input("Name", value=str(dis_data["name"]), key="dist_new_name")
            with col2:
                new_contact = st.text_input("Contact", value=str(dis_data.get("contact", "")), key="dist_new_contact")
            with col3:
                new_active = st.checkbox("Active", value=bool(dis_data.get("is_active", True)), key="dist_new_active")

            new_address = st.text_area("Address", value=str(dis_data.get("address", "")), key="dist_new_address")

            colA, colB, colC = st.columns(3)
            
            with colA:
                if st.button("Update Distributor", key="dist_update_btn"):
                    mask = distributors["distributor_id"].astype(int) == int(did)
                    distributors.loc[mask, ["name", "contact", "address", "is_active"]] = [
                        new_name.strip(),
                        new_contact.strip(),
                        new_address.strip(),
                        bool(new_active),
                    ]
                    
                    updated_row = distributors.loc[mask].copy()
                    safe_write_csv(updated_row, DISTRIBUTORS_FILE, allow_empty=False)
                    
                    st.success("Updated!")
                    st.rerun()

            with colB:
                if st.button("Deactivate (Safe)", key="dist_deactivate_btn"):
                    mask = distributors["distributor_id"].astype(int) == int(did)
                    distributors.loc[mask, "is_active"] = False

                    updated_row = distributors.loc[mask].copy()
                    safe_write_csv(updated_row, DISTRIBUTORS_FILE, allow_empty=False)

                    st.success("Distributor deactivated.")
                    st.rerun()



            with colC:
                confirm = st.text_input("Type DELETE to hard delete", key="dist_delete_confirm")
                if st.button("🗑️ Hard Delete", type="secondary", key="dist_delete_btn"):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_distributor_referenced(did):
                        st.error("Blocked: Distributor referenced in purchases/payments. Deactivate instead.")
                    else:
                        sb_delete_by_pk("distributors", "distributor_id", [did])
                        st.success("Hard deleted.")
                        st.rerun()


elif menu == "🧩 Distributor Category Mapping":
    st.header("🧩 Distributor → Category Mapping")
    st.caption("This controls exactly which categories appear for each distributor in the Daily Posting Sheet.")

    if distributors.empty or categories.empty:
        st.warning("Add distributors and categories first.")
        st.stop()

    distributors_active = distributors.copy()
    if "is_active" in distributors_active.columns:
        distributors_active["is_active"] = distributors_active["is_active"].apply(parse_boolish_active)
        distributors_active = distributors_active.loc[distributors_active["is_active"] == True].copy()

    categories_active = categories.copy()
    if "is_active" in categories_active.columns:
        categories_active["is_active"] = categories_active["is_active"].apply(parse_boolish_active)
        categories_active = categories_active.loc[categories_active["is_active"] == True].copy()

    if distributors_active.empty:
        st.info("No active distributors.")
        st.stop()
    if categories_active.empty:
        st.info("No active categories.")
        st.stop()

    # Helper: current mapped category ids
    def _mapped_ids(did: int) -> list[int]:
        if dist_cat_map is None or dist_cat_map.empty:
            return []
        m = dist_cat_map.copy()
        m["distributor_id"] = pd.to_numeric(m["distributor_id"], errors="coerce").fillna(0).astype(int)
        m["category_id"] = pd.to_numeric(m["category_id"], errors="coerce").fillna(0).astype(int)
        m["is_active"] = m.get("is_active", True).apply(parse_boolish_active)
        m = m.loc[(m["distributor_id"] == int(did)) & (m["is_active"] == True)].copy()
        return sorted(m["category_id"].astype(int).tolist())

    # UI
    did_list = distributors_active.sort_values("name")[["distributor_id", "name"]].to_dict(orient="records")
    cat_options = categories_active.sort_values("name")[["category_id", "name"]].to_dict(orient="records")
    cat_id_to_name = {int(c["category_id"]): str(c["name"]) for c in cat_options}
    cat_name_to_id = {str(c["name"]): int(c["category_id"]) for c in cat_options}
    all_cat_names = [str(c["name"]) for c in cat_options]

    st.divider()
    st.subheader("Set categories per distributor")

    for d in did_list:
        did = int(d["distributor_id"])
        dname = str(d["name"])

        current_ids = _mapped_ids(did)
        current_names = [cat_id_to_name[cid] for cid in current_ids if cid in cat_id_to_name]

        with st.expander(f"🚚 {dname}", expanded=False):
            selected_names = st.multiselect(
                "Supplies these categories",
                options=all_cat_names,
                default=current_names,
                key=f"dcm_ms_{did}",
            )

            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("💾 Save Mapping", key=f"dcm_save_{did}"):
                    # Overwrite mapping for this distributor (simple + correct)
                    sb_delete_where("distributor_category_map", [("distributor_id", "eq", int(did))])

                    new_rows = []
                    next_id = None if USE_DB_IDS else sb_next_id("distributor_category_map", "map_id")

                    for nm in selected_names:
                        cid = int(cat_name_to_id[nm])
                        mid = None if USE_DB_IDS else int(next_id)
                        if not USE_DB_IDS:
                            next_id += 1
                        new_rows.append([mid, int(did), int(cid), True])

                    if new_rows:
                        df_new = pd.DataFrame(new_rows, columns=CSV_SCHEMAS[DISTRIBUTOR_CATEGORY_MAP_FILE])
                        sb_insert_df(df_new, DISTRIBUTOR_CATEGORY_MAP_FILE)

                    st.success("Saved ✅")
                    st.rerun()

            with col2:
                st.caption("Tip: Keep this strict. If you don’t map it here, it won’t show in Daily Entry for this distributor.")

# ================== DISTRIBUTOR LEDGER ==================
elif menu == "📒 Distributor Ledger":
    st.header("📒 Distributor Ledger (Incoming Milk + Payments + Running Due)")

    if distributors.empty:
        st.warning("Add at least 1 distributor first.")
        st.stop()
    if categories.empty:
        st.warning("Add at least 1 category first.")
        st.stop()

    dis_name = st.selectbox("Select Distributor", distributors["name"].tolist(), key="dl_dis")
    did = int(distributors.loc[distributors["name"] == dis_name, "distributor_id"].iloc[0])

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input("From Date", value=date.today().replace(day=1), key="dl_start")
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="dl_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_names = categories["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    opening_due = distributor_balance_before(did, start_day)
    grid = build_distributor_daily_grid(did, start_day, end_day, cat_names)

    closing_due = float(pd.to_numeric(grid["Running Due (₹)"], errors="coerce").fillna(opening_due).iloc[-1]) if not grid.empty else opening_due
    total_milk = float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_pur = float(pd.to_numeric(grid["Purchases (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_pay = float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Purchases (This Period)", _fmt_money(total_pur))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()
    st.subheader("📌 Daily Sheet (Qty + Rate by Category)")

    preview = grid.copy()
    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"
        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)
        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)
            
    for c in ["Purchases (₹)", "Payment (₹)", "Running Due (₹)"]:
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)
            
    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)


    st.dataframe(df_for_display(preview), width="stretch")

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if "cat_cols" in locals() and isinstance(cat_cols, list) and len(cat_cols) > 0:
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (not _cn) and ("categories" in locals()) and hasattr(categories, "empty") and (not categories.empty) and ("name" in categories.columns):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [f"{cat} Qty" for cat in cat_names if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum())
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum())
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric("Payments Collected (₹)", f"₹{grand_pay:.2f}")    # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(lambda x: f"{float(x):.2f}")
        st.dataframe(df_for_display(tot_df), width="stretch")


    st.subheader("💳 Payment Mode Totals (Period)")
    pm = distributor_pay_mode_totals(did, start_day, end_day)
    if pm.empty:
        st.info("No payments in this period.")
    else:
        st.dataframe(pm.style.format({"Total (₹)": "₹{:.2f}"}), width="stretch")


# ================== DISTRIBUTOR BILL ==================
elif menu == "🧾 Distributor Bill":
    st.header("🧾 Distributor Statement / Bill (Printable)")

    if distributors.empty:
        st.warning("Add at least 1 distributor first.")
        st.stop()
    if categories.empty:
        st.warning("Add at least 1 category first.")
        st.stop()

    dis_name = st.selectbox("Select Distributor", distributors["name"].tolist(), key="db_dis")
    did = int(distributors.loc[distributors["name"] == dis_name, "distributor_id"].iloc[0])

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input("From Date", value=date.today().replace(day=1), key="db_start")
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="db_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_names = categories["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    drow = distributors.loc[distributors["distributor_id"].astype(int) == did].iloc[0].to_dict()

    grid = build_distributor_daily_grid(did, start_day, end_day, cat_names)
    pm = distributor_pay_mode_totals(did, start_day, end_day)

    opening_due = distributor_balance_before(did, start_day)
    closing_due = float(pd.to_numeric(grid["Running Due (₹)"], errors="coerce").fillna(opening_due).iloc[-1]) if not grid.empty else opening_due

    total_pur = float(pd.to_numeric(grid["Purchases (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_pay = float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_milk = float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Purchases (This Period)", _fmt_money(total_pur))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()
    st.subheader("📌 Bill Preview (Arrow-safe)")
    preview = grid.copy()

    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"
        
        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)
        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)
            
    for c in ["Purchases (₹)", "Payment (₹)", "Running Due (₹)"]:
        
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)
            
    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)


    st.dataframe(df_for_display(preview), width="stretch")

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if "cat_cols" in locals() and isinstance(cat_cols, list) and len(cat_cols) > 0:
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (not _cn) and ("categories" in locals()) and hasattr(categories, "empty") and (not categories.empty) and ("name" in categories.columns):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [f"{cat} Qty" for cat in cat_names if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum())
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum())
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric("Payments Collected (₹)", f"₹{grand_pay:.2f}")    # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(lambda x: f"{float(x):.2f}")
        st.dataframe(df_for_display(tot_df), width="stretch")


    html = build_distributor_bill_html(drow, start_day, end_day, grid, pm, cat_names)

    st.subheader("🖨️ Printable Statement")
    st.components.v1.html(html, height=750, scrolling=True)

    st.download_button(
        "⬇️ Download Distributor Statement (HTML - Print Ready)",
        data=html.encode("utf-8"),
        file_name=f"distributor_statement_{dis_name}_{start_day}_to_{end_day}.html",
        mime="text/html",
        key="db_dl_html",
    )




# ================== EXPENSES ==================
elif menu == "💼 Expenses":
    st.header("💼 Business Expenses Management")

    tab1, tab2 = st.tabs(["➕ Add Expense", "📋 View / Edit Expenses"])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ex_date = st.date_input("Date", value=date.today(), key="ex_date")
        with c2:
            ex_cat = st.text_input("Expense Category", value="", key="ex_cat")
        with c3:
            ex_amt = st.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%g", key="ex_amt")
        with c4:
            ex_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank", "Cheque", "Other"], key="ex_mode")

        ex_desc = st.text_input("Description", key="ex_desc")
        ex_paid = st.checkbox("Paid", value=True, key="ex_paid")

        if st.button("Save Expense", type="primary", key="ex_save"):
            if ex_amt <= 0:
                st.error("Amount must be > 0.")
                st.stop()
            eid = sb_new_id("expenses", "expense_id")
            new_row = pd.DataFrame(
                [[eid, str(ex_date), str(ex_cat).strip(), str(ex_desc).strip(), float(ex_amt), str(ex_mode), bool(ex_paid)]],
                columns=CSV_SCHEMAS[EXPENSES_FILE],
            )
            sb_insert_df(new_row, EXPENSES_FILE)
            st.success("✅ Expense saved.")
            st.rerun()

    with tab2:
        if expenses.empty:
            st.info("No expenses yet.")
        else:
            view = expenses.copy()
            view["date"] = _safe_dt(view["date"]).dt.strftime("%Y-%m-%d")
            view = view[["expense_id", "date", "category", "description", "amount", "payment_mode", "paid"]].sort_values(
                ["date", "expense_id"], ascending=[False, False]
            )
            st.dataframe(view.style.format({"amount": "₹{:.2f}"}), width="stretch")

            st.divider()
            st.subheader("✏️ Edit / Delete Expense")

            eid = st.number_input("Expense ID", min_value=1, step=1, key="ex_edit_id")
            if int(eid) not in set(expenses["expense_id"].astype(int).tolist()):
                st.caption("Enter an existing Expense ID to edit.")
            else:
                row = expenses.loc[expenses["expense_id"].astype(int) == int(eid)].iloc[0]
                cur_date = pd.to_datetime(row["date"], errors="coerce").date() if str(row["date"]) else date.today()
                cur_cat = str(row.get("category", "") or "")
                cur_desc = str(row.get("description", "") or "")
                cur_amt = float(row.get("amount", 0.0) or 0.0)
                cur_mode = str(row.get("payment_mode", "Cash") or "Cash")
                cur_paid = bool(row.get("paid", False))

                e1, e2, e3, e4 = st.columns(4)
                with e1:
                    new_date = st.date_input("Date", value=cur_date, key="ex_new_date")
                with e2:
                    new_cat = st.text_input("Category", value=cur_cat, key="ex_new_cat")
                with e3:
                    new_amt = st.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%g", value=cur_amt, key="ex_new_amt")
                with e4:
                    modes = ["Cash", "UPI", "Bank", "Cheque", "Other"]
                    idx = modes.index(cur_mode) if cur_mode in modes else 0
                    new_mode = st.selectbox("Mode", modes, index=idx, key="ex_new_mode")

                new_desc = st.text_input("Description", value=cur_desc, key="ex_new_desc")
                new_paid = st.checkbox("Paid", value=cur_paid, key="ex_new_paid")

                colA, colB = st.columns(2)
                with colA:
                    if st.button("Update Expense", key="ex_update"):
                        if new_amt <= 0:
                            st.error("Amount must be > 0.")
                            st.stop()
                            
                        mask = expenses["expense_id"].astype(int) == int(eid)
                        
                        expenses.loc[mask, ["date", "category", "description", "amount", "payment_mode", "paid"]] = [
                            str(new_date),
                            str(new_cat).strip(),
                            str(new_desc).strip(),
                            float(new_amt),
                            str(new_mode),
                            bool(new_paid),
                        ]
                        
                        updated = expenses.loc[mask].copy()
                        safe_write_csv(updated, EXPENSES_FILE, allow_empty=False)
                        st.success("Updated.")
                        st.rerun()


                with colB:
                    confirm = st.text_input("Type DELETE to delete expense", key="ex_del_confirm")
                    if st.button("Delete Expense", key="ex_delete"):
                        if confirm != "DELETE":
                            st.warning("Type DELETE to confirm.")
                        else:
                            sb_delete_by_pk("expenses", "expense_id", [int(eid)])
                            st.success("Deleted.")
                            st.rerun()

# ================== GENERATE BILL ==================
elif menu == "🧾 Retailers Bill":
    st.header("🧾 Generate Professional Customer Bill (Printable + Downloadable)")

    if retailers.empty:
        st.warning("Add at least 1 retailer first.")
        st.stop()

    bill_zone = st.selectbox("Select Zone", ["All Zones"] + get_all_zones(), key="bill_zone")

    rlist = retailers.copy()
    rlist["zone"] = rlist["zone"].apply(_norm_zone)
    if bill_zone != "All Zones":
        rlist = rlist.loc[rlist["zone"] == _norm_zone(bill_zone)].copy()

    if rlist.empty:
        st.warning("No retailers found in this zone.")
        st.stop()

    retailer_name = st.selectbox("Select Customer (Retailer)", rlist["name"].tolist(), key="bill_retailer")
    rid = int(rlist.loc[rlist["name"] == retailer_name, "retailer_id"].iloc[0])

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input("From Date", value=date.today().replace(day=1), key="bill_start")
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="bill_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_df = categories_active.copy() if not categories_active.empty else categories.copy()
    cat_names = cat_df["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    if not cat_names:
        st.error("No categories found.")
        st.stop()

    rrow = retailers.loc[retailers["retailer_id"].astype(int) == rid].iloc[0].to_dict()
    rrow["zone"] = _norm_zone(rrow.get("zone", "Default"))

    grid = build_bill_daily_grid(rid, start_day, end_day, cat_names)

    opening_due = retailer_balance_before(rid, start_day)
    closing_due = float(pd.to_numeric(grid["Running Due (₹)"], errors="coerce").fillna(opening_due).iloc[-1]) if not grid.empty else float(opening_due)

    if USE_SERVER_FILTERS:
        p = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("retailer_id", "eq", int(rid)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        p = payments.copy()
        if not p.empty:
            p["date"] = _safe_dt(p["date"]).dt.date
            p = p.loc[
                (p["retailer_id"].astype(int) == rid)
                & (p["date"] >= start_day)
                & (p["date"] <= end_day)
            ].copy()

    if p.empty:
        pay_mode_totals = pd.DataFrame(columns=["Mode", "Total (₹)"])
    else:
        p["payment_mode"] = p["payment_mode"].fillna("Cash").astype(str)
        pay_mode_totals = (
            p.groupby("payment_mode", as_index=False)["amount"]
             .sum()
             .sort_values("amount", ascending=False)
             .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

    total_sales = float(pd.to_numeric(grid["Sales (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_pay = float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0
    total_milk = float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum()) if not grid.empty else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Sales (This Period)", _fmt_money(total_sales))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()

    st.subheader("📌 Bill Preview (Arrow-safe)")

    preview = grid.copy()
    
    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"
        
        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)
            
        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)
            
    for c in ["Sales (₹)", "Payment (₹)", "Running Due (₹)"]:
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)
            
    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)

    st.dataframe(df_for_display(preview), width="stretch")

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if "cat_cols" in locals() and isinstance(cat_cols, list) and len(cat_cols) > 0:
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (not _cn) and ("categories" in locals()) and hasattr(categories, "empty") and (not categories.empty) and ("name" in categories.columns):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [f"{cat} Qty" for cat in cat_names if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum())
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum())
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric("Payments Collected (₹)", f"₹{grand_pay:.2f}")    # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(lambda x: f"{float(x):.2f}")
        st.dataframe(df_for_display(tot_df), width="stretch")


    st.subheader("💳 Payment Mode Totals (Period)")
    if pay_mode_totals.empty:
        st.info("No payments in this period.")
    else:
        st.dataframe(pay_mode_totals.style.format({"Total (₹)": "₹{:.2f}"}), width="stretch")

    # --- Print ONLY categories that were purchased (qty > 0 anywhere in the period) ---
    purchased_cats = []
    if grid is not None and not grid.empty:
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol not in grid.columns:
                continue
            # grid can contain numbers or "-" strings, so coerce safely
            qty_series = pd.to_numeric(grid[qcol], errors="coerce").fillna(0.0)
            if (qty_series > 0).any():
                purchased_cats.append(cat)
                
    # If nothing detected (edge case), fallback to original cat_names so bill isn't empty/broken
    cats_for_print = purchased_cats if purchased_cats else cat_names
    
    html = build_bill_html(rrow, start_day, end_day, grid, pay_mode_totals, cats_for_print, opening_due)


    st.subheader("🖨️ Printable Bill")
    st.components.v1.html(html, height=750, scrolling=True)

    st.caption("To print: click the Print button in the bill OR download HTML and press Ctrl+P.")
    st.download_button(
        "⬇️ Download Bill (HTML - Print Ready)",
        data=html.encode("utf-8"),
        file_name=f"bill_{retailer_name}_{start_day}_to_{end_day}.html",
        mime="text/html",
        key="bill_dl_html",
    )

    pdf_bytes = bill_pdf_bytes_from_html(html)
    if pdf_bytes is not None:
        st.download_button(
            "⬇️ Download Bill (PDF)",
            data=pdf_bytes,
            file_name=f"bill_{retailer_name}_{start_day}_to_{end_day}.pdf",
            mime="application/pdf",
            key="bill_dl_pdf",
        )

# ================== DATA HEALTH & BACKUP ==================
elif menu == "🛡️ Data Health & Backup":
    st.header("🛡️ Data Health & Backup")

    st.subheader("Backups")
    st.caption("Download a ZIP containing CSV exports of all tables currently in the app.")
    dv = st.session_state.get("data_version", 0)
    # Keep bytes stable across reruns to avoid duplicate downloads in some browsers.
    if st.session_state.get("backup_zip_version") != dv or "backup_zip_bytes" not in st.session_state:
        st.session_state["backup_zip_bytes"] = make_full_backup_zip(dv)
        st.session_state["backup_zip_version"] = dv
        
    zip_bytes = st.session_state["backup_zip_bytes"]
    
    st.download_button(
        "⬇️ Download Full Backup ZIP (CSV)",
        data=zip_bytes,
        file_name=f"milk_accounting_backup_{date.today().isoformat()}.zip",
        mime="application/zip",
        key=f"backup_zip_{dv}",
        width="stretch",
    )


    st.divider()



    st.subheader("📊 Range CSV Backup — Full Daily Detail")
    st.caption(
        "One row per date. Columns: Date | per-retailer qty per category | "
        "retailer sales ₹ | previous ledger ₹ | payments ₹ | total ledger ₹ | "
        "distributor purchases per category | distributor purchase amt ₹ | "
        "distributor payments ₹ | wastage per category."
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        b_start = st.date_input("From Date", value=date.today().replace(day=1), key="backup_start")
    with bc2:
        b_end = st.date_input("To Date", value=date.today(), key="backup_end")

    if st.button("📥 Generate & Download Detailed CSV", type="primary", key="backup_gen"):
        with st.spinner("Building report…"):

            # Fetch ALL data (full history needed for opening balances)
            _e_all = sb_fetch_df(ENTRIES_FILE, CSV_SCHEMAS[ENTRIES_FILE], filters=[])
            _p_all = sb_fetch_df(PAYMENTS_FILE, CSV_SCHEMAS[PAYMENTS_FILE], filters=[])
            _dp_all = sb_fetch_df(DISTRIBUTOR_PURCHASES_FILE, CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE], filters=[])
            _dpay_all = sb_fetch_df(DISTRIBUTOR_PAYMENTS_FILE, CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE], filters=[])

            _csv_bytes = make_range_backup_csv(
                start_date=b_start,
                end_date=b_end,
                retailers=retailers,
                categories=categories,
                entries=_e_all,
                payments=_p_all,
                dist_purchases=_dp_all,
                dist_payments=_dpay_all,
                distributors=distributors,
            )

            _fname = f"range_backup_{b_start.strftime('%d-%m-%y')}_to_{b_end.strftime('%d-%m-%y')}.csv"

            st.success(f"✅ Report ready.")
            st.download_button(
                label="📥 Download Range Report",
                data=_csv_bytes,
                file_name=_fname,
                mime="text/csv",
                key="range_csv_dl",
            )




    st.subheader("Integrity Checks")

    issues = []

    if not entries.empty and not retailers.empty:
        known_r = set(retailers["retailer_id"].astype(int))
        bad = entries.loc[~entries["retailer_id"].astype(int).isin(known_r)][["entry_id", "retailer_id", "date", "amount"]]
        if not bad.empty:
            issues.append(("Orphan retailer_id in entries", bad))

    if not payments.empty and not retailers.empty:
        known_r = set(retailers["retailer_id"].astype(int))
        bad = payments.loc[~payments["retailer_id"].astype(int).isin(known_r)][["payment_id", "retailer_id", "date", "amount"]]
        if not bad.empty:
            issues.append(("Orphan retailer_id in payments", bad))

    if not entries.empty and not categories.empty:
        known_c = set(categories["category_id"].astype(int))
        bad = entries.loc[~entries["category_id"].astype(int).isin(known_c)][["entry_id", "category_id", "date", "amount"]]
        if not bad.empty:
            issues.append(("Orphan category_id in entries", bad))

    if not entries.empty:
        bad = entries.loc[(entries["qty"] < 0) | (entries["rate"] < 0) | (entries["amount"] < 0)]
        if not bad.empty:
            issues.append(("Negative values in entries", bad))

    if not payments.empty:
        bad = payments.loc[payments["amount"] < 0]
        if not bad.empty:
            issues.append(("Negative payments", bad))

    for name, df, idcol in [
        ("entries", entries, "entry_id"),
        ("payments", payments, "payment_id"),
        ("prices", prices, "price_id"),
        ("retailers", retailers, "retailer_id"),
        ("categories", categories, "category_id"),
        ("distributors", distributors, "distributor_id"),
    ]:
        if not df.empty and idcol in df.columns:
            dup = df[df[idcol].duplicated(keep=False)].sort_values(idcol)
            if not dup.empty:
                issues.append((f"Duplicate IDs in {name} ({idcol})", dup))

    if not entries.empty:
        chk = entries.copy()
        chk["calc"] = (chk["qty"].astype(float) * chk["rate"].astype(float)).round(2)
        chk["amount_r"] = chk["amount"].astype(float).round(2)
        bad = chk.loc[(chk["qty"] > 0) & (chk["calc"] != chk["amount_r"])][["entry_id", "date", "qty", "rate", "amount", "calc"]]
        if not bad.empty:
            issues.append(("Entries amount mismatch (qty*rate != amount)", bad))

    if not issues:
        st.success("✅ No integrity problems found.")
    else:
        st.error(f"⚠️ Found {len(issues)} integrity issue group(s). Fix before trusting reports.")
        for title, df in issues:
            st.subheader(title)
            st.dataframe(df, width="stretch")
            st.divider()
  
