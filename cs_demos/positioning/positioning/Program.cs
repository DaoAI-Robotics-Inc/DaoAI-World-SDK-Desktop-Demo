using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Drawing.Imaging;
using System.Threading.Tasks;
using DaoAI.DeepLearningCLI;

namespace positioning
{
    class Program
    {
        static void Main(string[] args)
        {
            string currentDirectory = AppDomain.CurrentDomain.BaseDirectory;
            string fileName = "../../../../../../../Data/positioning_img.bmp";
            string filemodel = "../../../../../../../Data/positioning_model.dwm";
            string filePath_image = Path.Combine(currentDirectory, fileName);
            string filePath_model = Path.Combine(currentDirectory, filemodel);
            string filePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "resule_image.jpg");
            Console.WriteLine(filePath);
            Console.WriteLine(filePath_model);
            Console.WriteLine(filePath_image);
            // 测试点和多边形操作
            TestPointsAndPolygons();
            // 测试盒子和多边形转换
            TestBoxesAndPolygons();
            // 测试图像处理和OCR模型
            TestImageProcessingAndOCR(filePath_image, filePath_model, filePath);
            Console.WriteLine("Press anything to close the window");
            Console.ReadKey();
        }

        static void TestPointsAndPolygons()
        {
            DaoAI.DeepLearningCLI.Point p1 = new DaoAI.DeepLearningCLI.Point(1.0f, 2.0f);
            DaoAI.DeepLearningCLI.Point p2 = new DaoAI.DeepLearningCLI.Point(3.0f, 4.0f);
            Console.WriteLine($"Point 1 X: {p1.X}, Point 2 X: {p2.X}");
            Console.WriteLine($"Sum Point X: {(p1 + p2).X}");
            Console.WriteLine($"Difference Point X: {(p1 - p2).X}");
            DaoAI.DeepLearningCLI.Point[] points = { p1, p2 };
            DaoAI.DeepLearningCLI.Polygon poly = new DaoAI.DeepLearningCLI.Polygon(points);
            Console.WriteLine($"Polygon Point 1 X: {poly.Points[1].X}, Polygon Point 0 X: {poly.Points[0].X}");
        }

        static void TestBoxesAndPolygons()
        {
            DaoAI.DeepLearningCLI.Box box1 = new DaoAI.DeepLearningCLI.Box(new DaoAI.DeepLearningCLI.Point(1.0f, 2.0f), new DaoAI.DeepLearningCLI.Point(3.0f, 4.0f), 0.0f);
            DaoAI.DeepLearningCLI.Box box2 = new DaoAI.DeepLearningCLI.Box(1.0f, 2.0f, 3.0f, 4.0f, 0.0f, DaoAI.DeepLearningCLI.Box.Type.XYXY);
            Console.WriteLine($"Box 1: {box1.toString()}, Box 2: {box2.toString()}");
            Console.WriteLine($"Box 1 X2: {box1.x2()}, Box 1 Y2: {box1.y2()}");
            DaoAI.DeepLearningCLI.Box box3 = box1.toType(DaoAI.DeepLearningCLI.Box.Type.XYWH);
            Console.WriteLine($"Box 3: {box3.toString()}");
            DaoAI.DeepLearningCLI.Polygon poly_box = box1.toPolygon();
            Console.WriteLine($"Polygon Box Point 0 X: {poly_box.Points[0].X}, Polygon Box Point 2 X: {poly_box.Points[2].X}");
        }

        static void TestImageProcessingAndOCR(string image_path, string model_path1, string result_path)
        {
            System.Drawing.Bitmap image = new System.Drawing.Bitmap(@image_path);
            byte[] pixels = new byte[image.Width * image.Height * 3];
            for (int i = 0; i < image.Height; i++)
            {
                for (int j = 0; j < image.Width; j++)
                {
                    System.Drawing.Color color = image.GetPixel(j, i);
                    pixels[(i * image.Width + j) * 3] = (byte)(color.R);
                    pixels[(i * image.Width + j) * 3 + 1] = (byte)(color.G);
                    pixels[(i * image.Width + j) * 3 + 2] = (byte)(color.B);
                }
            }
            DaoAI.DeepLearningCLI.Image img = new DaoAI.DeepLearningCLI.Image(image.Height, image.Width, DaoAI.DeepLearningCLI.Image.Type.RGB, pixels);
            DaoAI.DeepLearningCLI.Image img_copy = img.clone();
            byte[] image_data = img_copy.data;
            //for (int i = 0; i < image.Width; i++)
            //{
            //    for (int j = 0; j < image.Height; j++)
            //    {
            //        int index_r = i * image.Height + j;
            //        int index_g = i * image.Height + j + image.Width * image.Height;
            //        int index_b = i * image.Height + j + 2 * image.Width * image.Height;
            //        byte r = image_data[index_r];
            //        byte g = image_data[index_g];
            //        byte b = image_data[index_b];
            //        System.Drawing.Color color = Color.FromArgb(r, g, b);
            //        image.SetPixel(i, j, color);
            //    }
            //}
            DaoAI.DeepLearningCLI.Image daoai_image = new DaoAI.DeepLearningCLI.Image(image_path);
            DaoAI.DeepLearningCLI.Application.initialize();
            String model_path = model_path1;
            Console.WriteLine(model_path);
            Console.WriteLine("Loading model...");
            DaoAI.DeepLearningCLI.Vision.Positioning model = new DaoAI.DeepLearningCLI.Vision.Positioning(model_path, DaoAI.DeepLearningCLI.DeviceType.GPU, -1);
            Console.WriteLine(model.GetType());
            Console.WriteLine("Model loaded. Running inference");
            Dictionary<DaoAI.DeepLearningCLI.PostProcessType, object> post_params = new Dictionary<DaoAI.DeepLearningCLI.PostProcessType, object>();
            post_params[DaoAI.DeepLearningCLI.PostProcessType.CONFIDENCE_THRESHOLD] = 0.5;
            DaoAI.DeepLearningCLI.Vision.PositioningResult result_pred = model.inference(daoai_image);
            Console.WriteLine(result_pred.toJSONString());
            DaoAI.DeepLearningCLI.Image result = DaoAI.DeepLearningCLI.Utils.visualize(img, model.inference(img));
            result.save(result_path);
            Console.WriteLine("Inference done");
        }

    }
}
