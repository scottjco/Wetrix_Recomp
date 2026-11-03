#pragma once
#include "ultramodern/config.hpp"
void wetrix_menu_init(void* native_window);
float wetrix_menu_volume();
bool wetrix_menu_hd_textures_available();
bool wetrix_menu_hd_textures_enabled();
bool wetrix_menu_take_graphics(ultramodern::renderer::GraphicsConfig& config);
