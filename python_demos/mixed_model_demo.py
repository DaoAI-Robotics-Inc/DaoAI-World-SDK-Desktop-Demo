import os
import re
import cv2
import time
import json
import logging
os.add_dll_directory(r"C:\Program Files\DaoAI World SDK\SDK\Windows\x64\Release\3rdparty\\")
os.add_dll_directory(r"C:\Program Files\DaoAI World SDK\SDK\Windows\x64\Release\lib\\")
import dwsdk.dwsdk as dwsdk



# ——— Logging setup ———
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def initialize_sdk():
    """Initialize the DaoAI SDK."""
    try:
        logger.info("Initializing the SDK...")
        dwsdk.initialize()
        logger.info("SDK initialized successfully.\n")
    except Exception as e:
        logger.error(f"Error during SDK initialization: {e}")
        raise

def load_model(model_path, device=dwsdk.DeviceType.CPU):
    """
    Load the Mixed (Multilabel) Detection model.
    
    Args:
        model_path (str): Path to the .dwm model file.
        device (dwsdk.DeviceType): Device to run the model on.
        
    Returns:
        model: an instance of dwsdk.MultilabelDetection
    """
    try:
        logger.info(f"Loading mixed model from: {model_path}")
        model = dwsdk.MultilabelDetection(model_path, device=device)
        logger.info("Model loaded successfully.\n")
        return model
    except Exception as e:
        logger.error(f"Error during model loading: {e}")
        raise

def load_image(image_path):
    """
    Load an image and wrap it for the SDK.
    
    Args:
        image_path (str): Path to the image file.
        
    Returns:
        dwsdk.Image or None
    """
    try:
        logger.info(f"Loading image from: {image_path}")
        bgr = cv2.imread(image_path)
        if bgr is None:
            raise ValueError(f"Cannot read image at {image_path}")
        img = dwsdk.Image(image_path)
        logger.info("Image loaded successfully.\n")
        return img
    except Exception as e:
        logger.error(f"Error during image loading: {e}")
        return None

def run_inference(model, img, confidence_threshold=0.5):
    """
    Run inference, excluding the very first warmup.
    
    Args:
        model: dwsdk.MultilabelDetection instance.
        img: dwsdk.Image
        confidence_threshold (float): detection threshold.
        
    Returns:
        prediction: result object
    """
    try:
        model.setConfidenceThreshold(confidence_threshold)
        # warmup
        model.inference(img)
        # timed run
        start = time.time()
        pred = model.inference(img)
        elapsed = time.time() - start
        logger.info(f"Inference completed in {elapsed:.3f}s\n")
        return pred
    except Exception as e:
        logger.error(f"Inference error: {e}")
        return None

def print_detection_results(pred):
    """
    Print class IDs, labels, confidences, and top attribute for each detection.
    """
    logger.info("=== Detection Results ===")
    for i, (cid, lbl, conf) in enumerate(zip(pred.class_ids, pred.class_labels, pred.confidences)):
        logger.info(f"[#{i}] ID={cid}, Label={lbl}, Conf={conf:.3f}")
        # attributes is a list of dicts
        attrs = pred.attributes[i]
        if attrs:
            key, val = max(attrs.items(), key=lambda x: x[1])
            logger.info(f"     → Top attribute: {key} ({val:.3f})")
    logger.info("")

def visualize_and_save(img, pred, out_path):
    """
    Visualize predictions on the image and save to file.
    """
    try:
        logger.info(f"Visualizing results to: {out_path}")
        vis = dwsdk.visualize(img, pred)
        vis.save(out_path)
        logger.info("Visualization saved.\n")
    except Exception as e:
        logger.error(f"Visualization error: {e}")

def save_json(pred, json_path, ann_path):
    """
    Save two JSON files: raw prediction and annotation JSON.
    """
    try:
        logger.info("Saving JSON results...")
        with open(json_path, "w") as f:
            json.dump(json.loads(pred.toJSONString()), f, indent=4)
        logger.info(f"  Prediction JSON -> {json_path}")
        with open(ann_path, "w") as f:
            json.dump(json.loads(pred.toAnnotationJSONString()), f, indent=4)
        logger.info(f"  Annotation JSON -> {ann_path}\n")
    except Exception as e:
        logger.error(f"JSON saving error: {e}")

def ensure_dirs(base="python_demos/output"):
    """
    Create output directories for images and JSON.
    """
    img_dir = os.path.join(base, "images")
    js_dir  = os.path.join(base, "json")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)
    return img_dir, js_dir

def timestamped_paths(base="python_demos/output"):
    """
    Return (img_path, json_path, ann_path) with timestamp.
    """
    now = time.strftime("%Y%m%d_%H%M%S")
    img_dir, js_dir = ensure_dirs(base)
    img_p = os.path.join(img_dir, f"mixed_model_{now}.png")
    json_p = os.path.join(js_dir,  f"mixed_model_pred_{now}.json")
    ann_p  = os.path.join(js_dir,  f"mixed_model_ann_{now}.json")
    return img_p, json_p, ann_p

def main():
    logger.info("=== Mixed Model Demo ===\n")
    # paths — adjust as needed:
    model_path = "data/mix_model.dwm"
    image_path = "data/mix_model_img.png"

    initialize_sdk()
    model = load_model(model_path)
    img   = load_image(image_path)
    if img is None:
        logger.error("Aborting: cannot load image.")
        return

    pred = run_inference(model, img, confidence_threshold=0.5)
    if pred is None:
        logger.error("Aborting: inference failed.")
        return

    print_detection_results(pred)

    img_out, json_out, ann_out = timestamped_paths("output")
    visualize_and_save(img, pred, img_out)
    save_json(pred, json_out, ann_out)

    logger.info("=== Done ===")

if __name__ == "__main__":
    main()
