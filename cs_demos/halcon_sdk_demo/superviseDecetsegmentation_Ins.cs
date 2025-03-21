using DaoAI.DeepLearningCLI.Vision;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace halcon_sdk_demo
{
    internal class superviseDecetsegmentation_Ins
    {
        #region 单例
        static object _locker = new object();
        static superviseDecetsegmentation_Ins _instance = null;
        public static superviseDecetsegmentation_Ins Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_locker)
                    {
                        _instance = new superviseDecetsegmentation_Ins();
                    }
                }
                return _instance;
            }
        }
        #endregion

        public SupervisedDefectSegmentation superviseddefectsegmentation;


        #region 方法

        /// <summary>
        /// 保存
        /// </summary>
        public void Save()
        {

        }
        /// <summary>
        /// 加载
        /// </summary>
        public void Load(string path)
        {
            // string path = @"C:\Users\Administrator\AppData\Local\Temp\DaoAI";

            //String model_path = @"D:\pretrained_model_v1.zip";
            superviseddefectsegmentation = new DaoAI.DeepLearningCLI.Vision.SupervisedDefectSegmentation(path, DaoAI.DeepLearningCLI.DeviceType.GPU, -1);
        }

        #endregion
    }
}
