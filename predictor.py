from authentication import *
from stat_table import *
import base64
import requests

#Get the API response for the cumulative stats
#This allows it to only call the API once per player (Efficiency!)
def get_response(player, year):
    try:
        response = requests.get(
            url="https://api.mysportsfeeds.com/v1.1/pull/nhl/" + year + "/cumulative_player_stats.json",
            params={
                "player": player
            },
            headers={
                "Authorization": "Basic " + base64.b64encode('{}:{}'
                .format(USERNAME,PASSWORD).encode('utf-8')).decode('ascii')
            }
        )
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
    return response.json()

#Get the specified stats of the player from the specified year from the mySportsFeedAPI
def get_stats(data, stat):
    return data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][stat]["#text"]

#Check if the player is a skater / goalie / non-existant or non-active
def get_player_type(data):
    try:
        return data["cumulativeplayerstats"]["playerstatsentry"][0]["player"]["Position"]
    
    #If there is a KeyError, then the value that the API returned was not for a player, so they are either
    #non-active or non-existant, both of which I do not want to work with.
    except KeyError:
        return "False"

#Get the player's name
def get_player_name(data):
    try:
        player = data["cumulativeplayerstats"]["playerstatsentry"][0]["player"]["FirstName"]
        player += " " + data["cumulativeplayerstats"]["playerstatsentry"][0]["player"]["LastName"]
        return player
    #If there is a KeyError, then the value that the API returned was not for a player, so they are either
    #non-active or non-existant, both of which I do not want to work with. This should ideally never occur.
    except KeyError:
        return "False"

player = "Price"
year = "2014-2015"

#Get the JSON data with all of the player stats
response = get_response(player, year)

if player.strip() == "" or player.isnumeric():
    print("Not a player")
elif get_player_type(response) != "G" and get_player_type(response) != "False":
    print(get_player_type(response) + " " + get_player_name(response) + " \n"
          + get_stats(response,GOALS) + " goals\n" + get_stats(response, ASSISTS) +
          " assists\n" + get_stats(response,POINTS) + " points")
elif get_player_type(response) == "G" and get_player_type(response) != "False":
    print(get_player_type(response) + " " + get_player_name(response) + " \n"
          + get_stats(response,GOALSAGAINST) + " goals against\n" + get_stats(response, SAVES) +
          " saves\n" + get_stats(response,SAVEPERCENTAGE) + " save percentage")
else:
    print("Not a player")
