# eBay E2E Test Suite

Playwright · Python · pytest · Allure · **uv**

End-to-end tests against [ebay.com](https://www.ebay.com). Environment-specific URLs and browser settings live in `resources/<env>/config.json` (default env: **preprod**).

See also: [automation-exercise.md](docs/automation-exercise.md) — Playwright test anti-patterns, consequences, and fixes.

---

## Getting started

### Prerequisites

| Tool                             | Install / requirement                                                                                |
| -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh`                                                   |
| Python 3.13+                     | managed automatically by uv                                                                          |
| Allure CLI (report viewer)       | `brew install allure`                                                                                |
| eBay account                     | required for login tests and `--with-login` E2E (manual bootstrap via `scripts/bootstrap_ebay_auth`) |

### Setup

```bash
# 1. Clone / enter the project
cd /path/to/ebay-e2e-tests

# 2. Create the virtual environment and install dependencies
uv sync

# 3. Install Playwright browsers (Chromium only)
uv run playwright install chromium

# 4. Bootstrap eBay session (local only — needed for login tests and --with-login)
uv run python -m scripts.healthcheck          # optional standalone preflight
uv run python -m scripts.bootstrap_ebay_auth  # runs healthcheck automatically
```

uv creates a `.venv` in the project root on `uv sync`. Activate it manually if you prefer:

```bash
source .venv/bin/activate   # optional — `uv run` handles this for you
deactivate
```

> The `.venv` folder is git-ignored. Recreate it any time with `uv sync`.

### First test run

Run the search-and-cart suite (guest session — no auth required):

```bash
uv run pytest tests/test_search_and_cart.py
```

Open the Allure report after a run:

```bash
allure serve reports/allure-results
```

---

## Running tests

Tests live under `tests/`. Pytest markers defined in `pyproject.toml` let you filter by area.

Default pytest options (in `pyproject.toml`): `-s` (live stdout/stderr) and `-v` (verbose names). Plain `pytest` / `uv run pytest …` is enough — no need to pass those flags each time.

| Marker       | Scope                                                     |
| ------------ | --------------------------------------------------------- |
| `search`     | Search workflow (find products, apply price filters)      |
| `cart`       | Add-to-cart and cart total verification                   |
| `login`      | Session replay (requires `ebay-auth.json` from bootstrap) |
| `bootstrap`  | One-time manual sign-in to create `ebay-auth.json`        |
| `regression` | Full end-to-end regression cases                          |
| `smoke`      | Reserved for quick smoke checks                           |

### Search & cart (`tests/test_search_and_cart.py`)

Data-driven test class that runs **3 cases** from `tests/data/test_data.json` (TC001–TC003). Each case searches eBay, filters by price, adds items to cart, and verifies the subtotal.

| Case  | Query            | Price range | Items |
| ----- | ---------------- | ----------- | ----- |
| TC001 | wireless earbuds | $15–$60     | 3     |
| TC002 | phone case       | $10–$40     | 2     |
| TC003 | vintage watch    | $5–$50      | 4     |

```bash
# All 3 DDT cases
uv run pytest tests/test_search_and_cart.py

# Parallel — one worker per case (~3× faster than serial)
uv run pytest tests/test_search_and_cart.py -n 3

# One case by test ID (-k matches the parametrized id from test_data.json)
uv run pytest tests/test_search_and_cart.py -k TC001
uv run pytest tests/test_search_and_cart.py -k TC002
uv run pytest tests/test_search_and_cart.py -k TC003

# Headed mode for a single case (watch the browser)
HEADLESS=false uv run pytest tests/test_search_and_cart.py -k TC001

# Multiple cases (OR expression)
uv run pytest tests/test_search_and_cart.py -k "TC001 or TC003"

# By marker
uv run pytest -m search
uv run pytest -m cart
uv run pytest -m regression
```

Pytest shows parametrized cases as `test_search_add_cart[TC001]`, `test_search_add_cart[TC002]`, etc. Use `-k TC00x` or the full node name:

```bash
uv run pytest tests/test_search_and_cart.py::TestSearchAndCart::test_search_add_cart[TC002]
```

To add or change cases, edit `tests/data/test_data.json` — no code changes required.

### Pagination (`tests/test_search_pagination.py`)

Data-driven from `tests/data/pagination_data.json` (PG001). Verifies that page 2 returns mostly new listings.

| Case  | Query     | Price range | Pages |
| ----- | --------- | ----------- | ----- |
| PG001 | usb cable | $1–$50      | 2     |

```bash
# All pagination cases
uv run pytest tests/test_search_pagination.py

# Single case
uv run pytest tests/test_search_pagination.py -k PG001
HEADLESS=false uv run pytest tests/test_search_pagination.py -k PG001

# By marker
uv run pytest -m pagination
```

### Login (`tests/test_login.py`)

One test for eBay session replay. **Requires** `secured_env_files/ebay-auth.json` from manual bootstrap. Auto-skips when the session file is missing.

| Test                 | What it verifies                                         |
| -------------------- | -------------------------------------------------------- |
| `test_login_success` | Saved session is valid and post-login URL is on ebay.com |

```bash
# One-time manual sign-in (local only; healthcheck runs automatically)
uv run python -m scripts.bootstrap_ebay_auth

uv run pytest tests/test_login.py
uv run pytest -m login
```

### Search & cart with login (optional)

Guest session is the default. Pass `--with-login` to run search/cart E2E with a saved session:

```bash
uv run pytest tests/test_search_and_cart.py --with-login
```

### Common run patterns

Uses [pytest-xdist](https://pytest-xdist.readthedocs.io/) (`-n` workers). Each worker gets its own browser session; guest tests reuse a session-scoped Ship-to-US state per worker.

```bash
# Everything except login (default CI-style run)
uv run pytest tests/ -m "not login"

# Parallel search-and-cart (3 parametrized cases → 3 workers)
uv run pytest tests/test_search_and_cart.py -n 3

# Full suite including login
uv run pytest tests/

# Headless override (CI)
HEADLESS=true uv run pytest tests/ -m "not login"

# Headed mode (watch the browser)
HEADLESS=false uv run pytest tests/test_search_and_cart.py

# Different environment
TEST_ENV=staging uv run pytest tests/ -m "not login"
TEST_ENV=prod uv run pytest tests/ -m "not login"
```

---

## Repository layout

Top-level folders and what each one is for.

### `tests/`

Pytest entry points. Test files stay thin — they call **workflows** and assert outcomes. Shared test setup lives here, not in individual test files.

| Path                        | Purpose                                                     |
| --------------------------- | ----------------------------------------------------------- |
| `test_search_and_cart.py`   | Search → filter → add to cart → verify total (DDT)          |
| `test_search_pagination.py` | Search pagination — new listings on page 2 (DDT)            |
| `test_login.py`             | Sign-in and post-login URL checks                           |
| `conftest.py`               | DDT parametrisation from JSON, Allure before-hooks          |
| `models.py`                 | Typed test data models (`SearchCartCase`, `PaginationCase`) |
| `data/test_data.json`       | Input data for search/cart cases (query, prices, limits)    |
| `data/pagination_data.json` | Input data for pagination cases                             |

### `pages/`

[Page Object Model](https://playwright.dev/python/docs/pom) — one class per eBay screen. Pages wrap Playwright locators and user actions; tests and workflows call page methods instead of raw selectors.

| Path              | Purpose                                                         |
| ----------------- | --------------------------------------------------------------- |
| `base_page.py`    | Shared helpers (navigation, waits, common clicks)               |
| `home_page.py`    | Landing page — global search box                                |
| `search_page.py`  | Search results — price filter, pagination, product cards        |
| `product_page.py` | Listing detail — variants, add-to-cart                          |
| `cart_page.py`    | Cart — line items, subtotal, checkout button                    |
| `login_page.py`   | Sign-in form and account navigation                             |
| `locators/`       | CSS selectors split by page (keeps page classes readable)       |

### `workflows/`

Reusable multi-step business flows composed from page objects. Keeps test files short and makes flows shareable across test classes.

| Module                 | Function              | Description                                                         |
| ---------------------- | --------------------- | ------------------------------------------------------------------- |
| `search_items.py`      | `search_items()`      | Search, apply price filter via URL, collect product URLs, write CSV |
| `add_items_to_cart.py` | `add_items_to_cart()` | Open listings, pick variants, add to cart, capture screenshots      |
| `assert_cart_total.py` | `assert_cart_total()` | Verify subtotal and line items from the cart page DOM |
| | `assert_cart_total_not_exceeds()` | Exercise check: `subtotal <= budget_per_item × items_count` |
| `ensure_logged_in.py`  | `ensure_logged_in()`  | Validate saved session from `ebay-auth.json`                        |

### `utilities/`

Shared non-page helpers used by tests, workflows, and fixtures.

| Path                  | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `config_loader.py`    | Load `resources/<env>/config.json`                        |
| `auth_storage.py`     | Save/load `secured_env_files/ebay-auth.json` (local only) |
| `verifications.py`    | Reusable assertion helpers with clear failure messages    |
| `common_ops.py`       | Price-filter predicates, pagination helpers               |
| `csv_writer.py`       | Thread-safe CSV writer for search results                 |
| `logger.py`           | Structured test logging (shown live in terminal)          |
| `screenshot_utils.py` | Capture PNGs and attach to Allure on failure              |
| `trace_utils.py`      | Playwright trace zip on failure (attach to Allure)        |
| `timeouts.py`         | Shared Playwright timeout constants (max 30 s)            |
| `random_data.py`      | Faker-backed text generators                              |

### `resources/`

Per-environment configuration. Set `TEST_ENV` to pick the folder (`staging`, `preprod`, `prod`). Default is **preprod**.

Each `config.json` includes `base_url`, `headless`, `slow_mo`, `timeout`, `screenshot_on_failure`, `trace_on_failure`, and `retry_count`.

### `secured_env_files/`

Local session storage — never commit real session files.

| Path             | Purpose                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------- |
| `ebay-auth.json` | Saved browser session from `uv run python -m scripts.bootstrap_ebay_auth` (git-ignored) |

### Output & artifacts (git-ignored)

| Path           | Purpose                                                 |
| -------------- | ------------------------------------------------------- |
| `reports/`     | Allure results, optional Playwright videos, traces (if enabled) |
| `downloads/`   | CSV output from `search_items()` (`search_results.csv`) |
| `screenshots/` | Per-run PNG captures                                    |

### Debugging artifacts

| Artifact | Status | Where |
| -------- | ------ | ----- |
| Allure report | enabled | `reports/allure-results/` — steps, attachments, env metadata |
| PNG screenshots | enabled | `screenshots/` + Allure attachments (add-to-cart, cart verify, failures) |
| Video (WebM) | optional | `reports/videos/` when `record_video: true` in config |
| Playwright trace | enabled on failure | `reports/traces/` + Allure zip attachment — open at [trace.playwright.dev](https://trace.playwright.dev) |
| HAR (network) | not enabled yet | `record_har_path` on browser context |
| Console / page errors | not enabled yet | `page.on("console")` / `page.on("pageerror")` → Allure text attachments |
| JUnit XML | not enabled yet | `pytest --junitxml=reports/junit.xml` for CI dashboards |
| CSV search log | enabled | `downloads/search_results.csv` |
| Terminal logs | enabled | live `[search]` / `[cart]` / `[verify]` output via pytest logging |

### Root & config files

| Path              | Purpose                                                                                 |
| ----------------- | --------------------------------------------------------------------------------------- |
| `conftest.py`     | Session/function fixtures — Playwright browser, context, page, `base_url`, Allure hooks |
| `pyproject.toml`  | Dependencies, pytest config, markers, logging                                           |
| `.flake8`         | Lint rules                                                                              |
| `.python-version` | Python version for uv (3.13)                                                            |

---

## Limitations & assumptions

| Topic | Assumption |
| ----- | ---------- |
| **Selectors (CSS vs XPath)** | The exercise sample uses XPath; this repo uses **CSS** (and ARIA roles where possible). CSS is generally faster, more readable, and aligns with [Playwright’s recommended locator strategy](https://playwright.dev/python/docs/locators). XPath is still used in a few fallback paths (e.g. cart subtotal label lookup). |
| **Auth** | Guest session by default. Login tests and `--with-login` replay a saved session from `ebay-auth.json` (manual bootstrap). eBay sign-in flows include CAPTCHA, 2FA, and bot detection — programmatic login is not reliable in CI, so session replay is the practical approach. |
| **Currency** | Price parsing targets **USD** (`US $`, `$`, `USD`). Foreign-currency-only listings are skipped. |
| **Environment profiles** | `staging` / `preprod` / `prod` differ in runtime settings (retries, video, slow_mo), not in target URL — all point at `https://www.ebay.com`. |
| **Cart budget check** | `assert_cart_total_not_exceeds(budget_per_item, items_count)` asserts `subtotal <= budget_per_item × items_count` (exercise contract). Defaults to `search.max_price` as the per-item budget. Optional `min_total` / `max_total` in JSON provide extra sanity bounds. |
| **Variant selection** | The exercise suggests random variant picks. This repo selects the **first valid option** per variant control (dropdown, radio, listbox). Random size/color choices often change the item price or select premium options, which would break the price-filter and budget assertions. |
| **Quantity selectors** | Not handled on the product page. Test cases add **one unit per listing** (`limit` = number of distinct URLs). Quantity inputs on eBay vary by listing type (spinbutton, dropdown, fixed qty) and changing qty would multiply the subtotal outside the `budget_per_item × items_count` formula. Quantity is read on the cart page when present, but never modified during add-to-cart. |

---

## Environment variables

| Variable          | Default     | Description                                                                            |
| ----------------- | ----------- | -------------------------------------------------------------------------------------- |
| `TEST_ENV`        | `preprod`   | `staging` / `preprod` / `prod` — selects `resources/<env>/config.json`                 |
| `WITH_LOGIN`      | —           | Set to `1` / `true` to run search/cart E2E with saved session (same as `--with-login`) |
| `HEADLESS`        | from config | `true` / `false` — override browser headless mode (shell/CI)                           |
| `SLOW_MO`         | from config | Browser slow-motion ms (shell/CI)                                                      |
| `DEFAULT_TIMEOUT` | from config | Playwright default timeout in ms, capped at **30000** (shell/CI)                       |

---

## Dependency management

Dependencies are declared in `pyproject.toml` and pinned at the **major-version** level.

```bash
uv add <package>                  # add a dependency
uv lock --upgrade && uv sync      # upgrade within major-version constraints
uv pip list                       # show installed versions
```

---

## Running in CI (GitHub Actions example)

```yaml
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v4
  with:
    python-version: "3.13"
- run: uv sync
- run: uv run playwright install --with-deps chromium
- run: uv run pytest tests/ -m "not login"
  env:
    TEST_ENV: preprod
    HEADLESS: "true"
- uses: actions/upload-artifact@v4
  with:
    name: allure-results
    path: reports/allure-results/
```
