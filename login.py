"""
=============================================================
             AUTH SYSTEM — REGISTRATION & SIGN IN
=============================================================
Features:
  - Sign Up (Registration) with full input validation
  - Sign In (Login) by Username or Email with masked password
  - Password Reset with Phone OTP verification
  - 18+ Age verification from Date of Birth (YYYY-MM-DD)
  - Diversified email domain check + banned disposable domains block
  - Strict password rules + confirmation + Salted SHA-256 hashing
  - Robust OTP generation & verification (preserves leading zeroes)
  - Terms & Conditions agreement acceptance
  - Persistent storage in users.json
  - Visual loading animations and error handling (no unhandled crashes)
=============================================================
"""

import os
import sys
import json
import time
import re
import secrets
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

# Optional loading bar import
try:
    import loading_bar
except ImportError:
    loading_bar = None

# -------------------------------------------------------------
# Configuration & Constants
# -------------------------------------------------------------
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
MINIMUM_AGE = 18
OTP_EXPIRY_SECONDS = 120
MAX_OTP_ATTEMPTS = 3

# Common disposable/temporary email domains to reject
BANNED_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "throwawaymail.com", "trashmail.com", "yopmail.com", "sharklasers.com",
    "fakeinbox.com", "dispostable.com", "getairmail.com", "maildrop.cc",
    "inboxkitten.com", "temp-mail.org", "burnermail.io", "crazymailing.com",
    "mytemp.email", "mohmal.com", "fakemailgenerator.com"
}

# -------------------------------------------------------------
# UI Helpers
# -------------------------------------------------------------
LINE = "-" * 56
DLINE = "=" * 56


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner(title: str):
    print(f"\n{DLINE}")
    print(f"| {title.center(52)} |")
    print(f"{DLINE}")


def play_loading(msg="Processing", steps=5, delay=0.15):
    """Triggers the loading animation if available, else a brief pause."""
    if loading_bar and hasattr(loading_bar, "show_loading"):
        try:
            loading_bar.show_loading(message=msg, num_steps=steps, delay=delay)
            return
        except Exception:
            pass
    print(f"\t{msg}...")
    time.sleep(1.0)


def prompt_masked_password(prompt_text="Enter password: ") -> str:
    """Prompt for password using getpass, with clean fallback if needed."""
    """
    Prompt for password displaying asterisks (*) as characters are typed on Windows,
    giving instant visual feedback so the terminal never feels frozen or locked.
    Falls back gracefully to standard input if console hooks are unavailable.
    """
    sys.stdout.write(prompt_text)
    sys.stdout.flush()

    if os.name == "nt":
        try:
            import msvcrt
            chars = []
            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                elif ch == "\x08":  # Backspace
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":  # Ctrl+C
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    raise KeyboardInterrupt
                elif ch in ("\x00", "\xe0"):  # Special keys (arrows, F-keys)
                    msvcrt.getwch()  # Consume prefix code
                else:
                    chars.append(ch)
                    sys.stdout.write("*")
                    sys.stdout.flush()
            return "".join(chars)
        except Exception:
            pass

    try:
        pwd = getpass.getpass(prompt_text)
        return getpass.getpass("").strip()
    except Exception:
        pwd = input(prompt_text)
    return pwd
    return input().strip()



# -------------------------------------------------------------
# Storage & Security Helpers
# -------------------------------------------------------------
def load_users() -> dict:
    """Load users from the JSON database file."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_users(users: dict):
    """Save users to the JSON database file."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hashes a password with a unique salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    salted = f"{salt}{password}".encode("utf-8")
    pwd_hash = hashlib.sha256(salted).hexdigest()
    return pwd_hash, salt


def verify_password(stored_hash: str, salt: str, password_attempt: str) -> bool:
    """Verifies a password against the stored salted hash."""
    attempt_hash, _ = hash_password(password_attempt, salt)
    return secrets.compare_digest(stored_hash, attempt_hash)


# -------------------------------------------------------------
# Validators
# -------------------------------------------------------------
def validate_email(email: str, existing_users: dict) -> tuple[bool, str]:
    """Validates email format, domain validity, and uniqueness."""
    email = email.strip().lower()
    pattern = r"^[\w\.-]+@([\w\.-]+\.[a-zA-Z]{2,})$"
    match = re.match(pattern, email)

    if not match:
        return False, "Invalid email address format (e.g., name@example.com)."

    domain = match.group(1).lower()
    if domain in BANNED_EMAIL_DOMAINS:
        return False, f"Disposable email provider '@{domain}' is banned. Please use a trusted provider."

    # Check for duplicate email
    for user_info in existing_users.values():
        if user_info.get("email", "").lower() == email:
            return False, "An account with this email already exists."

    return True, ""


def validate_password_rules(password: str) -> list[str]:
    """Checks password complexity requirements."""
    errors = []
    if len(password) < 8:
        errors.append("• Must contain at least 8 characters.")
    if not re.search(r"[a-z]", password):
        errors.append("• Must contain at least one lowercase letter (a-z).")
    if not re.search(r"[A-Z]", password):
        errors.append("• Must contain at least one uppercase letter (A-Z).")
    if not re.search(r"\d", password):
        errors.append("• Must contain at least one number (0-9).")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("• Must contain at least one special character (!@#$%^&* etc.).")
    if " " in password:
        errors.append("• Must not contain any spaces.")
    return errors


def validate_username(username: str, existing_users: dict) -> tuple[bool, str]:
    """Checks username length, allowed characters, and uniqueness."""
    username = username.strip().lower()
    if len(username) < 4:
        return False, "Username must be at least 4 characters."
    if len(username) > 10:
        return False, "Username cannot exceed 10 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores (_)."
    if username in existing_users:
        return False, f"Username '{username}' is already taken. Please choose another."
    return True, ""


def calculate_age(dob: date) -> int:
    """Calculates exact age from date of birth."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# -------------------------------------------------------------
# Input Prompts with Retry Loops
# -------------------------------------------------------------
def prompt_email(existing_users: dict) -> str:
    while True:
        email = input("\nEnter your Email address: ").strip()
        if not email:
            print("❌ Email cannot be empty.")
            continue
        is_valid, err_msg = validate_email(email, existing_users)
        if is_valid:
            print("Verifying email...")
            time.sleep(0.5)
            print("✅ Email is valid.")
            return email.lower()
        else:
            print(f"❌ {err_msg}")


def prompt_password() -> str:
    while True:
        print("\nPassword requirements:")
        print(" - At least 8 characters")
        print(" - Must include uppercase, lowercase, number, and special character")
        print(" - No spaces")
        pwd = prompt_masked_password("\nCreate your password: ")
        issues = validate_password_rules(pwd)
        if issues:
            print("\n❌ Password does not meet security rules:")
            for issue in issues:
                print(f"  {issue}")
            print("Please try again.\n")
            continue

        confirm_pwd = prompt_masked_password("Confirm your password: ")
        if pwd != confirm_pwd:
            print("❌ Passwords do not match! Please try again.\n")
            continue

        print("✅ Strong password verified and confirmed!")
        return pwd


def prompt_username(existing_users: dict) -> str:
    while True:
        user_name = input("\nEnter your desired Username (4-10 chars): ").strip()
        is_valid, err_msg = validate_username(user_name, existing_users)
        if is_valid:
            time.sleep(0.4)
            print(f"✅ Username '{user_name.lower()}' is available!")
            return user_name.lower()
        else:
            print(f"❌ {err_msg}")


def prompt_dob() -> tuple[str, int]:
    while True:
        dob_str = input("\nEnter your Date of Birth (YYYY-MM-DD): ").strip()
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2002-05-18).")
            continue

        today = date.today()
        if dob >= today:
            print("❌ Date of birth cannot be today or in the future.")
            continue

        age = calculate_age(dob)
        if age < MINIMUM_AGE:
            print(f"❌ You are {age} years old. You must be at least {MINIMUM_AGE} years old to register.")
            retry = input("Would you like to re-enter your DOB? (y/n): ").strip().lower()
            if retry != 'y':
                return None, age
            continue

        print(f"✅ Age verified: {age} years old (Eligible 18+).")
        return dob.strftime("%Y-%m-%d"), age


def prompt_phone(existing_users: dict) -> str:
    while True:
        phone_input = input("\nEnter your phone number: +254 ").strip()
        # Remove any stray spaces or dashes
        cleaned = phone_input.replace(" ", "").replace("-", "")

        # If user typed leading 0, adjust
        if cleaned.startswith("0") and len(cleaned) == 10:
            cleaned = cleaned[1:]

        if not cleaned.isdigit():
            print("❌ Phone number must contain digits only.")
            continue

        if len(cleaned) != 9:
            print(f"❌ Expected 9 digits after +254 (e.g. 712345678). You entered {len(cleaned)} digits.")
            continue

        full_phone = f"+254{cleaned}"

        # Check uniqueness
        duplicate = any(u.get("phone") == full_phone for u in existing_users.values())
        if duplicate:
            print("❌ This phone number is already linked to another account.")
            continue

        print("\tVerifying phone number format...")
        time.sleep(0.5)
        print(f"✅ Phone number verified: {full_phone}")
        return full_phone


def verify_phone_otp(phone_number: str) -> bool:
    """Simulates sending a 6-digit zero-padded OTP and verifying user input."""
    max_attempts = MAX_OTP_ATTEMPTS

    while max_attempts > 0:
        # Generates a secure 6-digit OTP string with preserved leading zeroes
        secret_otp = f"{secrets.randbelow(1_000_000):06d}"
        expiry_time = time.time() + OTP_EXPIRY_SECONDS

        print(f"\n📱 Sending 6-digit OTP to {phone_number}...")
        time.sleep(1.0)
        print(f"┌{'─' * 38}┐")
        print(f"│  [SMS SIMULATION] Your OTP is: {secret_otp}  │")
        print(f"│  (Valid for {OTP_EXPIRY_SECONDS} seconds)                 │")
        print(f"└{'─' * 38}┘")

        while max_attempts > 0:
            user_input = input("\nEnter the 6-digit OTP code received (or 'R' to resend): ").strip()

            if user_input.upper() == 'R':
                print("🔄 Requesting new OTP...")
                break

            if time.time() > expiry_time:
                print("⏱️  OTP has expired! A fresh code is being generated...")
                max_attempts -= 1
                break

            if user_input == secret_otp:
                play_loading("Verifying OTP code", steps=4, delay=0.15)
                print("\n✅ Phone number verification successful!")
                return True
            else:
                max_attempts -= 1
                if max_attempts > 0:
                    print(f"❌ Incorrect OTP. {max_attempts} attempt(s) remaining.")
                else:
                    print("❌ Maximum OTP attempts exceeded.")
                    return False

    return False


def prompt_terms_and_conditions() -> bool:
    print("\n" + LINE)
    print("           TERMS AND CONDITIONS AGREEMENT")
    print(LINE)
    print("1. You agree to use this platform responsibly and legally.")
    print("2. Your account credentials must be kept confidential.")
    print("3. Multiple false login attempts may result in temporary lockout.")
    print("4. You confirm that all submitted details are true and accurate.")
    print(LINE)

    while True:
        agreement = input("\nDo you agree to the Terms & Conditions? (yes/no): ").strip().lower()
        if agreement in ("yes", "y"):
            print("✅ Terms accepted.")
            return True
        elif agreement in ("no", "n"):
            print("❌ You must accept the terms and conditions to create an account.")
            return False
        else:
            print("Please enter 'yes' or 'no'.")


# -------------------------------------------------------------
# Core Flows: Sign Up, Sign In, Forgot Password
# -------------------------------------------------------------
def sign_up():
    print_banner("USER REGISTRATION (SIGN UP)")
    existing_users = load_users()

    # 1. Email
    email = prompt_email(existing_users)

    # 2. Password with complexity check & confirmation
    password = prompt_password()

    # 3. Username
    username = prompt_username(existing_users)

    # 4. Date of Birth & Age check (18+)
    dob_str, age = prompt_dob()
    if dob_str is None:
        print("\nRegistration cancelled due to age requirements.")
        return

    # 5. Phone Number
    phone_number = prompt_phone(existing_users)

    # 6. OTP Verification
    otp_success = verify_phone_otp(phone_number)
    if not otp_success:
        print("\n❌ Phone verification failed. Registration aborted.")
        return

    # 7. Terms & Conditions
    if not prompt_terms_and_conditions():
        print("\nRegistration cancelled.")
        return

    # 8. Save user securely
    pwd_hash, salt = hash_password(password)
    new_user = {
        "username": username,
        "email": email,
        "password_hash": pwd_hash,
        "salt": salt,
        "dob": dob_str,
        "age": age,
        "phone": phone_number,
        "created_at": datetime.now().isoformat()
    }

    existing_users[username] = new_user
    play_loading("Creating account and encrypting credentials", steps=6, delay=0.15)
    save_users(existing_users)

    print("\n" + DLINE)
    print(f"🎉 Welcome aboard, @{username}! Your account has been created.")
    print(f"   Registered Email: {email}")
    print(f"   Registered Phone: {phone_number}")
    print(DLINE)


def sign_in():
    print_banner("USER LOGIN (SIGN IN)")
    existing_users = load_users()

    if not existing_users:
        print("\nℹ️  No registered users found. Please Sign Up first!")
        return

    identifier = input("\nEnter your Username or Email: ").strip().lower()
    pwd_attempt = prompt_masked_password("Enter your Password: ")

    # Find user by username or email
    target_user = None
    for username, data in existing_users.items():
        if username == identifier or data.get("email", "").lower() == identifier:
            target_user = data
            break

    play_loading("Authenticating credentials", steps=5, delay=0.12)

    if not target_user:
        print("\n❌ Invalid username/email or password.")
        return

    # Verify password hash
    if verify_password(target_user["password_hash"], target_user["salt"], pwd_attempt):
        print("\n" + DLINE)
        print(f"✅ LOGIN SUCCESSFUL! Welcome back, {target_user['username']}!")
        print(DLINE)
        print(f" • Username:     @{target_user['username']}")
        print(f" • Email:        {target_user['email']}")
        print(f" • Phone:        {target_user['phone']}")
        print(f" • Age:          {target_user['age']} years old")
        print(f" • Member Since: {target_user.get('created_at', 'N/A')[:10]}")
        print(DLINE)
    else:
        print("\n❌ Invalid username/email or password. Please try again.")


def forgot_password():
    print_banner("PASSWORD RESET (FORGOT PASSWORD)")
    existing_users = load_users()

    if not existing_users:
        print("\nℹ️  No accounts exist yet. Please register first.")
        return

    identifier = input("\nEnter your registered Username or Email: ").strip().lower()

    target_user = None
    username_key = None
    for u_name, data in existing_users.items():
        if u_name == identifier or data.get("email", "").lower() == identifier:
            target_user = data
            username_key = u_name
            break

    if not target_user:
        print("❌ No account found with that identifier.")
        return

    registered_phone = target_user.get("phone", "")
    print(f"\nFound account for @{username_key}.")
    print(f"A verification OTP will be sent to linked phone: {registered_phone[:6]}***{registered_phone[-2:]}")

    confirm = input("Proceed with sending reset OTP? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Password reset cancelled.")
        return

    if verify_phone_otp(registered_phone):
        print("\nSet your new password:")
        new_pwd = prompt_password()
        new_hash, new_salt = hash_password(new_pwd)

        target_user["password_hash"] = new_hash
        target_user["salt"] = new_salt
        existing_users[username_key] = target_user

        play_loading("Updating encrypted password", steps=5, delay=0.15)
        save_users(existing_users)
        print("\n✅ Password reset successful! You can now log in with your new password.")
    else:
        print("\n❌ Verification failed. Password reset aborted.")


# -------------------------------------------------------------
# Main Application Menu Loop
# -------------------------------------------------------------
def main():
    while True:
        print_banner("WELCOME TO THE AUTHENTICATION PORTAL")
        print(" [1] 🔐 Sign In (Log In)")
        print(" [2] 📝 Sign Up (Create New Account)")
        print(" [3] 🔑 Forgot Password (Reset via OTP)")
        print(" [4] 🚪 Exit")
        print(LINE)

        choice = input("Select an option (1-4): ").strip()

        if choice == "1":
            sign_in()
        elif choice == "2":
            sign_up()
        elif choice == "3":
            forgot_password()
        elif choice == "4":
            print("\nThank you for visiting! Goodbye.\n")
            break
        else:
            print("❌ Invalid selection. Please enter a number between 1 and 4.")

        input("\nPress [Enter] to return to the main menu...")
        clear_screen()


if __name__ == "__main__":
    main()
