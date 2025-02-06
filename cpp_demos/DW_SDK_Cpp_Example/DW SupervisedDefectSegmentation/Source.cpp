#include <iostream>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>

int main()
{
    std::cout << "Start DaoAI World \"Supervised Defect Segmentation\" model example!" << std::endl;

    // Define the root path and file paths for the image and model
    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "supervised_defect_segmentation_img.png";   // Image file path
    std::string model_path = rootpath + "supervised_defect_segmentation_model.dwm"; // Model file path

    // Convert relative paths to absolute paths for easier debugging and traceability
    std::filesystem::path abs_image_path = std::filesystem::absolute(image_path);
    std::filesystem::path abs_model_path = std::filesystem::absolute(model_path);

    // Print the absolute paths of the image and model
    std::cout << "Image Path: " << abs_image_path << std::endl;
    std::cout << "Model Path: " << abs_model_path << std::endl;

    try
    {
        /*
         * Step 0: Initialize the SDK
         */
        std::cout << "Step 0: Initialize the DW SDK" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * Step 1: Load the image using the DaoAI API
         */
        std::cout << "Step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);

        /*
         * Step 2: Load the SupervisedDefectSegmentation model using the DaoAI API
         *
         * Note: The deep learning model should be trained and exported
         * from the DaoAI World platform before use.
         */
        std::cout << "Step 2: Call the DaoAI API to load the SupervisedDefectSegmentation model" << std::endl;
        DaoAI::DeepLearning::Vision::SupervisedDefectSegmentation model(model_path);

        /*
         * Step 3: Use the loaded model to make predictions
         */
        std::cout << "Step 3: Use the deep learning model to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::SupervisedDefectSegmentationResult prediction = model.inference(image);

        /*
         * Step 4: Print detailed detection results
         */
        std::cout << "Step 4: Print detailed detection results" << std::endl;

        // Print Masks to Polygons
        std::cout << "\nMasks to Polygons:" << std::endl;
        for (const auto& mask_pair : prediction.masks) {  // Assuming masks is a map or similar container
            const auto& key = mask_pair.first;
            const auto& mask = mask_pair.second;
            std::vector<DaoAI::DeepLearning::Polygon> polygons = mask.toPolygons();

            for (size_t i = 0; i < polygons.size(); ++i) {
                std::cout << "  " << key << " Polygon " << (i + 1) << ":" << std::endl;
                size_t max_points_to_print = 5;  // Define the maximum number of points to print
                for (size_t j = 0; j < std::min(polygons[i].points.size(), max_points_to_print); ++j) {
                    std::cout << "    Point " << (j + 1) << ": (" << polygons[i].points[j].x << ", " << polygons[i].points[j].y << ")" << std::endl;
                }
                if (polygons[i].points.size() > max_points_to_print) {
                    std::cout << "    ... and " << (polygons[i].points.size() - max_points_to_print)
                        << " more points omitted." << std::endl;
                }
            }
        }

        // Print the inference decision
        std::cout << "\nInference Decision: " << prediction.decision << std::endl;

        std::cout << "\nDetection results printed successfully." << std::endl;
        /*
         * Step 5: Output the results
         */
        std::cout << "Step 5: Output the results" << std::endl;

        // Visualize the segmentation result on the image
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);

        // Write the prediction results to a JSON file
        std::string json_output_path = rootpath + "output/testSupervisedDefectSegmentation_Result.json";
        std::string json_abs_path = std::filesystem::absolute(json_output_path).string();
        std::cout << "Writing prediction results to JSON file at: " << json_abs_path << std::endl;
        std::ofstream fout(json_output_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        // Save the visualization result as an image file
        std::string image_output_path = rootpath + "output/testSupervisedDefectSegmentation_Result.bmp";
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
