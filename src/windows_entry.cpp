#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <shellapi.h>
#include <string>
#include <vector>

int main(int argc, char** argv);

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    int argc = 0;
    LPWSTR* wide = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!wide) return 1;
    std::vector<std::string> arguments;
    for (int i = 0; i < argc; ++i) {
        const int length = WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, nullptr, 0, nullptr, nullptr);
        std::string value(length, '\0');
        WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, value.data(), length, nullptr, nullptr);
        value.resize(length - 1);
        arguments.push_back(std::move(value));
    }
    LocalFree(wide);
    std::vector<char*> argv;
    for (auto& argument : arguments) argv.push_back(argument.data());
    argv.push_back(nullptr);
    return main(argc, argv.data());
}
