import logging.handlers
import os

from EnhancedRotatingFileHandler import EnhancedRotatingFileHandler

logs_format = '[%(asctime)s] [%(levelname)-7s] [%(module)-8s.%(funcName)-16s] %(message)s'
log_date_fmt = '%m/%d/%Y %H:%M:%S %z'

logging.basicConfig(format=logs_format, datefmt=log_date_fmt, level=logging.INFO)

#  File logs
logger = logging.getLogger('')
formatter = logging.Formatter(logs_format, datefmt=log_date_fmt)
cwd = os.getcwd()  # get current working directory
logs_path = cwd + '\logs\\autogiveaway.log'

# rotate log every day or by file size
handler = EnhancedRotatingFileHandler(logs_path, maxBytes = 500000, backupCount=1, encoding='utf8', when='d',interval=1)

handler.setFormatter(formatter)
logger.addHandler(handler)

#  Set logging level for libraries:
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# giveaway_args = [type, date, guessnum, minnum, maxnum, keyword, winners, is_mention, pkarma, ckarma, days]
check_logs = 1  # (in minutes) Interval to check and upload logs to pastebin
check_pm_interval = 1  # (in minutes) Interval to check for new PMs
check_mentions_interval = 1  # (in minutes) Interval to check for new mentions
check_post_interval = 1  # (in minutes) Interval to check for giveaway post
check_post_timeout = 15  # (in minutes) Timeout to check for giveaway post
submissions_limit = 5  # number of *new* submissions that will be checked for the unique identifier
comment_character_limit = 300  # comments longer than this char limit will be skipped (keyword giveaway)
update_numbers_interval = 1  # (in minutes) Interval to update numbers that have been posted in a number giveaway
update_numbers_comment_limit = 2000  # if number of comments gets past this, bot will stop updating numbers
reply_subject = "AutoGiveaway Bot"
footer_message = '  \n  \n-------------------------------------' \
                 '  \n AutoGiveaway Bot - [Wiki](https://www.reddit.com/r/autogiveaway/wiki/index)' \
                 '  \n ^Visit ^/r/AutoGiveaway ^for ^more ^info.'

# ---------------- error / retry in case of connection/API errors
retries = 5  # Number of times script will retry
backoff_multiplier = 1
wait_time = 5  # (in seconds) wait time between retries (*backoff_multiplier per additional try)
retry_failed_pms_retries = 6  # number of times retry_failed_pms will run
retry_failed_pms_wait_time = 15  # (in minutes) wait time between retry_failed_pms executions

# ---------------- giveaway.process_pm errors
parse_errormessage = '**Giveaway not started:**' \
                     '  \n Something went wrong while parsing your message,' \
                     ' please double check the formatting and try again.'

parse_mention_errormessage = 'This doesn\'t look like anything to me...'

codes_errormessage = '**Giveaway not started:**' \
                     '  \n Something went wrong while parsing the codes,' \
                     ' please double check the formatting and try again.'

winners_errormessage = '**Giveaway not started:**' \
                               '  \n There aren\'t enough codes for each possible winner:' \
                               '  \n  Possible winners: {0}' \
                               '  \n  Codes detected: {1}' \
                               '  \n Please double check your input and try again.'

# ----------------------------------------------------------------------------------------

# ---------------- giveaway.setup
setup_message = 'Initial setup requirement:' \
                '  \nCreate a giveaway post and include this code in the title or body of the message:' \
                '  \n**{1}**' \
                '  \nA comment will be posted on it announcing the giveaway and other details.' \
                '  \nIf post is not found within {0} minutes the giveaway and codes will be cleared.'
# ----------------------------------------------------------------------------------------

# ---------------- giveaway.schedule
giveaway_comment_random = 'A **random** giveaway has been started in this post by **/u/{0}**!  \n' \
                          '  \n* To participate **reply to the OP** (*not this comment!*)' \
                          '  \n* Code(s) will be sent by PM.  \n' \
                          '  \nWinner selection will be around: ' \
                          '*[{1} UTC](http://www.wolframalpha.com/input/?i={1}+UTC+To+Local+Time)*' \
                          '  \n  \n' \
                          '  \n*Minimum account requirements:*  \n' \
                          '  \n    {2} post karma' \
                          '  \n    {3} comment karma' \
                          '  \n    {4} days old  \n' \
                          '  \n*Number of winners to pick: {5}*  \n' \
                          '  \n*^Upvote ^for ^visibility, ^this ^comment ^will ^be ^edited ^with ^the ^results.*'

giveaway_comment_number = 'A **number guess** giveaway has been started in this post by **/u/{0}**!  \n' \
                          '  \n* To participate **reply to the OP** with a number(*not this comment!*)' \
                          '  \n* The number must be **between {1} and {2}**' \
                          '  \n* *Only one number in your comment will be accepted and only' \
                          ' one comment will be checked!*' \
                          '  \n* *Comments will be processed in order by date, oldest first*' \
                          '  \n* Code(s) will be sent by PM.  \n' \
                          '  \nWinner selection will be around: ' \
                          '*[{3} UTC](http://www.wolframalpha.com/input/?i={3}+UTC+To+Local+Time)*' \
                          '  \n  \n' \
                          '  \n*Minimum account requirements:*  \n' \
                          '  \n    {4} post karma' \
                          '  \n    {5} comment karma' \
                          '  \n    {6} days old  \n' \
                          '  \n*Number of winners to pick: {7}*  \n' \
                          '  \n*^Upvote ^for ^visibility, ^this ^comment ^will ^be ^edited ^with ^the ^results.*  \n' \
                          '  \n*^Check ^the ^comment ^below ^to ^see ^what ^numbers ^have ^already ^been ^used.*'

giveaway_comment_keyword = 'A **keyword guess** giveaway has been started for this post by **/u/{0}**!  \n' \
                           '  \n To participate **reply to the OP** with a keyword guess (*not this comment!*)  \n' \
                           '  \n* Check the OP for clues on what the keyword(s) might be!' \
                           '  \n* *Comments longer than 300 characters (inc. spaces) will be ignored!*' \
                           '  \n* *Comments will be processed in order by date, oldest first*' \
                           '  \n* Code(s) will be sent by PM.  \n' \
                           '  \nWinner selection will be around: ' \
                           '*[{1} UTC](http://www.wolframalpha.com/input/?i={1}+UTC+To+Local+Time)*' \
                           '  \n  \n' \
                           '  \n*Minimum account requirements:*  \n' \
                           '  \n    {2} post karma' \
                           '  \n    {3} comment karma' \
                           '  \n    {4} days old  \n' \
                           '  \n*Number of winners to pick: {5}*  \n' \
                           '  \n*^Upvote ^for ^visibility, ^this ^comment ^will ^be ^edited ^with ^the ^results.*'

giveaway_scheduling_failed = 'Failed to schedule giveaway **{0}**:  \n' \
                           '  \n* The bot did not detect a valid giveaway type: "random", "number", "keyword". '
giveaway_comment_failed = 'Failed to schedule giveaway **{0}**:  \n' \
                           '  \n* The bot was unable to create a comment in the giveaway post.  '
# ----------------------------------------------------------------------------------------

# ---------------- giveaway.process
giveaway_comment_end = 'The giveaway has ended!' \
                       '  \n Winner(s):' \
                       '  \n {0}' \
                       '  \n Check your inbox for your goodies!'

giveaway_comment_end_mention = 'The giveaway has ended!' \
                       '  \n Winner(s):' \
                       '  \n {0}' \
                       '  \n Congrats!'

giveaway_message_winner = 'Congratulations! You\'ve won a giveaway from /u/{0}!' \
                          '  \n Giveaway post: [{1}]({2})' \
                          '  \n Your codes(s): ' \
                          '  \n  \n    {3}'

giveaway_message_requester = 'Your giveaway has ended!' \
                       '  \n Winner(s):' \
                       '  \n {0}' \
                       '  \n Giveaway post: [{1}]({2})'

giveaway_error_type = 'Giveaway **ERROR:**' \
                      '  \n Unable to recognize the type of giveaway.' \
                      '  \n Something went *wrong*!'  \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n Giveaway post: [{0}]({1})' \
                      '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

giveaway_comment_error = 'Giveaway **ERROR:**' \
                      '  \n Unable to properly process the giveaway.' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n PM has been sent to OP.' \
                      '  \n Error Message: {0}'

giveaway_error_nowinner = 'Giveaway **ERROR:**' \
                      '  \n Could not find **any** winner for this giveaway.' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n Giveaway post: [{0}]({1})' \
                      '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

giveaway_error_nocomments = 'Giveaway **ERROR:**' \
                      '  \n Could not find any comments with the matching requirements.' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n Giveaway post: [{0}]({1})' \
                      '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

giveaway_comment_nowinnercomments = '**Did not find a winner for this giveaway.**' \
                                    '  \n Could not find any comments with the matching requirements!' \
                                    '  \n Giveaway has been cleared and no codes were sent out!' \
                                    '  \n PM has been sent to OP.'

giveaway_comment_nowinner = '**Did not find a winner for this giveaway.**' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n PM has been sent to OP.'

giveaway_error_enoughwinners = 'Giveaway **ERROR:**' \
                      '  \n Could not find **enough** winners vs codes for this giveaway.' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n Giveaway post: [{0}]({1})' \
                      '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

giveaway_comment_enoughwinner = '**Did not find enough winners for this giveaway.**' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n PM has been sent to OP.'

giveaway_error_winners_accounts = 'Giveaway **ERROR:**' \
                      '  \n Could not find enough winners with valid accounts.' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n Giveaway post: [{0}]({1})' \
                      '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

giveaway_comment_winners_accounts = '**Did not find enough winners with valid accounts for this giveaway.**' \
                      '  \n Account requirements: post karma: {0}, comment karma: {1}, days old: {2}' \
                      '  \n Giveaway has been cleared and no codes were sent out!' \
                      '  \n PM has been sent to OP.'

giveaway_error_api = 'Giveaway **ERROR:**' \
                     '  \n There was a major error during the attempt to process the giveaway.' \
                     '  \n Something went wrong with the Reddit or bot API.' \
                     '  \n Giveaway has been cleared and no codes were sent out!' \
                     '  \n Giveaway post: [{0}]({1})' \
                     '  \n For more info: [Wiki](https://www.reddit.com/r/autogiveaway/wiki/error)'

# ----------------------------------------------------------------------------------------
