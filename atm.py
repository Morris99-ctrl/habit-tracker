"""
╔══════════════════════════════════════════════════════╗
║          AXIOM CAPITAL INVESTMENTS — ATM             ║
║          Full-Featured Terminal Banking App          ║
╚══════════════════════════════════════════════════════╝

Features:
  • Multiple accounts with persistent JSON storage
  • SHA-256 hashed PINs (never stored in plain text)
  • Deposit, Withdraw, Transfer, Balance, Statement
  • PIN change with old-PIN verification
  • Daily withdrawal limit per account
  • Full transaction history with timestamps
  • Input validation — no crashes on bad input
  • Multiple transactions per session (loop-back menu)
  • Graceful logout and exit
"""

import json
import os
import sys
import hashlib
import getpass
from datetime import datetime, date

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────
DATA_FILE            = os.path.join(os.path.dirname(__file__), "atm_accounts.json")
DAILY_WITHDRAW_LIMIT = 5_000   # max withdrawal per calendar day
MAX_PIN_ATTEMPTS     = 3
PIN_LENGTH           = 4

# ─────────────────────────────────────────────────────────────────────────────
#  UI helpers
# ─────────────────────────────────────────────────────────────────────────────
LINE  = "-" * 54
DLINE = "=" * 54

def header(title: str):
    print(f"\n+{DLINE}+")
    print(f"|  {'AXIOM CAPITAL INVESTMENTS':^50}  |")
    print(f"|  {title:^50}  |")
    print(f"+{DLINE}+")

def box(lines: list[str]):
    print(f"+{LINE}+")
    for ln in lines:
        print(f"|  {ln:<50}  |")
    print(f"+{LINE}+")

def fmt_money(amount: float) -> str:
    return f"${amount:>12,.2f}"

def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y  %H:%M")
    except Exception:
        return ts

def get_amount(prompt: str) -> float | None:
    """Ask for a monetary amount; return None if invalid."""
    raw = input(prompt).strip()
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
        return round(amount, 2)
    except ValueError:
        print("  [X] Invalid amount. Please enter a positive number.")
        return None

def get_pin(prompt: str = "  Enter PIN: ") -> str:
    """Read a PIN via standard input so typing is visible and never freezes in any terminal."""
    return input(prompt).strip()

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
#  Account
# ─────────────────────────────────────────────────────────────────────────────
class Account:
    def __init__(
        self,
        account_number: str,
        name: str,
        pin_hash: str,
        balance: float,
        transactions: list | None = None,
        daily_withdrawn: float = 0.0,
        last_withdraw_date: str = "",
    ):
        self.account_number  = account_number
        self.name            = name
        self.pin_hash        = pin_hash
        self.balance         = balance
        self.transactions    = transactions or []
        self.daily_withdrawn = daily_withdrawn
        self.last_withdraw_date = last_withdraw_date

    # ── PIN ───────────────────────────────────────────────────────────────────
    def verify_pin(self, pin: str) -> bool:
        return self.pin_hash == hash_pin(pin)

    def change_pin(self, old_pin: str, new_pin: str) -> tuple[bool, str]:
        if not self.verify_pin(old_pin):
            return False, "Incorrect current PIN."
        if len(new_pin) != PIN_LENGTH or not new_pin.isdigit():
            return False, f"New PIN must be exactly {PIN_LENGTH} digits."
        if new_pin == old_pin:
            return False, "New PIN must differ from current PIN."
        self.pin_hash = hash_pin(new_pin)
        return True, "PIN changed successfully."

    # ── Daily limit tracking ──────────────────────────────────────────────────
    def _reset_daily_if_needed(self):
        today = str(date.today())
        if self.last_withdraw_date != today:
            self.daily_withdrawn    = 0.0
            self.last_withdraw_date = today

    def remaining_daily_limit(self) -> float:
        self._reset_daily_if_needed()
        return max(0.0, DAILY_WITHDRAW_LIMIT - self.daily_withdrawn)

    # ── Transactions ──────────────────────────────────────────────────────────
    def _record(self, kind: str, amount: float, note: str = ""):
        self.transactions.append({
            "type":      kind,
            "amount":    amount,
            "balance":   self.balance,
            "note":      note,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

    def deposit(self, amount: float) -> tuple[bool, str]:
        if amount <= 0:
            return False, "Deposit amount must be positive."
        self.balance = round(self.balance + amount, 2)
        self._record("DEPOSIT", amount)
        return True, f"Deposited {fmt_money(amount)}. New balance: {fmt_money(self.balance)}"

    def withdraw(self, amount: float) -> tuple[bool, str]:
        self._reset_daily_if_needed()
        if amount <= 0:
            return False, "Withdrawal amount must be positive."
        if amount > self.balance:
            return False, (f"Insufficient funds. Available: {fmt_money(self.balance)}")
        if amount > self.remaining_daily_limit():
            return False, (
                f"Daily withdrawal limit reached.\n"
                f"  Remaining today: {fmt_money(self.remaining_daily_limit())}"
            )
        self.balance         = round(self.balance - amount, 2)
        self.daily_withdrawn = round(self.daily_withdrawn + amount, 2)
        self._record("WITHDRAW", amount)
        return True, f"Withdrawn {fmt_money(amount)}. New balance: {fmt_money(self.balance)}"

    def receive(self, amount: float, from_name: str):
        self.balance = round(self.balance + amount, 2)
        self._record("TRANSFER IN", amount, f"From {from_name}")

    def transfer(self, amount: float, target: "Account") -> tuple[bool, str]:
        self._reset_daily_if_needed()
        if amount <= 0:
            return False, "Transfer amount must be positive."
        if amount > self.balance:
            return False, f"Insufficient funds. Available: {fmt_money(self.balance)}"
        if amount > self.remaining_daily_limit():
            return False, (
                f"Daily limit reached. Remaining today: {fmt_money(self.remaining_daily_limit())}"
            )
        self.balance         = round(self.balance - amount, 2)
        self.daily_withdrawn = round(self.daily_withdrawn + amount, 2)
        self._record("TRANSFER OUT", amount, f"To {target.name} ({target.account_number})")
        target.receive(amount, f"{self.name} ({self.account_number})")
        return True, (
            f"Transferred {fmt_money(amount)} to {target.name}.\n"
            f"  Your new balance: {fmt_money(self.balance)}"
        )

    def mini_statement(self, n: int = 10) -> list[dict]:
        return self.transactions[-n:]

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "account_number":    self.account_number,
            "name":              self.name,
            "pin_hash":          self.pin_hash,
            "balance":           self.balance,
            "transactions":      self.transactions,
            "daily_withdrawn":   self.daily_withdrawn,
            "last_withdraw_date":self.last_withdraw_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        return cls(
            account_number    = d["account_number"],
            name              = d["name"],
            pin_hash          = d["pin_hash"],
            balance           = d["balance"],
            transactions      = d.get("transactions", []),
            daily_withdrawn   = d.get("daily_withdrawn", 0.0),
            last_withdraw_date= d.get("last_withdraw_date", ""),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Bank  (multi-account data layer)
# ─────────────────────────────────────────────────────────────────────────────
class Bank:
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self._load()

    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    raw = json.load(f)
                for d in raw:
                    acc = Account.from_dict(d)
                    self.accounts[acc.account_number] = acc
                return
            except Exception:
                print("  [!] Data file corrupted. Starting fresh.")
        # Seed demo accounts if no data file exists
        self._seed_demo_accounts()
        self.save()

    def _seed_demo_accounts(self):
        demos = [
            ("1001", "Alex Johnson",  "1234", 5_000.00),
            ("1002", "Maria Santos",  "5678", 12_500.00),
            ("1003", "David Kimani",  "9999", 350.00),
        ]
        for acc_no, name, pin, bal in demos:
            acc = Account(acc_no, name, hash_pin(pin), bal)
            acc._record("OPENING BALANCE", bal, "Account opened")
            self.accounts[acc_no] = acc

    def save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump([a.to_dict() for a in self.accounts.values()], f, indent=2)
        except Exception as e:
            print(f"  [!] Could not save data: {e}")

    def get(self, account_number: str) -> Account | None:
        return self.accounts.get(account_number)

    def create_account(self, name: str, pin: str, initial_deposit: float = 0.0) -> Account:
        # Generate next available 4-digit account number
        existing = [int(k) for k in self.accounts.keys() if k.isdigit()]
        next_num = str(max(existing, default=1000) + 1)
        acc = Account(next_num, name, hash_pin(pin), initial_deposit)
        acc._record("OPENING BALANCE", initial_deposit, "Account opened")
        self.accounts[next_num] = acc
        self.save()
        return acc


# ─────────────────────────────────────────────────────────────────────────────
#  ATM  (user-interaction layer)
# ─────────────────────────────────────────────────────────────────────────────
MENU = {
    "1": "Check Balance",
    "2": "Deposit",
    "3": "Withdraw",
    "4": "Transfer / Send Money",
    "5": "Mini Statement",
    "6": "Change PIN",
    "7": "Logout",
}

class ATM:
    def __init__(self, bank: Bank):
        self.bank    = bank
        self.account: Account | None = None

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        header("Welcome")
        print(f"\n  {'Axiom Capital Investments':^52}")
        print(f"  {'Your No.1 Choice':^52}\n")

        while True:
            self.account = None
            if not self._login():
                break
            self._session()
            self.bank.save()
            print("\n  Thank you for banking with Axiom Capital!\n")

    # ── Login ─────────────────────────────────────────────────────────────────
    def _login(self) -> bool:
        header("Card Login")
        print("\n  Available Accounts (Select one to test):")
        print(f"  +{'-'*12}+{'-'*20}+{'-'*12}+")
        print(f"  | {'Acc No':<10} | {'Account Holder':<18} | {'Demo PIN':<10} |")
        print(f"  +{'-'*12}+{'-'*20}+{'-'*12}+")
        demo_pins = {"1001": "1234", "1002": "5678", "1003": "9999"}
        for acc in self.bank.accounts.values():
            p = demo_pins.get(acc.account_number, "(custom)")
            print(f"  | {acc.account_number:<10} | {acc.name:<18} | {p:<10} |")
        print(f"  +{'-'*12}+{'-'*20}+{'-'*12}+")
        print("  Commands: Type Account Number | 'new' to register | 'quit' to exit")

        acc_no = input("\n  Enter Account Number: ").strip()
        if acc_no.lower() in ("quit", "q", "exit"):
            print("\n  Goodbye!\n")
            return False

        if acc_no.lower() in ("new", "register", "open"):
            self._create_account()
            return True

        account = self.bank.get(acc_no)
        if not account:
            print(f"\n  [X] Account '{acc_no}' not found.\n")
            return True   # allow retry from outer loop

        for attempt in range(1, MAX_PIN_ATTEMPTS + 1):
            pin = get_pin(f"  Enter PIN [{attempt}/{MAX_PIN_ATTEMPTS}]: ")
            if account.verify_pin(pin):
                self.account = account
                print(f"\n  [OK] Welcome back, {account.name}!\n")
                return True
            remaining = MAX_PIN_ATTEMPTS - attempt
            if remaining:
                print(f"  [X] Wrong PIN. {remaining} attempt(s) remaining.")
            else:
                print(
                    "\n  [LOCKED] Card locked after 3 failed attempts.\n"
                    "           Please visit an Axiom Capital branch to unlock.\n"
                )
        return True   # locked but don't quit the outer ATM loop

    def _create_account(self):
        header("Open New Account")
        name = input("\n  Enter your full name: ").strip()
        if not name:
            print("  [X] Name cannot be empty.")
            return

        pin = get_pin("  Choose a 4-digit PIN: ")
        if len(pin) != PIN_LENGTH or not pin.isdigit():
            print(f"  [X] PIN must be exactly {PIN_LENGTH} digits.")
            return

        confirm = get_pin("  Confirm 4-digit PIN: ")
        if pin != confirm:
            print("  [X] PINs do not match. Registration cancelled.")
            return

        dep = get_amount("  Initial deposit amount (optional, $0 to skip): $")
        initial_deposit = dep if dep is not None else 0.0

        new_acc = self.bank.create_account(name, pin, initial_deposit)
        print(f"\n  [SUCCESS] Account successfully created!")
        print(f"  +{'-'*40}+")
        print(f"  | Your Account Number : {new_acc.account_number:<18} |")
        print(f"  | Account Holder      : {new_acc.name:<18} |")
        print(f"  | Starting Balance    : {fmt_money(new_acc.balance):<18} |")
        print(f"  +{'-'*40}+")
        print("  Please remember your Account Number and PIN to log in.\n")

    # ── Session menu loop ─────────────────────────────────────────────────────
    def _session(self):
        while True:
            self._show_menu()
            choice = input("  Select option: ").strip()
            print()

            if choice == "1":
                self._check_balance()
            elif choice == "2":
                self._deposit()
            elif choice == "3":
                self._withdraw()
            elif choice == "4":
                self._transfer()
            elif choice == "5":
                self._mini_statement()
            elif choice == "6":
                self._change_pin()
            elif choice == "7":
                print("  [OK] Logged out successfully.")
                break
            else:
                print("  [X] Invalid option. Please choose 1-7.")

            input("\n  Press Enter to continue...")

    def _show_menu(self):
        header(f"Account: {self.account.account_number}  |  {self.account.name}")
        print()
        for num, label in MENU.items():
            print(f"    [{num}]  {label}")
        print()

    # ── Operations ────────────────────────────────────────────────────────────
    def _check_balance(self):
        acc = self.account
        acc._reset_daily_if_needed()
        box([
            f"Account Holder : {acc.name}",
            f"Account Number : {acc.account_number}",
            LINE[:52],
            f"Available Balance  : {fmt_money(acc.balance)}",
            f"Daily Withdraw Used: {fmt_money(acc.daily_withdrawn)}",
            f"Daily Withdraw Left: {fmt_money(acc.remaining_daily_limit())}",
        ])

    def _deposit(self):
        print("  -- Deposit --------------------------------------")
        amount = get_amount("  Amount to deposit: $")
        if amount is None:
            return
        pin = get_pin()
        if not self.account.verify_pin(pin):
            print("  [X] Wrong PIN. Transaction cancelled.")
            return
        ok, msg = self.account.deposit(amount)
        print(f"\n  {'[OK]' if ok else '[X]'}  {msg}")

    def _withdraw(self):
        print("  -- Withdraw -------------------------------------")
        self.account._reset_daily_if_needed()
        print(f"  Available balance   : {fmt_money(self.account.balance)}")
        print(f"  Remaining daily limit: {fmt_money(self.account.remaining_daily_limit())}")
        amount = get_amount("  Amount to withdraw: $")
        if amount is None:
            return
        pin = get_pin()
        if not self.account.verify_pin(pin):
            print("  [X] Wrong PIN. Transaction cancelled.")
            return
        ok, msg = self.account.withdraw(amount)
        print(f"\n  {'[OK]' if ok else '[X]'}  {msg}")

    def _transfer(self):
        print("  -- Transfer / Send Money ------------------------")
        target_no = input("  Recipient account number: ").strip()
        if target_no == self.account.account_number:
            print("  [X] You cannot transfer to your own account.")
            return
        target = self.bank.get(target_no)
        if not target:
            print(f"  [X] Account '{target_no}' not found.")
            return
        print(f"  Recipient: {target.name}")
        amount = get_amount("  Amount to transfer: $")
        if amount is None:
            return
        pin = get_pin()
        if not self.account.verify_pin(pin):
            print("  [X] Wrong PIN. Transaction cancelled.")
            return
        ok, msg = self.account.transfer(amount, target)
        print(f"\n  {'[OK]' if ok else '[X]'}  {msg}")

    def _mini_statement(self):
        txns = self.account.mini_statement(10)
        header("Mini Statement - Last 10 Transactions")
        if not txns:
            print("  No transactions found.\n")
            return
        print(f"\n  {'Date & Time':<20} {'Type':<14} {'Amount':>12}  {'Balance':>12}")
        print(f"  {LINE}")
        for t in reversed(txns):
            sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER IN", "OPENING BALANCE") else "-"
            note = f"  ({t['note']})" if t.get("note") else ""
            print(
                f"  {fmt_ts(t['timestamp']):<20} "
                f"{t['type']:<14} "
                f"{sign}{fmt_money(t['amount']).strip():>12}  "
                f"{fmt_money(t['balance']).strip():>12}"
                f"{note}"
            )
        print()

    def _change_pin(self):
        print("  -- Change PIN -----------------------------------")
        old_pin = get_pin("  Current PIN: ")
        new_pin = get_pin("  New PIN (4 digits): ")
        confirm = get_pin("  Confirm New PIN: ")
        if new_pin != confirm:
            print("  [X] PINs do not match. Change cancelled.")
            return
        ok, msg = self.account.change_pin(old_pin, new_pin)
        print(f"\n  {'[OK]' if ok else '[X]'}  {msg}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bank = Bank()
    ATM(bank).run()
