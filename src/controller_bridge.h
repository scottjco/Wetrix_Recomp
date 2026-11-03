#pragma once
#include <array>
#include <cstdint>
#include "recomp.h"

inline bool wetrix_port_present(uint8_t mask,unsigned port) { return port<2 && (mask&(1U<<port)); }

inline void wetrix_write_controller_status(uint8_t* rdram,int64_t address,uint8_t mask) {
    for(unsigned port=0;port<4;++port) {
        const bool present=wetrix_port_present(mask,port);
        MEM_H(port*4,address)=present ? 0x0500 : 0;
        MEM_B(port*4+2,address)=present && port==0 ? 1 : 0;
        MEM_B(port*4+3,address)=present ? 0 : 8;
    }
}

inline void wetrix_write_controller_reads(uint8_t* rdram,int64_t address,uint8_t mask,
    const std::array<uint32_t,2>& inputs) {
    for(unsigned port=0;port<4;++port) {
        const bool present=wetrix_port_present(mask,port);
        const uint32_t input=present ? inputs[port] : 0;
        MEM_H(port*6,address)=input&0xFFFF;
        MEM_B(port*6+2,address)=(input>>16)&0xFF;
        MEM_B(port*6+3,address)=(input>>24)&0xFF;
        MEM_B(port*6+4,address)=present ? 0 : 8;
    }
}

inline void wetrix_write_native_port_presence(uint8_t* rdram,uint8_t mask) {
    wetrix_write_controller_status(rdram,int32_t(0x800876D8U),mask);
    MEM_W(0,int32_t(0x800A242CU))=mask&3;
    // Match func8001BA40's physical-controller cache exactly. This is not the
    // game's player count; Lesson CPU and two-player world state are separate.
    MEM_W(0,int32_t(0x800B0C14U))=(mask&3)==3 ? 2 : (mask&3)==1 ? 1 : 0;
}

inline void wetrix_clear_disconnected_ports(uint8_t* rdram,uint8_t lost_mask) {
    // These are the physical pad/current/previous/edge records maintained by
    // func8001BB70/8001BD14. Release held input on unplug even when the shorter
    // native polling loop no longer visits that port. CPU player input lives
    // separately at 800A2B68 and is deliberately left alone.
    for(unsigned p=0;p<2;++p) if(lost_mask&(1U<<p)) {
        for(int64_t base:{int64_t(int32_t(0x800B0BD0U)),int64_t(int32_t(0x800A2B40U)),
                         int64_t(int32_t(0x800A2768U)),int64_t(int32_t(0x800A24A8U))})
            for(int offset=0;offset<6;++offset) MEM_B(p*6+offset,base)=0;
        MEM_B(p*6+4,int64_t(int32_t(0x800B0BD0U)))=8;
        MEM_B(p*6+4,int64_t(int32_t(0x800A2B40U)))=8;
    }
}
