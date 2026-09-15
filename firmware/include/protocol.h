#pragma once
#include <stdint.h>
enum Message : uint8_t { DATA=1, STATUS=2, ACK=3, ERROR=4, SET_ALARM=16,
 CLEAR_ALARM=17, START_STREAM=18, STOP_STREAM=19, PING=20, GET_CONFIG=21 };
uint16_t crc16(const uint8_t* data, uint8_t length);
