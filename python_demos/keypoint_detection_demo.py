import os
import re
import cv2
import time
import json
import logging
import dlsdk.dlsdk as dlsdk

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def initialize_sdk():
    """
    Initialize the SDK.
    
    Returns:
        None
    """
    try:
        logger.info("Initializing the SDK...")
        dlsdk.initialize()
        logger.info("SDK initialized successfully.\n")
    except Exception as e:
        logger.error(f"Error during SDK initialization: {str(e)}")
        raise

def load_model(model_path, device=dlsdk.DeviceType.CPU):
    """
    Load the Keypoint Detection model.
    
    Args:
        model_path (str): Path to the model file.
        device (dlsdk.DeviceType): Device to run the model on (default: GPU).
    
    Returns:
        model: Loaded model object.
    """
    try:
        logger.info(f"Loading model from: {model_path}")
        model = dlsdk.KeypointDetection(model_path, device=device)
        logger.info("Model loaded successfully.\n")
        return model
    except Exception as e:
        logger.error(f"Error during model loading: {str(e)}")
        raise

def load_image(image_path):
    """
    Load and convert an image to SDK-supported format.
    
    Args:
        image_path (str): Path to the image file.
    
    Returns:
        daoai_image: Converted image object, or None if an error occurs.
    """
    try:
        logger.info(f"Loading image from: {image_path}")
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Unable to load image at {image_path}")
        daoai_image = dlsdk.Image(image_path)
        assert isinstance(daoai_image, dlsdk.Image)
        logger.info("Image loaded successfully.\n")
        return daoai_image
    except Exception as e:
        logger.error(f"Error during image loading: {str(e)}")
        return None

def run_inference(model, daoai_image, confidence_threshold=0.95):
    """
    Run inference on the image with error handling.
    
    Args:
        model: The Keypoint Detection model object.
        daoai_image: The image in the format supported by the SDK.
        confidence_threshold (float): Confidence threshold for post-processing.
    
    Returns:
        prediction: Inference result, or None if an error occurs.
    """
    try:
        logger.info(f"Running inference with confidence threshold: {confidence_threshold}")
        model.setConfidenceThreshold(confidence_threshold)
        prediction = model.inference(daoai_image )
        
        # The first inference involves loading the model into memory, so the time for the first inference should be excluded
        # from the performance measurement.
        start_time = time.time()
        prediction = model.inference(daoai_image )
        execution_time = time.time() - start_time
        logger.info(f"Inference completed in {execution_time:.2f} seconds.\n")
        return prediction
    except Exception as e:
        logger.error(f"Error during inference: {str(e)}")
        return None


def visualize_and_save_result(daoai_image, prediction, output_path="output.png"):
    """
    Visualize the prediction and save the output image.
    
    Args:
        daoai_image: The input image object.
        prediction: The prediction results.
        output_path (str): Path to save the output image.
    
    Returns:
        None
    """
    try:
        logger.info("Visualizing results and saving to output image...")
        result = dlsdk.visualize(daoai_image, prediction)
        result.save(output_path)
        logger.info(f"Visualization saved to: {output_path}\n")
    except Exception as e:
        logger.error(f"Error during visualization: {str(e)}")

def save_prediction_to_json(prediction, json_path="output.json", annotation_path="outputAnnotation.json"):
    """
    Save the prediction result to JSON files.
    
    Args:
        prediction: The prediction results.
        json_path (str): Path to save the JSON file for predictions.
        annotation_path (str): Path to save the annotation JSON file.
    
    Returns:
        None
    """
    try:
        logger.info("Saving predictions to JSON files...")
        
        # Convert prediction to JSON strings
        prediction_json = prediction.toJSONString()
        annotation_json = prediction.toAnnotationJSONString()
        
        # Save formatted prediction JSON
        with open(json_path, "w") as f:
            json.dump(json.loads(prediction_json), f, indent=4)
        logger.info(f"Prediction JSON saved to: {json_path}")
        
        # Save formatted annotation JSON
        with open(annotation_path, "w") as f:
            json.dump(json.loads(annotation_json), f, indent=4)
        logger.info(f"Annotation JSON saved to: {annotation_path}\n")
    except Exception as e:
        logger.error(f"Error during JSON saving: {str(e)}")
               
def print_detection_results(prediction, max_points_to_print=3):
    """Print detailed detection results with limited polygon points for readability."""
    logger.info("Printing detection results...")
    logger.info("\nClass IDs and Labels:")
    for class_id, class_label, confidence in zip(prediction.class_ids, prediction.class_labels, prediction.confidences):
        logger.info(f"  Class ID: {class_id}, Label: {class_label}, Confidence: {confidence:.2f}")

    logger.info("\nBounding Boxes:")
    for box in prediction.boxes:
        logger.info(f"  Top-left (x1, y1): ({box.x1()}, {box.y1()}), Bottom-right (x2, y2): ({box.x2()}, {box.y2()})")
    
    logger.info("\nMasks to Polygons:")
    for mask in prediction.masks:
        polygons = mask.toPolygons()
        for i, polygon in enumerate(polygons):
            logger.info(f"  Polygon {i + 1}:")
            for j, point in enumerate(polygon.points[:max_points_to_print]):
                logger.info(f"    Point {j + 1}: ({point.x}, {point.y})")
            if len(polygon.points) > max_points_to_print:
                logger.info(f"    ... and {len(polygon.points) - max_points_to_print} more points omitted.")
    
    logger.info("\nKeypoints:")
    for obj_index, keypoints in enumerate(prediction.keypoints):
        logger.info(f"  Keypoints for Object {obj_index + 1}:")
        for kp_index, keypoint in enumerate(keypoints):
            logger.info(f"    Keypoint {kp_index + 1}: (x: {keypoint.x}, y: {keypoint.y})")
    
    logger.info("\nDetection results printed successfully.\n")

def create_output_directories(base_dir=r"python_demos\output"):
    """Create output directories if they do not exist."""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    image_output_dir = os.path.join(base_dir, "images")
    json_output_dir = os.path.join(base_dir, "json")
    
    if not os.path.exists(image_output_dir):
        os.makedirs(image_output_dir)
    
    if not os.path.exists(json_output_dir):
        os.makedirs(json_output_dir)
    
    return image_output_dir, json_output_dir

def generate_output_paths(base_dir=r"python_demos\output"):
    """Generate file paths for saving the results."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    timestamp = re.sub(r'[:]', '-', timestamp)  # Replace ':' to avoid invalid filename
    image_output_dir, json_output_dir = create_output_directories(base_dir)
    
    image_output_path = os.path.join(image_output_dir, f"keypoint_detection_result_{timestamp}.png")
    json_output_path = os.path.join(json_output_dir, f"keypoint_detection_prediction_{timestamp}.json")
    annotation_output_path = os.path.join(json_output_dir, f"keypoint_detection_annotation_{timestamp}.json")
    
    return image_output_path, json_output_path, annotation_output_path

def main():
    """Main function to demonstrate Keypoint Detection."""
    logger.info("=== Starting Keypoint Detection Demo ===\n")

    # Paths (update these to your environment)
    model_path = r"data\keypoint_detection_model.dwm"
    image_path =  r"data\keypoint_detection_img.png"

    # Step 1: Initialize SDK
    initialize_sdk()
    
    # Step 2: Load model
    model = load_model(model_path)
    
    # Step 3: Load image
    daoai_image = load_image(image_path)
    if daoai_image is None:
        logger.error("Exiting program due to image load failure.")
        return
    
    # Step 4: Run inference
    prediction = run_inference(model, daoai_image)
    if prediction is None:
        logger.error("Exiting program due to inference failure.")
        return

    # Step 5: Generate output paths (with timestamp)
    image_output_path, json_output_path, annotation_output_path = generate_output_paths()

    # Step 6: Print detection results
    print_detection_results(prediction)
    
    # Step 7: Visualize and save results
    visualize_and_save_result(daoai_image, prediction, output_path=image_output_path)

    # Step 8: Save results to JSON
    save_prediction_to_json(prediction, json_path=json_output_path, annotation_path=annotation_output_path)

    logger.info("=== Keypoint Detection Demo Completed ===")

if __name__ == "__main__":
    main()
