CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    camera_id INTEGER,
    timestamp BIGINT,
    message TEXT,
    image BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traffic_logs (
    id SERIAL PRIMARY KEY,
    camera_id INTEGER,
    timestamp BIGINT,
    counts JSONB,
    avg_speed REAL,
    status TEXT,
    anomaly TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);