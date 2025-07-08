import json
import logging
import os
import time
from urllib.parse import urlparse

import psycopg2
import redis_utils
import s3_utils

QUEUE_NAME = "alerts_queue"
EXPIRY_TIME_MILLISECONDS = 2000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    parse_result = urlparse(
        os.getenv(
            "POSTGRES_URL", "postgresql://postgres:password@postgres:5432/postgres"
        )
    )
    return psycopg2.connect(
        user=parse_result.username,
        password=parse_result.password,
        host=parse_result.hostname,
        port=parse_result.port,
        dbname=parse_result.path[1:],
    )


def write_to_db(conn, cur, camera_id, timestamp, message):
    cur.execute(
        "INSERT INTO alerts (camera_id, timestamp, message) VALUES (%s, %s, %s)",
        (camera_id, timestamp, message),
    )
    logger.info(
        f"Stored alert message from camera {camera_id} at timestamp {timestamp}"
    )
    conn.commit()


def process_messages():
    redis_client = redis_utils.get_redis_client()
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    while True:
        try:
            _, message = redis_client.blpop(QUEUE_NAME)

            data = json.loads(message)
            camera_id = data.get("camera_id")
            timestamp = data.get("timestamp")

            # Discard old messages
            if timestamp < time.time() * 1000 - EXPIRY_TIME_MILLISECONDS:
                continue

            text = "Hello"
            image_data = redis_utils.get_camera_frame(camera_id, timestamp)
            if image_data:
                s3_utils.save_image(camera_id, timestamp, image_data)
                logger.info(
                    f"Image saved to S3, captured from camera {camera_id} at timestamp {timestamp}"
                )
            write_to_db(conn, cur, camera_id, timestamp, text)
            # To run a workflow:
            # api_utils.run_workflow(input_image, workflow_id)
        except Exception as exc:
            logger.error(f"Error processing message: {exc}")
            logger.exception(exc)
            time.sleep(1)


def main():
    process_messages()


if __name__ == "__main__":
    main()
