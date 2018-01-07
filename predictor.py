from authentication import *
from stat_table import *
import base64
import requests
import os
import time

#If a player has multiple words in their last name, please use their full name
PLAYER = ""
CURRENTYEAR = "2017-2018"
NOW = int(time.time())

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
                .format(MSFUSERNAME,MSFPASSWORD).encode('utf-8')).decode('ascii')
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

#Get what the player is on pace for in the current season
def get_expected_forward_stats(data):
    expected = []
    try:
        #Get current stats
        GP = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"][GAMESPLAYED]["#text"]
        G = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][GOALS]["#text"]
        A = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][ASSISTS]["#text"]
        PPP = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][POWERPLAYPOINTS]["#text"]
        SHP = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][SHORTHANDEDPOINTS]["#text"]
        GWG = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][GAMEWINNINGGOALS]["#text"]
        PIM = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][PENALTYMINUTES]["#text"]
        S = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][SHOTS]["#text"]
        H = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"]["stats"][HITS]["#text"]

        #Convert from string to int
        GP = float(GP)
        G = int(G)
        A = int(A)
        PPP = int(PPP)
        SHP = int(SHP)
        GWG = int(GWG)
        PIM = int(PIM)
        S = int(S)
        H = int(H)

        #Find the scalar to get their pace and make sure you are not dividing by 0
        if GP != 0.0:
            scalar = 82.0/GP
        else:
            return expected

        #Calculate on pace stats
        G = int(scalar * G)
        A = int(scalar * A)
        P = G + A

        S = int(scalar * S)

        #Append those stats to a list and return them
        expected.append(G)
        expected.append(A)
        expected.append(P)
        expected.append(PPP)
        expected.append(SHP)
        expected.append(GWG)
        expected.append(PIM)
        expected.append(S)
        expected.append(H)
        return expected
    except KeyError:
        return expected

def get_predicted_forward_stats(data):
    predicted = []
    deltaList = []
    outliers = []
    finalPrediction = []

    #Parse the current year into two ints so that I can easily decrement them for previous seasons
    startyear = int(CURRENTYEAR[:-5])
    endyear = int(CURRENTYEAR[5:])
    try:
        gamesPlayed = data["cumulativeplayerstats"]["playerstatsentry"][0]["stats"][GAMESPLAYED]["#text"]
        predicted.append(get_expected_forward_stats(data))

        #Get every season that the API has on record and log them into a list of lists
        while True:
            try:
                startyear -= 1
                endyear -= 1
                data = get_response(PLAYER, str(startyear) + "-" + str(endyear))
                predicted.append(get_expected_forward_stats(data))

            #If we have gone too far, then break from the loop
            except ValueError:
                break

        #Clean the list of any empty sets and find the change b/w seasons
        predicted = [x for x in predicted if x != []]
        deltaList = get_delta_list(predicted)
        
        #Use the deltaListBuffer to find the outliers
        noOutliers = get_removed_outliers_list(deltaList)

        null = True
        for i in range(0, len(noOutliers)):
            if noOutliers[i] != 0.0:
                null = False
                break
        if not null:
            for i in range(0, len(noOutliers)):
                noOutliers[i] = int(noOutliers[i] * int(predicted[1][i]))
                finalPrediction.append(int(float(noOutliers[i]) * ((82.0 - float(gamesPlayed))/ 82.0))
                                       + int(float(predicted[0][i]) * (float(gamesPlayed)/82.0)))

            finalPrediction[2] = finalPrediction[0] + finalPrediction[1]
        else:
            finalPrediction = predicted[0]
        return finalPrediction
    except KeyError:
        return finalPrediction

#The following two functions get the change from one season to another and record it in a list of lists
def get_delta(stats, i):
        delta = []

        for j in range (0,len(stats[i])):
            if(i + 1 != len(stats)):
                if(stats[i+1][j] != 0):
                    delta.append(stats[i][j] / stats[i+1][j])
                else:
                    delta.append("null")
            else:
                delta.append("null")
        return delta

def get_delta_list(stats):
    deltaList = []
    for i in range(len(stats)-1,-1,-1):
        deltaList.append(get_delta(stats, i))
    return deltaList

def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

#Find the outliers and get rid of them
def get_removed_outliers_list(deltaList):
    deltaOutliers = []
    deltaNoOutliers = []
    outliers = []
    medians = []
    firstq = []
    thirdq = []
    iqr = []
    scalar = []
    buffer = []

    #Transpose the list of lists
    deltaOutliers = list(map(list,zip(*deltaList)))

    #Sort the delta values for each individual stat
    for i in range(0,len(deltaOutliers)):
        deltaOutliers[i] = [x for x in deltaOutliers[i] if x != "null"]
        deltaOutliers[i].sort()
        
    #Find the medians of the delta values
    for i in range(0,len(deltaOutliers)):
        if len(deltaOutliers[i]) % 2 == 0 and len(deltaOutliers[i]) > 1:
            medians.append((deltaOutliers[i][int(len(deltaOutliers[i])/2)-1]
                            + deltaOutliers[i][int(len(deltaOutliers[i])/2)])/2)
        elif len(deltaOutliers[i]) % 2 != 0 and len(deltaOutliers[i]) > 1:
            medians.append(deltaOutliers[i][int(len(deltaOutliers[i])/2) + 1])
        elif len(deltaOutliers[i]) == 1:
            medians.append(deltaOutliers[i][0])
        else:
            medians.append(0)

    #Find the first quartiles of the delta values
    buffer = list(deltaOutliers)
    for i in range(0,len(buffer)):
        buffer[i] = [x for x in buffer[i] if x <= medians[i]]

    #Find the first quartile
    for i in range(0,len(buffer)):
        if len(buffer[i]) % 2 == 0 and len(buffer[i]) > 1:
            firstq.append((buffer[i][int(len(buffer[i])/2)-1]
                            + buffer[i][int(len(buffer[i])/2)])/2)
        elif len(buffer[i]) % 2 != 0 and len(buffer[i]) > 1:
            firstq.append(buffer[i][int(len(buffer[i])/2)])
        elif len(buffer[i]) == 1:
            firstq.append(buffer[i][0])
        else:
            firstq.append(0)

    #Find the third quartiles of the delta values
    buffer = list(deltaOutliers)
    for i in range(0,len(buffer)):
        buffer[i] = [x for x in buffer[i] if x >= medians[i]]

    #Find the third quartile
    for i in range(0,len(buffer)):
        if len(buffer[i]) % 2 == 0 and len(buffer[i]) > 1:
            thirdq.append((buffer[i][int(len(buffer[i])/2)-1]
                            + buffer[i][int(len(buffer[i])/2)])/2)
        elif len(buffer[i]) % 2 != 0 and len(buffer[i]) > 1:
            thirdq.append(buffer[i][int(len(buffer[i])/2)])
        elif len(buffer[i]) == 1:
            thirdq.append(buffer[i][0])
        else:
            thirdq.append(0)


    #Find this interquartile ranges
    for i in range(0,len(thirdq)):
        iqr.append(thirdq[i] - firstq[i])

    #Find the necessary scalar value
    for i in range(0,len(iqr)):
        scalar.append(iqr[i] * 0.25)

    #List of tuples containing upper and lower bounds for outliers
    for i in range(0,len(scalar)):
        bounds = (firstq[i] - scalar[i], thirdq[i] + scalar[i])
        outliers.append(bounds)

    buffer = list(deltaOutliers)
    for i in range(0,len(buffer)):
        buffer[i] = [x for x in buffer[i] if x >= outliers[i][0] and x <= outliers[i][1]]
        deltaNoOutliers.append(mean(buffer[i]))
            
    return deltaNoOutliers

def run():
    #Get the JSON data with all of the player stats
    response = get_response(PLAYER, CURRENTYEAR)

    #Two arrays that will be populated with the player's expected total
    #and the predicted stats respectively
    predictedStatsList = []
    expectedStatsList = []
    reply = ""
    try:
        if PLAYER == "" or PLAYER.isnumeric():
            reply = "Not a player";
            reply += "\n\n&nbsp;\n\n&nbsp;\n\n*I am a bot! If you have any issues or find any bugs, contact my creator /u/heavie1!*"

        #If the player is a forward
        elif get_player_type(response) != "G" and get_player_type(response) != "False":
            expectedStatsList = get_expected_forward_stats(response)
            predictedStatsList = get_predicted_forward_stats(response)
            if expectedStatsList != []:
                reply = get_player_type(response) + " " + get_player_name(response) + " is on pace to have:\n\n"
                reply += "G|A|P|PPP|SHP|GWG|PIM|S|H\n:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"
                for i in range(0,len(expectedStatsList)):
                    reply += str(expectedStatsList[i])
                    reply += "|"
                if expectedStatsList[2] >= predictedStatsList[2] - 5 and expectedStatsList[2] <= predictedStatsList[2] + 5:
                    reply += "\n\nI think he is very close to being on pace with my prediction!\nHere it is:\n\n"
                elif expectedStatsList[2] < predictedStatsList[2]:
                    reply += "\n\nHe is underperforming a bit from what I expected.\nHere is my guess for the end of the season:\n\n"
                else:
                    reply += "\n\nHe is doing much better than I expected!\nHere is my guess for the end of the season:\n\n"
                reply += "G|A|P|PPP|SHP|GWG|PIM|S|H\n:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"
                for i in range(0,len(predictedStatsList)):
                    reply += str(predictedStatsList[i])
                    reply += "|"

                reply += "\n\n&nbsp;\n\n&nbsp;\n\n*I am a bot! If you have any issues or find any bugs, contact my creator /u/heavie1!*"

        #If the player is a goalie
        elif get_player_type(response) == "G" and get_player_type(response) != "False":
            reply = "Sorry, I don't work with goalies right now.\n\nHere are some of G "
            if get_player_name(response) == "Carey Price":
                reply += "Jesus Price"
            else:
                reply += str(get_player_name(response))

            reply += "'s stats to make up for it:\n\n" + str(get_stats(response,GOALSAGAINST)) + " goals against\n\n"
            reply += str(get_stats(response, SAVES)) + " saves\n\n" + str(get_stats(response,SAVEPERCENTAGE))
            reply += " save percentage"
            reply += "\n\n&nbsp;\n\n&nbsp;\n\n*I am a bot! If you have any issues or find any bugs, contact my creator /u/heavie1!*"
        else:
            reply ="Player not found. Please be sure you spelled their name correctly.\n\nOtherwise, I might not have any information on them.\n\nSorry!"
            reply += "\n\n&nbsp;\n\n&nbsp;\n\n*I am a bot! If you have any issues or find any bugs, contact my creator /u/heavie1!*"


        return reply
    except UnboundLocalError:
        print("Unable to access API")

#Function to make a list of all instances of a character so that I can read many different inputs of names
def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub)

if not os.path.isfile("comments_replied_to.txt"):
    comments_replied_to = []
else:
    with open("comments_replied_to.txt", "r") as f:
              comments_replied_to = f.read()
              comments_replied_to = comments_replied_to.split("\n")

while True:
    for comment in REDDIT.subreddit("test+habs+hockey").comments(limit=None):
        commentTime = int(comment.created_utc)
        if (NOW - commentTime) > 18000:
            pass
        else:
            try:
                if "!predict-nhl" in comment.body and comment.id not in comments_replied_to and comment.author != REDDIT.user.me():
                    commentFetch = comment.body.split("!predict-nhl ", 1)[-1]
                    PLAYER = commentFetch
                    
                    #Convert player into proper form
                    PLAYER = PLAYER.strip()
                    if len(list(find_all(PLAYER, " "))) == 1:
                        PLAYER = PLAYER.replace(" ", "-")
                    elif len(list(find_all(PLAYER, " "))) > 1:
                        PLAYER = PLAYER.replace(" ", "-", 1)
                        PLAYER = PLAYER.replace(" ", "")
                        
                    comment.reply(run())

                    comments_replied_to.append(comment.id)
                    with open ("comments_replied_to.txt", "a") as f:
                        f.write(comment.id + "\n")

                    print("Successfully replied!")
            except praw.exceptions.APIException:
                print("We stuck")
                time.sleep(60)
    time.sleep(10)
