-- upgrade

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500),
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS important_links (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    url VARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL
);

-- rollback

DROP TABLE important_links;
DROP TABLE groups;
