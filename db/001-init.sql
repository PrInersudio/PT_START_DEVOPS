select pg_create_physical_replication_slot('replication_slot');

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255)
);
INSERT INTO emails (email) VALUES ('test1@example.net'), ('test2@example.com');

CREATE TABLE phone_numbers (
    id SERIAL PRIMARY KEY,
    number VARCHAR(255)
);
INSERT INTO phone_numbers (number) VALUES ('89175982868'), ('+79001234578');