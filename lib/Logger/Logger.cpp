#include "Logger.h"
#include "Sensor.h"
#include <Arduino.h>

static LoggingFlags* flagsPtr = nullptr;
static unsigned long lastPidLog = 0;

void Logger_Init(LoggingFlags& flags) {
    flagsPtr = &flags;
}

void Logger_LogSensor(void) {
    if (flagsPtr != nullptr && flagsPtr->logS) {
        char buffer[64];
        Sensor_getSensorValues(buffer);
        Serial.write(buffer);
    }
}

void Logger_LogLine(int16_t line) {
    if (flagsPtr != nullptr && flagsPtr->logL) {
        Serial.print("L,");
        Serial.println(line);
    }
}

void Logger_LogOutput(int16_t output) {
    if (flagsPtr != nullptr && flagsPtr->logO) {
        Serial.print("O,");
        Serial.println(output);
    }
}

void Logger_LogPID(double kp, double ki, double kd) {
    if (flagsPtr == nullptr) return;
    
    // Log PID values less frequently (every 100ms max)
    unsigned long currentTime = millis();
    if (currentTime - lastPidLog > 100) {
        if (flagsPtr->logP) {
            Serial.print(F("pid p "));
            Serial.println(kp, 3);
        }
        if (flagsPtr->logI) {
            Serial.print(F("pid i "));
            Serial.println(ki, 3);
        }
        if (flagsPtr->logD) {
            Serial.print(F("pid d "));
            Serial.println(kd, 3);
        }
        lastPidLog = currentTime;
    }
}

