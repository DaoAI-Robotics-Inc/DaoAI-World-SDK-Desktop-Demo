#include <iostream>
#include <filesystem>
#include <chrono>
#include <thread>
#include <vector>
#include <memory>

#include <dwsdk/model.h>
#include <dwsdk/prediction.h>

int main() {
    namespace fs = std::filesystem;
    using Clock = std::chrono::high_resolution_clock;

    std::cout << "Compare sequential vs threaded inference across 4 different models\n";

    // 1) Initialize SDK once
    DaoAI::DeepLearning::initialize();
    DaoAI::DeepLearning::DeviceType device = DaoAI::DeepLearning::DeviceType::GPU;

    // 2) Define 4 model paths and a single test image
    std::string root1 = "../../../data/";
    std::string root2 = "C://Users//daoai//test_vision//";
    std::vector<std::string> model_fns = {
        root1 + "classification_model_fast.dwm",
        root2 + "cls_test_fast.dwm",
        root2 + "cls_fast.dwm",
        root2 + "cls2_fast.dwm"
    };
    std::string image_fn = root1 + "classification_img.png";

    // 3) Check existence
    for (auto& m : model_fns) {
        if (!fs::exists(m)) {
            std::cerr << "[ERROR] Model not found: " << m << "\n";
            return -1;
        }
    }
    if (!fs::exists(image_fn)) {
        std::cerr << "[ERROR] Image not found: " << image_fn << "\n";
        return -1;
    }

    // 4) Load image once
    DaoAI::DeepLearning::Image img(image_fn);

    const int N = (int)model_fns.size();

    // ——— Sequential inference over each model ———
    std::cout << "\n[Sequential loop inference]\n";
    auto seq_start = Clock::now();
    for (int i = 0; i < N; ++i) {
        auto t0 = Clock::now();
        auto model = std::make_unique<DaoAI::DeepLearning::Vision::Classification>(model_fns[i], device);
        auto t1 = Clock::now();
        model->inference(img);
        auto t2 = Clock::now();

        auto load_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t1 - t0).count();
        auto infer_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t2 - t1).count();
        std::cout << "Model " << (i + 1)
            << " load=" << load_ms << " ms, infer=" << infer_ms << " ms\n";
    }
    auto seq_end = Clock::now();
    auto seq_total = std::chrono::duration_cast<std::chrono::milliseconds>(seq_end - seq_start).count();
    std::cout << "Total sequential time: " << seq_total << " ms\n";

    // 5) Pre-create N model instances
    std::vector<std::unique_ptr<DaoAI::DeepLearning::Vision::Classification>> models;
    models.reserve(N);
    for (int i = 0; i < N; ++i) {
        models.emplace_back(
            std::make_unique<DaoAI::DeepLearning::Vision::Classification>(model_fns[i], device)
        );
    }

    // 6) Threaded inference (only inference time)
    std::cout << "\n[Threaded inference]\n";
    std::vector<long long> thread_infer(N);
    auto th_start = Clock::now();
    std::vector<std::thread> threads;
    threads.reserve(N);

    for (int i = 0; i < N; ++i) {
        threads.emplace_back([&, i]() {
            auto t0 = Clock::now();
            models[i]->inference(img);
            auto t1 = Clock::now();
            thread_infer[i] = std::chrono::duration_cast<std::chrono::milliseconds>(t1 - t0).count();
            });
    }
    for (auto& th : threads) {
        if (th.joinable()) th.join();
    }
    auto th_end = Clock::now();
    auto th_total = std::chrono::duration_cast<std::chrono::milliseconds>(th_end - th_start).count();

    for (int i = 0; i < N; ++i) {
        std::cout << "Model " << (i + 1)
            << " threaded infer=" << thread_infer[i] << " ms\n";
    }
    std::cout << "Total threaded inference time: " << th_total << " ms\n";

    return 0;
}
