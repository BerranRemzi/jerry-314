#include "Command.h"
#include <string.h>

// Static member definitions
SerialTerminal* CommandHandler::termPtr = nullptr;
PID* CommandHandler::pidPtr = nullptr;
int16_t* CommandHandler::baseSpeedPtr = nullptr;
LoggingFlags* CommandHandler::loggingFlagsPtr = nullptr;

// Initialize command handlers
void CommandHandler::init(SerialTerminal& term, PID& pid, int16_t& baseSpeed, LoggingFlags& flags) {
  // Store references
  termPtr = &term;
  pidPtr = &pid;
  baseSpeedPtr = &baseSpeed;
  loggingFlagsPtr = &flags;
  
  // Set default handler for unknown commands
  term.setDefaultHandler(unknownCommand);
  
  // Add command callbacks
  term.addCommand("?", cmdHelp);
  term.addCommand("help", cmdHelp);
  term.addCommand("bootloader", cmdBootloader);
  
  // PID command
  term.addCommand("pid", cmdPid);
  
  // Motor command
  term.addCommand("motor", cmdMotor);
  
  // Logging command
  term.addCommand("log", cmdLog);
}

// PID command handler
void CommandHandler::cmdPid(void) {
  char *paramType = termPtr->getNext();
  if (paramType == NULL) {
    Serial.println(F("Usage: pid <p|i|d> <value> or pid <p|i|d> ?"));
    return;
  }
  
  char *valueStr = termPtr->getNext();
  if (valueStr == NULL) {
    Serial.println(F("Usage: pid <p|i|d> <value> or pid <p|i|d> ?"));
    return;
  }
  
  // Handle read or write
  if (strcmp(valueStr, "?") == 0) {
    // Read mode
    Serial.print(F("pid "));
    Serial.print(paramType);
    Serial.print(F(" "));
    switch (paramType[0]) {
      case 'p':
        Serial.println(pidPtr->getKp(), 3);
        break;
      case 'i':
        Serial.println(pidPtr->getKi(), 3);
        break;
      case 'd':
        Serial.println(pidPtr->getKd(), 3);
        break;
      default:
        Serial.println(F("Invalid parameter. Use: p, i, or d"));
        return;
    }
  } else {
    // Write mode
    double value = atof(valueStr);
    switch (paramType[0]) {
      case 'p':
        pidPtr->setKp(value);
        break;
      case 'i':
        pidPtr->setKi(value);
        break;
      case 'd':
        pidPtr->setKd(value);
        break;
      default:
        Serial.println(F("Invalid parameter. Use: p, i, or d"));
        return;
    }
  }
}

// Motor command handler
void CommandHandler::cmdMotor(void) {
  char *subcmd = termPtr->getNext();
  if (subcmd == NULL) {
    Serial.println(F("Usage: motor <speed|start|stop> [value|?]"));
    return;
  }
  
  if (strcmp(subcmd, "speed") == 0) {
    // Handle speed command
    char *valueStr = termPtr->getNext();
    if (valueStr == NULL) {
      Serial.println(F("Usage: motor speed <value> or motor speed ?"));
      return;
    }
    
    if (strcmp(valueStr, "?") == 0) {
      // Read mode
      Serial.print(F("motor speed "));
      Serial.println(*baseSpeedPtr);
    } else {
      // Write mode
      int value = atoi(valueStr);
      *baseSpeedPtr = value;
    }
  } else if (strcmp(subcmd, "start") == 0) {
    // Handle start command
    Jerry_motorEnable();
  } else if (strcmp(subcmd, "stop") == 0) {
    // Handle stop command
    Jerry_motorDisable();
  } else {
    Serial.println(F("Usage: motor <speed|start|stop> [value|?]"));
  }
}

// Logging command handler
void CommandHandler::cmdLog(void) {
  char *type = termPtr->getNext();
  if (type == NULL) {
    Serial.println(F("Usage: log <type> <on|off>"));
    Serial.println(F("Types: p, i, d, s, l, o"));
    return;
  }
  
  char *stateStr = termPtr->getNext();
  if (stateStr == NULL) {
    Serial.println(F("Usage: log <type> <on|off>"));
    return;
  }
  
  bool state = (strcmp(stateStr, "on") == 0);
  
  // Update appropriate flag
  switch (type[0]) {
    case 'p':
      loggingFlagsPtr->logP = state;
      break;
    case 'i':
      loggingFlagsPtr->logI = state;
      break;
    case 'd':
      loggingFlagsPtr->logD = state;
      break;
    case 's':
      loggingFlagsPtr->logS = state;
      break;
    case 'l':
      loggingFlagsPtr->logL = state;
      break;
    case 'o':
      loggingFlagsPtr->logO = state;
      break;
    default:
      Serial.println(F("Invalid log type. Use: p, i, d, s, l, o"));
      return;
  }
}

// Help command handler
void CommandHandler::cmdHelp(void) {
  Serial.println(F("Available commands:"));
  Serial.println(F("  help              - Print this help"));
  Serial.println(F("  bootloader        - Jump to bootloader"));
  Serial.println(F("  pid p <value>     - Set PID P coefficient"));
  Serial.println(F("  pid p ?           - Read PID P coefficient"));
  Serial.println(F("  pid i <value>     - Set PID I coefficient"));
  Serial.println(F("  pid i ?           - Read PID I coefficient"));
  Serial.println(F("  pid d <value>     - Set PID D coefficient"));
  Serial.println(F("  pid d ?           - Read PID D coefficient"));
  Serial.println(F("  motor speed <val> - Set motor speed"));
  Serial.println(F("  motor speed ?     - Read motor speed"));
  Serial.println(F("  motor start       - Start motor"));
  Serial.println(F("  motor stop        - Stop motor"));
  Serial.println(F("  log <type> <on|off> - Enable/disable logging"));
  Serial.println(F("    Types: p, i, d, s, l, o"));
}

// Unknown command handler
void CommandHandler::unknownCommand(const char *command) {
  Serial.print(F("Unknown command: "));
  Serial.println(command);
  Serial.println(F("Type 'help' for available commands"));
}

