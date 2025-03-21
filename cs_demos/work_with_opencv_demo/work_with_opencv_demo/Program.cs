using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using OpenCvSharp;
using DaoAI.DeepLearningCLI;
using System.Runtime.InteropServices;

namespace WorkWithOpenCVDEMO
{
    class Program
    {
        // 将 Mat 数据转换为 byte[] 数组
        static byte[] MatToByteArray(Mat mat)
        {
            int dataSize = mat.Rows * mat.Cols * mat.ElemSize();
            byte[] data = new byte[dataSize];
            // 将数据从 mat.Data (IntPtr) 复制到 byte 数组中
            Marshal.Copy(mat.Data, data, 0, dataSize);
            return data;
        }

        static void Main(string[] args)
        {
            // 如果提供了文件夹路径，则使用，否则使用默认路径
            DaoAI.DeepLearningCLI.Application.initialize();
            string folderPath = (args.Length >= 1) ? args[0] : "../../../../../../../Data/work_with_opencv";
            string outputFolder = Path.Combine(folderPath, "output");
            Directory.CreateDirectory(outputFolder);

            // 模型路径（请根据需要修改）
            string modelPath = "../../../../../../../Data/work_with_opencv.dwm";

            // 打印完整路径
            string fullModelPath = Path.GetFullPath(modelPath);
            Console.WriteLine("Full model path: " + fullModelPath);


            // 初始化模型，指定使用 GPU（DeviceType.GPU）；第三个参数 -1 表示使用默认 GPU 设备
            DaoAI.DeepLearningCLI.Vision.ObjectDetection model = new DaoAI.DeepLearningCLI.Vision.ObjectDetection(modelPath, DeviceType.GPU, -1);

            Stopwatch programWatch = Stopwatch.StartNew();

            // Warm-up: 使用一张 dummy 图片进行推理
            Mat dummyMat = new Mat(480, 640, MatType.CV_8UC3, Scalar.All(0));
            byte[] dummyPixels = MatToByteArray(dummyMat);
            // 构造 DaoAI 图片对象
            Image dummyImage = new Image(dummyMat.Rows, dummyMat.Cols, Image.Type.RGB, dummyPixels);
            Stopwatch warmupWatch = Stopwatch.StartNew();
            var dummyPrediction = model.inference(dummyImage);
            warmupWatch.Stop();
            Console.WriteLine("Warmup inference completed in {0} ms.", warmupWatch.ElapsedMilliseconds);

            // 定义有效的图片扩展名
            string[] validExt = new string[] { ".jpg", ".jpeg", ".png", ".bmp", ".tiff" };

            double totalConversionTime = 0.0;
            double totalInferenceTime = 0.0;
            int imageCount = 0;

            // 读取文件夹内所有图片（仅处理有效扩展名文件）
            var files = Directory.EnumerateFiles(folderPath)
                                 .Where(f => validExt.Contains(Path.GetExtension(f).ToLower()));

            foreach (var file in files)
            {
                // 使用 OpenCvSharp 读取图片
                Mat img = Cv2.ImRead(file);
                if (img.Empty())
                    continue;

                // 颜色转换计时 (BGR -> RGB)
                Stopwatch convWatch = Stopwatch.StartNew();
                Mat rgb = new Mat();
                Cv2.CvtColor(img, rgb, ColorConversionCodes.BGR2RGB);
                convWatch.Stop();
                totalConversionTime += convWatch.Elapsed.TotalSeconds;

                int height = rgb.Rows, width = rgb.Cols;
                // 将 rgb 数据转换为 byte[] 数组
                byte[] pixelData = MatToByteArray(rgb);

                // 创建 DaoAI 图片对象
                Image sdkImage = new Image(height, width, Image.Type.RGB, pixelData);

                // 推理计时（单张图片推理）
                Stopwatch infWatch = Stopwatch.StartNew();
                var prediction = model.inference(sdkImage);
                infWatch.Stop();
                long infTime = infWatch.ElapsedMilliseconds;
                totalInferenceTime += infTime;
                imageCount++;

                Console.WriteLine("Processed image: {0}, inference time: {1} ms", Path.GetFileName(file), infTime);

                // 可视化推理结果
                var daoaiResult = Utils.visualize(sdkImage, prediction);
                int resWidth = daoaiResult.width, resHeight = daoaiResult.height;
                byte[] resultData = daoaiResult.data;
                // 创建一个空的 Mat（注意：总字节数应为 resHeight * resWidth * 每像素字节数）
                Mat resultMat = new Mat(resHeight, resWidth,
                    daoaiResult.type == Image.Type.GRAYSCALE ? MatType.CV_8UC1 : MatType.CV_8UC3);
                // 将 resultData 数组复制到 resultMat 的数据区中
                Marshal.Copy(resultData, 0, resultMat.Data, resultData.Length);
                Mat resultBGR = new Mat();
                if (daoaiResult.type == Image.Type.RGB)
                    Cv2.CvtColor(resultMat, resultBGR, ColorConversionCodes.RGB2BGR);
                else if (daoaiResult.type == Image.Type.BGR)
                    resultBGR = resultMat;
                else if (daoaiResult.type == Image.Type.GRAYSCALE)
                    Cv2.CvtColor(resultMat, resultBGR, ColorConversionCodes.GRAY2BGR);
                else
                    resultBGR = resultMat;

                string outPath = Path.Combine(outputFolder, "prediction_" + Path.GetFileName(file));
                Cv2.ImWrite(outPath, resultBGR);
            }

            if (imageCount > 0)
            {
                double avgConvMs = (totalConversionTime / imageCount) * 1000;
                double avgInfMs = totalInferenceTime / imageCount;
                Console.WriteLine("Processed {0} images.", imageCount);
                Console.WriteLine("Total conversion time: {0} s, average: {1} ms/image", totalConversionTime, avgConvMs);
                Console.WriteLine("Total inference time: {0} ms, average: {1} ms/image", totalInferenceTime, avgInfMs);
            }
            else
            {
                Console.WriteLine("No images were read!");
            }

            programWatch.Stop();
            Console.WriteLine("Total program runtime: {0} seconds", programWatch.Elapsed.TotalSeconds);
        }
    }
}
