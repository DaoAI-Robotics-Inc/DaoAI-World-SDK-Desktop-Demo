import cv2
import json
import dlsdk.dlsdk as dlsdk
import numpy as np
import os

# Initialize Deep Learning SDK
dlsdk.initialize()

# Global variables
clicked_points = []
drawn_boxes = []
is_drawing = False
start_point = None
original_image = None
model = None
embedding = None
window_name = "Image Viewer"
drag_threshold = 5
image_path = r"data\instance_segmentation_img.jpg"  # Change to your image path
model_path = r"data\auto_segment.dwm"  # Change to your model path

# Save JSON result to a file
def save_result_to_file(json_data, image_path):
    directory = os.path.dirname(image_path)
    output_path = os.path.join(directory, "result.json")
    
    try:
        with open(output_path, "w") as file:
            json.dump(json_data, file, indent=4)
        print(f"Result saved to: {output_path}")
    except Exception as e:
        print(f"Error: Could not save result to {output_path}, {e}")

# Mouse callback function
def on_mouse(event, x, y, flags, param):
    global is_drawing, start_point, clicked_points, drawn_boxes, original_image

    display_image = original_image.copy()
    
    if event == cv2.EVENT_LBUTTONDOWN:
        is_drawing = True
        start_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and is_drawing:
        if abs(x - start_point[0]) > drag_threshold or abs(y - start_point[1]) > drag_threshold:
            cv2.rectangle(display_image, start_point, (x, y), (0, 255, 0), 2)
            cv2.imshow(window_name, display_image)

    elif event == cv2.EVENT_LBUTTONUP:
        is_drawing = False
        end_point = (x, y)

        if start_point == end_point:
            clicked_points.append(dlsdk.Point(x, y, "1"))  # Positive point
        else:
            drawn_boxes.append(dlsdk.Box(dlsdk.Point(*start_point), dlsdk.Point(*end_point)))
            cv2.rectangle(display_image, start_point, end_point, (0, 255, 0), 2)

        run_inference()

    elif event == cv2.EVENT_RBUTTONDOWN:
        clicked_points.append(dlsdk.Point(x, y, "0"))  # Negative point
        run_inference()

# Perform inference and update display
def run_inference():
    global model, embedding, clicked_points, drawn_boxes, original_image

    if not model or not embedding:
        print("Model or embedding not initialized!")
        return

    # Perform inference
    result = model.inference(embedding, drawn_boxes, clicked_points)
    daoai_mask_image = result.mask.toImage()

    # Save result
    save_result_to_file(result.toJSONString(), image_path)

    # Convert mask to OpenCV format
    mask_image = np.array(daoai_mask_image, dtype=np.uint8).reshape(daoai_mask_image.height, daoai_mask_image.width)

    # Create masked image
    masked_image = cv2.bitwise_and(original_image, original_image, mask=mask_image)

    # Blend images
    blended_image = cv2.addWeighted(original_image, 0.3, masked_image, 0.7, 0)

    # Display updated image
    cv2.imshow(window_name, blended_image)

# Main function
def main():
    global original_image, model, embedding

    # Load image
    original_image = cv2.imread(image_path)
    if original_image is None:
        print(f"Error: Could not load the image from {image_path}")
        return

    # Load model and generate embeddings
    try:
        model = dlsdk.AutoSegmentation(model_path, dlsdk.DeviceType.GPU)
        daoai_image = dlsdk.Image(image_path)
        embedding = model.generateImageEmbeddings(daoai_image)
    except Exception as e:
        print(f"Error initializing the model: {e}")
        return

    # Create OpenCV window
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.imshow(window_name, original_image)
    cv2.setMouseCallback(window_name, on_mouse)

    # Wait for user input
    while True:
        key = cv2.waitKey(1)
        if key == 27:  # Exit on 'Esc'
            break
        elif key in [ord('r'), ord('R')]:  # Reset on 'r'
            clicked_points.clear()
            drawn_boxes.clear()
            cv2.imshow(window_name, original_image)  # Reset display

    # Cleanup
    del model
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
