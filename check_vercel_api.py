import requests
import re

res = requests.get('https://luxury-hotel-booking-platform-main.vercel.app')
js_links = re.findall(r'assets/index-[a-zA-Z0-9_-]+\.js', res.text)
if js_links:
    js_url = 'https://luxury-hotel-booking-platform-main.vercel.app/' + js_links[0]
    js_res = requests.get(js_url)
    
    match = re.search(r'.{0,50}hasRoomConflict.{0,100}', js_res.text)
    if match:
        print('Snippet:', match.group(0))
    else:
        print('No snippet found')
