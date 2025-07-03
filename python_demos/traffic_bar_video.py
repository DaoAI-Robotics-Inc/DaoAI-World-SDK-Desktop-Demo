import os
import cv2
import time
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import dwsdk.dwsdk as dwsdk

# -------------------- 配置 --------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# 全局用于存储 ROI 顶点
roi_points = []

# 英文标签到中文标签的映射
label_map = {
    "bar":    "栏杆",
    "car":    "汽车",
    "truck":  "卡车",
    "person": "行人",
    "staff":  "工作人员"
}
classes = set(label_map.keys())

# Pillow 中文字体
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_SIZE = 24
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

# -------------------- ROI 绘制 --------------------
def draw_roi(event, x, y, flags, param):
    """鼠标回调：左键添加顶点"""
    global roi_points
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points.append((x, y))
        cv2.circle(param, (x, y), 3, (0, 0, 255), -1)
        if len(roi_points) > 1:
            cv2.line(param, roi_points[-2], roi_points[-1], (0, 0, 255), 2)

def get_roi(frame):
    """
    让用户在第一帧上用鼠标绘制多边形 ROI，
    按 's' 键完成绘制并关闭窗口。
    """
    tmp = frame.copy()
    cv2.namedWindow("Draw ROI - 点击添加顶点，按 's' 保存")
    cv2.setMouseCallback("Draw ROI - 点击添加顶点，按 's' 保存", draw_roi, tmp)
    while True:
        disp = tmp.copy()
        if len(roi_points) >= 3:
            cv2.polylines(disp, [np.array(roi_points, np.int32)], isClosed=True, color=(0,255,0), thickness=2)
        cv2.imshow("Draw ROI - 点击添加顶点，按 's' 保存", disp)
        if cv2.waitKey(1) == ord('s'):
            break
    cv2.destroyAllWindows()
    return roi_points

# -------------------- SDK 初始化与模型加载 --------------------
def initialize_sdk():
    try:
        dwsdk.initialize()
        logger.info("SDK 初始化成功。")
    except Exception as e:
        logger.error(f"SDK 初始化失败: {e}", exc_info=True)
        raise

def load_model(model_path, device=dwsdk.DeviceType.CPU):
    try:
        model = dwsdk.ObjectDetection(model_path, device=device)
        logger.info(f"模型加载成功: {model_path}")
        return model
    except Exception as e:
        logger.error(f"模型加载失败: {e}", exc_info=True)
        raise

# -------------------- 帧上绘制中文文本 --------------------
def draw_chinese_text(frame, texts):
    """
    texts: list of tuples (text, (x, y), color)
    """
    # 转为 PIL Image
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    for text, (x, y), color in texts:
        draw.text((x, y), text, font=font, fill=color)
    # 转回 OpenCV BGR
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# -------------------- 视频处理 --------------------
def process_video(
    video_path,
    model,
    output_path="out.mp4",
    save_frames_dir=None,
    num_save_frames=0,
    confidence_threshold=0.5,
    log_interval=50
):
    # 若指定保存目录，则创建
    if save_frames_dir:
        os.makedirs(save_frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"无法打开视频: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info(f"视频已打开: {total_frames} 帧, {fps:.2f} FPS, 分辨率 {width}x{height}")

    # 读取第一帧，绘制 ROI
    ret, first_frame = cap.read()
    if not ret:
        logger.error("无法读取第一帧用于 ROI 绘制")
        return
    roi = get_roi(first_frame)

    # 准备视频写出
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    barrier_up  = False
    start_frame = None
    frame_idx   = 0

    # 写出第一帧
    out.write(first_frame)
    frame_idx = 1

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.info("视频播放结束")
            break

        # SDK 推理
        try:
            daoai_image = dwsdk.Image.from_numpy(frame, dwsdk.Image.Type.RGB)
            model.setConfidenceThreshold(confidence_threshold)
            pred = model.inference(daoai_image)
        except Exception as e:
            logger.error(f"第 {frame_idx} 帧推理失败: {e}", exc_info=True)
            out.write(frame)
            frame_idx += 1
            continue

        current_barrier_up = False
        draw_texts = []

        # 遍历检测结果
        for box, label, conf in zip(pred.boxes, pred.class_labels, pred.confidences):
            lbl = label.lower()
            if lbl not in classes:
                continue

            x1, y1 = int(box.x1()), int(box.y1())
            x2, y2 = int(box.x2()), int(box.y2())
            cx, cy = (x1 + x2)//2, (y1 + y2)//2
            # 仅在 ROI 内可视化
            if cv2.pointPolygonTest(np.array(roi, np.int32), (cx, cy), False) < 0:
                continue

            # 绘制矩形框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 准备中文标签文本
            ch_label = label_map[lbl]
            text = f"{ch_label}:{conf:.2f}"
            draw_texts.append((text, (x1, y1 - FONT_SIZE - 5), (0, 255, 0)))

            # 栏杆状态判断
            if lbl == "bar":
                w, h = x2 - x1, y2 - y1
                if h > w * 1.2:
                    current_barrier_up = True

        # 栏杆计时逻辑
        if current_barrier_up and not barrier_up:
            barrier_up  = True
            start_frame = frame_idx
            logger.info(f"栏杆抬起 at 帧 {frame_idx}")
        elif not current_barrier_up and barrier_up:
            barrier_up = False
            logger.info(f"栏杆放下 at 帧 {frame_idx}")
            start_frame = None

        if barrier_up and start_frame is not None:
            elapsed = (frame_idx - start_frame) / fps
            text = f"抬起时长: {elapsed:.1f}秒"
            draw_texts.append((text, (50, 50), (255, 0, 0)))

        # 用 Pillow 绘制所有中文文本
        frame = draw_chinese_text(frame, draw_texts)

        # 可选：保存前 N 帧
        if save_frames_dir and frame_idx <= num_save_frames:
            save_path = os.path.join(save_frames_dir, f"processed_{frame_idx:03d}.jpg")
            cv2.imwrite(save_path, frame)
            logger.info(f"保存第 {frame_idx} 帧到 {save_path}")

        # 定期打印进度
        if frame_idx % log_interval == 0:
            pct = frame_idx / total_frames * 100
            logger.info(f"Processing {frame_idx}/{total_frames} ({pct:.1f}%)")

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    logger.info(f"处理完成，视频已保存到 {output_path}")

# -------------------- 脚本入口 --------------------
if __name__ == "__main__":
    MODEL_PATH      = r"C:\Users\daoai\Downloads\traffic_test\traffic_bar3.dwm"
    VIDEO_PATH      = r"C:\Users\daoai\Downloads\traffic_test\traffic_personel.mp4"
    OUTPUT_PATH     = r"C:\Users\daoai\Downloads\traffic_test\out.mp4"
    SAVE_FRAMES_DIR = r"C:\Users\daoai\Downloads\traffic_test\out"
    NUM_SAVE_FRAMES = 1
    CONF_THRESH     = 0.97
    LOG_INTERVAL    = 50

    initialize_sdk()
    model = load_model(MODEL_PATH, device=dwsdk.DeviceType.GPU)
    process_video(
        video_path=VIDEO_PATH,
        model=model,
        output_path=OUTPUT_PATH,
        save_frames_dir=SAVE_FRAMES_DIR,
        num_save_frames=NUM_SAVE_FRAMES,
        confidence_threshold=CONF_THRESH,
        log_interval=LOG_INTERVAL
    )
