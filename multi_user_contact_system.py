#!/usr/bin/env python3
"""
Multi-User Contact Management System with Search Analytics
=============================================================
Extends the single-user ContactManager into a multi-tenant system:
each user owns an isolated contact list, all guarded by simple
password auth, with fuzzy search, an analytics dashboard, CSV/JSON/
vCard import-export, and a full audit trail of every operation.

Data shape
----------
users = {
    "alice": {
        "password_hash": "<sha256 hex digest>",
        "created_at": "2026-08-01T12:00:00+00:00",
        "contacts": {
            "Bob Jones": {
                "phone": "555-1234",
                "email": "bob@acme.com",
                "company": "Acme",
                "notes": "",
                "created_at": "...",
                "updated_at": "...",
            }
        },
    },
    ...
}

Design notes
------------
- Passwords are hashed with SHA-256 (stdlib `hashlib`), not the naive
  built-in `hash()` from the spec's illustrative snippet -- `hash()` is
  salted per-process and unsuitable even for a toy auth system. This is
  still not production-grade (no per-user salt, no bcrypt/argon2), and
  the docstring says so, but it's a meaningful step up.
- Fuzzy search uses `difflib.get_close_matches`, which is stdlib and
  needs no extra dependency, to catch typos and partial matches beyond
  plain substring search.
- Every mutating operation appends a record to `operation_log`, so
  "who changed what, when" is always answerable -- the audit trail
  required by the advanced challenge.
- Analytics and audit methods operate per-user by default but can be
  called with `scope="global"` to aggregate across every user, which is
  how `most_searched_contact` and `average_contacts_per_user` are
  computed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from difflib import get_close_matches
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Contact = Dict[str, str]


def _hash_password(password: str) -> str:
    """
    SHA-256 hash of a password. NOTE: for real production auth you'd
    want a slow, salted KDF (bcrypt/scrypt/argon2) -- this is a
    deliberate, documented simplification for a learning project.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class MultiUserContactSystem:
    def __init__(self, data_file: str | Path = "multi_user_contacts.json"):
        self.users: Dict[str, Dict] = {}
        self.current_user: Optional[str] = None
        self.operation_log: List[Dict] = []
        # (username, contact_name) -> number of times surfaced in a search
        self.search_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.data_file = Path(data_file)
        self._load()

    # -- audit helper -------------------------------------------------------
    def _log(self, action: str, username: Optional[str], **details) -> None:
        self.operation_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": username,
            "action": action,
            **details,
        })

    # -- authentication -------------------------------------------------------
    def register_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Register a new user with an empty, isolated contact dictionary."""
        username = username.strip()
        if not username or not password:
            return False, "Username and password are required."
        if username in self.users:
            return False, f"Username {username!r} is already taken."

        self.users[username] = {
            "password_hash": _hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "contacts": {},
        }
        self._log("register", username)
        return True, f"User {username!r} registered."

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        user = self.users.get(username)
        if user is None or user["password_hash"] != _hash_password(password):
            self._log("login_failed", username)
            return False, "Invalid username or password."
        self.current_user = username
        self._log("login", username)
        return True, f"Welcome back, {username}."

    def logout(self) -> None:
        if self.current_user:
            self._log("logout", self.current_user)
        self.current_user = None

    def _require_login(self) -> str:
        if self.current_user is None:
            raise PermissionError("No user is logged in. Call login() first.")
        return self.current_user

    # -- CRUD (delegates to the logged-in user's contact dict) -------------------------------------------------
    def add_contact(
        self, name: str, phone: str, email: str, company: str = "", notes: str = ""
    ) -> Tuple[bool, str]:
        username = self._require_login()
        name = name.strip()
        if not name or not phone or not email:
            return False, "Name, phone, and email are required."

        contacts = self.users[username]["contacts"]
        if name in contacts:
            return False, f"Contact {name!r} already exists."

        now = datetime.now(timezone.utc).isoformat()
        contacts[name] = {
            "phone": phone.strip(),
            "email": email.strip(),
            "company": company.strip(),
            "notes": notes.strip(),
            "created_at": now,
            "updated_at": now,
        }
        self._log("add_contact", username, contact=name)
        return True, f"Contact {name!r} added."

    def get_contact(self, name: str) -> Optional[Contact]:
        username = self._require_login()
        return self.users[username]["contacts"].get(name.strip())

    def update_contact(self, name: str, **updates) -> Tuple[bool, str]:
        username = self._require_login()
        name = name.strip()
        contacts = self.users[username]["contacts"]
        if name not in contacts:
            return False, f"Contact {name!r} not found."

        valid_fields = {"phone", "email", "company", "notes"}
        changed = []
        for field, value in updates.items():
            if field in valid_fields and value is not None and str(value).strip():
                contacts[name][field] = str(value).strip()
                changed.append(field)

        contacts[name]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._log("update_contact", username, contact=name, fields=changed)
        return True, f"Contact {name!r} updated."

    def delete_contact(self, name: str) -> Tuple[bool, str]:
        username = self._require_login()
        name = name.strip()
        contacts = self.users[username]["contacts"]
        if name not in contacts:
            return False, f"Contact {name!r} not found."
        contacts.pop(name)
        self._log("delete_contact", username, contact=name)
        return True, f"Contact {name!r} deleted."

    def list_contacts(self) -> List[str]:
        username = self._require_login()
        return sorted(self.users[username]["contacts"].keys())

    # -- advanced search -------------------------------------------------
    def fuzzy_search(self, query: str, threshold: float = 0.6, max_results: int = 10) -> List[str]:
        """
        Approximate-match search over contact names (typo-tolerant),
        using difflib's ratio-based matcher.
        """
        username = self._require_login()
        query = query.strip()
        if not query:
            return []

        names = list(self.users[username]["contacts"].keys())
        matches = get_close_matches(query, names, n=max_results, cutoff=threshold)

        for name in matches:
            self.search_counts[(username, name)] += 1
        self._log("fuzzy_search", username, query=query, result_count=len(matches))
        return matches

    def search_by_phone_pattern(self, pattern: str) -> List[str]:
        """
        Search contacts whose phone number matches a regex pattern,
        e.g. r'^555-' or r'\\d{3}-4321$'.
        """
        username = self._require_login()
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid phone pattern: {e}") from e

        matches = [
            name
            for name, contact in self.users[username]["contacts"].items()
            if regex.search(contact.get("phone", ""))
        ]
        matches.sort()
        for name in matches:
            self.search_counts[(username, name)] += 1
        self._log("phone_pattern_search", username, pattern=pattern, result_count=len(matches))
        return matches

    def filter_contacts(
        self,
        company: Optional[str] = None,
        added_after: Optional[str] = None,
        added_before: Optional[str] = None,
    ) -> List[str]:
        """
        Filter contacts by company (case-insensitive substring) and/or
        a created_at date range (inclusive, 'YYYY-MM-DD' strings).
        """
        username = self._require_login()
        contacts = self.users[username]["contacts"]

        results = []
        for name, contact in contacts.items():
            if company and company.lower() not in contact.get("company", "").lower():
                continue
            created = contact.get("created_at", "")[:10]
            if added_after and created < added_after:
                continue
            if added_before and created > added_before:
                continue
            results.append(name)

        return sorted(results)

    # -- analytics dashboard -------------------------------------------------
    def get_analytics(self, username: Optional[str] = None) -> Dict:
        """Per-user analytics. Defaults to the currently logged-in user."""
        username = username or self._require_login()
        contacts = self.users[username]["contacts"]

        companies: Dict[str, int] = defaultdict(int)
        for contact in contacts.values():
            companies[contact.get("company") or "Unknown"] += 1

        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        added_this_month = sum(
            1 for c in contacts.values() if c.get("created_at", "").startswith(this_month)
        )

        most_searched = None
        best_count = 0
        for (u, name), count in self.search_counts.items():
            if u == username and count > best_count:
                most_searched, best_count = name, count

        return {
            "username": username,
            "total_contacts": len(contacts),
            "contacts_by_company": dict(companies),
            "contacts_added_this_month": added_this_month,
            "contacts_with_email": sum(1 for c in contacts.values() if c.get("email")),
            "contacts_with_phone": sum(1 for c in contacts.values() if c.get("phone")),
            "most_searched_contact": most_searched,
        }

    def get_global_analytics(self) -> Dict:
        """System-wide analytics across every registered user."""
        all_companies: Dict[str, int] = defaultdict(int)
        total_contacts = 0
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        added_this_month = 0

        for user_data in self.users.values():
            for contact in user_data["contacts"].values():
                total_contacts += 1
                all_companies[contact.get("company") or "Unknown"] += 1
                if contact.get("created_at", "").startswith(this_month):
                    added_this_month += 1

        most_searched = None
        best_count = 0
        aggregate_search: Dict[str, int] = defaultdict(int)
        for (_u, name), count in self.search_counts.items():
            aggregate_search[name] += count
        for name, count in aggregate_search.items():
            if count > best_count:
                most_searched, best_count = name, count

        user_count = len(self.users) or 1  # avoid ZeroDivisionError

        return {
            "total_users": len(self.users),
            "total_contacts": total_contacts,
            "contacts_by_company": dict(all_companies),
            "contacts_added_this_month": added_this_month,
            "most_searched_contact": most_searched,
            "average_contacts_per_user": round(total_contacts / user_count, 2),
        }

    # -- audit trail -------------------------------------------------
    def get_audit_trail(self, username: Optional[str] = None) -> List[Dict]:
        """Full operation log, optionally filtered to one user."""
        if username is None:
            return list(self.operation_log)
        return [entry for entry in self.operation_log if entry.get("user") == username]

    # -- import / export -------------------------------------------------
    def import_from_csv(self, filepath: str | Path) -> Tuple[bool, str, int]:
        """
        Import contacts from a CSV with headers:
        name,phone,email,company,notes
        Skips rows that would collide with an existing contact.
        """
        username = self._require_login()
        path = Path(filepath)
        if not path.exists():
            return False, f"File not found: {filepath}", 0

        imported = 0
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                phone = (row.get("phone") or "").strip()
                email = (row.get("email") or "").strip()
                if not name or not phone or not email:
                    continue
                ok, _ = self.add_contact(
                    name, phone, email,
                    company=row.get("company", ""), notes=row.get("notes", ""),
                )
                if ok:
                    imported += 1

        self._log("import_csv", username, file=str(path), imported=imported)
        return True, f"Imported {imported} contact(s) from {path.name}.", imported

    def export_to_json(self, filepath: str | Path) -> bool:
        username = self._require_login()
        contacts = self.users[username]["contacts"]
        data = {
            "username": username,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_contacts": len(contacts),
            "contacts": contacts,
        }
        Path(filepath).write_text(json.dumps(data, indent=2))
        self._log("export_json", username, file=str(filepath))
        return True

    def export_to_vcard(self, filepath: str | Path) -> bool:
        """Export the current user's contacts as a single .vcf file."""
        username = self._require_login()
        contacts = self.users[username]["contacts"]

        lines: List[str] = []
        for name, contact in contacts.items():
            lines.append("BEGIN:VCARD")
            lines.append("VERSION:3.0")
            lines.append(f"FN:{name}")
            if contact.get("phone"):
                lines.append(f"TEL:{contact['phone']}")
            if contact.get("email"):
                lines.append(f"EMAIL:{contact['email']}")
            if contact.get("company"):
                lines.append(f"ORG:{contact['company']}")
            if contact.get("notes"):
                lines.append(f"NOTE:{contact['notes']}")
            lines.append("END:VCARD")

        Path(filepath).write_text("\n".join(lines) + "\n")
        self._log("export_vcard", username, file=str(filepath))
        return True

    # -- persistence -------------------------------------------------
    def save(self) -> None:
        data = {
            "users": self.users,
            "operation_log": self.operation_log,
            "search_counts": {f"{u}::{n}": c for (u, n), c in self.search_counts.items()},
        }
        self.data_file.write_text(json.dumps(data, indent=2))

    def _load(self) -> bool:
        if not self.data_file.exists():
            return False
        try:
            data = json.loads(self.data_file.read_text())
        except json.JSONDecodeError:
            return False

        self.users = data.get("users", {})
        self.operation_log = data.get("operation_log", [])
        self.search_counts = defaultdict(int)
        for key, count in data.get("search_counts", {}).items():
            user, name = key.split("::", 1)
            self.search_counts[(user, name)] = count
        return True


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
def run_self_tests() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        data_file = Path(tmp) / "multi_user_contacts.json"
        sys_ = MultiUserContactSystem(data_file=data_file)

        # -- auth --
        ok, _ = sys_.register_user("alice", "hunter2")
        assert ok
        ok, _ = sys_.register_user("alice", "otherpass")
        assert not ok  # duplicate username

        ok, _ = sys_.login("alice", "wrongpass")
        assert not ok
        ok, _ = sys_.login("alice", "hunter2")
        assert ok
        assert sys_.current_user == "alice"

        # calling a contact method while logged out raises
        sys_.logout()
        try:
            sys_.add_contact("X", "1", "x@x.com")
            assert False, "expected PermissionError"
        except PermissionError:
            pass
        sys_.login("alice", "hunter2")

        # -- isolation between users --
        sys_.register_user("bob", "swordfish")
        sys_.add_contact("Shared Name", "111", "alice1@x.com", company="Acme")
        sys_.logout()
        sys_.login("bob", "swordfish")
        sys_.add_contact("Shared Name", "222", "bob1@x.com", company="Beta")
        assert sys_.get_contact("Shared Name")["phone"] == "222"
        sys_.logout()
        sys_.login("alice", "hunter2")
        assert sys_.get_contact("Shared Name")["phone"] == "111"  # unaffected by bob's contact

        # -- CRUD --
        sys_.add_contact("Bob Jones", "555-1234", "bob@acme.com", "Acme")
        sys_.add_contact("Barbara Lane", "555-4321", "barb@beta.com", "Beta")
        assert sys_.list_contacts() == ["Barbara Lane", "Bob Jones", "Shared Name"]

        ok, _ = sys_.update_contact("Bob Jones", company="Acme Corp")
        assert ok and sys_.get_contact("Bob Jones")["company"] == "Acme Corp"

        ok, _ = sys_.delete_contact("Barbara Lane")
        assert ok
        assert "Barbara Lane" not in sys_.list_contacts()

        # -- fuzzy search --
        sys_.add_contact("Jonathan Smith", "555-9999", "jsmith@acme.com", company="Acme")
        fuzzy_hits = sys_.fuzzy_search("Jonathon Smith")  # typo'd query
        assert "Jonathan Smith" in fuzzy_hits

        # -- phone pattern search --
        phone_hits = sys_.search_by_phone_pattern(r"^555-1")
        assert "Bob Jones" in phone_hits

        # -- filter by company / date --
        by_company = sys_.filter_contacts(company="acme")
        assert "Bob Jones" in by_company and "Jonathan Smith" in by_company
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        by_date = sys_.filter_contacts(added_after=today)
        assert "Bob Jones" in by_date

        # -- analytics --
        analytics = sys_.get_analytics()
        assert analytics["total_contacts"] == 3  # Shared Name, Bob Jones, Jonathan Smith
        assert analytics["most_searched_contact"] == "Jonathan Smith"

        global_analytics = sys_.get_global_analytics()
        assert global_analytics["total_users"] == 2
        assert global_analytics["total_contacts"] == 4  # 3 for alice + 1 for bob

        # -- audit trail --
        trail = sys_.get_audit_trail("alice")
        actions = {entry["action"] for entry in trail}
        assert "add_contact" in actions and "login" in actions

        # -- CSV import --
        csv_path = Path(tmp) / "import.csv"
        csv_path.write_text(
            "name,phone,email,company,notes\n"
            "Carla Diaz,555-0001,carla@gamma.com,Gamma,VIP\n"
            "Bob Jones,555-0002,dup@x.com,Dup,should be skipped\n"  # duplicate -> skipped
        )
        ok, _, imported = sys_.import_from_csv(csv_path)
        assert ok and imported == 1
        assert "Carla Diaz" in sys_.list_contacts()

        # -- JSON export --
        json_path = Path(tmp) / "export.json"
        assert sys_.export_to_json(json_path)
        exported = json.loads(json_path.read_text())
        assert exported["username"] == "alice"
        assert exported["total_contacts"] == 4

        # -- vCard export --
        vcf_path = Path(tmp) / "export.vcf"
        assert sys_.export_to_vcard(vcf_path)
        vcf_content = vcf_path.read_text()
        assert "BEGIN:VCARD" in vcf_content and "FN:Bob Jones" in vcf_content

        # -- persistence round-trip --
        sys_.save()
        reloaded = MultiUserContactSystem(data_file=data_file)
        assert "alice" in reloaded.users
        assert len(reloaded.users["alice"]["contacts"]) == 4
        assert reloaded.get_audit_trail("alice")  # log survived the round-trip

    print("All self-tests passed.")


def main() -> None:
    import sys

    if "--test" in sys.argv:
        run_self_tests()
        return

    system = MultiUserContactSystem(data_file="multi_user_contacts_demo.json")

    system.register_user("alice", "hunter2")
    system.register_user("bob", "swordfish")

    system.login("alice", "hunter2")
    system.add_contact("Jonathan Smith", "555-9999", "jsmith@acme.com", "Acme")
    system.add_contact("Barbara Lane", "555-4321", "barb@beta.com", "Beta")
    system.fuzzy_search("Jonathon Smith")  # typo, still finds Jonathan Smith
    system.logout()

    system.login("bob", "swordfish")
    system.add_contact("Carla Diaz", "555-0001", "carla@gamma.com", "Gamma")
    system.logout()

    system.login("alice", "hunter2")
    print("Alice's contacts:", system.list_contacts())
    print("Alice's analytics:", system.get_analytics())
    print("\nGlobal analytics:", system.get_global_analytics())
    print("\nAudit trail (alice):")
    for entry in system.get_audit_trail("alice"):
        print(" ", entry)

    system.save()
    print(f"\nSaved to {system.data_file}")


if __name__ == "__main__":
    main()
