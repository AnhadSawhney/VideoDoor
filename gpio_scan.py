import RPi.GPIO as GPIO
import time

# try and set every GPIO pin to input
# if an exception is caught, print the pin number

GPIO.setmode(GPIO.BOARD)


def setupPins():
    for i in range(1, 40):
        try:
            GPIO.setup(i, GPIO.IN)
        except:
            print("Bad pin: " + str(i))

    for i in range(1, 40):
        print(i, end=" ")
    print("")


# go through every pin and print the pin number and the value
# if an exception is caught, ignore it
def scanPins():
    for i in range(1, 40):
        try:
            print(GPIO.input(i), end=" ")
        except:
            print("x ")
    print("")


setupPins()

while True:
    scanPins()
    time.sleep(0.1)
