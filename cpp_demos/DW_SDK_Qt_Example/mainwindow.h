#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <dwsdk/model.h>
#include <dwsdk/prediction.h>
#include <dwsdk/utils.h>
#include <string>
#include <memory>
#include <QMainWindow>
#include <QGraphicsScene>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private:
    void displayImage(QImage image);

private slots:
    void on_pushButton_LoadModel_clicked();

    void on_pushButton_LoadImage_clicked();

    void on_pushButton_Detection_clicked();

    void on_pushButton_result_clicked();

private:
    Ui::MainWindow *ui;
    QGraphicsScene *scene;

    /*
     * 为方便进行演示。使用智能指针 作为成员变量
    */
    std::unique_ptr<DaoAI::DeepLearning::Image> m_daoai_image_ptr;
    std::unique_ptr<DaoAI::DeepLearning::Vision::ObjectDetection> m_model_ptr;
    std::unique_ptr<DaoAI::DeepLearning::Vision::ObjectDetectionResult> m_result_ptr;
};
#endif // MAINWINDOW_H
