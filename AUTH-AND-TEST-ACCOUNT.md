# Authentication and Local Demo Account

Authentication uses a unique username and a password hash stored in PostgreSQL. Passwords are never stored in plaintext; the backend uses salted scrypt hashes.

## Local Demo Account

After upgrading the database, create or reset a local demo account from the `backend` directory:

```powershell
python scripts/create_test_account.py
```

This script refuses to run when `ENVIRONMENT=production`.

Demo credentials are intentionally excluded from this document. Do not use demo credentials in a deployed environment.

The login screen does not display demo credentials or prefill the login form.

Existing users receive temporary usernames such as `user_1` during migration `0003_usernames`. New registrations choose a username.

## Office Invitation Code and Registration

- Employee registration uses a unique username and does not require an email address.
- For database compatibility, a non-deliverable `@users.invalid` address is stored; it is not used for sending email.
- The office registration code is configured through the backend `.env` file using `OFFICE_REGISTRATION_CODE`.
- Administrators can view and copy the code from the User Management screen after signing in. Backend authorization restricts this action to administrators.
