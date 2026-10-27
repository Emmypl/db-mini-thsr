CREATE TABLE users (
    user_id VARCHAR(20) PRIMARY KEY,
    name    VARCHAR(50) NOT NULL CHECK (btrim(name) <> ''),
    phone   VARCHAR(20)
);
