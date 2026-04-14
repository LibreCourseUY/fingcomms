-- upgrade

CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500),
    pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
)

CREATE TABLE IF NOT EXISTS important_links (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP
)

-- rollback

DROP TABLE important_links

DROP TABLE groups
