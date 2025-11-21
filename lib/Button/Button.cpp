#include "Button.h"
#include "Jerry.h"
#include <Arduino.h>

static bool buttonState[BUTTON_COUNT] = {false, false, false};
static bool lastButtonState[BUTTON_COUNT] = {false, false, false};
static ButtonCallback pressCallback = nullptr;

// Map button IDs to pins
static const uint8_t buttonPins[BUTTON_COUNT] = {
    BTN_1_PIN,
    BTN_2_PIN,
    BTN_3_PIN
};

void Button_Init(void) {
    // Buttons are already initialized in Jerry_Init with INPUT_PULLUP
    // This function is here for future expansion
}

void Button_Update(void) {
    // Store previous state
    for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
        lastButtonState[i] = buttonState[i];
    }
    
    // Read current state (buttons are active LOW with pull-up)
    for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
        buttonState[i] = (digitalRead(buttonPins[i]) == LOW);
        
        // Trigger callback on edge detection
        if (buttonState[i] && !lastButtonState[i] && pressCallback != nullptr) {
            pressCallback((ButtonID_t)i);
        }
    }
}

bool Button_IsPressed(ButtonID_t button) {
    if (button >= BUTTON_COUNT) return false;
    return buttonState[button];
}

bool Button_IsPressedEdge(ButtonID_t button) {
    if (button >= BUTTON_COUNT) return false;
    return buttonState[button] && !lastButtonState[button];
}

void Button_SetPressCallback(ButtonCallback callback) {
    pressCallback = callback;
}

