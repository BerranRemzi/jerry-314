// BigLoop.h
#ifndef BIGLOOP_H
#define BIGLOOP_H

#include <Arduino.h>

class BigLoop
{
private:
    uint32_t intervalMs;        // Task interval in milliseconds
    uint32_t lastExecutionTime; // Timestamp of the last task execution

public:
    // Constructor
    BigLoop(uint32_t intervalMs)
        : intervalMs(intervalMs), lastExecutionTime(0) {}

    // Check if the task should be executed based on the interval
    bool shouldExecuteTask()
    {
        uint32_t currentTime = millis();
                if (currentTime - lastExecutionTime >= intervalMs)
        {
            // Increment by interval instead of setting to current time
            // to prevent drift accumulation over time
            lastExecutionTime += intervalMs;
            
            // If multiple intervals have passed (e.g., long blocking operation),
            // catch up to avoid sudden burst of executions
            if (currentTime - lastExecutionTime >= intervalMs)
            {
                lastExecutionTime = currentTime;
            }
            
            return true;
        }
        return false;
    }
};

#endif // BIGLOOP_H
