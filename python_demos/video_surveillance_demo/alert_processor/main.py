import json
import logging
import os
import time

import psycopg2
import redis

QUEUE_NAME = "alerts_queue"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


def process_messages():
    redis_client = get_redis_client()
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    while True:
        try:
            _, message = redis_client.blpop(QUEUE_NAME)
            data = json.loads(message)
            camera_id = data.get("camera_id")
            cur.execute(
                "INSERT INTO alerts (camera_id, message) VALUES (%s, %s)",
                (camera_id, message),
            )
            logger.info(f"Stored alert from camera {camera_id}")
        except Exception as exc:
            logger.error(f"Error processing message: {exc}")
            time.sleep(1)


def main():
    process_messages()


if __name__ == "__main__":
    main()
