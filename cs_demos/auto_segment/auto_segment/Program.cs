using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using Emgu.CV;
using Emgu.CV.CvEnum;
using Emgu.CV.Structure;
using Emgu.CV.UI;
using Newtonsoft.Json;
using System.Windows.Forms;
using DaoAI.DeepLearningCLI;

namespace AutoSegmentationApp
{
    public class AutoSegmentationProcessor
    {
        private List<System.Drawing.Point> clickedPoints = new List<System.Drawing.Point>();
        private List<System.Drawing.Box> drawnBoxes = new List<System.Drawing.Box>();
        private bool isDrawing = false;
        private System.Drawing.Point startPoint;
        private Mat originalImage;
        private DaoAI.DeepLearningCLI.Vision.AutoSegmentation model;
        private DaoAI.DeepLearningCLI.Vision.ImageEmbedding embedding;
        private const int DragThreshold = 5;
        private const string WindowName = "Image Viewer";

        private readonly string imagePath = @"data\instance_segmentation_img.jpg";
        private readonly string modelPath = @"data\auto_segment.dwm";

        public void Run()
        {
            // 初始化深度学习SDK
            DaoAI.DeepLearningCLI.Application.initialize(false,0);

            // 加载图像
            originalImage = CvInvoke.Imread(imagePath);
            if (originalImage.IsEmpty)
            {
                Console.WriteLine($"Error loading image: {imagePath}");
                return;
            }

            try
            {
                // 加载模型
                model = new DaoAI.DeepLearningCLI.Vision.AutoSegmentation(modelPath, DaoAI.DeepLearningCLI.DeviceType.GPU, -1);

                var sdkImage = new DaoAI.DeepLearningCLI.Image(imagePath);
                embedding = model.GenerateImageEmbeddings(sdkImage);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Model initialization failed: {ex.Message}");
                return;
            }

            // 创建UI窗口
            using (var viewer = new ImageViewer())
            {
                viewer.Image = originalImage;
                viewer.Text = WindowName;

                viewer.MouseDown += OnMouseDown;
                viewer.MouseMove += OnMouseMove;
                viewer.MouseUp += OnMouseUp;

                while (true)
                {
                    var key = CvInvoke.WaitKey(1);
                    if (key == 27) break; // ESC退出
                    if (key == 'r' || key == 'R') ResetState();
                }
            }

            model.Dispose();
        }

        private void OnMouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                isDrawing = true;
                startPoint = e.Location;
            }
        }

        private void OnMouseMove(object sender, MouseEventArgs e)
        {
            if (!isDrawing) return;

            var currentImage = originalImage.Clone();
            if (Math.Abs(e.X - startPoint.X) > DragThreshold ||
                Math.Abs(e.Y - startPoint.Y) > DragThreshold)
            {
                CvInvoke.Rectangle(currentImage,
                    new Rectangle(startPoint, new Size(e.X - startPoint.X, e.Y - startPoint.Y)),
                    new MCvScalar(0, 255, 0), 2);
                UpdateDisplay(currentImage);
            }
        }

        private void OnMouseUp(object sender, MouseEventArgs e)
        {
            isDrawing = false;

            if (e.Button == MouseButtons.Left)
            {
                if (startPoint == e.Location)
                {
                    clickedPoints.Add(new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "1"));
                }
                else
                {
                    drawnBoxes.Add(new DaoAI.DeepLearningCLI.Box(startPoint, e.Location));
                }
                RunInference();
            }
            else if (e.Button == MouseButtons.Right)
            {
                clickedPoints.Add(new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "0"));
                RunInference();
            }
        }

        private void RunInference()
        {
            if (model == null || embedding == null) return;

            try
            {
                var result = model.Inference(embedding, drawnBoxes, clickedPoints);
                SaveResult(result);
                UpdateMaskDisplay(result.Mask);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Inference error: {ex.Message}");
            }
        }

        private void UpdateMaskDisplay(Mask mask)
        {
            using (var maskImage = ConvertMaskToMat(mask))
            using (var maskedImage = new Mat())
            {
                CvInvoke.BitwiseAnd(originalImage, originalImage, maskedImage, maskImage);
                CvInvoke.AddWeighted(originalImage, 0.3, maskedImage, 0.7, 0, maskedImage);
                UpdateDisplay(maskedImage);
            }
        }

        private Mat ConvertMaskToMat(Mask mask)
        {
            var mat = new Mat(mask.height, mask.width, DepthType.Cv8U, 1);
            mat.SetTo(mask.toImage().data);
            return mat;
        }

        private void SaveResult(DaoAI.DeepLearningCLI.Vision.AutoSegmentationResult result)
        {
            try
            {
                var json = JsonConvert.SerializeObject(result, Formatting.Indented);
                var outputPath = Path.Combine(Path.GetDirectoryName(imagePath), "result.json");
                File.WriteAllText(outputPath, json);
                Console.WriteLine($"Result saved to: {outputPath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Save error: {ex.Message}");
            }
        }

        private void UpdateDisplay(Mat image)
        {
            CvInvoke.Imshow(WindowName, image);
        }

        private void ResetState()
        {
            clickedPoints.Clear();
            drawnBoxes.Clear();
            UpdateDisplay(originalImage);
        }
    }

    // 启动类
    class Program
    {
        static void Main(string[] args)
        {
            new AutoSegmentationProcessor().Run();
        }
    }
}