import argparse
import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple

import requests
import websockets
from redis import asyncio as aioredis
import redis

# Flags that represent vehicle classes in the received JSON. These are used
# when attempting to categorise a detected vehicle from the flags field. The
# program no longer strictly filters by these categories so that any provided
# label can be counted.
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

# track low speed info per tracker
# Each entry stores a mapping of tracker_id -> {"start": timestamp, "detected": bool}
low_speed_tracker: Dict[int, Dict[int, Dict[str, float | bool]]] = defaultdict(dict)

ACCIDENT_NODE_ID = "5416394f-7193-409c-aec2-5f4a435317db"

r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
r_server = redis.from_url(os.getenv("REDIS_SERVER", "redis://redis:6379/0"))


def get_redis_client():
    return r


def get_key(camera_id: int, timestamp: int) -> str:
    return f"camera:{camera_id}:frame:{timestamp}"


def get_camera_frame(camera_id: int, timestamp: int) -> bytes | None:
    hash_name = get_key(camera_id, timestamp)
    return r_server.hget(hash_name, "image_data")


API_ENDPOINT = os.getenv("API_SERVER", "http://localhost:38080")


def run_workflow(input_image: bytes, workflow_id: int, target_node_id: str | None = None) -> requests.Response:
    files = {"input_image": ("image.jpg", input_image, "image/jpeg")}
    params = {"target_node_id": target_node_id} if target_node_id else None
    return requests.post(
        API_ENDPOINT + f"/workflows/{workflow_id}/run", files=files, params=params
    )


async def check_accident(image_key: str | None) -> bool:
    """Send image bytes from Redis to accident detection API."""
    if not image_key:
        return False
    try:
        parts = image_key.split(":")
        if len(parts) != 4:
            return False
        camera_id = int(parts[1])
        timestamp = int(parts[3])
    except Exception:
        return False

    image_bytes = await asyncio.to_thread(get_camera_frame, camera_id, timestamp)
    if not image_bytes:
        return False

    def _call():
        resp = run_workflow(image_bytes, 12, ACCIDENT_NODE_ID)
        if resp.status_code == 200:
            return resp.json()
        return None

    data = await asyncio.to_thread(_call)
    if data:
        return bool(data.get(ACCIDENT_NODE_ID))
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

    wrong_way_detected = False
    accident_detected = False
    abnormal_stop_detected = False

    # Extract detection shapes from any node outputs.
    node_outputs = data.get("node_outputs", {})
    image_key = node_outputs.get("input_image_key")
    image_w = data.get("image_width") or 1
    image_h = data.get("image_height") or 1
    road_area = float(image_w * image_h)

    detections_by_tracker: Dict[int, Dict[str, object]] = {}
    for node in node_outputs.values():
        if not isinstance(node, dict):
            continue
        # some nodes expose detections under "predictions" rather than "shapes"
        shapes = node.get("predictions") or node.get("shapes") or []
        for shape in shapes:
            if str(shape.get("label", "")).lower() != "vehicle":
                continue
            tracker = shape.get("tracker_id")
            key_id = tracker if tracker is not None else id(shape)
            det = detections_by_tracker.setdefault(
                key_id, {"box": None, "cls": None, "tracker": tracker, "speed": None}
            )
            pts = shape.get("points")
            if pts and len(pts) == 2:
                det["box"] = (
                    float(pts[0][0]),
                    float(pts[0][1]),
                    float(pts[1][0]),
                    float(pts[1][1]),
                )

            if "speed" in shape and det.get("speed") is None:
                try:
                    det["speed"] = float(shape.get("speed"))
                except Exception:
                    det["speed"] = None

            flags = shape.get("flags", {})
            if not det.get("cls"):
                for key in VEHICLE_CATEGORIES:
                    if flags.get(key) or flags.get(key.lower()) or flags.get(key.capitalize()):
                        det["cls"] = key.lower()
                        break
            if not det.get("cls"):
                lbl = shape.get("label")
                if isinstance(lbl, str):
                    det["cls"] = lbl.lower()

    detections = list(detections_by_tracker.values())

    # Tally vehicles found in this frame for reporting
    frame_counts: Dict[str, int] = defaultdict(int)
    direction_stats: Dict[int, Dict[str, float]] = defaultdict(lambda: {"count": 0, "speed": 0.0, "area": 0.0})
    detection_dirs: Dict[int, int] = {}
    now = time.time()
    for det in detections:
        if det.get("cls"):
            frame_counts[det["cls"]] += 1

        box = det.get("box")
        if box is None:
            continue
        tracker = det.get("tracker")
        speed = det.get("speed")
        if speed is not None:
            try:
                speed = float(speed)
            except Exception:
                speed = None

        # running speed history
        if speed is not None and speed > 0:
            hist = speed_histories[camera_id]
            hist.append((now, speed))
            while hist and now - hist[0][0] > 10:
                hist.popleft()

        if tracker is not None:
            entry = low_speed_tracker[camera_id].get(tracker)
            if speed is not None and speed < 5:
                if entry is None:
                    low_speed_tracker[camera_id][tracker] = {"start": now, "detected": False}
                else:
                    if not entry.get("detected") and now - float(entry["start"]) >= 3:
                        accident = await check_accident(image_key)
                        if accident:
                            logger.warning(
                                "Camera %s tracker %s \u68c0\u6d4b\u5230\u4ea4\u901a\u4e8b\u6545",
                                camera_id,
                                tracker,
                            )
                            accident_detected = True
                        else:
                            logger.warning(
                                "Camera %s tracker %s \u68c0\u6d4b\u5230\u8f66\u8f86\u5f02\u5e38\u505c\u6b62",
                                camera_id,
                                tracker,
                            )
                            abnormal_stop_detected = True
                        entry["detected"] = True
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

        if speed is not None and speed < -5:
            logger.warning("Camera %s tracker %s \u68c0\u6d4b\u5230\u9006\u884c", camera_id, tracker)
            wrong_way_detected = True

        info = direction_stats[sign]
        info["count"] += 1
        if speed is not None:
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
        wrong_way_detected = True

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
        if vehicle_cls and vehicle_cls not in {"people", "person", "pedestrian"}:
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
            if not matched and cls:
                vehicle_counts[camera_id][cls] += 1
            new_boxes.append((box, cls or ""))
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

    anomaly_msg = "\u65e0"
    if accident_detected:
        anomaly_msg = "\u68c0\u6d4b\u5230\u4ea4\u901a\u4e8b\u6545"
    elif abnormal_stop_detected:
        anomaly_msg = "\u68c0\u6d4b\u5230\u8f66\u8f86\u5f02\u5e38\u505c\u6b62"
    elif wrong_way_detected:
        anomaly_msg = "\u68c0\u6d4b\u5230\u9006\u884c"

    logger.info(
        "Camera %s totals(%d) -> %s | current frame(%d) -> %s | avg speed %.1f km/h | \u8f66\u6d41\u72b6\u6001: %s | \u5f02\u5e38: %s",
        camera_id,
        total_count,
        stats,
        current_total,
        frame_stats,
        avg_speed_overall,
        status,
        anomaly_msg,
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
    except KeyboardInterrupt:
        pass
