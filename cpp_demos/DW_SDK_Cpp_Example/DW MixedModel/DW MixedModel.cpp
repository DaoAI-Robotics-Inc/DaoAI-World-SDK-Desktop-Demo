#include <iostream>
#include <dwsdk/model.h>
#include <dwsdk/prediction.h>
#include <dwsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>
#include <vector>
#include <algorithm>

int main()
{
    std::cout << "Start DaoAI World \"Mixed Model\" example!" << std::endl;

    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "mix_model_img.png";   // Image file path
    std::string model_path = rootpath + "mix_model.dwm";    // Model file path

    // Convert relative paths to absolute paths for easier debugging and traceability
    std::filesystem::path abs_image_path = std::filesystem::absolute(image_path);
    std::filesystem::path abs_model_path = std::filesystem::absolute(model_path);

    // Print the absolute paths of the image and model for verification
    std::cout << "Image Path: " << abs_image_path << std::endl;
    std::cout << "Model Path: " << abs_model_path << std::endl;

    try
    {
        /*
         * Step 0: Initialize the DaoAI SDK
         */
        std::cout << "Step 0: DW SDK initialize" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * Step 1: Load the image using DaoAI API
         */
        std::cout << "Step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);

        /*
         * Step 2: Load the instance segmentation model using DaoAI API
         * p.s. The model is pre-trained on DaoAI World platform.
         */
        std::cout << "Step 2: Call the DaoAI API to load the instance segmentation model" << std::endl;
        DaoAI::DeepLearning::Vision::MultilabelDetection model(model_path, DaoAI::DeepLearning::DeviceType::GPU);

        /*
         * Step 3: Use the deep learning model to make predictions on the image
         */
        std::cout << "Step 3: Use deep learning models to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::MultilabelDetectionResult prediction = model.inference(image);


        /*
         * Step 4: Print Detailed Detection Results
         */
        
         // Print detailed detection results for readability
        std::cout << "Printing detection results..." << std::endl;

        // Print Class IDs and Labels with confidence
        std::cout << "\nClass IDs and Labels:" << std::endl;
        for (size_t i = 0; i < prediction.class_ids.size(); ++i)
        {
            std::cout << "  Class ID: " << prediction.class_ids[i]
                << ", Label: " << prediction.class_labels[i]
                    << ", Confidence: " << prediction.confidences[i] <<", ";

            // find the inference result attribute
            if (!prediction.attributes[i].empty()) {
                // find the attribute with the max confident 
                auto max_kv = std::max_element(
                    prediction.attributes[i].begin(), prediction.attributes[i].end(),
                    [](auto const& a, auto const& b) {
                        return a.second < b.second;  
                    }
                );
                std::cout << "Attribute: " << max_kv->first
                    << ", score = " << max_kv->second << std::endl;
            }

        }
        // Print Bounding Boxes
        std::cout << "\nBounding Boxes:" << std::endl;
        for (const auto& box : prediction.boxes)
        {
            std::cout << "  Top-left (x1, y1): (" << box.x1() << ", " << box.y1() << "), "
                << "Bottom-right (x2, y2): (" << box.x2() << ", " << box.y2() << ")" << std::endl;

        }

        std::cout << "\nDetection results printed successfully.\n" << std::endl;

        /*
         * Step 5: Output the results
         */
        std::cout << "Step 4: Result output" << std::endl;

        // Visualize the result on the image
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);

        // Write the prediction results to a JSON file
        std::filesystem::path abs_output_json_path = std::filesystem::absolute(rootpath + "output/testMixedModel_Result.json");
        std::cout << "Writing prediction results to JSON file at: " << abs_output_json_path << std::endl;
        std::ofstream fout(abs_output_json_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        // Save the result image to a file
        std::filesystem::path abs_output_image_path = std::filesystem::absolute(rootpath + "output/testMixedModel_Result.bmp");
        std::cout << "Writing result image at: " << abs_output_image_path << std::endl;
        resultImage.save(rootpath + "output/testMixedModel_Result.bmp");

        std::cout << "Process completed successfully" << std::endl;

        system("pause");
        return 0;
    }
    catch (const std::exception&)
    {
        std::cout << "Failed to process the image!" << std::endl;
        return -1;
    }
}
