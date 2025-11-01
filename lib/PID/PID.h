#ifndef PID_H
#define PID_H

#include <stdint.h>

class PID {
public:
    // Constructor
    PID(double kp, double ki, double kd);
    
    // Destructor
    ~PID();
    
    // Compute PID output based on error
    double compute(double error);
    
    // Reset the controller (clears integral and last error)
    void reset();
    
    // Set PID gains
    void setKp(double kp);
    void setKi(double ki);
    void setKd(double kd);
    
    // Set output limits
    void setOutputLimits(double min, double max);
    
    // Get current values
    double getKp() const { return kp_; }
    double getKi() const { return ki_; }
    double getKd() const { return kd_; }
    double getLastError() const { return lastError_; }
    double getIntegral() const { return integral_; }
    
private:
    double kp_;          // Proportional gain
    double ki_;          // Integral gain
    double kd_;          // Derivative gain
    
    double lastError_;   // Last error value for derivative calculation
    double integral_;    // Integral accumulator
    
    double outputMin_;   // Minimum output limit
    double outputMax_;   // Maximum output limit
    bool limitsEnabled_; // Flag to enable/disable output limits
};

#endif /* PID_H */

