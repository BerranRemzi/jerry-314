#include <Arduino.h>
#include "BigLoop.h"
#include "Jerry.h"
#include "PID.h"
#include <IRremote.h>

BigLoop Task_100ms(100u);
BigLoop Task_10ms(20u);

//Specify the links and initial tuning parameters
double Kp=2.0, Ki=0.0, Kd=5.0;
PID pidController(Kp, Ki, Kd);


int16_t baseSpeed = 70;
double motorSpeed=0;
uint16_t line=0;

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
            if (IrReceiver.decodedIRData.command == 0x16) {
                Serial.println(F("Received command 0x10."));
                // do something
                Jerry_motorEnable(); // Enable motors when button 1 is pressed
                digitalWrite(LED_BUILTIN, HIGH); // Turn on built-in LED
            } else if (IrReceiver.decodedIRData.command == 0x19) {
                Serial.println(F("Received command 0x11."));
                // do something else
                Jerry_motorDisable(); // Disable motors when button 2 is pressed
                digitalWrite(LED_BUILTIN, LOW); // Turn off built-in LED
            }
        }
    }
}

void setup()
{
  // put your setup code here, to run once:
  Serial.begin(9600); // Initialize serial communication at 9600 baud
  Jerry_Init();
  Jerry_setSpeed(0, 0); // Set speed for both motors
  Jerry_setMaxSpeed(100); // Limit maximum speed to 150

  // Optional: set output limits
  pidController.setOutputLimits(-255, 255);
  // Start the receiver and if not 3. parameter specified, take LED_BUILTIN pin from the internal boards definition as default feedback LED
    IrReceiver.begin(IR_RECEIVE_PIN);
}

void loop()
{
  IR_Task(); // Handle IR receiving
  if(Task_10ms.shouldExecuteTask())
  {
    //digitalWrite(LED_BUILTIN, HIGH);   // turn the LED on (HIGH is the voltage level)
    
    // 10ms tasks can be added here if needed
    line = Jerry_lineRead(); // Read line sensor values
    motorSpeed = pidController.compute((double)line);
    Jerry_setSpeed(baseSpeed - (int)motorSpeed, baseSpeed + (int)motorSpeed); // Adjust motor speeds based on PID output
    
    //digitalWrite(LED_BUILTIN, LOW);    // turn the LED off by making the voltage LOW
  }

  if (Task_100ms.shouldExecuteTask())
  {
    char buffer[64]; // Increased buffer size for safety
    snprintf(buffer, sizeof(buffer), "L:%3d O:%3d\n", line, (int)motorSpeed);
    Serial.print(buffer); // Send line position and PID output over serial

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
