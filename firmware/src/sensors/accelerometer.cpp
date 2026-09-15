#include "accelerometer.h"
#include <Arduino.h>
#include <SPI.h>
#include "config.h"
namespace {
uint8_t reg(uint8_t address, uint8_t value, bool reading) {
    SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE3));
    digitalWrite(sentinel::kCs, LOW);
    SPI.transfer(address | (reading ? 0x80 : 0));
    uint8_t result = SPI.transfer(value);
    digitalWrite(sentinel::kCs, HIGH);
    SPI.endTransaction();
    return result;
}
}
namespace acceleration {
bool begin() {
    pinMode(sentinel::kCs, OUTPUT);
    digitalWrite(sentinel::kCs, HIGH);
    SPI.begin();
    if (reg(0, 0, true) != 0xE5) return false;
    reg(0x2D, 0, false);
    reg(0x31, 0x08, false); // full resolution, +/-2g, four-wire SPI
    const uint8_t rate = sentinel::kRate == 800 ? 0x0D : 0x0A;
    reg(0x2C, rate, false);
    reg(0x38, 0x80, false); // stream FIFO, oldest sample replaced on overflow
    reg(0x2D, 0x08, false);
    return reg(0x31, 0, true) == 0x08 && reg(0x2C, 0, true) == rate;
}
uint8_t pending() { return reg(0x39, 0, true) & 0x3F; }
bool overrun() { return (reg(0x30, 0, true) & 1) != 0; }
void read(int16_t* xyz) {
    SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE3));
    digitalWrite(sentinel::kCs, LOW);
    SPI.transfer(0x32 | 0xC0);
    for (uint8_t i=0; i<3; ++i) {
        uint8_t lo = SPI.transfer(0);
        uint8_t hi = SPI.transfer(0);
        xyz[i] = static_cast<int16_t>(lo | (uint16_t(hi) << 8));
    }
    digitalWrite(sentinel::kCs, HIGH);
    SPI.endTransaction();
    delayMicroseconds(5); // FIFO pop timing margin at 2 MHz.
}
}
