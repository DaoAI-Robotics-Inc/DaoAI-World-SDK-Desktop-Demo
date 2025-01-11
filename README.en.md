# DaoAI World SDK Code Samples

This repository provides **DaoAI World SDK** multi-language examples (Python, C++, and C#). These examples demonstrate how to use the deep learning models provided by DaoAI and obtain inference results.

---

## Repository Structure

This repository includes the following directories and files:

- **Python Examples**:
  - **Basic Usage**: Demonstrates how to use Python to call DaoAI World SDK and obtain inference results from deep learning models.
  - **GUI Application**: Demonstrates how to create a graphical user interface (GUI) application in Python, allowing users to load images and view inference results through the interface.
  
- **C++ Examples**:
  - **Basic Usage**: Demonstrates how to integrate DaoAI World SDK in C++ and obtain model inference results.
  - **GUI Application**: Demonstrates how to integrate DaoAI World SDK in C++ and create a GUI application. Users can load images and view inference results through the interface.

- **C# Examples**:
  - **Basic Usage**: Demonstrates how to use DaoAI World SDK in C# to obtain inference results.
  - **GUI Application**: Demonstrates how to create a GUI application in C#, allowing users to load images and view inference results.

Each example includes detailed code comments to help developers quickly understand how to use the DaoAI World SDK in different programming languages.

### Installing DaoAI World SDK

Before running the example code in this repository, you need to install the DaoAI World SDK. Follow these steps:

1. Open the [DaoAI World User Manual](http://docs.welinkirt.com/daoai-world-user-manual/latest/index.html).
2. Navigate to the developer functionality section and follow the documentation to download and install the DaoAI World SDK.

Ensure that the DaoAI World SDK is correctly installed and configured before running the example code.

## Quick Start

To get started with the sample code in this repository, follow these steps:

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/yourusername/DaoAI-World-SDK-Demo.git
cd DaoAI-World-SDK-Demo
```

### 2. Download Sample Data

Download [Data](https://daoairoboticsinc-my.sharepoint.com/:f:/g/personal/nrd_daoai_com/ElXWeD4qcbFLkto-NhXxgmsBlIEZ0G5iKVtdV_N0yPWfiQ?e=ViNAAL), locate `data.zip`, and extract it to the root directory.

### 3. Install Dependencies

Based on your development environment, choose the appropriate language and dependencies:

- **Python 3.10**:
  - Install the required Python libraries:
    ```bash
    cd python_demos
    pip install -r requirements.txt
    ```

- **C++**:
  - Refer to the instructions in `cpp_demos/README.md` to install dependencies suitable for your platform, including GUI-related libraries (such as Qt or other UI libraries).

- **C#**:
  - Refer to the instructions in `cs_demos/README.md` to install required .NET libraries and tools, including GUI-related components (such as WinForms or WPF).

### 4. Run the Examples

- **Python**:
  - **Basic Usage Example**: Run the Python example code:
    ```bash
    python instance_segmentation_demo.py
    ```
  - **GUI Application**: Run the GUI-based Python example code:
    ```bash
    python python_gui_example.py
    ```

- **C++**:
  - **Basic Usage Example**: Follow the steps in `C++/README.md` to compile and run the example to obtain inference results.
  - **GUI Application**: Follow the steps in `C++/README.md` to compile and run the GUI-based C++ example. Open the GUI, load an image, and view the inference results.

- **C#**:
  - **Basic Usage Example**: Follow the steps in `C#/README.md` to run the C# example and obtain inference results.
  - **GUI Application**: Follow the steps in `C#/README.md` to run the GUI-based C# example. Open the GUI, load an image, and view the inference results.

### Features Demonstrated

Each example showcases the core functionalities of the **DaoAI World SDK**, including:

- **Loading Deep Learning Models**: Demonstrates how to load deep learning models provided by DaoAI.
- **Performing Inference**: Demonstrates how to input data into the model and obtain inference results.
- **Processing Inference Results**: Demonstrates how to handle and parse inference results from the model output.
- **GUI Examples** (C++, C#, and Python): Demonstrates how to use DaoAI World SDK in desktop applications, allowing users to load images through a GUI and view inference results. The processed results are displayed within the interface.

### Contributing

Contributions are welcome! If you have any suggestions for improvement or discover bugs, feel free to submit an Issue or a Pull Request. We welcome community participation to enhance the **DaoAI World SDK Code Samples**.

### License

This project is licensed under the [MIT License](LICENSE).
