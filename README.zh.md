
# DaoAI World SDK 代码示例

本仓库提供了 **DaoAI World SDK** 的多语言示例（Python、C++ 和 C#）。这些示例展示了如何使用 DaoAI 提供的深度学习模型，并获取推理结果。

---

## 仓库结构

本仓库包含以下目录和文件：

- **Python 示例**：
  - **简单使用**：展示如何使用 Python 调用 DaoAI World SDK 获取深度学习模型的推理结果。
  - **图形界面应用**：展示如何在 Python 中创建带图形界面的应用，用户可以通过界面加载图像并查看推理结果。
  
- **C++ 示例**：
  - **简单使用**：展示如何在 C++ 中集成 DaoAI World SDK，并获取模型推理结果。
  - **图形界面应用**：展示如何在 C++ 中集成 DaoAI World SDK，并创建图形界面应用，用户可以通过界面加载图像并查看推理结果。

- **C# 示例**：
  - **简单使用**：展示如何在 C# 中使用 DaoAI World SDK 获取推理结果。
  - **图形界面应用**：展示如何在 C# 中创建图形界面应用，用户可以通过界面加载图像并查看推理结果。

每个示例都包括了详细的代码注释，帮助开发者快速理解如何在不同编程语言中使用 DaoAI World SDK。

### 安装 DaoAI World SDK

在运行本项目示例代码之前，你需要安装 DaoAI World SDK。请按照以下步骤进行操作：

1. 打开 [DaoAI World 用户手册](http://docs.welinkirt.com/daoai-world-user-manual/latest/index.html)。
2. 找到开发功能章节，按照文档说明下载并安装 DaoAI World SDK。

请确保在运行示例代码之前，DaoAI World SDK 已正确安装并配置完成。

## 快速开始

要开始使用本仓库中的示例代码，按照以下步骤进行：

### 1. 克隆仓库

首先，将本仓库克隆到本地：

```bash
git clone https://github.com/yourusername/DaoAI-World-SDK-Demo.git
cd DaoAI-World-SDK-Demo
```

### 2. 安装依赖

根据你的开发环境，选择合适的语言和依赖：

- **Python 3.10**:
  - 安装所需的 Python 库：
    ```bash
    cd python_demos
    pip install -r requirements.txt
    ```

- **C++**:
  - 请参考 `cpp_demos/README.md` 中的说明，安装适用于你的平台的依赖，包含图形界面所需的库（如 Qt 或其他 UI 库）。

- **C#**:
  - 请参考 `cs_demos/README.md` 中的说明，安装所需的 .NET 库和工具，包含图形界面所需的组件（如 WinForms 或 WPF）。

### 3. 运行示例

- **Python**：
  - **简单使用示例**：运行 Python 示例代码：
    ```bash
    python instance_segmentation_demo.py
    ```
  - **图形界面应用**：运行带图形界面的 Python 示例代码：
    ```bash
    python python_gui_example.py
    ```

- **C++**：
  - **简单使用示例**：按照 `C++/README.md` 中的步骤，编译并运行示例，获取推理结果。
  - **图形界面应用**：按照 `C++/README.md` 中的步骤，编译并运行带图形界面的 C++ 示例，打开图形界面，加载图像并查看推理结果。

- **C#**：
  - **简单使用示例**：按照 `C#/README.md` 中的步骤，运行 C# 示例，获取推理结果。
  - **图形界面应用**：按照 `C#/README.md` 中的步骤，运行带图形界面的 C# 示例，打开图形界面，加载图像并查看推理结果。

### 功能展示

每个示例展示了 **DaoAI World SDK** 的核心功能：如何使用深度学习模型进行推理，并获取结果。包括但不限于以下功能：

- **加载深度学习模型**：展示如何加载 DaoAI 提供的深度学习模型。
- **进行推理**：展示如何将数据输入模型并获取推理结果。
- **处理推理结果**：展示如何处理和解析模型输出的推理结果。
- **图形界面示例**（C++、C# 和 Python）：展示如何在桌面应用中使用 DaoAI World SDK，用户可以通过图形界面加载图像，并查看推理结果。图像处理结果会在界面上显示。


### 贡献

欢迎贡献！如果你有任何改进建议，或者发现 bug，欢迎提交 Issue 或 Pull Request。我们欢迎社区的参与来改进 **DaoAI World SDK 代码示例**。


### 许可证

本项目使用 [MIT License](LICENSE)。