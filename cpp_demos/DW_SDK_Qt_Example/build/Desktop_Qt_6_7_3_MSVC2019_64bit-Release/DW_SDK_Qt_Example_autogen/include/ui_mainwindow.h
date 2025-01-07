/********************************************************************************
** Form generated from reading UI file 'mainwindow.ui'
**
** Created by: Qt User Interface Compiler version 6.7.3
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_MAINWINDOW_H
#define UI_MAINWINDOW_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QGraphicsView>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QMenuBar>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QTextBrowser>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_MainWindow
{
public:
    QWidget *centralwidget;
    QHBoxLayout *horizontalLayout;
    QVBoxLayout *verticalLayout;
    QGraphicsView *graphicsView;
    QTextBrowser *textBrowser;
    QVBoxLayout *verticalLayout_2;
    QPushButton *pushButton_LoadImage;
    QPushButton *pushButton_LoadModel;
    QPushButton *pushButton_Detection;
    QPushButton *pushButton_result;
    QSpacerItem *verticalSpacer;
    QMenuBar *menubar;
    QStatusBar *statusbar;

    void setupUi(QMainWindow *MainWindow)
    {
        if (MainWindow->objectName().isEmpty())
            MainWindow->setObjectName("MainWindow");
        MainWindow->resize(800, 600);
        centralwidget = new QWidget(MainWindow);
        centralwidget->setObjectName("centralwidget");
        horizontalLayout = new QHBoxLayout(centralwidget);
        horizontalLayout->setObjectName("horizontalLayout");
        verticalLayout = new QVBoxLayout();
        verticalLayout->setObjectName("verticalLayout");
        graphicsView = new QGraphicsView(centralwidget);
        graphicsView->setObjectName("graphicsView");

        verticalLayout->addWidget(graphicsView);

        textBrowser = new QTextBrowser(centralwidget);
        textBrowser->setObjectName("textBrowser");

        verticalLayout->addWidget(textBrowser);

        verticalLayout->setStretch(0, 4);
        verticalLayout->setStretch(1, 1);

        horizontalLayout->addLayout(verticalLayout);

        verticalLayout_2 = new QVBoxLayout();
        verticalLayout_2->setObjectName("verticalLayout_2");
        pushButton_LoadImage = new QPushButton(centralwidget);
        pushButton_LoadImage->setObjectName("pushButton_LoadImage");

        verticalLayout_2->addWidget(pushButton_LoadImage);

        pushButton_LoadModel = new QPushButton(centralwidget);
        pushButton_LoadModel->setObjectName("pushButton_LoadModel");

        verticalLayout_2->addWidget(pushButton_LoadModel);

        pushButton_Detection = new QPushButton(centralwidget);
        pushButton_Detection->setObjectName("pushButton_Detection");

        verticalLayout_2->addWidget(pushButton_Detection);

        pushButton_result = new QPushButton(centralwidget);
        pushButton_result->setObjectName("pushButton_result");

        verticalLayout_2->addWidget(pushButton_result);

        verticalSpacer = new QSpacerItem(20, 40, QSizePolicy::Policy::Minimum, QSizePolicy::Policy::Expanding);

        verticalLayout_2->addItem(verticalSpacer);


        horizontalLayout->addLayout(verticalLayout_2);

        horizontalLayout->setStretch(0, 5);
        horizontalLayout->setStretch(1, 1);
        MainWindow->setCentralWidget(centralwidget);
        menubar = new QMenuBar(MainWindow);
        menubar->setObjectName("menubar");
        menubar->setGeometry(QRect(0, 0, 800, 19));
        MainWindow->setMenuBar(menubar);
        statusbar = new QStatusBar(MainWindow);
        statusbar->setObjectName("statusbar");
        MainWindow->setStatusBar(statusbar);

        retranslateUi(MainWindow);

        QMetaObject::connectSlotsByName(MainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *MainWindow)
    {
        MainWindow->setWindowTitle(QCoreApplication::translate("MainWindow", "DW_SDK_Qt_Example", nullptr));
        pushButton_LoadImage->setText(QCoreApplication::translate("MainWindow", "\345\212\240\350\275\275\345\233\276\347\211\207", nullptr));
        pushButton_LoadModel->setText(QCoreApplication::translate("MainWindow", "\345\212\240\350\275\275\346\250\241\345\236\213", nullptr));
        pushButton_Detection->setText(QCoreApplication::translate("MainWindow", "\346\243\200\346\265\213\345\233\276\345\203\217", nullptr));
        pushButton_result->setText(QCoreApplication::translate("MainWindow", "\346\230\276\347\244\272\347\273\223\346\236\234", nullptr));
    } // retranslateUi

};

namespace Ui {
    class MainWindow: public Ui_MainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_MAINWINDOW_H
