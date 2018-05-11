A reddit bot for giveaways.
Automatically picks winners and sends game codes to them via pm.

---
Autogiveaway bot can be used in two different ways, a fire and forget automatic giveaway, or a user mention.
Although the initial concept was for game code giveaways, it can be used to pick winners for other things as well.

# Types of giveaways supported

- Random - randomly picks users
- Number - collects all comments, extracts numbers and picks the closest to the number to guess.
- Keyword - collects all comments and looks for users who have a matching keyword or phrase.

# Automatic Giveaway Instructions
To set up an automatic giveaway send a properly formatted message to autogiveaway with the subject of: giveaway.
You will be sent a code that needs to be placed in the giveaway post and the bot will look for this code in your post submissions for a certain amount of time, if the code is not found the giveaway will be forgotten.
If the giveaway was setup properly, autogiveaway will make a comment in the post with the giveaway information.

#### Format:
**giveaway type, when to run, number of winners, post karma check, comment karma check, account age check, codes**
##### Examples:
- Message: **random, in 24 hours, 2, pkarma:100, ckarma:100, days:30, GAME-CODE-1 GAME-CODE-2**
- Message: **number:123:0:10000, 15 february 2017, 3, pkarma:50, ckarma:100, days:365, GAME-CODE-1 GAME-CODE-2 [GAME-CODE-3E GAME-3-DLCE]**
- Message: **keyword:guess this, friday 24 february 2017 5:00 pm EST, pkarma:25, ckarma:50, days:3, GAME-CODE-1**

#### Not all values are required, number of winners, post/comment karma and day values are optional
**giveaway type, when to run, codes** is also valid or **giveaway type, when to run, number of winnners, codes**
##### Additional Examples:
- Message: **random, in 48 hours, 2, GAME-CODE-1-HERE GAME-CODE-2** -- two winners will be picked and each will get one code
- Message: **number 1:0:1000, 21 february 2017 7:00 pm PST, GAME-CODE-1 GAME-CODE-2** -- one winner will be picked and will get the two codes
- Message: **keyword:lolipop, in 12 hours, GAME-CODE-1** -- one winner will be picked and will get one code

*When entering codes, ensure they are separated by spaces, use [] if you want to group up codes such as game+dlc*
- Message: **random, in 48 hours, 2, CODE-1 [CODE-2 CODE-2-DLC]**
*Use quotes "xbox one" if giving away something other than codes.*
- Message: **random, in 48 hours, 2, "xbox one" "battlefiedl 1"**

**If no number of winners is provided then 1 winner is assumed and if you have more than one code then that 1 winner will get all the codes.**

#### More examples:
*To randomly giveway the game code: GAME-CODE-1, in 24 hours, and only to people with 50 post/comment karma and 30+ day accounts:*
- **random, in 24 hours, pkarma:50, ckarma:50, days:30, GAME-CODE-1**

*To giveaway one game and a game+dlc to two people without caring about their reddit account:*
- **random, in 24 hours, 2, GAME-CODE-1 [GAME-CODE-2 GAME-CODE-2-DLC]**

*To giveaway a video card to one person:*
- **random, in 24 hours, "GFX 9000"**

*To giveaway two video cards to two people:*
- **random, in 24 hours, 2, "GFX 9000" "GFX 109000"**

# User Mention Giveaway Instructions
User mention can be used to have the autogiveaway bot pick winners from a post as soon as possible.
To trigger the bot simple mention */u/autogiveaway* followed by some options and the bot will reply to your comment with a list of winners based on those options.
#### Format Examples:

*pick one random winner*
- **/u/autogiveaway random** 

*pick two random winners*
- **/u/autogiveaway random, 2** 

*pick one winner, whoever posted the number closest to 234 out of 0 to 1000*
- **/u/autogiveaway number:234:0:1000**

*pick one winner, whoever posted 'test apple' first*
- **/u/autogiveaway keyword:test apple** 

*pick two winners who have 'test' in their comment*
- **/u/autogiveaway keyword:test, 2** 

*Account checks can also be done in mentions:*
- **/u/autogiveaway random, 2, pkarma:50, ckarma:10, days:45**

**Only the OP can launch a giveaway in their post, also the comment must be top-level directly under the post.**


# F.A.Q.

#### How does the bot work?
- For automatic giveaway:
The bot will store the codes given and schedule a process to run at whatever time it was told to. When it runs the giveaway and based on whatever parameters are sent to it, the bot will gather all top level comments, sort them by date, extract their content, and then pick the winners.
For number giveaways, if the number has already been used, whoever posted it first will get it, any other comment with the same number will be ignored. The bot will keep track and update a list of used numbers.
Once winners are picked, the bot will randomly assign the codes to the winners round-robin style (if there is more than one winner), and the codes will then be sent to the winners by PM.
- For user mention giveaway:
The bot will gather all top level comments, sort them by date, extract their content, and pick a winner based on parameters given in the user mention.
The winners will be announced in a reply to the comment where the user mention was made.
- More details:
The bot will only care about one comment per user, any additional comments are ingnored.

#### The giveaway didn't run at exactly the time it was supposed to?
The time you give the bot will be when the process of running the giveaway will start, to that is added the time it takes it to collect all comments, process them, and post replies/send pms. Which can be from seconds to 10+ minutes.

#### How long does the bot take to process a giveaway?
It depends on how many comments it needs to fetch from a post, connection with reddit and whether it is doing other things at the same time as well.
##### A very rough estimate from testing:
- 0 - 1500 comments: around 30 secs
- 1500 - 3000 comments: around 1 minute
- 3000 - 5000 comments: around 5 minutes
- 5000 - 8000 comments: around 8 minutes
- 8000 - 10000 comments: around 11 minutes

These are just estimates from development testing, the times could be longer depending on bot/reddit load.


#### Sample tested giveaways:
- Number
[r/pcmasterrace/ADR1FT and Dangerous Golf](https://www.reddit.com/r/pcmasterrace/comments/5d3swm/giveaway_adr1ft_and_dangerous_golf/?st=jh25ppyx&sh=419199bf)

- Random
[r/pcmasterrace/The Culling](https://www.reddit.com/r/pcmasterrace/comments/5coclr/giveaway_the_culling/?st=jh25rpjf&sh=22be206b)
