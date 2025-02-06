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
using System.Threading; // Include this namespace for Thread.Sleep

namespace AutoSegmentationApp
{
    public class AutoSegmentationProcessor
    {
        private List<DaoAI.DeepLearningCLI.Point> clickedPoints = new List<DaoAI.DeepLearningCLI.Point>();
        private List<DaoAI.DeepLearningCLI.Box> drawnBoxes = new List<DaoAI.DeepLearningCLI.Box>();
        private bool isDrawing = false;
        private DaoAI.DeepLearningCLI.Point startPoint;
        private Mat originalImage;
        private DaoAI.DeepLearningCLI.Vision.AutoSegmentation model;
        private DaoAI.DeepLearningCLI.Vision.ImageEmbedding embedding;
        private const int DragThreshold = 5;
        private const string WindowName = "Image Viewer";
        private readonly string imagePath = "../../../../../../../Data/instance_segmentation_img.jpg";
        private readonly string modelPath = "../../../../../../../Data/auto_segment.dwm";

        public void Run()
        {
            string absoluteImagePath = Path.GetFullPath(imagePath);
            string absoluteModelPath = Path.GetFullPath(modelPath);

            Console.WriteLine("Absolute Image Path: " + absoluteImagePath);
            Console.WriteLine("Absolute Model Path: " + absoluteModelPath);
            //Thread.Sleep(5000); // Time is in milliseconds, so 5000 ms = 5 seconds


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
                embedding = model.generateImageEmbeddings(sdkImage);
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
                startPoint.X = e.Location.X;
                startPoint.Y = e.Location.Y;
            }
        }

        private void OnMouseMove(object sender, MouseEventArgs e)
        {
            if (!isDrawing) return;

            var currentImage = originalImage.Clone();
            if (Math.Abs(e.X - startPoint.X) > DragThreshold ||
                Math.Abs(e.Y - startPoint.Y) > DragThreshold)
            {
                // Properly balance parentheses and syntax
                CvInvoke.Rectangle(
                    currentImage,
                    new Rectangle(
                        new System.Drawing.Point((int)Math.Round(startPoint.X), (int)Math.Round(startPoint.Y)),
                        new Size(e.X - (int)Math.Round(startPoint.X), e.Y - (int)Math.Round(startPoint.Y))
                    ),
                    new MCvScalar(0, 255, 0),  // Color for the rectangle (green)
                    2  // Line thickness
                );
                UpdateDisplay(currentImage);
            }
        }

        private void OnMouseUp(object sender, MouseEventArgs e)
        {
            isDrawing = false;

            if (e.Button == MouseButtons.Left)
            {
                if (startPoint.X == e.Location.X && startPoint.Y == e.Location.Y)
                {
                    clickedPoints.Add(new DaoAI.DeepLearningCLI.Point(e.X, e.Y, "1"));
                }
                else
                {
                    drawnBoxes.Add(new DaoAI.DeepLearningCLI.Box(startPoint, new DaoAI.DeepLearningCLI.Point(e.Location.X, e.Location.Y),0));
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
                // Convert List<DaoAI.DeepLearningCLI.Point> to Point[][]
                var clickedPointsArray = new DaoAI.DeepLearningCLI.Point[1][];  // Create a 2D array with 1 row
                clickedPointsArray[0] = clickedPoints.ToArray();  // Convert List<DaoAI.DeepLearningCLI.Point> to an array and assign to the row

                // Convert List<DaoAI.DeepLearningCLI.Box> to Box[][]
                var drawnBoxesArray = new DaoAI.DeepLearningCLI.Box[1][];  // Create a 2D array with 1 row
                drawnBoxesArray[0] = drawnBoxes.ToArray();  // Convert List<DaoAI.DeepLearningCLI.Box> to an array and assign to the row

                // Convert embedding to an array (if necessary)
                var embeddingArray = new DaoAI.DeepLearningCLI.Vision.ImageEmbedding[] { embedding };

                // Now call the inference method with the correct arguments
                var result = model.inference(embeddingArray, drawnBoxesArray, clickedPointsArray);

                SaveResult(result[0]);
                UpdateMaskDisplay(result[0].mask);
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