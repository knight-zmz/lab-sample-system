# Migration Baseline (MySQL -> SQLite)

## Entry

- Main entry: `app_stable.py`
- Routing style: single Streamlit app with sidebar menu -> `views/*.py`

## View to DB Object Mapping

- `views/sample_view.py`
  - Reads `v_sample_detail`
- `views/sample_add.py`
  - Calls `sp_register_sample`
- `views/borrow_sample.py`
  - Reads `v_sample_detail`
  - Calls `sp_borrow_sample`
- `views/return_sample.py`
  - Reads `v_current_borrowed_samples`
  - Calls `sp_return_sample`
- `views/sample_out.py`
  - Reads `v_sample_detail`
  - Calls `sp_move_sample`
  - Calls `sp_dispose_sample`
- `views/io_records.py`
  - Reads `v_current_borrowed_samples`
  - Reads `sample_transactions` joins
- `views/project_manage.py`
  - Reads `projects`
  - Reads `v_project_sample_statistics`
  - Writes `projects` via SQL

## Current Data Access Layer

- `db.py`
  - Uses `pymysql` connection
  - Exposes `query_df`, `fetch_*`, `execute`, `execute_action`, `call_procedure`
  - Converts MySQL errors to user messages

## MySQL-Specific Runtime Coupling

- Runtime API coupling:
  - `pymysql`
  - stored procedures through `call_procedure`
- SQL object coupling:
  - Views: `v_sample_detail`, `v_current_borrowed_samples`, `v_project_sample_statistics`
  - Procedures: `sp_register_sample`, `sp_borrow_sample`, `sp_return_sample`, `sp_move_sample`, `sp_dispose_sample`

## Deployment Coupling

- `README.md` documents Railway-based env and start command
- No `railway.json`, `Procfile`, `Dockerfile`, `nixpacks.toml` found

## Baseline Acceptance Checklist

- App starts with existing command
- Sidebar contains all original business menus
- All seven business pages render
- Existing write flows still available before migration replacement
