import json
import os
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup

def lambda_handler(event, context):
    # Get html code of the website
    site = requests.get('https://www.leedsgrandmosque.com/')
    soup = BeautifulSoup(site.content, 'html.parser')

    # Get the prayer section part from the html code
    prayer_section = soup.find(class_="prayers-list")

    # Save Prayer, Time and Jammah in info
    info ={
        "Prayer": [prayer.get_text().capitalize() for prayer in prayer_section.select(".prayer-name")],
        "Time": [time.get_text() for time in prayer_section.select(".date")],
        "Jammah": [jammah.get_text() for jammah in prayer_section.select(".jammah-date")],
    }

    # Get Prayer timetable on Notion page
    token = os.environ.get('NOTION_API_TOKEN')
    database_id = os.environ.get('NOTION_DATABASE_ID')

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Read the Notion page
    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    res = requests.request("POST", read_url, headers=headers)
    data = res.json()

    # Save Notion page info in a json file
    with open('/tmp/Prayer_Time.json', 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False)

    # Open the json file
    data = json.load(open("/tmp/Prayer_Time.json"))

    # Create a dictionary to store page id
    pageid = dict.fromkeys(info["Prayer"])

    # Get page id of each prayer
    for i in data["results"]:
        pageid[i["properties"]["Prayer"]["title"][0]["plain_text"]] = i["id"]

    # Put page id into the list (Not used in code but for completeness)
    info["pageId"] = list(pageid.values())

    # For each prayer
    for i in range(len(pageid)):
        # Get URL of Notion page
        update_url = f"https://api.notion.com/v1/pages/{info['pageId'][i]}"

        # Get Jummah date right
        try:
            day = {
                "start": str(datetime.strptime(str(date.today()) + " " + info["Jammah"][i], '%Y-%m-%d %H:%M')),
                "time_zone": "Europe/London"
            }
        except:
            day = None

        # Notion page code
        update_data = {
            "properties": {
                "Time": {
                    "date": {
                        "start": str(datetime.strptime(str(date.today()) + " " + info["Time"][i], '%Y-%m-%d %H:%M')),
                        "time_zone": "Europe/London"
                    }
                },
                "Jummah": {
                    "date": day
                }
            }
        }

        # Update Notion page
        data = json.dumps(update_data)
        response = requests.request("PATCH", update_url, headers=headers, data=data)

    # Output status
    return {
        'statusCode': response.status_code,
        'body': response.text
    }
