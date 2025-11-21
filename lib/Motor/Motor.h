#ifndef MOTOR_H
#define MOTOR_H
#include "stdint.h"

#define MOTOR_EN_PIN 4   // PD4 (Digital Pin 4)
#define MOTOR_R1_PIN 5   // PD5 (Digital Pin 5)
#define MOTOR_R2_PIN 6   // PD6 (Digital Pin 6)

#define WRONG_MOTOR_PINS
#ifndef WRONG_MOTOR_PINS
#define MOTOR_L1_PIN 10  // PB1 (Digital Pin 9)
#define MOTOR_L2_PIN 9   // PB2 (Digital Pin 10)
#else
#define MOTOR_L1_PIN 10  // PB2 (Digital Pin 10)
#define MOTOR_L2_PIN 9   // PB1 (Digital Pin 9)
#endif

// Function to initialize motor pins and Timer1 for PWM
void Motor_init(void);
void Motor_enable(void);
void Motor_disable(void);
void Motor_setMaxSpeed(uint8_t maxSpeed);
void Motor_setSpeed(int16_t left, int16_t right);

#endif /* MOTOR_H */

