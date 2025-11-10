#include "Jerry.h"
#include <Arduino.h>
#include <stdio.h>
#ifdef ARDUINO
#include <avr/interrupt.h>
#endif
#include <ErriezSerialTerminal.h>

// Constants
#define ANALOG_PIN_COUNT 8
static const uint8_t ANALOG_PIN[ANALOG_PIN_COUNT] = {A0, A1, A2, A3, A4, A5, A6, A7};
static const uint16_t MIN_CONTRAST = 200;
static const uint16_t EDGE_DIFF_THRESHOLD = 100;
static const uint32_t MIN_SIGNAL_SUM = 100;
static const double WEIGHT_SCALE_FACTOR = 127.0 / 52.5; // Scale from [-52.5, +52.5] to [-127, +127]

// Weight values for weighted average calculation
// Sensor 0 (leftmost) -> -52.5, Sensor 3.5 (center) -> 0, Sensor 7 (rightmost) -> +52.5
static const double WEIGHT[ANALOG_PIN_COUNT] = {-52.5, -37.5, -22.5, -7.5, 7.5, 22.5, 37.5, 52.5};

// Global variables
static uint16_t adc_line[ANALOG_PIN_COUNT] = {0}; // Array to hold ADC values
static int16_t last_line_pos = 0; // Last known line position (for fallback when contrast is low)
static uint8_t maxSpeed = 255; // Default maximum speed
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
}



// Helper function to find min/max values in sensor array
static void findMinMax(const uint16_t* array, uint8_t size, uint16_t* min_val, uint16_t* max_val) {
    *min_val = array[0];
    *max_val = array[0];
    for (uint8_t i = 1; i < size; ++i) {
        if (array[i] < *min_val) *min_val = array[i];
        if (array[i] > *max_val) *max_val = array[i];
    }
}

// Helper function to check edge detection
static bool checkEdgeDetection(uint16_t max_val, uint16_t* adc_array, uint8_t edge_idx, int16_t* result) {
    if (max_val == adc_array[edge_idx]) {
        int16_t diff = (int16_t)adc_array[edge_idx] - (int16_t)adc_array[edge_idx + (edge_idx == 0 ? 1 : -1)];
        if (diff >= EDGE_DIFF_THRESHOLD) {
            *result = (edge_idx == 0) ? -127 : 127;
            return true;
        }
    }
    return false;
}

int16_t Jerry_lineRead(void) {
    // Enable line sensor
    digitalWrite(LINE_SENSOR_EN_PIN, HIGH);
    delay(10); // Allow sensor to stabilize
    
    // Read all ADC channels
    for (uint8_t i = 0; i < ANALOG_PIN_COUNT; ++i) {
        adc_line[i] = analogRead(ANALOG_PIN[i]);
    }
    
    // Disable line sensor
    digitalWrite(LINE_SENSOR_EN_PIN, LOW);

    // Find minimum and maximum values (background/ambient light level)
    uint16_t min_val, max_val;
    findMinMax(adc_line, ANALOG_PIN_COUNT, &min_val, &max_val);
    
    // Calculate contrast (difference between max and min)
    uint16_t contrast = max_val - min_val;
    
    // Check contrast threshold FIRST - reject readings with insufficient contrast
    // This handles cases where sensors are too far from surface (high ambient, low contrast)
    // or too close to surface (all values saturated), or line is completely outside array
    if (contrast < MIN_CONTRAST) {
        // No line detected or insufficient contrast - hold last known position for continuity
        return last_line_pos;
    }
    
    // Only check edge detection if we have sufficient contrast (line is actually visible)
    // Check if line is going outside sensor array boundaries
    int16_t edge_result;
    if (checkEdgeDetection(max_val, adc_line, 0, &edge_result) || 
        checkEdgeDetection(max_val, adc_line, ANALOG_PIN_COUNT - 1, &edge_result)) {
        last_line_pos = edge_result;
        return edge_result;
    }
    
    // Subtract background (minimum) from all readings to normalize ambient light
    // This makes the calculation robust to changes in sensor distance
    double weighted_sum = 0.0;
    uint32_t sum = 0;
    for (uint8_t i = 0; i < ANALOG_PIN_COUNT; ++i) {
        // Subtract minimum, ensure non-negative
        uint16_t normalized = (adc_line[i] > min_val) ? (adc_line[i] - min_val) : 0;
        weighted_sum += (double)normalized * WEIGHT[i];
        sum += normalized;
    }
    
    // Check if we have enough signal after background subtraction
    if (sum < MIN_SIGNAL_SUM) {
        // Insufficient signal - hold last known position for continuity
        return last_line_pos;
    }

    // Calculate line position: weighted average normalized by total sum
    // Result is in weight range: [-52.5, +52.5], scale to [-127, +127]
    double line_pos_d = (weighted_sum / (double)sum) * WEIGHT_SCALE_FACTOR;
    
    // Clamp to ensure we stay within [-127, +127] range
    if (line_pos_d > 127.0) line_pos_d = 127.0;
    else if (line_pos_d < -127.0) line_pos_d = -127.0;
    
    int16_t line_pos = (int16_t)line_pos_d;
    
    // Update last known position and return calculated value
    last_line_pos = line_pos;
    return line_pos;
}

void Jerry_getSensorValues(char * output) {
    // Format sensor values as "S,val1,val2,val3,val4,val5,val6,val7,val8\n"
    char * ptr = output;
    ptr += sprintf(ptr, "S");
    
    for (uint8_t i = 0; i < ANALOG_PIN_COUNT; ++i) {
        ptr += sprintf(ptr, ",%u", adc_line[i]);
    }
    sprintf(ptr, "\n");
}
void Jerry_motorEnable(void) {
    digitalWrite(MOTOR_L1_PIN, LOW);
    digitalWrite(MOTOR_L2_PIN, LOW);
    digitalWrite(MOTOR_R1_PIN, LOW);
    digitalWrite(MOTOR_R2_PIN, LOW);
    // Enable motor driver
    digitalWrite(MOTOR_EN_PIN, HIGH);
}
void Jerry_motorDisable(void) {
    // Disable motor driver
    digitalWrite(MOTOR_EN_PIN, LOW);
}
void Jerry_setMaxSpeed(uint8_t speed) {
    maxSpeed = speed; // Limit to 0-255 (already uint8_t)
}

void Jerry_setSpeed(int16_t left, int16_t right) {
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

void cmdBootloader(void)
{
#if FLASHEND > 140000
  Serial.println(F("Jump not supported on chips with >128k"));
#else
  typedef void (*do_reboot_t)(void);
  const do_reboot_t do_reboot = (do_reboot_t)((FLASHEND - 511) >> 1);
  
  Serial.println(F("Jumping to bootloader..."));
  Serial.print(F("Bootloader address: 0x"));
  Serial.println((uint16_t)do_reboot, HEX);
  Serial.flush();
  cli();
  TCCR0A = TCCR1A = TCCR2A = 0;
  do_reboot();
#endif
}