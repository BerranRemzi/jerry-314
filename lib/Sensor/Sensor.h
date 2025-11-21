#ifndef SENSOR_H
#define SENSOR_H
#include "stdint.h"

int16_t Sensor_readBlack(void);
void Sensor_getSensorValues(char * output);
void Sensor_setEdgeDiffThreshold(uint16_t threshold);
uint16_t Sensor_getEdgeDiffThreshold(void);

#endif /* SENSOR_H */

