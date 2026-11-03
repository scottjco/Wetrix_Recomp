/* Native execution diagnostic, NOT a game runtime. The two OS boundaries are
 * explicit: initialization is recorded; scheduling terminates the probe. */
#include "recomp.h"
#include "funcs.h"
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
#define RAM32(address) (*(uint32_t*)(rdram + ((uint32_t)(address) & 0x1FFFFFFF)))

static jmp_buf stop;
static uint32_t status_register;
static unsigned init_count, start_count, checks;
static int failed;
static uint32_t expected_clock;
static const char* tv_name;

static void check(int condition, const char* description) {
    ++checks;
    if (!condition) {
        fprintf(stderr, "FAIL [%s]: %s\n", tv_name, description);
        failed = 1;
        longjmp(stop, 2);
    }
}

gpr cop0_status_read(recomp_context* ctx) { (void)ctx; return status_register; }
void cop0_status_write(recomp_context* ctx, gpr value) { (void)ctx; status_register = (uint32_t)value; }

void do_break(uint32_t vram) {
    fprintf(stderr, "Unexpected MIPS break at %08X\n", vram);
    failed = 1;
    longjmp(stop, 2);
}

void probe_osInitialize(uint8_t* rdram, recomp_context* ctx) {
    ++init_count;
    check(init_count == 1, "initialization reached exactly once");
    check((uint32_t)ctx->r29 == 0x803FFFC8, "startup stack and main stack frame");
    check(RAM32(0x8007AE48) == expected_clock, "TV-dependent clock selected by original main");
    for (uint32_t i = 0x7C380; i < 0x12C040; ++i) {
        if (rdram[i] != 0) {
            check(0, "entire BSS cleared by native startup loop");
        }
    }
    check(1, "entire BSS cleared by native startup loop");
    check(rdram[0x7C37C] == 0xA5 && rdram[0x12C040] == 0xA5, "BSS boundary sentinels preserved");
    printf("  PASS %s: original startup cleared %u BSS bytes; clock %u Hz\n",
        tv_name, 0x12C040 - 0x7C380, expected_clock);
    /* Deliberately return without touching hardware. The following diagnostic
     * tests only the game's thread-construction code, not OS initialization. */
}

void probe_osStartThread(uint8_t* rdram, recomp_context* ctx) {
    ++start_count;
    const uint32_t thread = (uint32_t)ctx->r4;
    check(init_count == 1 && start_count == 1, "expected OS boundary order");
    check(thread == 0x8006D760, "first thread object address");
    check(RAM32(thread + 0x14) == 1, "thread ID written by recompiled create-thread");
    check(RAM32(thread + 0x4) == 10, "thread priority written by recompiled create-thread");
    check(RAM32(thread + 0x11C) == 0x80031EB4, "thread entrypoint written by recompiled create-thread");
    check(RAM32(thread + 0xF4) == 0x8006FAB0, "thread stack written by recompiled create-thread");
    check(RAM32(thread + 0x3C) == 0x12345678, "boot argument propagated into thread context");
    check(RAM32(0x8007B2CC) == thread, "thread inserted into native thread list");
    check(status_register == 0x34000001, "interrupt status restored");
    printf("  PASS %s: native thread context ID=1 priority=10 entry=80031EB4 stack=8006FAB0\n", tv_name);
    longjmp(stop, 1); /* Scheduling is the explicit end of this diagnostic. */
}

int main(int argc, char** argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: WetrixBootProbe.exe path/to/data.z64\n");
        return 2;
    }
    FILE* input = fopen(argv[1], "rb");
    if (!input) { perror("ROM"); return 2; }
    uint8_t* rom = malloc(0x800000);
    uint8_t* rdram = malloc(0x800000);
    if (!rom || !rdram) { fclose(input); free(rom); free(rdram); return 2; }
    size_t got = fread(rom, 1, 0x800000, input);
    int extra = fgetc(input);
    fclose(input);
    if (got != 0x800000 || extra != EOF || memcmp(rom, "\x80\x37\x12\x40", 4)) {
        fprintf(stderr, "Expected an 8 MiB big-endian ROM. Use the verified probe launcher.\n");
        free(rom); free(rdram); return 2;
    }
    printf("Wetrix N64 - native static recompilation boot diagnostic\n");
    printf("5 original ROM routines compiled to Windows x64 with N64Recomp.\n");
    printf("Diagnostic boundaries: OS initialization bypassed; stop before scheduling.\n\n");
    const uint32_t clocks[] = {49656530, 48681812, 48628316};
    const char* names[] = {"PAL input", "NTSC input", "MPAL input"};
    for (unsigned tv = 0; tv < 3 && !failed; ++tv) {
        memset(rdram, 0xA5, 0x800000);
        /* N64Recomp uses word-swapped RAM on a little-endian host. */
        for (unsigned i = 0x1000; i < 0x7CF80; ++i)
            rdram[((i - 0xC00) ^ 3)] = rom[i];
        memset(rdram + 0x7C380, 0xA5, 0x12C040 - 0x7C380);
        memset(rdram + 0x7C37C, 0xA5, 4);
        RAM32(0x80000300) = tv;
        init_count = start_count = 0;
        expected_clock = clocks[tv];
        tv_name = names[tv];
        status_register = 0x34000001;
        recomp_context ctx = {0};
        ctx.r4 = 0x12345678;
        int reason = setjmp(stop);
        if (reason == 0) {
            recomp_entrypoint(rdram, &ctx);
            check(0, "startup unexpectedly returned");
        }
    }
    free(rom); free(rdram);
    printf("\n%s: %u checks. No renderer, audio, scheduler, or gameplay is implemented.\n",
        failed ? "FAILED" : "PASSED", checks);
    return failed ? 1 : 0;
}
