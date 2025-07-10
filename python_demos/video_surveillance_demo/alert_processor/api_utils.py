import os

import requests

API_ENDPOINT = os.getenv("API_SERVER", "http://192.168.10.101:38080")

def run_workflow(
    input_image: bytes, workflow_id: int, target_node_id: str | None = None
) -> requests.Response:
    files = {"input_image": ("image.jpg", input_image, "image/jpeg")}
    params = {"target_node_id": target_node_id} if target_node_id else None
    return requests.post(
        API_ENDPOINT + f"/workflows/{workflow_id}/run", files=files, params=params
    )

import os
import time

import api_utils
import redis


r_server = redis.from_url(
    os.getenv("REDIS_SERVER", "redis://default:mypassword@192.168.10.101:16379/0")
)

def get_key(camera_id, timestamp):
    return f"camera:{camera_id}:frame:{timestamp}"


def get_camera_frame(camera_id, timestamp):
    hash_name = get_key(camera_id, timestamp)
    field = "image_data"
    return r_server.hget(hash_name, field)


def get_latest_camera_frame(camera_id):
    keys = r_server.keys(f"camera:{camera_id}:frame:*")
    timestamps = [int(key.decode().split(":")[-1]) for key in keys]
    max_timestamp = max(timestamps)
    return get_camera_frame(camera_id, max_timestamp)

