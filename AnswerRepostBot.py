#Python Script for the RepostAnswerBot
#!/usr/bin/python

import praw
import time
import re
import os
from pathlib import Path

BANNED_WORDS = ["abused","abuse","abducted","drugs", "drug", "salvia","opiods","ecstasy","molly","ketamine","lsd","psilocybin", "weed", "marijuana", "pot", "cocaine", "rape","molested","raped", "heroin", "anal","anus","blowjob","blow job","bollock","bollok","boner","bugger","bum","buttplug","clitoris","cock","coon","cunt","dick","dildo","dyke","fag","feck","fellate","fellatio","felching","homo","jizz","knobend","knob end","labia","muff","nigger","nigga","penis","piss","poop","prick","pube","pussy","queer","scrotum","sex","s hit","sh1t","slut","smegma","spunk","tit","tosser","twat","vagina","wank","whore"]

def compareTitles(str1, str2):
    str1 = str1.lower()
    str2 = str2.lower()

    str1 = re.sub('[.?!@#$\"\']', '', str1)
    str2 = re.sub('[.?!@#$\"\']', '', str2)
    
    if(str1 == str2):
        return 100

    listStr1 = str1.split(" ")
    listStr2 = str2.split(" ")

    #Using the fact that if two words are the same, they are subsets of eachother

    count = 0
    for word in listStr1:
        if(word in listStr2):
            count += 1
            listStr2[listStr2.index(word)] = ""

    listStr2 = str2.split(" ")

    # NUMBER OF MATCHES / NUMBER OF WORDS IN STRING
    equalPercentage12 = count / len(listStr1)
    count = 0
    
    for word in listStr2:
        if(word in listStr1):
            count += 1
            listStr1[listStr1.index(word)] = ""

    equalPercentage21 = count / len(listStr2)
    #Taking the average of the two
    equalPercentage = (equalPercentage12 + equalPercentage21) / 2
    return 100 * equalPercentage

#Initializing the reddit/subreddit
def init(idFilename):
    reddit = praw.Reddit('bot1')
    askreddit = reddit.subreddit("askreddit")

    #If the ANSWERED_POST_IDS_FILE is not there, create it
    if(not os.path.isfile(idFilename)):
        f = open(idFilename, "w+")
        f.close()

    #Open the file, grab the contents and parse it making an array of the postID's we already visited
    f = open(idFilename, "r")
    fileContents = f.read()
    if(fileContents == ""):
        answeredPosts = []
    else:
        #Removing the last \n at the end of the string
        fileContents = fileContents[0:len(fileContents)-1]
        answeredPosts = fileContents.split("\n")
    f.close()
    
    return reddit, askreddit, answeredPosts

#Getting the most recents posts in the "new" section for AskReddit
def getRecentPosts(numPosts, answeredPosts, isPrinting):
    posts = []
    #Getting all the "new" submissions and adding them to the posts array
    for submission in askreddit.new(limit=numPosts):
        if(str(submission.id) not in answeredPosts):
            posts.append([submission.title, submission.url])
    if(isPrinting):
        print("All recent posts in '/r/AskReddit'")
        print()
        for post in posts:
            print("\tPost Title: " + post[0])
            print("\t\tPost URL: " + post[1])
            print()
        print("End of the recent posts in '/r/AskReddit'")
        print()
    return posts

#Getting all recent posts which seemed to have been posted before
def searchPreviousPosts(recentPosts, searchLimit, isPrinting):
    SimilarPosts = []
    #Traversing through recentPosts
    for recentPost in recentPosts:
        #Getting the recentPostTitle
        recentPostTitle = recentPost[0]
        if(isPrinting):
            print("Recent Post: " + recentPostTitle)
        #Making an object which will store the most relevant previous post and an integer representing
        #the current relevant posts equality to the original
        relevantPost = None
        maxEquality = 0
        maxUpvotes = 0
        #Querying for the posts that have a similar title to the post we want to comment on.
        for post in askreddit.search(recentPostTitle, limit=searchLimit):
            #Calculating how likely the two titles are using the property that
            #two equal strings are subsets of eachother
            equality = compareTitles(recentPostTitle, post.title)
            #If the current post in the list we are iterating through is
            #the most similar one we have seen yet, taking into account how popular this post is
            #AND its not exact same post as the one we want to comment on,
            #AND it seems to be >= the similarity threshold we pass through(75% Similar),
            #We are going to update the most relevant post and the maximum equality
            if((equality + (post.score / 2)) > (maxEquality + (maxUpvotes / 2)) and recentPost[1] != post.url and equality >= ACCEPTANCE_THRESHOLD):
                relevantPost = post
                maxEquality = equality
                maxUpvotes = post.score
            if(isPrinting):
                print('\tPrevious Post: ' + post.title)
                print('\t\tEquality: ' + str(equality))
                print('\t\tScore: ' + str(post.score))
        #After checking all the responses to our search, if we had atleast one "match",
        #we append that match to previousPosts array 
        if(relevantPost is not None):
            SimilarPosts.append([recentPost, relevantPost])
            if(isPrinting):
                print("Most Relevant Search: " + relevantPost.title + " Equivalence: " + str(maxEquality))
                print("URL: " + relevantPost.url)
                print()
    if(isPrinting):
        print()
        print()
        print("Printing out the list of similar posts and original posts")
        for post in SimilarPosts:
            print("Original Title: " + post[0][0])
            print("Similar  Title: " + post[1].title)
    return SimilarPosts

def getPreviousComments(similarPosts, redditInstance, isPrinting):
    commentsToPost = []
    #Traversing the SimilarPosts array and looking for the top comment
    for similarPost in similarPosts:
        #Getting the similar posts's url to get that post's comments
        similarPostsURL = similarPost[1].url
        #Getting the similar post's comments
        similarPostComments = redditInstance.submission(url = similarPostsURL).comments
        #Iterating through the root(Top Level) comments for this post
        for rootComment in similarPostComments:
            #If the top comment of the post contains words like "Drugs", "Rape", etc I want to get the next comment
            isValidComment = True
            for word in BANNED_WORDS:
                if(word.lower() in rootComment.body.lower().split(" ")):
                    isValidComment = False
            if(rootComment.body.lower() == "[deleted]"):
                isValidComment = False
            #The comment doesn't contain anything inappropriate
            if(isValidComment):
                #Appending the URL of the post we want to comment on and the first comment to the commentsToPost array
                commentsToPost.append([similarPost[0][1], rootComment.body])
                if(isPrinting):
                    print("Original Post: " + str(similarPost[0][0]))
                    print("\tBody: " + str(rootComment.body))
                    print("\tScore: " + str(rootComment.score))
                    print()
                #After we got the first comment, break
                break
    return commentsToPost

def postComments(commentsToPost, isPrinting, delayTime, idFile, answeredPosts):
    #Traversing through the list of comments and URLs and posting the respective
    #comment on each post, then waiting 10 minutes
    for comment in commentsToPost:
        if(isPrinting):
            print("URL: " + comment[0])
            print("Comment: " + comment[1])
            print()
        #Opening the original post
        originalPost = reddit.submission(url = comment[0])
        #Replying to that reddit post
        originalPost.reply(comment[1])
        f = open(idFile, "a")
        f.write(originalPost.id + "\n")
        answeredPosts.append(str(originalPost.id))
        f.close()
        for x in range(0, delayTime):
            print(str(delayTime - x) + " Minutes remaining before next post.")
            time.sleep(60)
    return answeredPosts

def delay():
    time.sleep(5)

if(__name__ == '__main__'):
    NUMBER_OF_POSTS_TO_CHECK = 15
    NUMBER_OF_POSTS_TO_SEARCH = 60
    ACCEPTANCE_THRESHOLD = 75
    MINUTES_OF_DELAY = 10
    ANSWERED_POST_IDS_FILENAME = "AnsweredRepostsIDList.txt"
    
    reddit, askreddit, answeredPosts = init(ANSWERED_POST_IDS_FILENAME)
    delay()
    
    while(True):
        try:
            recentPosts = getRecentPosts(NUMBER_OF_POSTS_TO_CHECK, answeredPosts, True)
            delay()
            similarPosts = searchPreviousPosts(recentPosts, NUMBER_OF_POSTS_TO_SEARCH, False)
            delay()
            commentsToPost = getPreviousComments(similarPosts, reddit, False)
            delay()
            answeredPosts = postComments(commentsToPost, True, MINUTES_OF_DELAY, ANSWERED_POST_IDS_FILENAME, answeredPosts)
            delay()
        except Exception as e:
            print(str(e))
            time.sleep(600)
    
