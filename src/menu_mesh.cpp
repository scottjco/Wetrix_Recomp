#include "menu_mesh.h"
#include "runtime.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

// These getters read atomic settings. Model fallback must follow the same
// installed-pack/HD option as textures, without touching native descriptors.
bool wetrix_menu_hd_textures_available();
bool wetrix_menu_hd_textures_enabled();

namespace {
constexpr double Pi = 3.14159265358979323846;
constexpr uint32_t BankPointer = 0x800876C4;
constexpr uint32_t FirstObject = 0x80069BA8, SecondObject = 0x80069CB0;
constexpr uint32_t DlPointer = 0x800A1DAC;
thread_local bool reserveNext = false, expandedAllocation = false;
thread_local uint32_t allocatedBank = 0, readyBank = 0;
bool valid(uint32_t address, uint32_t bytes) {
    return address >= 0x80000400U && bytes <= 0x800000U && address <= 0x80800000U - bytes;
}
uint32_t word(uint8_t* rdram, uint32_t address) { return uint32_t(MEM_W(0, int32_t(address))); }
void put(uint8_t* rdram, uint32_t address, uint32_t value) { MEM_W(0, int32_t(address)) = int32_t(value); }
bool freeBlockFits(uint8_t* rdram, uint32_t bytes) {
    uint32_t node = word(rdram, 0x800A2C38);
    for (unsigned n=0; n<4096 && valid(node, 16); ++n) {
        if (word(rdram, node+8) >= bytes) return true;
        node = word(rdram, node);
        if (node == 1) break;
    }
    return false;
}
WetrixRimVertex readVertex(uint8_t* rdram, uint32_t base) {
    WetrixRimVertex v{};
    v.x=MEM_H(0,int32_t(base)); v.y=MEM_H(2,int32_t(base)); v.z=MEM_H(4,int32_t(base));
    v.flag=uint16_t(MEM_H(6,int32_t(base))); v.s=MEM_H(8,int32_t(base)); v.t=MEM_H(10,int32_t(base));
    for (unsigned c=0;c<4;++c) v.normalAlpha[c]=MEM_BU(int(c+12),int32_t(base));
    return v;
}
void writeVertex(uint8_t* rdram, uint32_t base, const WetrixRimVertex& v) {
    MEM_H(0,int32_t(base))=v.x; MEM_H(2,int32_t(base))=v.y; MEM_H(4,int32_t(base))=v.z;
    MEM_H(6,int32_t(base))=int16_t(v.flag); MEM_H(8,int32_t(base))=v.s; MEM_H(10,int32_t(base))=v.t;
    for (unsigned c=0;c<4;++c) MEM_B(int(c+12),int32_t(base))=int8_t(v.normalAlpha[c]);
}
}

WetrixSmoothRim wetrix_build_smooth_rim(const std::array<WetrixRimVertex,70>& native, uint32_t address) {
    WetrixSmoothRim out{};
    for (unsigned ring=0;ring<2;++ring) {
        double cx=0,cz=0,radius=0;
        for (unsigned i=0;i<35;++i) { cx+=native[i*2+ring].x; cz+=native[i*2+ring].z; }
        cx/=35; cz/=35;
        for (unsigned i=0;i<35;++i) radius+=std::hypot(native[i*2+ring].x-cx,native[i*2+ring].z-cz);
        radius/=35;
        const double phase=std::atan2(native[ring].x-cx,-(native[ring].z-cz));
        for (unsigned i=0;i<WetrixRimSegments;++i) {
            const double sample=double(i)*35/WetrixRimSegments;
            const unsigned left=unsigned(sample),right=(left+1)%35;
            const double f=sample-left;
            const auto& a=native[left*2+ring]; const auto& b=native[right*2+ring];
            auto mix=[&](double u,double v) { return u+(v-u)*f; };
            auto& v=out.vertices[i*2+ring]; v=a;
            const double angle=phase+2*Pi*i/WetrixRimSegments;
            v.x=int16_t(std::lround(cx+radius*std::sin(angle)));
            v.z=int16_t(std::lround(cz-radius*std::cos(angle)));
            v.y=int16_t(std::lround(mix(a.y,b.y)));
            v.s=int16_t(std::lround(mix(a.s,b.s))); v.t=int16_t(std::lround(mix(a.t,b.t)));
            double normal[3],length=0,magnitude=0;
            for(unsigned c=0;c<3;++c) { normal[c]=mix(int8_t(a.normalAlpha[c]),int8_t(b.normalAlpha[c])); length+=normal[c]*normal[c]; magnitude+=double(int8_t(a.normalAlpha[c]))*int8_t(a.normalAlpha[c]); }
            const double scale=length>0?std::sqrt(magnitude/length):1;
            for(unsigned c=0;c<3;++c) v.normalAlpha[c]=uint8_t(int8_t(std::clamp(std::lround(normal[c]*scale),-127L,127L)));
            v.normalAlpha[3]=uint8_t(std::lround(mix(a.normalAlpha[3],b.normalAlpha[3])));
        }
        out.vertices[WetrixRimSegments*2+ring]=out.vertices[ring];
    }
    unsigned w=0;
    for(unsigned i=0;i<WetrixRimSegments;++i) {
        // Same F3DEX encodings as native268AC, proven against RT64's decoder:
        // count=p0(10,6), v0=p0(17,7); TRI1 indices=p1(17/9/1,7).
        out.commands[w++]=0x0400103F; out.commands[w++]=address+i*32;
        out.commands[w++]=0xBF000000; out.commands[w++]=(3U<<9)|(2U<<1); // 0,3,2
        out.commands[w++]=0xBF000000; out.commands[w++]=(1U<<9)|(3U<<1); // 0,1,3
    }
    out.commands[w++]=0xB8000000; out.commands[w++]=0;
    return out;
}

extern "C" void wetrix_menu_mesh_begin_bank(void) {
    reserveNext=wetrix_menu_hd_textures_available();
    expandedAllocation=false; allocatedBank=readyBank=0;
}
extern "C" void wetrix_menu_mesh_allocate(uint8_t* rdram,recomp_context* ctx) {
    if (!reserveNext) return;
    reserveNext=false;
    const uint32_t requested=uint32_t(ctx->r4);
    if (requested!=WetrixMenuBankBytes) return;
    if (!freeBlockFits(rdram,requested+WetrixMenuMeshReserve)) {
        static bool reported=false;
        if (!reported) { puts("Menu platter: native 35-segment fallback; expanded bank does not fit native heap"); fflush(stdout); reported=true; }
        return;
    }
    ctx->r4=requested+WetrixMenuMeshReserve;
    expandedAllocation=true;
}
extern "C" void wetrix_menu_mesh_allocation_result(uint8_t*,recomp_context* ctx) {
    if (expandedAllocation && allocatedBank==0) allocatedBank=uint32_t(ctx->r2);
}
extern "C" void wetrix_menu_mesh_bank_ready(uint8_t* rdram) {
    const uint32_t bank=word(rdram,BankPointer);
    if (!expandedAllocation || bank!=allocatedBank || !valid(bank,WetrixMenuBankBytes+WetrixMenuMeshReserve)) return;
    for(unsigned mesh=0;mesh<2;++mesh) {
        std::array<WetrixRimVertex,70> source;
        const uint32_t nativeAddress=bank+(mesh?0x7A8:0);
        for(unsigned i=0;i<70;++i) source[i]=readVertex(rdram,nativeAddress+i*16);
        const uint32_t storage=bank+WetrixMenuBankBytes+mesh*WetrixRimStorage;
        const auto smooth=wetrix_build_smooth_rim(source,storage);
        for(unsigned i=0;i<smooth.vertices.size();++i) writeVertex(rdram,storage+i*16,smooth.vertices[i]);
        for(unsigned i=0;i<smooth.commands.size();++i) put(rdram,storage+WetrixRimVertexBytes+i*4,smooth.commands[i]);
    }
    readyBank=bank;
    printf("Menu platter: 128 segments per rim; native heap reserve %u bytes; frame DL 24 bytes/object (native at least1136)\n",WetrixMenuMeshReserve);
    fflush(stdout);
}
extern "C" int wetrix_draw_smooth_menu_mesh(uint8_t* rdram,recomp_context* ctx) {
    const uint32_t object=uint32_t(ctx->r4),bank=word(rdram,BankPointer);
    if (!wetrix_menu_hd_textures_enabled() || readyBank==0 || bank!=readyBank ||
        (object!=FirstObject && object!=SecondObject)) return 0;
    const unsigned mesh=object==SecondObject?1:0;
    if (word(rdram,object+0xBC)!=(mesh?0x040007A8U:0x04000000U) ||
        word(rdram,object+0xC0)!=(mesh?0x04000C08U:0x04000460U) || word(rdram,object+0xCC)!=70) return 0;
    const uint32_t dl=word(rdram,DlPointer),buffer=word(rdram,0x8006D59C);
    if (!valid(dl,24) || buffer>1) return 0;
    const uint32_t tint=uint32_t(MEM_BU(0xD0,int32_t(object)))<<24 |
        uint32_t(MEM_BU(0xD1,int32_t(object)))<<16 | uint32_t(MEM_BU(0xD2,int32_t(object)))<<8 | 0xC0;
    put(rdram,dl,0x01020040); put(rdram,dl+4,object+0x10+buffer*64);
    put(rdram,dl+8,0xFA000000); put(rdram,dl+12,tint);
    put(rdram,dl+16,0x06000000);
    put(rdram,dl+20,bank+WetrixMenuBankBytes+mesh*WetrixRimStorage+WetrixRimVertexBytes);
    put(rdram,DlPointer,dl+24);
    static const bool audit=std::getenv("WETRIX_MESH_AUDIT")!=nullptr;
    static thread_local unsigned seen=0;
    if(audit && (seen&(1U<<mesh))==0) {
        seen|=1U<<mesh;
        printf("Menu platter GPU submission: rim %u, 128 segments, owned child DL %08X\n",
            mesh,bank+WetrixMenuBankBytes+mesh*WetrixRimStorage+WetrixRimVertexBytes);
        fflush(stdout);
    }
    return 1;
}
