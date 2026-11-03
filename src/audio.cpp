#include "audio.h"
#include "menu.h"
#include "librecomp/rsp.hpp"
#include <SDL.h>
#include <vector>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
static SDL_AudioDeviceID device=0;
static uint32_t sample_rate=22050;
RspExitReason wetrixAspMain(uint8_t*,uint32_t);
static RspUcodeFunc* audio_microcode(const OSTask* task) {
    // The verified Wetrix aspMain text maps ROM FF80 to RAM 8000F380.
    return task->t.type==M_AUDTASK && (task->t.ucode&0x1FFFFFFF)==0xF380 ? wetrixAspMain : nullptr;
}
void wetrix_audio_task(uint8_t* rdram, uint32_t task) {
    static bool initialized=false;
    if(!initialized) {
        recomp::rsp::constants_init();
        recomp::rsp::set_callbacks({audio_microcode}); initialized=true;
    }
    if(!recomp::rsp::run_task(rdram, TO_PTR(OSTask,(int64_t)(int32_t)task))) {
        fprintf(stderr,"Audio microcode failed\n"); std::_Exit(9);
    }
}
uint32_t wetrix_audio_frequency(uint32_t hz) {
    if(device) SDL_CloseAudioDevice(device);
    if(SDL_InitSubSystem(SDL_INIT_AUDIO)!=0) { fprintf(stderr,"Audio initialization: %s\n",SDL_GetError()); std::_Exit(9); }
    SDL_AudioSpec desired{}, obtained{};
    desired.freq=hz; desired.format=AUDIO_S16SYS; desired.channels=2; desired.samples=256;
    device=SDL_OpenAudioDevice(nullptr,0,&desired,&obtained,0);
    if(!device) { fprintf(stderr,"Audio device: %s\n",SDL_GetError()); std::_Exit(9); }
    sample_rate=obtained.freq;
    SDL_PauseAudioDevice(device,0);
    printf("Audio output active: %u Hz stereo\n",sample_rate);
    return sample_rate;
}
uint32_t wetrix_audio_remaining(uint32_t maximum) {
    if(!device) return 0;
    // Keep two retraces buffered independently of the 30 Hz graphics clock.
    // SDL consumes whole device blocks, so a half-retrace lead can underrun.
    // Saturate at the game's safe arithmetic limit after long stalls.
    const uint32_t queued=SDL_GetQueuedAudioSize(device);
    const uint32_t lead=sample_rate*4/30;
    return std::min(queued>lead ? queued-lead : 0,maximum) & ~7u;
}
void wetrix_audio_queue(uint8_t* rdram, uint32_t address, uint32_t bytes) {
    address &= 0x1FFFFFFF;
    if(address+uint64_t(bytes)>0x800000 || bytes%4) { fprintf(stderr,"Invalid audio buffer address=%08X bytes=%u\n",address,bytes); std::_Exit(9); }
    if(!device) wetrix_audio_frequency(sample_rate);
    std::vector<int16_t> samples(bytes/2);
    const auto* source=reinterpret_cast<const int16_t*>(rdram+address);
    int peak=0;
    const float volume=wetrix_menu_volume();
    for(unsigned i=0;i<samples.size();++i) { samples[i]=int16_t(source[i^1]*volume); peak=std::max(peak,abs(int(samples[i]))); }
    static bool reported=false;
    if(peak && !reported) { printf("Audio synthesis verified: nonzero PCM peak=%d\n",peak); reported=true; }
    static uint64_t frames=0;
    static uint32_t empty_queues=0;
    static uint32_t last_report=SDL_GetTicks();
    if(SDL_GetQueuedAudioSize(device)==0) ++empty_queues;
    frames+=bytes/4;
    uint32_t now=SDL_GetTicks();
    if(now-last_report>=10000) {
        printf("Audio pacing: %.0f frames/sec, queue %.1f ms, empty queues %u\n", frames*1000.0/(now-last_report), SDL_GetQueuedAudioSize(device)*250.0/sample_rate, empty_queues);
        frames=0; empty_queues=0; last_report=now;
    }
    if(SDL_QueueAudio(device,samples.data(),bytes)!=0) { fprintf(stderr,"Audio queue: %s\n",SDL_GetError()); std::_Exit(9); }
}
