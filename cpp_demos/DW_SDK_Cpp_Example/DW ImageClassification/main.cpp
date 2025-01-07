#include <iostream>
#include <dlsdk/model.h>
#include <dlsdk/prediction.h>
#include <dlsdk/utils.h>

#include <iostream>
#include <fstream>
#include <cstring>


int main()
{
    std::cout << "Start DaoAI World \"image classification\" model example !" << std::endl;

    std::string rootpath = "./data/";
    std::string image_path = rootpath + "output/classification_img.png";   //ͼ��·��
    std::string model_path = rootpath + "output/classification_model.dwm";    //ģ��·��

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
        std::cout << "step 2: Call the DaoAI API to load the Image Classification model" << std::endl;
        DaoAI::DeepLearning::Vision::Classification model(model_path);

        /*
         * step 3: ʹ�����ѧϰģ�ͽ���Ԥ��
         */
        std::cout << "step 3: Use deep learning models to make predictions" << std::endl;
        DaoAI::DeepLearning::Vision::ClassificationResult prediction = model.inference(image);

        // д��json�ļ�
        std::cout << "write to json file" << std::endl;
        std::ofstream fout(rootpath + "output/ImageClassification_result.json");
        fout << prediction.toJSONString() << "\n";
        fout.close();

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