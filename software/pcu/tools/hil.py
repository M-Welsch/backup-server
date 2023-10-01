#!/usr/bin/python3

import serial


def main():
    with serial.Serial("/dev/ttyACM1", baudrate=115200) as ser:
        ser.write(b"led_on\n\r")


if __name__ == "__main__":
    main()
