using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using HalconDotNet;
using DaoAI.DeepLearningCLI;
using System.Security;
using System.Runtime.InteropServices;
using System;
using System.Reflection;
using System.Windows.Media.Media3D;
using DaoAI.DeepLearningCLI.Vision;
using System.Drawing;
using System.Diagnostics;

namespace halcon_sdk_demo
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
        }
        HObject hImage = new HObject();

        // 按钮点击事件：加载并显示图像
        private void LoadImageButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                // 创建 OpenFileDialog 实例
                Microsoft.Win32.OpenFileDialog openFileDialog = new Microsoft.Win32.OpenFileDialog();

                // 设置文件过滤器，限制用户只能选择图像文件
                openFileDialog.Filter = "Image Files (*.jpg; *.png; *.bmp; *.tif)|*.jpg; *.png; *.bmp; *.tif|All Files (*.*)|*.*";

                // 显示文件选择对话框
                bool? result = openFileDialog.ShowDialog();

                // 如果用户选择了文件并点击了“打开”
                if (result == true)
                {
                    // 获取用户选择的文件路径
                    string filePath = openFileDialog.FileName;

                    // 使用 Halcon 读取图像
                   // HImage hImage;
                    HOperatorSet.ReadImage(out hImage, filePath);

                    // 在 Halcon 显示控件中显示图像
                    HalconDisplay.HalconWindow.DispObj(hImage);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading image: {ex.Message}");
            }
        }

        private async void LoadModelButton_Click(object sender, RoutedEventArgs e)
        {
            // 禁用按钮，防止重复点击
            LoadModelButton.IsEnabled = false;

            // 显示进度条
            LoadProgressBar.Visibility = Visibility.Visible;
            LoadProgressBar.IsIndeterminate = true; // 不确定进度模式

            try
            {
                // 在后台线程中执行耗时任务
                await Task.Run(() => LoadModelAsync());

                // 任务完成后更新 UI
                MessageBox.Show("模型加载完成！");
            }
            catch (Exception ex)
            {
                // 处理异常
                MessageBox.Show($"加载模型时出错: {ex.Message}");
            }
            finally
            {
                // 隐藏进度条
                LoadProgressBar.Visibility = Visibility.Collapsed;

                // 重新启用按钮
                LoadModelButton.IsEnabled = true;
            }
        }
        private void LoadModelAsync()
        {
            // 初始化
            DaoAI.DeepLearningCLI.Application.initialize();

            // 加载模型
            superviseDecetsegmentation_Ins.Instance.Load(@"C:\Users\daoai\Documents\DWSDK_Demo\data\halcon_sdk_demo_model.dwm");

        }

        private void InferenceButton_Click(object sender, RoutedEventArgs e)
        {
            System.Diagnostics.Stopwatch stopwatch = new Stopwatch();
            stopwatch.Start();
            DaoAI.DeepLearningCLI.Image image = Hobject2Image(hImage);
            stopwatch.Stop();
            MessageBox.Show(stopwatch.ElapsedMilliseconds.ToString());
            SupervisedDefectSegmentationResult result = superviseDecetsegmentation_Ins.Instance.superviseddefectsegmentation.inference(image);
            
            var a = result.masks["hanfeng"].toImage();
            DWres2HalconRegion(a);
            hImage.Dispose();

        }

        private unsafe DaoAI.DeepLearningCLI.Image Hobject2Image(HObject Himage)
        {
            HTuple channels;
            HOperatorSet.CountChannels(Himage, out channels);
            DaoAI.DeepLearningCLI.Image image;

            Stopwatch sw = Stopwatch.StartNew();

            if (channels == 3)
            {
                HTuple pointerR, pointerG, pointerB, type, width, height;
                HOperatorSet.GetImagePointer3(Himage, out pointerR, out pointerG, out pointerB, out type, out width, out height);
                int totalPixels = width * height;
                byte[] interleavedBytes = new byte[totalPixels * 3];

                fixed (byte* pInterleaved = interleavedBytes)
                {
                    byte* pDest = pInterleaved;
                    byte* pRed = (byte*)pointerR.IP;
                    byte* pGreen = (byte*)pointerG.IP;
                    byte* pBlue = (byte*)pointerB.IP;

                    // 使用指针直接复制和交错 RGB 数据
                    for (int i = 0; i < totalPixels; i++)
                    {
                        *pDest++ = pRed[i];     // Red
                        *pDest++ = pGreen[i];   // Green
                        *pDest++ = pBlue[i];    // Blue
                    }
                }

                image = new DaoAI.DeepLearningCLI.Image(height, width, DaoAI.DeepLearningCLI.Image.Type.RGB, interleavedBytes);
            }
            else
            {
                HTuple pointer, type, width, height;
                HOperatorSet.GetImagePointer1(Himage, out pointer, out type, out width, out height);
                int totalPixels = width * height;
                byte[] interleavedBytes = new byte[totalPixels * 3];

                fixed (byte* pInterleaved = interleavedBytes)
                {
                    byte* pDest = pInterleaved;
                    byte* pGray = (byte*)pointer.IP;

                    // 使用指针直接复制和交错灰度数据（模拟 RGB）
                    for (int i = 0; i < totalPixels; i++)
                    {
                        byte grayValue = pGray[i];
                        *pDest++ = grayValue;     // Red
                        *pDest++ = grayValue;   // Green
                        *pDest++ = grayValue;    // Blue
                    }
                }

                image = new DaoAI.DeepLearningCLI.Image(height, width, DaoAI.DeepLearningCLI.Image.Type.RGB, interleavedBytes);
            }

            sw.Stop();
            //MessageBox.Show($"Total conversion time: {sw.ElapsedMilliseconds} ms");
            return image;
        }

        private void DWres2HalconRegion(DaoAI.DeepLearningCLI.Image maskImg) 
        {
            HObject ho_Image,res_region;
            unsafe
            {
                fixed (byte* ptr = maskImg.data)
                {
                    byte* gPtr = ptr;          // 通道起始位置
                    HTuple gPointer = new HTuple((IntPtr)gPtr);
                    HOperatorSet.GenImage1(out ho_Image, "byte", maskImg.width, maskImg.height, gPointer);
                }
            }
            // 使用阈值分割提取白色区域
           
            HOperatorSet.Threshold(ho_Image, out res_region, 200, 255); // 200-255是白色区域的灰度范围

            // 设置区域显示属性
            HalconDisplay.HalconWindow.SetColor("cyan"); // 设置区域颜色为绿色
            HalconDisplay.HalconWindow.SetDraw("margin");   // 设置填充模式
            HalconDisplay.HalconWindow.SetLineWidth(10);   // 设置边框宽度

            // 显示区域
            HalconDisplay.HalconWindow.DispObj(res_region);

        }
    }
}