-- dbwarden v0.3.3.1
-- Migration: Initial schema
-- Database: postgresql
-- Direction: forward

BEGIN;

CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500),
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE important_links (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMIT;
