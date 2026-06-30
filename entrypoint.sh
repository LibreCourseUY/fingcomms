#!/bin/sh
set -e

# Run migrations
export DBWARDEN_CONFIG_MODULE=database
dbwarden migrate --verbose

# Start application
exec uvicorn main:app --host 0.0.0.0 --port 8080
