import os
import sys
import re
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
    """初始化 SDK."""
    try:
        logger.info("Initializing the SDK...")
        dwsdk.initialize()
        logger.info("SDK initialized successfully.\n")
    except Exception as e:
        logger.error(f"Error during SDK initialization: {e}")
        raise

def load_model(model_path, device=dwsdk.DeviceType.CPU):
    """加载 Rotated Object Detection 模型."""
    try:
        logger.info(f"Loading rotated object detection model from: {model_path}")
        model = dwsdk.RotatedObjectDetection(model_path, device=device)
        logger.info("Model loaded successfully.\n")
        return model
    except Exception as e:
        logger.error(f"Error during model loading: {e}")
        raise

def load_image(image_path):
    """加载图片为 SDK 支持的格式."""
    try:
        logger.info(f"Loading image from: {image_path}")
        img = dwsdk.Image(image_path)
        assert isinstance(img, dwsdk.Image)
        logger.info("Image loaded successfully.\n")
        return img
    except Exception as e:
        logger.error(f"Error during image loading: {e}")
        return None

def run_inference(model, daoai_image, confidence_threshold=0.5):
    """执行推理并返回预测结果."""
    try:
        logger.info(f"Running inference with confidence threshold: {confidence_threshold}")
        model.setConfidenceThreshold(confidence_threshold)

        # 首次推理仅加载模型，不计时
        _ = model.inference(daoai_image)

        start = time.time()
        prediction = model.inference(daoai_image)
        elapsed = (time.time() - start) * 1000
        logger.info(f"Inference completed in {elapsed:.1f} ms.\n")
        return prediction
    except Exception as e:
        logger.error(f"Error during inference: {e}")
        return None

def print_detection_results(prediction):
    """打印带角度信息的检测结果."""
    logger.info("=== Detection Results ===")
    # 类别与置信度
    for cid, label, conf in zip(prediction.class_ids, prediction.class_labels, prediction.confidences):
        logger.info(f"Class ID: {cid}, Label: {label}, Confidence: {conf:.2f}")
    # 旋转框
    logger.info("\nRotated Boxes:")
    for box in prediction.boxes:
        logger.info(
            f"  x1,y1=({box.x1():.1f},{box.y1():.1f})  "
            f"x2,y2=({box.x2():.1f},{box.y2():.1f})  "
            f"Angle={box.angle():.1f}"
        )
    logger.info("=========================\n")

def create_output_dirs(base_dir="output"):
    """创建输出目录."""
    os.makedirs(base_dir, exist_ok=True)
    img_dir = os.path.join(base_dir, "images")
    json_dir = os.path.join(base_dir, "json")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    return img_dir, json_dir

def generate_output_paths(base_dir="output"):
    """生成带时间戳的输出文件路径."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    img_dir, json_dir = create_output_dirs(base_dir)
    img_out = os.path.join(img_dir, f"rotated_od_{ts}.png")
    json_out = os.path.join(json_dir, f"rotated_od_{ts}.json")
    return img_out, json_out

def visualize_and_save(daoai_image, prediction, out_image):
    """可视化并保存检测结果图."""
    try:
        logger.info(f"Visualizing and saving to {out_image}")
        vis = dwsdk.visualize(daoai_image, prediction)
        vis.save(out_image)
        logger.info("Visualization saved.\n")
    except Exception as e:
        logger.error(f"Error during visualization: {e}")

def save_json(prediction, out_json):
    """保存原始 JSON 结果."""
    try:
        logger.info(f"Writing JSON results to {out_json}")
        with open(out_json, "w") as f:
            json.dump(json.loads(prediction.toJSONString()), f, indent=4)
        logger.info("JSON saved.\n")
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")

def main():
    logger.info("=== Rotated Object Detection Demo ===\n")

    # TODO: 根据实际情况修改下面路径
    model_path = r"data/rotated_object_detection_model.dwm"
    image_path = r"data/rotated_object_detection_img.png"

    initialize_sdk()

    model = load_model(model_path, device=dwsdk.DeviceType.CPU)
    daoai_img = load_image(image_path)
    if daoai_img is None:
        return

    prediction = run_inference(model, daoai_img, confidence_threshold=0.5)
    if prediction is None:
        return

    print_detection_results(prediction)

    img_out, json_out = generate_output_paths("python_demos/output")
    visualize_and_save(daoai_img, prediction, img_out)
    save_json(prediction, json_out)

    logger.info("=== Demo Completed ===")

if __name__ == "__main__":
    main()
