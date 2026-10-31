CREATE TABLE users (
    user_id VARCHAR(20) PRIMARY KEY,
    name    VARCHAR(50) NOT NULL CHECK (btrim(name) <> ''),
    phone   VARCHAR(20)
);

-- TODO: add stations table --
CREATE TABLE stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       VARCHAR(50) NOT NULL,
    seq        INT NOT NULL UNIQUE
    
);