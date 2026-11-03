"""Check identity-free 0.1.1 defaults from source without loading user settings."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
menu=(ROOT/'src/menu.cpp').read_text()
graphics=(ROOT/'lib/RecompFrontend/recompui/src/config/ui_config_tab_graphics.cpp').read_text()
calls=dict(re.findall(r'graphics\.add_enum_option\("([^"]+)"(.*?)\);',menu,re.S))
assert re.search(r'graphics\.add_bool_option\("hd_textures".*?,true\);',menu,re.S)
assert 'graphics.update_option_hidden("hd_textures",!pack_available)' in menu
assert calls['fps_mode'].rstrip().endswith(',0U') and '{0U,"Hybrid"}' in calls['fps_mode']
assert calls['fps_target'].rstrip().endswith(',0U') and '{0U,"Display"}' in calls['fps_target']
assert calls['startup_monitor'].rstrip().endswith('monitor_options,0U')
assert 'monitor_options{{0U,"Automatic"}}' in menu
window=re.search(r'WindowMode wm_default\(\)\s*\{([^}]+)\}',graphics).group(1)
assert window.strip()=='return is_steam_deck() ? ultramodern::renderer::WindowMode::Fullscreen : ultramodern::renderer::WindowMode::Windowed;'
assert 'static const Version version{0,1,1,""}' in menu
assert 'VERSION 0.1.1' in (ROOT/'CMakeLists.txt').read_text()
assert '#include <Windows.h>' not in menu and 'PostQuitMessage' not in menu
assert 'selected{"auto", "none"}' in (ROOT/'src/wetrix_devices.cpp').read_text()
controller_calls=re.findall(r'set_default_mapping_for_controller\(G::(\w+),',menu)
assert len(controller_calls)==len(set(controller_calls))==25
report={'version':'0.1.1','fresh_defaults':{'hd_textures':True,'hd_option_hidden_without_pack':True,
    'fps_mode':'Hybrid','frame_rate':'Display','window_mode':{'desktop':'Windowed','Steam Deck':'Fullscreen'},'startup_monitor':'Automatic',
    'controller_actions':25,'player_2_assignment':'Not assigned'},
    'saved_preferences':'Loaded through normal configuration; no user settings copied into distribution defaults.',
    'verification':'Source checks only; no build, launch, save-file or user-configuration changes.'}
destination=ROOT/'work/release-defaults-audit.json'
destination.write_text(json.dumps(report,indent=2)+'\n')
print('PASS: identity-free 0.1.1 release defaults, all requested display/FPS/HD defaults, 25 controller actions, P2 None, portable menu quit')
