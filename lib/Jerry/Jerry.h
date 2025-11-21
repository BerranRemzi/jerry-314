#ifndef JERRY_H
#define JERRY_H
#include "stdint.h"

#define LINE_SENSOR_EN_PIN 11  // PD1 (Digital Pin 11)
#define DIST_SENSOR_EN_PIN 12  // PD0 (Digital Pin 12)
#define IR_RECEIVE_PIN 8  // PB0 (Digital Pin 8)
#define BTN_1_PIN 2   // PD2 (Digital Pin 2)
#define BTN_2_PIN 3   // PD3 (Digital Pin 3)
#define BTN_3_PIN 7   // PD7 (Digital Pin 7)

void Jerry_Init(void);

void cmdBootloader(void);

#endif /* JERRY_H */
