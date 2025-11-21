#include "IR.h"
#include "Jerry.h"
#include "Motor.h"
#include <IRremote.hpp>
#include <Arduino.h>

static IRCommandCallback commandCallback = nullptr;

void IR_Init(void) {
    IrReceiver.begin(IR_RECEIVE_PIN);
}

void IR_Update(void) {
    if (IrReceiver.decode()) {
        if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
            IrReceiver.resume();
        } else {
            IrReceiver.resume();
            
            // Only process non-repeat commands
            if (!(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
                uint8_t command = IrReceiver.decodedIRData.command;
                Serial.println(command, HEX);
                
                // Call callback if set
                if (commandCallback != nullptr) {
                    commandCallback(command);
                }
            } else {
                Serial.println(F("Repeat received. Here you can repeat the same action as before."));
            }
        }
    }
}

void IR_SetCommandCallback(IRCommandCallback callback) {
    commandCallback = callback;
}

