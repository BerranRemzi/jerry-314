#ifndef BUTTON_H
#define BUTTON_H

#include <stdint.h>
#include <stdbool.h>

// Button IDs
typedef enum {
    BUTTON_1 = 0,
    BUTTON_2 = 1,
    BUTTON_3 = 2,
    BUTTON_COUNT = 3
} ButtonID_t;

// Button callback type
typedef void (*ButtonCallback)(ButtonID_t button);

// Initialize button subsystem
void Button_Init(void);

// Update button states (call periodically, e.g., every 100ms)
void Button_Update(void);

// Check if button is currently pressed
bool Button_IsPressed(ButtonID_t button);

// Check if button was just pressed (edge detection)
bool Button_IsPressedEdge(ButtonID_t button);

// Set callback for button press events
void Button_SetPressCallback(ButtonCallback callback);

#endif /* BUTTON_H */

