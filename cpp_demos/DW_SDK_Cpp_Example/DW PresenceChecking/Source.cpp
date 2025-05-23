#include <iostream>
#include <dwsdk/model.h>
#include <dwsdk/prediction.h>
#include <dwsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>

int main()
{
    std::cout << "Start DaoAI World \"presence checking\" model example!" << std::endl;

    // Define the root path and file paths for the image and model
    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "presence_checking_img.png";   // Image file path
    std::string model_path = rootpath + "presence_checking_model.dwm"; // Model file path

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
         * Step 2: Load the presence checking model using the DaoAI API
         *
         * Note: The deep learning model should be trained and exported
         * from the DaoAI World platform before use.
         */
        std::cout << "Step 2: Call the DaoAI API to load the presence checking model" << std::endl;
        DaoAI::DeepLearning::Vision::PresenceChecking model(model_path);

        /*
         * Step 3: Use the loaded model to make predictions
         */
        std::cout << "Step 3: Use the deep learning model to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::PresenceCheckingResult prediction = model.inference(image);

        /*
         * Step 4: Print detailed detection results
         */
        std::cout << "Step 4: Print detailed detection results" << std::endl;

        // Print Class IDs, Labels, and Confidence
        std::cout << "\nClass IDs and Labels:" << std::endl;
        for (size_t i = 0; i < prediction.class_ids.size(); ++i) {
            std::cout << "  Class ID: " << prediction.class_ids[i]
                << ", Label: " << prediction.class_labels[i]
                << ", Confidence: " << prediction.confidences[i] << std::endl;
        }

        // Print Bounding Boxes
        std::cout << "\nBounding Boxes:" << std::endl;
        for (const auto& box : prediction.boxes) {
            std::cout << "  Top-left (x1, y1): (" << box.x1() << ", " << box.y1()
                << "), Bottom-right (x2, y2): (" << box.x2() << ", " << box.y2() << ")" << std::endl;
        }

        std::cout << "\nDetection results printed successfully." << std::endl;

        /*
         * Step 5: Output the results
         */
        std::cout << "Step 5: Output the results" << std::endl;

        // Visualize the prediction results on the image
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);

        // Write the prediction results to a JSON file
        std::string json_output_path = rootpath + "output/testPresenceChecking_Result.json";
        std::string json_abs_path = std::filesystem::absolute(json_output_path).string();
        std::cout << "Writing prediction results to JSON file at: " << json_abs_path << std::endl;
        std::ofstream fout(json_output_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        // Save the visualization result as an image file
        std::string image_output_path = rootpath + "output/testPresenceChecking_Result.bmp";
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
