import os
import cv2
import time
import dwsdk.dwsdk as dwsdk
import numpy as np
import concurrent.futures
from tkinter import Tk, filedialog

def select_folder_dialog(title="Select Folder"):
    """
    弹出文件夹选择对话框，并返回选择的文件夹路径。
    
    Parameters:
        title (str): 对话框标题。
        
    Returns:
        str: 选择的文件夹路径，如果未选择则为空字符串。
    """
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    folder_selected = filedialog.askdirectory(title=title)
    root.destroy()
    return folder_selected

def read_and_convert_images(folder_path):
    """
    遍历指定文件夹中的所有图片文件，读取图片、将 BGR 转换为 RGB，并构造 dwsdk.Image 对象。
    
    同时统计转换时间，并返回转换后的图片列表，每个元素为 (filename, daoai_image)。
    
    Parameters:
        folder_path (str): 包含图片的文件夹路径。
        
    Returns:
        list: 转换后的图片列表。
    """
    image_list = []
    total_conversion_time = 0.0
    image_count = 0
    valid_ext = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
    
    for filename in os.listdir(folder_path):
        if os.path.splitext(filename)[1].lower() in valid_ext:
            file_path = os.path.join(folder_path, filename)
            img = cv2.imread(file_path)
            if img is None:
                continue

            start_time = time.perf_counter()
            # 将 BGR 转换为 RGB
            rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            # 通过 numpy 数组构造 dwsdk.Image 对象
            daoai_image = dwsdk.Image.from_numpy(rgb_frame, dwsdk.Image.Type.RGB)
            end_time = time.perf_counter()

            total_conversion_time += (end_time - start_time)
            image_count += 1
            image_list.append((filename, daoai_image))
    
    if image_count > 0:
        avg_conversion_ms = (total_conversion_time / image_count) * 1000
        print(f"转换 {image_count} 张图片，总耗时 {total_conversion_time:.2f} 秒，平均转换时间: {avg_conversion_ms:.2f} ms/张")
    else:
        print("没有读取到图片！")
    return image_list

def main():
    """
    主函数：
    1. 选择包含图片的文件夹；
    2. 读取并转换图片；
    3. 初始化 SDK 和模型，并进行一次 warmup inference；
    4. 按批次进行推理，并使用并行方式生成可视化结果保存至输出文件夹。
    """
    # 选择图片文件夹
    folder_path = select_folder_dialog("请选择包含图片的文件夹")
    if not folder_path:
        print("未选择文件夹，程序退出！")
        return

    # 创建输出文件夹（保存推理后的图片）
    output_folder = os.path.join(folder_path, "output")
    os.makedirs(output_folder, exist_ok=True)

    # 模型路径和 batch 大小（请根据实际情况修改）
    model_path = r"data\work_with_opencv.dwm"
    batch_size = 16

    program_start = time.perf_counter()

    # 初始化 SDK 并加载模型
    dwsdk.initialize()
    model = dwsdk.ObjectDetection(model_path, device=dwsdk.DeviceType.GPU)
    model.setBatchSize(batch_size)

    # 预热推理：构造一个 dummy image，并重复 batch_size 次调用推理接口
    dummy_array = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_image = dwsdk.Image.from_numpy(dummy_array, dwsdk.Image.Type.RGB)
    _ = model.inferenceBatch([dummy_image] * batch_size)
    print("Warmup inference 完成。")

    # 读取并转换图片
    image_list = read_and_convert_images(folder_path)

    total_inference_time = 0.0
    total_images_inferred = 0
    batch_items = []  # 每个元素为 (filename, daoai_image)

    # 使用 ThreadPoolExecutor 并行进行 visualize（可选）
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as vis_executor:
        # 按 batch_size 处理图片
        for item in image_list:
            batch_items.append(item)
            if len(batch_items) == batch_size:
                start = time.perf_counter()
                predictions = model.inferenceBatch([img for (_, img) in batch_items])
                elapsed = (time.perf_counter() - start) * 1000  # 毫秒
                total_inference_time += elapsed
                total_images_inferred += batch_size
                print(f"推理 batch：{batch_size} 张图片，耗时 {elapsed:.2f} ms")

                # 并行生成可视化结果
                result_frames = list(vis_executor.map(lambda pair: dwsdk.visualize(pair[0], pair[1]),
                                                       zip([img for (_, img) in batch_items], predictions)))
                # 保存可视化图片
                for idx, (fname, _) in enumerate(batch_items):
                    result_img = np.array(result_frames[idx])
                    output_path = os.path.join(output_folder, f"prediction_{fname}")
                    cv2.imwrite(output_path, cv2.cvtColor(result_img, cv2.COLOR_RGBA2BGR))
                batch_items = []

        # 处理最后不足 batch_size 的图片
        if batch_items:
            dummy_needed = max(0, batch_size - len(batch_items))
            if dummy_needed > 0:
                # 构造 dummy image（尺寸以第一张图片为准，如有需要请自行调整）
                dummy_array = np.zeros((480, 640, 3), dtype=np.uint8)
                dummy_image = dwsdk.Image.from_numpy(dummy_array, dwsdk.Image.Type.RGB)
                for _ in range(dummy_needed):
                    batch_items.append(("dummy", dummy_image))
            start = time.perf_counter()
            predictions = model.inferenceBatch([img for (_, img) in batch_items])
            elapsed = (time.perf_counter() - start) * 1000
            real_count = len(batch_items) - dummy_needed
            if real_count > 0:
                total_inference_time += elapsed
                total_images_inferred += real_count
                print(f"最终 batch：实际 {real_count} 张图片，推理耗时 {elapsed:.2f} ms")
            real_items = batch_items[:real_count]
            real_predictions = predictions[:real_count]
            result_frames = list(vis_executor.map(lambda pair: dwsdk.visualize(pair[0], pair[1]),
                                                   zip([img for (_, img) in real_items], real_predictions)))
            for idx, (fname, _) in enumerate(real_items):
                result_img = np.array(result_frames[idx])
                output_path = os.path.join(output_folder, f"prediction_{fname}")
                cv2.imwrite(output_path, cv2.cvtColor(result_img, cv2.COLOR_RGBA2BGR))

    # 输出推理耗时统计信息
    if total_images_inferred > 0:
        avg_inference_time = total_inference_time / total_images_inferred
        print(f"平均每张图片推理耗时：{avg_inference_time:.2f} ms")
    else:
        print("没有图片进行推理。")

    total_runtime = time.perf_counter() - program_start
    print(f"程序总运行时间：{total_runtime:.2f} 秒")

if __name__ == '__main__':
    main()
