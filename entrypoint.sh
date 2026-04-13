#!/bin/sh
set -e

# Generate warden.toml at runtime (TOML doesn't support env vars)
if [ "$ENVIRONMENT" = "PROD" ]; then
    DB_TYPE="postgresql"
    DB_URL="$DATABASE_URL"
else
    DB_TYPE="sqlite"
    DB_URL="${DATABASE_URL:-sqlite:///./groups.db}"
fi

cat > warden.toml <<EOF
default = "main"

[database]
[database.main]
database_type = "${DB_TYPE}"
sqlalchemy_url = "${DB_URL}"
migrations_dir = "migrations"
EOF

# Run migrations
dbwarden migrate --verbose

# Start application
exec uvicorn main:app --host 0.0.0.0 --port 8080 --root-path "${ROOT_PATH:-/fingcomms}"
