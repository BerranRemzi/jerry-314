#ifndef JERRY_H
#define JERRY_H
#include "stdint.h"

#define LINE_SENSOR_EN_PIN 11  // PD1 (Digital Pin 11)
#define DIST_SENSOR_EN_PIN 12  // PD0 (Digital Pin 12)
#define IR_RECEIVE_PIN 8  // PB0 (Digital Pin 8)
#define BTN_1_PIN 2   // PD2 (Digital Pin 2)
#define BTN_2_PIN 3   // PD3 (Digital Pin 3)
#define BTN_3_PIN 7   // PD7 (Digital Pin 7)

#define MOTOR_EN_PIN 4   // PD4 (Digital Pin 4)
#define MOTOR_R1_PIN 5   // PD5 (Digital Pin 5)
#define MOTOR_R2_PIN 6   // PD6 (Digital Pin 6)
#define MOTOR_L1_PIN 9   // PB1 (Digital Pin 9)
#define MOTOR_L2_PIN 10  // PB2 (Digital Pin 10)

void Jerry_Init(void);

int16_t Jerry_lineRead(void);
void Jerry_getSensorValues(char * output);
void Jerry_setMaxSpeed(uint8_t maxSpeed);
void Jerry_setSpeed(int16_t left, int16_t right);
void Jerry_motorEnable(void);
void Jerry_motorDisable(void);

#endif /* JERRY_H */
