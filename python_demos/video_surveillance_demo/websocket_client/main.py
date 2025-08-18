import asyncio
import json
import logging
import os
import time
from typing import List

import aiohttp
from redis import asyncio as aioredis
import websockets

API_ENDPOINT = os.getenv("API_SERVER", "http://s1.daoai.ca:38080")
WS_SERVER = os.getenv("WS_SERVER", "ws://s1.daoai.ca:48080")
REDIS_SERVER_URL = os.getenv(
    "REDIS_SERVER", "redis://default:mypassword@s1.daoai.ca:16379/0"
)
WORKFLOW_ID = 105
TARGET_NODE_ID = None
CLIENT_ID = "demo_client"
BASE_DIR = os.path.dirname(__file__)
LOG_FILE = os.path.join(BASE_DIR, "traffic_demo.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger(__name__)

LIMIT = 200


async def fetch_all_cameras(session: aiohttp.ClientSession) -> List[dict]:
    """Fetch all cameras with pagination."""
    cameras: List[dict] = []
    offset = 0
    while True:
        params = {"offset": offset, "limit": LIMIT}
        async with session.get(f"{API_ENDPOINT}/cameras", params=params) as resp:
            resp.raise_for_status()
            batch = await resp.json()
        if not batch:
            break
        cameras.extend(batch)
        if len(batch) < LIMIT:
            break
        offset += LIMIT
    return cameras


async def list_target_cameras(session: aiohttp.ClientSession, workflow_id: int) -> List[int]:
    """Return camera IDs that belong to the given workflow."""
    all_cams = await fetch_all_cameras(session)
    return [
        c.get("id") or c.get("camera_id")
        for c in all_cams
        if c.get("workflow_id") == workflow_id
    ]


async def get_latest_image(redis_client: aioredis.Redis, camera_id: int) -> bytes | None:
    """Return the latest frame image bytes for the given camera."""
    pattern = f"camera:{camera_id}:frame:*"
    keys = await redis_client.keys(pattern)
    if not keys:
        return None
    ts = max(int(k.decode().split(":")[-1]) for k in keys)
    key = f"camera:{camera_id}:frame:{ts}"
    return await redis_client.hget(key, "image_data")


async def run_workflow(
    session: aiohttp.ClientSession,
    input_image: bytes,
    workflow_id: int,
    target_node_id: str | None = None,
) -> dict:
    """Invoke the workflow run API and return its JSON response."""
    url = f"{API_ENDPOINT}/workflows/{workflow_id}/run"
    form = aiohttp.FormData()
    form.add_field(
        "input_image", input_image, filename="image.jpg", content_type="image/jpeg"
    )
    params = {"target_node_id": target_node_id} if target_node_id else None
    async with session.post(url, data=form, params=params) as resp:
        resp.raise_for_status()
        return await resp.json()


def save_message(data: dict) -> str:
    """Save the WebSocket message to a JSON file and return its path."""
    ts = int(time.time() * 1000)
    path = os.path.join(BASE_DIR, f"message_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


async def handle_message(
    message: str,
    session: aiohttp.ClientSession,
    redis_client: aioredis.Redis,
) -> None:
    """Save message and run workflow on the latest camera frame."""
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON message")
        return

    file_path = save_message(data)
    logger.info("Saved message to %s", file_path)

    cam_id = data.get("camera_id")
    if cam_id is None:
        logger.warning("camera_id missing in message")
        return

    image = await get_latest_image(redis_client, cam_id)
    if not image:
        logger.warning("No image available for camera %s", cam_id)
        return

    result = await run_workflow(session, image, WORKFLOW_ID, TARGET_NODE_ID or None)
    logger.info("Workflow result for camera %s: %s", cam_id, result)


async def connect_and_listen(
    camera_id: int, session: aiohttp.ClientSession, redis_client: aioredis.Redis
) -> None:
    """Subscribe to a camera via WebSocket and process one message."""
    uri = f"{WS_SERVER.rstrip('/')}/stream/ws?client_id={CLIENT_ID}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"action": "subscribe", "camera_ids": [camera_id]}))
        msg = await ws.recv()
        await handle_message(msg, session, redis_client)


async def main() -> None:
    redis_client = aioredis.from_url(REDIS_SERVER_URL, decode_responses=False)
    async with aiohttp.ClientSession() as session:
        cameras = await list_target_cameras(session, WORKFLOW_ID)
        if not cameras:
            logger.error("No cameras found for workflow %s", WORKFLOW_ID)
            await redis_client.aclose()
            return
        camera_id = cameras[0]
        logger.info("Using camera %s", camera_id)
        await connect_and_listen(camera_id, session, redis_client)
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
