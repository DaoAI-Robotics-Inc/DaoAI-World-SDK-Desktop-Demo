#include <iostream>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>
#include <fstream>
#include <cstring>
#include <filesystem>
#include <vector>

int main()
{
    std::cout << "Start DaoAI World \"OCR\" model example!" << std::endl;

    std::string rootpath = "../../../data/";
    std::string image_path = rootpath + "ocr_img.png";   // Image file path
    std::string model_path = rootpath + "ocr_model.dwm"; // Model file path

    // Convert relative paths to absolute paths for easier debugging and traceability
    std::filesystem::path abs_image_path = std::filesystem::absolute(image_path);
    std::filesystem::path abs_model_path = std::filesystem::absolute(model_path);

    // Print the absolute paths of the image and model for verification
    std::cout << "Image Path: " << abs_image_path << std::endl;
    std::cout << "Model Path: " << abs_model_path << std::endl;

    try
    {
        /*
         * Step 0: Initialize the SDK
         */
        std::cout << "Step 0: DW SDK initialize" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * Step 1: Load the input image using DaoAI API
         */
        std::cout << "Step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);

        /*
         * Step 2: Load the OCR model using DaoAI API
         * Note: The model used for this task is pre-trained on DaoAI World platform.
         */
        std::cout << "Step 2: Call the DaoAI API to load the OCR model" << std::endl;
        DaoAI::DeepLearning::Vision::OCR model(model_path);

        /*
         * Step 3: Use the model to make predictions on the input image
         */
        std::cout << "Step 3: Use OCR model to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::OCRResult prediction = model.inference(image);

        /*
         * Step 4: Print Detailed Detection Results
         */
        std::cout << "\nStep 4: Print Detailed Detection Results" << std::endl;

        // Print detected texts and their confidence scores
        std::cout << "\nDetected Texts and Confidence Scores:" << std::endl;
        for (size_t i = 0; i < prediction.texts.size(); ++i)
        {
            std::cout << "  Text: \"" << prediction.texts[i]
                << "\", Confidence: " << prediction.confidences[i] << std::endl;
        }

        // Print bounding boxes with their points
        std::cout << "\nBounding Boxes for Detected Texts:" << std::endl;
        for (size_t i = 0; i < prediction.boxes.size(); ++i)
        {
            const auto& box = prediction.boxes[i];
            std::cout << "  Text Bounding Box " << i + 1 << ":" << std::endl;
            for (size_t j = 0; j < box.points.size(); ++j)
            {
                std::cout << "    Point " << j + 1 << ": (" << box.points[j].x << ", " << box.points[j].y << ")" << std::endl;
            }
        }

        std::cout << "\nDetection results printed successfully.\n" << std::endl;

        /*
         * Step 5: Output the results
         */
        std::cout << "Step 5: Result output" << std::endl;

        // Visualize the prediction results on the input image
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);
         
        // Write the prediction results to a JSON file for further inspection
        std::filesystem::path abs_output_json_path = std::filesystem::absolute(rootpath + "output/testOCR_Result.json");
        std::cout << "Writing prediction results to JSON file at: " << abs_output_json_path << std::endl;
        std::ofstream fout(abs_output_json_path);
        fout << prediction.toJSONString() << "\n";
        fout.close();

        // Save the result image with visualized segmentation to a file
        std::filesystem::path abs_output_image_path = std::filesystem::absolute(rootpath + "output/testOCR_Result.bmp");
        std::cout << "Writing result image at: " << abs_output_image_path << std::endl;
        resultImage.save(rootpath + "output/testOCR_Result.bmp");

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
