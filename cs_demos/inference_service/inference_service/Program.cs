using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;
using DaoAI.InferenceClient;

namespace Inference_Service_Demo
{
    class Program
    {
        static void Main(string[] args)
        {
            // 获取当前执行目录
            string currentDirectory = AppDomain.CurrentDomain.BaseDirectory;
            // 定义实例分割图片和模型的相对路径（请根据实际情况调整）
            string fileName = "../../../../../../../data/instance_segmentation_img.jpg";
            string filemodel = "../../../../../../../data/instance_segmentation_model.dwm";
            // 构造完整路径
            string filePath_image = Path.Combine(currentDirectory, fileName);
            string filePath_model = Path.Combine(currentDirectory, filemodel);
            string filePath = Path.Combine(currentDirectory, "result_image.jpg");

            // 转换为绝对路径
            string fullFilePath_image = Path.GetFullPath(filePath_image);
            string fullFilePath_model = Path.GetFullPath(filePath_model);
            string fullFilePath = Path.GetFullPath(filePath);

            Console.WriteLine("Full Result Image Path: " + fullFilePath);
            Console.WriteLine("Full Model Path: " + fullFilePath_model);
            Console.WriteLine("Full Image Path: " + fullFilePath_image);

            // ===============================
            // Step 1: 加载模型
            // ===============================
            Console.WriteLine("Loading instance segmentation model...");
            // 使用 GPU 设备加载模型（也可改为 DeviceType.CPU）
            InstanceSegmentation model = new InstanceSegmentation(fullFilePath_model, DeviceType.GPU);
            Console.WriteLine("Model loaded. Running inference...");

            // ===============================
            // Step 2: 读取图像文件并转换为 Base64 字符串
            // ===============================
            string base64Image = Convert.ToBase64String(File.ReadAllBytes(fullFilePath_image));

            // ===============================
            // Step 3: 模型推理
            // ===============================
            InstanceSegmentationResult result = model.inference(base64Image);
            Console.WriteLine("Inference done.");
            Console.WriteLine("Detected objects: " + result.class_labels.Length);
            for (int i = 0; i < result.class_labels.Length; i++)
            {
                Console.WriteLine("Object " + (i + 1));
                Console.WriteLine("Class: " + result.class_labels[i]);
                Console.WriteLine("Bounding box: " + result.boxes[i].x1() + " " + result.boxes[i].y1() + " " + result.boxes[i].x2() + " " + result.boxes[i].y2());
                Console.WriteLine("Confidence: " + result.confidences[i]);
                // 注：下面这行原代码中对 mask 的输出存在问题，此处已在绘制部分详细处理
                // Console.WriteLine("Mask Point: " + result.masks[i].polygon_data[0].points[0] + ", " + result.masks[i].polygon_data[0].points[1]);
            }

            // ===============================
            // Step 4: 绘制推理结果（边界框、类别标签及分割掩码）
            // ===============================
            try
            {
                using (Bitmap image = new Bitmap(fullFilePath_image))
                {
                    using (Graphics g = Graphics.FromImage(image))
                    {
                        for (int i = 0; i < result.class_labels.Length; i++)
                        {
                            // 获取边界框坐标
                            int x1 = (int)result.boxes[i].x1();
                            int y1 = (int)result.boxes[i].y1();
                            int x2 = (int)result.boxes[i].x2();
                            int y2 = (int)result.boxes[i].y2();
                            int boxWidth = x2 - x1;
                            int boxHeight = y2 - y1;

                            // 绘制边界框（红色）
                            using (Pen pen = new Pen(Color.Red, 2))
                            {
                                g.DrawRectangle(pen, x1, y1, boxWidth, boxHeight);
                            }

                            // 绘制类别和置信度文本（带背景以提高可读性）
                            string labelText = $"{result.class_labels[i]}: {result.confidences[i]:0.00}";
                            using (Font font = new Font("Arial", 12, FontStyle.Bold))
                            {
                                SizeF textSize = g.MeasureString(labelText, font);
                                // 绘制半透明背景
                                using (Brush bgBrush = new SolidBrush(Color.FromArgb(128, Color.Yellow)))
                                {
                                    g.FillRectangle(bgBrush, x1, y1 - textSize.Height, textSize.Width, textSize.Height);
                                }
                                // 绘制文本
                                using (Brush textBrush = new SolidBrush(Color.Black))
                                {
                                    g.DrawString(labelText, font, textBrush, x1, y1 - textSize.Height);
                                }
                            }

                            // 绘制分割掩码（如果存在）
                            if (result.masks != null && result.masks.Length > i &&
                                result.masks[i] != null && result.masks[i].polygon_data != null &&
                                result.masks[i].polygon_data.Count > 0)
                            {
                                // 取第一个多边形数据
                                var polygon = result.masks[i].polygon_data[0];
                                // 注意：如果 polygon.points 为方法，则需要调用它；否则直接使用属性即可。
                                // 例如：var pointsList = polygon.points(); 
                                var pointsList = polygon.points; // 修改为 polygon.points 如果 points 是属性

                                if (pointsList != null && pointsList.Count >= 2)
                                {
                                    int numPoints = pointsList.Count;
                                    PointF[] pts = new PointF[numPoints];
                                    for (int p = 0; p < numPoints; p++)
                                    {
                                        // 此处假设每个点有属性 x 和 y（如果属性名不同请作相应修改）
                                        pts[p] = new PointF((float)pointsList[p].x, (float)pointsList[p].y);
                                    }

                                    // 绘制半透明的 mask 填充（蓝色）
                                    using (Brush maskBrush = new SolidBrush(Color.FromArgb(80, Color.Blue)))
                                    {
                                        g.FillPolygon(maskBrush, pts);
                                    }
                                    // 绘制 mask 边界
                                    using (Pen maskPen = new Pen(Color.Blue, 2))
                                    {
                                        g.DrawPolygon(maskPen, pts);
                                    }
                                }
                            }
                        }
                    }
                    // 保存绘制结果的图像
                    image.Save(fullFilePath, ImageFormat.Jpeg);
                    Console.WriteLine("Result image saved: " + fullFilePath);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error while drawing results: " + ex.Message);
            }

            Console.WriteLine("Press any key to close the window.");
            Console.ReadKey();
        }
    }
}
