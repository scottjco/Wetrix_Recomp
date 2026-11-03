"""Generate dispatch entries and fail-fast adapters for unimplemented services."""
import tomllib
import re
from project import ROOT

generated = ROOT / 'build/generated-runtime'
header = (generated / 'funcs.h').read_text()
declared = set(re.findall(r'void (\w+)\(', header))
services = set(re.findall(r'\b(\w+_recomp)\(rdram', (generated / 'funcs_0.c').read_text()))
declared |= services
(generated / 'runtime_services.h').write_text('''#ifdef __cplusplus
extern "C" {
#endif
''' + ''.join(f'void {n}(uint8_t*, recomp_context*);\n' for n in sorted(services)) + '''#ifdef __cplusplus
}
#endif
''')
symbols = tomllib.loads((ROOT / 'WetrixRecompSyms/runtime.syms.toml').read_text())
names = {f"{f['vram']:08X}": f['name'] for sec in symbols['section'] for f in sec['functions']}
entries = []
for addr, name in names.items():
    target = name + '_recomp' if name + '_recomp' in declared else name
    if target in declared:
        entries.append((int(addr, 16), target))
for name in declared:
    if name.startswith('static_0_'):
        entries.append((int(name.rsplit('_', 1)[1], 16), name))
(generated / 'dispatch.inl').write_text('\n'.join(f'{{0x{a:08X}u, {n}}},' for a,n in entries))
implemented = set(re.findall(r'void (\w+_recomp)\(', (ROOT / 'src/runtime.cpp').read_text()))
missing = sorted(n for n in declared if n.endswith('_recomp') and n not in implemented)
(generated / 'unimplemented.cpp').write_text('#include "runtime.h"\n' + ''.join(
    f'extern "C" void {n}(uint8_t*, recomp_context*) {{ wetrix_unimplemented("{n}"); }}\n' for n in missing))
print(f'Dispatch entries: {len(entries)}; explicit unsupported services: {len(missing)}')
