#include "startup.h"
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <nfd.h>
#define XXH_INLINE_ALL
#include "xxHash/xxhash.h"
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>

namespace fs = std::filesystem;

static void startup_error(const char* message) {
    SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Wetrix Recompiled", message, nullptr);
}

static bool read_supported_rom(const fs::path& path, std::vector<uint8_t>& rom) {
    std::error_code ec;
    if (fs::file_size(path, ec) != 0x800000 || ec) return false;
    std::ifstream input(path, std::ios::binary);
    rom.assign(std::istreambuf_iterator<char>(input), {});
    // The supported big-endian US revision, verified against the project ROM.
    return rom.size() == 0x800000 && XXH3_64bits(rom.data(), rom.size()) == 0x7a64fdf6513d3659ULL;
}

int wetrix_load_rom(int argc, char** argv, std::vector<uint8_t>& rom) {
    SDL_SetMainReady();
    if (argc > 2) {
        startup_error("Open Wetrix Recompiled directly, or pass one Wetrix ROM path.");
        return -1;
    }
    std::error_code ec;
    fs::path requested;
    if (argc == 2) requested = fs::absolute(fs::u8path(argv[1]), ec);
    else {
        // Explorer, shortcuts and terminal launches may start in another folder.
        char* base = SDL_GetBasePath();
        if (!base) { startup_error("Could not locate the application folder."); return -1; }
        fs::current_path(fs::u8path(base), ec);
        SDL_free(base);
        if (ec) { startup_error("Could not open the application folder."); return -1; }
        requested = fs::path("Assets") / "data.z64";
    }
    if (read_supported_rom(requested, rom)) return 0;
    if (fs::exists(requested))
        startup_error("This ROM is not the supported Wetrix revision. Select the original big-endian US revision 0 .z64 ROM (8 MiB).");

    if (NFD_Init() != NFD_OKAY) {
        startup_error("The ROM file picker could not start. Place your supported ROM at Assets/data.z64 and try again.");
        return -1;
    }
    for (;;) {
        nfdu8char_t* chosen = nullptr;
        const nfdu8filteritem_t filter{"Wetrix N64 ROM", "z64"};
        const nfdresult_t result = NFD_OpenDialogU8(&chosen, &filter, 1, nullptr);
        if (result != NFD_OKAY) {
            if (result == NFD_ERROR) startup_error("The ROM file picker failed. Place your supported ROM at Assets/data.z64 and try again.");
            NFD_Quit();
            return result == NFD_CANCEL ? 1 : -1;
        }
        fs::path selected = fs::u8path(chosen);
        NFD_FreePathU8(chosen);
        if (!read_supported_rom(selected, rom)) {
            startup_error("That file is not the supported Wetrix ROM. Select the original big-endian US revision 0 .z64 ROM (8 MiB).");
            continue;
        }
        // Import only the user's verified selection so subsequent launches work.
        fs::create_directories("Assets", ec);
        if (!ec) fs::copy_file(selected, fs::path("Assets") / "data.z64", fs::copy_options::overwrite_existing, ec);
        if (ec) SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_WARNING, "Wetrix Recompiled",
            "The ROM will work for this session, but could not be saved in Assets. Extract the application to a writable folder to remember it.", nullptr);
        NFD_Quit();
        return 0;
    }
}
