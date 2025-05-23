using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Drawing.Imaging;
using System.Threading.Tasks;
using DaoAI.DeepLearningCLI;

namespace MixedModelDemo
{
    class Program
    {
        static void Main(string[] args)
        {
            // 根目录（可根据实际路径调整）
            string root = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "../../../../../../../data/");
            string imagePath = Path.Combine(root, "mix_model_img.png");
            string modelPath = Path.Combine(root, "mix_model.dwm");

            Console.WriteLine("Start DaoAI World Mixed Model example!");
            Console.WriteLine($"Image Path: {Path.GetFullPath(imagePath)}");
            Console.WriteLine($"Model Path: {Path.GetFullPath(modelPath)}\n");

            try
            {
                // 0. 初始化 SDK
                Application.initialize();
                Console.WriteLine("SDK initialized.\n");

                // 1. 加载图片
                Console.WriteLine("Loading image...");
                var image = new DaoAI.DeepLearningCLI.Image(imagePath);
                Console.WriteLine("Image loaded.\n");

                // 2. 加载多标签检测模型
                Console.WriteLine("Loading MultilabelDetection model...");
                var model = new DaoAI.DeepLearningCLI.Vision.MultilabelDetection(modelPath, DeviceType.GPU, -1);
                Console.WriteLine("Model loaded.\n");

                // 3. 推理
                Console.WriteLine("Running inference...");
                var prediction = model.inference(image);
                Console.WriteLine("Inference completed.\n");

                // 4. 打印结果
                Console.WriteLine("=== Detection Results ===");
                for (int i = 0; i < prediction.class_ids.Length; i++)
                {
                    Console.Write($"Class ID: {prediction.class_ids[i]}, ");
                    Console.Write($"Label: {prediction.class_labels[i]}, ");
                    Console.Write($"Confidence: {prediction.confidences[i]:F4}");

                    // 取属性中置信度最高的一项
                    var attrs = prediction.attributes[i];
                    if (attrs != null && attrs.Count > 0)
                    {
                        var maxAttr = attrs.Aggregate((l, r) => l.Value > r.Value ? l : r);
                        Console.Write($", Attribute: {maxAttr.Key}, Score: {maxAttr.Value:F4}");
                    }
                    Console.WriteLine();
                }

                Console.WriteLine("\n=== Bounding Boxes ===");
                foreach (var box in prediction.boxes)
                {
                    Console.WriteLine(
                        $"Top-left: ({box.x1():F1}, {box.y1():F1}), " +
                        $"Bottom-right: ({box.x2():F1}, {box.y2():F1})");
                }
                Console.WriteLine();

                // 5. 输出 JSON
                string outDir = Path.Combine(root, "output");
                Directory.CreateDirectory(outDir);
                string jsonPath = Path.Combine(outDir, "testMixedModel_Result.json");
                File.WriteAllText(jsonPath, prediction.toJSONString());
                Console.WriteLine($"Saved JSON to: {jsonPath}");

                // 6. 可视化并保存结果图
                var visImg = Utils.visualize(image, prediction);
                string bmpPath = Path.Combine(outDir, "testMixedModel_Result.bmp");
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
