#include <dlsdk/utils.h>
#include <dlsdk/model.h>
#include <iostream>
#include <fstream>

using namespace DaoAI::DeepLearning;

int main()
{
    try {
        // Initialize Unsupervised library
        initialize();

        // Configure the model and data path
        std::string root_directory = "../../../data/";  // Change to your own directory

        // Construct the model on the specified device
        Vision::UnsupervisedDefectSegmentation model(DeviceType::GPU);
        model.addComponentArchive(root_directory + "unsupervised_defect_segmentation_model.dwm");
        std::cout << model.getBatchSize() << std::endl;

        // Set batch size
        model.setBatchSize(1);

        std::string img_path = root_directory + "unsupervised_defect_segmentation_img.bmp";  // Change to your own directory
        Image img(img_path);

        Vision::UnsupervisedDefectSegmentationResult result = model.inference(img);

        // Print the result
        std::cout << "Anomaly score: " << result.confidence << std::endl;
        std::cout << "JSON result: " << result.toAnnotationJSONString() << "\n\n";

        // Save the result to a file
        std::string file_path = root_directory + "output.json";
        std::ofstream output_file(file_path);
        if (output_file.is_open()) {
            output_file << result.toAnnotationJSONString();
            output_file.close();
            std::cout << "JSON result saved to: " << file_path << std::endl;
        }
        else {
            std::cerr << "Failed to open the file: " << file_path << std::endl;
        }

        return 0;
    }
    catch (const std::exception& e) {
        std::cout << "Caught an exception: " << e.what() << std::endl;
        return -1;
    }
}