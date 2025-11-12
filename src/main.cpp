#include <Arduino.h>
#include "BigLoop.h"
#include "Jerry.h"
#include "PID.h"
#include "Command.h"
#include <IRremote.hpp>
#include <ErriezSerialTerminal.h>

BigLoop Task_100ms(100u);
BigLoop Task_10ms(10u);

//Specify the links and initial tuning parameters
double Kp=1.0, Ki=0.0, Kd=5.0;
PID pidController(Kp, Ki, Kd);

// Newline character '\r' or '\n'
int8_t newlineChar = '\n';
// Separator character between commands and arguments
int8_t delimiterChar = ' ';

// Create serial terminal object
SerialTerminal term(newlineChar, delimiterChar);

int16_t baseSpeed = 20;
int16_t motorSpeed=0;
int16_t line = 0;

// Logging flags - default: sensor, line, and output enabled
LoggingFlags loggingFlags = {false, false, false, true, true, true};

void IR_Task()
{
  // IR handling code here
  if (IrReceiver.decode()) {

        /*
         * Print a summary of received data
         */
        if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
            //Serial.println(F("Received noise or an unknown (or not yet enabled) protocol"));
            // We have an unknown protocol here, print extended info
            //IrReceiver.printIRResultRawFormatted(&Serial, true);

            IrReceiver.resume(); // Do it here, to preserve raw data for printing with printIRResultRawFormatted()
        } else {
            IrReceiver.resume(); // Early enable receiving of the next IR frame

            //IrReceiver.printIRResultShort(&Serial);
            //IrReceiver.printIRSendUsage(&Serial);
        }
        //Serial.println();

        /*
         * Finally, check the received data and perform actions according to the received command
         */
        if (IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT) {
            Serial.println(F("Repeat received. Here you can repeat the same action as before."));
        } else {
            Serial.println(IrReceiver.decodedIRData.command, HEX);
            switch(IrReceiver.decodedIRData.command) {
              case 0x52: // Example command
                    // Action for command 0x52
                    Jerry_motorDisable(); // Disable motors when button 2 is pressed
                    break;
                case 0x19: // Example command
                    // Action for command 0x19
                    Jerry_motorEnable(); // Enable motors when button 1 is pressed
                    baseSpeed = 0; // Increase base speed
                    break;
                case 0x16: // Example command
                    // Action for command 0x16
                    Jerry_motorEnable(); // Enable motors when button 1 is pressed
                    baseSpeed = 25; // Increase base speed
                    break;
                case 0x0D: // Example command
                    // Action for command 0x0D
                    Jerry_motorEnable(); // Enable motors when button 1 is pressed
                    baseSpeed = 50; // Increase base speed
                    break;
                    case 0x0C: // Example command
                    // Action for command 0x0C
                    Jerry_motorEnable(); // Enable motors when button 1 is pressed
                    baseSpeed = 75; // Increase base speed
                    break;
                    case 0x18: // Example command
                    // Action for command 0x18
                    Jerry_motorEnable(); // Enable motors when button 1 is pressed
                    baseSpeed = 100; // Increase base speed
                    break;
                    case 0x5E: // Example command
                    // Action for command 0x5E
                    break;
                default:
                    Serial.println(F("Unknown command received.")); 
                    break;
            }
            
        }
    }
}


void setup()
{
  // put your setup code here, to run once:
  Serial.begin(115200); // Initialize serial communication at 9600 baud
  Jerry_Init();
  //Jerry_motorEnable(); // Enable motors when button 1 is pressed 
  //Jerry_setSpeed(-40, 40); // Set speed for both motors
  //delay(1000); // Wait for a second
  Jerry_motorDisable(); // Enable motors when button 1 is pressed 

  //Jerry_setMaxSpeed(100); // Limit maximum speed to 150

  // Optional: set output limits
  pidController.setOutputLimits(-255, 255);
  // Start the receiver and if not 3. parameter specified, take LED_BUILTIN pin from the internal boards definition as default feedback LED
    IrReceiver.begin(IR_RECEIVE_PIN);

  // Initialize command handlers (all command registration is handled in Command library)
  CommandHandler::init(term, pidController, baseSpeed, loggingFlags);
}

void loop()
{
  IR_Task(); // Handle IR receiving
  // Read from serial port and handle command callbacks
  term.readSerial();
  if(Task_10ms.shouldExecuteTask())
  {
    // 10ms tasks can be added here if needed
    line = Jerry_lineRead(); // Read line sensor values
    motorSpeed = (int16_t)pidController.compute((double)line);
    Jerry_setSpeed(baseSpeed - (int)motorSpeed, baseSpeed + (int)motorSpeed); // Adjust motor speeds based on PID output
    
    // Output data based on logging flags
    if (loggingFlags.logS) {
      char buffer[64];
      Jerry_getSensorValues(buffer);
      Serial.write(buffer);
    }
    if (loggingFlags.logL) {
      Serial.print("L,");
      Serial.println(line);
    }
    if (loggingFlags.logO) {
      Serial.print("O,");
      Serial.println(motorSpeed);
    }
    
    // Log PID values if enabled (less frequent, only when changed)
    static unsigned long lastPidLog = 0;
    if (millis() - lastPidLog > 100) { // Log PID values every 100ms max
      if (loggingFlags.logP) {
        Serial.print(F("pid p "));
        Serial.println(pidController.getKp(), 3);
      }
      if (loggingFlags.logI) {
        Serial.print(F("pid i "));
        Serial.println(pidController.getKi(), 3);
      }
      if (loggingFlags.logD) {
        Serial.print(F("pid d "));
        Serial.println(pidController.getKd(), 3);
      }
      lastPidLog = millis();
    }
 }

  if (Task_100ms.shouldExecuteTask())
  {
    //char buffer[64]; // Increased buffer size for safety
    //snprintf(buffer, sizeof(buffer), "L:%3d O:%3d\n", line, (int)motorSpeed);
    //Serial.print(buffer); // Send line position and PID output over serial

    // Button handling
    if(digitalRead(BTN_1_PIN) == LOW) {
      Serial.println("Button 1 pressed");
      Jerry_motorEnable(); // Enable motors when button 1 is pressed
    }

    if(digitalRead(BTN_2_PIN) == LOW) {
      Serial.println("Button 2 pressed");
      Jerry_motorDisable(); // Disable motors when button 2 is pressed
    }
  }
}
