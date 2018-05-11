import logging
import random
import re
import collections
import datetime
import os
import glob

import dateparser
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pytz import utc
from pastebin import PastebinAPI
import config
import reddit
import auth

# global scheduler
# noinspection PyRedeclaration
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///giveaways.sqlite')
}
job_defaults = {
    'coalesce': True,
    # 'max_instances': 3
}

scheduler = BlockingScheduler(jobstores=jobstores, job_defaults=job_defaults, timezone=utc)
pastebin = PastebinAPI()


def giveaway_codes(requester, identifier, winner, codes, post):
    """ Distributes giveaway codes, sends PM to winners and to requester
        Parameters:
            requester:  [string] reddit username
            identifier: [string] unique 6 digit
            winner:     [list] of winner usernames [strings]
            codes:      [list] giveaway codes [strings]
            post:       [object] post from praw
        Returns: winners/redditor[string] usernames in reddit format /u/username"""
    logging.info("%s:%s: Distributing codes to winners...", identifier, requester)

    pms_to_send = []
    failed_pms = []

    if len(winner) > 1:  # if multiple winners
        sorted_codes = []
        winners = ''
        winner_list = ''
        winner_dict = {}

        # Create code list matching list size of winners
        for redditor in winner:
            winner_dict[redditor] = None
        # sort out the codes between the winners
        while len(codes) > 0:
            for redditor in winner_dict:
                old_codes = winner_dict[redditor]
                if len(codes) is 0:
                    logging.info("%s:%s: All codes have been randomly assigned to winners.", identifier, requester)
                    break
                code = random.choice(codes)
                codes.remove(code)
                if old_codes:
                    winner_dict[redditor] = '%s, %s' % (old_codes, code)
                else:
                    winner_dict[redditor] = code

        # replace spaces with coma
        for x in sorted_codes:
            y = x.replace(" ", ", ")
            index = sorted_codes.index(x)
            sorted_codes[index] = y

        # build pms that need to be sent
        # winner pms
        logging.info("%s:%s: Building list of PMs to send...", identifier, requester)
        for redditor in winner_dict:
            goodies = winner_dict[redditor].strip(',')
            logging.info("%s:%s: Adding PM for winner %s, with code: %s.",
                     identifier, requester, redditor, obfuscate(goodies))
            pm = [redditor,
                  config.reply_subject,
                  config.giveaway_message_winner.format(requester, post.title, post.permalink, goodies), identifier]
            pms_to_send.append(pm)

            # create a list of winners to send to the requester
            username = '/u/%s ' % redditor
            winners += username
            winner_list += '%s %s  \n' % (username, goodies)

        # requester pm
        logging.info("%s:%s: Adding PM for requester, %s, with winner info.", identifier, requester, requester)
        pm = [requester,
              config.reply_subject,
              config.giveaway_message_requester.format(winner_list, post.title, post.permalink),
              identifier]
        pms_to_send.append(pm)

    else:
        redditor = winner[0]
        # Split codes into string for pm
        if len(codes) > 1:
            tmp = ' '.join(codes)
            str_codes = tmp.replace(" ", ", ")
        else:
            tmp = codes[0]
            str_codes = tmp.replace(" ", ", ")
        # build pms that need to be sent
        logging.info("%s:%s: Adding PM for winner %s, with code: %s", identifier, requester, redditor, obfuscate(str_codes))
        pm = [redditor,
              config.reply_subject,
              config.giveaway_message_winner.format(requester, post.title, post.permalink, str_codes), identifier]
        pms_to_send.append(pm)

        # winner list for requester
        username = '/u/%s ' % redditor
        winner_list = '%s : %s  \n' % (username, str_codes)

        logging.info("%s:%s: Adding PM for requester, %s, with winner info.", identifier, requester, requester)
        pm = [requester,
              config.reply_subject,
              config.giveaway_message_requester.format(winner_list, post.title, post.permalink),
              identifier]
        pms_to_send.append(pm)

        winners = redditor

    # Send pms out
    logging.info("%s:%s: Sending all PMs...", identifier, requester)
    for pm in pms_to_send:
        pm_redditor = pm[0]
        pm_subject = pm[1]
        pm_message = pm[2]
        pm_identifier = pm[3]

        sent = reddit.send_pm(pm_redditor, pm_subject, pm_message, pm_identifier, requester)

        if sent:
            #logging.info("%s:%s: PM sent to: %s", identifier, requester, pm_redditor)
            continue
        else:
            logging.error("%s:%s: Failed to send PM to: %s, add to retry list.", identifier, requester, pm_redditor)
            failed_pms.append(pm)

    # if pms failed, create job to retry to send them later
    if failed_pms:
        date = datetime.datetime.now() + datetime.timedelta(minutes=config.retry_failed_pms_wait_time)
        job_id = '%s:%s:FAILED_PM_RETRY' % (identifier, requester)
        scheduler.add_job(retry_failed_pms, 'date', run_date=date, id=job_id,
                          args=[requester, identifier, failed_pms, 1])
        logging.error("%s:%s: Failed to send some PMs, scheduled retry job.", identifier, requester)

    logging.info("%s:%s: Completed, OK", identifier, requester)
    return winners


def retry_failed_pms(requester, identifier, failed_pms, retry):
    """ Retries sending PMs
            Parameters:
                requester:  [string] reddit username
                identifier: [string] unique 6 digit
                failed_pms: [list] of PMs to send [list]
                retry:      [int] number of times retried
            Returns: nothing"""
    logging.info("%s:%s: Retrying to send failed PMs for completed giveaway...", identifier, requester)
    more_failed_pms = []
    for pm in failed_pms:
        pm_redditor = pm[0]
        pm_subject = pm[1]
        pm_message = pm[2]
        pm_identifier = pm[3]

        sent = reddit.send_pm(pm_redditor, pm_subject, pm_message, pm_identifier, requester)

        if sent:
            #logging.info("%s:%s: Retry: %s -- PM sent to: %s", identifier, requester, retry, pm_redditor)
            continue
        else:
            logging.error("%s:%s: Retry: %s -- PM Failed to be sent to: %s, add to retry list.",
                      identifier, requester, retry, pm_redditor)
            more_failed_pms.append(pm)

    if more_failed_pms and retry < config.retry_failed_pms_retries:
        logging.error("%s:%s: Retry: %s -- Failed to send some PMs, another chance to retry will be added.",
                  identifier, requester, retry)
        retry += 1
        date = datetime.datetime.now() + datetime.timedelta(minutes=config.retry_failed_pms_wait_time)
        job_id = '%s:%s:FAILED_PM_RETRY_%s' % (identifier, requester, retry)
        scheduler.add_job(retry_failed_pms, 'date', run_date=date, id=job_id,
                          args=[requester, identifier, more_failed_pms, retry])
        return

    if retry >= config.retry_failed_pms_retries:
        message = ''
        for pm in more_failed_pms:
            pm_redditor = pm[0]
            message += pm_redditor + ', '
        logging.error("%s:%s: Retry: %s -- Failed to send PMs to the following redditors: %s",
                  identifier, requester, retry, message)
        return


def random_winner(requester, identifier, giveaway_args, post):
    """ Picks random winner for random giveaway type.
        Parameters:
            requester:      [string] reddit username
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            post:           [object] post object from praw
        Returns: winners[list] of reddit usernames [strings] or single reddit username winner[string]
                    -1 if no users found, -3 if error occurred"""
    num_winners = giveaway_args[6]
    pkarma = giveaway_args[8]
    ckarma = giveaway_args[9]
    days = giveaway_args[10]
    winner_list = []

    if pkarma > 0 or ckarma > 0 or days > 0:
        check_accounts = True
    else:
        check_accounts = False

    logging.info("%s:%s: Picking random winners, need: %s", identifier, requester, num_winners)

    all_comments = reddit.unique_users(requester, identifier, post.id)

    if all_comments == -1:  # No comments / users found
        logging.warning("%s:%s: 0 comments found in post. Ending <random_winner> process.", identifier, requester)
        return -1
    else:
        if not all_comments:
            logging.error("%s:%s: all_comments = False | Something went wrong. Ending <random_winner> process.",
                      identifier, requester)
            return -3
        else:
            if check_accounts:
                logging.info("%s:%s: Start check_accounts process...", identifier, requester)
                new_winner = 0
                while len(winner_list) < num_winners:
                    if not all_comments:
                        logging.warning("%s:%s: Not enough winners with valid accounts found, required: %s, found: %s."
                                    " Ending <random_winner> process.", identifier, requester, num_winners,
                                    len(winner_list))
                        return -4
                    if new_winner > 0:
                        winner = random.sample(list(all_comments), new_winner)
                        new_winner = 0  # new winners already picked so reset
                    else:
                        winner = random.sample(list(all_comments), num_winners)
                    for comment in winner:
                        author = str(all_comments[comment].author)
                        logging.info("%s:%s: Checking account: %s", identifier, requester, author)
                        valid = reddit.check_account(all_comments[comment].author, pkarma, ckarma, days,
                                                         identifier, requester)
                        if valid is not None:
                            if valid:
                                winner_list.append(author)
                                logging.info("%s:%s: Redditor added to winners list: %s", identifier, requester, author)
                                del all_comments[comment]
                            else:
                                logging.info("%s:%s: Redditor removed from possible winners: %s",
                                         identifier, requester, author)
                                del all_comments[comment]
                                new_winner += 1
                        else:
                            logging.error("%s:%s: Error during account check. Ending <random_winner> process.",
                                      identifier, requester)
                            return -3
                logging.info("%s:%s: End of check_accounts process.", identifier, requester)
            else:
                winner = random.sample(list(all_comments), num_winners)
                for comment in winner:
                    author = str(all_comments[comment].author)
                    winner_list.append(author)
                    logging.info("%s:%s: Redditor added to winners list: %s", identifier, requester, author)
            logging.info("%s:%s: Completed, OK, winners: %s", identifier, requester, winner_list)

            if len(winner_list) < num_winners:
                logging.warning("%s:%s: Not enough winners found, required: %s, found: %s. Ending <random_winner> process.",
                            identifier, requester, num_winners, len(winner_list))
                return -2
            return winner_list


def pick_winner(requester, identifier, giveaway_args, post):
    """ Picks winners for number and keyword giveaway types.
        Note on closest number pick: if two numbers are the same distance (8->6<-4) the first number will be picked (8)
        Parameters:
            requester:      [string] reddit username
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            post:           [object] post from praw
        Returns: winners[list] of reddit usernames [strings] or single reddit username winner[string]
                winner_comment[list] of winning numbers / matched keywords or single matched number/keyword[string]
                Errors: -1 if 0 comments /-2 not enough winners found/ -3 if exception API/connection"""
    giveaway_type = giveaway_args[0]
    guessnum = giveaway_args[2]
    minnum = giveaway_args[3]
    maxnum = giveaway_args[4]
    keyword = giveaway_args[5]
    num_winners = giveaway_args[6]
    pkarma = giveaway_args[8]
    ckarma = giveaway_args[9]
    days = giveaway_args[10]

    if pkarma > 0 or ckarma > 0 or days > 0:
        check_accounts = True
    else:
        check_accounts = False

    logging.info("%s:%s: Picking %s winners, need: %s", identifier, requester, giveaway_type, num_winners)

    possible_winners = {}
    winner = []
    winner_comment = {}
    keyword_winners = collections.OrderedDict()
    # get all unique top level comments
    all_comments = reddit.unique_users(requester, identifier, post.id)

    if all_comments == -1:  # No comments / users found
        logging.warning("%s:%s: 0 comments found in post. Ending <pick_winner> process.", identifier, requester)
        return -1
    else:
        if not all_comments:
            logging.error("%s:%s: all_comments = False | Something went wrong. Ending <pick_winner> process.",
                      identifier, requester)
            return -3
        else:
            if giveaway_type == 'number':
                # extract numbers from comments
                logging.info("%s:%s: Extracting numbers from comments...", identifier, requester)
                for key in all_comments:
                    comment = all_comments[key]
                    author = comment.author
                    body = comment.body
                    found = re.search("(\d+)", body)
                    if found is not None:
                        number = int(found.group(0))  # select first number that was found
                        if minnum <= number <= maxnum or minnum is 0 and maxnum is 0:
                            # check to see if someone else already got that number
                            if number not in possible_winners.values():
                                possible_winners[author] = number
                                logging.debug("%s:%s: Comment: %s - %s - %s", identifier, requester,
                                          datetime.datetime.fromtimestamp(comment.created_utc), author, number)
                            else:
                                logging.debug("%s:%s: Comment: %s - %s - %s -- Number already used", identifier, requester,
                                          datetime.datetime.fromtimestamp(comment.created_utc), author, number)
                        else:
                            logging.debug("%s:%s: Comment: %s - %s - %s -- Number out of valid range", identifier,
                                      requester,
                                      datetime.datetime.fromtimestamp(comment.created_utc), author, number)
                    else:
                        logging.debug("%s:%s: Comment: %s - %s -- No number found", identifier, requester,
                                  datetime.datetime.fromtimestamp(comment.created_utc), author)

                if not possible_winners:
                    logging.warning("%s:%s: No winners found. Ending <pick_winner> process.", identifier, requester)
                    return -1, None
                else:
                    if len(possible_winners) < num_winners:
                        logging.warning("%s:%s: Not enough winners found, required: %s, found: %s."
                                    " Ending <pick_winner> process.",
                                    identifier, requester, num_winners, len(possible_winners))
                        return -2, None
                    # pick closest numbers as winners
                    if check_accounts:
                        logging.info("%s:%s: Picking closest numbers as winners...", identifier, requester)
                        logging.info("%s:%s: Start check_accounts process...", identifier, requester)
                        while len(winner) < num_winners:
                            if not possible_winners:
                                logging.warning("%s:%s: List of possible winners exhausted. Ending <pick_winner> process.",
                                            identifier, requester)
                                return -4, None
                            temp_winner = min(possible_winners, key=lambda y: abs(int(possible_winners[y]) - guessnum))
                            inverted_possible_winners = {}
                            for key, value in possible_winners.items():
                                inverted_possible_winners[value] = key
                            value = possible_winners.get(temp_winner, None)
                            author_account = inverted_possible_winners[value]
                            author = str(inverted_possible_winners[value])
                            logging.info("%s:%s: Checking account: %s", identifier, requester, author)
                            valid = reddit.check_account(author_account, pkarma, ckarma, days,
                                                             identifier, requester)
                            if valid is not None:
                                if valid:
                                    winner.append(author)
                                    winner_comment[author] = value
                                    logging.info("%s:%s: Redditor added to winners list: %s, Number: %s", identifier,
                                             requester, author, value)
                                    del possible_winners[temp_winner]
                                else:
                                    logging.info("%s:%s: Redditor removed from possible winners: %s",
                                             identifier, requester, author)
                                    del possible_winners[temp_winner]
                            else:
                                logging.error("%s:%s: Error during account check. Ending <pick_winner> process.",
                                          identifier, requester)
                                return -3
                        logging.info("%s:%s: End of check_accounts process.", identifier, requester)
                    else:
                        logging.info("%s:%s: Picking closest numbers as winners...", identifier, requester)
                        while len(winner) < num_winners:
                            temp_winner = min(possible_winners, key=lambda y: abs(int(possible_winners[y]) - guessnum))
                            # invert possible winners to match number (which is unique) to reddit account object
                            inverted_possible_winners = {}
                            for key, value in possible_winners.items():
                                inverted_possible_winners[value] = key
                            value = possible_winners.get(temp_winner, None)
                            author = str(inverted_possible_winners[value])
                            winner.append(author)
                            winner_comment[author] = value
                            del possible_winners[temp_winner]
                            logging.info("%s:%s: Redditor added to winners list: %s, Number: %s",
                                     identifier, requester, author, value)
                    logging.info("%s:%s: Completed, OK, winners: %s", identifier, requester, winner)
                    return winner, winner_comment

            if giveaway_type == 'keyword':
                # extract matches from comments
                logging.info("%s:%s: Extracting and picking matching keyword comments...", identifier, requester)
                for key in all_comments:
                    comment = all_comments[key]
                    author = comment.author
                    body = comment.body
                    char_num = len(body)
                    if char_num < config.comment_character_limit:
                        regex = re.escape(keyword)
                        found = re.search(regex, body, re.IGNORECASE)
                        if found is not None:
                            match = found.group(0)
                            keyword_winners[author] = match  # any match found could be a winner, just add them all
                            logging.debug("%s:%s: Comment: %s - %s - %s", identifier, requester,
                                      datetime.datetime.fromtimestamp(comment.created_utc), author, match)
                        else:
                            logging.debug("%s:%s: Comment: %s - %s -- No match found", identifier, requester,
                                      datetime.datetime.fromtimestamp(comment.created_utc), author)
                    else:
                        logging.debug("%s:%s: Comment: %s - %s - %s -- Comment length limit", identifier, requester,
                                  datetime.datetime.fromtimestamp(comment.created_utc), author, char_num)
                if not keyword_winners:
                    logging.warning("%s:%s: No winners found. Ending <pick_winner> process.", identifier, requester)
                    return -1, None
                else:
                    if len(keyword_winners) < num_winners:
                        logging.warning("%s:%s: Not enough winners found, required: %s, found: %s."
                                    " Ending <pick_winner> process.",
                                    identifier, requester, num_winners, len(keyword_winners))
                        return -2, None
                    # the first matches as winners
                    keyword_winners_list = list(keyword_winners.items())
                    if check_accounts:
                        logging.info("%s:%s: Pick first matching comments as winners...", identifier, requester)
                        logging.info("%s:%s: Start check_accounts process...", identifier, requester)
                        while len(winner) < num_winners:
                            if not keyword_winners_list:
                                logging.warning("%s:%s: List of possible winners exhausted. Ending <pick_winner> process.",
                                            identifier, requester)
                                return -4, None
                            author, match = keyword_winners_list[0]
                            author_account = author
                            author = str(author)
                            logging.info("%s:%s: Checking account: %s", identifier, requester, author)
                            valid = reddit.check_account(author_account, pkarma, ckarma, days,
                                                             identifier, requester)
                            if valid is not None:
                                if valid:
                                    winner.append(author)
                                    winner_comment[author] = match
                                    logging.info("%s:%s: Redditor added to winners list: %s, Match: %s", identifier,
                                             requester, author, match)
                                    del keyword_winners_list[0]
                                else:
                                    logging.info("%s:%s: Redditor removed from possible winners: %s", identifier,
                                             requester, author)
                                    del keyword_winners_list[0]
                            else:
                                logging.error("%s:%s: Error during account check. Ending <pick_winner> process.",
                                          identifier, requester)
                                return -3
                        logging.info("%s:%s: End of check_accounts process.", identifier, requester)
                    else:
                        logging.info("%s:%s: Pick first matching comments as winners...", identifier, requester)
                        while len(winner) < num_winners:
                            author, match = keyword_winners_list[0]
                            author = str(author)
                            winner.append(author)
                            winner_comment[author] = match
                            logging.info("%s:%s: Redditor added to winners list: %s, Match: %s", identifier, requester,
                                     author, match)
                            del keyword_winners_list[0]
                    logging.info("%s:%s: Completed, OK, winners: %s", identifier, requester, winner)
                    return winner, winner_comment


def parse_codes(codes_input, message_id, requester):
    """ Extracts codes.
        Parameters:
            codes_input: [string] containing all codes sent in for giveaway.
            message_id:          [string] message id
            requester:   [string] requester username
        Returns: codes[list] of codes [strings]
                None if parsing fails"""

    if '"' in codes_input:
        logging.info("%s:%s: Parsing prices: %s", message_id, requester, codes_input)
        prizes = re.findall('\"(.+?)\"', codes_input)
        prizes = [x.strip() for x in prizes]
        logging.info("%s:%s: Completed: %s", message_id, requester, prizes)
        return prizes
    else:
        logging.info("%s:%s: Parsing codes: %s", message_id, requester, obfuscate(codes_input))
        grouped_codes = re.findall('\[(.+?)\]', codes_input)  # extract codes in brackets
        individual_codes = re.sub('\[(.+?)\]', '', codes_input)  # extract single codes only
        # split and remove whitespaces
        codes = individual_codes.split()
        codes = [x.strip() for x in codes]
        # merge grouped codes with single codes
        for x in grouped_codes:
            codes.append(x)
        # check codes for formatting
        logging.info("%s:%s: Checking codes for proper formatting, only \"A-Z a-Z 0-9 and -\" allowed ...",
                 message_id, requester)
        for code in codes:
            if ' ' in code:  # need to split the grouped codes to check one at a time
                tmp = code.split()
                for x in tmp:
                    result = re.match("^[A-Za-z0-9\-]+$", x)
                    if not result:
                        return None
            else:
                result = re.match("^[A-Za-z0-9\-]+$", code)
                if not result:
                    return None
        logging.info("%s:%s: Completed: %s", message_id, requester, obfuscate(codes))
        return codes


def gen_code():
    """ Generates random 6 digit code used as 'identifier' to track and identify giveaways."""
    return random.randint(100000, 999999)


def end_job(identifier, reason):
    """ Ends apscheduler job."""
    if scheduler.get_job(identifier) is not None:
        logging.info("%s: Reason: \"%s\"", identifier, reason)
        scheduler.remove_job(identifier)
    else:
        logging.warning("%s: Job not found", identifier)


def parse_pm(content, requester, message_id):
    """ Parses PM content.
        Parameters:
            content:    [string] PM message body
            requester:  [string] request author
            message_id:         [string] message id
        Returns: giveaway_args[list] of parsed giveaway arguments
                None if parsing fails"""
    logging.info("%s:%s: Parsing message content...", message_id, requester)

    giveaway_types = ['random', 'number', 'keyword']
    guessnum = None  # number to guess (number giveaway)
    minnum = None  # min number (number giveaway)
    maxnum = None  # max number (number giveaway)
    keyword = None  # keyword (keyword giveaway)
    winners = 1  # number of possible winners (1 default)
    is_mention = False  # is a user mention message?
    pkarma = 0  # winner account post karma check?
    ckarma = 0  # winner account comment karma check?
    days = 0  # winner account days check?

    if "/u/autogiveaway" in content:
        content = content.replace("/u/autogiveaway", "")
        is_mention = True

    tmp_args = content.split(',')  # separate content
    tmp_args = [x.strip() for x in tmp_args]  # remove beginning and trailing white spaces

    first_arg = tmp_args[0].lower()  # grab first arg to figure out what we are dealing with
    found = re.search("((?:[a-z][a-z]+))", first_arg)  # find words only
    if found:
        giveaway_type = found.group(0)  # select first word that was found
    else:
        logging.warning("%s:%s: No words found, found = None. Ending <parse_pm> process.", message_id, requester)
        return None

    if giveaway_type in giveaway_types:
        # if type 'number' then extract the numbers
        if giveaway_type == 'number':
            tmp = first_arg.split(':')
            guessnum = int(tmp[1])
            minnum = int(tmp[2])
            maxnum = int(tmp[3])
            if guessnum < 0 or minnum < 0 or maxnum < 0:
                logging.warning("%s:%s: No valid numbers found for number giveaway. Ending <parse_pm> process.",
                            message_id, requester)
                return None
        # if type 'keyword' then extract the keyword
        if giveaway_type == 'keyword':
            tmp = first_arg.split(':')
            keyword = tmp[1].strip().lower()
            if not keyword:
                logging.warning("%s:%s: No keyword found for keyword giveaway provided. Ending <parse_pm> process.",
                            message_id, requester)
                return None
        if is_mention:
            # remove giveaway type and give current date & time
            date = datetime.datetime.now()
            tmp_args.remove(tmp_args[0])
        else:
            # get date and parse it
            date = dateparser.parse(tmp_args[1],
                                    settings={'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC', 'STRICT_PARSING': True,
                                              'DATE_ORDER': 'MDY'})
            if not date or date < (datetime.datetime.now()):
                logging.warning("%s:%s: Bad date provided. Ending <parse_pm> process.", message_id, requester)
                return None
            # remove date args from tmp_args
            tmp_args.remove(tmp_args[0])
            tmp_args.remove(tmp_args[0])
        # process rest of args
        argcnt = 0  # track how many args we run through
        for arg in tmp_args:
            if arg.isdigit():
                winners = int(arg)
                argcnt += 1
            if 'pkarma:' in arg.lower():
                tmp = arg.split(':')
                try:
                    pkarma = int(tmp[1])
                except IndexError as error:
                    logging.error("%s:%s: pkarma value not found. Error: %s", message_id, requester, error)
                    return None
                argcnt += 1
            if 'ckarma:' in arg.lower():
                tmp = arg.split(':')
                try:
                    ckarma = int(tmp[1])
                except IndexError as error:
                    logging.error("%s:%s: ckarma value not found. Error: %s", message_id, requester, error)
                    return None
                argcnt += 1
            if 'days:' in arg.lower():
                tmp = arg.split(':')
                try:
                    days = int(tmp[1])
                except IndexError as error:
                    logging.error("%s:%s: days value not found. Error: %s", message_id, requester, error)
                    return None
                argcnt += 1
        # remove processed args from tmp_args to leave only the codes
        if argcnt > 0:
            del tmp_args[0:argcnt]
        if is_mention:
            giveaway_args = [giveaway_type, date, guessnum, minnum, maxnum, keyword, winners, is_mention, pkarma,
                             ckarma, days]
            logging.info("%s:%s: Return: \"%s\"", message_id, requester, giveaway_args)
        else:
            giveaway_args = [giveaway_type, date, guessnum, minnum, maxnum, keyword, winners, is_mention, pkarma,
                             ckarma, days, tmp_args]
            codes = tmp_args[0]
            # Check if leftover values actually look like codes
            #if '-' not in codes:
             #   logging.error("%s:%s: No dashes '-' found in codes string.", message_id, requester)
             #   return None
            logging.info("%s:%s: Return: \"%s %s\"", message_id, requester, giveaway_args[0:11], obfuscate(codes))
        return giveaway_args
    else:  # no type specified, just do random
        # check to see if first arg is a date or time
        date = dateparser.parse(tmp_args[0],
                                settings={'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC', 'STRICT_PARSING': True,
                                          'DATE_ORDER': 'MDY'})
        if date and not date < (datetime.datetime.now()):
            giveaway_type = 'random'  # set to default random giveaway
            tmp_args.remove(tmp_args[0])  # remove date
            giveaway_args = [giveaway_type, date, guessnum, minnum, maxnum, keyword,
                             winners, is_mention, pkarma, ckarma, days, tmp_args]
            if not tmp_args:
                logging.warning("%s:%s: No codes provided. Ending <parse_pm> process.", message_id, requester)
                return None
            codes = tmp_args[0]
            logging.info("%s:%s: Return: \"%s %s\"", message_id, requester, giveaway_args[0:11], obfuscate(codes))
            return giveaway_args
        else:
            logging.warning("%s:%s: No valid input to parse or bad date provided. Ending <parse_pm> process.",
                        message_id, requester)
            return None


def update_numbers(requester, identifier, giveaway_args, post, bot_comment):
    """ Updates a comment with the numbers from the top comments in a numbers giveaway post."""
    numbers = []
    string_numbers = ''
    min_num = giveaway_args[3]
    max_num = giveaway_args[4]

    logging.info("%s:%s: Updating numbers used in giveaway...", identifier, requester)
    # get all top level comments
    all_comments = reddit.unique_users(requester, identifier, post.id)

    if all_comments == -1:  # No comments / users found
        logging.warning("%s:%s: 0 comments found. Ending <update_numbers> process.", identifier, requester)
        return
    else:
        if not all_comments:
            logging.error("%s:%s: all_comments = False | Something went wrong. Ending <update_numbers> process.",
                      identifier, requester)
            return
        else:
            # extract numbers from comments
            logging.info("%s:%s: Extracting numbers from comments...", identifier, requester)
            for key in all_comments:
                comment = all_comments[key]
                author = comment.author
                body = comment.body
                found = re.search("(\d+)", body)
                if found is not None:
                    number = int(found.group(0))  # select first number that was found
                    if min_num <= number <= max_num:
                        numbers.append(number)
                        logging.debug("%s:%s: Comment from: %s, Number: %s", identifier, requester, author, number)
                else:
                    logging.debug("%s:%s: Comment from: %s, No number found.", identifier, requester, author)

            tmp_set = set(numbers)
            unique_numbers = sorted(list(tmp_set))
            for x in unique_numbers:
                string_numbers += '%s, ' % str(x)

            # get old pastebin code to delete it
            old_comment = reddit.get_comment(bot_comment.id)
            old_comment_body = old_comment.body
            old_pastebin_url = re.search("(?:pastebin\.com/\w*)", old_comment_body)
            if old_pastebin_url:
                logging.info("%s:%s: Deleting old pastebin post...", identifier, requester)
                pastebin_code = old_pastebin_url.group(0)
                code = re.sub('(?:pastebin\.com/)', '', pastebin_code)
                pastebin_delete(code, identifier)

            # paste list of numbers to pastebin
            logging.info("%s:%s: Posting numbers to pastebin...", identifier, requester)
            title = '{0} - /r/{1}'.format(post.title, post.subreddit)
            paste = '{0} \n\n {1}'.format(post.url, string_numbers)
            pastebin_url = pastebin_paste(paste, title, None, '1H', identifier)

            # edit comment linking pastebin
            message = '[List of numbers already posted - Pastebin.com]({0})  ' \
                      '\n ^This ^comment ^updates ^every ^{1} ^minutes.  ' \
                      '\n ^Link ^might ^be ^down ^temporarily ^during ^update.' \
                .format(pastebin_url, config.update_numbers_interval)

            logging.info("%s:%s: Updating giveaway comment with new pastebin link...", identifier, requester)
            reddit.edit_comment(bot_comment, message, identifier, requester)
            logging.info("%s:%s: Completed, OK", identifier, requester)


def obfuscate(codes_string):
    """ Obfuscates codes in the log files"""
    codes = ''
    # if passed var is list convert to string
    if isinstance(codes_string, list):
        for x in codes_string:
            codes += ' ' + x
    else:
        codes = codes_string

    obfuscated = ''
    if ' ' in codes:  # multiple codes
        codes_list = codes.split()
        for code in codes_list:
            remove_dash = re.sub('(-)', '', code)  # don't want to count dashes
            half_code = int(len(remove_dash) / 2)
            obs_code = re.sub('(\w|\d)', '*', code, count=half_code)  # replace half the code with asterisks
            obfuscated += ' ' + obs_code
    else:  # single code
        remove_dash = re.sub('(-)', '', codes)  # don't want to count dashes
        half_code = int(len(remove_dash) / 2)
        obfuscated = re.sub('(\w|\d)', '*', codes, count=half_code)
    return obfuscated


def comment_permalink(comment):
    """ Builds a working permalink for comments"""
    post_id = comment.parent_id[3:]
    permalink = "/r/%s/comments/%s/_/%s" % (str(comment.subreddit), post_id, comment.id)
    return permalink


def pastebin_paste(text, title, paste_format, expiration, identifier):
    """ Creates a new paste page in pastebin.com under user: autogiveaway
        Returns: URL of paste"""
    paste_url = pastebin.paste(
        auth.pastebin_api_dev_key,
        text,
        api_user_key=auth.pastebin_api_user_key,
        paste_name=title,
        paste_format=paste_format,  # http://pastebin.com/api#5
        paste_private='unlisted',  # Public/Unlisted/Private
        paste_expire_date=expiration  # 1H=1 Hour/1M=1 Month
    )

    logging.info("%s: %s", identifier, paste_url)
    return paste_url


def pastebin_delete(code, identifier):
    """ Deletes pastebin pages"""
    logging.info("%s: Deleting pastebin.com/%s", identifier, code)
    pastebin.delete_paste(
        auth.pastebin_api_dev_key,
        auth.pastebin_api_user_key,
        code
    )


def check_logs():
    logging.info("Checking logs...")
    date = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    title = date + ' - Autogiveaway Log'
    data = None
    log_file = None
    # find saved log file
    old_log_pattern = config.logs_path + '.*'
    if glob.glob(old_log_pattern):
        for name in glob.glob(old_log_pattern):
            log_file = name
        logging.info("Log file found...")
        #  get file data
        try:
            my_file = open(log_file, 'r')
            data = my_file.read()
            my_file.close()
        except IOError as error:
            logging.info("Error while trying to open log file: %s", error)
        # post to pastebin
        if data:
            logging.info("Uploading to pastebin...")
            pastebin_url = pastebin_paste(data, title, 'apache', '1M', 'Log file upload... ')
            if pastebin_url:
                logging.info("Deleting log file...")
                os.remove(log_file)
                logging.info("Posting new log file link to /r/autogiveaway...")
                reddit.make_link_post(title, pastebin_url)
                logging.info("Completed")
            else:
                logging.warning("Uploading failed?, keeping log file.")
        else:
            logging.error("Failed to get data from log file.")
    else:
        logging.info("No log file found.")
        return

