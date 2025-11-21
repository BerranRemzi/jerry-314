#include "Sensor.h"
#include "Jerry.h"
#include <Arduino.h>

// Constants
#define ANALOG_PIN_COUNT 8
static const uint8_t ANALOG_PIN[ANALOG_PIN_COUNT] = {A0, A1, A2, A3, A4, A5, A6, A7};
static const uint16_t MIN_CONTRAST = 200;
static const uint32_t MIN_SIGNAL_SUM = 100;
static const double WEIGHT_SCALE_FACTOR = 127.0 / 52.5; // Scale from [-52.5, +52.5] to [-127, +127]

// Global variables
static uint16_t edgeDiffThreshold = 100; // Configurable edge detection threshold
// Weight values for weighted average calculation
// Sensor 0 (leftmost) -> -52.5, Sensor 3.5 (center) -> 0, Sensor 7 (rightmost) -> +52.5
static const double WEIGHT[ANALOG_PIN_COUNT] = {-52.5, -37.5, -22.5, -7.5, 7.5, 22.5, 37.5, 52.5};

// Global variables
static int16_t last_line_pos = 0; // Last known line position (for fallback when contrast is low)
static uint16_t adc_line[ANALOG_PIN_COUNT] = {0}; // Array to hold ADC values (used by Sensor.cpp and Jerry_getSensorValues)

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
static bool checkEdgeDetection(uint16_t max_val, uint16_t* adc_array, uint8_t edge_idx, int16_t threshold, int16_t* result) {
    if (max_val == adc_array[edge_idx]) {
        int16_t diff = (int16_t)adc_array[edge_idx] - (int16_t)adc_array[edge_idx + (edge_idx == 0 ? 1 : -1)];
        if (diff >= threshold) {
            *result = (edge_idx == 0) ? -127 : 127;
            return true;
        }
    }
    return false;
}

int16_t Sensor_readBlack(void) {
    // Enable line sensor
    digitalWrite(LINE_SENSOR_EN_PIN, HIGH);
    delay(1); // Allow sensor to stabilize
    
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
    if (checkEdgeDetection(max_val, adc_line, 0, edgeDiffThreshold, &edge_result) || 
        checkEdgeDetection(max_val, adc_line, ANALOG_PIN_COUNT - 1, edgeDiffThreshold, &edge_result)) {
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

void Sensor_setEdgeDiffThreshold(uint16_t threshold) {
    edgeDiffThreshold = threshold;
}

uint16_t Sensor_getEdgeDiffThreshold(void) {
    return edgeDiffThreshold;
}

void Sensor_getSensorValues(char * output) {
    // Format sensor values as "S,val1,val2,val3,val4,val5,val6,val7,val8\n"
    char * ptr = output;
    ptr += sprintf(ptr, "S");
    
    for (uint8_t i = 0; i < ANALOG_PIN_COUNT; ++i) {
        ptr += sprintf(ptr, ",%u", adc_line[i]);
    }
    sprintf(ptr, "\n");
}

