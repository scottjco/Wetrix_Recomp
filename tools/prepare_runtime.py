"""Generate an experimental call-graph map, cutting at identified OS services."""
import csv
import json
import re
import struct
from project import ROOT, verify

_, rom = verify()
rows = {int(r['address'], 16): r for r in csv.DictReader((ROOT / 'work/cpu-functions.csv').open())}
names = {
    0x80051240: 'osInitialize', 0x800503C0: 'osCreateThread',
    0x8005C100: 'osStartThread', 0x800591C0: 'osCreatePiManager',
    0x80060D40: 'osCreateViManager', 0x8005B000: 'osSetThreadPri',
    0x80059BC0: 'osRecvMesg', 0x8005AC40: 'osSendMesg',
    0x8004FBC0: 'osContStartReadData', 0x8004FE40: 'osContInit',
    0x80051080: 'osGetTime',
    0x80050F80: 'osEPiStartDma', 0x8004FA00: 'osCartRomInit',
    0x80050540: 'osDestroyThread',
    0x80051580: 'osInvalDCache',
    0x8005BFC0: 'osSpTaskYield', 0x8005C080: '__osSpGetStatus',
    0x8005B4C0: '__osSiRawStartDma',
    0x8004F500: 'osAiGetLength', 0x8004F6C0: 'osAiSetNextBuffer',
}
# Only unambiguous public OS signatures; ambiguous matches remain unnamed.
for m in json.loads((ROOT / 'work/reference-candidates.json').read_text()):
    if len(m['candidates']) == 1 and m['candidates'][0].startswith('os'):
        names.setdefault(int(m['address'], 16), m['candidates'][0])
# Scheduler helpers are game-side libultra code, not host service boundaries.
for addr in list(names):
    if names[addr].startswith('osSc') or names[addr] == 'osPfsChecker':
        del names[addr]
rows[0x80031DC0] = dict(rows[0x80031DAC], address='0x80031DC0', name='wetrix_main', length='0xF4')
rows[0x8004B940] = dict(rows[0x8004B938], address='0x8004B940', name='func_8004B940', length='0x13C')
rows[0x80000400] = {'address': '0x80000400', 'name': 'recomp_entrypoint', 'length': '0x3C',
    'functions called by this function': '[func_80031DC0]'}
# Shared tails: branch targets cross the automatic disassembler's boundary.
rows[0x8004FA00]['length'] = '0xF0'
rows[0x8004FA00]['functions called by this function'] += '[func_80051560]'
rows[0x8004C694]['length'] = '0x124'
rows[0x8004C694]['functions called by this function'] += '[func_8004DF04]'

def extend_flow(addr, row):
    """Follow local branches to include shared tails missed by linear splitting."""
    original_end = addr + int(row['length'], 16)
    frontier, entry_seen = [addr], set()
    falls_through = False
    while frontier:
        pc = frontier.pop()
        if pc == original_end:
            falls_through = True
            continue
        if pc in entry_seen or not addr <= pc < original_end:
            continue
        entry_seen.add(pc)
        w = struct.unpack_from('>I', rom, pc - 0x80000000 + 0xC00)[0]
        op = w >> 26
        if op == 2:
            frontier.append(0x80000000 | ((w & 0x3FFFFFF) << 2))
        elif op == 3:
            frontier.append(pc + 8)
        elif op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (op == 17 and (w >> 21) & 31 == 8):
            offset = struct.unpack('>h', struct.pack('>H', w & 0xFFFF))[0]
            frontier.extend([pc + 4 + offset * 4, pc + 8])
        elif not (op == 0 and (w & 63) in (8, 9, 13)):
            frontier.append(pc + 4)
    # Seed every decoded block in the original range, including switch cases
    # reached through indirect JR instructions.
    pending, visited, calls = list(range(addr, original_end, 4)), set(), set()
    if falls_through:
        pending.append(original_end)
    end = original_end
    while pending:
        pc = pending.pop()
        if pc in visited or pc < addr or pc >= max(original_end, addr + 0x10000):
            continue
        if not 0x800101C0 <= pc < 0x80063CFC:
            continue
        visited.add(pc)
        word = struct.unpack_from('>I', rom, pc - 0x80000000 + 0xC00)[0]
        op = word >> 26
        end = max(end, pc + 4)
        if op == 3:
            calls.add(0x80000000 | ((word & 0x3FFFFFF) << 2))
            if pc + 8 < original_end or pc >= original_end:
                pending.append(pc + 8)
            end = max(end, pc + 8)
        elif op == 2:
            target = 0x80000000 | ((word & 0x3FFFFFF) << 2)
            if target >= addr and target < original_end + 0x2000 and target not in names:
                pending.append(target)
            else:
                calls.add(target)
            end = max(end, pc + 8)
        elif op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (op == 17 and (word >> 21) & 31 == 8):
            offset = struct.unpack('>h', struct.pack('>H', word & 0xFFFF))[0]
            pending.append(pc + 4 + offset * 4)
            if pc + 8 < original_end or pc >= original_end:
                pending.append(pc + 8)
            end = max(end, pc + 8)
        elif op == 0 and (word & 63) in (8, 9, 13):
            end = max(end, pc + (4 if word & 63 == 13 else 8))
        else:
            if pc + 4 < original_end or pc >= original_end:
                pending.append(pc + 4)
    if end > original_end:
        row['length'] = hex(end - addr)
        for other, other_row in rows.items():
            if original_end <= other < end:
                row['referenced functions'] = row.get('referenced functions', '') + other_row.get('referenced functions', '')
    row['functions called by this function'] = row.get('functions called by this function', '') + ''.join(f'[func_{a:08X}]' for a in calls)

for addr, row in rows.items():
    if addr not in names and addr != 0x80000400:
        extend_flow(addr, row)
# Audio command callbacks stored in the ROM data table are not direct calls.
# Include exact disassembled function starts; interior jump-table labels remain local.
callback_words = struct.unpack('>80I', rom[0x7B800:0x7B940])
# Data segments contain additional game callback tables.
data_words = struct.unpack('>'+str((0x7CF80-0x648FC)//4)+'I', rom[0x648FC:0x7CF80]) + struct.unpack('>'+str((0xEA40-0x1000)//4)+'I', rom[0x1000:0xEA40])
todo = [0x80000400, 0x80031A80] + [a for a in callback_words+data_words if a in rows and a < 0x8004F000]
chosen = set()
missing = set()
while todo:
    addr = todo.pop()
    if addr in chosen:
        continue
    if addr not in rows:
        missing.add(addr)
        continue
    chosen.add(addr)
    if addr in names:
        continue
    row = rows[addr]
    for field in ['functions called by this function', 'non-jal function calls', 'referenced functions']:
        todo.extend(int(a, 16) for a in re.findall(r'(?:func_|T_)([0-9A-Fa-f]{8})', row.get(field, '')))
text = '''# Experimental reachable-code map, not a release-ready whole-game map.
[[section]]
name = ".main"
rom = 0x1000
vram = 0x80000400
size = 0x7BF80
functions = [
'''
for addr in sorted(chosen):
    row = rows[addr]
    text += f'  {{ name = "{names.get(addr, row["name"])}", vram = 0x{addr:08X}, size = {row["length"]} }},\n'
(ROOT / 'WetrixRecompSyms/runtime.syms.toml').write_text(text + ']\n')
(ROOT / 'work/runtime-names.json').write_text(json.dumps({f'{a:08X}': names.get(a, rows[a]['name']) for a in sorted(chosen)}, indent=2))
print(f'{len(chosen)} reachable functions; {len(chosen & names.keys())} OS boundaries; missing: {[hex(a) for a in sorted(missing)]}')
