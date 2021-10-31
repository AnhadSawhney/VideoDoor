# VideoDoor
 
Generates a constantly scrolling image animation of the blue ball machine.
Procedurally generates new tiles and seamlessly animates them across the screen.

Also generates custom tiles to check the open status of the MITERS makerspace and to tell people to go to bed.

Python dependencies: (`pip install` these)
`pillow` (PIL)
`tweepy`
`RGBMatrixEmulator` (when `EMULATE = True`)
https://github.com/hzeller/rpi-rgb-led-matrix (when `EMULATE = False`)
Tkinter/tk (when `TK_GUI = True`)
`Rpi.GPIO` (when `GPIO = True`)

Installation:
Clone this repository, this creates a folder videoDoor
In the same folder as videodoor, clone rpi-rgb-led-matrix and build it for python
Folder structure should look like this:
``` 
Some_Folder
├── VideoDoor
└── rpi-rb-led-matrix
```

Running at boot:
Open root's crontab with `sudo crontab -e`
Put this in `@reboot cd /home/VideoDoor && python3 displayGIF.py >> /var/log/mail.log 2>&1`

Hardware:
Adafruit LED Matrix Shield with PWM Mod
PIR sensor wired to BCM Pin 24

Running:
`python3 displayGIF.py`

For the twitter integration to work you must generate and add your own tokens and put them in `tokens.txt`.
Sign up for a twitter developer account, make a new app and copy paste the tokens into a text file called `tokens.txt`.

`tokens.txt` format:

```
API Key
<paste key here>

API Key Secret
<paste key here>

Bearer Token
<paste key here>

Access Token
<paste key here>

Access Token Secret
<paste key here>
```
