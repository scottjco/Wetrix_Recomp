#include "runtime.h"
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <atomic>
#include <vector>
#include "funcs.h"
#include "stick_repeat.h"

// First responsive-gameplay milestone: 60 Hz control/piece updates, with
// water/scoring at their original fixed step. Opt-in until play-tested.
static std::atomic<int> control_rate{30};
static std::atomic<unsigned> fps_mode{0}, fps_target{0};
extern "C" void wetrix_set_fps(unsigned mode,unsigned target) { fps_mode=mode; fps_target=target; }
extern "C" unsigned wetrix_fps_mode() { return fps_mode.load(); }
extern "C" unsigned wetrix_fps_target() { return fps_target.load(); }
static bool control_extra = false;
extern "C" void wetrix_capture_sprite(uint8_t* rdram,recomp_context* ctx) {
    static const bool enabled=std::getenv("WETRIX_CAPTURE_SPRITES")!=nullptr;
    static unsigned next=0, warmup=0;
    if(!enabled || next>=105) return;
    // Let initial texture DMA/scene setup settle before recording references.
    if(++warmup<90) return;
    // Capture-only substitution uses the original sprite renderer and its
    // exact TMEM uploads, never a guessed replacement hash.
    while(next<105 && MEM_W(int(next*4),int32_t(0x80075D10))==0) ++next;
    if(next<105) {
        ctx->r4=next++; ctx->r5=320; ctx->r6=240; ctx->r7=0;
        MEM_W(0x10,ctx->r29)=0x3F800000;
        MEM_W(0x14,ctx->r29)=0x3F800000;
        for(int offset=0x18;offset<=0x24;offset+=4) MEM_W(offset,ctx->r29)=255;
        printf("Sprite capture ID %u\n",unsigned(ctx->r4)); fflush(stdout);
    }
}
extern "C" int wetrix_precision_active(uint8_t* rdram) {
    return MEM_W(0,int32_t(0x8007536C))==3 && MEM_W(0,int32_t(0x800A1D10))==0 &&
        MEM_W(0,int32_t(0x80065980))==0 && MEM_W(0,int32_t(0x8006598C))==0;
}
extern "C" void wetrix_analog_input(uint8_t* rdram,recomp_context* ctx) {
    static std::array<std::array<WetrixStickRepeat,2>,2> sticks{};
    const unsigned player=unsigned(ctx->r22);
    if(!wetrix_precision_active(rdram)) { sticks={}; return; }
    if(player>=sticks.size()) return;
    const double dt=1.0/wetrix_control_rate();
    const int x=sticks[player][0].update(MEM_B(0,ctx->r18),dt);
    const int y=sticks[player][1].update(MEM_B(1,ctx->r18),dt);
    MEM_W(0,ctx->r10) |= (x>0?1:x<0?2:0) | (y<0?8:y>0?4:0);
}
// Input history stores held logical buttons in the low byte and press edges
// in the high byte. 0x80 is the new, separately bound reverse-rotation action.
extern "C" void wetrix_prepare_rotation(uint8_t* rdram, recomp_context* ctx) {
    const bool forward=(ctx->r2 & 0x1000)!=0;
    const bool reverse=(ctx->r2 & 0x8000)!=0;
    if (forward && reverse) ctx->r2 &= ~0x1000; // Opposing presses cancel.
    else if (reverse) {
        // The native path below subtracts one quarter turn. Offset by two
        // first so it instead adds one, retaining its sound and collision path.
        auto& rotation=MEM_W(0x13C8,ctx->r5);
        rotation=(rotation+2)&3;
        ctx->r2 |= 0x1000;
    }
}
extern "C" int wetrix_control_rate() { return control_rate.load(); }
extern "C" int wetrix_control_extra() { return control_extra; }
// Rainbow band geometry is authored once per original 30 Hz draw. Hybrid
// draws it at 60 Hz; scale only its visual phase/size increments, while keeping
// every draw so RT64 can interpolate the resulting geometry at the target FPS.
extern "C" float wetrix_rainbow_visual_step() { return 30.0f / control_rate.load(); }
extern "C" int wetrix_control_frame(uint8_t* rdram, recomp_context* ctx) {
    const bool enabled = fps_mode==0 && fps_target!=30;
    const auto word = [rdram](uint32_t a)->int32_t& { return MEM_W(0,int32_t(a)); };
    const bool active = enabled && word(0x8007536C)==3 && word(0x80075364)==0 &&
        word(0x800A2774)==1 && word(0x80065980)==0 && word(0x8006598C)==0 && word(0x800A1D10)==0;
    if (!active) { control_rate=30; control_extra=false; return 0; }
    control_rate=60;
    control_extra=!control_extra;
    if (!control_extra) return 0;
    // Preserve elapsed retraces for the original 30 Hz catch-up calculation.
    word(0x800A2428) += word(0x800A1D80);
    recomp_context sub=*ctx;
    func_8003C940(rdram,&sub);
    const int32_t saved=word(0x800A2780);
    for(int n=0;n<word(0x800876D0) && n<2;++n) {
        word(0x800A2780)=word(0x800A2D60+4*n);
        // Start remains responsive on the additional update as well.
        if (MEM_HU(0,int32_t(0x800A24A8+6*n)) & 0x1000) {
            func_8003B3B4(rdram,&sub);
            break;
        }
        func_80037DE8(rdram,&sub);
        func_800349CC(rdram,&sub);
    }
    word(0x800A2780)=saved;
    return 1;
}

extern "C" void wetrix_piece_substep(uint8_t* rdram, unsigned stage) {
    static int32_t height, drop_credit;
    if(control_rate!=60) return;
    const uint32_t player=uint32_t(MEM_W(0,int32_t(0x800A2780)));
    if(stage==0) {
        height=MEM_W(0x13C4,int32_t(player));
        drop_credit=MEM_W(0x13DC,int32_t(player));
    }
    else {
        // Divide continuous falling before collision/placement, not afterwards.
        auto& current=MEM_W(0x13C4,int32_t(player));
        current=height+(current-height)/2;
        // Held drop awards credit once per original tick, not twice. Preserve
        // the native reset when the player releases drop.
        auto& credit=MEM_W(0x13DC,int32_t(player));
        if(control_extra && credit>drop_credit) credit=drop_credit;
    }
}

// Called only on the game's main thread. Opt-in observations, not timing
// changes: distinguish displayed frames from actual input/physics updates.
extern "C" void wetrix_timing_audit(uint8_t* rdram, unsigned stage) {
    // Capture transient visual objects once when pausing. Their expiration
    // uses the 30 Hz world counter, independently of responsive piece steps.
    if(stage==0) {
        static bool was_paused=false;
        const bool paused=MEM_W(0,int32_t(0x800A1D10))!=0;
        if(paused && !was_paused) {
            for(unsigned p=0;p<2;++p) {
                const uint32_t player=uint32_t(MEM_W(int(4*p),int32_t(0x800A2D60)));
                if(player<0x80000400 || player>0x807CF800) continue;
                const int step=MEM_W(0x30738,int32_t(player));
                uint32_t object=uint32_t(MEM_W(0x306B0,int32_t(player)));
                printf("Paused visual objects: player %u world step %d\n",p+1,step);
                for(unsigned n=0;n<256 && object>=0x80000400 && object<=0x807FFFB8;++n) {
                    printf("  object %08X type %d graphic %d expiry_delta %d removed %d xyz %d/%d/%d\n",
                        object,MEM_W(0x18,int32_t(object)),MEM_W(0x10,int32_t(object)),
                        MEM_W(0x3C,int32_t(object))-step,MEM_W(0x40,int32_t(object)),
                        MEM_W(0x1C,int32_t(object)),MEM_W(0x20,int32_t(object)),MEM_W(0x24,int32_t(object)));
                    object=uint32_t(MEM_W(0,int32_t(object)));
                }
            }
            fflush(stdout);
        }
        was_paused=paused;
    }
    if(stage==0 && MEM_W(0,int32_t(0x8007536C))!=3) {
        control_rate=30;
        control_extra=false;
    }
    static const bool enabled = std::getenv("WETRIX_TIMING_AUDIT") != nullptr;
    if (!enabled || stage >= 4) return;
    static std::array<unsigned, 4> counts{};
    static auto previous = std::chrono::steady_clock::now();
    ++counts[stage];
    const auto now = std::chrono::steady_clock::now();
    const double seconds = std::chrono::duration<double>(now - previous).count();
    if (stage != 0 || seconds < 5.0) return;
    const auto word = [rdram](uint32_t address) -> int32_t {
        return MEM_W(0, int32_t(address));
    };
    const uint32_t player = uint32_t(word(0x800A2D60));
    printf("Gameplay audit: dispatch %.2f/s, input %.2f/s, world %.2f/s, piece %.2f/s; mode %d, retraces %d, paused %d",
        counts[0]/seconds, counts[1]/seconds, counts[2]/seconds, counts[3]/seconds,
        word(0x8007536C), word(0x800A1D80), word(0x800A1D10));
    if (player >= 0x80000400 && player <= 0x807CF800) {
        printf("; player %08X, step %d, countdown %d, piece %d, xyz %d/%d/%d, rotation %d",
            player, word(player+0x30738), word(player+0x13B0), word(player+0x13B8),
            word(player+0x13BC), word(player+0x13C0), word(player+0x13C4), word(player+0x13C8));
    }
    puts("");
    fflush(stdout);
    counts.fill(0);
    previous = now;
}

// Mark the original background display-list span. The renderer can extend
// that layer without relying on draw-call numbers or changing foreground scale.
static thread_local unsigned wetrix_marker_layer = 0;
static thread_local std::vector<unsigned> wetrix_marker_stack;
static thread_local bool wetrix_cpu_counter_span = false;

static bool wetrix_hud_audit_enabled() {
    static const bool enabled = std::getenv("WETRIX_HUD_AUDIT") != nullptr;
    return enabled;
}

static void wetrix_write_resolved_marker(uint8_t* rdram, unsigned layer) {
    const uint32_t dl = uint32_t(MEM_W(0, int32_t(0x800A1DAC)));
    if (dl < 0x80000400U || dl > 0x807FFFF0U) return;
    MEM_W(0, int32_t(dl)) = int32_t(0xC0575458);
    MEM_W(4, int32_t(dl)) = layer;
    MEM_W(0, int32_t(0x800A1DAC)) = int32_t(dl + 8);
    wetrix_marker_layer = layer;
}

extern "C" void wetrix_background_marker(uint8_t* rdram, unsigned layer) {
    if (layer == 11) wetrix_cpu_counter_span = true;
    else if (layer == 0) wetrix_cpu_counter_span = false;
    // Resolve player identity on the game/producer thread. The renderer only
    // consumes immutable draw-call tags, never live player pointers.
    if (layer >= 8 && layer <= 11) {
        const bool multiplayer = MEM_W(0, int32_t(0x800876D0)) == 2;
        const uint32_t current = uint32_t(MEM_W(0, int32_t(0x800A2780)));
        const uint32_t first = uint32_t(MEM_W(0, int32_t(0x800A2D60)));
        const uint32_t second = uint32_t(MEM_W(0, int32_t(0x800A2D64)));
        if (layer == 8) { // Earthquake meter: only P1 faces the outside edge.
            layer = multiplayer && current == first ? 8 : 5;
        }
        else if (layer == 9) { // Beaker and its complete next-piece preview.
            layer = !multiplayer ? 6 : current == second ? 9 : 6;
        }
        else if (layer == 10) { // Exact CPU-label span in func80024120.
            layer = multiplayer ? 10 : 0;
        }
        else { // Exact CPU-counter span; this routine draws both players.
            layer = multiplayer ? 9 : 0;
        }
    }
    wetrix_write_resolved_marker(rdram, layer);
}

extern "C" void wetrix_push_background_marker(uint8_t* rdram, unsigned layer) {
    wetrix_marker_stack.push_back(wetrix_marker_layer);
    static thread_local unsigned audit_count = 0;
    if (wetrix_hud_audit_enabled() && wetrix_cpu_counter_span && audit_count++ < 8) {
        printf("CPU HUD nested panel: parent tag11 resolved%u, child classification%u, effective%u\n",
            wetrix_marker_layer, layer, layer != 0 ? layer : wetrix_marker_layer);
        fflush(stdout);
    }
    // A small rectangle is still part of its parent's HUD producer. Only a
    // genuine full-width panel temporarily overrides that producer's tag.
    if (layer != 0) wetrix_background_marker(rdram, layer);
}

extern "C" void wetrix_pop_background_marker(uint8_t* rdram) {
    if (wetrix_marker_stack.empty()) return;
    const unsigned parent = wetrix_marker_stack.back();
    wetrix_marker_stack.pop_back();
    // Restore the already-resolved tag. Resolving tag9 again from live current
    // player RAM would misclassify CPU counters drawn in a two-player loop.
    if (wetrix_marker_layer != parent) wetrix_write_resolved_marker(rdram, parent);
    static thread_local unsigned audit_count = 0;
    if (wetrix_hud_audit_enabled() && wetrix_cpu_counter_span && audit_count++ < 8) {
        printf("CPU HUD nested panel return: restored resolved parent%u\n", wetrix_marker_layer);
        fflush(stdout);
    }
}

extern "C" void wetrix_audit_cpu_counter(unsigned player_index) {
    static thread_local unsigned audit_count = 0;
    if (!wetrix_hud_audit_enabled() || player_index != 1 || audit_count++ >= 4) return;
    printf("CPU HUD boxed counter end: tag11 active%d, resolved layer%u, panel depth%zu; %s after border, fill and three digits\n",
        wetrix_cpu_counter_span ? 1 : 0, wetrix_marker_layer, wetrix_marker_stack.size(),
        wetrix_cpu_counter_span && wetrix_marker_layer == 9 && wetrix_marker_stack.empty() ? "PASS" : "FAIL");
    fflush(stdout);
}
