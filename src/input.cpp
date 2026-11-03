#include "input.h"
#include <SDL.h>
#include <atomic>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include "recompinput/players.h"
#include "wetrix_devices.h"
#include "recompinput/recompinput.h"
#include "recompinput/input_events.h"
#include "recompinput/profiles.h"
static SDL_Window* game_window;
static std::array<std::atomic_uint32_t,2> state{};
void wetrix_input_key(unsigned) {}
bool wetrix_input_init(void* native_window) {
    game_window=static_cast<SDL_Window*>(native_window);
    SDL_SetHint(SDL_HINT_XINPUT_ENABLED,"1");
    SDL_SetHint(SDL_HINT_JOYSTICK_HIDAPI_PS5,"1");
    return SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER | SDL_INIT_EVENTS)==0;
}
void wetrix_input_poll() {
    recompinput::handle_events();
    wetrix_devices_refresh();
    recompinput::poll_inputs();
    for(unsigned p=0;p<2;++p) {
        if(SDL_GetKeyboardFocus()!=game_window || !wetrix_input_connected(p)) { state[p]=0; continue; }
        uint16_t buttons=0;
        float x=0,y=0;
        recompinput::profiles::get_n64_input(p,&buttons,&x,&y);
        state[p]=buttons | (uint32_t(uint8_t(int(x*80)))<<16) | (uint32_t(uint8_t(int(y*80)))<<24);
    }
    static const bool audit = std::getenv("WETRIX_TIMING_AUDIT") != nullptr;
    if (audit) {
        static auto previous = std::chrono::steady_clock::now();
        static unsigned polls = 0;
        ++polls;
        const auto now = std::chrono::steady_clock::now();
        const double seconds = std::chrono::duration<double>(now-previous).count();
        if (seconds >= 5.0) {
            printf("Controller sampling: %.1f polls/sec\n", polls/seconds);
            polls=0; previous=now;
        }
    }
}
uint32_t wetrix_input_state(unsigned player) { return wetrix_input_connected(player) ? state[player].load() : 0; }
uint8_t wetrix_input_present_mask() { return wetrix_devices_present_mask(); }
bool wetrix_input_connected(unsigned player) { return player<2 && (wetrix_input_present_mask()&(1U<<player)); }
extern "C" int wetrix_intro_skip_requested() {
    return ((wetrix_input_state(0)|wetrix_input_state(1)) & 0x1000)!=0;
}
