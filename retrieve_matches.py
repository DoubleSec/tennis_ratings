# requires Chromedriver in same directory
# https://sites.google.com/a/chromium.org/chromedriver/downloads

from selenium import webdriver

import pandas as pd
import sqlite3

from datetime import date
import time

# Extremely crappy string cleaning for sql
def clean(string):
    return string.replace('"', '').replace("'", "").replace(';', '')
    
# if rank = UNR, replace with 999
def rankFix(rk):
    if rk == "UNR":
        return 999
    else:
        return int(rk)
    
# Converts rounds into integers, F = 1, goes down, format tentative
def parseRound(string):
    
    roundNames = { "BR" : 12,
                   "RR" : 11,
                   "Q1" : 10,
                   "Q2" : 9,
                   "Q3" : 8,
                   "R128" : 7,
                   "R64" : 6,
                   "R32" : 5,
                   "R16" : 4,
                   "QF" : 3,
                   "SF" : 2,
                   "F" : 1 }
                   
    return roundNames[string]
    
# Very bad method for determining winner: returns 1 if this player won, 0 if other player won
def parseResult(string):
    if string[-1] == ']':
        return 1
    else:
        return 0
    
# Get a date from the scraped stuff into a python date object
def parseDate(string):

    monthNums = { "Jan" : 1,
                  "Feb" : 2,
                  "Mar" : 3,
                  "Apr" : 4,
                  "May" : 5,
                  "Jun" : 6,
                  "Jul" : 7,
                  "Aug" : 8,
                  "Sep" : 9,
                  "Oct" : 10,
                  "Nov" : 11,
                  "Dec" : 12 }

    year = int(string[-4:])
    month = int(monthNums[string[-7:-4]])
    day = int(string[:-7])
    
    return date(year, month, day)

# Generate a (probably?) unique number for each match, for uh, stuff. Barf
def matchNumber(dt, rk, ork):
    return int(str(dt.year) + str(dt.month) + str(dt.day) + str(int(max(rk, ork))) + str(int(min(rk, ork))))

# Formats player name to replace spaces with underscores
def formatName(name):
    return name.replace(' ', '_')
    
# Writes table of player results for each player
def PlayerTable(c, driver, playerName):
    
    driver.find_element_by_id("tabResults").click()
    driver.find_element_by_id("spanCareerqq").click()
    
    # Create dataframe
    df1 = pd.read_html(driver.page_source.encode("ascii","ignore").decode(), match="Tournament", header=0)[-1]

    # Finds first row from 2014 (most recent 2014 match) and saves index
    first = 0

    for i in df1.itertuples():
        if "2014" in i.Date:
            first = i.Index
            break

    # Drop matches before start date (currently start of 2015)
    df1.drop(df1.index[first:], inplace=True)

    # Drop unused columnns
    df1.drop(['More', 'DR', 'A%', 'DF%', '1stIn', '1st%', '2nd%', 'BPSvd', 'Time'], axis=1, inplace=True)

    # Rename single unnamed column
    df1.rename(columns={list(df1)[6] : 'Result'}, inplace=True)
    
    df1.fillna(value=999, inplace=True)

    # Format name
    pName = formatName(playerName)
    
    # create table
    c.execute("CREATE TABLE {tn} ({n1} {t1}, {n2} {t2}, {n3} {t3}, {n4} {t4}, {n5} {t5}, {n6} {t6}, {n7} {t7}, {n8} {t8}, {n9} {t9});"\
             .format(tn=pName,
                     n1="Date", t1="DATE",
                     n2="Tournament", t2="TEXT",
                     n3="Surface", t3="TEXT",
                     n4="Round", t4="INTEGER",
                     n5="Rank", t5="INTEGER",
                     n6="OppRank", t6="INTEGER",
                     n7="Result", t7="INTEGER",
                     n8="Score", t8="TEXT",
                     n9="MatchNum", t9="INTEGER"))

    # Iterate through rows of dataframe, add entry for each one to sqlite database
    for i in df1.itertuples():

        pDate = parseDate(i.Date)
        rk = rankFix(i.Rk)
        vrk = rankFix(i.vRk)
        
        c.execute("INSERT INTO {tn} VALUES ('{v1}', '{v2}', '{v3}', '{v4}', '{v5}', '{v6}', '{v7}', '{v8}', '{v9}');"\
                 .format(tn=pName,
                         v1=pDate,
                         v2=clean(i.Tournament),
                         v3=clean(i.Surface),
                         v4=parseRound(i.Rd),
                         v5=rk,
                         v6=vrk,
                         v7=parseResult(i.Result),
                         v8=clean(i.Score),
                         v9=matchNumber(pDate, rk, vrk)))

# --- BODY --- 
                         
# Quote out second line to watch, go EVEN SLOWER
options = webdriver.ChromeOptions()
options.add_argument("--headless")

# Retrieve from web
driver = webdriver.Chrome(executable_path='chromedriver.exe', chrome_options=options)

driver.get("http://tennisabstract.com/reports/atpRankings.html")
time.sleep(2)

#df = pd.read_html(driver.page_source.encode("ascii","ignore").decode(), match="Player", header=0)[-1]
df = pd.read_html(driver.page_source, match="Player", header=0)[-1]

#Controls how many results to be retrieved.
df.drop(df.index[10:], inplace=True)

conn = sqlite3.connect("testfile.sqlite")
c = conn.cursor()

for i in df.itertuples():

    print(i.Player)
    driver.get("http://www.tennisabstract.com/cgi-bin/player.cgi?p=" + i.Player.replace(u'\xa0', ''))
    time.sleep(2)
    
    PlayerTable(c, driver, i.Player)

conn.commit()
conn.close()

driver.close()