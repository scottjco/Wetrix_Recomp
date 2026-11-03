"""Read-only check: shipped defaults equal a backed-up active controller profile.

Uses the bundled SDL enum values and the real InputField axis encoding. Does
not build, launch, save settings, or copy physical controller identities.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--profile',default='controller_sp')
    args=parser.parse_args()
    saved=json.loads((args.snapshot/'controls.json').read_text())
    active=next(p for p in saved['profiles'] if p['key']==args.profile)
    header=(ROOT/'lib/rt64/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/include/SDL_gamecontroller.h').read_text()
    enums={}
    for suffix in ('Axis','Button'):
        body=re.search(r'typedef enum\s*\{([^}]+)\}\s*SDL_GameController'+suffix+r';',header).group(1)
        value=-1
        for token in re.sub(r'/\*.*?\*/','',body,flags=re.S).split(','):
            match=re.search(r'(SDL_CONTROLLER_\w+)(?:\s*=\s*(-?\d+))?',token)
            if match:
                value=int(match[2]) if match[2] is not None else value+1
                enums[match[1]]=value
    source=(ROOT/'src/menu.cpp').read_text()
    definitions={}
    for action,fields in re.findall(r'set_default_mapping_for_controller\(G::(\w+),\{(.*?)\}\);',source):
        assert action not in definitions, f'Duplicate setter: {action}'
        decoded=[]
        for kind,name,positive in re.findall(r'F::controller_(digital|analog)\((SDL_CONTROLLER_\w+)(?:,(true|false))?\)',fields):
            value=enums[name]
            if kind=='analog': value=(value+1)*(-1 if positive=='false' else 1)
            decoded.append({'input_type':3 if kind=='digital' else 4,'input_id':value})
        assert len(decoded)<=2
        definitions[action]=decoded+[{'input_type':0,'input_id':0}]*(2-len(decoded))
    assert set(definitions)==set(active['mappings']), 'Missing or extra default actions'
    for action,expected in active['mappings'].items():
        assert definitions[action]==expected, f'Binding mismatch: {action}'
    expected_keyboard={'A':'F::keyboard(SDL_SCANCODE_SPACE)','B':'F::keyboard(SDL_SCANCODE_E)',
        'START':'F::keyboard(SDL_SCANCODE_RETURN)','DPAD_UP':'F::keyboard(SDL_SCANCODE_W)',
        'DPAD_DOWN':'F::keyboard(SDL_SCANCODE_S)','DPAD_LEFT':'F::keyboard(SDL_SCANCODE_A)',
        'DPAD_RIGHT':'F::keyboard(SDL_SCANCODE_D)','X_AXIS_POS':'','X_AXIS_NEG':'',
        'Y_AXIS_POS':'','Y_AXIS_NEG':'','Z':'F::keyboard(SDL_SCANCODE_Q)','R':'F::keyboard(SDL_SCANCODE_R)'}
    keyboard=dict(re.findall(r'set_default_mapping_for_keyboard\(G::(\w+),\{(.*?)\}\);',source))
    assert keyboard==expected_keyboard, 'Keyboard defaults changed'
    for filename in ('controls.json','general.json'):
        assert (ROOT/'config/user'/filename).read_bytes()==(args.snapshot/filename).read_bytes(), f'Existing {filename} was modified'
    assert source.rindex('set_default_mapping_for_controller')<source.index('recompui::config::create_controls_tab()')<source.index('recompui::config::finalize()')
    assert 'selected{"auto", "none"}' in (ROOT/'src/wetrix_devices.cpp').read_text(), 'P2 default assignment changed'
    general=json.loads((args.snapshot/'general.json').read_text())
    assert general=={'background_input_mode':'On','debug_mode':False,'joystick_deadzone':5}
    result={'active_profile':args.profile,'controller_actions_matched':len(definitions),'keyboard_defaults_preserved':len(keyboard),
        'existing_settings_unchanged':True,'p2_default':'none','general_defaults_already_match':general,
        'controller_defaults':definitions,'controls_snapshot_sha256':hashlib.sha256((args.snapshot/'controls.json').read_bytes()).hexdigest(),
        'activation_trace':['wetrix_input_poll -> profiles::get_n64_input(0)','get_n64_input -> players_input_profile_indices[0].first',
            'players::assign_device(0) -> get_sp_controller_profile_index()','initialize_input_bindings -> controller_sp for player 0'],
        'scope':'Only default mapping setters; saved profiles are loaded afterwards and not reset.'}
    (args.snapshot/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS: {len(definitions)} active controller actions match; {len(keyboard)} keyboard defaults preserved; saved controls/general unchanged; P2 None preserved")

if __name__=='__main__':main()
