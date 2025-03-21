#include <iostream>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>

int main()
{
    std::cout << "Start DaoAI World \"keypoint detection\" model example!" << std::endl;

    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "keypoint_detection_img.png";   // Image file path
    std::string model_path = rootpath + "keypoint_detection_model.dwm"; // Model file path
     // Convert relative paths to absolute paths
    std::filesystem::path abs_image_path = std::filesystem::absolute(image_path);
    std::filesystem::path abs_model_path = std::filesystem::absolute(model_path);

    // Print the absolute paths
    std::cout << "Image Path: " << abs_image_path << std::endl;
    std::cout << "Model Path: " << abs_model_path << std::endl;
    try
    {
        /*
         * Step 0: Initialize the SDK
         */
        std::cout << "Step 0: DW SDK initialization" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * Step 1: Load the image using DaoAI API
         */
        std::cout << "Step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);

        /*
         * Step 2: Load the keypoint detection model using DaoAI API
         *
         * Note: The deep learning model should be trained and exported
         * from the DaoAI World platform.
         */
        std::cout << "Step 2: Call the DaoAI API to load the keypoint detection model" << std::endl;
        DaoAI::DeepLearning::Vision::KeypointDetection model(model_path, DaoAI::DeepLearning::DeviceType::GPU);

        /*
         * Step 3: Use the loaded model to make predictions
         */
        std::cout << "Step 3: Use the deep learning model to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::KeypointDetectionResult prediction = model.inference(image);

        /*
         * Step 3.1: Log detailed detection results
         */
        std::cout << "Step 3.1: Print detailed detection results" << std::endl;

        // Print class IDs, labels, and confidences
        std::cout << "\nClass IDs and Labels:" << std::endl;
        for (size_t i = 0; i < prediction.class_ids.size(); ++i) {
            std::cout << "  Class ID: " << prediction.class_ids[i]
                << ", Label: " << prediction.class_labels[i]
                << ", Confidence: " << prediction.confidences[i] << std::endl;
        }

        // Print bounding boxes
        std::cout << "\nBounding Boxes:" << std::endl;
        for (const auto& box : prediction.boxes) {
            std::cout << "  Top-left (x1, y1): (" << box.x1() << ", " << box.y1()
                << "), Bottom-right (x2, y2): (" << box.x2() << ", " << box.y2() << ")" << std::endl;
        }

        // Print masks converted to polygons
        size_t max_points_to_print = 3; // Limit polygon points for readability
        std::cout << "\nMasks to Polygons:" << std::endl;
        for (const auto& mask : prediction.masks) {
            auto polygons = mask.toPolygons();
            for (size_t i = 0; i < polygons.size(); ++i) {
                std::cout << "  Polygon " << i + 1 << ":" << std::endl;
                for (size_t j = 0; j < std::min(polygons[i].points.size(), max_points_to_print); ++j) {
                    const auto& point = polygons[i].points[j];
                    std::cout << "    Point " << j + 1 << ": (" << point.x << ", " << point.y << ")" << std::endl;
                }
                if (polygons[i].points.size() > max_points_to_print) {
                    std::cout << "    ... and " << polygons[i].points.size() - max_points_to_print
                        << " more points omitted." << std::endl;
                }
            }
        }

        // Print keypoints
        std::cout << "\nKeypoints:" << std::endl;
        for (size_t obj_index = 0; obj_index < prediction.keypoints.size(); ++obj_index) {
            std::cout << "  Keypoints for Object " << obj_index + 1 << ":" << std::endl;
            for (size_t kp_index = 0; kp_index < prediction.keypoints[obj_index].size(); ++kp_index) {
                const auto& keypoint = prediction.keypoints[obj_index][kp_index];
                std::cout << "    Keypoint " << kp_index + 1 << ": (x: " << keypoint.x
                    << ", y: " << keypoint.y << ")" << std::endl;
            }
        }

        std::cout << "\nDetailed detection results printed successfully." << std::endl;

        /*
         * Step 4: Output the results
         */
        std::cout << "Step 4: Result output" << std::endl;

        // Visualize the prediction results on the image
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);

        // Write the prediction results to a JSON file
        std::string json_output_path = rootpath + "output/testKeypointDetection_Result.json";
        std::string json_abs_path = std::filesystem::absolute(json_output_path).string();
        std::cout << "Writing prediction results to JSON file at: " << json_abs_path << std::endl;
        std::ofstream fout(json_output_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        // Save the visualization result as an image file
        std::string image_output_path = rootpath + "output/testKeypointDetection_Result.bmp";
        std::string image_abs_path = std::filesystem::absolute(image_output_path).string();
        std::cout << "Writing result image to: " << image_abs_path << std::endl;
        resultImage.save(image_output_path);

        std::cout << "Process completed successfully" << std::endl;

        system("pause");
        return 0;
    }
    catch (const std::exception&)
    {
        std::cout << "Failed to complete the process!" << std::endl;
        return -1;
    }
}
