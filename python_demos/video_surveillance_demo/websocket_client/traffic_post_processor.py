import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple

import requests
from redis import asyncio as aioredis
import redis
import websockets
import cv2
import numpy as np
import math

# Flags that represent vehicle classes in the received JSON. These are used
# when attempting to categorise a detected vehicle from the flags field. The
# program no longer strictly filters by these categories so that any provided
# label can be counted.
VEHICLE_CATEGORIES = ["car", "Truck", "SUV", "Motor", "mianbao", "sanlun"]
ACCIDENT_WORKFLOW_ID = 52
ACCIDENT_NODE_ID = "a3dc06bc-fd72-4941-a5c7-9be854192370"
EXPECTED_SPEED = 50
CAMERA_IDS = [4,42]
CLIENT_ID = "demo_client"


IOU_THRESHOLD = 0.25
API_ENDPOINT   = os.getenv("API_SERVER", "http://s1.daoai.ca:38080")
REDIS_SERVER_URL   = os.getenv(
    "REDIS_SERVER",
    "redis://default:mypassword@192.168.10.101:16379/0"
)
# expected normal traffic speed (km/h)
BASE_DIR = os.path.dirname(__file__)
ALERT_DIR = os.path.join(BASE_DIR, "alert")
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")
os.makedirs(ALERT_DIR, exist_ok=True)

# startup time and cooldown configuration
STARTUP_DELAY = 10.0  # seconds before alerts are persisted
SCRIPT_START_TIME = time.time()
EVENT_COOLDOWN = 10.0  # minimum seconds between same event type
last_event_time: Dict[str, float] = defaultdict(float)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
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

# tracking state for computing object speeds
speed_states: Dict[int, Dict[int, Dict[str, object]]] = defaultdict(dict)

# configuration for speed computation per camera
speed_configs: Dict[int, Dict[str, object]] = {}

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


def _compute_homography(
    polygon: List[Tuple[float, float]], edge_distances: List[float]
) -> np.ndarray:
    src = np.array(polygon, dtype=np.float32)

    dst = [np.array([0.0, 0.0], dtype=np.float32)]
    for i in range(1, len(src)):
        vec = src[i] - src[i - 1]
        pix_len = float(np.linalg.norm(vec)) or 1.0
        scale = edge_distances[i - 1] / pix_len
        dst.append(dst[i - 1] + vec * scale)

    dst = np.array(dst, dtype=np.float32)

    if len(src) == 4:
        H = cv2.getPerspectiveTransform(src, dst)
    else:
        H, _ = cv2.findHomography(src, dst)
    return H


def compute_speeds_inplace(
    dets: List[Dict[str, object]],
    timestamp: int,
    polygon: List[Tuple[float, float]],
    edge_distances: List[float],
    states: Dict[int, Dict[str, object]],
    smoothing_window: int = 2,
    unit: str = "kmh",
) -> None:
    H = _compute_homography(polygon, edge_distances)
    for det in dets:
        box = det.get("box")
        tracker_id = det.get("tracker")
        if box is None or tracker_id is None:
            continue
        cx = (box[0] + box[2]) / 2.0
        cy = (box[1] + box[3]) / 2.0
        world = cv2.perspectiveTransform(
            np.array([[[cx, cy]]], dtype=np.float32), H
        )[0][0]
        state = states.get(tracker_id, {"last_pos": None, "last_time": None, "speeds": []})
        last_pos = state["last_pos"]
        last_time = state["last_time"]
        speeds = state["speeds"]
        speed_mps = 0.0
        if last_pos is not None and last_time is not None and timestamp > last_time:
            dx = world[0] - last_pos[0]
            dy = world[1] - last_pos[1]
            dist = math.hypot(dx, dy)
            dt = (timestamp - last_time) / 1000.0
            if dt > 0:
                inst_speed = dist / dt
                speeds.append(inst_speed)
                if smoothing_window > 1:
                    speeds = speeds[-smoothing_window:]
                speed_mps = sum(speeds) / len(speeds)
            else:
                speeds = []
        states[tracker_id] = {"last_pos": world, "last_time": timestamp, "speeds": speeds}
        if unit == "kmh":
            det["speed"] = float(speed_mps * 3.6)
        elif unit == "cms":
            det["speed"] = float(speed_mps * 100.0)
        else:
            det["speed"] = float(speed_mps)
        det["speed_unit"] = unit


def ensure_speed_config(camera_id: int, data: Dict[str, object]) -> None:
    if camera_id in speed_configs:
        return
    node_defs = data.get("node_defs", {})
    for node in node_defs.values():
        if not isinstance(node, dict):
            continue
        if node.get("type") != "dataProcessing":
            continue
        cfg = node.get("data") or {}
        if cfg.get("type") != "object_movement_speed":
            continue
        polygon = cfg.get("polygon")
        edge_distances = cfg.get("edge_distances")
        if not polygon or not edge_distances:
            continue
        try:
            polygon = [tuple(map(float, p)) for p in polygon]
            edge_distances = [float(x) for x in edge_distances]
        except Exception:
            continue
        unit = cfg.get("unit", "kmh")
        smoothing = int(cfg.get("smoothing_window", 1))
        speed_configs[camera_id] = {
            "polygon": polygon,
            "edge_distances": edge_distances,
            "unit": unit,
            "smoothing_window": smoothing,
        }
        break




# track low speed info per tracker
# Each entry stores a mapping of tracker_id -> {"start": timestamp, "detected": bool}
low_speed_tracker: Dict[int, Dict[int, Dict[str, float | bool]]] = defaultdict(dict)


r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
r_server = redis.from_url(
    os.getenv("REDIS_SERVER", "redis://default:mypassword@s1.daoai.ca:16379/0")
)


def get_redis_client():
    return r


def get_key(camera_id: int, timestamp: int) -> str:
    return f"camera:{camera_id}:frame:{timestamp}"


def get_camera_frame(camera_id: int, timestamp: int) -> bytes | None:
    hash_name = get_key(camera_id, timestamp)
    return r_server.hget(hash_name, "image_data")


def get_latest_camera_frame(camera_id: int) -> bytes | None:
    """Return the latest frame image bytes for the given camera."""
    pattern = f"camera:{camera_id}:frame:*"
    latest_ts = None
    latest_key = None
    for key in r_server.scan_iter(pattern):
        try:
            ts = int(key.rsplit(":", 1)[-1])
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
                latest_key = key
        except Exception:
            continue
    if latest_key:
        return r_server.hget(latest_key, "image_data")
    return None


def save_alert(event_type: str, message: str, image_key: str | None, camera_id: int) -> None:
    """Persist alert log and related image under ALERT_DIR."""
    now = time.time()
    if now - SCRIPT_START_TIME < STARTUP_DELAY:
        return
    last = last_event_time.get(event_type, 0.0)
    if now - last < EVENT_COOLDOWN:
        last_event_time[event_type] = now
        return
    last_event_time[event_type] = now
    ts = int(now * 1000)
    event_dir = os.path.join(ALERT_DIR, event_type)
    os.makedirs(event_dir, exist_ok=True)
    log_path = os.path.join(event_dir, f"{ts}.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(message)

    image_bytes = None
    if image_key:
        try:
            parts = image_key.split(":")
            if len(parts) == 4:
                cid = int(parts[1])
                ts_img = int(parts[3])
                image_bytes = get_camera_frame(cid, ts_img)
        except Exception:
            image_bytes = None
    if not image_bytes:
        image_bytes = get_latest_camera_frame(camera_id)
    if image_bytes:
        with open(os.path.join(event_dir, f"{ts}.jpg"), "wb") as img_f:
            img_f.write(image_bytes)


API_ENDPOINT = os.getenv("API_SERVER", "http://localhost:38080")

# workflow and node constants for traffic statistics
TARGET_WORKFLOW_ID = int(os.getenv("TARGET_WORKFLOW_ID", "5"))
TARGET_NODE_ID = os.getenv("TARGET_NODE_ID", "")



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
        resp = run_workflow(image_bytes, ACCIDENT_WORKFLOW_ID, ACCIDENT_NODE_ID)
        if resp.status_code == 200:
            return resp.json()
        return None

    data = await asyncio.to_thread(_call)
    if data:
        return bool(data.get(ACCIDENT_NODE_ID))
    return False


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

    ensure_speed_config(camera_id, data)

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

    cfg = speed_configs.get(camera_id)
    if cfg:
        ts = int(data.get("timestamp") or int(time.time() * 1000))
        compute_speeds_inplace(
            detections,
            ts,
            cfg["polygon"],
            cfg["edge_distances"],
            speed_states[camera_id],
            cfg.get("smoothing_window", 1),
            cfg.get("unit", "kmh"),
        )

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
                            msg = (
                                f"Camera {camera_id} tracker {tracker} \u68c0\u6d4b\u5230\u4ea4\u901a\u4e8b\u6545"
                            )
                            logger.warning(msg)
                            accident_detected = True
                            await asyncio.to_thread(
                                save_alert,
                                "accident",
                                msg,
                                image_key,
                                camera_id,
                            )
                        else:
                            msg = (
                                f"Camera {camera_id} tracker {tracker} \u68c0\u6d4b\u5230\u8f66\u8f86\u5f02\u5e38\u505c\u6b62"
                            )
                            logger.warning(msg)
                            abnormal_stop_detected = True
                            await asyncio.to_thread(
                                save_alert,
                                "abnormal_stop",
                                msg,
                                image_key,
                                camera_id,
                            )
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
            msg = (
                f"Camera {camera_id} tracker {tracker} \u68c0\u6d4b\u5230\u9006\u884c"
            )
            logger.warning(msg)
            wrong_way_detected = True
            await asyncio.to_thread(
                save_alert,
                "wrong_way",
                msg,
                image_key,
                camera_id,
            )

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
            msg = (
                f"Camera {camera_id} congestion {severity} dir {sign} (avg_speed {avg_speed:.1f} km/h count {info['count']} area_ratio {area_ratio:.2f})"
            )
            logger.warning(
                "Camera %s congestion %s dir %d (avg_speed %.1f km/h count %d area_ratio %.2f)",
                camera_id,
                severity,
                sign,
                avg_speed,
                info["count"],
                area_ratio,
            )
            await asyncio.to_thread(
                save_alert,
                "congestion",
                msg,
                image_key,
                camera_id,
            )

    if wrong_way_ids:
        msg = f"Camera {camera_id} wrong-way trackers: {wrong_way_ids}"
        logger.warning("Camera %s wrong-way trackers: %s", camera_id, wrong_way_ids)
        wrong_way_detected = True
        await asyncio.to_thread(
            save_alert,
            "wrong_way",
            msg,
            image_key,
            camera_id,
        )

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

async def connect_and_listen(server: str, camera_ids: List[int]) -> None:
    """Subscribe to cameras via WebSocket and handle incoming messages."""
    uri = f"{server.rstrip('/')}" + f"/stream/ws?client_id={CLIENT_ID}"
    print(uri, camera_ids)
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(
                    json.dumps({"action": "subscribe", "camera_ids": camera_ids})
                )
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
            await asyncio.sleep(2)

async def _main_async() -> None:
    """Initialize Redis client and start WebSocket listener."""
    global redis_client
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    )
    server = os.getenv("WS_SERVER", "ws://s1.daoai.ca:48080")
    await connect_and_listen(server, CAMERA_IDS)

def main() -> None:
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
