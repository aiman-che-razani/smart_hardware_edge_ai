#include "sampler.h"
#include "../sensors/accelerometer.h"
#include "../sensors/current.h"
#include "../sensors/temperature.h"
#include "../communication/serial_protocol.h"
#include "../actuators/alarm.h"
#include "types.h"
#include "config.h"
#include <Arduino.h>
namespace {
Sample sample={};
bool accelerationOk=false, currentOk=false;
uint32_t currentTime=0, lastPoll=0, lastStatus=0, lastMissing=0;
uint16_t age(uint32_t now,uint32_t previous) {
    uint32_t elapsed=now-previous; return elapsed>65535 ? 65535 : elapsed;
}
}
namespace sampler {
void begin(uint32_t boot) {
    sample.boot=boot;
    accelerationOk=acceleration::begin();
    currentOk=current::begin();
    temperature::begin();
}
void poll() {
    uint32_t now=millis();
    if(uint32_t(now-lastPoll)>=40) {
        lastPoll=now;
        currentOk=current::read(sample.shunt);
        if(currentOk) currentTime=now;
    }
    temperature::poll(now);
    uint32_t tempTime=0;
    bool tempOk=temperature::value(sample.temperature,tempTime);
    sample.currentAge=age(now,currentTime); sample.temperatureAge=age(now,tempTime);
    sample.flags=(currentOk?2:0) | (tempOk?4:0);
    if(uint32_t(now-lastStatus)>=1000) { lastStatus=now; transport::status(); }
    if(!accelerationOk) {
        if(uint32_t(now-lastMissing)>=100) {
            lastMissing=now; sample.timestamp=micros(); ++sample.sequence;
            if(transport::streaming()) transport::send(sample);
        }
        return;
    }
    bool overflow=acceleration::overrun();
    uint8_t pending=acceleration::pending();
    if(pending>32) { accelerationOk=false; return; }
    // Bound each pass to four FIFO samples to keep command service responsive.
    if(pending>4) pending=4;
    while(pending--) {
        int16_t xyz[3]; acceleration::read(xyz);
        sample.timestamp=micros(); // FIFO readout time, not an invented acquisition timestamp.
        sample.ax=xyz[0]; sample.ay=xyz[1]; sample.az=xyz[2];
        sample.flags |= 1;
        if(overflow) sample.flags |= 8; // Exact sensor loss count is unknown after overrun.
        ++sample.sequence; // Also increment when TX cannot accept a packet.
        if(transport::streaming()) transport::send(sample);
#ifdef SENTINEL_EDGE
        // Separate optional streaming threshold experiment, no vibration window allocation.
        static uint8_t peaks=0;
        if(abs(sample.ax)>128) { if(peaks<255) ++peaks; } else peaks=0;
        if(peaks>=4) alarm::set(2);
#endif
    }
}
}
