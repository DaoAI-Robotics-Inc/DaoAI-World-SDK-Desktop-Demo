import os
import cv2
import base64
import json
import asyncio
import logging
import argparse
from datetime import datetime
from collections import defaultdict

import numpy as np
import websockets

CLIENT_ID = "demo_client"
VEHICLE_ATTRS = {"truck", "car", "motor"}
MAX_MISSED = 5
IOU_THRESHOLD = 0.5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

tracks = []
totals = defaultdict(int)
events = []


def decode_image(b64str):
    data = base64.b64decode(b64str)
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def iou(box_a, box_b):
    xA = max(box_a[0], box_b[0])
    yA = max(box_a[1], box_b[1])
    xB = min(box_a[2], box_b[2])
    yB = min(box_a[3], box_b[3])
    if xB <= xA or yB <= yA:
        return 0.0
    inter = (xB - xA) * (yB - yA)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / float(area_a + area_b - inter)


def update_tracks(detections, timestamp):
    matched = [False] * len(detections)
    for track in tracks:
        best_iou = 0.0
        best_idx = -1
        for i, det in enumerate(detections):
            if matched[i]:
                continue
            val = iou(track["bbox"], det["bbox"])
            if val > best_iou:
                best_iou = val
                best_idx = i
        if best_iou > IOU_THRESHOLD:
            track["bbox"] = detections[best_idx]["bbox"]
            track["missed"] = 0
            track["consecutive"] += 1
            if track["consecutive"] >= 2 and not track["counted"]:
                totals[track["attr"]] += 1
                events.append({"time": timestamp, "attr": track["attr"]})
                track["counted"] = True
            matched[best_idx] = True
        else:
            track["missed"] += 1
            track["consecutive"] = 0
    for i, det in enumerate(detections):
        if not matched[i]:
            tracks.append({
                "bbox": det["bbox"],
                "attr": det["attr"],
                "missed": 0,
                "consecutive": 1,
                "counted": False,
            })
    tracks[:] = [t for t in tracks if t["missed"] <= MAX_MISSED]


def _extract_predictions(data):
    """Return detection results from the websocket message."""
    preds = []
    # direct predictions (fallback)
    root_preds = data.get("predictions")
    if isinstance(root_preds, list):
        preds.extend(root_preds)

    node_defs = data.get("node_defs", {})
    node_outputs = data.get("node_outputs", {})

    # only parse outputs from model nodes
    model_ids = [uid for uid, nd in node_defs.items() if nd.get("type") == "models"]

    for uid in model_ids:
        node = node_outputs.get(uid, {})
        for shape in node.get("shapes", []):
            attr = shape.get("label")
            flags = shape.get("flags", {})
            for key in ("truck", "car", "motor"):
                if flags.get(key) or flags.get(key.capitalize()):
                    attr = key
            pts = shape.get("points") or []
            if attr and len(pts) >= 2:
                x1, y1 = pts[0]
                x2, y2 = pts[1]
                preds.append({"attr": attr, "bbox": [x1, y1, x2, y2]})

    return preds


def output_stats():
    """Print current vehicle totals."""
    if totals:
        stats = " ".join(f"{k}:{v}" for k, v in totals.items())
        logger.info(f"Current totals -> {stats}")


def process(data):
    image_b64 = data.get("image")
    if image_b64:
        _ = decode_image(image_b64)
    preds = _extract_predictions(data)
    detections = []
    for item in preds:
        attr = item.get("attr") or item.get("label")
        bbox = item.get("bbox")
        if attr and bbox:
            attr = attr.lower()
            if attr in VEHICLE_ATTRS:
                detections.append({"bbox": bbox, "attr": attr})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def record():
        update_tracks(detections, timestamp)
        output_stats()

    record()


async def subscribe(server: str, camera_ids):
    uri = f"ws://{server.rstrip('/')}" + f"/stream/ws?client_id={CLIENT_ID}"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"action": "subscribe", "camera_ids": camera_ids}))
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                process(data)
        except asyncio.CancelledError:
            pass
        finally:
            await websocket.send(json.dumps({"action": "unsubscribe", "camera_ids": camera_ids}))


def save_report(out_dir="python_demos/output"):
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"vehicle_flow_report_{now}.json")
    with open(path, "w") as f:
        json.dump({"totals": totals, "events": events}, f, indent=4)
    logger.info(f"Report saved to {path}\n")


def parse_args():
    parser = argparse.ArgumentParser(description="WebSocket vehicle flow client")
    parser.add_argument("--server", required=True, help="Server host:port, e.g. 127.0.0.1:8000")
    parser.add_argument("--camera-ids", required=True, help="Comma-separated camera IDs")
    return parser.parse_args()


def main():
    args = parse_args()
    camera_ids = [int(cid) for cid in args.camera_ids.split(',') if cid]
    try:
        asyncio.run(subscribe(args.server, camera_ids))
    except KeyboardInterrupt:
        pass
    finally:
        save_report()


if __name__ == "__main__":
    main()