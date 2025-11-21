#ifndef IR_H
#define IR_H

#include <stdint.h>

// IR command callback type - returns true if command was handled
typedef bool (*IRCommandCallback)(uint8_t command);

// Initialize IR receiver
void IR_Init(void);

// Update IR receiver (call in main loop)
void IR_Update(void);

// Set callback for IR commands
void IR_SetCommandCallback(IRCommandCallback callback);

#endif /* IR_H */

