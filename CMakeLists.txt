cmake_minimum_required(VERSION 3.24)
project(WetrixRecompiled VERSION 0.1.0 LANGUAGES C CXX)
set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(WETRIX_USE_PREGENERATED "Build from verified generated sources without a ROM" OFF)
find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/lib/N64Recomp/lib/fmt/CMakeLists.txt")
  message(FATAL_ERROR "Run git submodule update --init --recursive first")
endif()
add_subdirectory(lib/N64Recomp EXCLUDE_FROM_ALL)
add_custom_target(wetrix-tools DEPENDS N64RecompCLI RSPRecomp)
add_custom_target(verify-rom
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/project.py" verify
  VERBATIM)
add_custom_target(recompile
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/project.py" recompile --tool "$<TARGET_FILE:N64RecompCLI>"
  DEPENDS N64RecompCLI
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  VERBATIM)
# A playable executable requires the Wetrix-specific runtime integration.

set(BOOT_GEN "${CMAKE_CURRENT_SOURCE_DIR}/build/generated-boot")
if(NOT WETRIX_USE_PREGENERATED)
add_custom_command(
  OUTPUT "${BOOT_GEN}/funcs_0.c" "${BOOT_GEN}/funcs.h"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/project.py" verify
  COMMAND "$<TARGET_FILE:N64RecompCLI>" "${CMAKE_CURRENT_SOURCE_DIR}/config/boot-probe.toml"
  DEPENDS N64RecompCLI config/boot-probe.toml WetrixRecompSyms/boot-probe.syms.toml Assets/data.z64
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  VERBATIM)
add_executable(WetrixBootProbe src/boot_probe.c "${BOOT_GEN}/funcs_0.c")
target_include_directories(WetrixBootProbe PRIVATE lib/N64Recomp/include "${BOOT_GEN}" src)
if(MSVC)
  target_compile_definitions(WetrixBootProbe PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()
add_custom_target(run-boot-probe
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/project.py" verify
  COMMAND "$<TARGET_FILE:WetrixBootProbe>" "${CMAKE_CURRENT_SOURCE_DIR}/Assets/data.z64"
  DEPENDS WetrixBootProbe
  VERBATIM)

endif()

option(WETRIX_EXPERIMENTAL_RUNTIME "Build the experimental game runtime" ON)
if(WETRIX_EXPERIMENTAL_RUNTIME)
  execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/patch_rt64.py"
    COMMAND_ERROR_IS_FATAL ANY)
  set(RT64_STATIC ON CACHE BOOL "" FORCE)
  if(UNIX AND NOT APPLE)
    set(RT64_SDL_WINDOW_VULKAN ON CACHE BOOL "" FORCE)
    add_compile_definitions(PLUME_SDL_VULKAN_ENABLED RT64_SDL_WINDOW_VULKAN)
  endif()
  if(NOT WIN32)
    find_package(SDL2 REQUIRED)
  endif()
  add_subdirectory(lib/rt64 EXCLUDE_FROM_ALL)
  target_compile_definitions(rt64 PRIVATE WETRIX_RECOMP)
  if(MSVC)
    target_compile_options(rt64 PRIVATE /MP)
  endif()
  target_include_directories(rt64 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/lib/rt64/src")
  set(UM lib/N64ModernRuntime/ultramodern)
  add_library(wetrix_threads STATIC
    ${UM}/src/threads.cpp ${UM}/src/threadqueue.cpp
    ${UM}/src/scheduling.cpp ${UM}/src/mesgqueue.cpp)
  target_include_directories(wetrix_threads PUBLIC
    ${UM}/include lib/N64ModernRuntime/thirdparty
    lib/N64ModernRuntime/thirdparty/concurrentqueue)
  target_compile_definitions(wetrix_threads PUBLIC NOMINMAX _DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR)
  set(RUNTIME_GEN "${CMAKE_CURRENT_SOURCE_DIR}/build/generated-runtime")
  if(NOT WETRIX_USE_PREGENERATED)
  add_custom_command(OUTPUT "${RUNTIME_GEN}/funcs_0.c" "${RUNTIME_GEN}/unimplemented.cpp" "${RUNTIME_GEN}/dispatch.inl"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/project.py" verify
    COMMAND "$<TARGET_FILE:N64RecompCLI>" "${CMAKE_CURRENT_SOURCE_DIR}/config/runtime.toml"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/finalize_runtime.py"
    DEPENDS N64RecompCLI config/runtime.toml WetrixRecompSyms/runtime.syms.toml Assets/data.z64 tools/finalize_runtime.py src/runtime.cpp
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" VERBATIM)
  add_custom_command(OUTPUT "${RUNTIME_GEN}/aspMain.cpp"
    COMMAND "$<TARGET_FILE:RSPRecomp>" "${CMAKE_CURRENT_SOURCE_DIR}/config/audio.toml"
    DEPENDS RSPRecomp config/audio.toml Assets/data.z64
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" VERBATIM)
  endif()
  add_executable(WetrixRuntime src/runtime.cpp src/graphics.cpp src/input.cpp src/pak.cpp src/audio.cpp lib/N64ModernRuntime/librecomp/src/rsp.cpp "${RUNTIME_GEN}/aspMain.cpp" "${RUNTIME_GEN}/funcs_0.c" "${RUNTIME_GEN}/unimplemented.cpp")
  target_include_directories(WetrixRuntime PRIVATE lib/N64ModernRuntime/librecomp/include lib/N64ModernRuntime/librecomp/include/librecomp src lib/N64Recomp/include "${RUNTIME_GEN}")
  target_include_directories(WetrixRuntime PRIVATE lib/rt64/src lib/rt64/src/contrib lib/rt64/src/contrib/plume lib/rt64/src/contrib/hlslpp/include lib/rt64/src/contrib/imgui)
  target_link_libraries(WetrixRuntime PRIVATE wetrix_threads rt64)
  if(WIN32)
    target_include_directories(WetrixRuntime PRIVATE lib/rt64/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/include)
    target_link_directories(WetrixRuntime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/lib/rt64/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/lib/x64")
  else()
    target_include_directories(WetrixRuntime PRIVATE ${SDL2_INCLUDE_DIRS})
    target_link_libraries(WetrixRuntime PRIVATE ${SDL2_LIBRARIES})
  endif()
  target_compile_definitions(WetrixRuntime PRIVATE HLSL_CPU)
  target_sources(WetrixRuntime PRIVATE src/timing_audit.cpp src/menu_mesh.cpp)
  if(WIN32)
  add_custom_command(TARGET WetrixRuntime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_SOURCE_DIR}/lib/rt64/src/contrib/dxc/bin/x64/dxcompiler.dll" "$<TARGET_FILE_DIR:WetrixRuntime>"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_SOURCE_DIR}/lib/rt64/src/contrib/dxc/bin/x64/dxil.dll" "$<TARGET_FILE_DIR:WetrixRuntime>"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_SOURCE_DIR}/lib/rt64/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/lib/x64/SDL2.dll" "$<TARGET_FILE_DIR:WetrixRuntime>")
  endif()
  target_compile_definitions(WetrixRuntime PRIVATE _CRT_SECURE_NO_WARNINGS)
  include(cmake/frontend.cmake)
  if(MSVC)
    target_compile_options(wetrix_threads PRIVATE /EHs)
    target_compile_options(WetrixRuntime PRIVATE $<$<COMPILE_LANGUAGE:CXX>:/EHs>)
    target_compile_options(WetrixRuntime PRIVATE /Zi)
    target_link_options(WetrixRuntime PRIVATE /DEBUG)
  endif()
endif()

add_executable(WetrixPakTest EXCLUDE_FROM_ALL tests/pak_test.cpp src/pak.cpp)
add_executable(WetrixControllerPresenceTest EXCLUDE_FROM_ALL tests/controller_presence_test.cpp)
target_include_directories(WetrixControllerPresenceTest PRIVATE src lib/N64Recomp/include)
target_include_directories(WetrixPakTest PRIVATE src)
target_compile_definitions(WetrixPakTest PRIVATE NOMINMAX)

add_executable(WetrixTimingTest EXCLUDE_FROM_ALL tests/timing_test.cpp src/timing_audit.cpp)

add_executable(WetrixMenuMeshTest EXCLUDE_FROM_ALL tests/menu_mesh_test.cpp src/menu_mesh.cpp)
target_include_directories(WetrixMenuMeshTest PRIVATE src lib/N64Recomp/include build/generated-runtime)
target_include_directories(WetrixTimingTest PRIVATE src lib/N64Recomp/include build/generated-runtime)
