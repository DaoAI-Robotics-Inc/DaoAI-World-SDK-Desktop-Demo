import os

import redis

r = redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
)
r_server = redis.from_url(os.getenv("REDIS_SERVER", "redis://redis:6379/0"))


def get_redis_client():
    return r


def get_key(camera_id, timestamp):
    return f"camera:{camera_id}:frame:{timestamp}"


def get_camera_frame(camera_id, timestamp):
    hash_name = get_key(camera_id, timestamp)
    field = "image_data"
    return r_server.hget(hash_name, field)
