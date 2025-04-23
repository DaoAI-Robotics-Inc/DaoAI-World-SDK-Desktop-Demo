import os
import sys
import cv2
import numpy as np
import shutil
from pathlib import Path
import dlsdk.dlsdk as dlsdk

# 固定显示窗口大小
FIXED_WIDTH = 800
FIXED_HEIGHT = 600

# 当前缩放比例（相对于原图）
scale = 1.0

# 当前索引，全局变量
currentIndex = 0

# 全局图像（原图和用于显示的图像）
originalImage = None   # 原图
displayImage = None    # 用于显示的图像（经过缩放、居中或裁剪后）
windowName = "Annotation"

# 定义每张图的标注数据
class ImageAnnotation:
    def __init__(self, filepath):
        self.filepath = filepath            # 图像全路径
        self.isAnnotated = False            # 是否已标注（好或坏）
        self.isGood = True                  # True：好图，False：坏图
        self.finished = False               # 对于坏图：多边形是否封闭完成
        self.polygon = []                   # 坏图标注的多边形点（原图坐标，支持亚像素）

annotations = []  # 所有图像标注数据列表

def redrawImage():
    global originalImage, displayImage, scale, annotations, currentIndex
    # 根据缩放比例计算新尺寸
    newWidth = int(originalImage.shape[1] * scale)
    newHeight = int(originalImage.shape[0] * scale)
    resized = cv2.resize(originalImage, (newWidth, newHeight))

    # 创建固定大小的黑色画布
    if len(resized.shape) == 2:
        canvas = np.zeros((FIXED_HEIGHT, FIXED_WIDTH), dtype=resized.dtype)
    else:
        canvas = np.zeros((FIXED_HEIGHT, FIXED_WIDTH, resized.shape[2]), dtype=resized.dtype)

    effectiveOffsetX = 0
    effectiveOffsetY = 0
    if newWidth <= FIXED_WIDTH and newHeight <= FIXED_HEIGHT:
        # 如果缩放后图像比画布小，则居中显示
        effectiveOffsetX = (FIXED_WIDTH - newWidth) // 2
        effectiveOffsetY = (FIXED_HEIGHT - newHeight) // 2
        canvas[effectiveOffsetY:effectiveOffsetY+newHeight, effectiveOffsetX:effectiveOffsetX+newWidth] = resized
    else:
        # 如果缩放后图像超出画布，则裁剪中间部分显示
        cropX = (newWidth - FIXED_WIDTH) // 2
        cropY = (newHeight - FIXED_HEIGHT) // 2
        effectiveOffsetX = -cropX
        effectiveOffsetY = -cropY
        canvas = resized[cropY:cropY+FIXED_HEIGHT, cropX:cropX+FIXED_WIDTH].copy()

    displayImage = canvas.copy()

    # 在左上角显示标注状态文字
    ann = annotations[currentIndex]
    labelText = "Unlabeled" if not ann.isAnnotated else ("Good" if ann.isGood else "Bad")
    cv2.putText(displayImage, labelText, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)

    # 如果当前图已标为坏图并且有多边形标注，则绘制标注点和连接线
    if ann.isAnnotated and not ann.isGood and len(ann.polygon) > 0:
        pts = ann.polygon
        for i, pt in enumerate(pts):
            ptDisplay = (int(round(pt[0] * scale) + effectiveOffsetX),
                         int(round(pt[1] * scale) + effectiveOffsetY))
            cv2.circle(displayImage, ptDisplay, 3, (0, 0, 255), -1)
            if i > 0:
                prevDisplay = (int(round(pts[i-1][0] * scale) + effectiveOffsetX),
                               int(round(pts[i-1][1] * scale) + effectiveOffsetY))
                cv2.line(displayImage, prevDisplay, ptDisplay, (0, 255, 0), 2)
        # 如果标注已完成，连接最后一点与第一点
        if ann.finished and len(pts) >= 2:
            firstDisplay = (int(round(pts[0][0] * scale) + effectiveOffsetX),
                            int(round(pts[0][1] * scale) + effectiveOffsetY))
            lastDisplay = (int(round(pts[-1][0] * scale) + effectiveOffsetX),
                           int(round(pts[-1][1] * scale) + effectiveOffsetY))
            cv2.line(displayImage, lastDisplay, firstDisplay, (0, 255, 0), 2)

def onMouse(event, x, y, flags, param):
    global originalImage, scale, annotations, currentIndex, displayImage
    newWidth = int(originalImage.shape[1] * scale)
    newHeight = int(originalImage.shape[0] * scale)
    effectiveOffsetX = 0
    effectiveOffsetY = 0
    if newWidth <= FIXED_WIDTH and newHeight <= FIXED_HEIGHT:
        effectiveOffsetX = (FIXED_WIDTH - newWidth) // 2
        effectiveOffsetY = (FIXED_HEIGHT - newHeight) // 2
    else:
        effectiveOffsetX = -(newWidth - FIXED_WIDTH) // 2
        effectiveOffsetY = -(newHeight - FIXED_HEIGHT) // 2

    # 处理鼠标滚轮缩放（注意：在 Python OpenCV 中鼠标滚轮事件支持可能受平台或后端影响）
    if event == cv2.EVENT_MOUSEWHEEL:
        zoomFactor = 1.1  # 每次缩放 10%
        # 这里根据 flags 判断滚轮方向（正值缩放，负值缩小）
        if flags > 0:
            scale *= zoomFactor
        else:
            scale /= zoomFactor
        scale = max(0.1, min(scale, 10.0))
        redrawImage()
        cv2.imshow(windowName, displayImage)
        return

    # 仅对标为坏图的图像允许添加标注点
    ann = annotations[currentIndex]
    if not ann.isAnnotated or ann.isGood:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        # 如果图像未填满整个画布，点击必须在图像区域内
        if newWidth <= FIXED_WIDTH and newHeight <= FIXED_HEIGHT:
            if x < effectiveOffsetX or x > effectiveOffsetX + newWidth or y < effectiveOffsetY or y > effectiveOffsetY + newHeight:
                return
        # 将点击的显示窗口坐标转换为原图的亚像素坐标
        origX = (x - effectiveOffsetX) / scale
        origY = (y - effectiveOffsetY) / scale
        ann.polygon.append((origX, origY))
        redrawImage()
        cv2.imshow(windowName, displayImage)

def main():
    global originalImage, displayImage, scale, currentIndex, annotations

    # 1. 初始化 dlsdk 库
    dlsdk.initialize()

    # 2. 让用户输入包含图像的文件夹路径
    folderPath = input("Enter the folder path containing images: ").strip()
    if not os.path.exists(folderPath):
        print("Folder does not exist:", folderPath)
        sys.exit(-1)

    # 3. 加载文件夹内所有图像（支持 .png, .jpg, .jpeg）
    valid_exts = ['.png', '.jpg', '.jpeg']
    imagePaths = []
    for entry in os.listdir(folderPath):
        ext = os.path.splitext(entry)[1].lower()
        if ext in valid_exts:
            imagePaths.append(os.path.join(folderPath, entry))
    if not imagePaths:
        print("No images found in folder.")
        sys.exit(-1)
    imagePaths.sort()

    # 初始化每张图的标注数据
    annotations.clear()
    for path in imagePaths:
        annotations.append(ImageAnnotation(path))
    currentIndex = 0

    # 4. 启动交互式标注界面（固定窗口、缩放、亚像素标注）
    cv2.namedWindow(windowName, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(windowName, onMouse)
    exitAnnotation = False
    print("Annotation instructions:")
    print(" n: Next image")
    print(" p: Previous image")
    print(" g: Mark current image as GOOD")
    print(" b: Mark current image as BAD (use mouse left-click to add polygon points)")
    print(" r: Reset polygon for current BAD image")
    print(" f: Finish annotation (close polygon by connecting last point to first)")
    print(" q: Quit annotation")
    print(" Use mouse wheel to zoom in/out.")

    while not exitAnnotation:
        # 加载当前图像
        ann = annotations[currentIndex]
        originalImage = cv2.imread(ann.filepath)
        if originalImage is None:
            print("Failed to load image:", ann.filepath)
            currentIndex = (currentIndex + 1) % len(annotations)
            continue
        # 设置初始缩放比例，使图像在固定窗口内全部显示
        scale = min(FIXED_WIDTH / originalImage.shape[1], FIXED_HEIGHT / originalImage.shape[0])
        redrawImage()
        cv2.imshow(windowName, displayImage)
        key = cv2.waitKey(0) & 0xFF
        if key == ord('n'):  # 下一张
            currentIndex = (currentIndex + 1) % len(annotations)
        elif key == ord('p'):  # 上一张
            currentIndex = (currentIndex - 1 + len(annotations)) % len(annotations)
        elif key == ord('g'):  # 标记为 GOOD（清除多边形数据）
            ann.isAnnotated = True
            ann.isGood = True
            ann.polygon.clear()
            ann.finished = False
            redrawImage()
            cv2.imshow(windowName, displayImage)
        elif key == ord('b'):  # 标记为 BAD（后续允许添加多边形点）
            ann.isAnnotated = True
            ann.isGood = False
            ann.polygon.clear()
            ann.finished = False
            redrawImage()
            cv2.imshow(windowName, displayImage)
        elif key == ord('r'):  # 重置当前 BAD 图的多边形标注
            if not ann.isGood:
                ann.polygon.clear()
                ann.finished = False
            redrawImage()
            cv2.imshow(windowName, displayImage)
        elif key == ord('f'):  # 完成标注：至少需要两个点，然后闭合多边形
            if not ann.isGood and len(ann.polygon) >= 2:
                ann.finished = True
                print("Annotation finished for image:", ann.filepath)
                redrawImage()
                cv2.imshow(windowName, displayImage)
            else:
                print("Need at least 2 points to finish annotation.")
        elif key == ord('q'):  # 退出标注
            exitAnnotation = True

        print(f"Image {currentIndex+1}/{len(annotations)} - {ann.filepath}")

    cv2.destroyWindow(windowName)

    # 5. 保存标注结果到初始文件夹下的 "out" 目录中
    outDir = os.path.join(folderPath, "out")
    goodDir = os.path.join(outDir, "good")
    badDir = os.path.join(outDir, "bad")
    maskDir = os.path.join(outDir, "masks")
    os.makedirs(goodDir, exist_ok=True)
    os.makedirs(badDir, exist_ok=True)
    os.makedirs(maskDir, exist_ok=True)

    for ann in annotations:
        if not ann.isAnnotated:
            continue
        srcPath = ann.filepath
        filename = os.path.basename(srcPath)
        if ann.isGood:
            destPath = os.path.join(goodDir, filename)
            try:
                shutil.copyfile(srcPath, destPath)
            except Exception as e:
                print("Error copying file:", e)
        else:
            destPath = os.path.join(badDir, filename)
            try:
                shutil.copyfile(srcPath, destPath)
            except Exception as e:
                print("Error copying file:", e)
            # 生成 mask：加载灰度图
            imgGray = cv2.imread(ann.filepath, cv2.IMREAD_GRAYSCALE)
            if imgGray is None:
                print("Failed to load image for mask generation:", ann.filepath)
                continue
            mask = np.zeros_like(imgGray)
            if len(ann.polygon) == 0:
                mask[:] = 255
            else:
                # 将 polygon 点转换为 int32 类型的 numpy 数组，适用于 fillPoly
                poly = np.array([[int(round(pt[0])), int(round(pt[1]))] for pt in ann.polygon], dtype=np.int32)
                if len(poly) >= 2 and not np.array_equal(poly[0], poly[-1]):
                    poly = np.vstack([poly, poly[0]])
                cv2.fillPoly(mask, [poly], 255)
            stem = os.path.splitext(filename)[0]
            maskPath = os.path.join(maskDir, stem + "_mask.png")
            cv2.imwrite(maskPath, mask)

    print("Annotated images saved to:")
    print("  Good:", goodDir)
    print("  Bad:", badDir)
    print("  Masks:", maskDir)

    # 6. 重新读取 "out" 目录中的图像作为训练数据
    good_images = []
    bad_images = []
    masks_list = []
    for entry in os.listdir(goodDir):
        file_path = os.path.join(goodDir, entry)
        if os.path.isfile(file_path):
            good_images.append(dlsdk.Image(file_path))
    for entry in os.listdir(badDir):
        file_path = os.path.join(badDir, entry)
        if os.path.isfile(file_path):
            bad_images.append(dlsdk.Image(file_path))
    for entry in os.listdir(maskDir):
        file_path = os.path.join(maskDir, entry)
        if os.path.isfile(file_path):
            masks_list.append(dlsdk.Image(file_path))
    print(f"Re-read {len(good_images)} good images, {len(bad_images)} bad images, and {len(masks_list)} masks for training.")

    # 7. 使用重新读取的数据构建训练组件
    print("creating model instance")
    model_instance = dlsdk.UnsupervisedDefectSegmentation(device=dlsdk.DeviceType.GPU)
    model_instance.setDetectionLevel(dlsdk.DetectionLevel.PIXEL_ACCURATE)
    print("running inference")
    component = model_instance.createComponentMemory("screw", good_images, bad_images, masks_list, True)
    compFile = os.path.join(folderPath, "component_1.pth")
    component.save(compFile)
    model_instance.setBatchSize(1)
    print("Component memory saved to", compFile)

    # 8. (可选) 对所有坏图进行推理并保存结果
    if bad_images:
        for idx, img in enumerate(bad_images):
            # 推理
            result = model_instance.inference(img)
            print(f"缺陷得分 [{idx}]:", result.ai_deviation_score)
            print(f"JSON 结果 [{idx}]:", result.toAnnotationJSONString())

            # 可视化
            vis = dlsdk.visualize(img, result)

            # 构造带索引的输出路径
            output_filename = f"test_unsupervised_result_{idx}.png"
            output_path = os.path.join(folderPath, "out", output_filename)

            # 保存并打印绝对路径
            vis.save(output_path)
            print(f"Saved visualization to: {os.path.abspath(output_path)}")
            
if __name__ == '__main__':
    main()
