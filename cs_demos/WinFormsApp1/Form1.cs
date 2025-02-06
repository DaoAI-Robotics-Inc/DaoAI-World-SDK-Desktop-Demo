using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Windows.Forms;
using System.Drawing.Imaging;
using System.Diagnostics;
using System.Collections.ObjectModel;
using DaoAI.DeepLearningCLI; // DaoAI深度学习CLI工具包
using Newtonsoft.Json.Linq;// JSON处理库
using System.Net.Sockets; // 网络套接字编程
using System.Net;


namespace WinFormsApp1

{
   
    public partial class Form1 : Form
    {
        string a;// 用于存储OCR识别结果的字符串
        Socket socketClient = null;// 用于网络通信的Socket对象
        Thread threadClient = null;// 用于处理网络通信的线程

        private bool isThreadStart = false; // 标识线程是否启动的标志
        #region 控件大小随窗体大小等比例缩放

        private readonly float x; //定义当前窗体的宽度
        private readonly float y; //定义当前窗体的高度
        private static DaoAI.DeepLearningCLI.Vision.OCR model;// 定义OCR模型
        String file;// 定义文件路径字符串
        // 递归设置控件的Tag属性，用于记录控件的初始大小和位置
        private void setTag(Control cons)
        {
            foreach (Control con in cons.Controls)
            {
                con.Tag = con.Width + ";" + con.Height + ";" + con.Left + ";" + con.Top + ";" + con.Font.Size;
                if (con.Controls.Count > 0) setTag(con);
            }
        }
        // 根据窗体的新大小，调整控件的大小和位置
        private void setControls(float newx, float newy, Control cons)
        {
            //遍历窗体中的控件，重新设置控件的值
            foreach (Control con in cons.Controls)
                //获取控件的Tag属性值，并分割后存储字符串数组
                if (con.Tag != null)
                {
                    var mytag = con.Tag.ToString().Split(';');
                    //根据窗体缩放的比例确定控件的值
                    con.Width = Convert.ToInt32(Convert.ToSingle(mytag[0]) * newx); //宽度
                    con.Height = Convert.ToInt32(Convert.ToSingle(mytag[1]) * newy); //高度
                    con.Left = Convert.ToInt32(Convert.ToSingle(mytag[2]) * newx); //左边距
                    con.Top = Convert.ToInt32(Convert.ToSingle(mytag[3]) * newy); //顶边距
                    var currentSize = Convert.ToSingle(mytag[4]) * newy; //字体大小                   
                    if (currentSize > 0) con.Font = new Font(con.Font.Name, currentSize, con.Font.Style, con.Font.Unit);
                    con.Focus();
                    if (con.Controls.Count > 0) setControls(newx, newy, con);
                }
        }


        /// <summary>
        /// 重置窗体布局
        /// </summary>
        private void ReWinformLayout()
        {
            var newx = Width / x;
            var newy = Height / y;
            setControls(newx, newy, this);

        }
        #endregion
        // 构造函数，初始化窗体和控件
        public Form1()
        {
            InitializeComponent();
            button4.Enabled = false;// 初始化时禁用按钮4
            TextBox.CheckForIllegalCrossThreadCalls = false;// 允许跨线程操作TextBox
            x = Width;// 存储窗体的初始宽度
            y = Height;// 存储窗体的初始高度
            setTag(this);// 为控件设置Tag属性
            DaoAI.DeepLearningCLI.Application.initialize(false, 0);// 初始化深度学习应用
            String model_path = @"../../../../../../Data/ocr_model.dwm";// 模型路径
            model = new DaoAI.DeepLearningCLI.Vision.OCR(model_path, DaoAI.DeepLearningCLI.DeviceType.GPU, -1);// 创建OCR模型实例
           
        }

    private void textBox1_TextChanged(object sender, EventArgs e)
        {

    }

        private void pictureBox1_Click(object sender, EventArgs e)
        {

        }

        private void Form1_Load(object sender, EventArgs e)
        {

        }
        // Form大小变化事件处理方法，调整控件布局
        private void Form1_Resize(object sender, EventArgs e)
        {
            ReWinformLayout();
        }
        // 按钮1点击事件处理方法，执行OCR识别
        private void button1_Click(object sender, EventArgs e)
        {
            System.Drawing.Bitmap image = new
               System.Drawing.Bitmap(file);// 创建Bitmap副本
            System.Drawing.Bitmap image_copy = new System.Drawing.Bitmap(image);// 从文件创建Bitmap副本
            byte[] pixels = new byte[image.Width * image.Height * 3]; // 创建像素数组
            for (int i = 0; i < image.Height; i++)
            {
                for (int j = 0; j < image.Width; j++)
                {
                    System.Drawing.Color color = image.GetPixel(j, i);// 获取像素颜色
                    pixels[(i * image.Width + j) * 3] = (byte)(color.R);// 设置红色分量
                    pixels[(i * image.Width + j) * 3 + 1] = (byte)(color.G);// 设置绿色分量
                    pixels[(i * image.Width + j) * 3 + 2] = (byte)(color.B);// 设置蓝色分量
                }
            }
            DaoAI.DeepLearningCLI.Image img = new DaoAI.DeepLearningCLI.Image(image.Height, image.Width, DaoAI.DeepLearningCLI.Image.Type.RGB, pixels);// 创建图像对象
            a = model.inference(img).toJSONString();// 执行OCR识别并转换为JSON字符串
            DaoAI.DeepLearningCLI.Image result = DaoAI.DeepLearningCLI.Utils.visualize(img, model.inference(img));// 可视化识别结果
            result.save("./result.png");// 保存可视化结果
            pictureBox2.ImageLocation = (@"./result.png");// 设置PictureBox的图片路径
            string textValue,textValue2,textValue3;//设置字符串的变量写入textBox里面
            string mun;
            string json = a;// 存储OCR识别结果的JSON字符串
            JObject detectionsObj = JObject.Parse(json);// 解析JSON字符串

            foreach (var detection in detectionsObj["Detections"])
            {
                textValue = detection["Text"].ToString(); // 获取识别的文本
                textValue2 = detection["Confidence"].ToString(); // 获取识别的置信度
                textValue3 = detection["Box"].ToString(); // 获取识别的边框
                textBox1.AppendText("Text:" + textValue + Environment.NewLine);// 将识别的文本添加到TextBox
                textBox1.AppendText("Confidence:" + textValue2 + Environment.NewLine);// 将识别的文本添加到TextBox
                textBox1.AppendText("Box:" + textValue3 + Environment.NewLine);// 将识别的文本添加到TextBox
                textBox1.ForeColor = Color.Green;// 将识别的文本颜色为绿色
            }

        }
        // 按钮2点击事件处理方法，清空TextBox内容
        private void button2_Click(object sender, EventArgs e)
        {
            textBox1.Clear();
        }
        private void RecMsg()
        {
            while (true) 
            {
                if (!isThreadStart)
                {
                    break;        // 如果线程未启动，则退出循环
                }
                try
                {
                    byte[] arrRecMsg = new byte[1024 * 1024];// 创建接收缓冲区
                    int length = socketClient.Receive(arrRecMsg);// 接收消息
                    string strRecMsg = Encoding.UTF8.GetString(arrRecMsg, 0, length);// 将字节转换为字符串
                    if (!isThreadStart)
                    {
                        break;        // 如果线程未启动，则退出循环
                    }
                    textBox4.AppendText("服务端 " + DateTime.Now.ToString() + "\r\n" + strRecMsg + "\r\n");
                }
                catch (Exception ex)
                {
                    this.textBox4.AppendText("远程服务器已中断连接！" + "\r\n");
                    //this.btnListenServer.Enabled = true;
                    break;
                }
            }
        }
        // 发送消息的方法
        private void ClientSendMsg(string sendMsg)
        {
            try
            {
                //将字符串转换为字节
                byte[] arrClientSendMsg = Encoding.UTF8.GetBytes(sendMsg);
                //调用客户端套接字发送字节数组
                socketClient.Send(arrClientSendMsg);
                //将发送的信息追加到聊天内容文本框中
                textBox4.AppendText("welinkirt " + DateTime.Now.ToString() + "\r\n" + sendMsg + "\r\n");
            }
            catch (Exception ex)
            {
                this.textBox4.AppendText("远程服务器已中断连接,无法发送消息！" + "\r\n");
            }
        }

        private void button3_Click(object sender, EventArgs e)
        {
            socketClient = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);// 创建Socket对象
            IPAddress ipaddress = IPAddress.Parse(this.textBox2.Text.Trim());// 解析IP地址
            IPEndPoint endpoint = new IPEndPoint(ipaddress, int.Parse(this.textBox3.Text.Trim())); // 创建IPEndPoint对象
            if (button3.Text == "已连接")
            {
                try
                {
                    isThreadStart = false;// 设置线程启动标志为false
                    Thread.Sleep(600);// 等待一段时间
                    threadClient = null;// 清空线程对象


                }
                catch (Exception)
                {

                    throw;// 抛出异常
                }


            }
            if (button3.Text=="连接")
            {
                try
                {
                    socketClient.Connect(endpoint);// 连接到服务端
                    this.textBox4.AppendText("客户端连接服务端成功！" + "\r\n");// 显示连接成功信息
                    threadClient = new Thread(RecMsg);// 创建接收消息的线程
                    threadClient.IsBackground = true; // 设置为后台线程
                    isThreadStart = true;// 设置线程启动标志为true
                    threadClient.Start();// 启动线程
                    textBox2.Enabled = false;// 禁用IP地址输入框
                    textBox3.Enabled = false;// 禁用端口号输入框
                    //button3.Text = "已连接";
                }
                catch (Exception ex)
                {
                    MessageBox.Show("远程服务端断开，连接失败！" + "\r\n");// 如果发生异常，显示错误信息
                }
                
            }
            // 更新按钮文本
            switch (button3.Text)
            {
                case "已连接":
                    button3.Text = "连接";
                    textBox2.Enabled = true;
                    textBox3.Enabled = true;
                    button4.Enabled = false ;
                    break;
                case "连接":
                    button3.Text = "已连接";
                    textBox2.Enabled = false;
                    textBox3.Enabled = false;
                    button4.Enabled= true;
                    break;
                default:
                    break;
            }
        }
        // 按钮4点击事件处理方法，发送消息
        private void button4_Click(object sender, EventArgs e)
        {
            string sendmsg = textBox1.Text;// 获取要发送的消息
            ClientSendMsg(sendmsg);// 发送消息
        }

        private void button5_Click(object sender, EventArgs e)
        {
            OpenFileDialog dialog = new OpenFileDialog();// 创建文件对话框
            dialog.Multiselect = true;// 允许选择多个文件
            dialog.Title = "请选择图片";// 设置对话框标题
            dialog.Filter = "所有文件(*.*)|*.*";// 设置文件过滤条件
            if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)// 如果用户选择了文件
            {
                file = dialog.FileName;// 获取选中的文件路径
                file = file.Replace("\\", "/");// 将路径中的反斜杠替换为斜杠
                pictureBox1.ImageLocation = (file);// 设置PictureBox的图片路径
            }
        }
    }
}
