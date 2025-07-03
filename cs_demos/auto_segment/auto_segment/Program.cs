using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Emgu.CV;
using Emgu.CV.UI;
using Emgu.CV.Structure;
using Emgu.CV.CvEnum;
using Newtonsoft.Json;
using DaoAI.DeepLearningCLI;

// 添加别名以避免 Application 命名冲突
using WinApp = System.Windows.Forms.Application;
using DaoAIApp = DaoAI.DeepLearningCLI.Application;

namespace AutoSegmentationApp
{
    // 主窗体：内含 ImageBox 用于显示图片及处理鼠标事件
    public class MainForm : Form
    {
        // 用于记录点击点和框选区域
        private List<DaoAI.DeepLearningCLI.Point> clickedPoints;
        private List<DaoAI.DeepLearningCLI.Box> drawnBoxes;
        private bool isDrawing;
        private bool isClickDetected; // 判断是否为单击
        private DaoAI.DeepLearningCLI.Point startPoint;
        private const int DragThreshold = 5;

        // 图像与模型相关
        private Mat originalImage;
        private DaoAI.DeepLearningCLI.Vision.AutoSegmentation model;
        private DaoAI.DeepLearningCLI.Vision.ImageEmbedding embedding;
        // 请根据实际情况修改图片和模型路径
        private readonly string imagePath = "../../../../../../../Data/instance_segmentation_img.jpg";
        private readonly string modelPath = "../../../../../../../Data/auto_segment.dwm";

        // 使用 Emgu CV 的 ImageBox 控件
        private ImageBox imageBox;

        public MainForm()
        {
            this.Text = "Image Viewer";
            this.StartPosition = FormStartPosition.CenterScreen;
            this.KeyPreview = true;
            this.KeyDown += MainForm_KeyDown;

            clickedPoints = new List<DaoAI.DeepLearningCLI.Point>();
            drawnBoxes = new List<DaoAI.DeepLearningCLI.Box>();
            isDrawing = false;
            isClickDetected = false;

            // 创建 ImageBox 控件，并设置充满窗口
            imageBox = new ImageBox
            {
                Dock = DockStyle.Fill,
                FunctionalMode = ImageBox.FunctionalModeOption.Minimum
            };
            // 绑定鼠标事件
            imageBox.MouseDown += ImageBox_MouseDown;
            imageBox.MouseMove += ImageBox_MouseMove;
            imageBox.MouseUp += ImageBox_MouseUp;
            imageBox.MouseClick += ImageBox_MouseClick; // 用于右键单击

            this.Controls.Add(imageBox);
        }

        private void MainForm_Load(object sender, EventArgs e)
        {
            // 初始化深度学习 SDK（使用 DaoAIApp 别名）
            DaoAIApp.initialize();

            // 加载图像
            originalImage = CvInvoke.Imread(imagePath);
            if (originalImage.IsEmpty)
            {
                MessageBox.Show("Error loading image: " + imagePath);
                this.Close();
                return;
            }

            // 加载模型并生成图像嵌入
            try
            {
                model = new DaoAI.DeepLearningCLI.Vision.AutoSegmentation(modelPath, DaoAI.DeepLearningCLI.DeviceType.GPU, -1);
                var sdkImage = new DaoAI.DeepLearningCLI.Image(imagePath);
                embedding = model.generateImageEmbeddings(sdkImage);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Model initialization failed: " + ex.Message);
                this.Close();
                return;
            }

            // 显示原始图像
            imageBox.Image = originalImage.Clone();
        }

        private void MainForm_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Escape)
                this.Close();
            else if (e.KeyCode == Keys.R)
                ResetState();
        }

        private void ImageBox_MouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                isDrawing = true;
                isClickDetected = true; // 初始认为为单击
                startPoint = new DaoAI.DeepLearningCLI.Point(e.X, e.Y,0, "");
            }
        }

        private void ImageBox_MouseMove(object sender, MouseEventArgs e)
        {
            if (!isDrawing)
                return;

            if (Math.Abs(e.X - startPoint.X) > DragThreshold || Math.Abs(e.Y - startPoint.Y) > DragThreshold)
            {
                isClickDetected = false; // 超过阈值，认为是拖拽
                // 在克隆的图像上绘制矩形
                Mat temp = originalImage.Clone();
                Rectangle rect = new Rectangle(new System.Drawing.Point((int)startPoint.X, (int)startPoint.Y),
                                               new Size(e.X - (int)startPoint.X, e.Y - (int)startPoint.Y));
                CvInvoke.Rectangle(temp, rect, new MCvScalar(0, 255, 0), 2);
                imageBox.Image = temp;
            }
        }

        private void ImageBox_MouseUp(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                isDrawing = false;
                if (isClickDetected)
                {
                    // 单击：添加点击点，标签 "1"
                    clickedPoints.Add(new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "1"));
                }
                else
                {
                    // 拖拽：记录矩形区域
                    var endPoint = new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "");
                    drawnBoxes.Add(new DaoAI.DeepLearningCLI.Box(startPoint, endPoint, 0));
                }
                RunInference();
            }
        }

        private void ImageBox_MouseClick(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Right)
            {
                // 右键点击：添加点击点，标签 "0"
                clickedPoints.Add(new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "0"));
                RunInference();
            }
        }

        /// <summary>
        /// 调用模型推理，并更新显示结果，同时保存 JSON 文件
        /// </summary>
        private void RunInference()
        {
            if (model == null || embedding == null)
                return;

            try
            {
                // 转换 List 到二维数组，满足 SDK 接口要求
                DaoAI.DeepLearningCLI.Point[][] clickedPointsArray = new DaoAI.DeepLearningCLI.Point[1][];
                clickedPointsArray[0] = clickedPoints.ToArray();
                DaoAI.DeepLearningCLI.Box[][] drawnBoxesArray = new DaoAI.DeepLearningCLI.Box[1][];
                drawnBoxesArray[0] = drawnBoxes.ToArray();
                var embeddingArray = new DaoAI.DeepLearningCLI.Vision.ImageEmbedding[] { embedding };

                var result = model.inference(embeddingArray, drawnBoxesArray, clickedPointsArray);
                SaveResult(result[0]);
                UpdateMaskDisplay(result[0].mask);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Inference error: " + ex.Message);
            }
        }

        /// <summary>
        /// 保存结果 JSON 到与图像相同目录下的 result.json 文件
        /// </summary>
        /// <param name="result">模型推理结果</param>
        private void SaveResult(DaoAI.DeepLearningCLI.Vision.AutoSegmentationResult result)
        {
            try
            {
                // Option 1: Write the raw JSON string directly.
                string json = result.toJSONString();

                // Option 2: If you need pretty-printed JSON, parse and reformat it:
                // var parsedJson = Newtonsoft.Json.Linq.JToken.Parse(result.toJSONString());
                // string json = parsedJson.ToString(Newtonsoft.Json.Formatting.Indented);

                string directory = Path.GetDirectoryName(imagePath);
                string outputPath = Path.Combine(directory, "result.json");
                File.WriteAllText(outputPath, json);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Save error: " + ex.Message);
            }
        }

        /// <summary>
        /// 根据模型返回的 mask 更新显示图像（原图与 mask 混合）
        /// </summary>
        /// <param name="mask">模型输出的 mask</param>
        private void UpdateMaskDisplay(Mask mask)
        {
            Mat maskMat = ConvertMaskToMat(mask).Clone();
            Mat maskedImage = new Mat();
            originalImage.CopyTo(maskedImage, maskMat);
            Mat blended = new Mat();
            CvInvoke.AddWeighted(originalImage, 0.3, maskedImage, 0.7, 0, blended);
            imageBox.Image = blended;
        }

        /// <summary>
        /// 将 SDK 的 mask 转换为 OpenCV Mat 格式
        /// </summary>
        /// <param name="mask">模型输出的 mask</param>
        /// <returns>转换后的 Mat 对象</returns>
        private Mat ConvertMaskToMat(Mask mask)
        {
            Mat mat = new Mat(mask.height, mask.width, DepthType.Cv8U, 1);
            mat.SetTo(mask.toImage().data);
            return mat;
        }

        /// <summary>
        /// 重置状态：清除所有记录的点和框，并恢复原始图像显示
        /// </summary>
        private void ResetState()
        {
            clickedPoints.Clear();
            drawnBoxes.Clear();
            imageBox.Image = originalImage.Clone();
        }

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            MainForm_Load(this, e);
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            WinApp.EnableVisualStyles();
            WinApp.SetCompatibleTextRenderingDefault(false);
            WinApp.Run(new MainForm());
        }
    }
}
