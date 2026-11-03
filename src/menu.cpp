#include <SDL.h>
#include <filesystem>
#include "recompui/recompui.h"
#include "recompui/config.h"
#include "recompui/program_config.h"
#include "recompui/renderer.h"
#include "recompinput/profiles.h"
#include "librecomp/game.hpp"
#include "menu.h"
#include "runtime.h"
#include <atomic>
#include <mutex>
#include <fstream>
#include "json/json.hpp"
#include "ultramodern/error_handling.hpp"
extern std::atomic_bool exited;

SDL_Window* window=nullptr;
static std::atomic<float> main_volume{0.5f};
static std::mutex config_mutex;
static bool graphics_pending=false;
static std::atomic_bool hd_textures_available{false};
static std::atomic_bool hd_textures_enabled{true};
float wetrix_menu_volume() { return main_volume.load(); }
bool wetrix_menu_hd_textures_available() { return hd_textures_available.load(); }
bool wetrix_menu_hd_textures_enabled() { return hd_textures_available.load() && hd_textures_enabled.load(); }
namespace recompui {
void process_game_started() {}
void drop_files(const std::list<std::filesystem::path>&) {}
void queue_ui_callback(ResourceId, const Event&, const UICallback&) {
    throw std::runtime_error("Guest UI callbacks are not registered in Wetrix");
}
}
namespace recomp {
static std::filesystem::path config_path;
void register_config_path(std::filesystem::path path) { config_path=std::move(path); }
std::filesystem::path get_config_path() { return config_path; }
const Version& get_project_version() { static const Version version{0,1,1,""}; return version; }
}
namespace ultramodern {
bool is_game_started() { return true; }
std::chrono::high_resolution_clock::duration time_since_start() {
    static const auto start=std::chrono::high_resolution_clock::now();
    return std::chrono::high_resolution_clock::now()-start;
}
void quit() { exited=true; }
}
namespace ultramodern::error_handling {
[[noreturn]] void quick_exit(const char* file,int line,const char* function,int status) {
    fprintf(stderr,"Menu error at %s:%d (%s)\n",file,line,function); fflush(stderr); std::_Exit(status);
}
}
namespace ultramodern::renderer {
static GraphicsConfig graphics_config;
void set_graphics_config(const GraphicsConfig& config) { std::lock_guard lock(config_mutex); graphics_config=config; graphics_pending=true; }
const GraphicsConfig& get_graphics_config() { return graphics_config; }
}
bool wetrix_menu_take_graphics(ultramodern::renderer::GraphicsConfig& config) {
    std::lock_guard lock(config_mutex);
    if(!graphics_pending) return false;
    auto& tab=recompui::config::get_graphics_config();
    wetrix_set_fps(std::get<uint32_t>(tab.get_option_value("fps_mode")),
        std::get<uint32_t>(tab.get_option_value("fps_target")));
    config=ultramodern::renderer::get_graphics_config(); graphics_pending=false; return true;
}
namespace recompui::renderer {
RT64::UserConfiguration::Antialiasing RT64MaxMSAA() { return RT64::UserConfiguration::Antialiasing::None; }
bool RT64SamplePositionsSupported() { return false; }
bool RT64HighPrecisionFBEnabled() { return false; }
}
void wetrix_menu_init(void* native_window) {
    SDL_InitSubSystem(SDL_INIT_VIDEO);
    window=SDL_GetWindowFromID(1);
    if(!window) throw std::runtime_error(SDL_GetError());
    recompui::programconfig::set_program_name("Wetrix N64 Recomp");
    recompui::programconfig::set_program_id(u8"wetrix-native");
    recomp::register_config_path(std::filesystem::absolute("config/user"));
    std::filesystem::create_directories(recomp::get_config_path());
    recompui::register_primary_font("InterVariable.ttf", "Inter Variable");
    recompinput::players::set_single_player_mode(false);
    recompinput::players::set_player_count_range(1,2);
    using G=recompinput::GameInput;
    using F=recompinput::InputField;
    recompinput::set_default_mapping_for_keyboard(G::A,{F::keyboard(SDL_SCANCODE_SPACE)});
    recompinput::set_default_mapping_for_keyboard(G::B,{F::keyboard(SDL_SCANCODE_E)});
    recompinput::set_default_mapping_for_keyboard(G::START,{F::keyboard(SDL_SCANCODE_RETURN)});
    recompinput::set_default_mapping_for_keyboard(G::DPAD_UP,{F::keyboard(SDL_SCANCODE_W)});
    recompinput::set_default_mapping_for_keyboard(G::DPAD_DOWN,{F::keyboard(SDL_SCANCODE_S)});
    recompinput::set_default_mapping_for_keyboard(G::DPAD_LEFT,{F::keyboard(SDL_SCANCODE_A)});
    recompinput::set_default_mapping_for_keyboard(G::DPAD_RIGHT,{F::keyboard(SDL_SCANCODE_D)});
    recompinput::set_default_mapping_for_keyboard(G::X_AXIS_POS,{});
    recompinput::set_default_mapping_for_keyboard(G::X_AXIS_NEG,{});
    recompinput::set_default_mapping_for_keyboard(G::Y_AXIS_POS,{});
    recompinput::set_default_mapping_for_keyboard(G::Y_AXIS_NEG,{});
    recompinput::set_default_mapping_for_keyboard(G::Z,{F::keyboard(SDL_SCANCODE_Q)});
    recompinput::set_default_mapping_for_keyboard(G::R,{F::keyboard(SDL_SCANCODE_R)});
    // Identity-free baseline shared by fresh profiles, newly attached pads and
    // Reset Bindings. Saved profiles are loaded afterwards and remain intact.
    recompinput::set_default_mapping_for_controller(G::A,{F::controller_digital(SDL_CONTROLLER_BUTTON_A)});
    recompinput::set_default_mapping_for_controller(G::B,{F::controller_digital(SDL_CONTROLLER_BUTTON_B)});
    recompinput::set_default_mapping_for_controller(G::ROTATE_REVERSE,{F::controller_digital(SDL_CONTROLLER_BUTTON_X)});
    recompinput::set_default_mapping_for_controller(G::Z,{});
    recompinput::set_default_mapping_for_controller(G::L,{F::controller_analog(SDL_CONTROLLER_AXIS_TRIGGERLEFT,true)});
    recompinput::set_default_mapping_for_controller(G::R,{F::controller_analog(SDL_CONTROLLER_AXIS_TRIGGERRIGHT,true)});
    recompinput::set_default_mapping_for_controller(G::START,{F::controller_digital(SDL_CONTROLLER_BUTTON_START)});
    recompinput::set_default_mapping_for_controller(G::C_LEFT,{F::controller_analog(SDL_CONTROLLER_AXIS_RIGHTX,false)});
    recompinput::set_default_mapping_for_controller(G::C_RIGHT,{F::controller_analog(SDL_CONTROLLER_AXIS_RIGHTX,true)});
    recompinput::set_default_mapping_for_controller(G::C_UP,{F::controller_analog(SDL_CONTROLLER_AXIS_RIGHTY,false),F::controller_digital(SDL_CONTROLLER_BUTTON_RIGHTSTICK)});
    recompinput::set_default_mapping_for_controller(G::C_DOWN,{F::controller_analog(SDL_CONTROLLER_AXIS_RIGHTY,true),F::controller_digital(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)});
    recompinput::set_default_mapping_for_controller(G::DPAD_UP,{F::controller_digital(SDL_CONTROLLER_BUTTON_DPAD_UP)});
    recompinput::set_default_mapping_for_controller(G::DPAD_DOWN,{F::controller_digital(SDL_CONTROLLER_BUTTON_DPAD_DOWN)});
    recompinput::set_default_mapping_for_controller(G::DPAD_LEFT,{F::controller_digital(SDL_CONTROLLER_BUTTON_DPAD_LEFT)});
    recompinput::set_default_mapping_for_controller(G::DPAD_RIGHT,{F::controller_digital(SDL_CONTROLLER_BUTTON_DPAD_RIGHT)});
    recompinput::set_default_mapping_for_controller(G::X_AXIS_NEG,{F::controller_analog(SDL_CONTROLLER_AXIS_LEFTX,false)});
    recompinput::set_default_mapping_for_controller(G::X_AXIS_POS,{F::controller_analog(SDL_CONTROLLER_AXIS_LEFTX,true)});
    recompinput::set_default_mapping_for_controller(G::Y_AXIS_POS,{F::controller_analog(SDL_CONTROLLER_AXIS_LEFTY,false)});
    recompinput::set_default_mapping_for_controller(G::Y_AXIS_NEG,{F::controller_analog(SDL_CONTROLLER_AXIS_LEFTY,true)});
    recompinput::set_default_mapping_for_controller(G::TOGGLE_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_BACK)});
    recompinput::set_default_mapping_for_controller(G::ACCEPT_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_A)});
    recompinput::set_default_mapping_for_controller(G::BACK_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_X)});
    recompinput::set_default_mapping_for_controller(G::APPLY_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_Y),F::controller_digital(SDL_CONTROLLER_BUTTON_START)});
    recompinput::set_default_mapping_for_controller(G::TAB_LEFT_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_LEFTSHOULDER)});
    recompinput::set_default_mapping_for_controller(G::TAB_RIGHT_MENU,{F::controller_digital(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)});
    recompui::config::GeneralTabOptions general{};
    general.has_rumble_strength=false;
    general.has_gyro_sensitivity=false;
    general.has_mouse_sensitivity=false;
    recompui::config::create_general_tab(general);
    auto& graphics=recompui::config::create_graphics_tab();
    using namespace recompui::config::graphics;
    for(const auto& id : {options::developer_mode,options::hr_option,options::api_option,
        options::hpfb_option,options::msaa_option,options::rr_option,options::rr_manual_value})
        graphics.update_option_hidden(id,true);
    // The optional distribution pack owns every HD replacement. Keep its saved
    // preference even when the pack is temporarily removed.
    const std::filesystem::path hd_pack="Textures/hd-sprites";
    std::error_code pack_error;
    bool pack_available=std::filesystem::is_directory(hd_pack,pack_error) &&
        std::filesystem::is_regular_file(hd_pack/"rt64.json",pack_error);
    if(pack_available) {
        try {
            std::ifstream manifest(hd_pack/"rt64.json");
            const auto data=nlohmann::json::parse(manifest);
            pack_available=data.is_object() && data.contains("configuration") &&
                data["configuration"].is_object() && data.contains("textures") && data["textures"].is_array();
        } catch(const std::exception&) { pack_available=false; }
    }
    hd_textures_available=pack_available;
    graphics.add_bool_option("hd_textures","HD Textures",
        "Use the installed HD texture pack for text, menus and sprites.",true);
    graphics.update_option_hidden("hd_textures",!pack_available);
    graphics.add_option_change_callback("hd_textures",[](auto value,auto,auto) {
        hd_textures_enabled=std::get<bool>(value);
        std::lock_guard lock(config_mutex); graphics_pending=true;
    });
    graphics.add_enum_option("fps_mode", "FPS Mode",
        "Hybrid combines responsive 60 Hz controls with interpolated rendering. Interpolate keeps 30 Hz gameplay with smoother rendering. Original runs at 30 FPS.",
        {{0U,"Hybrid"},{1U,"Interpolate"},{2U,"Original"}},0U);
    graphics.add_enum_option("fps_target", "Frame Rate",
        "Display follows your monitor. Original mode always runs at 30 FPS; your selected target is remembered.",
        {{0U,"Display"},{30U,"30"},{60U,"60"},{144U,"144"},{240U,"240"},{10000U,"Unlimited"}},0U);
    graphics.add_option_disable_dependency("fps_target","fps_mode",2U);
    std::vector<recomp::config::ConfigOptionEnumOption> monitor_options{{0U,"Automatic"}};
    for(int i=0;i<SDL_GetNumVideoDisplays();++i) {
        const char* name=SDL_GetDisplayName(i);
        if(name) monitor_options.emplace_back(unsigned(i+1),name,
            "Monitor "+std::to_string(i+1)+" ("+name+")");
    }
    graphics.add_enum_option("startup_monitor","Startup Monitor",
        "Select the display used on the next launch. Automatic uses the display containing the mouse pointer. Windowed and Fullscreen both use this selection.",
        monitor_options,0U);
    auto fps_changed=[](auto,auto,auto) {
        std::lock_guard lock(config_mutex); graphics_pending=true;
    };
    graphics.add_option_change_callback("fps_mode",fps_changed);
    graphics.add_option_change_callback("fps_target",fps_changed);
    recompui::config::create_controls_tab();
    auto& sound=recompui::config::create_sound_tab();
    sound.add_option_change_callback(recompui::config::sound::options::main_volume,
        [](auto value, auto, auto) { main_volume=float(std::get<double>(value)/200.0); });
    recompui::config::finalize();
    auto& loaded_graphics=recompui::config::get_graphics_config();
    hd_textures_enabled=std::get<bool>(loaded_graphics.get_option_value("hd_textures"));
    printf("HD Textures: pack %s, option %s, preference %s\n",
        pack_available ? "installed" : "absent", pack_available ? "visible" : "hidden",
        hd_textures_enabled.load() ? "on" : "off");
    wetrix_set_fps(std::get<uint32_t>(loaded_graphics.get_option_value("fps_mode")),
        std::get<uint32_t>(loaded_graphics.get_option_value("fps_target")));
    main_volume=float(recompui::config::sound::get_main_volume()/200.0);
    recompui::set_render_hooks();
}
