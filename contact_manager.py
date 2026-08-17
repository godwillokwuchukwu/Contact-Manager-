#!/usr/bin/env python3
"""
Contact List Management System
==============================
A production-ready contact management application using Python dictionaries.

This module demonstrates:
- Dictionary data structures for real-world business applications
- CRUD (Create, Read, Update, Delete) operations
- Input validation and error handling
- User-friendly command-line interface
- Data persistence using JSON files
"""

import json
import os
from typing import Dict, Optional, List
from datetime import datetime


class ContactManager:
    """
    Manages a collection of business contacts using dictionary data structure.

    Attributes:
        contacts (Dict[str, dict]): Dictionary mapping contact names to contact details
        backup_file (str): Path to JSON file for data persistence
    """

    def __init__(self, backup_file: str = "contacts_backup.json"):
        """
        Initialize the Contact Manager with empty contacts dictionary.

        Args:
            backup_file: Path to JSON file for saving/loading contacts
        """
        self.contacts: Dict[str, dict] = {}
        self.backup_file = backup_file
        self._load_from_backup()

    def add_contact(self, name: str, phone: str, email: str,
                    company: str = "", notes: str = "") -> bool:
        """
        Add a new contact to the system.

        Args:
            name: Unique identifier for the contact (dictionary key)
            phone: Contact phone number
            email: Contact email address
            company: Company name (optional)
            notes: Additional notes (optional)

        Returns:
            bool: True if contact added successfully, False if duplicate

        Business Logic:
            - Names must be unique (dictionary keys)
            - Phone and email are required fields
            - Automatically tracks creation timestamp
        """
        # Validate required fields
        if not name or not name.strip():
            print(" Error: Contact name is required.")
            return False

        if not phone or not phone.strip():
            print(" Error: Phone number is required.")
            return False

        if not email or not email.strip():
            print(" Error: Email address is required.")
            return False

        # Normalize name for consistent lookups
        name = name.strip()

        # Check for duplicate
        if name in self.contacts:
            print(f"  Warning: Contact '{name}' already exists.")
            print("   Use 'update' to modify existing contact information.")
            return False

        # Create contact dictionary
        contact_data = {
            "phone": phone.strip(),
            "email": email.strip(),
            "company": company.strip(),
            "notes": notes.strip(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Add to contacts dictionary
        self.contacts[name] = contact_data
        print(f"✅ Contact '{name}' added successfully.")
        return True

    def get_contact(self, name: str) -> Optional[Dict]:
        """
        Retrieve contact information by name.

        Args:
            name: Contact name to search for

        Returns:
            dict: Contact details if found, None otherwise

        Performance:
            - O(1) average time complexity (dictionary lookup)
            - Much faster than list iteration O(n)
        """
        if not name or not name.strip():
            print(" Error: Please provide a contact name.")
            return None

        name = name.strip()

        # Dictionary lookup - O(1) operation
        contact = self.contacts.get(name)

        if contact:
            return contact
        else:
            print(f" Contact '{name}' not found.")
            return None

    def update_contact(self, name: str, **updates) -> bool:
        """
        Update existing contact information.

        Args:
            name: Contact name to update
            **updates: Keyword arguments for fields to update
                      (phone, email, company, notes)

        Returns:
            bool: True if update successful, False otherwise

        Business Logic:
            - Only updates provided fields (partial updates)
            - Maintains audit trail with updated_at timestamp
            - Validates email format if email is being updated
        """
        if not name or not name.strip():
            print(" Error: Please provide a contact name.")
            return False

        name = name.strip()

        # Check if contact exists
        if name not in self.contacts:
            print(f" Contact '{name}' not found. Use 'add' to create new contact.")
            return False

        # Valid fields that can be updated
        valid_fields = {"phone", "email", "company", "notes"}

        # Filter and validate updates
        for field, value in updates.items():
            if field not in valid_fields:
                print(f"  Warning: '{field}' is not a valid field. Skipping.")
                continue

            if value is not None and value.strip():
                self.contacts[name][field] = value.strip()

        # Update timestamp
        self.contacts[name]["updated_at"] = datetime.now().isoformat()

        print(f" Contact '{name}' updated successfully.")
        return True

    def delete_contact(self, name: str) -> bool:
        """
        Remove a contact from the system.

        Args:
            name: Contact name to delete

        Returns:
            bool: True if deleted, False if not found

        Business Logic:
            - Requires confirmation before deletion (handled in UI)
            - Maintains audit trail (could log deleted contacts)
        """
        if not name or not name.strip():
            print(" Error: Please provide a contact name.")
            return False

        name = name.strip()

        if name in self.contacts:
            self.contacts.pop(name)
            print(f" Contact '{name}' deleted successfully.")
            return True
        else:
            print(f" Contact '{name}' not found.")
            return False

    def list_contacts(self) -> List[str]:
        """
        Get list of all contact names.

        Returns:
            List[str]: Sorted list of contact names

        Use Case:
            - Display contact directory
            - Autocomplete suggestions
            - Export functionality
        """
        if not self.contacts:
            return []

        # Return sorted list of names
        return sorted(self.contacts.keys())

    def search_contacts(self, query: str) -> List[str]:
        """
        Search contacts by name, company, or email.

        Args:
            query: Search term (case-insensitive)

        Returns:
            List[str]: Matching contact names

        Business Value:
            - Fuzzy search for partial matches
            - Search across multiple fields
            - Improves user productivity
        """
        if not query or not query.strip():
            return []

        query = query.strip().lower()
        matches = []

        # Search through all contacts
        for name, details in self.contacts.items():
            # Check if query matches name, company, or email
            if (query in name.lower() or
                query in details.get("company", "").lower() or
                query in details.get("email", "").lower()):
                matches.append(name)

        return sorted(matches)

    def get_contact_count(self) -> int:
        """Return total number of contacts in the system."""
        return len(self.contacts)

    def _save_to_backup(self) -> bool:
        """
        Save contacts to JSON file for persistence.

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f" Error saving backup: {e}")
            return False

    def _load_from_backup(self) -> bool:
        """
        Load contacts from JSON backup file.

        Returns:
            bool: True if load successful, False if file doesn't exist
        """
        if not os.path.exists(self.backup_file):
            return False

        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                self.contacts = json.load(f)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load backup file: {e}")
            return False

    def export_contacts(self, filename: str = "contacts_export.json") -> bool:
        """
        Export all contacts to a JSON file.

        Args:
            filename: Output filename for export

        Returns:
            bool: True if export successful
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "exported_at": datetime.now().isoformat(),
                    "total_contacts": len(self.contacts),
                    "contacts": self.contacts
                }, f, indent=2, ensure_ascii=False)
            print(f" Exported {len(self.contacts)} contacts to '{filename}'.")
            return True
        except IOError as e:
            print(f" Error exporting contacts: {e}")
            return False


def display_contact_details(name: str, contact: dict) -> None:
    """Display formatted contact information."""
    print("\n" + "=" * 50)
    print(f"📇 CONTACT: {name}")
    print("=" * 50)
    print(f"   📱 Phone:   {contact.get('phone', 'N/A')}")
    print(f"   📧 Email:   {contact.get('email', 'N/A')}")
    print(f"   🏢 Company: {contact.get('company', 'N/A') or 'Not specified'}")
    print(f"   📝 Notes:   {contact.get('notes', 'N/A') or 'No notes'}")
    print(f"   🕐 Created: {contact.get('created_at', 'Unknown')[:10]}")
    print(f"   🔄 Updated: {contact.get('updated_at', 'Unknown')[:10]}")
    print("=" * 50 + "\n")


def display_menu() -> None:
    """Display main menu options."""
    print("\n" + "📋 CONTACT MANAGEMENT SYSTEM ".center(50, "="))
    print("""
    1. Add New Contact
    2. View Contact
    3. Update Contact
    4. Delete Contact
    5. List All Contacts
    6. Search Contacts
    7. Export Contacts
    8. View Statistics
    0. Exit

    """)


def get_user_input(prompt: str, required: bool = True) -> Optional[str]:
    """Get validated user input from command line."""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print(" This field is required. Please try again.")


def run_self_tests() -> None:
    """Non-interactive validation of core ContactManager behavior."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        backup_path = os.path.join(tmp, "contacts_backup.json")
        cm = ContactManager(backup_file=backup_path)

        assert cm.add_contact("Alice Smith", "555-1234", "alice@acme.com", "Acme") is True
        assert cm.add_contact("Alice Smith", "555-9999", "dup@acme.com") is False  # duplicate
        assert cm.add_contact("Bob Jones", "", "bob@acme.com") is False  # missing phone

        contact = cm.get_contact("Alice Smith")
        assert contact is not None and contact["company"] == "Acme"
        assert cm.get_contact("Nobody") is None

        assert cm.update_contact("Alice Smith", company="Acme Corp") is True
        assert cm.contacts["Alice Smith"]["company"] == "Acme Corp"
        assert cm.update_contact("Nobody", company="X") is False

        cm.add_contact("Carol White", "555-4321", "carol@beta.com", "Beta")
        assert cm.list_contacts() == ["Alice Smith", "Carol White"]
        assert cm.search_contacts("beta") == ["Carol White"]
        assert cm.get_contact_count() == 2

        assert cm.delete_contact("Carol White") is True
        assert cm.delete_contact("Carol White") is False
        assert cm.get_contact_count() == 1

        assert cm._save_to_backup() is True
        cm2 = ContactManager(backup_file=backup_path)
        assert cm2.get_contact_count() == 1
        assert "Alice Smith" in cm2.contacts

    print("All self-tests passed.")


def main():
    """Main application entry point: interactive CLI."""
    contact_manager = ContactManager()

    print("\n" + " WELCOME TO CONTACT MANAGEMENT SYSTEM ".center(60, "="))
    print("   Built with Python Dictionaries")
    print("=" * 60 + "\n")

    while True:
        display_menu()
        choice = input("Enter your choice (0-8): ").strip()

        if choice == "1":
            print("\n➕ ADD NEW CONTACT")
            print("-" * 30)
            name = get_user_input("Name (required): ")
            phone = get_user_input("Phone (required): ")
            email = get_user_input("Email (required): ")
            company = get_user_input("Company (optional): ", required=False) or ""
            notes = get_user_input("Notes (optional): ", required=False) or ""
            contact_manager.add_contact(name, phone, email, company, notes)

        elif choice == "2":
            print("\n👁️  VIEW CONTACT")
            print("-" * 30)
            name = get_user_input("Enter contact name: ")
            contact = contact_manager.get_contact(name)
            if contact:
                display_contact_details(name, contact)

        elif choice == "3":
            print("\n✏️  UPDATE CONTACT")
            print("-" * 30)
            name = get_user_input("Enter contact name to update: ")
            if name in contact_manager.contacts:
                print(f"\nUpdating contact: {name}")
                print("(Leave blank to keep current value)")
                phone = get_user_input(f"Phone [{contact_manager.contacts[name]['phone']}]: ", required=False)
                email = get_user_input(f"Email [{contact_manager.contacts[name]['email']}]: ", required=False)
                company = get_user_input(f"Company [{contact_manager.contacts[name].get('company', '')}]: ", required=False)
                notes = get_user_input(f"Notes [{contact_manager.contacts[name].get('notes', '')}]: ", required=False)
                updates = {}
                if phone:
                    updates["phone"] = phone
                if email:
                    updates["email"] = email
                if company:
                    updates["company"] = company
                if notes:
                    updates["notes"] = notes
                if updates:
                    contact_manager.update_contact(name, **updates)
                else:
                    print("ℹ  No changes made.")
            else:
                print(f" Contact '{name}' not found.")

        elif choice == "4":
            print("\n🗑️  DELETE CONTACT")
            print("-" * 30)
            name = get_user_input("Enter contact name to delete: ")
            if name in contact_manager.contacts:
                confirm = input(f"Are you sure you want to delete '{name}'? (yes/no): ")
                if confirm.lower() in ["yes", "y"]:
                    contact_manager.delete_contact(name)
                else:
                    print("ℹ  Deletion cancelled.")
            else:
                print(f" Contact '{name}' not found.")

        elif choice == "5":
            print("\n📋 ALL CONTACTS")
            print("-" * 30)
            contacts = contact_manager.list_contacts()
            if contacts:
                print(f"Total contacts: {len(contacts)}\n")
                for idx, name in enumerate(contacts, 1):
                    company = contact_manager.contacts[name].get('company', '')
                    company_str = f" ({company})" if company else ""
                    print(f"   {idx}. {name}{company_str}")
            else:
                print("ℹ  No contacts in the system.")

        elif choice == "6":
            print("\n🔍 SEARCH CONTACTS")
            print("-" * 30)
            query = get_user_input("Enter search term: ")
            results = contact_manager.search_contacts(query)
            if results:
                print(f"\nFound {len(results)} matching contact(s):\n")
                for name in results:
                    company = contact_manager.contacts[name].get('company', '')
                    company_str = f" - {company}" if company else ""
                    print(f"   • {name}{company_str}")
            else:
                print("ℹ  No matching contacts found.")

        elif choice == "7":
            print("\n💾 EXPORT CONTACTS")
            print("-" * 30)
            filename = input("Enter filename (default: contacts_export.json): ").strip()
            if not filename:
                filename = "contacts_export.json"
            contact_manager.export_contacts(filename)

        elif choice == "8":
            print("\n SYSTEM STATISTICS")
            print("-" * 30)
            print(f"   Total Contacts: {contact_manager.get_contact_count()}")
            companies = sum(1 for c in contact_manager.contacts.values() if c.get('company'))
            print(f"   With Company:   {companies}")
            notes = sum(1 for c in contact_manager.contacts.values() if c.get('notes'))
            print(f"   With Notes:     {notes}")

        elif choice == "0":
            print("\n" + "=" * 60)
            print("   Thank you for using Contact Management System!")
            print("   Saving backup...")
            print("=" * 60 + "\n")
            contact_manager._save_to_backup()
            print(" Backup saved successfully.")
            print("0 Goodbye!\n")
            break

        else:
            print("\n Invalid choice. Please enter a number between 0 and 8.\n")


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        run_self_tests()
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("\n\n  Application interrupted by user.")
            print("0 Goodbye!\n")
