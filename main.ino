#include <Servo.h>

namespace {
constexpr size_t kServoCount = 4;
constexpr unsigned long kBaudRate = 9600;
constexpr unsigned long kCommandTimeoutMs = 1000;
constexpr uint8_t kServoPins[kServoCount] = {5, 6, 7, 8};
constexpr uint8_t kDefaultAngles[kServoCount] = {130, 90, 129, 110};

Servo servos[kServoCount];
uint8_t commandAngles[kServoCount] = {};
uint8_t currentAngles[kServoCount] = {};
unsigned long lastCommandAt = 0;

void applyAngles(const uint8_t angles[]) {
    for (size_t index = 0; index < kServoCount; ++index) {
        const uint8_t safeAngle = constrain(angles[index], 0, 180);
        if (safeAngle != currentAngles[index]) {
            servos[index].write(safeAngle);
            currentAngles[index] = safeAngle;
        }
    }
}
}  // namespace

void setup() {
    Serial.begin(kBaudRate);
    Serial.setTimeout(20);
    for (size_t index = 0; index < kServoCount; ++index) {
        servos[index].attach(kServoPins[index]);
    }
    applyAngles(kDefaultAngles);
    lastCommandAt = millis();
}

void loop() {
    if (Serial.available() >= static_cast<int>(kServoCount)) {
        const size_t bytesRead = Serial.readBytes(commandAngles, kServoCount);
        if (bytesRead == kServoCount) {
            applyAngles(commandAngles);
            lastCommandAt = millis();
        }
    }

    if (millis() - lastCommandAt > kCommandTimeoutMs) {
        applyAngles(kDefaultAngles);
    }
}
