#include "pak.h"
#include <chrono>
#include <array>
#include <cstdio>
#include <fstream>
#include <stdexcept>
void check(bool ok,const char* reason) { if(!ok) throw std::runtime_error(reason); }
int main() {
    try {
        auto path=std::filesystem::path("work")/("pak-test-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()))/"test.mpk";
        {
            WetrixPak pak(path);
            check(std::filesystem::file_size(path)==32768,"pak size");
            std::array<uint8_t,64> pif{};
            pif[0]=1;pif[1]=3;pif[2]=0;pif[6]=0xFE;
            pak.command(pif.data(),0);
            check(pif[3]==5 && pif[4]==0 && pif[5]==1,"pak presence");
            pif={};pif[0]=0;pif[1]=1;pif[2]=3;pif[3]=0;pif[7]=0xFE;
            pak.command(pif.data(),0);
            check(pif[4]==5 && pif[5]==0 && pif[6]==0 && (pif[2]&0x80)==0,"player 2 present without pak");
            pif={};pif[0]=1;pif[1]=4;pif[2]=1;pif[7]=1;pif[8]=4;pif[9]=1;pif[14]=0xFE;
            pak.command(pif.data(),0x10208000,0xF0304000);
            check(pif[3]==0x80 && pif[4]==0 && pif[5]==0x20 && pif[6]==0x10,"player 1 input routing");
            check(pif[10]==0x40 && pif[11]==0 && pif[12]==0x30 && pif[13]==0xF0,"player 2 independent input routing");
            for(uint8_t mask:{uint8_t(1),uint8_t(3),uint8_t(0),uint8_t(3)}) {
                pif={};pif[0]=1;pif[1]=4;pif[2]=1;pif[7]=1;pif[8]=4;pif[9]=1;pif[14]=0xFE;
                pak.command(pif.data(),0x10208000,0xF0304000,mask);
                check(((pif[1]&0x80)==0)==bool(mask&1),"PIF port 1 response tracks presence");
                check(((pif[8]&0x80)==0)==bool(mask&2),"PIF port 2 response tracks attach/unplug");
                if(!(mask&2)) check(pif[10]==0 && pif[11]==0 && pif[12]==0 && pif[13]==0,"disconnected PIF reply cleared");
            }
            pif={};pif[0]=35;pif[1]=1;pif[2]=3;pif[3]=5;pif[4]=0;pif[38]=0xFE;
            for(int i=0;i<32;++i) pif[5+i]=uint8_t(i*7+3);
            pak.command(pif.data(),0);
        }
        {
            WetrixPak pak(path);
            std::array<uint8_t,64> pif{};
            pif[0]=3;pif[1]=33;pif[2]=2;pif[3]=5;pif[4]=0;pif[38]=0xFE;
            pak.command(pif.data(),0);
            for(int i=0;i<32;++i) check(pif[5+i]==uint8_t(i*7+3),"persistent page round trip");
        }
        auto invalid=path.parent_path()/"invalid.mpk";
        { std::ofstream f(invalid); f<<"preserve"; }
        bool rejected=false;
        try { WetrixPak pak(invalid); } catch(const std::runtime_error&) { rejected=true; }
        check(rejected && std::filesystem::file_size(invalid)==8,"invalid existing file preserved");
        puts("PASS: two controller ports, independent button/stick routing, pak presence, 32 KiB format, persistent page round trip, invalid-file preservation");
        return 0;
    } catch(const std::exception& e) { fprintf(stderr,"FAIL: %s\n",e.what()); return 1; }
}
