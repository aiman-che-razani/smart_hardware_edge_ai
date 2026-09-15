#include "serial_protocol.h"
#include "protocol.h"
#include "config.h"
#include "../actuators/alarm.h"
#include <Arduino.h>
#include <string.h>
namespace {
uint8_t rx[47], used=0;
uint32_t bootId=0, lastByte=0;
bool enabled=true;
bool frame(uint8_t kind,const void* data,uint8_t length) {
    uint8_t buffer[47]={0xA5,0x5A,1,kind,length};
    if (length>40 || Serial.availableForWrite()<length+7) return false;
    memcpy(buffer+5,data,length);
    uint16_t crc=crc16(buffer+2,length+3);
    buffer[length+5]=crc&255; buffer[length+6]=crc>>8;
    Serial.write(buffer,length+7); return true;
}
void consume(uint8_t count) { memmove(rx,rx+count,used-count); used-=count; }
}
uint16_t crc16(const uint8_t* data,uint8_t length) {
    uint16_t crc=0xFFFF;
    while (length--) {
        crc^=uint16_t(*data++)<<8;
        for(uint8_t i=0;i<8;++i) crc=(crc&0x8000)?(crc<<1)^0x1021:crc<<1;
    }
    return crc;
}
namespace transport {
void begin(uint32_t boot) { bootId=boot; Serial.begin(sentinel::kConsoleBaud); }
bool streaming() { return enabled; }
void status() {
#ifndef SENTINEL_CSV
    uint8_t payload[10];
    memcpy(payload,&bootId,4);
    uint16_t rate=sentinel::kRate, scale=sentinel::kAccelerationUg, shunt=sentinel::kShuntMilliohm;
    memcpy(payload+4,&rate,2); memcpy(payload+6,&scale,2); memcpy(payload+8,&shunt,2);
    frame(STATUS,payload,10);
#endif
}
bool send(const Sample& s) {
#ifdef SENTINEL_CSV
    // Debug only: blocking formatting is intentionally excluded from the 800 Hz build.
    Serial.print(F("D,")); Serial.print(s.boot); Serial.print(',');
    Serial.print(s.sequence); Serial.print(','); Serial.print(s.timestamp); Serial.print(',');
    Serial.print(s.ax); Serial.print(','); Serial.print(s.ay); Serial.print(','); Serial.print(s.az); Serial.print(',');
    Serial.print(s.shunt); Serial.print(','); Serial.print(s.temperature); Serial.print(',');
    Serial.print(s.currentAge); Serial.print(','); Serial.print(s.temperatureAge); Serial.print(','); Serial.println(s.flags);
    return true;
#else
    return frame(DATA,&s,sizeof(s));
#endif
}
void poll() {
    if (used && uint32_t(millis()-lastByte)>500) used=0;
    uint8_t budget=32;
    while (Serial.available() && budget--) {
        if (used==sizeof(rx)) consume(1);
        rx[used++]=Serial.read(); lastByte=millis();
        while (used>=2) {
            if(rx[0]!=0xA5 || rx[1]!=0x5A) { consume(1); continue; }
            if(used<5) break;
            if(rx[2]!=1 || rx[4]>40) { consume(1); continue; }
            uint8_t total=rx[4]+7;
            if(used<total) break;
            uint16_t check=rx[total-2] | (uint16_t(rx[total-1])<<8);
            if(crc16(rx+2,total-4)!=check) { consume(1); continue; }
            if(rx[4]==3) {
                uint8_t kind=rx[3], value=rx[7], error=0;
                switch(kind) {
                    case SET_ALARM: if(value<=3) alarm::set(value); else error=1; break;
                    case CLEAR_ALARM: alarm::set(0); break;
                    case START_STREAM: enabled=true; break;
                    case STOP_STREAM: enabled=false; break;
                    case PING: case GET_CONFIG: break;
                    default: error=2;
                }
                if(!error) alarm::heartbeat();
                uint8_t ack[4]={rx[5],rx[6],kind,error};
                frame(ACK,ack,4);
                if(kind==GET_CONFIG) status();
            } else {
                uint8_t code=3; frame(ERROR,&code,1);
            }
            consume(total);
        }
    }
}
}
