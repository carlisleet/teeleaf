from flask import Flask,render_template,request,session
import argparse
import datetime 
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import calendar
import chromedriver_binary


web = Flask(__name__)

chrome_options = Options()
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--headless")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

# Global static variables

v_website = 'https://www.yourgolfclub.com' # golf club website
v_loginurl = v_website+'/login.php' # login page
v_consenturl = v_website+'/ttbconsent.php?action=accept' # consent page
v_teetimesurl = v_website+'/memberbooking/?date=' #tee times url
v_bookingurl = v_website+'/memberbooking/' # booking url
v_editbookingurl = ''


'''
Players:

player1 = 000001
player2 = 000002
etc etc
'''

## Add you player ID's here, can be found in your member directory.
players = [
    '000001', '000002', '000003', '000004'
    ]

class teeOff(object):
    def __init__(self,time,tokenName,tokenValue):
        self.time = time
        self.tokenName = tokenName
        self.tokenValue = tokenValue

def login(username, pin):
    print('[+] Attempting to login')
    global teeOffList
    teeOffList = []
    global s
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'})
    global driver
    driver = webdriver.Chrome(options=chrome_options) 
    driver.get(v_loginurl)
    driver.find_element(By.ID, 'memberid').send_keys(username)
    driver.find_element(By.ID, 'pin').send_keys(pin)
    driver.find_element(By.NAME, 'Submit').click()
    driver.get(v_consenturl)
    html = driver.page_source
    if 'Thankyou for accepting the code of conduct' in html:
        print('[+] Sucessfully logged in')
        return True
    else:
        print('[!] Login failed')
        driver.quit()
        return False

def timeslot_gen(start_time,end_time,slot_time):
    print('[+] Generating timeslot')
    days = []
    hours = []
    time = datetime.datetime.strptime(start_time, '%H:%M')
    end = datetime.datetime.strptime(end_time, '%H:%M')
    while time <= end:
        hours.append(time.strftime("%H:%M:%S"))
        time += datetime.timedelta(minutes=slot_time)
    days.append(hours)

    for hours in days:
        return hours

# Scrapes the booking page for a required date, if teetimes not showing it will retry 100 times.
# If teetimes are available it scrapes the page for times, token_name and token_value pairs which are required to make a booking.

def get_tee_times(v_date, v_course):
    print('[+] Getting teetimes for '+v_course)
    i = 0
    limit = 2000
    print('[+] Brute forcing website for teetimes')
    while i < limit:
        driver.get(v_teetimesurl+v_date+v_course)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        hidden_tags = soup.find_all('input', type='hidden')
        if len(hidden_tags) < 10:
            i += 1
            continue
        else:
            break
    if len(hidden_tags) < 10:
        print('[!] Tried '+str(limit)+' times, giving up :-(')
        driver.quit()
        return False
    else:
        print('[+] Populating token database')
        flag = False
        for x in hidden_tags:
            if 'book' in str(x):
                tempTime = (x.attrs.get('value'))
                print(tempTime)
            if len(str(x)) >= 60:
                tempTokenName = (x.attrs.get('name'))
                tempTokenValue = (x.attrs.get('value'))
                flag = True
            if flag:
                teeOffList.append(teeOff(tempTime,tempTokenName,tempTokenValue))
                flag = False           
    return True

# Books teetime

def book_teetime(v_date, v_course, numslots, time, tokenName, tokenValue):
    cookies = driver.get_cookies()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])
    driver.quit()
    bookingurl = (v_bookingurl+'?numslots='+numslots+'&date='+v_date+v_course+'&book='+time+'&'+tokenName+'='+tokenValue)
    print('[+] Trying at '+str(time))
    response = s.get(bookingurl)
    if 'Not permitted' in response.text:
        print('[!] Currently not permiited to book teetime on '+v_date+' at '+str(time))
        return False
    if 'You already have a teetime booked for this day' in response.text:
        print('[!] You already have a teetime booked on this day!')
        return False
    if 'All slots are no longer available' in response.text:
        print('[!] Teetime unavailable at '+str(time))
        return False
    if 'Sorry, it appears your teetime has been booked whilst you were viewing the availble times' in response.text:
        print('[!] Teetime unavailable on '+v_date+' at '+str(time))
        return False
    if 'Sorry, there was an error in the request to make this booking.' in response.text:
        print('[!] Bad token')
        return False
    else:
        print('[+] Succesfully booked teetime on '+v_date+' at '+str(time))
        global v_editbookingurl
        v_editbookingurl = response.url
        return True

# Adds other players to the booking in slots 2-4

def add_players():
    slot = 2
    for player in players:
        editurl = (v_editbookingurl+'addpartner='+player+'&partnerslot='+str(slot))
        editurl = editurl.replace('newbooking=1', '')
        response = s.get(editurl)
        slot += 1

@web.route("/")
@web.route("/home")
@web.route("/teetimes")

def home():
    return render_template("index.html")

@web.route("/result", methods = ['POST', 'GET'])
def result():
    output = request.form.to_dict()
    memberid = output["memberid"]
    pin = output["pin"]
    date = output["date"]
    course = output["course"]
    numslots = output["numslots"]
    starttime = output["starttime"]
    endtime = output["endtime"]
    addplayers = False
    

    if output.get('addplayers'):
        addplayers_flag = True
        print('[+] Adding other players requested')
    else:
         addplayers_flag = False

    if login(memberid, pin):
        dateTemp = datetime.datetime.strptime(date, "%Y-%m-%d")
        weekday = calendar.day_name[dateTemp.weekday()]
        date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        
        print('[+] Selected date: '+str(date))
        preferredTimes = timeslot_gen(starttime, endtime, 10)
        if get_tee_times(date, course):
            print('[+] Teetimes available')
            while True:
                for time in preferredTimes:
                    for item in teeOffList:
                        if item.time == time:
                            if book_teetime(date, course, numslots, time, item.tokenName, item.tokenValue):
                                if addplayers_flag:
                                    print('[+] Now adding players to the booked teetime')
                                    add_players()
                                    time = time[:-3]
                                    booked = 'Teetime sucessfully booked on '+str(date)+' at '+str(time)
                                    s.close()
                                    return render_template("index.html", booked=booked)
                                else:
                                    time = time[:-3]
                                    booked = 'Teetime sucessfully booked on '+str(date)+' at '+str(time)
                                    s.close()
                                    return render_template("index.html", booked=booked)
                else:
                    print('[!] Preferred teetimes unavailable')
                    teetime_unavail = 'Preferred teetimes unavailable, try expanding your search.'
                    s.close()
                    return render_template("index.html", teetime_unavail=teetime_unavail)
        else:
            print('[!] No teetimes available')
            teetime_unavail = 'No teetimes available'
            s.close()
            return render_template("index.html", teetime_unavail=teetime_unavail)
    else:
        login_failed = 'Invalid login address or pin'
        return render_template("index.html", login_failed=login_failed)

if __name__ == '__main__':
    web.run(host='0.0.0.0',port=5001)
