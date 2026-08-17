# Python Mini Projects

Eight small Python projects, each pairing a core exercise with an "advanced
challenge" extension. Role/fraud lean on **tuples + sets**; inventory leans
on **dictionaries** with nested per-branch state; the transaction/e-commerce
pair leans on **loops and dict aggregation** over lists of records, plus a
Flask REST layer as a stretch goal; the games/contacts pair leans on
**stateful classes and JSON persistence**.

## Contents

| File | Description |
|---|---|
| `role_manager.py` | Admin-dashboard role manager: assign users to roles, check role membership, find users with multiple roles, list all unique users. Includes JSON persistence and a role hierarchy. |
| `fraud_detection.py` | Rule-based fraud scoring engine: loads rules from JSON, tracks unique transactions/users/devices, and scores transactions against a blocklist and failed-attempt history. |
| `fraud_rules.json` | Sample rule config consumed by `fraud_detection.py` (rule weights, IP blocklist, risk thresholds). |
| `inventory_tracker.py` | Command-line inventory tracker for a single shop: add/find/update/sell/remove products, low-stock alerts, total inventory value, JSON persistence, sales history, and a menu-driven CLI. |
| `multi_branch_inventory.py` | Advanced challenge: multi-branch inventory service with branch-level lookups, validated stock transfers, global stock totals, per-branch low-stock alerts, sales reporting, and a full audit log of every stock movement. |
| `transaction_analyzer.py` | Microfinance transaction analyzer: total volume, average value, most active customers, fraud-threshold alerts, most frequent transaction type, date filtering, grouping by customer, and CSV report export. |
| `ecommerce_analytics.py` | Advanced challenge: e-commerce analytics backend — daily/weekly/monthly totals, top-selling products, customer purchase frequency, unusual-pattern (fraud) detection, order-value percentiles, and week-over-week trend analysis. |
| `flask_api.py` | Stretch goal: a Flask REST API exposing every `ecommerce_analytics.py` metric as a JSON endpoint, with optional date-range query params, plus a browsable landing page. |
| `number_guessing_game.py` | Interactive number guessing game with high/low + hot/warm/cold hints, selectable difficulty levels, a score based on attempts and solve speed, JSON-persisted high scores, and replay. |
| `contact_manager.py` | Single-user contact manager: add/view/update/delete/search contacts, statistics, JSON backup/export, and a menu-driven CLI. |
| `multi_user_contact_system.py` | Advanced challenge: multi-user contact management with password-hashed auth, per-user contact isolation, fuzzy + phone-pattern + company/date search, an analytics dashboard (per-user and system-wide), CSV import, JSON/vCard export, and a full audit trail. |

## Requirements

- Python 3.8+
- Everything except `flask_api.py` uses only the standard library
  (`json`, `csv`, `hashlib`, `difflib`, `re`, `datetime`, etc.).
- `flask_api.py` needs Flask: `pip install -r requirements.txt`.

## Usage

### Role Manager

```bash
python3 role_manager.py
```

Runs a demo that:
- defines three roles (`admin`, `manager`, `user`) with capacity limits
- assigns users, rejecting duplicates and over-capacity assignments
- checks individual role membership
- finds users holding multiple roles
- lists all unique users across every role
- saves the current state to `role_manager_state.json` and reloads it

**Core API**

```python
from role_manager import RoleManager

roles = [
    ("r1", "admin", 2),
    ("r2", "manager", 3),
    ("r3", "user", 10),
]

mgr = RoleManager(roles)
mgr.assign_user("r1", "alice")
mgr.has_role("alice", "r1")            # -> True
mgr.users_with_multiple_roles()        # -> set of users in 2+ roles
mgr.all_unique_users()                 # -> set of every assigned user

mgr.save("state.json")
mgr2 = RoleManager.load("state.json")
```

### Fraud Detection

```bash
python3 fraud_detection.py
```

Runs a demo that scores a handful of sample transactions against
`fraud_rules.json` and prints each transaction's score, triggered rules,
and recommended action (`ALLOW` / `REVIEW` / `BLOCK`).

**Core API**

```python
from fraud_detection import FraudDetectionSystem, Transaction

fds = FraudDetectionSystem("fraud_rules.json")
fds.mark_failed_attempt("user_42")

result = fds.score_transaction(
    Transaction("txn_001", "user_42", "device_B", "203.0.113.9", 999.00)
)
print(result.score, result.action, result.triggered_rules)
```

**Config format (`fraud_rules.json`)**

```json
{
  "rules": [
    ["RULE001", "blocklisted_ip", 40, "IP address appears on the known-bad blocklist"]
  ],
  "blocklisted_ips": ["203.0.113.9"],
  "thresholds": { "review": 30, "block": 60 }
}
```

Each rule is `[rule_id, rule_type, weight, description]`. Add, remove, or
reweight rules without touching code — just edit the JSON.

### Inventory Tracker

```bash
python3 inventory_tracker.py          # interactive menu
python3 inventory_tracker.py --test   # run automated self-tests, no input needed
```

On startup the CLI auto-loads `inventory_data.json` if it exists, and saves
to it on exit (or via the "Save to file" menu option). The menu covers every
required operation: add, view, search by SKU, update quantity, sell, remove,
low-stock report, and total inventory value.

**Core API**

```python
from inventory_tracker import InventoryTracker

t = InventoryTracker()
t.add_product("SKU-1001", "USB-C Charger", 25.50, 4, reorder_level=5,
               category="Accessories", supplier="Acme")
t.sell_product("SKU-1001", 2)            # -> (True, "Sold 2 x SKU-1001 for 51.00.")
t.get_low_stock_products()               # -> {sku: product, ...}
t.calculate_inventory_value()            # -> float

t.save_to_json("inventory_data.json")
t.load_from_json("inventory_data.json")
```

Each product is stored as:

```python
{
    "name": "USB-C Charger",
    "price": 25.50,
    "quantity": 4,
    "reorder_level": 5,
    "category": "Accessories",
    "supplier": "Acme Electronics",
}
```

### Multi-Branch Inventory Service

```bash
python3 multi_branch_inventory.py          # runs a scripted demo
python3 multi_branch_inventory.py --test   # run automated self-tests
```

**Core API**

```python
from multi_branch_inventory import MultiBranchInventoryService

svc = MultiBranchInventoryService()
svc.add_product("Lagos", "SKU-1001", "Wireless Keyboard", 45.99, 12, reorder_level=5)
svc.add_product("Abuja", "SKU-1001", "Wireless Keyboard", 45.99, 5, reorder_level=5)

svc.branch_stock("Lagos", "SKU-1001")            # -> product dict or None
svc.transfer_stock("Lagos", "Abuja", "SKU-1001", 4)  # validated, audited
svc.global_stock_totals()                        # -> {"SKU-1001": 17}
svc.low_stock_alerts()                           # -> {branch: {sku: product}}
svc.sell_product("Abuja", "SKU-1001", 2)
svc.sales_report("Abuja")                        # -> {branch, transactions, units_sold, total_revenue}
svc.audit_log                                    # -> list of every add/sale/transfer event
```

A failed transfer (insufficient stock, or same source/destination) never
mutates the inventory — it's validated up front and logged as
`transfer_failed` in the audit log.

### Transaction Analyzer

```bash
python3 transaction_analyzer.py          # demo report + filtered report + CSV export
python3 transaction_analyzer.py --test   # automated self-tests
```

**Core API**

```python
from transaction_analyzer import (
    sample_transactions, generate_report, print_report,
    filter_by_date, group_by_customer, export_report_to_csv,
)

txns = sample_transactions()
report = generate_report(txns, threshold=50_000)
print_report(report)

# Improvements
last_three_days = filter_by_date(txns, "2026-08-01", "2026-08-03")
by_customer = group_by_customer(txns)
export_report_to_csv(report, "transaction_report.csv")
```

Each transaction is stored as:

```python
{"customer": "Alice", "amount": 5000, "type": "transfer", "date": "2026-08-01"}
```

`generate_report()` returns total count, total volume, average value, most
frequent transaction type, most active customers, and the list of
fraud-threshold alerts (₦50,000 by default) — all computed with explicit
loops over the transaction list.

### E-commerce Sales Dashboard Backend

```bash
python3 ecommerce_analytics.py          # prints a full dashboard report
python3 ecommerce_analytics.py --test   # automated self-tests
```

**Core API**

```python
from ecommerce_analytics import sample_orders, generate_dashboard_report

orders = sample_orders()
report = generate_dashboard_report(orders, fraud_value_threshold=2000, max_orders_per_day=2)

report["daily_totals"]              # {"2026-08-01": 960.0, ...}
report["weekly_totals"]             # {"2026-W31": 2255.0, ...}
report["top_products"]              # [("Laptop", {"quantity_sold": 9, "revenue": 7650.0}), ...]
report["customer_frequency"]        # {"CUST123": 4, ...}
report["unusual_orders"]            # orders at/above the value threshold
report["unusual_customer_activity"] # same customer, multiple orders, same day
report["order_value_percentiles"]   # {"p50": ..., "p90": ..., "p95": ..., "p99": ...}
report["week_over_week_growth"]     # {"2026-W31": None, "2026-W32": 114.0, ...}
```

Order value is computed once, in `order_total()`, by summing `quantity *
price` across an order's line items (the orders → items nested loop) — every
other metric reuses that function instead of recomputing it.

### Flask API (Stretch Goal)

```bash
pip install flask
python3 flask_api.py
# -> http://127.0.0.1:5000/api/dashboard
```

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/daily-totals` | Revenue per day |
| `GET /api/weekly-totals` | Revenue per ISO week |
| `GET /api/monthly-totals` | Revenue per month |
| `GET /api/top-products?top_n=5` | Top-selling products by revenue |
| `GET /api/customer-frequency` | Order count per customer |
| `GET /api/customer-spend` | Total spend per customer |
| `GET /api/fraud-alerts?value_threshold=2000&max_orders_per_day=2` | Unusual orders + unusual same-day activity |
| `GET /api/percentiles` | Order-value percentiles (p50/p90/p95/p99) |
| `GET /api/trend` | Week-over-week revenue growth |
| `GET /api/dashboard` | Full combined report |

Every endpoint accepts optional `?start=YYYY-MM-DD&end=YYYY-MM-DD` to scope
the metric to a date range. The API is a thin routing layer — all analytics
logic lives in `ecommerce_analytics.py`, so the two stay in sync by
construction. Visiting `http://127.0.0.1:5000/` shows a landing page linking
every endpoint above.

### Number Guessing Game

```bash
python3 number_guessing_game.py          # interactive game
python3 number_guessing_game.py --test   # automated self-tests
```

Pick a difficulty (`easy` 1–50, `medium` 1–100, `hard` 1–200, each with its
own attempt limit), then guess. Every guess gets a direction hint ("too
high"/"too low") plus a proximity hint (🔥 hot / 🌡️ warm / ❄️ cold). Winning
records your name and score to `high_scores.json`, which persists across
runs and can be filtered by difficulty.

**Core API**

```python
from number_guessing_game import GuessingGame, HighScoreTracker

game = GuessingGame(difficulty="medium")
result = game.make_guess(50)          # -> {"guess", "attempt", "hint", "game_over", ...}
game.calculate_score()                # base score (attempts) + speed bonus, up to 120

scores = HighScoreTracker("high_scores.json")
scores.add_score("Alice", 90, "medium", attempts=4)
scores.top_scores(difficulty="medium", top_n=5)
```

### Contact Manager

```bash
python3 contact_manager.py          # interactive menu
python3 contact_manager.py --test   # automated self-tests
```

Single-user contact list backed by a dict of `name -> contact details`, with
add/view/update/delete/search, JSON auto-backup on exit, and a stats view.
This is the foundation `multi_user_contact_system.py` builds on.

### Multi-User Contact Management System (Advanced Challenge)

```bash
python3 multi_user_contact_system.py          # scripted two-user demo
python3 multi_user_contact_system.py --test   # automated self-tests
```

**Core API**

```python
from multi_user_contact_system import MultiUserContactSystem

sys_ = MultiUserContactSystem(data_file="contacts.json")
sys_.register_user("alice", "hunter2")
sys_.login("alice", "hunter2")

sys_.add_contact("Jonathan Smith", "555-9999", "jsmith@acme.com", company="Acme")
sys_.fuzzy_search("Jonathon Smith")            # typo-tolerant -> finds "Jonathan Smith"
sys_.search_by_phone_pattern(r"^555-9")        # regex over phone numbers
sys_.filter_contacts(company="acme", added_after="2026-08-01")

sys_.get_analytics()                           # per-user dashboard
sys_.get_global_analytics()                    # system-wide dashboard
sys_.get_audit_trail("alice")                  # every operation, timestamped

sys_.import_from_csv("contacts.csv")           # name,phone,email,company,notes
sys_.export_to_json("backup.json")
sys_.export_to_vcard("alice.vcf")

sys_.save()                                    # persist users + audit log + search stats
```

Each user's contacts live in their own dict under `users[username]["contacts"]`,
so two users can have a contact with the same name without collision.
Passwords are hashed with SHA-256 before storage (documented in the module
as a simplification — a real system would use a salted, slow KDF like
bcrypt or argon2).

## Design Notes

- **Tuples for definitions, sets for membership.** Role definitions and
  fraud rules don't change at runtime, so they're stored as tuples.
  Assignments and tracked IDs change constantly and must stay
  duplicate-free, so they're stored as sets.
- **Set algebra does the heavy lifting.** `users_with_multiple_roles` is a
  pairwise intersection across role sets; `all_unique_users` is a union.
- **Rules and config are data, not code.** Fraud rules load from JSON at
  startup, so thresholds and blocklists can be updated without a
  deployment.

- **Dicts model structured records; nesting models hierarchy.** Each
  product is a dict of named fields; wrapping that in `branch -> sku ->
  product` extends the same idea to model "the same SKU, independently
  stocked per location" without inventing a new structure.
- **Validate before you mutate.** `transfer_stock` checks source-branch
  availability *before* touching either branch's data, so a rejected
  transfer never leaves inventory half-updated.
- **Every mutation is audited.** Adds, sales, transfers, and failed
  transfers all append a timestamped record to `audit_log`, giving a
  trail of stock movements without needing a database.
- **One source of truth for derived values.** `order_total()` computes
  an order's value exactly once; every aggregation (daily totals, top
  products, percentiles, fraud checks) calls it rather than
  re-deriving the number, so there's no risk of two metrics disagreeing
  about what an order was worth.
- **The API layer stays thin.** `flask_api.py` only parses query params
  and serializes JSON — it imports and calls the same functions the
  plain-Python demo uses, so the CLI report and the API response can
  never drift apart.
- **Testable randomness.** `GuessingGame` accepts an internal
  `_target_override` so tests can pin the answer instead of depending on
  `random.randint`, while the real game still uses true randomness by
  default.
- **Isolation by construction.** In the multi-user contact system, every
  contact lives under `users[username]["contacts"]`, so per-user data
  can never leak across accounts — there's no shared contact dict to
  accidentally mix up.

## Possible Extensions

- Persist fraud-detection state (seen IDs, blocklist) the same way
  `RoleManager` persists roles.
- Add a real time-windowed velocity check instead of the duplicate-ID
  stand-in.
- Wire `RoleManager`'s hierarchy into an authorization check (e.g.
  "does this user's highest role outrank X?").
- Replace the nested-dict inventory with dataclasses or database tables
  (branches, products, stock_movements) once you need concurrency,
  historical queries, or many branches — deep dict nesting stops being
  maintainable well before that point.
- Expose `InventoryTracker` / `MultiBranchInventoryService` through a
  REST API (e.g. FastAPI) instead of a CLI.
- Add user authentication and per-branch access control.
- Back `transaction_analyzer.py` and `ecommerce_analytics.py` with a real
  database instead of in-memory sample lists, so date filtering and
  aggregation can run at scale.
- Add a lightweight frontend (e.g. a small React or HTML/JS page) that
  consumes `flask_api.py`'s JSON endpoints and renders charts.
- Extend fraud detection in both analyzers with velocity-based rules
  (e.g. N transactions/orders within a rolling time window) instead of
  same-day bucket checks.
- Add a tkinter (or web) GUI on top of `number_guessing_game.py`'s
  `GuessingGame` class — the game logic is already fully decoupled from
  the CLI, so a GUI only needs to call `make_guess()` and read the
  returned dict.
- Swap `multi_user_contact_system.py`'s SHA-256 hashing for a proper
  salted KDF (bcrypt/argon2) before using this anywhere near real
  credentials.
- Add session tokens / expiry to the multi-user system instead of a
  single `current_user` attribute, so it could safely back a real
  multi-request web backend.

## License

MIT — use freely.
