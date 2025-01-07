#include <iostream>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>

#include <iostream>
#include <fstream>
#include <cstring>


int main()
{
    std::cout << "Start DaoAI World \"instance segmentation\" model example !" << std::endl;

    std::string rootpath = "./data/";
    std::string image_path = rootpath + "output/instance_segmentation_img.jpg";   //ͼ��·��
    std::string model_path = rootpath + "output/instance_segmentation_model.dwm";    //ģ��·��

    try
    {
        /*
         * step 0: SDK ��ʼ��
         */
        std::cout << "step 0: DW SDK initialize" << std::endl;
        DaoAI::DeepLearning::initialize();

        /*
         * step 1: ���� DaoAI API ����ͼ��
         */
        std::cout << "step 1: Call the DaoAI API to load the image" << std::endl;
        DaoAI::DeepLearning::Image image(image_path);


        /*
         * step 2: ���� DaoAI API ����ģ��
         *
         * p.s.���ѧϰģ���Ǵ� DaoAI world ��ҳ��ѵ����ɺ�����������
         */
        std::cout << "step 2: Call the DaoAI API to load the instance segmentation model" << std::endl;
        DaoAI::DeepLearning::Vision::InstanceSegmentation model(model_path);

        /*
         * step 3: ʹ�����ѧϰģ�ͽ���Ԥ��
         */
        std::cout << "step 3: Use deep learning models to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::InstanceSegmentationResult prediction = model.inference(image);

        /*
         * step 4: ������
         */
        std::cout << "step 4: Result output" << std::endl;
        DaoAI::DeepLearning::Image resultImage = DaoAI::DeepLearning::Utils::visualize(image, prediction);

        // д��json�ļ�
        std::cout << "write to json file" << std::endl;
        std::ofstream fout(rootpath + "output/testInstanceSegmentation_Result.json");
        fout << prediction.toJSONString() << "\n";
        fout.close();

        //���ͼ��д��
        std::cout << "write result image" << std::endl;
        resultImage.save(rootpath + "output/testInstanceSegmentation_Result.bmp");

        std::cout << "Over" << std::endl;

        system("pause");
        return 0;
    }
    catch (const std::exception&)
    {
        std::cout << "Failed !" << std::endl;
        return -1;
    }
}