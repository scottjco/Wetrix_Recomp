#pragma once
#include <algorithm>
#include <cmath>

// Grid placement remains in whole cells. Deflection controls repeat speed,
// rather than jumping between the original game's three speed bands.
struct WetrixStickRepeat {
    int direction=0;
    double remaining=0;
    int update(int value, double dt) {
        const int magnitude=std::abs(value);
        const int next=magnitude >= (direction ? 8 : 12) ? (value>0 ? 1 : -1) : 0;
        if(!next) { direction=0; remaining=0; return 0; }
        const double strength=std::clamp((magnitude-12)/68.0,0.0,1.0);
        const double rate=6.0+24.0*strength;
        if(next!=direction) {
            direction=next;
            remaining=1.0/rate;
            return direction;
        }
        // A stronger deflection must not wait out the previous slow interval.
        remaining=std::min(remaining,1.0/rate)-dt;
        if(remaining>1e-9) return 0;
        remaining+=1.0/rate;
        return direction;
    }
};
