#pragma once
#include <array>
#include <string>
#include <vector>
#include <cstdint>
#include <map>

class WetrixDeviceOrdinals {
    std::map<std::pair<std::string,std::string>,unsigned> ordinals;
    std::map<std::string,unsigned> next;
public:
    unsigned resolve(const std::string& guid,const std::string& identity) {
        auto [entry,inserted]=ordinals.emplace(std::make_pair(guid,identity),0);
        if(inserted) entry->second=++next[guid];
        return entry->second;
    }
};

struct WetrixDeviceAssignment { int controller=-1; bool keyboard=false; };

// Explicit choices reserve devices before either Automatic choice is resolved.
// Indices refer only to currently attached controllers, never saved pointers.
inline std::array<WetrixDeviceAssignment,2> wetrix_resolve_devices(
    const std::array<std::string,2>& choices, const std::vector<std::string>& available) {
    std::array<WetrixDeviceAssignment,2> result{};
    std::vector<bool> used(available.size(),false);
    for(int p=0;p<2;++p) {
        result[p].keyboard=choices[p]=="keyboard";
        if(choices[p]=="auto" || choices[p]=="none" || result[p].keyboard) continue;
        for(size_t i=0;i<available.size();++i) if(available[i]==choices[p] && !used[i]) {
            result[p].controller=int(i); used[i]=true; break;
        }
    }
    for(int p=0;p<2;++p) if(choices[p]=="auto") {
        for(size_t i=0;i<available.size();++i) if(!used[i]) {
            result[p].controller=int(i); used[i]=true; break;
        }
        // Automatic keyboard fallback belongs to controller port 1 only.
        result[p].keyboard=(p==0 && result[p].controller<0);
    }
    return result;
}

inline uint8_t wetrix_assignment_mask(const std::array<WetrixDeviceAssignment,2>& assignments) {
    uint8_t mask=0;
    for(unsigned p=0;p<2;++p)
        if(assignments[p].keyboard || assignments[p].controller>=0) mask|=uint8_t(1U<<p);
    return mask;
}
