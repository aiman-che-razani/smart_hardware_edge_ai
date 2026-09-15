#include "current.h"
#include <Wire.h>
namespace {
bool readReg(uint8_t address, uint16_t& value) {
    Wire.beginTransmission(0x40);
    Wire.write(address);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(uint8_t(0x40), uint8_t(2)) != 2) return false;
    value = uint16_t(Wire.read()) << 8;
    value |= Wire.read();
    return true;
}
}
namespace current {
bool begin() {
    Wire.begin();
    Wire.setClock(100000);
    Wire.setWireTimeout(2000, true);
    Wire.beginTransmission(0x40);
    Wire.write(0);
    Wire.write(0x39); Wire.write(0x9F); // 32 V range, +/-320mV shunt, 12 bit continuous
    return Wire.endTransmission() == 0;
}
bool read(int16_t& shunt) {
    uint16_t bus = 0, raw = 0;
    if (!readReg(2, bus) || !(bus & 2) || (bus & 1)) return false;
    if (!readReg(1, raw)) return false;
    shunt = static_cast<int16_t>(raw); // 10 uV/LSB, PC applies measured shunt resistance.
    return true;
}
}
