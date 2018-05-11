import logging
import praw
from prawcore.exceptions import PrawcoreException
from praw.exceptions import APIException, ClientException, PRAWException
import auth
import giveaway
import utils
import config
import datetime
import collections
import time


reddit = praw.Reddit(user_agent=auth.my_user_agent,
                     client_id=auth.my_client_id,
                     client_secret=auth.my_client_secret,
                     username=auth.my_username,
                     password=auth.my_password)

def get_comment(comment_id):
    """Fetches an updated comment from reddit"""
    comment = reddit.comment(id=comment_id)
    return comment


def get_post(post_id):
    """Fetches an updated post from reddit"""
    post = reddit.submission(id=post_id)
    return post


def make_link_post(title, link):
    """Makes a link post in 'autogiveaway' """
    post = reddit.subreddit('autogiveaway').submit(title, url=link, send_replies=False)
    return post


def check_pms():
    """ Checks inbox for new PMs in bot account with subject 'giveaway'"""
    logging.info("Checking for new PMs...")
    try:
        for pm in reddit.inbox.messages(limit=25):
            if pm.dest.lower() == auth.my_username and pm.new:
                if pm.subject.lower() == 'giveaway':
                    giveaway.process_pm(pm)
                else:
                    logging.info("%s:%s: Skipping pm, not a giveaway, subject: \"%s\".", pm.id, pm.author, pm.subject)
                pm.mark_read()
    except (APIException, ClientException, PRAWException, PrawcoreException) as error:
        logging.error("%s", error)
    logging.info("Completed")


def check_mentions():
    """ Checks inbox for new user mentions."""
    logging.info("Checking for new User Mentions...")
    try:
        for mention in reddit.inbox.mentions(limit=25):
            if mention.new:
                giveaway.process_mention(mention)
            mention.mark_read()
    except (APIException, ClientException, PRAWException, PrawcoreException) as error:
        logging.error("%s", error)
    logging.info("Completed")


def check_post(requester, identifier, giveaway_args, codes):
    """ Looks for identifier in recent redditor posts to find giveaway post.
        Parameters:
            requester:      [string] redditor doing giveaway
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            codes:          [list] giveaway codes
        Returns: True / False"""
    tries = 0
    redditor = None
    submissions = None
    wait_time = config.wait_time

    logging.info("%s:%s: Checking for giveaway post...", identifier, requester)

    while not redditor or not submissions and tries < config.retries:
        try:
            redditor = reddit.redditor(requester)
            submissions = list(redditor.submissions.new(limit=config.submissions_limit))
        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1

    if redditor and submissions:
        giveaway_post = None

        # noinspection PyTypeChecker
        for post in submissions:
            title = post.title
            content = post.selftext
            post_id = post.id

            foundidentifier = title.find(identifier)
            if foundidentifier is -1:
                foundidentifier = content.find(identifier)
                if foundidentifier is -1:
                    logging.info("%s:%s: No identifier found for post: %s", identifier, requester, post_id)
                else:
                    logging.info("%s%s: Identifier found in content for post: %s", identifier, requester, post_id)
                    giveaway_post = post
                    break
            else:
                logging.info("%s:%s: Identifier found in title for post: %s", identifier, requester, post_id)
                giveaway_post = post
                break

        if giveaway_post:
            job_id_self = '%s:%s:CHECK_POST' % (identifier, requester)
            job_id_end_job = '%s:%s:END_JOB' % (identifier, requester)
            logging.info("%s:%s: Giveaway post found, scheduling giveaway.", identifier, requester)
            giveaway.schedule(requester, identifier, giveaway_args, codes, giveaway_post)
            utils.end_job(job_id_self,
                          "Giveaway post found for Identifier: {0} : end_job:check_post".format(identifier))
            utils.end_job(job_id_end_job,
                          "Giveaway post found for Identifier: {0} : end_job:end_job".format(identifier))
            logging.info("%s:%s: Completed, OK", identifier, requester)
        return True
    else:
        logging.error("%s%s: Unable to check for giveaway post.", identifier, requester)
        return False


def post_comment(post, message, identifier, requester):
    """ Posts comments.
        Parameters:
            post:       [object] from praw
            message:    [string] comment to post
            identifier: [string] unique 6 digit
            requester:  [string] redditor doing giveaway
        Returns: True / False"""
    tries = 0
    comment = None
    wait_time = config.wait_time
    message += config.footer_message

    while not comment and tries < config.retries:
        try:
            comment = post.reply(message)
        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1

    if comment:
        logging.info("%s:%s: Posted comment: \"%s\"", identifier, requester, utils.comment_permalink(comment))
        return comment
    else:
        logging.error("%s:%s: Failed to post comment.", identifier, requester)
        return False


def edit_comment(comment, message, identifier, requester):
    """ Edits comments.
        Parameters:
            comment:    [object] from praw
            message:    [string] comment to post
            identifier: [string] random 6 digit
            requester:  [string] redditor doing giveaway
        Returns: True / False"""
    tries = 0
    edited_comment = None
    wait_time = config.wait_time
    message += config.footer_message

    while not edited_comment and tries < config.retries:
        try:
            edited_comment = comment.edit(message)
        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1

    if edited_comment:
        logging.info("%s:%s: Edited comment: \"%s\"", identifier, requester, utils.comment_permalink(comment))
        return True
    else:
        logging.error("%s:%s: Failed to edit comment.", identifier, requester)
        return False


def send_pm(recipient, subject, message, identifier, requester):
    """ Sends PMs
        Parameters:
            recipient:  [string] reddit username
            subject:    [string] pm subject
            message:    [string] pm body
            identifier: [string] random 6 digits
            requester:  [string] redditor doing giveaway
        Returns: True / False"""
    tries = 0
    sent = None
    wait_time = config.wait_time
    message += config.footer_message

    while not sent and tries < config.retries:
        try:
            sent = reddit.redditor(recipient).message(subject, message)
        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1

    if sent:
        logging.info("%s:%s: PM sent to: %s", identifier, requester, recipient)
        return True
    else:
        logging.error("%s:%s: Failed to send PM to: %s", identifier, requester, recipient)
        return False


def unique_users(requester, identifier, post_id):
    """ Gets a list of unique redditors and their comments (top level comments only), not including requester and bot
        Parameters:
            requester:  [string] reddit username
            identifier: [string] random 6 digits
            post_id:    [string] post id
        Returns: [list] of unique redditor usernames [string] and [dict] of unique comments with date as key
                    -1 if no comments found, False if error"""
    start = datetime.datetime.now()
    redditors = []
    comment_dict = {}
    all_comments = collections.OrderedDict()

    tries = 0
    wait_time = config.wait_time

    while not comment_dict and tries < config.retries:
        try:
            post = reddit.submission(id=post_id)
            logging.info("%s:%s: Getting unique redditors and their comments for post: %s", identifier, requester,
                     post.permalink)
            # limit=None fetches all comments from a post (high comment posts will take a long time)
            post.comments.replace_more(limit=None)
            logging.info("%s:%s: Total top-level comments fetched: %s", identifier, requester, len(post.comments))
            # If no users / comments found
            if len(post.comments) == 0:
                return -1
            # Create dict with all comments and with date as key
            comment_cnt = 0
            for comment in post.comments:
                author = str(comment.author).lower()
                if author and author != 'none' and author != requester and author != auth.my_username:
                    timestamp = comment.created_utc
                    date = datetime.datetime.fromtimestamp(timestamp)
                    comment_dict[date] = comment
                    comment_cnt += 1
                else:
                    if author == 'none':
                        logging.debug("%s:%s: Comment author is NONE (deleted comment)", identifier, requester)
                    else:
                        logging.debug("%s:%s: Skipping comment from bot or giveaway requester: %s", identifier, requester,
                                  author)

        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1
            comment_dict = {}

    if comment_dict:
        logging.info("%s:%s: Sorting by date and removing extra comments...", identifier, requester)

        # Sort comments by date, keep only first comment per redditor in ordered dict
        for key in sorted(comment_dict):
            comment = comment_dict[key]
            author = str(comment.author).lower()
            comment_date = datetime.datetime.fromtimestamp(comment.created_utc)
            logging.debug("%s:%s: Comment: %s - %s", identifier, requester, comment_date, author)
            if author not in redditors:
                redditors.append(author)
                all_comments[author] = comment
            else:
                logging.debug("%s:%s: Deleting extra comment from user: %s.", identifier, requester, author)
                del comment_dict[key]

        logging.info("%s:%s: Total comments kept: %s", identifier, requester, len(comment_dict))
        logging.info("%s:%s: Completed, OK - processing time: %s", identifier, requester, (datetime.datetime.now() - start))
        return all_comments
    else:
        logging.error("%s:%s: Failed to get unique redditors.", identifier, requester)
        return False


def check_account(redditor, pkarma, ckarma, days, identifier, requester):
    """ Checks whether redditor account meets requirements for giveaway.
        Parameters:
            redditor:   [object] reddit user
            pkarma:     [int] minimum post karma
            ckarma:     [int] minimum comment karma
            days:       [int] minimum account age
            requester:  [string] redditor doing giveaway
            identifier: [string] unique 6 digit
        Returns: True / False"""
    pkarma_ok = True
    ckarma_ok = True
    days_ok = True
    username = str(redditor)

    checked = False
    tries = 0
    wait_time = config.wait_time

    #logging.info("%s:%s: Account check for: %s", identifier, requester, username)

    while not checked and tries < config.retries:
        try:
            if pkarma > 0:
                redditor_pkarma = redditor.link_karma
                if redditor_pkarma > pkarma:
                    pkarma_ok = True
                else:
                    pkarma_ok = False
            if ckarma > 0:
                redditor_ckarma = redditor.comment_karma
                if redditor_ckarma > ckarma:
                    ckarma_ok = True
                else:
                    ckarma_ok = False
            if days > 0:
                redditor_created = redditor.created_utc
                date_created = datetime.datetime.fromtimestamp(redditor_created)
                temp = datetime.datetime.now() - date_created
                redditor_age = temp.days
                if redditor_age > days:
                    days_ok = True
                else:
                    days_ok = False
            if pkarma_ok and ckarma_ok and days_ok:
                logging.info("%s:%s: OK, account requirements met: %s", identifier, requester, username)
                checked = True
                return True
            else:
                logging.info("%s:%s: FAIL, account requirements not met: %s",
                         identifier, requester, username)
                checked = True
                return False

        except (APIException, ClientException, PRAWException, PrawcoreException) as error:
            logging.error("%s:%s: %s", identifier, requester, error)
            logging.info("%s:%s: waiting %s seconds before retrying. Retry #: %s", identifier, requester, wait_time, tries)
            time.sleep(wait_time)
            wait_time = wait_time * config.backoff_multiplier
            tries += 1

    if checked:
        logging.info("%s:%s: Account check processed OK for: %s", identifier, requester, username)
    else:
        logging.error("%s:%s: Something occurred during account check for: %s", identifier, requester, username)
