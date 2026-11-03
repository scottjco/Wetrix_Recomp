#include "runtime.h"
#include <vector>
#include <cstdio>
#include <cstdlib>
#include "stick_repeat.h"

static unsigned inputs, pieces;
extern "C" void func_8003C940(uint8_t*,recomp_context*) { ++inputs; }
extern "C" void func_8003B3B4(uint8_t*,recomp_context*) {}
extern "C" void func_80037DE8(uint8_t*,recomp_context*) {}
extern "C" void func_800349CC(uint8_t*,recomp_context*) { ++pieces; }
static void check(bool ok) { if(!ok) { puts("Timing regression failed"); std::exit(1); } }
int main() {
    for(int hz: {30,60,240}) {
        WetrixStickRepeat fine,fast;
        int fine_moves=0,fast_moves=0;
        for(int frame=0;frame<hz;++frame) {
            fine_moves+=fine.update(20,1.0/hz);
            fast_moves+=fast.update(80,1.0/hz);
        }
        check(fine_moves>=8 && fine_moves<=10 && fast_moves>=29 && fast_moves<=31);
        check(fast.update(-80,1.0/hz)==-1);
        check(fast.update(0,1.0/hz)==0);
        check(fast.update(20,1.0/hz)==1);
    }
    WetrixStickRepeat jitter;
    check(jitter.update(11,1.0/60)==0);
    check(jitter.update(13,1.0/60)==1);
    for(int i=0;i<6;++i) check(jitter.update(i%2?11:13,1.0/60)==0);
    WetrixStickRepeat acceleration;
    check(acceleration.update(12,1.0/60)==1);
    check(acceleration.update(80,1.0/60)==0);
    check(acceleration.update(80,1.0/60)==1);
    puts("PASS: fine/full stick rates at 30/60/240 Hz, immediate reversal, neutral reset, threshold jitter");
    _putenv_s("WETRIX_GAMEPLAY_60","1");
    std::vector<uint8_t> ram(8*1024*1024);
    auto* rdram=ram.data();
    const auto word=[rdram](uint32_t a)->int32_t& { return MEM_W(0,int32_t(a)); };
    word(0x8007536C)=3; word(0x800A2774)=1; word(0x800876D0)=1;
    word(0x800A2D60)=int32_t(0x80100000); word(0x800A2780)=int32_t(0x80100000);
    word(0x800A1D80)=1;
    recomp_context ctx{};
    unsigned full=0;
    for(int n=0;n<60;++n) full+=!wetrix_control_frame(rdram,&ctx);
    check(full==30 && inputs==30 && pieces==30 && word(0x800A2428)==30);
    // One second of falling must cover exactly the same distance at 30 and
    // 60 updates, for both ordinary falling and held drop at multiple levels.
    for(int level: {0,1,10,30}) for(int step: {68+24*level,1152+32*level}) {
        word(0x801013C4)=100000;
        word(0x801013DC)=0;
        for(int n=0;n<60;++n) {
            wetrix_control_frame(rdram,&ctx);
            wetrix_piece_substep(rdram,0);
            word(0x801013C4)-=step;
            word(0x801013DC)+=level;
            wetrix_piece_substep(rdram,1);
        }
        check(word(0x801013C4)==100000-30*step);
        check(word(0x801013DC)==30*level);
    }
    word(0x800A1D10)=1;
    // Pause diagnostics must use signed guest offsets with the recomp memory
    // macros; unsigned offsets can turn guest addresses into invalid host ones.
    wetrix_timing_audit(rdram,0);
    check(wetrix_control_frame(rdram,&ctx)==0 && wetrix_control_rate()==30);
    word(0x801013C4)=1000;
    wetrix_piece_substep(rdram,0); word(0x801013C4)-=68;
    wetrix_piece_substep(rdram,1);
    check(word(0x801013C4)==932);
    // Exercise all orientations for each player, with held and opposing input.
    for(uint32_t player: {0x80100000U,0x80200000U}) for(int rotation=0;rotation<4;++rotation) {
        for(unsigned input: {0x1000U,0x8000U,0x9000U,0x0080U,0U}) {
            ctx.r5=int32_t(player); ctx.r2=input;
            word(player+0x13C8)=rotation;
            wetrix_prepare_rotation(rdram,&ctx);
            if(ctx.r2&0x1000) word(player+0x13C8)=(word(player+0x13C8)-1)&3;
            const int delta=input==0x1000 ? -1 : input==0x8000 ? 1 : 0;
            check(word(player+0x13C8)==((rotation+delta+4)&3));
        }
    }
    puts("PASS: opposite rotation, wraparound, held input, simultaneous presses, both players");
    word(0x800A1D10)=0;
    for(unsigned mode: {1U,2U}) {
        wetrix_set_fps(mode,240);
        check(wetrix_control_frame(rdram,&ctx)==0 && wetrix_control_rate()==30);
        check(wetrix_fps_target()==240);
    }
    wetrix_set_fps(0,30);
    check(wetrix_control_frame(rdram,&ctx)==0 && wetrix_control_rate()==30);
    wetrix_set_fps(0,0);
    wetrix_control_frame(rdram,&ctx);
    check(wetrix_control_rate()==60);
    puts("PASS: Original/Interpolate 30 Hz, Hybrid 60 Hz, target preserved across mode changes");
    // Rainbow visual motion remains 30 native phase steps per second. RT64's
    // output target changes interpolation only, not the native producer rate.
    for(unsigned mode: {0U,1U,2U}) for(unsigned target: {30U,60U,144U,240U}) {
        wetrix_set_fps(mode,target);
        wetrix_control_frame(rdram,&ctx);
        const int producer=(mode==0 && target!=30) ? 60 : 30;
        const float fraction=wetrix_rainbow_visual_step();
        check(fraction==(producer==60 ? 0.5f : 1.0f));
        double phase=0.0;
        int reveals=0;
        for(int n=0;n<producer;++n) {
            wetrix_control_frame(rdram,&ctx);
            phase+=0.8*wetrix_rainbow_visual_step();
            reveals+=!wetrix_control_extra();
        }
        check(phase>23.99999 && phase<24.00001 && reveals==30);
    }
    puts("PASS: rainbow visual phase/reveal cadence, Original/Interpolate/Hybrid at30/60/144/240 targets");
    puts("PASS: 60/30 cadence, original fall distance, drop credit, pause fallback");
}
