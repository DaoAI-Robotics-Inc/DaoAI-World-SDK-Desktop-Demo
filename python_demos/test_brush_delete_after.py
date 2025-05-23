import os
import re
import cv2
import time
import json
import logging
import numpy as np
import dwsdk.dwsdk as dwsdk

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def initialize_sdk():
    """Initialize the DAOAI SDK."""
    dwsdk.initialize()

def load_model(model_path, device=dwsdk.DeviceType.CPU):
    """Load the supervised defect segmentation model."""
    return dwsdk.SupervisedDefectSegmentation(model_path, device=device)

def load_image(image_path):
    """Load an image into the SDK format."""
    return dwsdk.Image(image_path)

def run_inference(model, daoai_image):
    """Run inference and return the prediction."""
    _ = model.inference(daoai_image)  # Warm up
    start = time.time()
    prediction = model.inference(daoai_image)
    logger.info(f"Inference time: {(time.time() - start):.3f}s")
    return prediction

def overlay_separated_mask_on_image(image_path, prediction, output_path,
                           max_erosion=10, alpha=0.5):
    """
    1) Rasterize 'maoshua' 多边形为二值 mask；
    2) 先做腐蚀以缩小并断开粘连；
    3) 再做开运算（morphological opening）进一步分离；
    4) 统计外轮廓数量，并将分离后的 mask 半透明红色叠加到原图，保存文件。
    """
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    final_mask = np.zeros((h, w), dtype=np.uint8)

    if 'maoshua' not in prediction.masks:
        logger.warning("No 'maoshua' label found.")
        return 0

    for poly in prediction.masks['maoshua'].toPolygons():
        # 构建单多边形掩码
        single = np.zeros((h, w), dtype=np.uint8)
        pts = np.array([[int(pt.x), int(pt.y)] for pt in poly.points], dtype=np.int32)
        cv2.fillPoly(single, [pts], 255)

        # 递增腐蚀
        used_mask = single
        for eros in range(1, max_erosion+1):
            kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (eros, eros))
            eroded = cv2.erode(single, kern, iterations=1)
            cnts, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(cnts) > 1:
                used_mask = eroded

        final_mask = cv2.bitwise_or(final_mask, used_mask)

    # 可视化叠加
    overlay = img.copy()
    overlay[final_mask == 255] = (0, 0, 255)
    vis = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, vis)

    # 统计最终块数
    blobs = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    logger.info(f"Total blobs after adaptive erosion: {len(blobs)}")
    return len(blobs)


def main():
    root = os.getcwd()
    model_path = os.path.join(root, "data", "brush2.dwm")
    image_path = os.path.join(root, "data", "brush.bmp")
    output_path = os.path.join(root, "output_eroded_overlay.png")

    initialize_sdk()
    model = load_model(model_path)
    daoai_img = load_image(image_path)
    prediction = run_inference(model, daoai_img)

    count = overlay_separated_mask_on_image(image_path, prediction, output_path)
    print(f"Final blob count: {count}")

if __name__ == "__main__":
    main()
