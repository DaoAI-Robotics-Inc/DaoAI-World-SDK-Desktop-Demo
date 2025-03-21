#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <chrono>
#include <opencv2/opencv.hpp>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>

namespace fs = std::filesystem;

int main(int argc, char** argv) {
    // 如果提供了文件夹路径，则使用，否则使用默认路径
    std::string folderPath = (argc >= 2) ? argv[1] : "../../../data/work_with_opencv";

    // 创建输出文件夹，位于输入文件夹的 "output" 子目录下
    std::string outputFolder = folderPath + "/output";
    fs::create_directories(outputFolder);

    // 模型路径（请根据需要修改）
    std::string modelPath = "../../../data/work_with_opencv.dwm";

    // 初始化 SDK 并加载模型
    DaoAI::DeepLearning::initialize();
    DaoAI::DeepLearning::Vision::ObjectDetection model(modelPath);

    auto programStart = std::chrono::high_resolution_clock::now();

    // Warm-up: 使用一张 dummy 图片进行推理
    cv::Mat dummyMat = cv::Mat::zeros(480, 640, CV_8UC3);
    DaoAI::DeepLearning::Image dummyImage(480, 640,
        DaoAI::DeepLearning::Image::Type::RGB,
        static_cast<void*>(dummyMat.data));
    auto warmupStart = std::chrono::high_resolution_clock::now();
    auto dummyPrediction = model.inference(dummyImage);
    auto warmupEnd = std::chrono::high_resolution_clock::now();
    long long warmupTime = std::chrono::duration_cast<std::chrono::milliseconds>(warmupEnd - warmupStart).count();
    std::cout << "Warmup inference completed in " << warmupTime << " ms." << std::endl;

    // 读取文件夹内图片并逐张处理
    std::vector<std::string> validExt = { ".jpg", ".jpeg", ".png", ".bmp", ".tiff" };
    double totalConversionTime = 0.0;
    double totalInferenceTime = 0.0;
    int imageCount = 0;

    for (const auto& entry : fs::directory_iterator(folderPath)) {
        if (!entry.is_regular_file())
            continue;
        std::string ext = entry.path().extension().string();
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
        if (std::find(validExt.begin(), validExt.end(), ext) == validExt.end())
            continue;

        cv::Mat img = cv::imread(entry.path().string());
        if (img.empty())
            continue;

        // 从opencv 图像转换为 DaoAI Image 
        auto convStart = std::chrono::high_resolution_clock::now();
        cv::Mat rgb;
        cv::cvtColor(img, rgb, cv::COLOR_BGR2RGB);
        auto convEnd = std::chrono::high_resolution_clock::now();
        double convTime = std::chrono::duration<double>(convEnd - convStart).count();
        int height = rgb.rows, width = rgb.cols;

        DaoAI::DeepLearning::Image sdkImage(height, width,
            DaoAI::DeepLearning::Image::Type::RGB,
            static_cast<void*>(rgb.data));

        totalConversionTime += convTime;


        // 对每张图片单独推理并计时
        auto infStart = std::chrono::high_resolution_clock::now();
        auto prediction = model.inference(sdkImage);
        auto infEnd = std::chrono::high_resolution_clock::now();
        long long infTime = std::chrono::duration_cast<std::chrono::milliseconds>(infEnd - infStart).count();
        totalInferenceTime += infTime;
        imageCount++;

        std::cout << "Processed image: " << entry.path().filename().string()
            << ", inference time: " << infTime << " ms" << std::endl;

        // 使用 SDK 的 visualize 工具生成可视化结果，并保存到输出文件夹
        auto daoaiResult = DaoAI::DeepLearning::Utils::visualize(sdkImage, prediction);
        int resWidth = daoaiResult.width, resHeight = daoaiResult.height;
        auto imageType = daoaiResult.type;
        int cvType = (imageType == DaoAI::DeepLearning::Image::Type::GRAYSCALE) ? CV_8UC1 : CV_8UC3;
        cv::Mat resultMat(resHeight, resWidth, cvType, daoaiResult.getData());
        cv::Mat resultBGR;
        if (imageType == DaoAI::DeepLearning::Image::Type::RGB)
            cv::cvtColor(resultMat, resultBGR, cv::COLOR_RGB2BGR);
        else if (imageType == DaoAI::DeepLearning::Image::Type::BGR)
            resultBGR = resultMat;
        else if (imageType == DaoAI::DeepLearning::Image::Type::GRAYSCALE)
            cv::cvtColor(resultMat, resultBGR, cv::COLOR_GRAY2BGR);
        else
            resultBGR = resultMat;

        std::string outPath = outputFolder + "/prediction_" + entry.path().filename().string();
        cv::imwrite(outPath, resultBGR);
    }

    if (imageCount > 0) {
        double avgConvMs = (totalConversionTime / imageCount) * 1000;
        double avgInfMs = totalInferenceTime / imageCount;
        std::cout << "Processed " << imageCount << " images." << std::endl;
        std::cout << "Total conversion time: " << totalConversionTime << " s, average: "
            << avgConvMs << " ms/image" << std::endl;
        std::cout << "Total inference time: " << totalInferenceTime << " ms, average: "
            << avgInfMs << " ms/image" << std::endl;
    }
    else {
        std::cout << "No images were read!" << std::endl;
    }

    auto programEnd = std::chrono::high_resolution_clock::now();
    auto totalRuntime = std::chrono::duration_cast<std::chrono::seconds>(programEnd - programStart).count();
    std::cout << "Total program runtime: " << totalRuntime << " seconds" << std::endl;

    return 0;
}
