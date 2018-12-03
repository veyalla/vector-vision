#!/usr/bin/env python3

# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wait for Vector to hear "Hey Vector!" and then play an animation.

The wake_word event only is dispatched when the SDK program has
not requested behavior control. After the robot hears "Hey Vector!"
and the event is received, you can then request behavior control
and control the robot. See the 'requires_behavior_control' method in
connection.py for more information.
"""

import sys
import time
import io
import os
import json
import requests
import threading
import logging
import anki_vector
from anki_vector.events import Events
from anki_vector.util import degrees

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

pic_number = 0
reboot_counter = 0
retry_counter = 0
wake_word_heard = False
wake_word_processing = False
url = os.environ['CSURL']


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, enable_camera_feed=True, requires_behavior_control=False, cache_animation_list=False) as robot:
        evt = threading.Event()

        def post_to_cognitive_services(): 
            global pic_number
            global url
            image = robot.camera.latest_image
            if image is None:
                print("Image acquisition error!")
                return
                #await robot.say_text("Something's got in my eye, please reboot me!")
                #await robot.conn.release_control()

            image.save('/sdk/' + str(pic_number) + '.jpg', 'JPEG')
            pic_number+=1
            imgByteArr = io.BytesIO()
            image.save(imgByteArr, format='JPEG')
            imgByteArr.seek(0)

            #image = image.resize((184, 96), Image.ANTIALIAS)
            #print("Display image on Vector's face...")
            #screen_data = anki_vector.screen.convert_image_to_screen_data(image)
            #robot.screen.set_screen_with_image_data(screen_data, 4.0)

            vision_base_url = url
            text_recognition_url = vision_base_url + "recognizeTextDirect"
            params = {'mode': 'printed'}
            data = {'form': ('jpegfile', imgByteArr, 'image/jpeg')}
            response = requests.post(text_recognition_url,  params=params, files=data) 
            response.raise_for_status()

            analysis = json.loads(response.text)
            print(json.dumps(analysis, indent=4, sort_keys=True))
            if len(analysis['lines']) != 0:
                return analysis

        async def my_coroutine():
            global retry_counter
            global wake_word_processing
            print("Running my_coroutine on the connection thread")
            # Connection request sometimes fails.
            #
            for attempt in range(2): 
                try:
                    robot.conn.CONTROL_PRIORITY_LEVEL = 20
                    await robot.conn.request_control(timeout=1.0)
                except:
                    #await robot.conn.release_control()
                    robot.events.unsubscribe(on_wake_word, Events.wake_word)
                    robot.events.subscribe(on_wake_word, Events.wake_word)
                    wake_word_processing = False
                    return

                else:
                    print ("Connected on attempt #", attempt)
                    break
            '''
            else:
                await robot.conn.release_control()
                print ("Unable to get control!")
                wake_word_processing = False 
                return
            '''

            #reboot_counter = 0 
            retry_counter += 1
            analysis = post_to_cognitive_services()
            if not analysis or len(analysis['lines']) == 0:
                if retry_counter < 3: 
                    await robot.conn.release_control()
                    robot.conn.run_soon(my_coroutine())
                    return;
                await robot.say_text("sorry, I didn't get that!")
            else:
                print("Number of lines: ", len(analysis['lines']))
                for i in range(len(analysis['lines'])):
                    await robot.say_text(analysis['lines'][i]['text'])

            await robot.conn.release_control()
            retry_counter = 0
            wake_word_processing = False
            return

        async def on_wake_word(event_type, event):
            global wake_word_processing
            if not wake_word_processing:     
                wake_word_processing = True
                print("Callback invoked...")
                robot.conn.request_control()
                robot.behavior.set_head_angle(degrees(25.0))
                robot.behavior.set_lift_height(0.0)
                time.sleep(1)
                robot.conn.run_soon(my_coroutine())
            return
            
        '''
        async def on_wake_word(event_type, event):
            global wake_word_heard
            global reboot_counter
            if not wake_word_heard:
                #reboot_counter+=1
                print("Callback invoked...")
                wake_word_heard = True
                robot.conn.run_soon(my_coroutine())

            wake_word_heard = False
        '''

        #evt.set()
        #robot.conn.request_control()
        #robot.behavior.set_lift_height(0.5, duration=0.5)
        #robot.behavior.set_lift_height(1.0, duration=0.7)
        #robot.behavior.set_lift_height(0.0, duration=0.0)
        #robot.conn.release_control()

        robot.events.subscribe(on_wake_word, Events.wake_word)

        print('------ Vector is waiting to hear "Hey Vector!" Press ctrl+c to exit early ------', file=sys.stderr)

        try:
            if not evt.wait(timeout=1000000):
                print('------ Vector never heard "Hey Vector!" ------')

        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
