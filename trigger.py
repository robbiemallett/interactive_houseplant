import time
import datetime
from picamera import PiCamera
import RPi.GPIO as GPIO
import os
import pickle
from twython import Twython, TwythonError, TwythonStreamer
starting = 0
timelast = datetime.datetime.now()
timelast = timelast.replace(day = timelast.day - 2)
timelast = timelast.replace(hour = timelast.hour - 2)

APP_KEY = "9wpgR7e0y4Gg6GLR1RDshn9fa"
APP_SECRET = 'Opgya3uigAwpNe0yJDbE8Daf6m5VNVvdFiNwxlZttqgCUjVlAt'
OAUTH_TOKEN = '1085612744244629505-CGqdAE3kKnYpo9wNGLwffedlKnqr7V'
OAUTH_TOKEN_SECRET = 'JmPsfcoQyi16hx1SHT0T9sNeBnSfA7R7PyeHoYcCZF9ym'

twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

# Search terms
TERMS = '@RobbiesPlantBot water yourself'
#TERMS = 'twitter'


def water(tweet_str, scr_name):
    relay_pin = 23
    camera = PiCamera()
    camera.start_preview()
    camera.start_recording('/home/pi/Documents/plantvid.h264')
    time.sleep(1)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(relay_pin, GPIO.OUT)
    GPIO.output(relay_pin, GPIO.HIGH)
    # set low
    timelast = datetime.datetime.now()
    GPIO.output(relay_pin, GPIO.LOW)
    time.sleep(2)
    # set high
    GPIO.output(relay_pin, GPIO.HIGH)
    time.sleep(2)
    camera.stop_recording()
    camera.stop_preview()
    os.system("MP4Box -add plantvid.h264 plantvid.mp4")
    time.sleep(3)
    timerightnow = datetime.datetime.now().strftime("%H:%M:%S")
    timesaver = datetime.datetime.now()
    os.system("rm plantvid.h264")
    with open("/home/pi/Documents/plantvid.mp4", 'rb') as vid:
        response = twitter.upload_video(media=vid, media_type='video/mp4')
        print(response['media_id'])
        speech = str("@{} You helped me water myself at {}".format(scr_name, timerightnow))
        print(speech)
        twitter.update_status(status=speech, media_ids=[response['media_id']], in_reply_to_status_id=tweet_str)
    pickle_out = open("timefile", "wb")
    print(timesaver)
    pickle.dump(timesaver, pickle_out)
    pickle_out.close
    starting = 0

def nowater(tweet_str, scr_name, timefuture):
    speech = str("@{} I can't be watered more than once per hour. You can next water me at {} GMT".format(scr_name, timefuture))
    twitter.update_status(status=speech, in_reply_to_status_id=tweet_str)

def timer():
    timenow = datetime.datetime.now()
    pickle_in = open("timefile", "rb")
    print("opened pickle file")
    timelast = pickle.load(pickle_in)
    print("loaded pickle file")
    daydiff = timenow.day - timelast.day
    hourdiff = timenow.hour - timelast.hour
    minutediff = timenow.minute < timelast.minute
    if hourdiff == 0:
        if daydiff == 0:
            print("time now: {}".format(timenow))
            print("last watered: {}".format(timelast))
            return False
        else:
            return True
    elif hourdiff == 1:
        if minutediff < 0:
            print("time now: {}".format(timenow))
            print("last watered: {}".format(timelast))
            return False
        else:
            return True
    else:
        return True

# Setup callbacks from Twython Streamer
class BlinkyStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            tweet_str = data['id_str']
            user = data['user']
            scr_name = user['screen_name']
            if starting == 1:
                print(data['text'].encode('utf-8'))
                water(tweet_str, scr_name)
            elif timer() == True:
                print(data['text'].encode('utf-8'))
                water(tweet_str, scr_name)
            elif timer() == False:
                print("Too Early")
                timenext = [(timelast.hour + 1), (timelast.minute)]
                if timenext[0] == 25:
                    timenext[0] = 0
                timefuture = str("{}:{}".format(timenext[0], timenext[1]))
                nowater(tweet_str, scr_name, timefuture)

    def on_error(self, status_code, data):
        print(status_code)


# Create streamer
try:
    stream = BlinkyStreamer(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    print('looking')
    stream.statuses.filter(track=TERMS)
except KeyboardInterrupt:
    GPIO.cleanup()
    print('interupt')