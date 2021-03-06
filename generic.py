import re
from string import punctuation as PUNCTUATION
from  profile import *
from  suffix_printer import *
from  parsers import *
from getpass import getpass
import json
import csv
from pathlib import Path
import sqlite3
from sys import exit

def importCookies(filenames):

    cookies = {}
    for filename in filenames:

        pth = Path(filename)
        if not pth.exists():
            raise f'File not found: {filename}'

        try:

            with open(filename) as infile:

                for jcookie in json.load(infile):

                    assert 'name' in jcookie,(
                        'Cookie must have a "name" member'
                    )

                    assert 'value' in jcookie,(
                        'Cookie must have a "value" member'
                    )

                    cookies[jcookie['name']] = jcookie['value']

        except Exception as e:

            esprint('Failed to import cookies as JSON file. '\
                    'Attempting to parse as SQLite3 file.')

            try:

                with open(filename,'rb') as infile:
                    with open('cookies.sqlite','wb') as outfile:
                        outfile.write(infile.read())

                conn = sqlite3.connect('cookies.sqlite')
                cur = conn.cursor()
                for row in cur.execute(
                        f"select * from moz_cookies where "\
                        "baseDomain like '%linkedin%';"
                        ):
                    k,v = row[3],row[4]
                    cookies[k] = v

            except Exception as e:

                esprint('Failed to import cookies!\n\n')
                print(e)
                exit()

    return cookies

def checkEntityUrn(inc,start):
    
    if 'entityUrn' in inc and \
            inc['entityUrn'].startswith(start):
        return True
    else:
        return False

def loadProfiles(output_file):

    main_profiles = []
    with open(output_file) as infile:
        rows = [r for r in csv.reader(infile)]
        if rows.__len__() > 2:
            columns = rows[0]
            main_profiles = [
                Profile.from_row(r,columns) for r in rows[1:]
            ]

    return main_profiles

def writeProfiles(output_file,profiles):

    written=[]
    if output_file == stdout:
        csvfile = stdout
    else:
        csvfile = open(output_file,'w')

    writer = csv.writer(csvfile)
    writer.writerow(Profile.ATTRS)
    for p in profiles:
        if p not in written:
            writer.writerow(p.to_row())
            written.append(p)
    csvfile.close()

def addContacts(session,profiles,message=None):

    counter = 0
    for p in profiles:

        # Skip anyprofile without an entity_urn or that has already
        # been requested during a previous run
        if not p.entity_urn or p.connection_requested: continue
        counter += 1
        esprint(f'Sending Connection Request {counter}: {p.first_name} ' \
                f'{p.last_name}, {p.occupation} @ {p.company_name}')

        # Send the connection request
        try:
            resp = session.postConnectionRequest(
                    urn=p.entity_urn,
                    message=message)
        except Exception as e:
            esprint('Failed to send connection request!',suf='[!]')
            raise e

        if resp.status_code == 201:
            p.connection_requested = True
        else:
            try:
                status = resp.json()['status']
                if status == 429:
                    esprint('API request limit hit. Halting execution')
                    break
                else:
                    p.connection_requested = True
            except Exception as e:
                esprint('Connection request failed!',suf='[!]')
                raise e

    return profiles

def filterDict(dct,blacklist=[]):

    for key in list(dct.keys()):

        if not key: continue

        if key[0] in PUNCTUATION or key in blacklist:
            del(dct[key])
        elif key and dct[key].__class__ == dict:
            dct[key] = filterDict(dct[key])

    return dct


def getInput(prompt,password=False):

    i = None
    while not i:
        if password:
            i = getpass(prompt)
        else:
            i = input(prompt)

    return i

def handleProxies(proxies=[]):


    new_proxies = {}
    if proxies:
        for proxy in proxies:
            match = re.match(r'^(https?)',proxy)
            if not match:
                raise Exception(f'Invalid proxy supplied: {proxy}')
            new_proxies[match.groups()[0]] = proxy

    return new_proxies
