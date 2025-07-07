import argparse
import asyncio
import json
import logging
import os

import websockets
from redis import asyncio as aioredis


CLIENT_ID = "demo_client"

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)


async def subscribe(server: str, camera_ids, redis_client):
    """Subscribe to camera alerts, log messages and enqueue them."""
    uri = f"ws://{server.rstrip('/')}" + f"/stream/ws?client_id={CLIENT_ID}"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"action": "subscribe", "camera_ids": camera_ids}))
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                camera_id = data.get("camera_id", "unknown")
                logger.info(f"Received message from camera {camera_id}: {message}")
                await redis_client.rpush("alerts_queue", message)
        except asyncio.CancelledError:
            # Allow graceful cancellation (e.g. on Ctrl+C)
            pass
        finally:
            await websocket.send(json.dumps({"action": "unsubscribe", "camera_ids": camera_ids}))


def parse_args():
    parser = argparse.ArgumentParser(description="WebSocket client for camera alerts")
    parser.add_argument("--server", default=os.getenv("WS_SERVER"), help="Server host:port, e.g. 127.0.0.1:8000")
    parser.add_argument("--camera-ids", default=os.getenv("CAMERA_IDS"), help="Comma-separated camera IDs")
    parser.add_argument("--redis-host", default=os.getenv("REDIS_HOST", "redis"), help="Redis host")
    parser.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", "6379")), help="Redis port")
    return parser.parse_args()


def main():
    args = parse_args()
    camera_ids = [int(cid) for cid in args.camera_ids.split(',') if cid]
    redis_client = aioredis.Redis(host=args.redis_host, port=args.redis_port, decode_responses=True)
    try:
        asyncio.run(subscribe(args.server, camera_ids, redis_client))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
