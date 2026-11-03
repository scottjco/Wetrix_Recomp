#include "wetrix_devices.h"
#include <SDL.h>
#include <array>
#include <map>
#include <mutex>
#include <fstream>
#include <atomic>
#include "device_resolution.h"
#include "recompinput/players.h"
#include "recompinput/profiles.h"
#include "recompinput/input_state.h"
#include "librecomp/game.hpp"
#include "json/json.hpp"
namespace {
std::mutex mutex;
std::array<std::string,2> selected{"auto", "none"};
bool loaded=false;
std::atomic_uint8_t present_mask{0};
std::mutex inventory_mutex;
WetrixDeviceOrdinals device_ordinals;
struct Device { std::string key, name; SDL_GameController* controller; };
std::vector<Device> devices() {
    std::lock_guard inventory_lock(inventory_mutex);
    std::vector<Device> result;
    for(int i=0;i<SDL_NumJoysticks();++i) {
        auto* controller=recompinput::get_controller_from_joystick_id(SDL_JoystickGetDeviceInstanceID(i));
        if(!controller || !SDL_GameControllerGetAttached(controller)) continue;
        auto guid=recompinput::profiles::get_guid_from_sdl_controller(controller);
        auto key=recompinput::profiles::get_string_from_controller_guid(guid);
        const char* serial=SDL_GameControllerGetSerial(controller);
        const char* path=SDL_JoystickPath(SDL_GameControllerGetJoystick(controller));
        const std::string identity=key+":"+
            (serial && *serial ? std::string("serial:")+serial : path && *path ?
                std::string("path:")+path : "instance:"+std::to_string(SDL_JoystickGetDeviceInstanceID(i)));
        const auto ordinal=device_ordinals.resolve(key,identity);
        key += ":" + std::to_string(ordinal);
        const char* name=SDL_GameControllerName(controller);
        result.push_back({key,std::string(name ? name : "Controller")+" ("+std::to_string(i+1)+")",controller});
    }
    return result;
}
void load() {
    if(loaded) return;
    loaded=true;
    try {
        std::ifstream file(recomp::get_config_path()/"player_devices.json");
        if(file) { nlohmann::json j; file>>j; selected=j.at("players").get<std::array<std::string,2>>(); }
    } catch(...) { selected={"auto","none"}; }
}
}
std::vector<std::pair<std::string,std::string>> wetrix_device_options() {
    std::vector<std::pair<std::string,std::string>> result{{"auto","Automatic"},{"keyboard","Keyboard"},{"none","Not assigned"}};
    for(auto& d:devices()) result.push_back({d.key,d.name});
    return result;
}
std::string wetrix_device_selection(int player) {
    std::lock_guard lock(mutex); load(); return selected.at(player);
}
void wetrix_device_select(int player,const std::string& key) {
    std::lock_guard lock(mutex); load();
    selected.at(player)=key;
    if(key!="keyboard" && key!="none" && key!="auto" && selected[1-player]==key) selected[1-player]="none";
    std::ofstream file(recomp::get_config_path()/"player_devices.json");
    file << nlohmann::json{{"players",selected}}.dump(2);
}
void wetrix_devices_refresh() {
    std::array<std::string,2> choices;
    { std::lock_guard lock(mutex); load(); choices=selected; }
    auto available=devices();
    std::vector<std::string> keys;
    for(const auto& device:available) keys.push_back(device.key);
    const auto resolved=wetrix_resolve_devices(choices,keys);
    for(int p=0;p<2;++p) {
        auto* controller=resolved[p].controller>=0 ? available[resolved[p].controller].controller : nullptr;
        const bool keyboard=resolved[p].keyboard;
        auto& old=recompinput::players::get_player(p);
        if(old.controller!=controller || old.keyboard_enabled!=keyboard)
            recompinput::players::assign_device(p,controller,keyboard);
    }
    present_mask=wetrix_assignment_mask(resolved);
}
uint8_t wetrix_devices_present_mask() { return present_mask.load(); }
