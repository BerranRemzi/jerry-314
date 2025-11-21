#ifndef LOGGER_H
#define LOGGER_H

#include <stdint.h>
#include "Command.h"  // For LoggingFlags

// Initialize logger with logging flags
void Logger_Init(LoggingFlags& flags);

// Log sensor values
void Logger_LogSensor(void);

// Log line position
void Logger_LogLine(int16_t line);

// Log motor output
void Logger_LogOutput(int16_t output);

// Log PID parameters (throttled internally)
void Logger_LogPID(double kp, double ki, double kd);

#endif /* LOGGER_H */

