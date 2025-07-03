import os
import cv2
import time
import json
import logging
import argparse
import dwsdk.dwsdk as dwsdk

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VEHICLE_ATTRS = {"truck", "car", "motor"}

# max frames an object can disappear before considered gone
MAX_MISSED = 5
# IoU threshold to match detections to existing tracks
IOU_THRESHOLD = 0.5

def initialize_sdk():
    """Initialize the DaoAI SDK."""
    try:
        logger.info("Initializing SDK...")
        dwsdk.initialize()
        logger.info("SDK initialized.\n")
    except Exception as e:
        logger.error(f"SDK initialization failed: {e}")
        raise

def load_model(model_path, device=dwsdk.DeviceType.GPU):
    """Load the mixed model."""
    try:
        logger.info(f"Loading mixed model: {model_path}")
        model = dwsdk.MultilabelDetection(model_path, device=device)
        logger.info("Model loaded.\n")
        return model
    except Exception as e:
        logger.error(f"Model load error: {e}")
        raise


def process_frame(model, frame, threshold=0.5):
    """Run inference on one frame and return vehicle detections."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = dwsdk.Image.from_numpy(rgb, dwsdk.Image.Type.RGB)
    model.setConfidenceThreshold(threshold)
    pred = model.inference(img)
    detections = []
    for lbl, attrs, box in zip(pred.class_labels, pred.attributes, pred.boxes):
        if lbl.lower() == "vehicle" and attrs:
            attr, _ = max(attrs.items(), key=lambda x: x[1])
            attr = attr.lower()
            if attr in VEHICLE_ATTRS:
                detections.append({
                    "bbox": [box.x1(), box.y1(), box.x2(), box.y2()],
                    "attr": attr,
                })
    return detections

def overlay_counts(frame, counts):
    """Overlay vehicle counts on the given frame."""
    text = " ".join([f"{k.capitalize()}: {v}" for k, v in counts.items()])
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


def iou(box_a, box_b):
    """Compute Intersection over Union of two boxes."""
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


def update_tracks(detections, tracks, totals, events, timestamp):
    """Update tracked objects with new detections and count new vehicles.

    Args:
        detections (list): vehicle detections for the current frame
        tracks (list): active object tracks
        totals (dict): accumulated counts per attribute
        events (list): list of detection events with time information
        timestamp (str): ISO formatted system time when frame processed
    """
    matched = [False] * len(detections)
    # match existing tracks to detections
    for track in tracks:
        best_iou = 0.0
        best_idx = -1
        for i, det in enumerate(detections):
            if matched[i]:
                continue
            iou_val = iou(track["bbox"], det["bbox"])
            if iou_val > best_iou:
                best_iou = iou_val
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

    # add unmatched detections as new tracks
    for i, det in enumerate(detections):
        if not matched[i]:
            tracks.append({
                "bbox": det["bbox"],
                "attr": det["attr"],
                "missed": 0,
                "consecutive": 1,
                "counted": False,
            })

    # remove stale tracks
    tracks[:] = [t for t in tracks if t["missed"] <= MAX_MISSED]


def save_report(counts, events, out_dir="python_demos/output"):
    """Save the accumulated counts and events to a JSON report."""
    os.makedirs(out_dir, exist_ok=True)
    now = time.strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(out_dir, f"vehicle_flow_report_{now}.json")
    with open(report_path, "w") as f:
        json.dump({"totals": counts, "events": events}, f, indent=4)
    logger.info(f"Report saved to {report_path}\n")


def run_video(model_path, video_path, output_path=None, use_gpu=True):
    """Process a video, save annotated output and vehicle count report."""
    initialize_sdk()
    device = dwsdk.DeviceType.GPU if use_gpu else dwsdk.DeviceType.CPU
    model = load_model(model_path, device=device)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    frame_idx = 0
    last_percent = -1
    totals = {k: 0 for k in VEHICLE_ATTRS}
    tracks = []
    events = []
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    if output_path is None:
        now = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("python_demos/output", f"vehicle_flow_{now}.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    logger.info("Starting video processing...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        detections = process_frame(model, frame)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        update_tracks(detections, tracks, totals, events, now_str)
        overlay_counts(frame, totals)
        writer.write(frame)
        frame_idx += 1
        if total_frames > 0:
            percent = int(frame_idx * 100 / total_frames)
            if percent != last_percent:
                last_percent = percent
                logger.info(f"Processing... {percent}% ({frame_idx}/{total_frames})")
        elif frame_idx % 30 == 0:
            logger.info(f"Processed {frame_idx} frames...")
    cap.release()
    writer.release()
    logger.info(f"Annotated video saved to {output_path}")
    if total_frames > 0:
        logger.info(f"Video processing finished. 100% ({frame_idx}/{total_frames})")
    else:
        logger.info("Video processing finished.")
    save_report(totals, events)


def main():
    parser = argparse.ArgumentParser(description="Mixed model video vehicle flow demo")
    parser.add_argument('--model', default='data/traffic_mixed_model.dwm', help='Path to mixed model')
    parser.add_argument('--video', default=r'c:\Users\daoai\Downloads\traffic_test\traffic_site.mp4', help='Path to road surveillance video')
    parser.add_argument('--output', default=None, help='Path to save annotated video')
    parser.add_argument('--cpu', action='store_true', help='Use CPU instead of GPU for inference')
    args = parser.parse_args()
    run_video(args.model, args.video, output_path=args.output, use_gpu=not args.cpu)

if __name__ == '__main__':
    main()