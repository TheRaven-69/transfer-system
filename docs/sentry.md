# Sentry

## Configuration

Configure the API and Celery worker with the same values:

```dotenv
SENTRY_DSN=https://...
SENTRY_ENVIRONMENT=staging
SENTRY_RELEASE=<git-sha-or-image-version>
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.0
SENTRY_EXTRA_SENSITIVE_KEYS=credential,private-key
```

These values are loaded by the optional `SentrySettings` group exposed as
`settings.sentry`.

When `SENTRY_ENVIRONMENT` is omitted, `APP_ENV` is used. When `SENTRY_DSN` is
empty, Sentry is disabled.

`SENTRY_EXTRA_SENSITIVE_KEYS` extends the default filtering list. Values can be
comma-separated or a JSON array.

`/health` transactions are not sampled. Redis span descriptions are filtered
because they may contain cache or idempotency keys.

## Live verification

Run the verification script only against a non-production Sentry environment:

```powershell
$env:ENV_FILE=".env.test"
$env:SENTRY_DSN="https://..."
$env:SENTRY_ENVIRONMENT="staging"
$env:SENTRY_RELEASE="$(git rev-parse HEAD)"
python scripts/verify_sentry.py
```

The script submits one controlled FastAPI error and one controlled Celery task
error. Verify in Sentry that:

- both events have the expected environment and release;
- the API event contains `request.request_id=sentry-api-verification`;
- the Celery event contains `component=celery`, task name, task ID, retries,
  transfer ID, user ID, and the idempotency fingerprint;
- SQLAlchemy and Redis spans appear on real transfer requests;
- Redis span descriptions and raw idempotency keys are filtered.
