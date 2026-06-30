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

INSERT INTO tags (id, name, created_at) VALUES (1, 'Mates', CURRENT_TIMESTAMP)

INSERT INTO tags (id, name, created_at) VALUES (2, 'Comp', CURRENT_TIMESTAMP)

INSERT INTO tags (id, name, created_at) VALUES (3, 'Ingeniería', CURRENT_TIMESTAMP)

INSERT INTO tags (id, name, created_at) VALUES (4, 'Ocio', CURRENT_TIMESTAMP)

INSERT INTO tags (id, name, created_at) VALUES (5, 'Social', CURRENT_TIMESTAMP)

-- rollback

DROP TABLE group_tags
DROP TABLE tags
