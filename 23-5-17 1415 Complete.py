import datetime
import json

import pysftp
import pytz
import requests
from tabulate import tabulate

############# DESTINATIONS DICTIONARIES #############

# Station name and ID dictionary
stations = {
    'Dover': '0089',
    'Portland': '0033',
    'Dartmouth': '0023',
    'Fowey': '0008',
    'Falmouth': '0005',
    'Helford': '0004A',
    'Lizard Point': '0003',
    'Penzance': '0002',
    'Great Yarmouth': '0142',
}

# Destination name and corresponding station
destinations = {
    'St Mawes Harbour': 'Falmouth',
    'The Pandora': 'Falmouth',
    'Helford Restaurants': 'Helford',
    'Fowey': 'Fowey',
    'Kynance Cove': 'Lizard Point',
    'St Michaels Mount': 'Penzance',
    'Salcombe': 'Dartmouth',
    'Great Yarmouth': 'Great Yarmouth',
}

# Destination tide requirements (min_height, max_height)
destination_tide_requirements = {
    'St Mawes Harbour': (2.00,10.0), #essentially no max height
    'The Pandora': (3.2,10.0), #essentially no max height
    'Helford Restaurants': (3.5, 10.0), #essentially no max height
    'Kynance Cove': (0.0, 1.5), #essentially no min height
    'St Michaels Mount': (3.2,10.0), #essentially no min height
    'Salcombe': (1.5, 10.0), #essentially no max height
    'Fowey': (1.5,10.0), #essentially no max height
    'Great Yarmouth': (0.0,10.0), #essentially no max height
}

# Destination weather forecast stations
destination_weather = {
    'St Mawes Harbour': {'lat': '50.1552197', 'lon': '-5.0688262'},
    'The Pandora': {'lat': '50.1552197', 'lon': '-5.0688262'},
    'Helford Restaurants': {'lat': '50.0931362', 'lon': '-5.1369699'},
    'Fowey': {'lat': '50.3357786', 'lon': '-4.6365952'},
    'Kynance Cove': {'lat': '49.9687683', 'lon': '-5.2039246'},
    'St Michaels Mount': {'lat': '50.1194794', 'lon': '-5.5352463'},
    'Salcombe': {'lat': '50.2388158', 'lon': '-3.7726121'},
    'Great Yarmouth': {'lat': '52.6071742', 'lon': '1.7314845'},
}

############# DEFINED TIDE FUNCTIONS #############

def is_bst(dt):
    london_tz = pytz.timezone('Europe/London')
    dt_aware = london_tz.localize(dt)
    return dt_aware.dst() != datetime.timedelta(0)

def adjust_for_bst(time_str):
    # Convert the string into a datetime object
    time = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
    
    # Check if it's BST and adjust the time if it is
    time_zone = "UTC"
    if is_bst(time):
        time = time + datetime.timedelta(hours=1)
        time_zone = "BST"
    
    # Format the adjusted time
    formatted_time = time.strftime('%H:%M')
    formatted_datetime = time.strftime('%Y-%m-%d')
    
    # Create the final formatted string
    formatted_string = f"{formatted_time} {time_zone} {formatted_datetime}"
    
    # Get today's date in London's time zone
    london_tz = pytz.timezone('Europe/London')
    now_london = datetime.datetime.now(london_tz)
    today = now_london.strftime('%Y-%m-%d')

    # If the adjusted date is today, replace the date with "today"
    if formatted_datetime == today:
        formatted_string = f"{formatted_time} {time_zone} today"

    # Get tomorrow's date in London's time zone
    tomorrow = (now_london + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    # If the adjusted date is tomorrow, replace the date with "tomorrow"
    if formatted_datetime == tomorrow:
        formatted_string = f"{formatted_time} {time_zone} tomorrow"
    
    return (formatted_string, time_zone)

# Get the current time in UTC
current_time_utc = datetime.datetime.utcnow()

# Create an empty list to hold all the adjusted times
adjusted_times = []

# Loop 14 times
for i in range(14):
    # Get the time incremented by i hours
    incremented_time_utc = current_time_utc + datetime.timedelta(hours=i)
    
    # Format the time as a string
    incremented_time_str = incremented_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Adjust the time for BST if necessary
    adjusted_time, time_zone = adjust_for_bst(incremented_time_str)
    
    # Add the adjusted time to the list
    adjusted_times.append(adjusted_time)

# Function to return a tide height at a specific time
def get_exact_tide_height(station_id, date_time):
    url = f"{base_url}/Stations/{station_id}/TidalHeight?DateTime={date_time}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        tide_data = json.loads(response.text)
#        print(f"get_exact_tide_height for {station_id} at {date_time}: {tide_data}")
        return tide_data["Height"]
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

# Function to get hourly tide levels
def find_hourly_heights(station_id, now):
    
    # Get current time
    start_time = now
    end_time = now + datetime.timedelta(hours=14)
    start_time_apiformat = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    end_time_apiformat = end_time.strftime("%Y-%m-%dT%H:%M:%S")

    #Get events 
    url = f"{base_url}/Stations/{station_id}/TidalHeights?StartDateTime={start_time_apiformat}&EndDateTime={end_time_apiformat}&IntervalInMinutes=60"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        hourly_tide_data = json.loads(response.text)
    # print(f"Hourly Tides Data: {hourly_tide_data}")
    return hourly_tide_data
    
    
def filter_tides(destination, hourly_tide_data):
    min_height, max_height = destination_tide_requirements[destination]
    
    tides = hourly_tide_data
    now = datetime.datetime.now(pytz.timezone('UTC'))
    
    filter_tides_result = []
    for i, tide in enumerate(tides):
        # Parse the date-time from the tide data
        from datetime import timezone

        # Inside your loop:
        tide_time = datetime.datetime.strptime(tide['DateTime'], '%Y-%m-%dT%H:%M:%SZ')
        tide_time = tide_time.replace(tzinfo=timezone.utc)

        # Now you can subtract:
        hours_difference = (tide_time - now).total_seconds() / 3600
        
        # If the tide height is within the required range and the time is in the future, add it to the result
        if min_height <= tide['Height'] <= max_height and hours_difference >= -0.5:
            filter_tides_result.append((i, tide['Height']))
    # print(f"Filter Tides Result: {filter_tides_result}")
    return filter_tides_result
    
# define function for getting weather data
def getWeather(URL):
    # Ensure there are no errors with connection
    error_connect = True
    while error_connect == True:
        try:
            # HTTP request
            # print('Attempting to connect to OWM.')
            response = requests.get(URL)
            # print('Connection to OWM successful.')
            error_connect = None
        except:
            # Call function to display connection error
            print('Connection error.')
            
    # Check status of code request
    if response.status_code == 200:
        # print('Connection to Open Weather successful.')
        # get data in jason format
        data = response.json()

        with open('data.txt', 'w') as outfile:
            json.dump(data, outfile)

        return data

    else:
        # Call function to display HTTP error
        print("foo")

############# DEFINED WEATHER FUNCTIONS #############

def get_force_value(wind_int):
    ranges = [(0, 388, 'Force 1'), 
            (389, 777, 'Force 2'), 
            (778, 1360, 'Force 3'), 
            (1361, 2137, 'Force 4'), 
            (2138, 3304, 'Force 5'), 
            (3305, 4276, 'Force 6'), 
            (4277, 5442, 'Force 7'), 
            (5443, 6609, 'Force 8'), 
            (6610, 7969, 'Force 9'), 
            (7970, 9330, 'Force 10'), 
            (9331, 10885, 'Force 11')]

    force_value = 'Force 12'  # default value
    for lower, upper, force in ranges:
        if lower <= wind_int <= upper:
            force_value = force
            break
    return force_value

def get_compass_direction(wind_dir_int):
    directions = [(0, 23, 'Northerly'), 
              (21, 40, 'North North Easterly'),
              (41, 60, 'North Easterly'), 
              (61, 80, 'East North Easterly'), 
              (81, 110, 'Easterly'), 
              (111, 130, 'East South Easterly'), 
              (131, 150, 'South Easterly'), 
              (151, 170, 'South South Easterly'), 
              (171, 200, 'Southerly'), 
              (201, 220, 'South South Westerly'),
              (221, 240, 'South Westerly'), 
              (241, 260, 'West South Westerly'),
              (261, 290, 'Westerly'), 
              (291, 310, 'West North Westerly'), 
              (311, 330, 'North Westerly')]

    compass_dir = 'North North Westerly'  # default value
    for lower, upper, direction in directions:
        if lower <= wind_dir_int <= upper:
            compass_dir = direction
            break

    return compass_dir

############# TIDE API PARAMETERS #############

# API base URL
base_url = "https://admiraltyapi.azure-api.net/uktidalapi-premium/api/V2"

# Subscription key
subscription_key = "e0d134c3ff44426c8ab9c4280d0c354e"

# Headers
headers = {
    "Ocp-Apim-Subscription-Key": subscription_key,
}

############# WEATHER API PARAMETERS #############

# From openweathermap.com
wx_base_url = 'http://api.openweathermap.org/data/2.5/onecall?'

api_key = '09af6edfead8f35f9a22092889595955'

units = 'metric'

# URL = BASE_URL + 'lat=' + LATITUDE + '&lon=' + LONGITUDE + '&units=' + UNITS +'&appid=' + API_KEY


############# WEATHER ACTIONS #############

# Define new dictionaries to hold the weather data
today_wind_force_by_location = {destination: '' for destination in destination_weather}
today_wind_dir_by_location = {destination: '' for destination in destination_weather}
tomorrow_wind_force_by_location = {destination: '' for destination in destination_weather}
tomorrow_wind_dir_by_location = {destination: '' for destination in destination_weather}

for place, coordinates in destination_weather.items():
    params = {
        'lat': coordinates['lat'],
        'lon': coordinates['lon'],
        'units': units,
        'appid': api_key
    }

    response = requests.get(wx_base_url, params=params)

    if response.status_code == 200:
        weather_data = response.json()

        # TODAY DATA
        current = weather_data['current']
        wind = current['wind_speed']
        today_wind = wind * 100
        wind_int = int(today_wind)
        wind_deg = current['wind_deg']
        wind_dir_int = int(wind_deg)

        # NEXT DAY DATA
        daily = weather_data['daily']
        nx_wind_speed = daily[1]['wind_speed']
        nx_wind_dir = daily[1]['wind_deg']
        nx_wind_int = int(nx_wind_speed) * 100
        nx_wind_dir_int = int(nx_wind_dir)

        today_wind_force = get_force_value(wind_int)
        today_compass_dir = get_compass_direction(wind_dir_int)

        next_day_wind_force = get_force_value(nx_wind_int)
        next_day_compass_dir = get_compass_direction(nx_wind_dir_int)

        today_wind_force_by_location[place] = today_wind_force
        today_wind_dir_by_location[place] = today_compass_dir
        tomorrow_wind_force_by_location[place] = next_day_wind_force
        tomorrow_wind_dir_by_location[place] = next_day_compass_dir

#        print(f"Today's wind force at {place} is: {today_wind_force}")
#        print(f"Today's wind direction at {place} is: {today_compass_dir}")
#        print(f"Tomorrow's wind force at {place} is: {next_day_wind_force}")
#        print(f"Tomorrow's wind direction at {place} is: {next_day_compass_dir}")
        
    else:
        print(f"Error getting data for {place}: {response.status_code}")

############# TIDE ACTIONS #############

current_tide_heights = {}
all_tide_data = {}

# Loop through the destinations and their corresponding stations
for destination, station_name in destinations.items():
    station_id = stations[station_name]
    now = datetime.datetime.utcnow()
    now_apiformat = now.strftime("%Y-%m-%dT%H:%M:%S")

    # Update the URL with the correct station_id
    tide_height_url = f"{base_url}/Stations/{station_id}/TidalHeight?DateTime={now_apiformat}"

    # Send the request
    response = requests.get(tide_height_url, headers=headers)

    # Check the status code and process the events
    if response.status_code == 200:
        events = json.loads(response.text)
    else:
        print("No dice!")

    # Get current tide height
    current_tide_heights[destination] = get_exact_tide_height(station_id, now.strftime('%Y-%m-%d %H:%M:%S'))

    # Find hourly heights
    all_tide_data[destination] = find_hourly_heights(station_id, now)

    # print(all_tide_data)
    # print(f"current_tide_height at {destination} is {current_tide_height}")
    # print(f"hourly_tide_data at {destination} is {hourly_tide_data}")
    # print("Destinations:", destinations)
    # print("Stations:", stations)


# Find when height is viable
#    filtered_tides = filter_tides(destination, hourly_tide_data)

#    print(filtered_tides)

# Initialize the HTML table
html_table = """
<!DOCTYPE html>
<html>
<head>
<style>
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        padding: 5px; /* Adjust as needed */
        border: 1px solid #ddd;
        text-align: center;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    th {
        background-color: #506BCF;
        color: white;
    }
    tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    @media screen and (max-width: 600px) {
        table, th, td {
            width: 100%;
            display: block;
        }
        th {
            display: none;
        }
        td {
            padding-left: 50%;
            text-align: right;
        }
        td:before {
            content: attr(data-header);
            position: absolute;
            left: 15px;
            width: 50%;
            padding-left: 15px;
            font-weight: bold;
            text-align: left;
        }
    }
</style>
</head>
<body>

<table>
"""

# Add a header row

html_table += "<tr><th>Weather Info</th>"

for destination in destination_weather:
    html_table += f"<th>{destination}</th>"

html_table += "</tr>"

# Add a row for Today's wind force
html_table += "<tr><td>Today's Wind Force</td>"

for destination in destination_weather:
    html_table += f"<td>{today_wind_force_by_location[destination]}</td>"

html_table += "</tr>"

# Add a row for Today's wind direction
html_table += "<tr><td>Today's Wind Direction</td>"

for destination in destination_weather:
    html_table += f"<td>{today_wind_dir_by_location[destination]}</td>"

html_table += "</tr>"

# Add a row for Tomorrow's wind force
html_table += "<tr><td>Tomorrow's Wind Force</td>"

for destination in destination_weather:
    html_table += f"<td>{tomorrow_wind_force_by_location[destination]}</td>"

html_table += "</tr>"

# Add a row for Tomorrow's wind direction
html_table += "<tr><td>Tomorrow's Wind Direction</td>"

for destination in destination_weather:
    html_table += f"<td>{tomorrow_wind_dir_by_location[destination]}</td>"

html_table += "</tr>"

html_table += "<tr><th>Times</th>"

# Add a header for each location
for destination in all_tide_data:
    html_table += f"<th>{destination}</th>"

html_table += "</tr>"

# Add a row for current tide height
html_table += "<td>Current Tide Height</td>"

# Add a column for each location's current tide height
for destination in all_tide_data:
    html_table += f"<td>{current_tide_heights[destination]:.1f}</td>"

html_table += "</tr>"

# Initialize an empty dictionary to hold the tides for each time and location
tides_by_time = {destination: {time: '' for time in adjusted_times} for destination in all_tide_data}

# Populate the tides_by_time dictionary with the filtered tides for each location
for destination in all_tide_data:
    filtered_tides = filter_tides(destination, all_tide_data[destination])
    for tide in filtered_tides:
        index, height = tide
        tides_by_time[destination][adjusted_times[index]] = height

# Loop through each time and add a row to the HTML table
for time in adjusted_times:
    html_table += f"<tr><td>{time}</td>"

    # Add a column for each location's tide at this time
    for destination in all_tide_data:
        tide_height = tides_by_time[destination][time]
        formatted_tide_height = format(tide_height, '.1f') if isinstance(tide_height, float) else ''
        html_table += f"<td>{formatted_tide_height}</td>"

    html_table += "</tr>"

# Close the HTML table
html_table += "</table>"

with open('tides_table.html', 'w') as f:
    f.write(html_table)

# Print the HTML file has been generated
print("The HTML file has been generated")

# Upload via SFTP

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None    # Use this line to bypass the host key. Not recommended for production code

with pysftp.Connection('www.zen186554.zen.co.uk', username='zen186554', password='VL6DGviJ', cnopts=cnopts) as sftp:
    print("Connection successfully established ...")
    
    local_file = 'tides_table.html'
    remote_file = 'tides_table.html'  # Path to where the file will be uploaded on the server

    sftp.put(local_file, remote_file)
    print(f"File '{local_file}' has been uploaded ...")

    # Verifying if the file has been uploaded
    if sftp.exists(remote_file):
        print(f"File '{local_file}' successfully uploaded at {remote_file}")
    else:
        print(f"Failed to upload the file '{local_file}'")

sftp.close()
print("Connection closed.")
