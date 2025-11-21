#include "Motor.h"
#include <Arduino.h>

// Global variables
static uint8_t maxSpeed = 255; // Default maximum speed

void Motor_configureTimer1(void);

// Function to initialize motor pins and Timer1 for PWM
void Motor_init(void) {
    // Set pin modes
    pinMode(MOTOR_EN_PIN, OUTPUT);
    pinMode(MOTOR_R1_PIN, OUTPUT);
    pinMode(MOTOR_R2_PIN, OUTPUT);
    pinMode(MOTOR_L1_PIN, OUTPUT);
    pinMode(MOTOR_L2_PIN, OUTPUT);
    // Set initial values
    digitalWrite(MOTOR_EN_PIN, LOW); // Disable motor driver
    digitalWrite(MOTOR_R1_PIN, LOW); // Set initial value for right motor
    digitalWrite(MOTOR_R2_PIN, LOW); // Set initial value for right motor
    digitalWrite(MOTOR_L1_PIN, LOW); // Set initial value for left motor
    digitalWrite(MOTOR_L2_PIN, LOW); // Set initial value for left motor
    // Configure Timer1 for 977Hz PWM frequency on pins 9 and 10
    Motor_configureTimer1();
}

void Motor_configureTimer1(void) {
    // --- Configure Timer1 ---
    TCCR1A = _BV(COM1A1) | _BV(COM1B1) | _BV(WGM10);  // Fast PWM 8-bit
    TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);      // Prescaler = 64 (CS11 + CS10)
}

void Motor_enable(void) {
    digitalWrite(MOTOR_L1_PIN, LOW);
    digitalWrite(MOTOR_L2_PIN, LOW);
    digitalWrite(MOTOR_R1_PIN, LOW);
    digitalWrite(MOTOR_R2_PIN, LOW);
    // Enable motor driver
    digitalWrite(MOTOR_EN_PIN, HIGH);
}

void Motor_disable(void) {
    // Disable motor driver
    digitalWrite(MOTOR_EN_PIN, LOW);
}

void Motor_setMaxSpeed(uint8_t speed) {
    maxSpeed = speed; // Limit to 0-255 (already uint8_t)
}

void Motor_setSpeed(int16_t left, int16_t right) {
    // Ensure left and right speeds are within valid range
    left = constrain(left, -maxSpeed, maxSpeed);
    right = constrain(right, -maxSpeed, maxSpeed);
    // Set motor speeds
    if (left > 0) {
        digitalWrite(MOTOR_L2_PIN, LOW);
        analogWrite(MOTOR_L1_PIN, left);
    } else {
        digitalWrite(MOTOR_L1_PIN, LOW);
        analogWrite(MOTOR_L2_PIN, -left);
    }

    if (right > 0) {
        digitalWrite(MOTOR_R2_PIN, LOW);
        analogWrite(MOTOR_R1_PIN, right);
    } else {
        digitalWrite(MOTOR_R1_PIN, LOW);
        analogWrite(MOTOR_R2_PIN, -right);
    }
}

