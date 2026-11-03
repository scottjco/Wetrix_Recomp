#include "pak.h"
#ifdef _WIN32
#include <Windows.h>
#endif
#include <algorithm>
#include <fstream>
#include <stdexcept>
// Controller Pak on-disk layout: four ID copies, mirrored allocation tables,
// sixteen directory entries, and 123 data pages. See docs/CONTROLS-AND-PAK.md.
WetrixPak::WetrixPak(const std::filesystem::path& filename) : path(filename) {
    if (std::filesystem::exists(path)) {
        if(std::filesystem::file_size(path)!=bytes.size()) throw std::runtime_error("Controller pak must be exactly 32768 bytes; existing file preserved");
        std::ifstream f(path,std::ios::binary);
        if(!f.read(reinterpret_cast<char*>(bytes.data()),bytes.size())) throw std::runtime_error("Unable to read controller pak");
        return;
    }
    std::array<uint8_t,32> id{};
    // Stable serial, one memory bank, version zero, device bit 0 set.
    id[0]=0x57; id[1]=0x45; id[2]=0x54; id[3]=0x52;
    id[25]=1; id[26]=1;
    uint16_t sum=0;
    for(int i=0;i<28;i+=2) sum+=uint16_t(id[i]<<8)|id[i+1];
    uint16_t inverse=uint16_t(0xFFF2-sum);
    id[28]=sum>>8; id[29]=sum; id[30]=inverse>>8; id[31]=inverse;
    for(int offset : {32,96,128,192}) std::copy(id.begin(),id.end(),bytes.begin()+offset);
    for(int page=5;page<128;++page) bytes[256+page*2+1]=3;
    bytes[257]=uint8_t(123*3);
    std::copy_n(bytes.begin()+256,256,bytes.begin()+512);
    store();
}
void WetrixPak::store() {
    std::filesystem::create_directories(path.parent_path());
    auto temporary=path; temporary+=".tmp";
    {
        std::ofstream f(temporary,std::ios::binary|std::ios::trunc);
        f.write(reinterpret_cast<const char*>(bytes.data()),bytes.size()); f.flush();
        if(!f) throw std::runtime_error("Unable to write controller pak");
    }
#ifdef _WIN32
    if(!MoveFileExW(temporary.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
        throw std::runtime_error("Unable to commit controller pak");
#else
    std::filesystem::rename(temporary,path);
#endif
}
static uint8_t data_crc(const uint8_t* data) {
    unsigned remainder=0;
    // Polynomial x^8+x^7+x^2+1, with eight trailing zero bits.
    for(int bit=0;bit<264;++bit) {
        remainder=(remainder<<1) | (bit<256 ? ((data[bit/8]>>(7-bit%8))&1) : 0);
        if(remainder&256) remainder^=0x185;
    }
    return uint8_t(remainder);
}
void WetrixPak::command(uint8_t* pif, uint32_t input, uint32_t input2, uint8_t present_mask) {
    unsigned cursor=0,channel=0;
    while(cursor<63) {
        uint8_t tx=pif[cursor];
        if(tx==0xFE) break;
        if(tx==0xFF || tx==0xFD) { ++cursor; continue; }
        if(tx==0) { ++channel; ++cursor; continue; }
        if(cursor+2>=63) break;
        unsigned rx=pif[cursor+1]&63;
        tx &= 63;
        if(!tx || cursor+2+tx+rx>63) break;
        uint8_t* request=pif+cursor+2;
        uint8_t* reply=request+tx;
        pif[cursor+1] &= 63;
        if(channel>1 || !(present_mask&(1U<<channel))) {
            std::fill_n(reply,rx,0); pif[cursor+1]|=0x80;
        }
        else if(channel==1) {
            if((request[0]==0 || request[0]==0xFF) && rx>=3) { reply[0]=5; reply[1]=0; reply[2]=0; }
            else if(request[0]==1 && rx>=4) {
                reply[0]=(input2>>8)&255; reply[1]=input2&255;
                reply[2]=(input2>>16)&255; reply[3]=(input2>>24)&255;
            } else pif[cursor+1]|=0x80;
        }
        else if((request[0]==0 || request[0]==0xFF) && rx>=3) {
            reply[0]=5;reply[1]=0;reply[2]=1;
        } else if(request[0]==1 && rx>=4) {
            reply[0]=(input>>8)&255; reply[1]=input&255;
            reply[2]=(input>>16)&255; reply[3]=(input>>24)&255;
        } else if(request[0]==2 && tx>=3 && rx>=33) {
            unsigned address=(unsigned(request[1])<<8)|(request[2]&0xE0);
            std::fill_n(reply,32,0);
            if(address<bytes.size()) std::copy_n(bytes.begin()+address,32,reply);
            reply[32]=data_crc(reply);
        } else if(request[0]==3 && tx>=35 && rx>=1) {
            unsigned address=(unsigned(request[1])<<8)|(request[2]&0xE0);
            if(address<bytes.size() && !std::equal(request+3,request+35,bytes.begin()+address)) {
                std::copy_n(request+3,32,bytes.begin()+address); store();
            }
            reply[0]=data_crc(request+3);
        } else { pif[cursor+1]|=0x40; }
        cursor+=2+tx+rx; ++channel;
    }
    pif[63]=0;
}
