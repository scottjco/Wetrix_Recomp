#include "device_resolution.h"
#include "controller_bridge.h"
#include <vector>
#include <cstdio>
#include <stdexcept>

static void check(bool condition,const char* reason) { if(!condition) throw std::runtime_error(reason); }
int main() {
    try {
        auto resolve=[](std::array<std::string,2> choice,std::vector<std::string> pads) {
            return wetrix_resolve_devices(choice,pads);
        };
        check(wetrix_assignment_mask(resolve({"auto","none"},{}))==1,"startup P1 keyboard fallback, P2 none");
        check(wetrix_assignment_mask(resolve({"none","none"},{}))==0,"both ports absent");
        check(wetrix_assignment_mask(resolve({"keyboard","keyboard"},{}))==3,"explicit keyboards are controllers");
        check(wetrix_assignment_mask(resolve({"auto","auto"},{}))==1,"P2 Automatic cannot fall back to keyboard");
        auto both=resolve({"auto","auto"},{"pad:1","pad:2"});
        check(both[0].controller==0 && both[1].controller==1,"automatic pads are independent");
        check(wetrix_assignment_mask(resolve({"auto","auto"},{"pad:1"}))==1,"one pad cannot occupy both ports");
        both=resolve({"auto","pad:1"},{"pad:1"});
        check(both[0].keyboard && both[1].controller==0,"P2 explicit reservation precedes P1 Auto");
        check(wetrix_assignment_mask(resolve({"pad:1","pad:1"},{"pad:1"}))==1,"duplicate saved assignment cannot share physical pad");
        check(wetrix_assignment_mask(resolve({"keyboard","pad:2"},{"pad:1"}))==1,"explicit disconnected controller remains absent");
        check(wetrix_assignment_mask(resolve({"keyboard","pad:2"},{"pad:1","pad:2"}))==3,"explicit controller attachment restores port");
        WetrixDeviceOrdinals ordinals;
        check(ordinals.resolve("guid","path-a")==1 && ordinals.resolve("guid","path-b")==2,"same-model pads get separate identities");
        check(ordinals.resolve("guid","path-b")==2,"removing first pad does not renumber second");
        check(ordinals.resolve("guid","path-a")==1,"reattachment restores saved identity");

        std::vector<uint8_t> memory(0x800000);auto* rdram=memory.data();
        const int64_t status=int32_t(0x80001000U),pads=int32_t(0x80001100U);
        MEM_W(0,int32_t(0x800876D0U))=2; // Lesson/Multiplay world player count.
        for(uint8_t mask:{uint8_t(1),uint8_t(3),uint8_t(1),uint8_t(0),uint8_t(1),uint8_t(2)}) {
            wetrix_write_controller_status(rdram,status,mask);
            wetrix_write_controller_reads(rdram,pads,mask,{0x10208000U,0xf0304000U});
            wetrix_write_native_port_presence(rdram,mask);
            for(unsigned p=0;p<4;++p) {
                const bool present=p<2 && (mask&(1U<<p));
                check((uint8_t(MEM_B(p*4+3,status))==0)==present,"query response reflects live mask");
                check(MEM_HU(p*4,status)==(present ? 0x0500 : 0),"controller query type");
                check(uint8_t(MEM_B(p*4+2,status))==(present && p==0 ? 1 : 0),"pak only responds on assigned port 1");
                check((uint8_t(MEM_B(p*6+4,pads))==0)==present,"read response reflects live mask");
                if(!present) check(MEM_HU(p*6,pads)==0 && MEM_B(p*6+2,pads)==0 && MEM_B(p*6+3,pads)==0,"absent port cannot retain buttons or stick");
            }
            check(MEM_W(0,int32_t(0x800A242CU))==mask,"native menu reads current physical port mask");
            check((MEM_W(0,int32_t(0x800A242CU))==3)==(mask==3),"native versus eligibility requires both ports");
            check(MEM_W(0,int32_t(0x800876D0U))==2,"Lesson CPU/world player count remains independent");
        }
        MEM_H(6,int64_t(int32_t(0x800A2B40U)))=0xffff;
        MEM_H(0,int32_t(0x800A2B68U))=0x1234;
        wetrix_clear_disconnected_ports(rdram,2);
        check(MEM_HU(6,int64_t(int32_t(0x800A2B40U)))==0,"unplug releases held physical P2 buttons immediately");
        check(MEM_HU(0,int32_t(0x800A2B68U))==0x1234,"unplug does not clear CPU/logical player input");
        puts("PASS: assignment resolution, startup/attach/unplug/duplicates/auto, stable pad identities, native RAM query/read errors, live menu presence, Lesson CPU independence");
        return 0;
    } catch(const std::exception& e) { fprintf(stderr,"FAIL: %s\n",e.what());return 1; }
}
