#include <iostream>
#include <dwsdk/model.h>
#include <dwsdk/prediction.h>
#include <dwsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>

int main()
{
    std::cout << "Start DaoAI World \"image classification\" model example !" << std::endl;

    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "classification_img.png";   // Image file path
    std::string model_path = rootpath + "classification_model.dwm"; // Model file path
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
        std::cout << "Step 0: Initialize the DW SDK" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * Step 1: Load the image using DaoAI API
         */
        std::cout << "Step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);

        /*
         * Step 2: Load the Image Classification model using DaoAI API
         *
         * Note: The deep learning model should be trained and exported from
         * the DaoAI World platform.
         */
        std::cout << "Step 2: Call the DaoAI API to load the Image Classification model" << std::endl;
        DaoAI::DeepLearning::Vision::Classification model(model_path);

        /*
         * Step 3: Use the loaded model to make predictions
         */
        std::cout << "Step 3: Use the deep learning model to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::ClassificationResult prediction = model.inference(image);


        /*
         * Step 3.1: Access prediction and print to console
         */
        std::cout << "Accessing prediction results..." << std::endl;

        float highest_confidence = 0.0f;
        std::string classification_result;

        // Iterate through the predictions
        std::cout << "\nClass Labels and Confidence:" << std::endl;
        for (size_t i = 0; i < prediction.flags.size(); ++i)
        {
            const auto& flag = prediction.flags[i];

            // Print details of each detection
            std::cout << "  Detection " << (i + 1) << ":" << std::endl;
            std::cout << "    Label: " << flag.label << ", Confidence: " << flag.confidence << std::endl;

            // Update the highest confidence and corresponding label
            if (flag.confidence > highest_confidence)
            {
                highest_confidence = flag.confidence;
                classification_result = flag.label;
            }
        }

        // Print the classification result with the highest confidence
        std::cout << "\nClassification Result:" << std::endl;
        std::cout << "  Label: " << classification_result << ", Confidence: " << highest_confidence << std::endl;

        std::cout << "\nPrediction results processed successfully.\n" << std::endl;
        

        // Write the prediction result to a JSON file
        std::string json_output_path = rootpath + "output/ImageClassification_result.json";
        std::string json_abs_path = std::filesystem::absolute(json_output_path).string();
        std::cout << "Writing prediction result to JSON file at: " << json_abs_path << std::endl;
        std::ofstream fout(json_output_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        std::cout << "Finished successfully" << std::endl;

        system("pause");
        return 0;
    }
    catch (const std::exception&)
    {
        std::cout << "Failed to complete the process!" << std::endl;
        return -1;
    }
}
