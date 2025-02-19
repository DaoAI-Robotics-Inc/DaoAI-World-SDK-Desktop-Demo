#include <dlsdk/utils.h>
#include <dlsdk/model.h>
#include <dlsdk/common.h>
#include <opencv2/opencv.hpp>
#include <filesystem>
#include <iostream>
#include <fstream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace DaoAI::DeepLearning;
namespace fs = std::filesystem;

// Fixed display window size
const int FIXED_WIDTH = 800;
const int FIXED_HEIGHT = 600;
// Current scale factor (relative to the original image)
double scale = 1.0;

// Annotation data for each image
// (All annotation coordinates are in the original image coordinate system, supporting sub-pixel precision)
struct ImageAnnotation {
    std::string filepath;            // Full image path
    bool isAnnotated = false;        // Whether the image has been annotated (good or bad)
    bool isGood = true;              // true: good, false: bad
    bool finished = false;           // For bad images: whether the annotation (polygon) is finished (closed)
    std::vector<cv::Point2f> polygon; // Polygon points for bad image annotations (in original image coordinates)
};

std::vector<ImageAnnotation> annotations;
int currentIndex = 0;
cv::Mat originalImage;   // Original image loaded from file
cv::Mat displayImage;    // Image for display in the fixed window (after scaling, centering, or cropping)
const std::string windowName = "Annotation";

// Render the scaled image to the fixed window and draw annotation text and points,
// based on the current scale factor and window settings.
void redrawImage() {
    // Calculate the dimensions after scaling
    int newWidth = static_cast<int>(originalImage.cols * scale);
    int newHeight = static_cast<int>(originalImage.rows * scale);
    cv::Mat resized;
    cv::resize(originalImage, resized, cv::Size(newWidth, newHeight));

    // Create a fixed-size canvas (black background)
    cv::Mat canvas(FIXED_HEIGHT, FIXED_WIDTH, resized.type(), cv::Scalar(0, 0, 0));

    int effectiveOffsetX = 0, effectiveOffsetY = 0;
    if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT) {
        // If the scaled image is smaller than the canvas, center it
        effectiveOffsetX = (FIXED_WIDTH - newWidth) / 2;
        effectiveOffsetY = (FIXED_HEIGHT - newHeight) / 2;
        resized.copyTo(canvas(cv::Rect(effectiveOffsetX, effectiveOffsetY, newWidth, newHeight)));
    }
    else {
        // If the scaled image exceeds the canvas, crop the central region for display
        int cropX = (newWidth - FIXED_WIDTH) / 2;
        int cropY = (newHeight - FIXED_HEIGHT) / 2;
        effectiveOffsetX = -cropX; // Display coordinate = original coordinate * scale - cropX
        effectiveOffsetY = -cropY;
        cv::Rect roi(cropX, cropY, FIXED_WIDTH, FIXED_HEIGHT);
        canvas = resized(roi).clone();
    }
    displayImage = canvas.clone();

    // Display annotation status text in the top-left corner
    std::string labelText;
    if (!annotations[currentIndex].isAnnotated)
        labelText = "Unlabeled";
    else
        labelText = (annotations[currentIndex].isGood ? "Good" : "Bad");
    cv::putText(displayImage, labelText, cv::Point(10, 30),
        cv::FONT_HERSHEY_SIMPLEX, 1.0, cv::Scalar(255, 0, 0), 2);

    // If the current image is annotated as bad and has polygon annotations,
    // draw lines connecting the points and the points themselves
    // (converted from original image coordinates to display coordinates)
    if (annotations[currentIndex].isAnnotated && !annotations[currentIndex].isGood &&
        !annotations[currentIndex].polygon.empty())
    {
        const auto& pts = annotations[currentIndex].polygon;
        for (size_t i = 0; i < pts.size(); i++) {
            cv::Point ptDisplay(cvRound(pts[i].x * scale) + effectiveOffsetX,
                cvRound(pts[i].y * scale) + effectiveOffsetY);
            cv::circle(displayImage, ptDisplay, 3, cv::Scalar(0, 0, 255), -1);
            if (i > 0) {
                cv::Point prevDisplay(cvRound(pts[i - 1].x * scale) + effectiveOffsetX,
                    cvRound(pts[i - 1].y * scale) + effectiveOffsetY);
                cv::line(displayImage, prevDisplay, ptDisplay, cv::Scalar(0, 255, 0), 2);
            }
        }
        // If the user has finished the annotation,
        // draw an extra line connecting the last point back to the first point.
        if (annotations[currentIndex].finished && pts.size() >= 2) {
            cv::Point firstDisplay(cvRound(pts.front().x * scale) + effectiveOffsetX,
                cvRound(pts.front().y * scale) + effectiveOffsetY);
            cv::Point lastDisplay(cvRound(pts.back().x * scale) + effectiveOffsetX,
                cvRound(pts.back().y * scale) + effectiveOffsetY);
            cv::line(displayImage, lastDisplay, firstDisplay, cv::Scalar(0, 255, 0), 2);
        }
    }
}

// Mouse callback function: handles zooming with the mouse wheel and adding annotation points with left-click
// (only valid for images annotated as bad)
// When left-clicking, convert the fixed window coordinates to sub-pixel coordinates in the original image.
void onMouse(int event, int x, int y, int flags, void* userdata) {
    int newWidth = static_cast<int>(originalImage.cols * scale);
    int newHeight = static_cast<int>(originalImage.rows * scale);
    int effectiveOffsetX = 0, effectiveOffsetY = 0;
    if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT) {
        effectiveOffsetX = (FIXED_WIDTH - newWidth) / 2;
        effectiveOffsetY = (FIXED_HEIGHT - newHeight) / 2;
    }
    else {
        effectiveOffsetX = -(newWidth - FIXED_WIDTH) / 2;
        effectiveOffsetY = -(newHeight - FIXED_HEIGHT) / 2;
    }

    if (event == cv::EVENT_MOUSEWHEEL) {
        int delta = cv::getMouseWheelDelta(flags);
        double zoomFactor = 1.1; // Zoom in/out by 10% each time
        if (delta > 0) {
            scale *= zoomFactor;
        }
        else if (delta < 0) {
            scale /= zoomFactor;
        }
        scale = std::max(0.1, std::min(scale, 10.0));
        redrawImage();
        cv::imshow(windowName, displayImage);
        return;
    }

    // Only allow adding annotation points for images annotated as bad
    if (!annotations[currentIndex].isAnnotated || annotations[currentIndex].isGood)
        return;

    if (event == cv::EVENT_LBUTTONDOWN) {
        // If the image does not fill the entire canvas, clicks must be within the image area
        if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT) {
            if (x < effectiveOffsetX || x > effectiveOffsetX + newWidth ||
                y < effectiveOffsetY || y > effectiveOffsetY + newHeight)
                return;
        }
        // Convert the clicked display coordinates to sub-pixel coordinates in the original image
        float origX = (x - effectiveOffsetX) / static_cast<float>(scale);
        float origY = (y - effectiveOffsetY) / static_cast<float>(scale);
        annotations[currentIndex].polygon.push_back(cv::Point2f(origX, origY));
        redrawImage();
        cv::imshow(windowName, displayImage);
    }
}

int main() {
    try {
        // Initialize the DaoAI Unsupervised library
        initialize();

        // 1. Prompt the user to enter the folder path containing images
        std::string folderPath;
        std::cout << "Enter the folder path containing images: ";
        std::getline(std::cin, folderPath);
        if (!fs::exists(folderPath)) {
            std::cerr << "Folder does not exist: " << folderPath << std::endl;
            return -1;
        }

        // 2. Load all images in the folder (supports .png, .jpg, .jpeg)
        std::vector<std::string> imagePaths;
        for (const auto& entry : fs::directory_iterator(folderPath)) {
            if (entry.is_regular_file()) {
                std::string ext = entry.path().extension().string();
                std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
                if (ext == ".png" || ext == ".jpg" || ext == ".jpeg")
                    imagePaths.push_back(entry.path().string());
            }
        }
        if (imagePaths.empty()) {
            std::cerr << "No images found in folder." << std::endl;
            return -1;
        }
        std::sort(imagePaths.begin(), imagePaths.end());

        // Initialize annotation data for each image
        annotations.clear();
        for (const auto& path : imagePaths) {
            ImageAnnotation ann;
            ann.filepath = path;
            annotations.push_back(ann);
        }

        // 3. Interactive annotation interface (fixed window, zooming, sub-pixel annotation)
        cv::namedWindow(windowName, cv::WINDOW_AUTOSIZE);
        cv::setMouseCallback(windowName, onMouse, nullptr);
        bool exitAnnotation = false;
        std::cout << "Annotation instructions:\n"
            << " n: Next image\n"
            << " p: Previous image\n"
            << " g: Mark current image as GOOD\n"
            << " b: Mark current image as BAD (use mouse left-click to add polygon points)\n"
            << " r: Reset polygon for current BAD image\n"
            << " f: Finish annotation (close polygon by connecting last point to first)\n"
            << " q: Quit annotation\n"
            << " Use mouse wheel to zoom in/out.\n";

        while (!exitAnnotation) {
            // Load the current image
            originalImage = cv::imread(annotations[currentIndex].filepath);
            if (originalImage.empty()) {
                std::cerr << "Failed to load image: " << annotations[currentIndex].filepath << std::endl;
                currentIndex = (currentIndex + 1) % annotations.size();
                continue;
            }
            // Set the initial scale factor so that the image is fully visible in the fixed window
            scale = std::min(static_cast<double>(FIXED_WIDTH) / originalImage.cols,
                static_cast<double>(FIXED_HEIGHT) / originalImage.rows);
            redrawImage();
            cv::imshow(windowName, displayImage);
            int key = cv::waitKey(0);
            switch (key) {
            case 'n': // Next image
                currentIndex = (currentIndex + 1) % annotations.size();
                break;
            case 'p': // Previous image
                currentIndex = (currentIndex - 1 + annotations.size()) % annotations.size();
                break;
            case 'g': // Mark as GOOD (and clear any polygon data)
                annotations[currentIndex].isAnnotated = true;
                annotations[currentIndex].isGood = true;
                annotations[currentIndex].polygon.clear();
                annotations[currentIndex].finished = false;
                redrawImage();
                cv::imshow(windowName, displayImage);
                break;
            case 'b': // Mark as BAD (allowing subsequent addition of polygon points)
                annotations[currentIndex].isAnnotated = true;
                annotations[currentIndex].isGood = false;
                annotations[currentIndex].polygon.clear();
                annotations[currentIndex].finished = false;
                redrawImage();
                cv::imshow(windowName, displayImage);
                break;
            case 'r': // Reset the polygon annotation for the current BAD image
                if (!annotations[currentIndex].isGood) {
                    annotations[currentIndex].polygon.clear();
                    annotations[currentIndex].finished = false;
                }
                redrawImage();
                cv::imshow(windowName, displayImage);
                break;
            case 'f': // Finish annotation: requires at least two points, then closes the polygon
                if (!annotations[currentIndex].isGood && annotations[currentIndex].polygon.size() >= 2) {
                    annotations[currentIndex].finished = true;
                    std::cout << "Annotation finished for image: " << annotations[currentIndex].filepath << std::endl;
                    redrawImage();
                    cv::imshow(windowName, displayImage);
                }
                else {
                    std::cout << "Need at least 2 points to finish annotation." << std::endl;
                }
                break;
            case 'q': // Exit annotation
                exitAnnotation = true;
                break;
            default:
                break;
            }
            std::cout << "Image " << currentIndex + 1 << "/" << annotations.size()
                << " - " << annotations[currentIndex].filepath << std::endl;
        }
        cv::destroyWindow(windowName);

        // 4. Save annotation results to an "out" directory under the initial folder
        fs::path outDir = fs::path(folderPath) / "out";
        fs::path goodDir = outDir / "good";
        fs::path badDir = outDir / "bad";
        fs::path maskDir = outDir / "masks";

        fs::create_directories(goodDir);
        fs::create_directories(badDir);
        fs::create_directories(maskDir);

        // For each annotation, copy the image to the corresponding directory,
        // and generate a binary mask for BAD images (mask saved as a 0/255 image)
        for (const auto& ann : annotations) {
            if (!ann.isAnnotated)
                continue;
            fs::path srcPath(ann.filepath);
            fs::path destPath;
            if (ann.isGood) {
                destPath = goodDir / srcPath.filename();
                try {
                    fs::copy_file(srcPath, destPath, fs::copy_options::overwrite_existing);
                }
                catch (std::exception& e) {
                    std::cerr << "Error copying file: " << e.what() << std::endl;
                }
            }
            else {
                destPath = badDir / srcPath.filename();
                try {
                    fs::copy_file(srcPath, destPath, fs::copy_options::overwrite_existing);
                }
                catch (std::exception& e) {
                    std::cerr << "Error copying file: " << e.what() << std::endl;
                }
                // Generate mask: load the grayscale image
                cv::Mat imgGray = cv::imread(ann.filepath, cv::IMREAD_GRAYSCALE);
                if (imgGray.empty()) {
                    std::cerr << "Failed to load image for mask generation: " << ann.filepath << std::endl;
                    continue;
                }
                cv::Mat mask = cv::Mat::zeros(imgGray.size(), CV_8UC1);
                if (ann.polygon.empty()) {
                    // If no polygon is annotated, make the mask entirely white
                    mask = cv::Mat::ones(imgGray.size(), CV_8UC1) * 255;
                }
                else {
                    // If there is a polygon, fill the polygon area with white (fillPoly automatically closes the polygon)
                    std::vector<cv::Point> poly;
                    for (const auto& pt : ann.polygon) {
                        poly.push_back(cv::Point(cvRound(pt.x), cvRound(pt.y)));
                    }
                    if (poly.size() >= 2 && poly.front() != poly.back())
                        poly.push_back(poly.front());
                    std::vector<std::vector<cv::Point>> pts{ poly };
                    cv::fillPoly(mask, pts, cv::Scalar(255));
                }
                fs::path maskPath = maskDir / srcPath.stem();
                maskPath += "_mask.png";
                cv::imwrite(maskPath.string(), mask);
            }
        }
        std::cout << "Annotated images saved to:" << std::endl;
        std::cout << "  Good: " << goodDir.string() << std::endl;
        std::cout << "  Bad: " << badDir.string() << std::endl;
        std::cout << "  Masks: " << maskDir.string() << std::endl;

        // 5. Re-read images from the "out" directory as training data
        std::vector<Image> good_images;
        std::vector<Image> bad_images;
        std::vector<Image> masks;

        for (const auto& entry : fs::directory_iterator(goodDir)) {
            if (entry.is_regular_file()) {
                good_images.push_back(Image(entry.path().string()));
            }
        }
        for (const auto& entry : fs::directory_iterator(badDir)) {
            if (entry.is_regular_file()) {
                bad_images.push_back(Image(entry.path().string()));
            }
        }
        for (const auto& entry : fs::directory_iterator(maskDir)) {
            if (entry.is_regular_file()) {
                masks.push_back(Image(entry.path().string()));
            }
        }
        std::cout << "Re-read " << good_images.size() << " good images, "
            << bad_images.size() << " bad images, and "
            << masks.size() << " masks for training." << std::endl;

        // 6. Use the re-read data to build a training component
        Vision::UnsupervisedDefectSegmentation model(DeviceType::GPU);
        model.setDetectionLevel(Vision::DetectionLevel::PIXEL);
        ComponentMemory component = model.createComponentMemory("screw", good_images, bad_images, masks, true);
        std::string compFile = (fs::path(folderPath) / "component_1.pth").string();
        component.save(compFile);
        model.setBatchSize(1);
        std::cout << "Component memory saved to " << compFile << std::endl;

        // 7. (Optional) Perform inference on a BAD image to view the results
        if (!bad_images.empty()) {
            Vision::UnsupervisedDefectSegmentationResult result = model.inference(bad_images[0]);
            std::cout << "Anomaly score: " << result.confidence << std::endl;
            std::cout << "JSON result: " << result.toAnnotationJSONString() << std::endl;
        }
        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Caught an exception: " << e.what() << std::endl;
        return -1;
    }
}
