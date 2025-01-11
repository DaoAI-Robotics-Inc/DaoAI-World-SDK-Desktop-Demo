# **DaoAI World SDK C++ 环境配置**

## **1. 安装最新版 DaoAI World SDK**
请参考以下链接：  
[DW_SDK Windows 安装包 — DaoAI World User Manual 2024.7 documentation](http://docs.welinkirt.com/daoai-world-user-manual/latest/develop/install.html#)

---
## **C++ 项目参考**




## **QT项目参考**
参考项目：`DW_SDK_Qt_Example`

### **代码使用步骤**
1. **打开项目**  
   打开 QtCreator，选择“打开已有项目”，并选中 `DW_SDK_Qt_Example` 下的 `CMakeLists.txt` 文件。  
   ![打开项目](image/open_qt.png)

2. **配置项目**  
   确保 Build 模式为 **Release**。  
   ![项目配置](image/prj_config.png)

3. **运行项目**  
   点击“运行”，开始运行项目。  
   ![运行项目](image/run.png)  

   将数据放置到您的 Build 目录下，例如：  
   `DW_SDK_Qt_Example\build\Desktop_Qt_6_5_3_MSVC2019_64bit-Release\bin\data`  
   ![数据目录](image/data.png)

   然后依次点击按钮，使用模型推理并获取结果：  
   ![运行结果](image/result.png)

---

## **新项目配置**

### **Qt 安装与新建项目**

#### 1. 安装 Qt（以 Qt6 为例）  
按照官网指南正确安装 Qt。

#### 2. 新建 Qt 项目  
打开 QtCreator，新建一个项目，选择 **Qt Widgets Application**：  
![Qt Widgets Application](image/Picture1.png)

#### 3. 设置项目名称与路径  
![设置项目名称与路径](image/Picture2.png)

#### 4. 选择构建系统为 CMake  
![选择 CMake 构建系统](image/Picture3.png)

#### 5. 完成构建  
点击“下一步”完成构建。  
![完成构建](image/Picture4.png)

---

### **选择 MSVC2019 构建套件**

#### 1. 设置构建套件为 MSVC2019  
![选择 MSVC2019 构建套件](image/Picture5.png)

#### 2. 点击“下一步”完成配置。

---

### **生成空工程并验证环境**

1. 在生成的空工程中，选择 **Release** 模式并生成。  
2. 如果空工程生成成功，则表示 C++ 环境配置正确无误。

> **注意**：  
> 笔者使用 **Qt6** 构建工程（Qt5 亦可，CMake 配置略有不同，但操作基本一致）。

---

### **自动生成基础 `CMakeLists.txt`**

Qt 会自动生成基础的 `CMakeLists.txt`，如下所示：  
![CMakeLists.txt](image/Picture6.png)

---

## **CMake 配置关键点**

在 CMake 的红框部分，请注意以下配置：  

1. 指定 C++ 标准为 **C++17**。  
2. 设置 DaoAI World SDK 的安装目录。  
3. 指定 DaoAI World SDK 的头文件目录。  
4. 指定 DaoAI World SDK 的库文件目录（Lib）。  
5. 将构建模式设为 **Release**。

---

## **完成环境配置，开始编程**

完成以上环境配置后，您即可开始编程开发。


---

# **DaoAI World SDK C++ Environment Setup**

## **1. Install the Latest Version of DaoAI World SDK**
Refer to the following link for installation details:  
[DW_SDK Windows Installer — DaoAI World User Manual 2024.7 documentation](http://docs.welinkirt.com/daoai-world-user-manual/latest/develop/install.html#)

---

## **QT Application Code Reference**
Reference project: `DW_SDK_Qt_Example`

### **Steps to Use the Code**
1. **Open the Project**  
   Open QtCreator, select "Open Project," and choose the `CMakeLists.txt` file in the `DW_SDK_Qt_Example` directory.  
   ![Open Project](image/open_qt.png)

2. **Configure the Project**  
   Ensure the build mode is set to **Release**.  
   ![Configure Project](image/prj_config.png)

3. **Run the Project**  
   Click "Run" to start the project.  
   ![Run Project](image/run.png)  

   Place your data files in the build directory, such as:  
   `DW_SDK_Qt_Example\build\Desktop_Qt_6_5_3_MSVC2019_64bit-Release\bin\data`  
   ![Data Directory](image/data.png)

   Then click the buttons sequentially to perform model inference and obtain results:  
   ![Results](image/result.png)

---

## **New Project Setup**

### **Installing Qt and Creating a New Project**

#### 1. Install Qt (Using Qt6 as an Example)  
Follow the official guide to install Qt correctly.

#### 2. Create a New Qt Project  
Open QtCreator and create a new project. Select **Qt Widgets Application**:  
![Qt Widgets Application](image/Picture1.png)

#### 3. Set Project Name and Path  
![Set Project Name and Path](image/Picture2.png)

#### 4. Choose the Build System as CMake  
![Choose CMake Build System](image/Picture3.png)

#### 5. Complete the Build  
Click "Next" to complete the build process.  
![Complete Build](image/Picture4.png)

---

### **Selecting MSVC2019 Build Kit**

#### 1. Set the Build Kit to MSVC2019  
![Select MSVC2019 Build Kit](image/Picture5.png)

#### 2. Click "Next" to finish the setup.

---

### **Generate an Empty Project and Verify the Environment**

1. In the generated empty project, select **Release** mode and build the project.  
2. If the empty project builds successfully, the C++ environment is properly configured.

> **Note**:  
> This guide uses **Qt6** for project building (Qt5 is also supported, with slight differences in CMake configuration).

---

### **Auto-Generated `CMakeLists.txt`**

Qt will automatically generate a basic `CMakeLists.txt` file, as shown below:  
![CMakeLists.txt](image/Picture6.png)

---

## **Key Points for CMake Configuration**

Pay attention to the following in the highlighted sections of the `CMakeLists.txt` file:  

1. Specify the C++ standard as **C++17**.  
2. Set the installation directory for DaoAI World SDK.  
3. Specify the header file directory for DaoAI World SDK.  
4. Specify the library (Lib) directory for DaoAI World SDK.  
5. Set the build mode to **Release**.

---

## **Start Programming**

Once the environment is configured, you are ready to start programming.
