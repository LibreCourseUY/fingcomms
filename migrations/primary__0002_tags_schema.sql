-- upgrade

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP
)

CREATE TABLE IF NOT EXISTS group_tags (
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, tag_id)
)

INSERT INTO tags (name, created_at) VALUES ('Mates', CURRENT_TIMESTAMP)
INSERT INTO tags (name, created_at) VALUES ('Comp', CURRENT_TIMESTAMP)
INSERT INTO tags (name, created_at) VALUES ('Ingeniería', CURRENT_TIMESTAMP)
INSERT INTO tags (name, created_at) VALUES ('Ocio', CURRENT_TIMESTAMP)
INSERT INTO tags (name, created_at) VALUES ('Social', CURRENT_TIMESTAMP)

-- rollback

DROP TABLE group_tags
DROP TABLE tags
