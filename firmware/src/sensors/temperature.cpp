#include "temperature.h"
#include <OneWire.h>
#include "config.h"
namespace {
OneWire bus(sentinel::kTemperature);
uint8_t address[8];
bool present=false, converting=false, valid=false;
uint32_t started=0, lastUpdate=0;
int16_t reading=0;
}
namespace temperature {
bool begin() {
    bus.reset_search();
    present = bus.search(address) && address[0]==0x28 && OneWire::crc8(address,7)==address[7];
    return present;
}
void poll(uint32_t now) {
    if (!present) return;
    if (!converting) {
        if (uint32_t(now-started)<1000) return;
        if (!bus.reset()) { valid=false; return; }
        bus.select(address); bus.write(0x44, 0); // external power required
        started=now; converting=true;
    } else if (uint32_t(now-started)>=750) {
        converting=false;
        if (!bus.reset()) { valid=false; return; }
        bus.select(address); bus.write(0xBE);
        uint8_t scratch[9];
        for (uint8_t i=0;i<9;++i) scratch[i]=bus.read();
        valid=OneWire::crc8(scratch,8)==scratch[8];
        if (valid) {
            reading=static_cast<int16_t>(scratch[0] | (uint16_t(scratch[1])<<8));
            valid=reading>=-55*16 && reading<=125*16;
            if (valid) lastUpdate=now;
        }
    }
}
bool value(int16_t& raw, uint32_t& updated) {
    raw=reading; updated=lastUpdate; return valid;
}
}
