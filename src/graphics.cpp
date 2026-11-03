#include "graphics.h"
#include "runtime.h"
#include "input.h"
#include "menu.h"
#include <SDL.h>
#ifdef _WIN32
#include <Windows.h>
#endif
#ifdef __APPLE__
#include <SDL_metal.h>
#endif
#if defined(_WIN32) || defined(__APPLE__)
#include <SDL_syswm.h>
#endif
#include <atomic>
#include <chrono>
#include "ultramodern/ultra64.h"
#include "hle/rt64_application.h"
#include "hle/rt64_state.h"
#include "hle/rt64_rsp.h"
#include "render/rt64_texture_cache.h"
#include <mutex>
#include <cstdio>
#include <fstream>
#include <filesystem>
#include <cstdlib>
#include "json/json.hpp"

static std::unique_ptr<RT64::Application> application;
static std::mutex graphics_mutex;
static uint8_t dmem[4096]{}, imem[4096]{};
static uint32_t regs[23]{};
static SDL_Window* window;
static std::atomic_uint32_t completed_frames{0};
static std::atomic_uint32_t presented_frames{0};
static std::atomic_uint64_t graphics_time_us{0}, graphics_calls{0}, present_time_us{0};
static bool land_detail_available=false;
void wetrix_graphics_frame_presented() { ++presented_frames; }
static void interrupts() {}

static void load_sprite_textures() {
    // Use the same native RT64 pack loader as SSSV. Missing packs leave the
    // original game textures intact; art and hash registration live in the pack.
    const std::filesystem::path pack = "Textures/hd-sprites";
    std::error_code error;
    if (wetrix_menu_hd_textures_available()) {
        try {
            if (application->textureCache->loadReplacementDirectories({RT64::ReplacementDirectory(pack)}))
                printf("RT64 sprite texture pack loaded: %s\n", pack.string().c_str());
            else
                fprintf(stderr, "RT64 sprite texture pack could not be loaded: %s\n", pack.string().c_str());
        } catch (const std::exception& e) {
            fprintf(stderr, "RT64 sprite texture pack fallback: %s\n", e.what());
        }
    }
    error.clear();
    if(wetrix_menu_hd_textures_available() &&
        std::filesystem::is_regular_file(pack/"terrain/land-detail.png",error)) {
        try {
            // The pack's preloader owns this texture and its lifetime. Calling
            // the editor's addReplacement API here would replace its Preload
            // operation with Auto, incorrectly enabling reference counting on
            // a permanent texture that has no reverse-map cache entry.
            land_detail_available=application->textureCache->hasReplacement(RT64::State::WetrixLandDetailHash);
            if(land_detail_available) printf("RT64 optional ground detail material available\n");
        } catch(const std::exception& e) {
            fprintf(stderr,"RT64 ground detail fallback: %s\n",e.what());
        }
    }
    application->state->wetrixLandDetailEnabled=land_detail_available && wetrix_menu_hd_textures_enabled();
    {
        std::lock_guard lock(application->textureCache->textureMapMutex);
        application->textureCache->textureMap.replacementMapEnabled=wetrix_menu_hd_textures_enabled();
    }

    // Optional authoring capture: RT64 writes its own hash-versioned PNGs,
    // tile metadata and TMEM dumps. Enable before visiting scenes to inventory.
    const char* dump_directory = std::getenv("WETRIX_DUMP_TEXTURES");
    if (dump_directory && *dump_directory) {
        const std::filesystem::path destination = std::filesystem::u8path(dump_directory);
        error.clear();
        std::filesystem::create_directories(destination, error);
        if (!error && std::filesystem::is_directory(destination, error)) {
            application->state->dumpingTexturesDirectory = destination;
            printf("RT64 texture capture enabled: %s\n", destination.string().c_str());
        } else {
            fprintf(stderr, "RT64 texture capture directory unavailable: %s\n", dump_directory);
        }
    }
}

bool wetrix_graphics_init(uint8_t* rdram, uint8_t* header) {
#ifdef _WIN32
    SetProcessDPIAware();
#endif
    if(SDL_InitSubSystem(SDL_INIT_VIDEO)!=0) return false;
    SDL_Rect area{0,0,1280,720};
    SDL_GetDisplayUsableBounds(0,&area);
    // Automatic follows the cursor, including displays with negative origins.
    // Backends without global mouse coordinates retain display zero's fallback.
    int mouse_x=0,mouse_y=0;
    SDL_ClearError();
    SDL_GetGlobalMouseState(&mouse_x,&mouse_y);
    if (!*SDL_GetError()) {
        for(int i=0;i<SDL_GetNumVideoDisplays();++i) {
            SDL_Rect bounds{};
            if(SDL_GetDisplayBounds(i,&bounds)==0 && mouse_x>=bounds.x && mouse_y>=bounds.y &&
               mouse_x-bounds.x<bounds.w && mouse_y-bounds.y<bounds.h) {
                SDL_Rect usable{};
                if(SDL_GetDisplayUsableBounds(i,&usable)==0) area=usable;
                break;
            }
        }
    }
    // Read the saved startup display before creating the window/settings UI.
    // SDL's display name is also used as the enum key in the menu.
    SDL_Rect startup_area=area;
    try {
        std::ifstream file("config/user/graphics.json");
        nlohmann::json settings; if(file) file>>settings;
        const std::string selected=settings.value("startup_monitor",std::string("Automatic"));
        for(int i=0;i<SDL_GetNumVideoDisplays();++i) {
            const char* name=SDL_GetDisplayName(i);
            if(name && selected==name) {
                SDL_Rect bounds;
                if(SDL_GetDisplayUsableBounds(i,&bounds)==0)
                    startup_area=bounds;
                break;
            }
        }
    } catch(const std::exception& e) { fprintf(stderr,"Startup display fallback: %s\n",e.what()); }
    const int startup_width=startup_area.w*3/4;
    const int startup_height=startup_area.h*3/4;
    Uint32 window_flags=SDL_WINDOW_SHOWN|SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI;
#ifdef __APPLE__
    window_flags |= SDL_WINDOW_METAL;
#elif !defined(_WIN32)
    window_flags |= SDL_WINDOW_VULKAN;
#endif
    window=SDL_CreateWindow("Wetrix N64 Recomp | 0.0 FPS",
        startup_area.x+(startup_area.w-startup_width)/2,
        startup_area.y+(startup_area.h-startup_height)/2,
        startup_width,startup_height,window_flags);
    if(!window) return false;
#if defined(_WIN32) || defined(__APPLE__)
    SDL_SysWMinfo info{}; SDL_VERSION(&info.version);
    if(!SDL_GetWindowWMInfo(window,&info)) return false;
#endif
    if (!wetrix_input_init(window)) return false;
    try { wetrix_menu_init(window); }
    catch(const std::exception& e) { fprintf(stderr,"Settings initialization failed: %s\n",e.what()); return false; }
    RT64::Application::Core core{};
#ifdef _WIN32
    core.window = info.info.win.window;
#elif defined(__APPLE__)
    core.window.window = info.info.cocoa.window;
    SDL_MetalView metal_view=SDL_Metal_CreateView(window);
    if(!metal_view) return false;
    core.window.view = SDL_Metal_GetLayer(metal_view);
    if(!core.window.view) return false;
#else
    core.window = window;
#endif
    core.HEADER = header; core.RDRAM = rdram; core.DMEM = dmem; core.IMEM = imem;
    core.checkInterrupts = interrupts;
    core.MI_INTR_REG = &regs[0];
    core.DPC_START_REG = &regs[1]; core.DPC_END_REG = &regs[2]; core.DPC_CURRENT_REG = &regs[3];
    core.DPC_STATUS_REG = &regs[4]; core.DPC_CLOCK_REG = &regs[5]; core.DPC_BUFBUSY_REG = &regs[6];
    core.DPC_PIPEBUSY_REG = &regs[7]; core.DPC_TMEM_REG = &regs[8];
    core.VI_STATUS_REG = &regs[9]; core.VI_ORIGIN_REG = &regs[10]; core.VI_WIDTH_REG = &regs[11];
    core.VI_INTR_REG = &regs[12]; core.VI_V_CURRENT_LINE_REG = &regs[13]; core.VI_TIMING_REG = &regs[14];
    core.VI_V_SYNC_REG = &regs[15]; core.VI_H_SYNC_REG = &regs[16]; core.VI_LEAP_REG = &regs[17];
    core.VI_H_START_REG = &regs[18]; core.VI_V_START_REG = &regs[19]; core.VI_V_BURST_REG = &regs[20];
    core.VI_X_SCALE_REG = &regs[21]; core.VI_Y_SCALE_REG = &regs[22];
    RT64::ApplicationConfiguration config;
    config.appId = "wetrix-native";
    config.useConfigurationFile = false;
    config.detectDataPath = false;
    config.dataPath = "build/rt64-user";
    application = std::make_unique<RT64::Application>(core, config);
#ifdef _WIN32
    application->userConfig.graphicsAPI = RT64::UserConfiguration::GraphicsAPI::D3D12;
#elif defined(__APPLE__)
    application->userConfig.graphicsAPI = RT64::UserConfiguration::GraphicsAPI::Metal;
#else
    application->userConfig.graphicsAPI = RT64::UserConfiguration::GraphicsAPI::Vulkan;
#endif
    application->userConfig.resolution = RT64::UserConfiguration::Resolution::Original;
    application->userConfig.antialiasing = RT64::UserConfiguration::Antialiasing::None;
    application->userConfig.aspectRatio = RT64::UserConfiguration::AspectRatio::Expand;
    application->userConfig.extAspectRatio = RT64::UserConfiguration::AspectRatio::Original;
    // Match the recomp presentation path: submit each completed game frame
    // directly, rather than depending on delayed VI framebuffer rotation.
    application->enhancementConfig.presentation.mode = RT64::EnhancementConfiguration::Presentation::Mode::PresentEarly;
    #ifdef _WIN32
    auto result = application->setup(GetCurrentThreadId());
#else
    auto result = application->setup(0);
#endif
    printf("RT64 setup result %d\n", (int)result);
    if (result == RT64::Application::SetupResult::Success) load_sprite_textures();
    return result == RT64::Application::SetupResult::Success;
}

void wetrix_graphics_task(uint8_t* rdram, uint32_t address) {
    std::lock_guard lock(graphics_mutex);
    auto* task = TO_PTR(OSTask, (int64_t)(int32_t)address);
    const auto task_start=std::chrono::steady_clock::now();
    application->state->rsp->reset();
    // Keep RT64's interpolation source rate independent of the 60 Hz audio VI.
    application->state->setRefreshRate(wetrix_control_rate());
    application->interpreter->loadUCodeGBI(task->t.ucode & 0x3FFFFFF, task->t.ucode_data & 0x3FFFFFF, true);
    application->processDisplayLists(rdram, task->t.data_ptr & 0x3FFFFFF, 0, true);
    graphics_time_us+=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-task_start).count();
    ++graphics_calls;
    ++completed_frames;
}

bool wetrix_graphics_poll() {
    SDL_PumpEvents();
    if(SDL_HasEvent(SDL_QUIT)) return false;
    wetrix_input_poll();
    return true;
}

bool wetrix_graphics_present(uint8_t* rdram, uint32_t fb, uint32_t mode_addr, bool black) {
    static auto previous = std::chrono::steady_clock::now();
    const auto now = std::chrono::steady_clock::now();
    const double elapsed = std::chrono::duration<double>(now-previous).count();
    if (elapsed >= 1.0) {
        char title[80];
        const double game_fps=completed_frames.exchange(0)/elapsed;
        const double render_fps=presented_frames.exchange(0)/elapsed;
        snprintf(title,sizeof(title),"Wetrix N64 Recomp | %.1f FPS",render_fps);
        static unsigned reports=0;
        if(++reports%10==0) {
            const auto calls=graphics_calls.exchange(0);
            printf("Frame pacing: game %.1f FPS, rendered %.1f FPS; graphics %.2f ms/task, presentation %.2f ms/task\n",game_fps,render_fps,
                graphics_time_us.exchange(0)/1000.0/std::max(uint64_t(1),calls),present_time_us.exchange(0)/1000.0/std::max(uint64_t(1),calls));
        }
        SDL_SetWindowTitle(window, title); previous=now;
    }
    if (!fb || !mode_addr) return true;
    if ((mode_addr & 0x1FFFFFFF) + sizeof(OSViMode) > 0x800000) return false;
    std::lock_guard lock(graphics_mutex);
    auto* mode = TO_PTR(OSViMode, (int64_t)(int32_t)mode_addr);
    ultramodern::renderer::GraphicsConfig settings;
    if(wetrix_menu_take_graphics(settings)) {
        application->state->wetrixLandDetailEnabled=land_detail_available && wetrix_menu_hd_textures_enabled();
        // RT64's render workers read this switch under textureMapMutex too.
        // Apply UI changes on the existing graphics path, never in its callback.
        {
            std::lock_guard texture_lock(application->textureCache->textureMapMutex);
            application->textureCache->textureMap.replacementMapEnabled=wetrix_menu_hd_textures_enabled();
        }
        using R=ultramodern::renderer::Resolution;
        auto& config=application->userConfig;
        config.aspectRatio=settings.ar_option==ultramodern::renderer::AspectRatio::Original ?
            RT64::UserConfiguration::AspectRatio::Original : RT64::UserConfiguration::AspectRatio::Expand;
        config.resolution=settings.res_option==R::Auto ? RT64::UserConfiguration::Resolution::WindowIntegerScale : RT64::UserConfiguration::Resolution::Manual;
        config.resolutionMultiplier=(settings.res_option==R::Original2x ? 2.0 : 1.0)*std::max(1,settings.ds_option);
        config.downsampleMultiplier=std::max(1,settings.ds_option);
        const unsigned target=wetrix_fps_target();
        using Rate=RT64::UserConfiguration::RefreshRate;
        config.refreshRate=wetrix_fps_mode()==2 ? Rate::Original :
            target==0 ? Rate::Display : target==10000 ? Rate::Unlimited : Rate::Manual;
        config.refreshRateTarget=int(target ? target : 60);
        application->updateUserConfig(true);
        static bool fullscreen=false;
        bool desired=settings.wm_option==ultramodern::renderer::WindowMode::Fullscreen;
        if(desired!=fullscreen) {
            SDL_SetWindowFullscreen(window,desired ? SDL_WINDOW_FULLSCREEN_DESKTOP : 0);
            fullscreen=desired;
        }
    }
    auto& common = mode->comRegs;
    auto& field = mode->fldRegs[0];
    regs[9] = common.ctrl;
    regs[10] = (fb & 0x1FFFFFFF) + field.origin;
    regs[11] = common.width; regs[12] = field.vIntr; regs[14] = common.burst;
    regs[15] = common.vSync; regs[16] = common.hSync; regs[17] = common.leap;
    regs[18] = black ? 0 : common.hStart; regs[19] = field.vStart; regs[20] = field.vBurst;
    regs[21] = common.xScale; regs[22] = field.yScale;
    const auto present_start=std::chrono::steady_clock::now();
    application->updateScreen();
    present_time_us+=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-present_start).count();
    return true;
}
