import argparse
import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple

import aiohttp
import websockets
from redis import asyncio as aioredis

# Flags that represent vehicle classes in the received JSON.  Only these
# keys will be used when attempting to categorise a detected vehicle.
VEHICLE_CATEGORIES = ["car", "Truck", "SUV", "Motor", "mianbao", "sanlun"]

CLIENT_ID = "demo_client"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# vehicle_counts[camera_id][category] -> count
vehicle_counts = defaultdict(lambda: defaultdict(int))

# previous_boxes[camera_id] -> List[Tuple[Tuple[float, float, float, float], str]]
# Each entry contains a bounding box and its classified category from the
# previous frame. This is used for a simple IoU-based matching so the same
# vehicle isn't counted across consecutive frames.
previous_boxes: Dict[int, List[Tuple[Tuple[float, float, float, float], str]]] = defaultdict(list)

# track_centers[camera_id][tracker_id] -> (x, y)
track_centers: Dict[int, Dict[int, Tuple[float, float]]] = defaultdict(dict)

# speed_histories[camera_id] -> deque[(timestamp, speed)] for running average
speed_histories: Dict[int, deque] = defaultdict(deque)

# Placeholder redis client for persisting statistics
redis_client: aioredis.Redis | None = None


def iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
    """Return Intersection over Union (IoU) of two bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    if inter_w <= 0.0 or inter_h <= 0.0:
        return 0.0

    inter_area = inter_w * inter_h
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    if union_area <= 0.0:
        return 0.0

    return inter_area / union_area




IOU_THRESHOLD = 0.1

# expected normal traffic speed (km/h)
EXPECTED_SPEED = 100

# track low speed start time per tracker
low_speed_tracker: Dict[int, Dict[int, float]] = defaultdict(dict)

ACCIDENT_API_URL = "http://prod.daoai.ca:38080/workflows/12/run"
ACCIDENT_NODE_ID = "5416394f-7193-409c-aec2-5f4a435317db"


async def check_accident(image_path: str | None) -> bool:
    """Send image to accident detection API."""
    if not image_path or not os.path.exists(image_path):
        return False
    try:
        async with aiohttp.ClientSession() as session:
            with open(image_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("input_image", f, filename=os.path.basename(image_path))
                form.add_field("target_node_id", ACCIDENT_NODE_ID)
                async with session.post(ACCIDENT_API_URL, data=form) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("traffic_accident", False)
    except Exception as exc:
        logger.error("Accident API call failed: %s", exc)
    return False


async def store_stats(camera_id: int, counts: Dict[str, int]) -> None:
    """Placeholder for persisting vehicle counts into Redis."""
    if redis_client is None:
        return
    try:
        await redis_client.hset(f"camera:{camera_id}:counts", mapping=counts)
    except Exception as exc:
        logger.error("Failed to store stats to redis: %s", exc)


async def handle_message(msg: str) -> None:
    """Process a single WebSocket message."""
    try:
        data = json.loads(msg)
    except json.JSONDecodeError:
        logger.warning("Received invalid JSON")
        return

    if not isinstance(data, dict):
        logger.warning("Unexpected JSON type: %s", type(data).__name__)
        return

    camera_id = data.get("camera_id")
    if camera_id is None:
        logger.warning("camera_id missing in message")
        return

    # Extract detection shapes from any node outputs.
    node_outputs = data.get("node_outputs", {})
    image_w = data.get("image_width") or 1
    image_h = data.get("image_height") or 1
    road_area = float(image_w * image_h)

    detections: List[Dict[str, object]] = []
    for node in node_outputs.values():
        if not isinstance(node, dict):
            continue
        shapes = node.get("shapes") or []
        for shape in shapes:
            pts = shape.get("points")
            if not pts or len(pts) != 2:
                continue
            box = (
                float(pts[0][0]),
                float(pts[0][1]),
                float(pts[1][0]),
                float(pts[1][1]),
            )
            flags = shape.get("flags", {})
            vehicle_cls = None
            for key in VEHICLE_CATEGORIES:
                if flags.get(key) or flags.get(key.lower()) or flags.get(key.capitalize()):
                    vehicle_cls = key.lower()
                    break

            if not vehicle_cls:
                label = shape.get("attr") or shape.get("label")
                if label:
                    vehicle_cls = str(label).lower()

            if not vehicle_cls or vehicle_cls == "people" or vehicle_cls not in [c.lower() for c in VEHICLE_CATEGORIES]:
                # Skip unrecognised objects and pedestrians
                continue

            detection = {
                "box": box,
                "cls": vehicle_cls,
                "tracker": shape.get("tracker_id"),
                "speed": float(shape.get("speed", 0.0)),
            }
            detections.append(detection)

    # Tally vehicles found in this frame for reporting
    frame_counts: Dict[str, int] = defaultdict(int)
    direction_stats: Dict[int, Dict[str, float]] = defaultdict(lambda: {"count": 0, "speed": 0.0, "area": 0.0})
    detection_dirs: Dict[int, int] = {}
    now = time.time()
    for det in detections:
        frame_counts[det["cls"]] += 1

        box = det["box"]
        tracker = det.get("tracker")
        speed = det.get("speed", 0.0)

        # running speed history
        if speed > 0:
            hist = speed_histories[camera_id]
            hist.append((now, speed))
            while hist and now - hist[0][0] > 10:
                hist.popleft()

        if tracker is not None:
            if speed < 5:
                start = low_speed_tracker[camera_id].get(tracker)
                if start is None:
                    low_speed_tracker[camera_id][tracker] = now
                elif now - start >= 3:
                    accident = await check_accident(data.get("input_image_key"))
                    if accident:
                        logger.warning("Camera %s tracker %s \u68c0\u6d4b\u5230\u4ea4\u901a\u4e8b\u6545", camera_id, tracker)
                    else:
                        logger.warning("Camera %s tracker %s \u68c0\u6d4b\u5230\u8f66\u8f86\u5f02\u5e38\u505c\u6b62", camera_id, tracker)
                    low_speed_tracker[camera_id][tracker] = now
            else:
                low_speed_tracker[camera_id].pop(tracker, None)

        # compute direction sign based on movement
        center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        sign = 0
        if tracker is not None:
            prev_center = track_centers[camera_id].get(tracker)
            if prev_center:
                dx = center[0] - prev_center[0]
                dy = center[1] - prev_center[1]
                if abs(dx) >= abs(dy):
                    if dx > 0:
                        sign = 1
                    elif dx < 0:
                        sign = -1
                else:
                    if dy > 0:
                        sign = 1
                    elif dy < 0:
                        sign = -1
            track_centers[camera_id][tracker] = center
        detection_dirs[tracker or -1] = sign

        if speed < -5:
            logger.warning("Camera %s tracker %s \u68c0\u6d4b\u5230\u9006\u884c", camera_id, tracker)

        info = direction_stats[sign]
        info["count"] += 1
        info["speed"] += speed
        area = (box[2] - box[0]) * (box[3] - box[1])
        info["area"] += area

    # compute stats after iterating detections
    hist = speed_histories[camera_id]
    avg_speed_overall = sum(s for _, s in hist) / len(hist) if hist else 0.0

    majority_sign = 0
    if direction_stats:
        majority_sign = max(direction_stats.items(), key=lambda kv: kv[1]["count"])[0]

    wrong_way_ids = [tid for tid, s in detection_dirs.items() if majority_sign and s == -majority_sign and tid != -1]

    # Congestion detection per direction
    for sign, info in direction_stats.items():
        if info["count"] == 0 or sign == 0:
            continue
        avg_speed = info["speed"] / info["count"]
        area_ratio = info["area"] / road_area if road_area else 0
        if avg_speed < 60 and info["count"] >= 6 and area_ratio > 0.5:
            severity = "light"
            if avg_speed < 20:
                severity = "severe"
            elif avg_speed < 40:
                severity = "medium"
            logger.warning(
                "Camera %s congestion %s dir %d (avg_speed %.1f km/h count %d area_ratio %.2f)",
                camera_id,
                severity,
                sign,
                avg_speed,
                info["count"],
                area_ratio,
            )

    if wrong_way_ids:
        logger.warning("Camera %s wrong-way trackers: %s", camera_id, wrong_way_ids)

    if not detections:
        # Fallback when message lacks explicit shape information.
        vehicle_cls = (
            data.get("vehicle_class")
            or data.get("class")
            or data.get("type")
            or data.get("attr")
            or data.get("label")
        )
        vehicle_cls = str(vehicle_cls).lower() if vehicle_cls else None
        if vehicle_cls and vehicle_cls in [c.lower() for c in VEHICLE_CATEGORIES]:
            vehicle_counts[camera_id][vehicle_cls] += 1
        previous_boxes[camera_id] = []
    else:
        prev = previous_boxes[camera_id]
        new_boxes: List[Tuple[Tuple[float, float, float, float], str]] = []
        for det in detections:
            box = det["box"]
            cls = det["cls"]
            matched = False
            for prev_box, _ in prev:
                if iou(box, prev_box) >= IOU_THRESHOLD:
                    matched = True
                    break
            if not matched:
                vehicle_counts[camera_id][cls] += 1
            new_boxes.append((box, cls))
        previous_boxes[camera_id] = new_boxes

    # Prepare logging output
    totals = vehicle_counts[camera_id]
    total_count = sum(totals.values())
    stats = " ".join(f"{k}:{v}" for k, v in totals.items())
    frame_stats = " ".join(f"{k}:{v}" for k, v in frame_counts.items())
    current_total = sum(frame_counts.values())

    ratio = avg_speed_overall / EXPECTED_SPEED * 100 if EXPECTED_SPEED else 0
    status = "\u4ea4\u901a\u7545\u901a"  # traffic normal
    if ratio < 20:
        status = "\u4e25\u91cd\u62e5\u5835"  # severe congestion
    elif ratio < 40:
        status = "\u4e2d\u5ea6\u62e5\u5835"  # medium congestion
    elif ratio < 60:
        status = "\u8f7b\u5ea6\u62e5\u5835"  # light congestion
    elif ratio < 80:
        status = "\u7f13\u884c"  # slow traffic

    logger.info(
        "Camera %s totals(%d) -> %s | current frame(%d) -> %s | avg speed %.1f km/h %s",
        camera_id,
        total_count,
        stats,
        current_total,
        frame_stats,
        avg_speed_overall,
        status,
    )

    await store_stats(camera_id, totals)

async def connect_and_listen(server, camera_ids):
    uri = f"{server.rstrip('/')}" + f"/stream/ws?client_id={CLIENT_ID}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"action": "subscribe", "camera_ids": camera_ids}))
                logger.info("Subscribed to cameras %s", camera_ids)
                while True:
                    try:
                        message = await websocket.recv()
                        await handle_message(message)
                    except websockets.ConnectionClosed:
                        logger.warning("WebSocket closed, reconnecting...")
                        break
                    except Exception as exc:
                        logger.error("Error handling message: %s", exc)
            await asyncio.sleep(1)
        except Exception as exc:
            logger.error("Connection error: %s", exc)
            await asyncio.sleep(5)

def parse_args():
    parser = argparse.ArgumentParser(description="Vehicle flow demo")
    parser.add_argument(
        "--server",
        default=os.getenv("WS_SERVER"),
        help="Server host:port, e.g. 127.0.0.1:8000",
    )
    parser.add_argument(
        "--camera-ids",
        default=os.getenv("CAMERA_IDS"),
        help="Comma-separated camera IDs",
    )
    parser.add_argument(
        "--redis-host", default=os.getenv("REDIS_HOST", "redis"), help="Redis host"
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=int(os.getenv("REDIS_PORT", "6379")),
        help="Redis port",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    camera_ids = [int(cid) for cid in args.camera_ids.split(',') if cid]

    global redis_client
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", f"redis://{args.redis_host}:{args.redis_port}/0"),
        decode_responses=True,
    )

    await connect_and_listen(args.server, camera_ids)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:        pass
