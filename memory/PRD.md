# Milk Accounting Pro — Production Stability & Ledger Correctness Fix Pack

## Problem Statement
Existing Streamlit + Supabase app (`ROHIT-KAWLE/milk_account`, `app.py` on `main`)
suffering from:
1. **Random segfaults** on Streamlit Community Cloud (Linux) — root cause: Supabase
   `numeric` → Python `Decimal` → pandas `object` dtype → PyArrow C++ serializer
   crash inside `@st.cache_data` / AgGrid.
2. **Ledger correctness drift** — same-day entries sorted non-deterministically
   (no `entry_id` tiebreaker), float drift on cumsums, cache invalidation gaps
   on `sb_delete_*` helpers.

Target: Streamlit Community Cloud, Python 3.12, Supabase.

## Architecture
- Single-file Streamlit app (`app.py`, 6.9k lines)
- Backend: Supabase (`supabase-py` v2.9.1) — retailers, categories, prices,
  entries, payments, distributors, distributor_purchases, distributor_payments,
  distributor_category_map, wastage, expenses
- Frontend: Streamlit widgets + `streamlit-aggrid` for the Daily Entry grid
- Deployment: Streamlit Community Cloud (`.streamlit/config.toml`,
  `.streamlit/secrets.toml`, `runtime.txt=python-3.12`)

## What's Been Implemented (2026-01)

### Native stack pinned (PATCH 1)
`requirements.txt` — every native ABI locked to a combo that does not segfault
on Linux under AgGrid 1.x: `streamlit==1.39.0`, `streamlit-aggrid==1.0.5`,
`pandas==2.2.3`, `numpy==1.26.4`, `pyarrow==17.0.0`, `plotly==5.24.1`,
`supabase==2.9.1`, `python-dateutil==2.9.0`.

### Streamlit config (PATCH 2)
`.streamlit/config.toml` — disabled `runOnSave`, `fileWatcherType`,
`enableWebsocketCompression`; capped uploads. (The originally-suggested
`global.dataFrameSerialization = "legacy"` option was **removed by Streamlit
in 1.28** — replaced with Arrow-safe boundary normalisation, which is what
that option was masking.)

### Arrow-safe DataFrame boundary (PATCH 3)
- Added `_arrow_safe_frame()` helper that coerces every column:
  - numeric-looking object → `float64`
  - other object → pandas `string` dtype (never NaN + object mix)
  - `date` / `effective_date` / `day` → tz-naive `datetime64[ns]` normalized
  - `*_id` float → `int64`
- Applied inside `sb_fetch_all()` (returns raw `pd.DataFrame(out)`) **and**
  inside `_normalize_df_from_rows()` — every Supabase read is now Arrow-safe
  before it can hit `@st.cache_data`.

### Deterministic ledger (PATCH 4)
- Rewrote `compute_ledger_fast(entries, payments)` — vectorised, stable
  mergesort, `retailer_id → date → kind (S<P) → primary key` tiebreaker chain,
  `.round(2)` on cumsum output. No more `iterrows`, no more shuffled sort.
- Added `compute_distributor_ledger_fast(purchases, payments)` — same
  deterministic pattern for distributor side, `kind (B<P)` ordering.

### Cache-invalidation gaps closed (PATCH 5)
- `invalidate_data_cache()` now bumps `data_version` **and** calls
  `st.cache_data.clear()` (previously a no-op cache clear).
- `sb_delete_by_pk()` and `sb_delete_where()` (both branches) now call
  `invalidate_data_cache()` after every delete.

### AgGrid mutation protection (PATCH 6)
- Added `_safe_for_grid(df)` — deep-copy + datetime-to-string + object-to-string,
  so AgGrid can never mutate a cached DataFrame reference (previous cause of
  double-free / use-after-free on rerun).
- Both AgGrid call sites (`daily_form_{ctx}` retailer grid + `dist_grid_*`
  distributor grid) now:
  - pass `_safe_for_grid(df)` instead of the raw frame
  - set `update_mode=GridUpdateMode.MODEL_CHANGED` (not the crash-prone
    `VALUE_CHANGED_OR_RELOAD_DATA`)
  - set `reload_data=False` (was a documented segfault vector)
  - include `data_version` in their `key` so a data change forces a fresh
    grid instance rather than mutating an in-cache one
  - `suppressColumnVirtualisation=True` for stable render identity

### daily_retailer_ledger (PATCH 7)
- Verified: **no such table exists in this codebase.** Nothing to demote —
  all ledger UI already goes through `compute_ledger_fast` /
  `cached_opening_balances`. Patch 7 is a no-op for this repo.

### Money helper (PATCH 8)
- Added `money(x) -> float` — Decimal HALF_UP rounding to 2dp with NaN/inf
  fallback to `0.0`. Available module-wide for any UI/export path that needs
  it.

### Session-state hygiene (PATCH 9)
- Added `_sanitize_page_state(current_page)` which purges heavy grid buffers
  (`daily_drafts`, `dist_flat_grid`, `dist_flat_payments`) whenever the sidebar
  page changes. Prevents 1 GB memory cap OOM on Streamlit Cloud after several
  navigations.

### Historical reconciliation
- `reconcile_history.py` — one-shot audit script. Boots the app under
  `streamlit.testing.v1.AppTest`, refetches all raw data, recomputes every
  retailer + distributor closing balance with the new deterministic ledger,
  diffs it against the app's cached opening/closing snapshot. Exits `0` clean
  / `2` on drift.

  **Live audit run against the current Supabase**:
  - 10,092 entries × 4,425 payments × 93 retailers → 14,517 ledger rows,
    zero drift outside ±₹0.01
  - 669 purchases × 7 dist payments × 6 distributors → 676 ledger rows,
    zero drift

### Live smoke test
- `smoke_test.py` — runs Arrow round-trip, ledger determinism, money helper,
  `_safe_for_grid` deep-copy behaviour, plus a live Supabase → ledger flow.
  **All tests pass** on real production data.

## Verification results (2026-01)
1. `python smoke_test.py` → ALL TESTS PASSED (6/6)
2. `python reconcile_history.py` → total drift = 0
3. `streamlit run app.py` + browser screenshot → dashboard renders full
   Business Overview (₹2.54 Cr sales, ₹2.15 Cr payments, ₹39.83 L
   outstanding) with all 17 nav pages, no error overlay, no crash.

## Prioritized backlog
- **P1** — Convert callers of `distributor_balance_before` to use
  `compute_distributor_ledger_fast` for cross-page consistency (currently a
  parallel path — same math, slightly higher round-trip cost).
- **P2** — Add unit tests for the ledger under CI so future refactors can't
  reintroduce non-determinism.
- **P2** — Wire `money()` into every user-facing balance render + CSV export.
- **P3** — Emit `entry_id` sort chain in the Excel/CSV exports so external
  reconciliations can be reproduced offline.

## Files touched
- `requirements.txt` — rewritten (pin the native stack)
- `.streamlit/config.toml` — extended (server hardening)
- `app.py` — surgical edits only:
  - imports (`numpy`, `Decimal`, `GridUpdateMode`)
  - `invalidate_data_cache()` now clears `st.cache_data`
  - new helpers: `_arrow_safe_frame`, `_safe_for_grid`, `money`,
    `_sanitize_page_state`
  - `sb_fetch_all`, `_normalize_df_from_rows` use `_arrow_safe_frame`
  - `sb_delete_by_pk`, `sb_delete_where` call `invalidate_data_cache`
  - `compute_ledger_fast` — deterministic rewrite
  - new: `compute_distributor_ledger_fast`
  - both `AgGrid(...)` sites hardened
  - sidebar `menu` block calls `_sanitize_page_state(menu)`

New files:
- `smoke_test.py`
- `reconcile_history.py`
