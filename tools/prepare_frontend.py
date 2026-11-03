"""Build the shared frontend's in-game UI without its launcher or mod installer."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / 'lib/RecompFrontend/recompui/src/base/ui_state.cpp').read_text()
source = source.replace('        recompui::init_launcher_menu();', '')
source = source.replace('    if (!recompui::is_any_context_shown() && !ultramodern::is_game_started()) {\n        recompui::show_context(recompui::get_launcher_context_id(), "");\n    }', '')
source = source.replace('        if (recompui::is_context_shown(recompui::get_launcher_context_id())) {\n            recompui::update_launcher_menu();\n        }', '')
source = source[:source.index('void recompui::drop_files(')]
source = source.replace('    ui_state->create_menus();', '    ui_state->create_menus();\n    puts("Wetrix settings UI initialized");')
source = 'extern void wetrix_graphics_frame_presented();\n' + source
source = source.replace('    apply_background_input_mode();', '    wetrix_graphics_frame_presented();\n    apply_background_input_mode();')
output = root / 'build/generated-runtime/ui_state.cpp'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(source)
file_source = (root / 'lib/RecompFrontend/recompui/src/util/file.cpp').read_text()
file_source = file_source.replace('        return "";', '        char* base = SDL_GetBasePath();\n        std::filesystem::path path = base ? base : "";\n        SDL_free(base);\n        return path;')
(output.parent / 'ui_file.cpp').write_text(file_source)
