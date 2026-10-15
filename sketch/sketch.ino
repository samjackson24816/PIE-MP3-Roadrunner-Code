#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include <Arduino_RouterBridge.h> // Ensure the library is correctly included

Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Corresponds to M1 and M2 on the shield
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

// Set to -1 if a motor is wired backwards physically
const int LEFT_MOTOR_DIR = -1;
const int RIGHT_MOTOR_DIR = 1; 

const int SCAN_SPEED = 30;
const int HUNT_BASE_SPEED = 50;

// control the motors with speed from -255 to 255
void setMotors(int leftRaw, int rightRaw) {
    int lSpeed = constrain(leftRaw, -255, 255) * LEFT_MOTOR_DIR;
    int rSpeed = constrain(rightRaw, -255, 255) * RIGHT_MOTOR_DIR;

    leftMotor->setSpeed(abs(lSpeed));
    rightMotor->setSpeed(abs(rSpeed));

    leftMotor->run(lSpeed >= 0 ? FORWARD : BACKWARD);
    rightMotor->run(rSpeed >= 0 ? FORWARD : BACKWARD);
}

// Callback functions for RouterBridge methods
void onSetMotors(int leftRaw, int rightRaw) {
    setMotors(leftRaw, rightRaw);
}

void onScan() {
    Serial.println("Arduino is scanning");
    setMotors(SCAN_SPEED, -SCAN_SPEED);
}

void onHunt(float delta) {
    Serial.print("Arduino is hunting with delta: ");
    Serial.println(delta);

    // Simple turning logic
    int lSpeed = HUNT_BASE_SPEED + (int)delta;
    int rSpeed = HUNT_BASE_SPEED - (int)delta;

    setMotors(lSpeed, rSpeed);
}

void onStop() {
    Serial.println("Arduino is stopping");

    leftMotor->setSpeed(0);
    rightMotor->setSpeed(0);
    leftMotor->run(RELEASE);
    rightMotor->run(RELEASE);
}

void setup() {
    Serial.begin(9600);

    Serial.println("Arduino is starting up and initializing connection");

    // Connect coms with linux computer
    Bridge.begin();

    // Initialize the motor shield
    if (!AFMS.begin()) {
        Serial.println("Could not find Motor Shield");

        // Pause until things are fixed and reset
        while (1);
    }
    Serial.println("Motor Shield found.");

    // Set initial stopped state
    onStop();

    // Provide methods for Python MPU
    Bridge.provide("set_motors", onSetMotors);
    Bridge.provide("scan", onScan);
    Bridge.provide("hunt", onHunt);
    Bridge.provide("stop", onStop);
}

void loop() {
    // Delay for stability
    delay(100);
}
