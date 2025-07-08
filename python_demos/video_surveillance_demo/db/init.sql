CREATE TABLE IF NOT EXISTS alerts
(
    id          SERIAL PRIMARY KEY,
    camera_id   INTEGER,
    "timestamp" BIGINT,
    "message"   CHARACTER VARYING,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
