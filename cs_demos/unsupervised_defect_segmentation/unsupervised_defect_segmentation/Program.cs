using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using DaoAI.DeepLearningCLI;  // SDK 命名空间
using OpenCvSharp;            // OpenCvSharp 用于图像显示与交互

namespace UnsupervisedDefectSegmentationDemo
{
    // 图像标注数据（所有坐标均为原图坐标，支持亚像素精度）
    class ImageAnnotation
    {
        public string FilePath { get; set; }
        public bool IsAnnotated { get; set; } = false;  // 是否已标注
        public bool IsGood { get; set; } = true;          // true：好图；false：坏图
        public bool Finished { get; set; } = false;       // 对于坏图：多边形是否闭合完成
        public List<PointF> Polygon { get; set; } = new List<PointF>();  // 多边形顶点
    }

    class Program
    {
        // 固定窗口尺寸
        const int FIXED_WIDTH = 800;
        const int FIXED_HEIGHT = 600;
        // 当前缩放比例（相对于原图）
        static double scale = 1.0;
        // 全部标注数据、当前索引
        static List<ImageAnnotation> annotations = new List<ImageAnnotation>();
        static int currentIndex = 0;
        // 当前原始图像与用于显示的图像（均使用 OpenCvSharp Mat 类型）
        static Mat originalImage;
        static Mat displayImage;
        const string windowName = "Annotation";

        /// <summary>
        /// 根据当前 scale 以及窗口设置，重新渲染显示图像（包括居中/裁剪、标注文字和多边形）
        /// </summary>
        static void RedrawImage()
        {
            // 计算缩放后尺寸
            int newWidth = (int)(originalImage.Width * scale);
            int newHeight = (int)(originalImage.Height * scale);
            Mat resized = new Mat();
            Cv2.Resize(originalImage, resized, new OpenCvSharp.Size(newWidth, newHeight));

            // 创建固定大小黑色画布
            Mat canvas = new Mat(new OpenCvSharp.Size(FIXED_WIDTH, FIXED_HEIGHT), resized.Type(), Scalar.All(0));
            int effectiveOffsetX = 0, effectiveOffsetY = 0;
            if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT)
            {
                // 图像较小，居中显示
                effectiveOffsetX = (FIXED_WIDTH - newWidth) / 2;
                effectiveOffsetY = (FIXED_HEIGHT - newHeight) / 2;
                Rect roi = new Rect(effectiveOffsetX, effectiveOffsetY, newWidth, newHeight);
                resized.CopyTo(new Mat(canvas, roi));
            }
            else
            {
                // 图像超出窗口，裁剪中间部分
                int cropX = (newWidth - FIXED_WIDTH) / 2;
                int cropY = (newHeight - FIXED_HEIGHT) / 2;
                effectiveOffsetX = -cropX;
                effectiveOffsetY = -cropY;
                Rect roi = new Rect(cropX, cropY, FIXED_WIDTH, FIXED_HEIGHT);
                canvas = resized.SubMat(roi).Clone();
            }
            displayImage = canvas.Clone();

            // 在左上角显示标注状态
            string labelText = "Unlabeled";
            var ann = annotations[currentIndex];
            if (ann.IsAnnotated)
                labelText = ann.IsGood ? "Good" : "Bad";
            Cv2.PutText(displayImage, labelText, new OpenCvSharp.Point(10, 30), HersheyFonts.HersheySimplex, 1.0, new Scalar(255, 0, 0), 2);

            // 如果当前图标记为坏且有多边形数据，绘制标注点和连接线
            if (ann.IsAnnotated && !ann.IsGood && ann.Polygon.Count > 0)
            {
                for (int i = 0; i < ann.Polygon.Count; i++)
                {
                    int dispX = (int)Math.Round(ann.Polygon[i].X * scale) + effectiveOffsetX;
                    int dispY = (int)Math.Round(ann.Polygon[i].Y * scale) + effectiveOffsetY;
                    Cv2.Circle(displayImage, new OpenCvSharp.Point(dispX, dispY), 3, new Scalar(0, 0, 255), -1);
                    if (i > 0)
                    {
                        int prevX = (int)Math.Round(ann.Polygon[i - 1].X * scale) + effectiveOffsetX;
                        int prevY = (int)Math.Round(ann.Polygon[i - 1].Y * scale) + effectiveOffsetY;
                        Cv2.Line(displayImage, new OpenCvSharp.Point(prevX, prevY), new OpenCvSharp.Point(dispX, dispY), new Scalar(0, 255, 0), 2);
                    }
                }
                // 如果已完成标注，连接最后一点与第一点
                if (ann.Finished && ann.Polygon.Count >= 2)
                {
                    int firstX = (int)Math.Round(ann.Polygon[0].X * scale) + effectiveOffsetX;
                    int firstY = (int)Math.Round(ann.Polygon[0].Y * scale) + effectiveOffsetY;
                    int lastX = (int)Math.Round(ann.Polygon[ann.Polygon.Count - 1].X * scale) + effectiveOffsetX;
                    int lastY = (int)Math.Round(ann.Polygon[ann.Polygon.Count - 1].Y * scale) + effectiveOffsetY;
                    Cv2.Line(displayImage, new OpenCvSharp.Point(lastX, lastY), new OpenCvSharp.Point(firstX, firstY), new Scalar(0, 255, 0), 2);
                }
            }
        }

        /// <summary>
        /// 鼠标回调函数：支持鼠标滚轮缩放和左键添加标注点（仅对 BAD 图有效）
        /// </summary>
        static void OnMouse(MouseEventTypes eventType, int x, int y, MouseEventFlags flags, IntPtr userdata)
        {
            int newWidth = (int)(originalImage.Width * scale);
            int newHeight = (int)(originalImage.Height * scale);
            int effectiveOffsetX = 0, effectiveOffsetY = 0;
            if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT)
            {
                effectiveOffsetX = (FIXED_WIDTH - newWidth) / 2;
                effectiveOffsetY = (FIXED_HEIGHT - newHeight) / 2;
            }
            else
            {
                effectiveOffsetX = -(newWidth - FIXED_WIDTH) / 2;
                effectiveOffsetY = -(newHeight - FIXED_HEIGHT) / 2;
            }

            // 鼠标滚轮事件：缩放图像
            if (eventType == MouseEventTypes.MouseWheel)
            {
                int delta = Cv2.GetMouseWheelDelta(flags);
                double zoomFactor = 1.1;
                if (delta > 0)
                    scale *= zoomFactor;
                else if (delta < 0)
                    scale /= zoomFactor;
                scale = Math.Max(0.1, Math.Min(scale, 10.0));
                RedrawImage();
                Cv2.ImShow(windowName, displayImage);
                return;
            }

            // 仅对标记为 BAD 的图像允许添加标注点
            var ann = annotations[currentIndex];
            if (!ann.IsAnnotated || ann.IsGood)
                return;

            if (eventType == MouseEventTypes.LButtonDown)
            {
                // 如果图像未充满整个画布，点击需位于图像区域内
                if (newWidth <= FIXED_WIDTH && newHeight <= FIXED_HEIGHT)
                {
                    if (x < effectiveOffsetX || x > effectiveOffsetX + newWidth ||
                        y < effectiveOffsetY || y > effectiveOffsetY + newHeight)
                        return;
                }
                // 将显示窗口坐标转换为原图亚像素坐标
                float origX = (x - effectiveOffsetX) / (float)scale;
                float origY = (y - effectiveOffsetY) / (float)scale;
                ann.Polygon.Add(new PointF(origX, origY));
                RedrawImage();
                Cv2.ImShow(windowName, displayImage);
            }
        }

        static void Main(string[] args)
        {
            try
            {
                // 1. 初始化库
                Application.initialize();
                Console.WriteLine("DaoAI.DeepLearningCLI 库已初始化。");

                // 2. 输入图像文件夹路径
                Console.Write("请输入包含图像的文件夹路径: ");
                string folderPath = Console.ReadLine().Trim();
                if (!Directory.Exists(folderPath))
                {
                    Console.WriteLine("文件夹不存在: " + folderPath);
                    return;
                }

                // 3. 加载文件夹中所有图像（支持 .png, .jpg, .jpeg）
                string[] validExts = new string[] { ".png", ".jpg", ".jpeg" };
                List<string> imagePaths = Directory.GetFiles(folderPath)
                    .Where(f => validExts.Contains(Path.GetExtension(f).ToLower()))
                    .OrderBy(f => f)
                    .ToList();
                if (imagePaths.Count == 0)
                {
                    Console.WriteLine("未找到图像文件。");
                    return;
                }

                // 初始化每张图的标注数据
                annotations.Clear();
                foreach (var path in imagePaths)
                {
                    annotations.Add(new ImageAnnotation { FilePath = path });
                }

                // 4. 启动交互式图形标注界面
                Cv2.NamedWindow(windowName, WindowFlags.AutoSize);
                Cv2.SetMouseCallback(windowName, OnMouse);
                Console.WriteLine("标注说明:");
                Console.WriteLine(" n: 下一张图");
                Console.WriteLine(" p: 上一张图");
                Console.WriteLine(" g: 标记为 GOOD");
                Console.WriteLine(" b: 标记为 BAD（使用鼠标左键添加多边形顶点）");
                Console.WriteLine(" r: 重置当前 BAD 图的标注");
                Console.WriteLine(" f: 完成标注（闭合多边形）");
                Console.WriteLine(" q: 退出标注");
                Console.WriteLine(" 使用鼠标滚轮缩放图像。");

                bool exitAnnotation = false;
                while (!exitAnnotation)
                {
                    // 加载当前图像
                    var ann = annotations[currentIndex];
                    originalImage = Cv2.ImRead(ann.FilePath, ImreadModes.Color);
                    if (originalImage.Empty())
                    {
                        Console.WriteLine("加载图像失败: " + ann.FilePath);
                        currentIndex = (currentIndex + 1) % annotations.Count;
                        continue;
                    }
                    // 设定初始缩放比例，使图像完整显示于窗口内
                    scale = Math.Min((double)FIXED_WIDTH / originalImage.Width, (double)FIXED_HEIGHT / originalImage.Height);
                    RedrawImage();
                    Cv2.ImShow(windowName, displayImage);
                    int key = Cv2.WaitKey(0);
                    char c = (char)key;
                    switch (c)
                    {
                        case 'n':
                            currentIndex = (currentIndex + 1) % annotations.Count;
                            break;
                        case 'p':
                            currentIndex = (currentIndex - 1 + annotations.Count) % annotations.Count;
                            break;
                        case 'g':
                            ann.IsAnnotated = true;
                            ann.IsGood = true;
                            ann.Polygon.Clear();
                            ann.Finished = false;
                            RedrawImage();
                            Cv2.ImShow(windowName, displayImage);
                            break;
                        case 'b':
                            ann.IsAnnotated = true;
                            ann.IsGood = false;
                            ann.Polygon.Clear();
                            ann.Finished = false;
                            RedrawImage();
                            Cv2.ImShow(windowName, displayImage);
                            break;
                        case 'r':
                            if (!ann.IsGood)
                            {
                                ann.Polygon.Clear();
                                ann.Finished = false;
                            }
                            RedrawImage();
                            Cv2.ImShow(windowName, displayImage);
                            break;
                        case 'f':
                            if (!ann.IsGood && ann.Polygon.Count >= 2)
                            {
                                ann.Finished = true;
                                Console.WriteLine("完成标注: " + ann.FilePath);
                                RedrawImage();
                                Cv2.ImShow(windowName, displayImage);
                            }
                            else
                            {
                                Console.WriteLine("至少需要2个标注点才能完成标注。");
                            }
                            break;
                        case 'q':
                            exitAnnotation = true;
                            break;
                        default:
                            break;
                    }
                    Console.WriteLine($"图像 {currentIndex + 1}/{annotations.Count} - {ann.FilePath}");
                }
                Cv2.DestroyWindow(windowName);

                // 5. 保存标注结果到输出目录
                string outDir = Path.Combine(folderPath, "out");
                string goodDir = Path.Combine(outDir, "good");
                string badDir = Path.Combine(outDir, "bad");
                string maskDir = Path.Combine(outDir, "masks");
                Directory.CreateDirectory(goodDir);
                Directory.CreateDirectory(badDir);
                Directory.CreateDirectory(maskDir);

                foreach (var ann in annotations)
                {
                    if (!ann.IsAnnotated)
                        continue;
                    string srcPath = ann.FilePath;
                    string filename = Path.GetFileName(srcPath);
                    if (ann.IsGood)
                    {
                        string destPath = Path.Combine(goodDir, filename);
                        File.Copy(srcPath, destPath, true);
                    }
                    else
                    {
                        string destPath = Path.Combine(badDir, filename);
                        File.Copy(srcPath, destPath, true);
                        // 生成 mask（使用 System.Drawing 绘制二值图，白色表示缺陷区域）
                        using (Bitmap img = new Bitmap(srcPath))
                        {
                            Bitmap maskBmp = new Bitmap(img.Width, img.Height, PixelFormat.Format24bppRgb);
                            // 设置灰度调色板
                            ColorPalette palette = maskBmp.Palette;
                            for (int i = 0; i < 256; i++)
                            {
                                palette.Entries[i] = Color.FromArgb(i, i, i);
                            }
                            maskBmp.Palette = palette;
                            using (Graphics g = Graphics.FromImage(maskBmp))
                            {
                                g.Clear(Color.Black);
                                if (ann.Polygon.Count == 0)
                                {
                                    g.Clear(Color.White);
                                }
                                else
                                {
                                    PointF[] pts = ann.Polygon.ToArray();
                                    if (pts.Length >= 2 && pts[0] != pts[pts.Length - 1])
                                    {
                                        List<PointF> ptsList = new List<PointF>(pts);
                                        ptsList.Add(pts[0]);
                                        pts = ptsList.ToArray();
                                    }
                                    g.FillPolygon(Brushes.White, pts);
                                }
                            }
                            string maskPath = Path.Combine(maskDir, Path.GetFileNameWithoutExtension(filename) + "_mask.png");
                            maskBmp.Save(maskPath, ImageFormat.Png);
                        }
                    }
                }
                Console.WriteLine("\n标注结果保存到：");
                Console.WriteLine("  Good: " + goodDir);
                Console.WriteLine("  Bad: " + badDir);
                Console.WriteLine("  Masks: " + maskDir);

                // 6. 重新读取输出目录中的图像作为训练数据
                List<DaoAI.DeepLearningCLI.Image> goodImages = new List<DaoAI.DeepLearningCLI.Image>();
                List<DaoAI.DeepLearningCLI.Image> badImages = new List<DaoAI.DeepLearningCLI.Image>();
                List<DaoAI.DeepLearningCLI.Image> masksList = new List<DaoAI.DeepLearningCLI.Image>();

                foreach (string file in Directory.GetFiles(goodDir))
                {
                    goodImages.Add(new DaoAI.DeepLearningCLI.Image(file));
                }
                foreach (string file in Directory.GetFiles(badDir))
                {
                    badImages.Add(new DaoAI.DeepLearningCLI.Image(file));
                }
                foreach (string file in Directory.GetFiles(maskDir))
                {
                    masksList.Add(new DaoAI.DeepLearningCLI.Image(file));
                }
                Console.WriteLine($"\n重新读取了 {goodImages.Count} 张好图, {badImages.Count} 张坏图, 和 {masksList.Count} 张 mask 图。");

                // 7. 使用重新读取的数据构建训练组件（无监督缺陷分割）
                Console.WriteLine("create model instance");

                var unsupervisedModel = new DaoAI.DeepLearningCLI.Vision.UnsupervisedDefectSegmentation(DeviceType.GPU);
                unsupervisedModel.setDetectionLevel(DaoAI.DeepLearningCLI.DetectionLevel.PIXEL_ACCURATE);
                var component = unsupervisedModel.createComponentMemory("screw", goodImages.ToArray(), badImages.ToArray(), masksList.ToArray(), true);
                string compFile = Path.Combine(folderPath, "component_1.pth");
                component.save(compFile);
                unsupervisedModel.setBatchSize(1);
                Console.WriteLine("训练组件已保存到: " + compFile);

                // 8. （可选）对一张坏图进行推理，输出缺陷得分及 JSON 格式结果
                if (badImages.Count > 0)
                {
                    for (int i = 0; i < badImages.Count; ++i)
                    {
                        var img = badImages[i];
                        var result = unsupervisedModel.inference(img);

                        Console.WriteLine($"缺陷得分 [{i}]: {result.ai_deviation_score}");
                        Console.WriteLine($"JSON 结果 [{i}]: {result.toJSONString()}");

                        string fileName = $"test_unsupervised_result_{i}.png";
                        string resultPath = Path.Combine(folderPath, "out", fileName);

                        // 可视化并保存
                        DaoAI.DeepLearningCLI.Image visualization = DaoAI.DeepLearningCLI.Utils.visualize(img, result);
                        visualization.save(resultPath);

                        Console.WriteLine($"Writing result image to: {Path.GetFullPath(resultPath)}");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("发生异常: " + ex.Message);
            }
        }
    }
}
