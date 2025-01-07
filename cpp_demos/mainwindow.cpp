#include "mainwindow.h"
#include "./ui_mainwindow.h"


#include <fstream>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
    ,m_daoai_image_ptr(nullptr)
    ,m_model_ptr(nullptr)
    ,m_result_ptr(nullptr)
{
    ui->setupUi(this);

    scene = new QGraphicsScene;
    ui->graphicsView->setScene(scene);
    /*
     * step 0: SDK 初始化
     */
    DaoAI::DeepLearning::initialize();
}

MainWindow::~MainWindow()
{
    delete ui;
}



void MainWindow::on_pushButton_LoadImage_clicked()
{
    try {
        /*
         * step 1: 选择图像路径
         */
        std::string image_path  = "./data/supervised_defect_segmentation_img.png";

        /*
         * step 2: 调用 DaoAI API 加载图像
         */
        m_daoai_image_ptr = std::make_unique<DaoAI::DeepLearning::Image>(image_path);


        ui->textBrowser->append("clicked button \"Load Image\" OK."); //显示进度

        QImage image(QString(image_path.c_str()));
        displayImage(image); //显示图像

    } catch (...) {
        ui->textBrowser->append("clicked button \"Load Image\" Failed");
    }
}



void MainWindow::on_pushButton_LoadModel_clicked()
{
    try {
        /*
         * step 3: 选择模型路径.
         *
         * p.s.模型是从 DaoAI world 网页端训练完成后下载下来的
         */
        std::string model_path = "./data/supervised_defect_segmentation_model.zip";

        /*
         * step 4: 调用 DaoAI API 加载模型
         * p.s.此例子使用的是监督缺陷检测模型
         */

        //实例分割
        //DaoAI::DeepLearning::Vision::InstanceSegmentation model(model_path);

        //关键点检测
        //DaoAI::DeepLearning::Vision::KeypointDetection model(model_path);
        //m_model_ptr = std::make_unique<DaoAI::DeepLearning::Vision::KeypointDetection>(model_path);

        //图像分类
        //DaoAI::DeepLearning::Vision::Classification model(model_path);
        //m_model_ptr = std::make_unique<DaoAI::DeepLearning::Vision::Classification>(model_path);

        //目标检测
        //DaoAI::DeepLearning::Vision::ObjectDetection model(model_path);
        m_model_ptr = std::make_unique<DaoAI::DeepLearning::Vision::ObjectDetection>(model_path);

        //非监督缺陷检测
        //DaoAI::DeepLearning::Vision::UnsupervisedDefectSegmentation model(model_path);

        //监督缺陷检测
        //m_model_ptr = std::make_unique<DaoAI::DeepLearning::Vision::SupervisedDefectSegmentation>(model_path);

        //OCR
        //DaoAI::DeepLearning::Vision::OCR model(model_path);

        //定位模型 (只在工业版支持)
        //DaoAI::DeepLearning::Vision::Positioning model(model_path);

        //漏错装检测 (只在工业版支持)
        //DaoAI::DeepLearning::Vision::PresenceChecking model(model_path);

        ui->textBrowser->append("clicked button \"Load Model\" OK.");

    } catch (...) {
        ui->textBrowser->append("clicked button \"Load Model\" Failed !");
    }
}

void MainWindow::on_pushButton_Detection_clicked()
{
    try {
        /*
         * step 5: 使用深度学习模型进行预测
         * p.s.此例子使用的是缺陷检测模型
         */
        if(!m_daoai_image_ptr && !m_model_ptr) //检查是否为空
            return;

        //实例分割
        //DaoAI::DeepLearning::Vision::InstanceSegmentationResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //关键点检测
        //DaoAI::DeepLearning::Vision::KeypointDetectionResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //图像分类
        //DaoAI::DeepLearning::Vision::ClassificationResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //目标检测
        DaoAI::DeepLearning::Vision::ObjectDetectionResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //非监督缺陷检测
        //DaoAI::DeepLearning::Vision::UnsupervisedDefectSegmentationResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //监督缺陷检测
        //DaoAI::DeepLearning::Vision::SupervisedDefectSegmentationResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //OCR
        //::DeepLearning::Vision::OCRResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //定位模型 (只在工业版支持)
        //DaoAI::DeepLearning::Vision::PositioningResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        //漏错装检测 (只在工业版支持)
        //DaoAI::DeepLearning::Vision::PresenceCheckingResult prediction = m_model_ptr->inference(*m_daoai_image_ptr);

        /*
         * step 6: 获取到结果模型
         * p.s.此例子使用的是监督缺陷检测模型
         */
        m_result_ptr = std::make_unique<DaoAI::DeepLearning::Vision::ObjectDetectionResult>(prediction);
        ui->textBrowser->append("clicked button \"Detection image\" OK.");

    } catch (...) {
        ui->textBrowser->append("clicked button \"Detection image\" Failed !");
    }

}

void MainWindow::on_pushButton_result_clicked()
{
    /*
     * step 7: 使用深度学习模型进行预测
     * p.s.此例子使用的是监督缺陷检测模型
     */
    if(!m_result_ptr) //检查是否为空
        return;

    DaoAI::DeepLearning::Image result = DaoAI::DeepLearning::Utils::visualize(*m_daoai_image_ptr, *m_result_ptr);   //降结果输出到图片上

    //获取到json结果
    std::string jsonResult = m_result_ptr->toJSONString();
    ui->textBrowser->append(jsonResult.c_str());

    //获取到结果然后转为QImage 并显示
    uint8_t* data = result.getData();
    int wd = result.height;
    int ht = result.width;
    DaoAI::DeepLearning::Image::Type type = result.type;
    QImage qimage =  QImage(data,ht,wd,QImage::Format_BGR888);
    displayImage(qimage);
}


void MainWindow::displayImage(QImage image)
{
    QPixmap scalePixmap = QPixmap::fromImage(image);
    // 计算缩放比例
    double scale = 1.0;
    double scaleX = static_cast<double>(ui->graphicsView->width()) / (scalePixmap.width() + 1);
    double scaleY = static_cast<double>(ui->graphicsView->height()) / (scalePixmap.height() + 1);
    if (scaleX > scaleY)
    {
        scale = scaleY;
    }
    else
    {
        scale = scaleX;
    }

    // 缩放
    scalePixmap = scalePixmap.scaled(scalePixmap.width() * scale, scalePixmap.height() * scale, Qt::KeepAspectRatio);
    scene->addPixmap(scalePixmap);

    ui->graphicsView->fitInView(ui->graphicsView->sceneRect(), Qt::KeepAspectRatio);
    ui->graphicsView->setAlignment(Qt::AlignCenter);

    scene->addPixmap(scalePixmap);
    ui->graphicsView->setScene(scene);
}




