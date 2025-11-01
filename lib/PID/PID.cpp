#include "PID.h"

PID::PID(double kp, double ki, double kd) 
    : kp_(kp), ki_(ki), kd_(kd), 
      lastError_(0.0), integral_(0.0),
      outputMin_(0.0), outputMax_(0.0), 
      limitsEnabled_(false) {
}

PID::~PID() = default;

double PID::compute(double error) {
    // Integral term accumulation (with anti-windup)
    if (ki_ != 0.0) {
        integral_ += error;
        // Anti-windup: only accumulate integral if output hasn't saturated
        // This prevents integral from growing when output is limited
        if (limitsEnabled_) {
            double output_no_integral = kp_ * error + (error - lastError_) * kd_;
            if ((output_no_integral >= outputMax_ && integral_ > 0) || 
                (output_no_integral <= outputMin_ && integral_ < 0)) {
                integral_ -= error; // Undo accumulation if saturated
            }
        }
    }
    
    // Derivative term calculation
    // Based on the algorithm: derivate = (error - lastError) * KD
    double derivative = (error - lastError_) * kd_;
    
    // PID calculation: motorSpeed = KP * error + derivate
    // For full PID: motorSpeed = KP * error + KI * integral + KD * derivative
    double output = kp_ * error + ki_ * integral_ + derivative;
    
    // Apply output limits if enabled
    if (limitsEnabled_) {
        if (output > outputMax_) {
            output = outputMax_;
        } else if (output < outputMin_) {
            output = outputMin_;
        }
    }
    
    // Store error for next derivative calculation
    lastError_ = error;
    
    return output;
}

void PID::reset() {
    lastError_ = 0.0;
    integral_ = 0.0;
}

void PID::setKp(double kp) {
    kp_ = kp;
}

void PID::setKi(double ki) {
    ki_ = ki;
}

void PID::setKd(double kd) {
    kd_ = kd;
}

void PID::setOutputLimits(double min, double max) {
    outputMin_ = min;
    outputMax_ = max;
    limitsEnabled_ = true;
}

