#include <Arduino.h>
#include <EEPROM.h>
#include "config.h"
#include "acquisition/sampler.h"
#include "communication/serial_protocol.h"
#include "actuators/alarm.h"

void setup() {
    // Persistent boot counter. EEPROM endurance/power-loss limitations are documented.
    uint32_t boot=0;
    EEPROM.get(0,boot);
    boot=(boot==0xFFFFFFFFUL)?1:boot+1;
    EEPROM.put(0,boot);
    alarm::begin();
    transport::begin(boot);
    sampler::begin(boot);
    transport::status();
}

void loop() {
    transport::poll();
    sampler::poll();
    alarm::poll();
}
