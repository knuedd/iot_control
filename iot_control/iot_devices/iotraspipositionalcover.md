# Raspi positional cover

This is an IOT device for a positional cover where the positions can be set to a number between 0 and 100 or OPEN (same as 100) or CLOSED (same as 0).

## Pins

This type of cover aims to control a servo motor through 4 GPIO pins. In the setup.yaml one needs to specify the maximum number of rotations from fully closed position (value 0) to to fully open position as a global value for all covers in this agent:

    position_open: 1600 

and the motos pins in correct order per cover:

    motorpins:
        - 12
        - 16
        - 20
        - 21
