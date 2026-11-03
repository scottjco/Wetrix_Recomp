#pragma once
#include <string>
#include <vector>
#include <utility>
#include <cstdint>
std::vector<std::pair<std::string,std::string>> wetrix_device_options();
std::string wetrix_device_selection(int player);
void wetrix_device_select(int player, const std::string& key);
void wetrix_devices_refresh();
uint8_t wetrix_devices_present_mask();
