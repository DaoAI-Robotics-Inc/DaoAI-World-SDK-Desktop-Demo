using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Drawing.Imaging;
using System.Threading.Tasks;
using DaoAI.DeepLearningCLI;

namespace RotatedObjectDetectionDemo
{
    class Program
    {
        static void Main(string[] args)
        {
            // 1. 根目录和文件路径，请根据实际情况调整
            string root = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "../../../../../../../data/");
            string imagePath = Path.Combine(root, "rotated_object_detection_img.png");
            string modelPath = Path.Combine(root, "rotated_object_detection_model.dwm");

            Console.WriteLine("Start DaoAI World \"Rotated Object Detection\" example!");
            Console.WriteLine($"Image Path: {Path.GetFullPath(imagePath)}");
            Console.WriteLine($"Model Path: {Path.GetFullPath(modelPath)}\n");

            try
            {
                // Step 0: 初始化 SDK
                Application.initialize();
                Console.WriteLine("SDK initialized.\n");

                // Step 1: 加载图片
                Console.WriteLine("Loading image...");
                var image = new DaoAI.DeepLearningCLI.Image(imagePath);
                Console.WriteLine("Image loaded.\n");

                // Step 2: 加载 RotatedObjectDetection 模型
                Console.WriteLine("Loading RotatedObjectDetection model...");
                var model = new DaoAI.DeepLearningCLI.Vision.RotatedObjectDetection(modelPath, DeviceType.GPU, -1);
                Console.WriteLine("Model loaded.\n");

                // Step 3: 执行推理
                Console.WriteLine("Running inference...");
                var prediction = model.inference(image);
                Console.WriteLine("Inference completed.\n");

                // Step 4: 打印检测结果
                Console.WriteLine("=== Detection Results ===");
                for (int i = 0; i < prediction.class_ids.Length; i++)
                {
                    Console.WriteLine(
                        $"Class ID: {prediction.class_ids[i]}, " +
                        $"Label: {prediction.class_labels[i]}, " +
                        $"Confidence: {prediction.confidences[i]:F4}"
                    );
                }

                Console.WriteLine("\n=== Bounding Boxes ===");
                foreach (var box in prediction.boxes)
                {
                    Console.WriteLine(
                        $"Top-left: ({box.x1():F1}, {box.y1():F1}), " +
                        $"Bottom-right: ({box.x2():F1}, {box.y2():F1}), " +
                        $"Angle: {box.angle():F1}"
                    );
                }
                Console.WriteLine();

                // Step 5: 输出 JSON 与可视化结果
                string outDir = Path.Combine(root, "output");
                Directory.CreateDirectory(outDir);

                string jsonPath = Path.Combine(outDir, "rotated_detection_result.json");
                File.WriteAllText(jsonPath, prediction.toJSONString());
                Console.WriteLine($"Saved JSON to: {jsonPath}");

                var visImg = Utils.visualize(image, prediction);
                string bmpPath = Path.Combine(outDir, "rotated_detection_result.bmp");
                visImg.save(bmpPath);
                Console.WriteLine($"Saved visualization to: {bmpPath}\n");
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error: {ex.Message}");
            }

            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
    }
}
