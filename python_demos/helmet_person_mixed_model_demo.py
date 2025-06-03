import os
import re
import time
import json
import logging
import cv2
import dwsdk.dwsdk as dwsdk

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


def initialize_sdk():
    """Initialize DaoAI World SDK."""
    try:
        logger.info("Initializing SDK...")
        dwsdk.initialize()
        logger.info("SDK initialized.\n")
    except Exception as e:
        logger.error(f"SDK initialization failed: {e}")
        raise


def load_model(model_path, device=dwsdk.DeviceType.CPU):
    """Load a mixed (multilabel) detection model."""
    try:
        logger.info(f"Loading model from: {model_path}")
        model = dwsdk.MultilabelDetection(model_path, device=device)
        logger.info("Model loaded.\n")
        return model
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise


def load_image(image_path):
    """Load an image using OpenCV and wrap it for the SDK."""
    try:
        logger.info(f"Loading image from: {image_path}")
        if cv2.imread(image_path) is None:
            raise ValueError(f"Cannot read image at {image_path}")
        img = dwsdk.Image(image_path)
        logger.info("Image loaded.\n")
        return img
    except Exception as e:
        logger.error(f"Image loading failed: {e}")
        return None


def run_inference(model, img, confidence=0.5):
    """Run inference with the given confidence threshold."""
    try:
        model.setConfidenceThreshold(confidence)
        model.inference(img)  # warmup
        start = time.time()
        pred = model.inference(img)
        logger.info(f"Inference done in {time.time() - start:.3f}s\n")
        return pred
    except Exception as e:
        logger.error(f"Inference error: {e}")
        return None


def filter_results(pred, allowed_labels):
    """Return indices of detections whose label is in allowed_labels."""
    indices = [i for i, lbl in enumerate(pred.class_labels) if lbl in allowed_labels]
    return indices


def print_filtered_results(pred, indices):
    logger.info("=== Helmet & Person Detections ===")
    for i in indices:
        cid = pred.class_ids[i]
        lbl = pred.class_labels[i]
        conf = pred.confidences[i]
        logger.info(f"ID={cid}, Label={lbl}, Confidence={conf:.3f}")
    logger.info("")


def visualize_and_save(img, pred, indices, out_path):
    """Visualize selected detections and save the image."""
    try:
        mask = [False] * len(pred.class_ids)
        for i in indices:
            mask[i] = True
        pred.setMask(mask)
        vis = dwsdk.visualize(img, pred)
        vis.save(out_path)
        logger.info(f"Visualization saved to: {out_path}\n")
    except Exception as e:
        logger.error(f"Visualization error: {e}")


def save_json(pred, indices, json_path):
    """Save filtered detections to JSON."""
    try:
        filtered = pred.filter(indices)
        with open(json_path, "w") as f:
            json.dump(json.loads(filtered.toJSONString()), f, indent=4)
        logger.info(f"JSON saved to: {json_path}\n")
    except Exception as e:
        logger.error(f"JSON saving error: {e}")


def ensure_dirs(base="python_demos/output"):
    img_dir = os.path.join(base, "images")
    json_dir = os.path.join(base, "json")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    return img_dir, json_dir


def timestamped_paths(base="python_demos/output"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    img_dir, js_dir = ensure_dirs(base)
    img_path = os.path.join(img_dir, f"helmet_person_{ts}.png")
    js_path = os.path.join(js_dir, f"helmet_person_{ts}.json")
    return img_path, js_path


def main():
    logger.info("=== Helmet & Person Mixed Model Demo ===\n")
    model_path = "data/mix_model.dwm"
    image_path = "data/mix_model_img.png"

    initialize_sdk()
    model = load_model(model_path)
    img = load_image(image_path)
    if img is None:
        return

    pred = run_inference(model, img, confidence=0.5)
    if pred is None:
        return

    target_labels = {"helmet", "person"}
    indices = filter_results(pred, target_labels)
    print_filtered_results(pred, indices)

    img_out, json_out = timestamped_paths("output")
    visualize_and_save(img, pred, indices, img_out)
    save_json(pred, indices, json_out)

    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
