#ifndef WETRIX_RUNTIME_H
#define WETRIX_RUNTIME_H
#include "recomp.h"
#include "runtime_services.h"
#ifdef __cplusplus
extern "C" {
#endif
void wetrix_background_marker(uint8_t* rdram, unsigned layer);
void wetrix_push_background_marker(uint8_t* rdram, unsigned layer);
void wetrix_pop_background_marker(uint8_t* rdram);
void wetrix_audit_cpu_counter(unsigned player_index);
void wetrix_menu_mesh_begin_bank(void);
void wetrix_menu_mesh_allocate(uint8_t* rdram, recomp_context* ctx);
void wetrix_menu_mesh_allocation_result(uint8_t* rdram, recomp_context* ctx);
void wetrix_menu_mesh_bank_ready(uint8_t* rdram);
int wetrix_draw_smooth_menu_mesh(uint8_t* rdram, recomp_context* ctx);
void wetrix_yield(uint8_t* rdram);
void wetrix_sync_controller_presence(uint8_t* rdram);
void wetrix_timing_audit(uint8_t* rdram, unsigned stage);
int wetrix_control_frame(uint8_t* rdram, recomp_context* ctx);
int wetrix_control_extra(void);
int wetrix_control_rate(void);
float wetrix_rainbow_visual_step(void);
int wetrix_intro_skip_requested(void);
void wetrix_capture_sprite(uint8_t* rdram, recomp_context* ctx);
void wetrix_set_fps(unsigned mode, unsigned target);
unsigned wetrix_fps_mode(void);
unsigned wetrix_fps_target(void);
void wetrix_piece_substep(uint8_t* rdram, unsigned stage);
void wetrix_prepare_rotation(uint8_t* rdram, recomp_context* ctx);
int wetrix_precision_active(uint8_t* rdram);
void wetrix_analog_input(uint8_t* rdram, recomp_context* ctx);
void wetrix_unimplemented(const char* name);
#ifdef __cplusplus
}
#endif
#endif
