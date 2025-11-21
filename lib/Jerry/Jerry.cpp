#include "Jerry.h"
#include "Motor.h"
#include <Arduino.h>
#include <stdio.h>
#ifdef ARDUINO
#include <avr/interrupt.h>
#endif
#include <ErriezSerialTerminal.h>

// Constants
#define ANALOG_PIN_COUNT 8

typedef struct {
    uint8_t pin;
    uint8_t mode;
    int8_t initialValue;
} PinConfig_t;

#define PIN_CONFIG_COUNT 10
PinConfig_t pinConfigs[PIN_CONFIG_COUNT] = {
    {LINE_SENSOR_EN_PIN, OUTPUT, LOW},
    {DIST_SENSOR_EN_PIN, OUTPUT, LOW},
    {MOTOR_EN_PIN, OUTPUT, LOW},
    {MOTOR_R1_PIN, OUTPUT, LOW},
    {MOTOR_R2_PIN, OUTPUT, LOW},
    {MOTOR_L1_PIN, OUTPUT, LOW},
    {MOTOR_L2_PIN, OUTPUT, LOW},
    {BTN_1_PIN, INPUT_PULLUP, -1},
    {BTN_2_PIN, INPUT_PULLUP, -1},
    {BTN_3_PIN, INPUT_PULLUP, -1}
};

void Jerry_Init(void) {
    for(uint8_t i = 0; i < PIN_CONFIG_COUNT; ++i) {
        pinMode(pinConfigs[i].pin, pinConfigs[i].mode);
        if (pinConfigs[i].initialValue != -1) {
            digitalWrite(pinConfigs[i].pin, pinConfigs[i].initialValue);
        }
    }
    Motor_init();
}



void cmdBootloader(void)
{
  typedef void (*do_reboot_t)(void);
  const do_reboot_t do_reboot = (do_reboot_t)((FLASHEND - 511) >> 1);
  
  Serial.println(F("Jumping to bootloader..."));
  Serial.print(F("Bootloader address: 0x"));
  Serial.println((uint16_t)do_reboot, HEX);
  Serial.flush();
  cli();
  TCCR0A = TCCR1A = TCCR2A = 0;
  do_reboot();
}