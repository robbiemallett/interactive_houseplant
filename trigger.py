# A raspberry pi zero is connected via a relay to a 5V pump. 

import time
import datetime
from picamera import PiCamera
import RPi.GPIO as GPIO
import os
import pickle
from twython import Twython, TwythonError, TwythonStreamer

starting = 0 #this allows me to bypass the timer to test the system by watering more than once per hour

APP_KEY = "XX" #you'll need your own credentials for your account
APP_SECRET = 'XX'
OAUTH_TOKEN = 'XX'
OAUTH_TOKEN_SECRET = 'XX'

twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET) #creates an instance of twython API

# Search terms
TERMS = '@RobbiesPlantBot water yourself' #this is what the program scans twitter for - the magic words
#TERMS = 'twitter' #this is for testing, since the word twitter comes up all the time. 


def water(tweet_str, scr_name): #the function that waters the plant
    relay_pin = 23 #sets the pin that triggers the relay
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
    with open("/home/pi/Documents/plantvid.mp4", 'rb') as vid: #this "with open" section is quite buggy - be very careful
        response = twitter.upload_video(media=vid, media_type='video/mp4')
        print(response['media_id'])
        speech = str("@{} You helped me water myself at {}".format(scr_name, timerightnow))
        print(speech) 
        #had a nightmare working out this section, but it's easy to implement. The twython package needs a bit of an update. 
        #The module "endpoints.py" needs every mention of "StringIO" changed to "BytesIO" when used on a raspberry pi.
        #Nightmare because it works when testing on a windows comp, but needs changing for RPi!
        twitter.update_status(status=speech, media_ids=[response['media_id']], in_reply_to_status_id=tweet_str)
    pickle_out = open("timefile", "wb")
    print(timesaver)
    pickle.dump(timesaver, pickle_out)
    pickle_out.close
    starting = 0
    
#function for when it's too early to water again.
def nowater(tweet_str, scr_name, timefuture):
    speech = str("@{} I can't be watered more than once per hour. You can next water me at {} GMT".format(scr_name, timefuture))
    twitter.update_status(status=speech, in_reply_to_status_id=tweet_str)

#extremely ugly code to work out if the plant has been watered in the last hour. Truly awful and doesn't work well.
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
                timefuture = str("{}:{}".format(timenext[0], timenext[1])) #god forgive me for this line
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
