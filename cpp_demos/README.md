# **DaoAI World SDK C++ 环境配置**

## **1. 正确安装最新版 DaoAI World SDK**
参考网站：
[DW_SDK Windows安装包 — DaoAI World User Manual 2024.7 documentation](http://docs.welinkirt.com/daoai-world-user-manual/latest/develop/install.html#)

---

## **2. CMake 和 Qt 环境配置**

### **Qt 安装与新建项目**

#### 1. 正确安装 Qt（以 Qt6 为例）

#### 2. 新建 Qt 项目
选择 **Qt Widgets Application**：

![Qt Widgets Application](image/Picture1.png)

#### 3. 项目名称和路径设置

![Project Name and Path](image/Picture2.png)

#### 4. 构建系统选择 CMake

![CMake Build System](image/Picture3.png)

#### 5. 点击下一步完成构建

![Complete Build](image/Picture4.png)

---

### **选择 MSVC2019 构建套件**

#### 1. 设置构建套件为 MSVC2019

![MSVC2019 Kit](image/Picture5.png)

#### 2. 点击下一步完成构建。

---

### **生成空工程并验证环境**

#### 1. 在生成的空工程中选择 **Release** 并生成。

#### 2. 如果空工程生成成功，即代表 C++ 环境配置无误。

> **注意**：
> 笔者使用的是 **Qt6** 构建工程（Qt5 亦可，CMake 略有不同，但操作一致）。

---

### **自动生成基础 `CMakeLists.txt`**

Qt 会自动生成基础的 `CMakeLists.txt`，如下图所示：

![CMakeLists.txt](image/Picture6.png)

---

## **CMake 配置关键点**

在 CMake 的红框部分注意以下项：

1. 指定 C++ 标准为 **C++17**
2. 设置 DaoAI World SDK 的安装目录
3. 指定 DaoAI World SDK 头文件目录
4. 指定 DaoAI World SDK Lib 库目录
5. 将构建环境设为 **Release**

---

## **完成环境配置，开始编程**

设置好以上环境后，即可开始编程。

### **代码参考**
请参考项目：
DW_SDK_Qt_Example

---

# **DaoAI World SDK C++ Environment Setup**

## **1. Install the Latest Version of DaoAI World SDK**
Refer to the documentation:
[DW_SDK Windows Installation Package — DaoAI World User Manual 2024.7 documentation](http://docs.welinkirt.com/daoai-world-user-manual/latest/develop/install.html#)

---

## **2. CMake and Qt Environment Configuration**

### **Qt Installation and New Project Setup**

#### 1. Correctly Install Qt (Using Qt6 as an Example)

#### 2. Create a New Qt Project
Select **Qt Widgets Application**:

![Qt Widgets Application](image/Picture1.png)

#### 3. Set Project Name and Path

![Project Name and Path](image/Picture2.png)

#### 4. Select CMake as the Build System

![CMake Build System](image/Picture3.png)

#### 5. Click "Next" to Complete the Build

![Complete Build](image/Picture4.png)

---

### **Select MSVC2019 Build Kit**

#### 1. Configure MSVC2019 as the Build Kit

![MSVC2019 Kit](image/Picture5.png)

#### 2. Click "Next" to Complete the Build.

---

### **Generate an Empty Project and Verify the Environment**

#### 1. In the generated empty project, select **Release** and build.

#### 2. If the empty project builds successfully, the C++ environment is correctly configured.

> **Note**:
> The example uses **Qt6** to create the project (Qt5 is also supported with slight differences in CMake, but the operations are similar).

---

### **Automatically Generated Basic `CMakeLists.txt`**

Qt will automatically generate a basic `CMakeLists.txt` file as shown below:

![CMakeLists.txt](image/Picture6.png)

---

## **Key Points for CMake Configuration**

In the highlighted parts of the CMake file, ensure the following settings:

1. Specify the C++ standard as **C++17**
2. Set the installation directory of DaoAI World SDK
3. Specify the header file directory of DaoAI World SDK
4. Specify the library directory of DaoAI World SDK
5. Set the build environment to **Release**

---

## **Complete the Configuration and Start Programming**

Once the above environment is set up, you can start programming.

### **Code Reference**
Refer to the project:
DW_SDK_Qt_Example
