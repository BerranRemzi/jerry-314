#ifndef COMMAND_H
#define COMMAND_H

#include <Arduino.h>
#include <ErriezSerialTerminal.h>
#include "PID.h"
#include "Jerry.h"

// Logging flags structure
struct LoggingFlags {
  bool logP;
  bool logI;
  bool logD;
  bool logS;
  bool logL;
  bool logO;
};

// Command handler class
class CommandHandler {
public:
  // Initialize command handlers and register them with the terminal
  static void init(SerialTerminal& term, PID& pid, int16_t& baseSpeed, LoggingFlags& flags);
  
  // Get logging flags (for external access)
  static LoggingFlags& getLoggingFlags() { return *loggingFlagsPtr; }

private:
  // Command handler functions
  static void cmdPid(void);
  static void cmdMotor(void);
  static void cmdLog(void);
  static void cmdHelp(void);
  static void unknownCommand(const char *command);
  
  // Static references to shared objects
  static SerialTerminal* termPtr;
  static PID* pidPtr;
  static int16_t* baseSpeedPtr;
  static LoggingFlags* loggingFlagsPtr;
};

#endif /* COMMAND_H */

