#include <opencv2/opencv.hpp>
#include <iostream>
#include <vector>
#include <fstream>
#include <dlsdk/model.h>

using namespace DaoAI::DeepLearning;

// Global variables
std::vector<Point> clicked_points;
std::vector<Box> drawn_boxes;
bool is_drawing = false;
Point start_point;
cv::Mat* original_image = nullptr;
Vision::AutoSegmentation* model = nullptr;
Vision::ImageEmbedding* embedding = nullptr;
const std::string window_name = "Image Viewer";
const int drag_threshold = 5;

// Save JSON result to a file
void saveResultToFile(const std::string& json_string, const std::string& image_path) {
    size_t last_slash_idx = image_path.find_last_of("/\\");
    std::string directory = (last_slash_idx == std::string::npos) ? "" : image_path.substr(0, last_slash_idx + 1);
    std::string output_path = directory + "result.json";

    std::ofstream file(output_path);
    if (file.is_open()) {
        file << json_string;
        file.close();
        std::cout << "Result saved to: " << output_path << std::endl;
    }
    else {
        std::cerr << "Error: Could not save result to " << output_path << std::endl;
    }
}

// Mouse callback function
void onMouse(int event, int x, int y, int flags, void* userdata) {
    static bool is_click_detected = false; // Track single clicks
    cv::Mat display_image = original_image->clone();

    if (event == cv::EVENT_LBUTTONDOWN) {
        is_drawing = true;
        is_click_detected = true; // Assume it's a click unless a drag is detected
        start_point = Point(x, y);
    }
    else if (event == cv::EVENT_MOUSEMOVE && is_drawing) {
        if (std::abs(x - start_point.x) > drag_threshold || std::abs(y - start_point.y) > drag_threshold) {
            is_click_detected = false; // It's a drag
            cv::rectangle(display_image, cv::Point(start_point.x, start_point.y), cv::Point(x, y), cv::Scalar(0, 255, 0), 2);
            cv::imshow(window_name, display_image);
        }
    }
    else if (event == cv::EVENT_LBUTTONUP) {
        is_drawing = false;
        Point end_point(x, y);

        if (is_click_detected) {
            clicked_points.push_back(Point(x, y, "1"));
        }
        else {
            drawn_boxes.push_back(Box(start_point, end_point));
            cv::rectangle(display_image, cv::Point(start_point.x, start_point.y), cv::Point(end_point.x, end_point.y), cv::Scalar(0, 255, 0), 2);
        }

        // Perform inference
        auto result = model->inference(*embedding, drawn_boxes, clicked_points);
        auto daoai_mask_image = result.mask.toImage();

        // Save result to file
        saveResultToFile(result.toJSONString(), *(std::string*)userdata);

        // Convert the mask to OpenCV format
        cv::Mat mask_image(daoai_mask_image.height, daoai_mask_image.width, CV_8UC1, daoai_mask_image.getData());
        mask_image = mask_image.clone();

        // Create a masked image
        cv::Mat masked_image;
        original_image->copyTo(masked_image, mask_image);

        // Blend the original and masked images
        cv::Mat blended_image;
        cv::addWeighted(*original_image, 0.3, masked_image, 0.7, 0, blended_image);

        // Display the blended image
        cv::imshow(window_name, blended_image);
    }
    else if (event == cv::EVENT_RBUTTONDOWN) {
        clicked_points.push_back(Point(x, y, "0"));

        // Perform inference with updated points
        auto result = model->inference(*embedding, drawn_boxes, clicked_points);
        auto daoai_mask_image = result.mask.toImage();

        // Save result to file
        saveResultToFile(result.toJSONString(), *(std::string*)userdata);

        // Convert the mask to OpenCV format
        cv::Mat mask_image(daoai_mask_image.height, daoai_mask_image.width, CV_8UC1, daoai_mask_image.getData());
        mask_image = mask_image.clone();

        // Create a masked image
        cv::Mat masked_image;
        original_image->copyTo(masked_image, mask_image);

        // Blend the original and masked images
        cv::Mat blended_image;
        cv::addWeighted(*original_image, 0.3, masked_image, 0.7, 0, blended_image);

        // Display the blended image
        cv::imshow(window_name, blended_image);
    }
}

int main() {
    // Initialize the deep learning environment
    DaoAI::DeepLearning::initialize();

    // Load the image
    std::string image_path = "../../../data/instance_segmentation_img.jpg"; // Change to your own path
    std::string model_path = "../../../data/auto_segment.dwm"; // Change to your own path
    cv::Mat image = cv::imread(image_path);
    if (image.empty()) {
        std::cerr << "Error: Could not load the image from " << image_path << std::endl;
        return -1;
    }
    original_image = &image;

    // Load the model and generate embeddings
    try {
        model = new Vision::AutoSegmentation(model_path, DeviceType::GPU);
        Image daoai_image(image_path);
        static auto temp_embedding = model->generateImageEmbeddings(daoai_image);
        embedding = &temp_embedding;
    }
    catch (const std::exception& e) {
        std::cerr << "Error initializing the model: " << e.what() << std::endl;
        return -1;
    }

    // Create a window to display the image
    cv::namedWindow(window_name, cv::WINDOW_AUTOSIZE);
    cv::imshow(window_name, image);

    // Set the mouse callback function
    cv::setMouseCallback(window_name, onMouse, &image_path);

    // Wait for user interaction
    while (true) {
        int key = cv::waitKey(1);
        if (key == 27) { // Exit on 'Esc' key press
            break;
        }
        else if (key == 'r' || key == 'R') { // Clear boxes and points on 'r'
            clicked_points.clear();
            drawn_boxes.clear();
            cv::imshow(window_name, *original_image); // Reset to original image
        }
    }

    // Clean up resources
    delete model;
    return 0;
}