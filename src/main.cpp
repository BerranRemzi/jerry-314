#include <Arduino.h>
#include "BigLoop.h"
#include "Jerry.h"
#include "Sensor.h"
#include "Motor.h"
#include "PID.h"
#include "Command.h"
#include "IR.h"
#include "Button.h"
#include "Logger.h"
#include <ErriezSerialTerminal.h>

// Task schedulers
BigLoop Task_100ms(100u);
BigLoop Task_10ms(10u);

// PID controller with initial tuning parameters
double Kp = 1.0, Ki = 0.0, Kd = 5.0;
PID pidController(Kp, Ki, Kd);

// Serial terminal for command interface
SerialTerminal term('\n', ' ');

// Control variables (kept in main as requested)
int16_t baseSpeed = 20;
int16_t motorSpeed = 0;
int16_t line = 0;

// Logging flags - default: sensor, line, and output enabled
LoggingFlags loggingFlags = {false, false, false, true, true, true};

// IR command handler - handles IR remote commands
bool handleIRCommand(uint8_t command) {
    switch(command) {
        case 0x52: // Stop
            Motor_disable();
            return true;
        case 0x19: // Speed 0
            Motor_enable();
            baseSpeed = 0;
            return true;
        case 0x16: // Speed 25
            Motor_enable();
            baseSpeed = 25;
            return true;
        case 0x0D: // Speed 50
            Motor_enable();
            baseSpeed = 50;
            return true;
        case 0x0C: // Speed 75
            Motor_enable();
            baseSpeed = 75;
            return true;
        case 0x18: // Speed 100
            Motor_enable();
            baseSpeed = 100;
            return true;
        case 0x5E: // Reserved
            return true;
        default:
            Serial.println(F("Unknown command received."));
            return false;
    }
}

// Button press handler
void handleButtonPress(ButtonID_t button) {
    switch(button) {
        case BUTTON_1:
            Serial.println("Button 1 pressed");
            Motor_enable();
            break;
        case BUTTON_2:
            Serial.println("Button 2 pressed");
            Motor_disable();
            break;
        case BUTTON_3:
            // Button 3 not used yet
            break;
        default:
            break;
    }
}


void setup()
{
  // Initialize serial communication
  Serial.begin(115200);
  
  // Initialize hardware
  Jerry_Init();
  IR_Init();
  Button_Init();
  
  // Initialize control system
  pidController.setOutputLimits(-255, 255);
  
  // Initialize subsystems
  IR_SetCommandCallback(handleIRCommand);
  Button_SetPressCallback(handleButtonPress);
  Logger_Init(loggingFlags);
  CommandHandler::init(term, pidController, baseSpeed, loggingFlags);
  
  // Start with motors disabled
  Motor_disable();
}

void loop()
{
  // Handle IR input
  IR_Update();
  
  // Handle serial commands
  term.readSerial();
  
  // 10ms control loop - KEEP IN LOOP AS REQUESTED
  if(Task_10ms.shouldExecuteTask())
  {
    // Read sensor
    line = Sensor_readBlack();
    
    // Compute PID
    motorSpeed = (int16_t)pidController.compute((double)line);
    
    // Set motor speeds
    Motor_setSpeed(baseSpeed - (int)motorSpeed, baseSpeed + (int)motorSpeed);
    
    // Logging (using Logger module)
    Logger_LogSensor();
    Logger_LogLine(line);
    Logger_LogOutput(motorSpeed);
    Logger_LogPID(pidController.getKp(), pidController.getKi(), pidController.getKd());
  }

  // 100ms tasks
  if (Task_100ms.shouldExecuteTask())
  {
    // Update button states (handles edge detection and callbacks)
    Button_Update();
  }
}
