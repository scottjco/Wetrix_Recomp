#include "runtime.h"
#include "funcs.h"
#include "graphics.h"
#include "input.h"
#include "audio.h"
#include "pak.h"
#include "controller_bridge.h"
#include <memory>
#include "ultramodern/ultramodern.hpp"
#include <atomic>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <mutex>
#include <vector>
#ifdef _WIN32
#include <Windows.h>
#endif

std::atomic_bool exited{false};
static std::vector<uint8_t> rom;
static std::unique_ptr<WetrixPak> controller_pak;
static std::array<uint8_t,64> pif_ram{};
static std::vector<uint8_t> ram(8 * 1024 * 1024);
static thread_local uint32_t status_register = 0x34000001;
static auto start_time = std::chrono::steady_clock::now();
struct Event { int32_t queue = 0; int32_t message = 0; };
static std::mutex event_mutex;
static Event events[16], vi_event;
static std::atomic_bool vi_started{false};
static std::atomic_bool pending_dp{false};
static std::atomic_bool vi_black{true};
static std::atomic_uint32_t vi_mode{0}, vi_features{0}, framebuffer{0};
static void send_event(unsigned id) {
    Event event;
    { std::lock_guard lock(event_mutex); event = events[id]; }
    if (event.queue) ultramodern::enqueue_external_message(event.queue, event.message, false, id == OS_EVENT_SP || id == OS_EVENT_DP || id == OS_EVENT_SI);
}
static const std::map<uint32_t, recomp_func_t*> dispatch{
#include "dispatch.inl"
};
extern "C" void wetrix_yield(uint8_t* rdram) {
    ultramodern::wait_for_external_message_timed(rdram, 1);
    ultramodern::check_running_queue(rdram);
}
extern "C" void wetrix_unimplemented(const char* name) {
    fprintf(stderr, "STOP: runtime service not yet implemented: %s\n", name);
    fflush(nullptr);
    std::_Exit(2);
}
extern "C" recomp_func_t* get_function(int32_t address) {
    auto entry = dispatch.find((uint32_t)address);
    if (entry == dispatch.end()) {
        fprintf(stderr, "STOP: unresolved function %08X\n", (uint32_t)address);
        fflush(nullptr); std::_Exit(3);
    }
    return entry->second;
}
extern "C" void do_break(uint32_t address) {
    fprintf(stderr, "STOP: MIPS break at %08X\n", address);
    fflush(nullptr); std::_Exit(4);
}
extern "C" void switch_error(const char* name, uint32_t address, uint32_t table) {
    fprintf(stderr, "STOP: switch %s at %08X table %08X\n", name, address, table);
    fflush(nullptr); std::_Exit(5);
}
extern "C" gpr cop0_status_read(recomp_context*) { return status_register; }
extern "C" void cop0_status_write(recomp_context*, gpr value) { status_register = (uint32_t)value; }

void run_thread_function(uint8_t* rdram, uint64_t address, uint64_t sp, uint64_t arg) {
    printf("RUN thread %d entry=%08X stack=%08X\n", osGetThreadId(rdram, 0), (uint32_t)address, (uint32_t)sp);
    recomp_context context{};
    context.f_odd = &context.f0.u32h;
    context.r29 = (int32_t)sp;
    context.r4 = (int32_t)arg;
    get_function((int32_t)address)(rdram, &context);
}

extern "C" void osInitialize_recomp(uint8_t*, recomp_context*) {
    // Hardware setup is replaced by host runtime initialization before entry.
    puts("OS initialized: host thread and message runtime");
}
extern "C" void osCreateThread_recomp(uint8_t* rdram, recomp_context* ctx) {
    printf("CREATE thread %d entry=%08X priority=%d\n", (int)ctx->r5, (uint32_t)ctx->r6, MEM_W(0x14, ctx->r29));
    osCreateThread(rdram, (int32_t)ctx->r4, (int32_t)ctx->r5, (int32_t)ctx->r6,
        (int32_t)ctx->r7, MEM_W(0x10, ctx->r29), MEM_W(0x14, ctx->r29));
}
extern "C" void osStartThread_recomp(uint8_t* rdram, recomp_context* ctx) {
    osStartThread(rdram, (int32_t)ctx->r4);
    if (ultramodern::is_entrypoint_thread()) throw ultramodern::thread_terminated{};
}
extern "C" void osDestroyThread_recomp(uint8_t* rdram, recomp_context* ctx) { osDestroyThread(rdram, (int32_t)ctx->r4); }
extern "C" void osSetThreadPri_recomp(uint8_t* rdram, recomp_context* ctx) { osSetThreadPri(rdram, (int32_t)ctx->r4, (int32_t)ctx->r5); }
extern "C" void osCreateMesgQueue_recomp(uint8_t* rdram, recomp_context* ctx) { osCreateMesgQueue(rdram, (int32_t)ctx->r4, (int32_t)ctx->r5, (int32_t)ctx->r6); }
extern "C" void osRecvMesg_recomp(uint8_t* rdram, recomp_context* ctx) { ctx->r2 = osRecvMesg(rdram, (int32_t)ctx->r4, (int32_t)ctx->r5, (int32_t)ctx->r6); }
extern "C" void osSendMesg_recomp(uint8_t* rdram, recomp_context* ctx) { ctx->r2 = osSendMesg(rdram, (int32_t)ctx->r4, (int32_t)ctx->r5, (int32_t)ctx->r6); }
extern "C" void osCreatePiManager_recomp(uint8_t* rdram, recomp_context* ctx) {
    // Host DMA service completes directly and sends its completion message.
    osCreateMesgQueue(rdram, (int32_t)ctx->r5, (int32_t)ctx->r6, (int32_t)ctx->r7);
    puts("PI command queue ready");
}
extern "C" void osCreateViManager_recomp(uint8_t*, recomp_context*) {
    if (vi_started.exchange(true)) return;
    std::thread([] {
        auto next = std::chrono::steady_clock::now();
        unsigned retraces=0;
        while (!exited) {
            next += std::chrono::nanoseconds(16666667);
            std::this_thread::sleep_until(next);
            if (((++retraces & 1)==0 || wetrix_control_rate()==60) && pending_dp.exchange(false)) send_event(OS_EVENT_DP);
            send_event(OS_EVENT_VI);
            Event event;
            { std::lock_guard lock(event_mutex); event = vi_event; }
            if (event.queue) ultramodern::enqueue_external_message(event.queue, event.message, false, false);
        }
    }).detach();
    puts("VI/audio running at 60 Hz; graphics completion paced at 30 Hz");
}
extern "C" void osSetEventMesg_recomp(uint8_t*, recomp_context* ctx) {
    if (ctx->r4 >= 16) wetrix_unimplemented("invalid event ID");
    std::lock_guard lock(event_mutex);
    printf("EVENT id=%u queue=%08X message=%08X\n", (unsigned)ctx->r4, (unsigned)ctx->r5, (unsigned)ctx->r6);
    events[ctx->r4] = {(int32_t)ctx->r5, (int32_t)ctx->r6};
}
extern "C" void osViSetEvent_recomp(uint8_t*, recomp_context* ctx) {
    std::lock_guard lock(event_mutex);
    printf("VI EVENT queue=%08X message=%08X count=%u\n", (unsigned)ctx->r4, (unsigned)ctx->r5, (unsigned)ctx->r6);
    vi_event = {(int32_t)ctx->r4, (int32_t)ctx->r5};
    if (ctx->r6 != 1) wetrix_unimplemented("VI retrace count other than 1");
}
extern "C" void osViSetMode_recomp(uint8_t*, recomp_context* ctx) { vi_mode = (uint32_t)ctx->r4; }
extern "C" void osViBlack_recomp(uint8_t*, recomp_context* ctx) { vi_black = ctx->r4 != 0; }
extern "C" void osViSetSpecialFeatures_recomp(uint8_t*, recomp_context* ctx) { vi_features = (uint32_t)ctx->r4; }
extern "C" void osViSwapBuffer_recomp(uint8_t*, recomp_context* ctx) {
    framebuffer = (uint32_t)ctx->r4;
}
static uint64_t ticks() {
    auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - start_time).count();
    return uint64_t(ns) * 46875 / 1000000;
}
extern "C" void osGetTime_recomp(uint8_t*, recomp_context* ctx) { auto t = ticks(); ctx->r2 = (int32_t)(t >> 32); ctx->r3 = (int32_t)t; }
extern "C" void osGetCount_recomp(uint8_t*, recomp_context* ctx) { ctx->r2 = (int32_t)ticks(); }
extern "C" void osSetIntMask_recomp(uint8_t*, recomp_context* ctx) { static thread_local uint32_t mask = 0x3FFF01; ctx->r2 = mask; mask = (uint32_t)ctx->r4; }
// Host RAM is coherent; guest cache management has no additional work.
extern "C" void osInvalDCache_recomp(uint8_t*, recomp_context*) {}
extern "C" void osWritebackDCache_recomp(uint8_t*, recomp_context*) {}
extern "C" void osWritebackDCacheAll_recomp(uint8_t*, recomp_context*) {}
extern "C" void osVirtualToPhysical_recomp(uint8_t*, recomp_context* ctx) {
    const uint32_t addr = (uint32_t)ctx->r4;
    if ((addr & 0xC0000000u) != 0x80000000u && addr >= ram.size()) {
        fprintf(stderr, "Unmapped virtual address %08X\n", addr);
        wetrix_unimplemented("TLB address translation");
    }
    ctx->r2 = addr & 0x1FFFFFFF;
}
static void dma(uint8_t* rdram, uint32_t dest, uint32_t source, uint32_t size, uint32_t direction, int32_t queue) {
    dest &= 0x1FFFFFFF;
    source &= 0x0FFFFFFF;
    if (direction != 0 || uint64_t(source) + size > rom.size() || uint64_t(dest) + size > ram.size())
        wetrix_unimplemented("DMA outside ROM/RAM or write DMA");
    for (uint32_t i = 0; i < size; ++i) rdram[(dest + i) ^ 3] = rom[source + i];
    osSendMesg(rdram, queue, 0, OS_MESG_NOBLOCK);
}
extern "C" void osPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx) {
    dma(rdram, MEM_W(0x10, ctx->r29), (uint32_t)ctx->r7, MEM_W(0x14, ctx->r29), (uint32_t)ctx->r6, MEM_W(0x18, ctx->r29));
    ctx->r2 = 0;
}
extern "C" void osEPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx) {
    auto* msg = TO_PTR(OSIoMesg, ctx->r5);
    dma(rdram, msg->dramAddr, msg->devAddr, msg->size, (uint32_t)ctx->r6, msg->hdr.retQueue);
    ctx->r2 = 0;
}
extern "C" void osCartRomInit_recomp(uint8_t* rdram, recomp_context* ctx) {
    // Use Wetrix's existing handle allocation identified in the original routine.
    auto* handle = TO_PTR(OSPiHandle, (int64_t)(int32_t)0x80082CC0u);
    memset(handle, 0, sizeof(*handle)); handle->baseAddress = 0xB0000000;
    ctx->r2 = (int32_t)0x80082CC0u;
}
extern "C" void wetrix_sync_controller_presence(uint8_t* rdram) {
    static std::atomic_uint8_t previous_mask{0};
    const uint8_t mask=wetrix_input_present_mask();
    const uint8_t previous=previous_mask.exchange(mask);
    if(previous!=mask) {
        wetrix_clear_disconnected_ports(rdram,previous&~mask);
        printf("Native controller ports: mask %02X; P1 %s, P2 %s\n",unsigned(mask),
            mask&1 ? "present" : "absent",mask&2 ? "present" : "absent");
    }
    wetrix_write_native_port_presence(rdram,mask);
}
extern "C" void osContInit_recomp(uint8_t* rdram, recomp_context* ctx) {
    // libultra's pak routines share these globals with osContInit.
    MEM_B(0, (int32_t)0x80082D81u) = 4;
    MEM_B(0, (int32_t)0x80082D80u) = 0xFE;
    const uint8_t mask=wetrix_input_present_mask();
    MEM_B(0,ctx->r5)=mask;
    wetrix_write_controller_status(rdram,int32_t(ctx->r6),mask);
    ctx->r2 = 0;
}
extern "C" void osContStartReadData_recomp(uint8_t* rdram, recomp_context* ctx) { send_event(OS_EVENT_SI); ctx->r2 = 0; }
extern "C" void osContGetReadData_recomp(uint8_t* rdram, recomp_context* ctx) {
    const uint8_t mask=wetrix_input_present_mask();
    wetrix_write_controller_reads(rdram,int32_t(ctx->r4),mask,{wetrix_input_state(0),wetrix_input_state(1)});
    wetrix_sync_controller_presence(rdram);
}
extern "C" void osContStartQuery_recomp(uint8_t*,recomp_context* ctx) { send_event(OS_EVENT_SI);ctx->r2=0; }
extern "C" void osContGetQuery_recomp(uint8_t* rdram,recomp_context* ctx) {
    wetrix_write_controller_status(rdram,int32_t(ctx->r4),wetrix_input_present_mask());
    wetrix_sync_controller_presence(rdram);
}
extern "C" void osPfsIsPlug_recomp(uint8_t* rdram, recomp_context* ctx) { MEM_B(0, ctx->r5) = wetrix_input_present_mask()&1; ctx->r2 = 0; }
extern "C" void __osSiRawStartDma_recomp(uint8_t* rdram, recomp_context* ctx) {
    const uint32_t address = uint32_t(ctx->r5) & 0x1FFFFFFF;
    if(address+64 > ram.size()) wetrix_unimplemented("PIF DMA outside RAM");
    if(ctx->r4 == 1) {
        for(unsigned i=0;i<64;++i) pif_ram[i]=rdram[(address+i)^3];
        try { controller_pak->command(pif_ram.data(),wetrix_input_state(),wetrix_input_state(1),wetrix_input_present_mask()); }
        catch(const std::exception& e) { fprintf(stderr,"Pak error: %s\n",e.what()); std::_Exit(8); }
    } else if(ctx->r4 == 0) {
        for(unsigned i=0;i<64;++i) rdram[(address+i)^3]=pif_ram[i];
    } else wetrix_unimplemented("invalid PIF DMA direction");
    ctx->r2=0; send_event(OS_EVENT_SI);
}
extern "C" void osAiSetFrequency_recomp(uint8_t*, recomp_context* ctx) { ctx->r2 = wetrix_audio_frequency((uint32_t)ctx->r4); }
extern "C" void osAiGetLength_recomp(uint8_t* rdram, recomp_context* ctx) {
    const int32_t target=MEM_W(0,(int32_t)0x80082C10u);
    const int32_t extra=MEM_W(0,(int32_t)0x80082C48u);
    ctx->r2 = wetrix_audio_remaining(uint32_t(std::max(0,target+extra-16))*4);
}
extern "C" void osAiSetNextBuffer_recomp(uint8_t* rdram, recomp_context* ctx) { wetrix_audio_queue(rdram, (uint32_t)ctx->r4, (uint32_t)ctx->r5); ctx->r2 = 0; send_event(OS_EVENT_AI); }
extern "C" void osSpTaskLoad_recomp(uint8_t*, recomp_context*) { /* Task is consumed at StartGo, as in N64ModernRuntime. */ }
extern "C" void osSpTaskStartGo_recomp(uint8_t* rdram, recomp_context* ctx) {
    auto* task = TO_PTR(OSTask, ctx->r4);
    if (task->t.type == M_GFXTASK) wetrix_graphics_task(rdram, (uint32_t)ctx->r4);
    else if (task->t.type == M_AUDTASK) wetrix_audio_task(rdram, (uint32_t)ctx->r4);
    else wetrix_unimplemented("unknown RSP task type");
    send_event(OS_EVENT_SP);
    if (task->t.type == M_GFXTASK) {
        // The native scheduler already waits for a VI before presenting.
        // Deferring completion to the next VI adds a second retrace at 60 Hz.
        if (wetrix_control_rate()==60) send_event(OS_EVENT_DP);
        else pending_dp = true;
    }
}
extern "C" void osSpTaskYield_recomp(uint8_t*, recomp_context*) { /* Tasks complete synchronously. */ }
extern "C" void osSpTaskYielded_recomp(uint8_t*, recomp_context* ctx) { ctx->r2 = 0; }

int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    if (argc != 2) { fprintf(stderr, "Usage: WetrixRuntime.exe data.z64\n"); return 1; }
    std::ifstream input(argv[1], std::ios::binary);
    rom.assign(std::istreambuf_iterator<char>(input), {});
    if (rom.size() != 0x800000) { fprintf(stderr, "Wrong ROM size\n"); return 1; }
    try {
        controller_pak = std::make_unique<WetrixPak>("saves/controller1.mpk");
        puts("Controller pak present: saves/controller1.mpk (32 KiB)");
    } catch(const std::exception& e) { fprintf(stderr,"Pak error: %s\n",e.what()); return 8; }
    uint8_t* rdram = ram.data();
    for (uint32_t i = 0x1000; i < 0x7CF80; ++i) rdram[(i - 0xC00) ^ 3] = rom[i];
    MEM_W(0, (int64_t)(int32_t)0x80000300u) = 1;
    MEM_W(0, (int64_t)(int32_t)0x80000318u) = 0x800000;
    if (!wetrix_graphics_init(rdram, rom.data())) { fprintf(stderr, "Renderer initialization failed\n"); std::_Exit(7); }
    // Resolve saved assignments and queued SDL attachment events before the
    // guest's first osContInit; SDL remains on the window thread throughout.
    wetrix_input_poll();
    ultramodern::set_entrypoint_thread();
    ultramodern::init_thread_cleanup();
    puts("Wetrix experimental native runtime");
    recomp_context context{};
    context.f_odd = &context.f0.u32h;
    try { recomp_entrypoint(rdram, &context); }
    catch (ultramodern::thread_terminated&) {}
    // SDL events stay on the window thread, but are sampled independently of
    // presentation. A high-resolution wait avoids Windows' coarse sleep tick.
#ifdef _WIN32
    HANDLE input_timer = CreateWaitableTimerExW(nullptr, nullptr, 0x2, TIMER_ALL_ACCESS);
    if (!input_timer) input_timer = CreateWaitableTimerExW(nullptr, nullptr, 0, TIMER_ALL_ACCESS);
#endif
    auto next_present = std::chrono::steady_clock::now();
    while (!exited) {
        if (!wetrix_graphics_poll()) std::_Exit(0);
        const auto now = std::chrono::steady_clock::now();
        if (now >= next_present) {
            if (!wetrix_graphics_present(rdram, framebuffer.load(), vi_mode.load(), vi_black.load())) std::_Exit(0);
            next_present = now + std::chrono::milliseconds(16);
        }
#ifdef _WIN32
        LARGE_INTEGER due; due.QuadPart = -40000; // 4 ms, approximately 250 polls/s.
        if (input_timer && SetWaitableTimer(input_timer, &due, 0, nullptr, nullptr, FALSE))
            WaitForSingleObject(input_timer, INFINITE);
        else
#endif
            std::this_thread::sleep_for(std::chrono::milliseconds(4));
    }
#ifdef _WIN32
    if (input_timer) CloseHandle(input_timer);
#endif
    std::_Exit(0);
}
