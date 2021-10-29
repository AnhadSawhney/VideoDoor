TK_GUI = True
GPIO = False
EMULATE = True

if TK_GUI:
    try:
        from Tkinter import *
    except ImportError:
        from tkinter import *
from PIL import Image, ImageTk
import time
import random

import tweepy
import signal

if EMULATE:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

if GPIO:
    import RPi.GPIO as GPIO

    PIR_PIN = 17
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIR_PIN, GPIO.IN)  # Read output from PIR motion sensor

    def signal_handler(sig, frame):
        GPIO.cleanup()
        # sys.exit(0)
        # pass

    def PIR_Callback(channel):
        global keep_running, stop_after
        keep_running = True
        if GPIO.input(PIR_PIN):  # rising edge
            stop_after = 0  # stay on permanently
        else:  # falling edge
            stop_after = time.time() + STOP_AFTER_DELAY  # stop after 30 seconds

    GPIO.add_event_detect(PIR_PIN, GPIO.BOTH, callback=PIR_Callback, bouncetime=100)
    signal.signal(signal.SIGINT, signal_handler)

WIDTH = 96
HEIGHT = 192
DELAY = 1 / 18
STOP_AFTER_DELAY = 30

# seed random number generator with current time
random.seed(time.time())

keep_running = True
if GPIO:
    stop_after = time.time() + 30
else:
    stop_after = 0

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 32
options.chain_length = 9
options.parallel = 1
options.hardware_mapping = "adafruit-hat"  # If you have an Adafruit HAT: 'adafruit-hat'
options.pixel_mapper_config = "Vmapper:Z"

matrix = RGBMatrix(options=options)

# init twitter API
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


# create a subclass of Tile called Miters_Tile
# overload the draw method to draw frame[0] if self.open is True and frame[1] if self.open is False
class Miters_Tile(Tile):
    def __init__(self, frames, background=None):
        Tile.__init__(self, frames, background)
        self.checkMitersStatus()

    # using the Tweepy library
    # get the text of the latest tweet from @MITERS_door2
    # if the text contains "open" set open to True
    # if the text contains "closed" set open to False
    def checkMitersStatus(self):
        # Get the latest tweet and print its text
        latest_tweets = api.user_timeline(screen_name="MITERS_door2", count=1)
        t = latest_tweets[0].text
        print(t)
        self.open = "open" in t

    def draw(self, canvas, x, y):
        if self.background is not None:
            canvas.paste(self.background, (int(x), int(y)))
        if self.open:
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
        self.startcoord[0] -= 1
        self.startcoord[1] -= 0.1

        for x in range(2):
            for y in range(3):
                self.tiles[x][y].update()

        if self.startcoord[0] <= -100:  # x is offscreen, shift everything left
            self.startcoord[0] = 0
            for y in range(3):
                self.tiles[0][y] = self.tiles[1][y]
                self.tiles[1][y] = createTile()

        if self.startcoord[1] <= -100:  # y is offscreen, shift everything up
            self.startcoord[1] = 0
            for x in range(2):
                self.tiles[x][0] = self.tiles[x][1]
                self.tiles[x][1] = self.tiles[x][2]
                self.tiles[x][2] = createTile()


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


gif1frames = importpicture("BlueBallMachine.gif")
# print(len(gif1frames))
# print(gif1frames)
gif2frames = importpicture("BlueBallMachine2.gif")
# print(len(gif2frames))
gif3frames = importpicture("BlueBallMachine3.gif")
# print(len(gif3frames))

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


# this is the image that eventually gets drawn to the matrix
image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

if TK_GUI:
    root = Tk()
    root.title("Blue Ball Machine")

    def on_closing():
        root.destroy()
        root.quit()
        global keep_running
        keep_running = False

    root.protocol("WM_DELETE_WINDOW", on_closing)

    lbl = Label(root, image=ImageTk.PhotoImage(image))
    lbl.pack()

    root.update()

t = TileGrid()

while True:
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    matrixImage = Image.new("RGB", (WIDTH * 3, HEIGHT // 3), (0, 0, 0))
    matrix.Clear()
    while keep_running:
        # measure the time that the main loop took to complete
        start = time.time()

        t.draw(image)
        t.update()

        # image.show()

        matrixImage.paste(image, (0, 0))
        matrixImage.paste(image, (WIDTH, -HEIGHT // 3))
        matrixImage.paste(image, (WIDTH * 2, -2 * HEIGHT // 3))

        matrix.SetImage(matrixImage)

        if TK_GUI and keep_running:
            i = ImageTk.PhotoImage(image)
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
