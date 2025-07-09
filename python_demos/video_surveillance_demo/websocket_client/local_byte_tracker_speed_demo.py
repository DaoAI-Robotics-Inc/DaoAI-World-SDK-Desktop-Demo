import argparse
import math
import os
import time
from types import SimpleNamespace

import cv2
import numpy as np
import random

from byte_tracker_core import ByteTrack

from daoai_detectron2.src.models.multilabel_roi_heads import MultiLabelROIHeads

import supervision as sv
from dt2.dt2.config import get_cfg
from daoai_detectron2.src.evaluation.evaluate import Predictor
from dt2.dt2 import model_zoo
from dt2.dt2.config import CfgNode


def letterbox_resize(img: np.ndarray, long_side: int = 1024) -> tuple[np.ndarray, float, int, int]:
    """Resize image to the given long side with padding.

    Returns the resized image along with the resize ratio and x/y offsets
    used for padding so coordinates can be scaled back if needed.
    """
    h, w = img.shape[:2]
    scale = long_side / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((long_side, long_side, 3), 114, dtype=resized.dtype)
    top = (long_side - new_h) // 2
    left = (long_side - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas, scale, left, top

def _compute_homography(
    polygon: list[tuple[float, float]], edge_distances: list[float]
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


def load_predictor(config_path: str, weights_path: str, score_thresh: float, device: str) -> Predictor:
    """Load a Detectron2 predictor from config and weights."""
    with open(config_path, 'r') as f:
        cfg_str = f.read()
    cfg = CfgNode().load_cfg(cfg_str)

    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thresh
    cfg.MODEL.WEIGHTS = weights_path
    cfg.MODEL.DEVICE = device
    return Predictor(cfg)


def decode_video_gpu(path: str):
    cap = cv2.cudacodec.createVideoReader(path)
    while True:
        ret, gpu_frame = cap.nextFrame()
        if not ret or gpu_frame.empty():
            break
        yield gpu_frame.download()


def decode_video_cpu(path: str):
    cap = cv2.VideoCapture(path)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame


def compute_speeds(tracked, timestamp, polygon, edge_distances, states, smoothing_window, unit):
    H = _compute_homography(polygon, edge_distances)
    poly = np.array(polygon, dtype=np.float32)
    results = []
    for det in tracked:
        pts = det.get("points") or []
        if len(pts) < 2:
            continue
        cx = (pts[0][0] + pts[1][0]) / 2.0
        cy = (pts[0][1] + pts[1][1]) / 2.0
        # if cv2.pointPolygonTest(poly, (cx, cy), False) < 0:
        #     continue
        world = cv2.perspectiveTransform(np.array([[[cx, cy]]], dtype=np.float32), H)[0][0]
        tracker_id = det.get("tracker_id")
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
        out_det = det.copy()
        if unit == "kmh":
            out_det["speed"] = float(speed_mps * 3.6)
        elif unit == "cms":
            out_det["speed"] = float(speed_mps * 100.0)
        else:
            out_det["speed"] = float(speed_mps)
        out_det["speed_unit"] = unit
        results.append(out_det)
    return results

import torch 

def main(
        video, 
        config, 
        weights, 
        score_thresh=0.5, 
        d2_device="cuda", 
        use_gpu_decode=True, 
        polygon=None, 
        edge_distances=None, 
        smoothing_window=1, 
        unit="kmh"
    ):

    predictor = load_predictor(config, weights, score_thresh, d2_device)
    predictor.model = predictor.model.half()

    polygon = [tuple(map(float, p.split(','))) for p in polygon.split()]
    edge_distances = [float(d) for d in edge_distances.split()]
    poly_pts = np.array(polygon, dtype=np.int32)

    tracker = ByteTrack()
    states: dict[int, dict] = {}
    colors: dict[int, tuple[int, int, int]] = {}

    decoder = decode_video_gpu if use_gpu_decode else decode_video_cpu
    cv2.namedWindow("tracking", cv2.WINDOW_NORMAL)
    times = []
    for frame in decoder(video):
        t_frame = time.perf_counter()
        ts = int(time.time() * 1000)
        resized, scale, off_x, off_y = letterbox_resize(frame, long_side=1024)
        t_model = time.perf_counter()
        outputs = predictor(resized)
        dets = sv.Detections.from_detectron2(outputs[0])
        print(f"MODEL TIME - {time.perf_counter() - t_model}")
        xyxy = dets.xyxy.astype(np.float32)
        xyxy[:, [0, 2]] = (xyxy[:, [0, 2]] - off_x) / scale
        xyxy[:, [1, 3]] = (xyxy[:, [1, 3]] - off_y) / scale
        confs = dets.confidence.astype(np.float32)
        labels = [str(c) for c in dets.class_id]
        det_ns = SimpleNamespace(xyxy=xyxy, confidence=confs, class_labels=labels)

        active = tracker.update_with_detections(det_ns, ts)
        tracked = []
        for t in active:
            x1, y1, x2, y2 = t.tlbr
            tracked.append({
                "points": [[float(x1), float(y1)], [float(x2), float(y2)]],
                "shape_type": "rectangle",
                "confidence": float(t.confidence),
                "label": getattr(t, "class_label", "unknown"),
                "tracker_id": int(t.external_track_id),
            })

        results = compute_speeds(
            tracked,
            ts,
            polygon,
            edge_distances,
            states,
            smoothing_window,
            unit,
        )

        times.append(time.perf_counter() - t_frame)
        print(f"Frame results computed in: {times[-1]}")

        cv2.polylines(frame, [poly_pts], isClosed=True, color=(255, 0, 0), thickness=2)

        for det in results:
            tid = int(det["tracker_id"])
            if tid not in colors:
                colors[tid] = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                )
            color = colors[tid]

            x1, y1 = map(int, det["points"][0])
            x2, y2 = map(int, det["points"][1])
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID {tid} {det['speed']:.2f} {det['speed_unit']}"
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        cv2.imshow('tracking', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cv2.destroyAllWindows()

    # Print the min, max and avg frame processing times
    print(f"Min frame processing time: {min(times)}")
    print(f"Max frame processing time: {max(times[1:])}")
    print(f"Avg frame processing time: {sum(times) / len(times)}")


if __name__ == "__main__":
    main(
        video="/home/daoai/dev_misc/Speed-Estimation-Help/daoai-video-analytics/scripts/highway.mp4",
        config="/home/daoai/dev_misc/Speed-Estimation-Help/daoai-video-analytics/scripts/config.yaml",
        weights="/home/daoai/dev_misc/Speed-Estimation-Help/daoai-video-analytics/scripts/model_best.pth",
        score_thresh=0.5,
        d2_device="cuda",
        use_gpu_decode=False,
        polygon="0,620 1280,620 1280,720 0,720",
        edge_distances="1280 100 1280 100",
        smoothing_window=1,
        unit="kmh"
    )