#include <iostream>
#include <fstream>
#include <cstring>
#include <filesystem>
#include <algorithm>
#include <vector>
#include <stdexcept>
#include <opencv2/opencv.hpp>

// DaoAI 深度学习相关头文件
#include <inference_client/common.h>
#include <inference_client/model.h>

// 使用 DaoAI 命名空间
using namespace DaoAI::DeepLearning;
using namespace DaoAI::DeepLearning::Vision;

// ----------------------------
// Base64 编码函数实现
// ----------------------------
static const std::string base64_chars =
"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
"abcdefghijklmnopqrstuvwxyz"
"0123456789+/";

std::string base64Encode(const std::string& in) {
    std::string out;
    int val = 0, valb = -6;
    for (unsigned char c : in) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            out.push_back(base64_chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6)
        out.push_back(base64_chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (out.size() % 4)
        out.push_back('=');
    return out;
}

// ----------------------------
// 函数：读取图片并返回 Base64 字符串
// ----------------------------
std::string loadImageAsBase64(const std::string& imagePath) {
    cv::Mat img = cv::imread(imagePath, cv::IMREAD_COLOR);
    if (img.empty()) {
        throw std::runtime_error("Could not open or find the image: " + imagePath);
    }
    std::vector<uchar> buffer;
    // 使用 PNG 格式编码图片
    cv::imencode(".png", img, buffer);
    std::string buffer_string(reinterpret_cast<const char*>(buffer.data()), buffer.size());
    return base64Encode(buffer_string);
}

// ----------------------------
// 函数：利用 OpenCV 绘制检测结果并保存图像
// ----------------------------
void visualizeAndSaveResult(const cv::Mat& img, const InstanceSegmentationResult& result, const std::string& outputPath) {
    cv::Mat visImage = img.clone();
    for (int i = 0; i < result.num_detections; ++i) {
        // 绘制边界框
        cv::rectangle(visImage,
            cv::Point(result.boxes[i].x1(), result.boxes[i].y1()),
            cv::Point(result.boxes[i].x2(), result.boxes[i].y2()),
            cv::Scalar(0, 255, 0), 2);

        // 构造类别和置信度文本
        std::string label = result.class_labels[i] + " " + std::to_string(result.confidences[i]);
        int baseLine = 0;
        cv::Size labelSize = cv::getTextSize(label, cv::FONT_HERSHEY_SIMPLEX, 0.5, 1, &baseLine);
        // 注意：result.boxes[i].y1() 可能是 float 类型，需转换为 int
        int boxY1 = static_cast<int>(result.boxes[i].y1());
        int top = boxY1;
        if (labelSize.height > top)
        {
            top = labelSize.height;
        }
        // 绘制文本背景
        cv::rectangle(visImage,
            cv::Point(result.boxes[i].x1(), top - labelSize.height),
            cv::Point(result.boxes[i].x1() + labelSize.width, top + baseLine),
            cv::Scalar(0, 255, 0), cv::FILLED);
        // 绘制文本
        cv::putText(visImage, label, cv::Point(result.boxes[i].x1(), top),
            cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 0, 0), 1);
    }
    // 保存绘制结果图像
    cv::imwrite(outputPath, visImage);
}

int main()
{
    std::cout << "Start DaoAI World \"instance segmentation\" model example!" << std::endl;

    // 设置数据所在的根目录和文件路径
    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "instance_segmentation_img.jpg";   // 图像文件路径
    std::string model_path = rootpath + "instance_segmentation_model.dwm";   // 模型文件路径

    // 转换为绝对路径，便于调试
    std::filesystem::path abs_image_path = std::filesystem::absolute(image_path);
    std::filesystem::path abs_model_path = std::filesystem::absolute(model_path);

    std::cout << "Image Path: " << abs_image_path << std::endl;
    std::cout << "Model Path: " << abs_model_path << std::endl;

    try
    {
        // ================================
        // Step 1: 读取图片并转换为 Base64 字符串
        // ================================
        std::cout << "Step 1: Load image and convert to Base64" << std::endl;
        std::string encodedImage = loadImageAsBase64(abs_image_path.string());

        // 同时利用 OpenCV 读取原图，用于后续可视化
        cv::Mat originalImage = cv::imread(abs_image_path.string(), cv::IMREAD_COLOR);
        if (originalImage.empty()) {
            throw std::runtime_error("Failed to load image for visualization.");
        }

        // ================================
        // Step 2: 加载实例分割模型
        // ================================
        std::cout << "Step 2: Load instance segmentation model" << std::endl;
        // 使用 GPU 设备加载模型（也可改为 DeviceType::CPU）
        InstanceSegmentation model(abs_model_path.string(), DeviceType::GPU);

        // ================================
        // Step 3: 模型推理
        // ================================
        std::cout << "Step 3: Run inference on the image" << std::endl;
        // 调用模型的 inference 方法，传入 Base64 编码后的图像字符串
        InstanceSegmentationResult result = model.inference(encodedImage);

        // ================================
        // Step 4: 打印检测结果（对象数、类别、边界框、关键点）
        // ================================
        std::cout << "\nDetected Objects: " << result.num_detections << "\n";
        for (int i = 0; i < result.num_detections; ++i)
        {
            std::cout << "Object " << (i + 1) << "\n";
            std::cout << "Class: " << result.class_labels[i] << "\n";
            std::cout << "Bounding box: " << result.boxes[i].x1() << " "
                << result.boxes[i].y1() << " "
                << result.boxes[i].x2() << " "
                << result.boxes[i].y2() << "\n";
            std::cout << "Confidence: " << result.confidences[i] << "\n";
            std::cout << "\n";
        }

        // ================================
        // Step 5: 使用 OpenCV 绘制检测结果并保存可视化图片
        // ================================
        std::cout << "Step 5: Visualizing results with OpenCV..." << std::endl;
        std::string outputPath = std::filesystem::absolute("result_image.jpg").string();
        visualizeAndSaveResult(originalImage, result, outputPath);
        std::cout << "Result image saved to: " << outputPath << std::endl;

        std::cout << "Press any key to close the window..." << std::endl;
        system("pause");
        return 0;
    }
    catch (const std::exception& ex)
    {
        std::cout << "Error: " << ex.what() << std::endl;
        return -1;
    }
}
