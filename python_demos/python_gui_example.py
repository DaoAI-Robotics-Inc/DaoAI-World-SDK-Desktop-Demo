import sys
import os
import time
import re
import logging
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QWidget, QScrollArea, QSplitter, QTextEdit)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QPoint
import dlsdk.dlsdk as dlsdk

# Custom handler to log to QTextEdit
class QTextEditHandler(logging.Handler):
    def __init__(self, text_edit_widget):
        super().__init__()
        self.text_edit_widget = text_edit_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_edit_widget.append(msg)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def initialize_sdk():
    try:
        logger.info("Initializing the SDK...")
        dlsdk.initialize()
        logger.info("SDK initialized successfully.\n")
    except Exception as e:
        logger.error(f"Error during SDK initialization: {str(e)}")
        raise

def load_model(model_path, device=dlsdk.DeviceType.CPU):
    try:
        logger.info(f"Loading model from: {model_path}")
        model = dlsdk.KeypointDetection(model_path, device=device)
        logger.info("Model loaded successfully.\n")
        return model
    except Exception as e:
        logger.error(f"Error during model loading: {str(e)}")
        raise

def run_inference(model, daoai_image, confidence_threshold=0.95):
    try:
        logger.info(f"Running inference with confidence threshold: {confidence_threshold}")
        prediction = model.inference(
            daoai_image,
            {dlsdk.PostProcessType.CONFIDENCE_THRESHOLD: confidence_threshold}
        )
        logger.info("Inference completed successfully.\n")
        return prediction
    except Exception as e:
        logger.error(f"Error during inference: {str(e)}")
        return None

def visualize_and_save_result(daoai_image, prediction, output_path="python_demos/output/images"):
    try:
        logger.info("Visualizing results and saving to output image...")
        os.makedirs(output_path, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        timestamp = re.sub(r'[:]', '-', timestamp)  # Replace ':' to avoid invalid filename
        output_file = os.path.join(output_path, f"python_gui_example_result_{timestamp}.png")
        result = dlsdk.visualize(daoai_image, prediction)
        result.save(output_file)
        logger.info(f"Visualization saved to: {output_file}\n")
        return output_file
    except Exception as e:
        logger.error(f"Error during visualization: {str(e)}")
        return None

class DraggableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.drag_position = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            move = event.pos() - self.drag_position
            self.move(self.pos() + move)

class KeypointDetectionApp(QMainWindow):
    def __init__(self, model_path):
        super().__init__()
        self.setWindowTitle("Python GUI Example Demo")
        self.setGeometry(100, 100, 1400, 900)  # Window size

        self.model = load_model(model_path)
        self.scale_factor = 1.0  # Initial zoom scale
        self.min_scale = 0.1    # Minimum zoom scale
        self.max_scale = 5.0    # Maximum zoom scale
        self.inference_image_path = None  # Track the inference image
        self.initUI()

    def initUI(self):
        # Use a QSplitter to split horizontally (left for image, right for log output)
        central_widget = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_widget)

        # Left side: Image display
        self.image_scroll = QScrollArea()
        self.image_label = DraggableLabel("No image loaded")
        self.image_scroll.setWidget(self.image_label)
        self.image_scroll.setWidgetResizable(True)

        # Right side: Output log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        central_widget.addWidget(self.image_scroll)
        central_widget.addWidget(self.log_output)

        # Set horizontal stretch factors: image gets 2 parts, log gets 1 part
        central_widget.setStretchFactor(0, 2)
        central_widget.setStretchFactor(1, 1)

        # Vertical layout for buttons (placed at the bottom)
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)

        self.infer_button = QPushButton("Run Inference")
        self.infer_button.clicked.connect(self.run_inference)
        self.infer_button.setEnabled(False)
        button_layout.addWidget(self.infer_button)

        button_widget = QWidget()
        button_widget.setLayout(button_layout)

        # Create a layout for the main window
        main_layout = QVBoxLayout()
        main_layout.addWidget(central_widget)  # Image and log area (takes most of the height)
        main_layout.addWidget(button_widget)   # Button at the bottom (takes minimal height)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Set custom logging handler to output to QTextEdit
        text_edit_handler = QTextEditHandler(self.log_output)
        text_edit_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_edit_handler)

        # Adjust the vertical space allocation between image/log and buttons
        central_widget.setSizes([1000, 300])  # Image and log areas (combined) take up most of the height
        button_widget.setFixedHeight(60)  # Buttons are given a fixed height (this controls their space)

    def load_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)", options=options)
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)
            self.scale_factor = 1.0  # Reset zoom scale
            self.infer_button.setEnabled(True)
            logger.info(f"Loaded image: {file_path}")
            self.apply_auto_fit()

    def apply_auto_fit(self):
        # Get the size of the image label and the pixmap (image)
        label_size = self.image_label.size()
        pixmap = QPixmap(self.image_path)
        image_size = pixmap.size()

        # Calculate scale factor based on label size and image size
        if image_size.width() > 0 and image_size.height() > 0:
            scale_x = label_size.width() / image_size.width()
            scale_y = label_size.height() / image_size.height()
            self.scale_factor = min(scale_x, scale_y)  # Preserve aspect ratio by using the smaller of the two scale factors

        # Scale the pixmap based on the calculated scale factor
        scaled_pixmap = pixmap.scaled(pixmap.size() * self.scale_factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Set the scaled pixmap to the label and adjust size
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.adjustSize()
        
    def wheelEvent(self, event):
        # Handle wheel event for zooming
        delta = event.angleDelta().y()
        if delta > 0:  # Zoom in
            new_scale = self.scale_factor * 1.1
        else:  # Zoom out
            new_scale = self.scale_factor / 1.1

        # Limit zoom range
        if self.min_scale <= new_scale <= self.max_scale:
            self.scale_factor = new_scale
            self.apply_zoom()
        event.accept()

    def apply_zoom(self):
        # Load the image based on whether inference has been run or not
        if hasattr(self, "inference_image_path") and self.inference_image_path:
            pixmap = QPixmap(self.inference_image_path)
        else:
            pixmap = QPixmap(self.image_path)

        scaled_pixmap = pixmap.scaled(pixmap.size() * self.scale_factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.adjustSize()
        
    def run_inference(self):
        if not hasattr(self, 'image_path'):
            logger.error("No image loaded.")
            return

        daoai_image = dlsdk.Image(self.image_path)
        prediction = run_inference(self.model, daoai_image)

        if prediction:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            timestamp = re.sub(r'[:]', '-', timestamp)  # Replace ':' to avoid invalid filename
            output_path = os.path.join("python_demos/output/images")
            os.makedirs(output_path, exist_ok=True)
            result_path = visualize_and_save_result(daoai_image, prediction, output_path)

            if result_path:
                self.inference_image_path = result_path  # Store the inference image path
                pixmap = QPixmap(result_path)
                self.image_label.setPixmap(pixmap)
                self.image_label.adjustSize()
                logger.info(f"Result saved and displayed: {result_path}")

            # Log detailed predictions (polygons and keypoints)
            max_points_to_print = 5
            logger.info("\nPolygons Output:")
            for obj_index, mask in enumerate(prediction.masks):
                polygons = mask.toPolygons()
                logger.info(f"  Polygon Mask for Object {obj_index + 1}:")
                for poly_index, polygon in enumerate(polygons):
                    logger.info(f"    Polygon {poly_index + 1}:")
                    for point_index, point in enumerate(polygon.points[:max_points_to_print]):
                        logger.info(f"      Point {point_index + 1}: ({point.x}, {point.y})")
                    if len(polygon.points) > max_points_to_print:
                        logger.info(f"      ... and {len(polygon.points) - max_points_to_print} more points omitted.")

            logger.info("\nKeypoints:")
            for obj_index, keypoints in enumerate(prediction.keypoints):
                logger.info(f"  Keypoints for Object {obj_index + 1}:")
                for kp_index, keypoint in enumerate(keypoints):
                    logger.info(f"    Keypoint {kp_index + 1}: (x: {keypoint.x}, y: {keypoint.y})")

            self.apply_zoom()  # Apply zoom to the inference image

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Update this path to your model file
    model_path = r"data\keypoint_detection_model.dwm"

    initialize_sdk()
    main_window = KeypointDetectionApp(model_path)
    main_window.show()
    sys.exit(app.exec_())
