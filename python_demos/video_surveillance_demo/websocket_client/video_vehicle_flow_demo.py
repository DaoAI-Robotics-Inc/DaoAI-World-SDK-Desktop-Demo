import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

import websockets

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
    detections: List[Tuple[Tuple[float, float, float, float], str]] = []
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
            vehicle_cls = "unknown"
            for key in VEHICLE_CATEGORIES:
                if flags.get(key):
                    vehicle_cls = key
                    break
            detections.append((box, vehicle_cls))

    # Tally vehicles found in this frame for reporting
    frame_counts: Dict[str, int] = defaultdict(int)
    for _, cls in detections:
        frame_counts[cls] += 1

    if not detections:
        # Fallback when message lacks explicit shape information.
        vehicle_cls = (
            data.get("vehicle_class")
            or data.get("class")
            or data.get("type")
            or data.get("attr")
            or data.get("label")
            or "unknown"
        )
        vehicle_counts[camera_id][vehicle_cls] += 1
        previous_boxes[camera_id] = []
    else:
        prev = previous_boxes[camera_id]
        new_boxes: List[Tuple[Tuple[float, float, float, float], str]] = []
        for box, cls in detections:
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
    logger.info(
        "Camera %s totals(%d) -> %s | current frame(%d) -> %s",
        camera_id,
        total_count,
        stats,
        current_total,
        frame_stats,
    )

async def connect_and_listen(server, camera_ids):
    uri = f"ws://{server.rstrip('/')}" + f"/stream/ws?client_id={CLIENT_ID}"
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

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vehicle flow demo")
    parser.add_argument("--server", required=True, help="Server host:port")
    parser.add_argument("--camera-ids", required=True, help="Comma separated IDs")
    args = parser.parse_args()

    camera_ids = [int(cid) for cid in args.camera_ids.split(',') if cid]
    await connect_and_listen(args.server, camera_ids)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass