#include "menu_mesh.h"
#include "runtime.h"
#include <vector>
#include <fstream>
#include <iterator>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <algorithm>

static bool available=true,enabled=false;
bool wetrix_menu_hd_textures_available() { return available; }
bool wetrix_menu_hd_textures_enabled() { return available&&enabled; }
static void check(bool condition,const char* message) { if(!condition) { printf("FAIL: %s\n",message); std::exit(1); } }
static uint16_t u16(const std::vector<uint8_t>& data,size_t at) { return uint16_t(data[at])<<8|data[at+1]; }
static WetrixRimVertex vertex(const std::vector<uint8_t>& rom,size_t at) {
    WetrixRimVertex v{};
    v.x=int16_t(u16(rom,at));v.y=int16_t(u16(rom,at+2));v.z=int16_t(u16(rom,at+4));v.flag=u16(rom,at+6);
    v.s=int16_t(u16(rom,at+8));v.t=int16_t(u16(rom,at+10));
    std::copy_n(rom.begin()+at+12,4,v.normalAlpha.begin());return v;
}
int main(int argc,char** argv) {
    check(argc==2,"Supply exact native ROM fixture");
    std::ifstream file(argv[1],std::ios::binary);std::vector<uint8_t> rom((std::istreambuf_iterator<char>(file)),{});
    check(rom.size()==0x800000,"Native ROM size");
    for(unsigned mesh=0;mesh<2;++mesh) {
        std::array<WetrixRimVertex,70> native;
        for(unsigned i=0;i<70;++i)native[i]=vertex(rom,0xEEC00+(mesh?0x7A8:0)+i*16);
        constexpr uint32_t address=0x80300000;
        const auto art=wetrix_build_smooth_rim(native,address);
        check(art.vertices.size()==258&&art.commands.size()==770,"128 segments, seam pair and bounded list size");
        check(!memcmp(&art.vertices[0],&art.vertices[256],32),"Seam vertices identical");
        for(unsigned ring=0;ring<2;++ring) {
            double cx=0,cz=0,radius=0;
            for(unsigned i=0;i<35;++i){cx+=native[i*2+ring].x;cz+=native[i*2+ring].z;}cx/=35;cz/=35;
            for(unsigned i=0;i<35;++i)radius+=std::hypot(native[i*2+ring].x-cx,native[i*2+ring].z-cz);radius/=35;
            for(unsigned i=0;i<128;++i) {
                const auto& v=art.vertices[i*2+ring];
                check(std::abs(std::hypot(v.x-cx,v.z-cz)-radius)<0.8,"Native radius preserved on true circle");
                check(v.y==native[ring].y&&v.normalAlpha[3]==255,"Native Y profile and opacity");
                const double normalLength=std::sqrt(double(int8_t(v.normalAlpha[0]))*int8_t(v.normalAlpha[0])+double(int8_t(v.normalAlpha[1]))*int8_t(v.normalAlpha[1])+double(int8_t(v.normalAlpha[2]))*int8_t(v.normalAlpha[2]));
                check(normalLength>115&&normalLength<140,"Smooth signed normals retain native magnitude");
            }
        }
        for(unsigned segment=0;segment<128;++segment) {
            const auto* c=art.commands.data()+segment*6;
            check((c[0]>>24)==4&&((c[0]>>10)&63)==4&&((c[0]>>17)&127)==0,"F3DEX load-four-vertices encoding");
            check(c[1]==address+segment*32&&c[1]+64<=address+WetrixRimVertexBytes,"Every vertex DMA in allocated vertex pool");
            const unsigned expected[2][3]={{0,3,2},{0,1,3}};
            for(unsigned t=0;t<2;++t){uint32_t w=c[3+t*2];check(c[2+t*2]==0xBF000000,"Native TRI1 opcode");check(((w>>17)&127)==expected[t][0]&&((w>>9)&127)==expected[t][1]&&((w>>1)&127)==expected[t][2],"Native winding and all indices inside four-vertex cache");}
        }
        check(art.commands[768]==0xB8000000&&art.commands[769]==0,"Child list terminates inside reserved storage");
    }
    std::vector<uint8_t> ram(0x800000,0xA5);uint8_t* rdram=ram.data();recomp_context ctx{};
    constexpr uint32_t bank=0x80300000,heapNode=0x80200000,dl=0x80010000;
    auto set=[&](uint32_t at,uint32_t value){MEM_W(0,int32_t(at))=int32_t(value);};
    auto get=[&](uint32_t at){return uint32_t(MEM_W(0,int32_t(at)));};
    auto copy=[&](uint32_t at,size_t source,size_t size){for(size_t i=0;i<size;++i)MEM_B(int(i),int32_t(at))=int8_t(rom[source+i]);};
    check(((WetrixMenuBankBytes+WetrixMenuMeshReserve+15)&~15U)==WetrixMenuBankBytes+WetrixMenuMeshReserve,"Native allocator aligns payload to16, no inline header");
    set(0x800A2C38,heapNode);set(heapNode,1);set(heapNode+8,WetrixMenuBankBytes+WetrixMenuMeshReserve);set(heapNode+12,bank);
    copy(bank,0xEEC00,WetrixMenuBankBytes);copy(0x80069BA8,0x6A7A8,0x108);copy(0x80069CB0,0x6A8B0,0x108);
    const auto before=ram;
    wetrix_menu_mesh_begin_bank();ctx.r4=WetrixMenuBankBytes;wetrix_menu_mesh_allocate(rdram,&ctx);
    check(ctx.r4==WetrixMenuBankBytes+WetrixMenuMeshReserve,"HD OFF startup reserves when pack available");
    ctx.r2=bank;wetrix_menu_mesh_allocation_result(rdram,&ctx);set(0x800876C4,bank);wetrix_menu_mesh_bank_ready(rdram);
    for(uint32_t i=0;i<WetrixMenuBankBytes;++i)check(ram[(bank&0x7fffff)+i]==before[(bank&0x7fffff)+i],"Original bank bytes including reflection textures unchanged");
    const uint32_t end=(bank&0x7fffff)+WetrixMenuBankBytes+WetrixMenuMeshReserve;
    for(unsigned i=0;i<64;++i)check(ram[end+i]==0xA5,"Reserved-bank end canary");
    check(!memcmp(ram.data()+0x69BA8,before.data()+0x69BA8,0x210),"Both native object descriptors and animation matrices untouched");
    set(0x800A1DAC,dl);set(0x8006D59C,1);ctx.r4=0x80069BA8;
    check(!wetrix_draw_smooth_menu_mesh(rdram,&ctx)&&get(0x800A1DAC)==dl,"HD OFF uses untouched native function");
    enabled=true;check(wetrix_draw_smooth_menu_mesh(rdram,&ctx)==1,"Live HD ON uses prepared mesh");
    check(get(0x800A1DAC)==dl+24&&get(dl)==0x01020040&&get(dl+4)==0x80069BA8+0x50,"Frame DL only24 bytes, original matrix buffer1");
    check(get(dl+8)==0xFA000000&&get(dl+12)==0xC8FFF0C0,"Original tint and material alphaC0");
    check(get(dl+16)==0x06000000&&get(dl+20)==bank+WetrixMenuBankBytes+WetrixRimVertexBytes,"Bounded native child-list call");
    check(get(dl+24)==0xA5A5A5A5,"Main frame DL canary beyond24 bytes");
    ctx.r4=0x80069CB0;set(0x800A1DAC,dl);check(wetrix_draw_smooth_menu_mesh(rdram,&ctx)==1,"Second exact rim uses smooth dispatch");
    ctx.r4=0x80069BA8;enabled=false;check(!wetrix_draw_smooth_menu_mesh(rdram,&ctx),"Live OFF immediately restores native35 segment path");
    available=false;wetrix_menu_mesh_begin_bank();ctx.r4=WetrixMenuBankBytes;wetrix_menu_mesh_allocate(rdram,&ctx);check(ctx.r4==WetrixMenuBankBytes,"No pack does not reserve optional heap");
    enabled=true;ctx.r4=0x80069BA8;check(!wetrix_draw_smooth_menu_mesh(rdram,&ctx),"No pack native fallback");
    available=true;set(heapNode+8,WetrixMenuBankBytes);wetrix_menu_mesh_begin_bank();ctx.r4=WetrixMenuBankBytes;wetrix_menu_mesh_allocate(rdram,&ctx);check(ctx.r4==WetrixMenuBankBytes,"Insufficient expanded space leaves successful native allocation request unchanged");
    ctx.r4=0x80069BA8;check(!wetrix_draw_smooth_menu_mesh(rdram,&ctx),"Insufficient heap native fallback");
    printf("PASS: production128-segment geometry, normals, winding, GBI bounds, heap/DL canaries and HD toggle/fallback; reserve%u bytes\n",WetrixMenuMeshReserve);
}
