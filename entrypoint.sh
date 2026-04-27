#!/bin/sh
set -e

# Run migrations
dbwarden migrate --verbose

# Start application
exec uvicorn main:app --host 0.0.0.0 --port 8080 --root-path "${ROOT_PATH:-/fingcomms}"
