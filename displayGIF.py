# TODO: check MITERS status in a different thread

import sys

TK_GUI = False
GPIO = False
USE_MATRIX = True
EMULATE = False

WIDTH = 96
HEIGHT = 192
DELAY = 1 / 18
STOP_AFTER_DELAY = 30
MITERS_CHECK_DELAY_SEC = 5 * 60
MOVEX = 0.5
MOVEY = 0.1

if TK_GUI:
    try:
        from Tkinter import *
    except ImportError:
        from tkinter import *
    from PIL import ImageTk
from PIL import Image
import time
import random
from threading import Timer
import tweepy
import signal

# import keyboard

if USE_MATRIX:
    if EMULATE:
        from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    else:
        sys.path.append("/home/rpi-rgb-led-matrix/bindings/python")
        from rgbmatrix import RGBMatrix, RGBMatrixOptions

    print("Initializing matrix options")

    # Configuration for the matrix
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 32  # 64
    options.chain_length = 18  # 9
    options.multiplexing = 2  # weird wiring setup
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat-pwm"
    # custom pixel mapper must be written
    # options.pixel_mapper_config = "V-mapper:Z"
    options.pwm_bits = 11
    options.pwm_dither_bits = 2
    options.brightness = 25
    options.gpio_slowdown = 2
    options.scan_mode = 1
    options.show_refresh_rate = False  # True

    matrix = RGBMatrix(options=options)
    double_buffer = matrix.CreateFrameCanvas()

if GPIO:
    import RPi.GPIO as GPIO

    print("Initializing GPIO")

    PIR_PIN = 17
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIR_PIN, GPIO.IN)  # Read output from PIR motion sensor

    def signal_handler(sig, frame):
        GPIO.cleanup()

    def PIR_Callback(channel):
        global keep_running, stop_after
        keep_running = True
        if GPIO.input(PIR_PIN):  # rising edge
            stop_after = 0  # stay on permanently
        else:  # falling edge
            stop_after = time.time() + STOP_AFTER_DELAY  # stop after 30 seconds

    GPIO.add_event_detect(PIR_PIN, GPIO.BOTH, callback=PIR_Callback, bouncetime=100)
    signal.signal(signal.SIGINT, signal_handler)

# seed random number generator with current time
random.seed(time.time())

keep_running = True
if GPIO:
    stop_after = time.time() + 30
else:
    stop_after = 0

# init twitter API
print("Initializing Twitter API")
# read consumer API key, API key secret, Access token, Access token secret from tokens.txt
with open("tokens.txt", "r") as f:
    lines = f.readlines()
    consumer_key = lines[1].strip()
    consumer_secret = lines[4].strip()
    access_token = lines[10].strip()
    access_token_secret = lines[13].strip()

try:
    # OAuth process, using the keys and tokens
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    # Creation of the actual interface, using authentication
    api = tweepy.API(auth, wait_on_rate_limit=True)
    if not api.verify_credentials():
        raise tweepy.TweepError
except tweepy.TweepError as e:
    print("ERROR : connection failed. Check your OAuth keys.")
# else:
# print("Connected as @{}, you can start to tweet !".format(api.me().screen_name))
# client_id = api.me().id


class Tile:
    def __init__(self, frames, background=None):
        self.frames = frames
        self.animtimer = 0
        self.background = background

    def setBackground(self, background):
        self.background = background

    def appendframe(self, frame):
        self.frames.append(frame)

    def update(self):
        self.animtimer += 1
        if self.animtimer >= len(self.frames):
            self.animtimer = 0

    def draw(self, canvas, x, y):
        # paste the background onto the canvas at location x, y
        if self.background is not None:
            canvas.paste(self.background, (int(x), int(y)))
        # paste the frame on top of the background
        canvas.paste(
            self.frames[self.animtimer], (int(x), int(y)), self.frames[self.animtimer]
        )


miters_status = False  # True = open, false = closed
# launch a thread to check the status of MITERS every five minutes
def check_miters():
    # print("attempting tweet check")
    global miters_status
    # Get the latest tweet and print its text
    latest_tweets = api.user_timeline(screen_name="MITERS_door2", count=1)
    t = latest_tweets[0].text
    print(t)
    miters_status = "open" in t


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


miters_thread = RepeatTimer(MITERS_CHECK_DELAY_SEC, check_miters)
miters_thread.start()

# create a subclass of Tile called Miters_Tile
# overload the draw method to draw frame[0] if self.open is True and frame[1] if self.open is False
class Miters_Tile(Tile):
    def __init__(self, frames, background=None):
        Tile.__init__(self, frames, background)

    def draw(self, canvas, x, y):
        if self.background is not None:
            canvas.paste(self.background, (int(x), int(y)))
        if miters_status:
            canvas.paste(self.frames[0], (int(x), int(y)), self.frames[0])
        else:
            canvas.paste(self.frames[1], (int(x), int(y)), self.frames[1])


# tile grid class
# holds a 2x3 array of tiles and fills it using createTile on init
# has an update function which runs once each main loop
class TileGrid:
    def __init__(self):
        self.startcoord = [0, 0]
        self.tiles = [
            [
                createTile(),
                createTile(),
                createTile(),
            ],
            [
                createTile(),
                createTile(),
                createTile(),
            ],
        ]
        self.startcoord = [0, 0]

    def draw(self, canvas):
        # go through all of the tiles in self.tiles and draw them on the canvas
        for x in range(2):
            for y in range(3):
                self.tiles[x][y].draw(
                    canvas, self.startcoord[0] + x * 100, self.startcoord[1] + y * 100
                )

    def update(self):
        self.startcoord[0] += MOVEX
        self.startcoord[1] += MOVEY

        for x in range(2):
            for y in range(3):
                self.tiles[x][y].update()

        if self.startcoord[0] <= -100:  # x is offscreen, shift everything left
            self.startcoord[0] = 0
            for y in range(3):
                self.tiles[0][y] = self.tiles[1][y]
                self.tiles[1][y] = createTile()
        elif self.startcoord[0] >= 0:  # x is offscreen, shift everything right
            self.startcoord[0] = -100
            for y in range(3):
                self.tiles[1][y] = self.tiles[0][y]
                self.tiles[0][y] = createTile()

        if self.startcoord[1] <= -100:  # y is offscreen, shift everything up
            self.startcoord[1] = 0
            for x in range(2):
                self.tiles[x][0] = self.tiles[x][1]
                self.tiles[x][1] = self.tiles[x][2]
                self.tiles[x][2] = createTile()
        elif self.startcoord[1] >= 0:  # y is offscreen, shift everything down
            self.startcoord[1] = -100
            for x in range(2):
                self.tiles[x][2] = self.tiles[x][1]
                self.tiles[x][1] = self.tiles[x][0]
                self.tiles[x][0] = createTile()


# import a GIF image
# assert that the dimensions of the GIF are multiples of 100
# split the image into 100 by 100 pixel squares
# extract frames from the GIF image
# put the frames in an array and return the array
def importpicture(filename):
    im = Image.open(filename, "r")
    width, height = im.size
    assert width % 100 == 0, "width not multiple of 100"
    assert height % 100 == 0, "height not multiple of 100"

    # background = Image.new("RGB", (width, height), (100, 100, 100))

    # extract frames before splitting into chunkframes
    frames = []
    try:
        i = 0
        while 1:
            # tobeadded = background.copy()
            # tobepasted = im.copy().convert("RGBA")
            # tobeadded.paste(tobepasted, (0, 0), tobepasted)
            # frames.append(tobeadded)

            # replace all the black in tobepasted with white
            # tobepasted.paste((255, 255, 255, 255), (0, 0, width, height), tobepasted)
            # frames.append(tobepasted)

            frames.append(im.copy().convert("RGBA"))

            # frame
            i += 1
            im.seek(i)  # skip to next frame
    except EOFError:
        pass  # we're done

    chunks = []

    for i in range(width // 100):
        for j in range(height // 100):
            chunkframes = []
            # split the frame into 100 by 100 pixel squares
            box = (i * 100, j * 100, (i + 1) * 100, (j + 1) * 100)
            for frame in frames:
                chunkframes.append(frame.crop(box))

            chunks.append(chunkframes)
            # make a new tile?

    return chunks


# assert that the file has dimensions divisible by 100
# split the file into 100 by 100 pixel squares
# put the squares in an array and return it
def splitbackground(filename):
    im = Image.open(filename, "r")
    width, height = im.size
    assert width % 100 == 0, "width not multiple of 100"
    assert height % 100 == 0, "height not multiple of 100"

    tiles = []

    for i in range(width // 100):
        for j in range(height // 100):
            box = (i * 100, j * 100, (i + 1) * 100, (j + 1) * 100)
            tiles.append(im.crop(box))

    return tiles


print("Importing GIFs")
gif1frames = importpicture("BlueBallMachine.gif")
gif2frames = importpicture("BlueBallMachine2.gif")
gif3frames = importpicture("BlueBallMachine3.gif")

backgrounds = splitbackground("Background.png")

frames = gif1frames + gif2frames + gif3frames

miters_frames = [Image.open("open.png", "r"), Image.open("closed.png", "r")]

go_to_bed = Image.open("GoToBed.png", "r")


def createTile():
    r = random.random()
    t = time.localtime()
    # choose a random background from backgrounds
    background = backgrounds[int(r * len(backgrounds))]

    if t.tm_hour < 7:  # before 7 AM
        # cutoff is a number increasing from 0 to 0.25 based on the number of hours after 1AM until 6AM
        cutoff = max(0, min((t.tm_hour - 1) / 5 * 0.25, 0.25))
        if r < cutoff:
            return Tile([go_to_bed], background)

    r = random.random()

    if r < 0.05:  # 5% chance of Miters_Tile
        return Miters_Tile(miters_frames, background)
    else:
        i = random.randint(0, len(frames) - 1)
        return Tile(frames[i], background)


# source is a PIL image WIDTH by HEIGHT, dest is a PIL image 32 by 576 (32*18)
# split source into 32 by 32 chunks and paste each chunk sequentially into dest
def remapImage(source, dest):
    # each element of the array is the filling order index. negative means rotate image 180
    # each element in fillingorder represents a 32x32 chunk of the image

    # 0  -3  4
    # 1  -2  5
    # 10 -9  6
    # 11 -8  7
    # 12 -15 16
    # 13 -14 17

    fillingOrder = [
        [1, 11, 0, 10, 13, 12],
        [-2, -3, -8, -9, -14, -15],
        [5, 4, 6, 17, 7, 16],
    ]

    # traverse through each element in fillingOrder
    for x in range(3):
        for y in range(6):
            i = fillingOrder[x][y]
            box = (x * 32, y * 32, (x + 1) * 32, (y + 1) * 32)
            toadd = source.crop(box)
            if i < 0:
                dest.paste(toadd.rotate(90), (-i * 32, 0))
            else:
                dest.paste(toadd.rotate(-90), (i * 32, 0))


# this is the image that eventually gets drawn to the matrix
image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

if TK_GUI:
    global root
    print("Initializing Tkinter")
    root = Tk()
    root.title("Blue Ball Machine")

    def on_closing():
        root.quit()
        root.destroy()
        stop()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    lbl = Label(root, image=ImageTk.PhotoImage(image))
    lbl.pack()

    root.update()

t = TileGrid()

outer_loop = True


def stop():
    print("Shutting down")
    global keep_running
    keep_running = False
    if GPIO:
        signal_handler()

    miters_thread.cancel()
    global outer_loop
    outer_loop = False
    # keyboard.unhook_all()
    # sys.exit(0)


# keyboard.on_press_key("esc", lambda _: stop())

testImage = Image.open("test.png", "r")

print("Entering main loop")
while outer_loop:
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    matrixImage = Image.new("RGB", (32 * 18, 32), (0, 0, 0))
    if USE_MATRIX:
        matrix.Clear()

    while keep_running:
        # measure the time that the main loop took to complete
        start = time.time()

        t.draw(image)
        t.update()

        # image.show()
        remapImage(testImage, matrixImage)
        # remapImage(image, matrixImage)

        if USE_MATRIX:
            double_buffer.SetImage(matrixImage)
            double_buffer = matrix.SwapOnVSync(double_buffer)

        if TK_GUI and keep_running:
            i = ImageTk.PhotoImage(image)
            # i = ImageTk.PhotoImage(matrixImage)
            lbl.configure(image=i)
            lbl.image = i
            root.update()

        # measure the time that the main loop took to complete
        end = time.time()
        dt = end - start
        if dt < DELAY:
            time.sleep(DELAY - dt)
        if stop_after > 0 and end > stop_after:
            keep_running = False
