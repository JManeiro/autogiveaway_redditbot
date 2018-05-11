import logging
import utils
import config
import reddit
import datetime


def process_pm(pm):
    """ Processes giveaway PMs.
        Parameters:
            pm: [object] from praw"""
    requester = str(pm.author).lower()  # Author of the PM
    # subject = str(pm.subject).lower()  # Subject of the PM
    content = str(pm.body)  # Content of the PM
    message_id = str(pm.id)  # ID of the PM

    logging.info("%s:%s: Processing PM...", message_id, requester)
    giveaway_args = utils.parse_pm(content, requester, message_id)  # parse giveaway settings
    if giveaway_args is None:
        reddit.send_pm(requester, config.reply_subject, config.parse_errormessage, message_id, requester)
        logging.warning("%s:%s: Failed to parse pm, check formatting. Ending <process_pm> process.", message_id, requester)
        return
    codes_tmp = giveaway_args[11]
    codes = utils.parse_codes(codes_tmp[0], message_id, requester)  # parse codes
    if codes is None:
        reddit.send_pm(requester, config.reply_subject, config.codes_errormessage, message_id, requester)
        logging.warning("%s:%s: Failed to parse codes, check formatting. Ending <process_pm> process.", message_id,
                    requester)
        return
    giveaway_args.remove(giveaway_args[11])  # remove codes from giveaway_args
    # check to make sure we have enough codes for all winners
    num_winners = giveaway_args[6]
    num_codes = len(codes)
    if num_codes < num_winners:
        reddit.send_pm(requester, config.reply_subject, config.winners_errormessage
                           .format(num_winners, num_codes), message_id, requester)
        logging.warning("%s:%s: More winners than codes to give away: winners: %s, codes: %s. Ending <process_pm> process.",
                    message_id, requester, num_winners, num_codes)
        return
    identifier = str(utils.gen_code())
    setup(requester, identifier, giveaway_args, codes)
    logging.info("%s:%s: Processed OK, identifier assigned: %s", message_id, requester, identifier)


def process_mention(mention):
    """ Processes user mentions."""
    requester = str(mention.author).lower()  # Author of the mention
    # subject = str(mention.subject).lower()  # Subject of the mention
    content = str(mention.body)  # Content of the mention
    parent_id = str(mention.parent_id)  # parent ID of the mention
    comment_id = str(mention.name)  # comment id

    logging.info("%s:%s: Processing User Mention...", parent_id, requester)

    # get info for comment
    comment_id = comment_id.replace("t1_", "")
    comment = reddit.get_comment(comment_id)

    # check whether mention is a top level comment
    if "t3_" in parent_id:
        post_id = parent_id.replace("t3_", "")
    else:
        logging.info("%s:%s: Mention is not a top level comment. Ending <process_mention> process.", parent_id, requester)
        error = "  \n User mention must be a top level comment. "
        reddit.post_comment(comment, config.parse_mention_errormessage + error, parent_id, requester)
        return

    # get info for post
    post = reddit.get_post(post_id)
    post_author = str(post.author).lower()

    # only OP should be able to run the giveaway
    if requester == post_author:
        logging.info("%s:%s: Requester matches giveaway OP, processing request.", parent_id, requester)

        giveaway_args = utils.parse_pm(content, requester, parent_id)
        if giveaway_args is None:
            error = "  \n Double check the formatting and try again."
            reddit.post_comment(comment, config.parse_mention_errormessage + error, parent_id, requester)
            logging.warning("%s:%s: Failed to parse arguments, check formatting. Ending <process_mention> process.",
                        parent_id, requester)
            return

        # args OK, launch giveaway
        identifier = str(utils.gen_code())
        job_id_mention = '%s:%s:PROCESS_MENTION' % (identifier, requester)
        codes = None
        utils.scheduler.add_job(process, id=job_id_mention,
                                args=[requester, identifier, giveaway_args, codes, post, comment])
        logging.info("%s:%s: Completed, OK", parent_id, requester)
    else:
        error = "  \n Only the OP can run a giveaway in this post.  \n ^Your ^username ^does ^not ^match ^OP."
        reddit.post_comment(comment, config.parse_mention_errormessage + error, parent_id, requester)
        logging.info("%s:%s: Requester does not match giveaway OP. Ending <process_mention> process.", parent_id, requester)
        return


def setup(requester, identifier, giveaway_args, codes):
    """ Initializes giveaway by asking requester to identify giveaway post with 6 digit code, adds
        check_post job to apscheduler and end_job.
        Parameters:
            requester:      [string] reddit username
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            codes:          [list] parsed giveaway codes"""
    logging.info("%s:%s: Initiating setup...", identifier, requester)
    # send message asking to setup giveaway post
    sent = reddit.send_pm(requester, config.reply_subject, config.setup_message
                              .format(str(config.check_post_timeout), identifier), identifier, requester)
    # if PM was not sent successfully, don't bother setting anything up
    if not sent:
        logging.error("%s:%s: Was unable to send PM with setup information. Ending <setup> process.", identifier, requester)
        return
    # add job to check for post
    job_id_checkpost = '%s:%s:CHECK_POST' % (identifier, requester)
    utils.scheduler.add_job(reddit.check_post, 'interval', minutes=config.check_post_interval, id=job_id_checkpost,
                            args=[requester, identifier, giveaway_args, codes])
    # get timedelta for when to stop
    request_timeout = datetime.datetime.now() + datetime.timedelta(minutes=config.check_post_timeout)
    # end job of checking for post if timeout is reached
    job_id_endjob = '%s:%s:END_JOB' % (identifier, requester)
    utils.scheduler.add_job(utils.end_job, 'date', run_date=request_timeout, id=job_id_endjob,
                            args=[job_id_checkpost, "Giveaway post not found within the time limit."])
    logging.info("%s:%s: Completed, OK", identifier, requester)


def schedule(requester, identifier, giveaway_args, codes, post):
    """ Posts comment on giveaway post and schedules giveaway by adding process to apscheduler.
        Parameters:
            requester:      [string] reddit username
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            codes:          [list] parsed giveaway codes
            post:           [object] from praw"""
    logging.info("%s:%s: Scheduling...", identifier, requester)
    giveaway_type = giveaway_args[0]
    date = giveaway_args[1]
    string_date = date.strftime("%d-%b-%Y %H:%M")
    num_winners = giveaway_args[6]
    pkarma = giveaway_args[8]
    ckarma = giveaway_args[9]
    days = giveaway_args[10]
    numbers_comment = None
    if giveaway_type == 'random':
        comment = reddit.post_comment(post, config.giveaway_comment_random
                                          .format(requester, string_date, pkarma, ckarma, days, num_winners),
                                          identifier, requester)
    else:
        if giveaway_type == 'number':
            min_number = giveaway_args[3]
            max_number = giveaway_args[4]
            comment = reddit.post_comment(post, config.giveaway_comment_number
                                              .format(requester, min_number, max_number,
                                                      string_date, pkarma, ckarma, days, num_winners),
                                              identifier, requester)
            # comment to track numbers used
            numbers_comment = reddit.post_comment(comment, 'Numbers already posted will be added here.'
                                                               '  \n ^This ^comment ^updates ^every ^{0} ^minutes.'
                                                      .format(config.update_numbers_interval), identifier, requester)
        else:
            if giveaway_type == 'keyword':
                comment = reddit.post_comment(post, config.giveaway_comment_keyword
                                                  .format(requester, string_date, pkarma, ckarma, days, num_winners),
                                                  identifier, requester)
            else:
                sent = reddit.send_pm(requester, config.reply_subject,
                                          config.giveaway_comment_failed.format(identifier), identifier, requester)
                if not sent:
                    logging.error("%s:%s: No giveaway type detected, failed to send PM. Ending <schedule> process.",
                              identifier, requester)
                    return
                else:
                    logging.error("%s:%s: No giveaway type detected, PM sent. Ending <schedule> process.",
                              identifier, requester)
                    return

    if comment:
        # schedule job to process giveaway
        job_id = '%s:%s:PROCESS' % (identifier, requester)
        utils.scheduler.add_job(process, 'date', run_date=date, id=job_id,
                                args=[requester, identifier, giveaway_args, codes, post, comment])

        # if giveaway is of number type, create job to track numbers used
        if numbers_comment:
            job_id = '%s:%s:UPDATE_NUMBERS' % (identifier, requester)
            utils.scheduler.add_job(utils.update_numbers, 'interval', minutes=config.update_numbers_interval, id=job_id,
                                    args=[requester, identifier, giveaway_args, post, numbers_comment])

        logging.info("%s:%s: Completed, OK", identifier, requester)
    else:
        # failed to create comment
        # send PM informing that giveaway was not scheduled
        sent = reddit.send_pm(requester, config.reply_subject, config.giveaway_scheduling_failed
                                  .format(identifier), identifier, requester)
        if not sent:
            logging.error("%s:%s: Failed to post giveaway comment, failed to send PM. Ending <schedule> process.",
                      identifier, requester)
            return
        else:
            logging.error("%s:%s: Failed to post giveaway comment, PM was sent. Ending <schedule> process.",
                      identifier, requester)
            return


def process(requester, identifier, giveaway_args, codes, post, comment):
    """ Processes the giveaway, gets winners, edits giveaway comment, notifies requester of end or errors.
        Parameters:
            requester:      [string] reddit username
            identifier:     [string] unique 6 digit
            giveaway_args:  [list] parsed giveaway arguments
            codes:          [list] parsed giveaway codes
            post:           [object] from praw
            comment:        [object] from praw"""

    logging.info("%s:%s: Running giveaway...", identifier, requester)
    giveaway_type = giveaway_args[0]
    is_mention = giveaway_args[7]
    winner_comment = None
    error_codes = False
    pm_message = None
    post_comment = None
    log_msg1 = None
    log_msg2 = None

    if giveaway_type == 'random':
        winner = utils.random_winner(requester, identifier, giveaway_args, post)
    else:
        winner, winner_comment = utils.pick_winner(requester, identifier, giveaway_args, post)
    # Handle errors if they happen or dish out the codes
    if winner is -1:  # 0 comments on post
        pm_message = config.giveaway_error_nocomments
        post_comment = config.giveaway_comment_nowinnercomments
        log_msg1 = "%s:%s: No comments found in post, failed to send PM."
        log_msg2 = "%s:%s: No comments found in post, PM was sent."
        error_codes = True

    if winner is -2:  # not enough winners vs codes were found
        pm_message = config.giveaway_error_enoughwinners
        post_comment = config.giveaway_comment_enoughwinner
        log_msg1 = "%s:%s: Not enough winners found, failed to send PM. Ending <process> process."
        log_msg2 = "%s:%s: Not enough winners found, PM was sent. Ending <process> process."
        error_codes = True

    if winner is -3:  # api problems
        pm_message = config.giveaway_error_api
        log_msg1 = "%s:%s: There was an API/Reddit error, failed to send PM. Ending <process> process."
        log_msg2 = "%s:%s: There was an API/Reddit error, PM was sent. Ending <process> process."
        error_codes = True

    if winner is -4:  # not enough winners with valid accounts
        pm_message = config.giveaway_error_winners_accounts
        post_comment = config.giveaway_comment_winners_accounts.format(
            giveaway_args[8], giveaway_args[9], giveaway_args[10])
        log_msg1 = "%s:%s: Not enough winners with valid accounts found, failed to send PM. Ending <process> process."
        log_msg2 = "%s:%s: Not enough winners with valid accounts found, PM was sent. Ending <process> process."
        error_codes = True

    if error_codes:
        sent = reddit.send_pm(requester, config.reply_subject, pm_message.
                                  format(post.title, post.permalink), identifier, requester)
        if not is_mention:
            if post_comment:
                reddit.edit_comment(comment, post_comment, identifier, requester)

            if giveaway_type == 'number':
                job_id = '%s:%s:UPDATE_NUMBERS' % (identifier, requester)
                utils.end_job(job_id, "Giveaway ended for Identifier: {0} : end_job:update_numbers".format(identifier))

        if not sent:
            logging.error(log_msg1, identifier, requester)
            return
        else:
            logging.error(log_msg2, identifier, requester)
            return
    else:
        str_winner = ''
        if not is_mention:
            # distribute codes and send PMs
            str_winner = utils.giveaway_codes(requester, identifier, winner, codes, post)
        # end update numbers job
        if giveaway_type == 'number':
            job_id = '%s:%s:UPDATE_NUMBERS' % (identifier, requester)
            utils.end_job(job_id, "Giveaway ended for Identifier: {0} : end_job:update_numbers".format(identifier))
        # edit giveaway comment
        if winner_comment:
            str_winner_numbers = ''
            for redditor in winner:
                redditor_comment = winner_comment[redditor]
                str_winner_numbers += '/u/%s Comment: %s  \n' % (redditor, redditor_comment)
            if is_mention:
                comment_return = reddit.post_comment(comment,
                                                         config.giveaway_comment_end_mention.format(str_winner_numbers),
                                                         identifier, requester)
            else:
                comment_return = reddit.edit_comment(comment,
                                                         config.giveaway_comment_end.format(str_winner_numbers),
                                                         identifier, requester)
        else:
            if is_mention:
                if len(winner) > 1:
                    for x in winner:
                        username = '/u/%s ' % x
                        str_winner += username
                else:
                    username = winner[0]
                    str_winner = '/u/%s ' % username
                comment_return = reddit.post_comment(comment,
                                                         config.giveaway_comment_end_mention.format(str_winner),
                                                         identifier, requester)
            else:
                comment_return = reddit.edit_comment(comment, config.giveaway_comment_end.format(str_winner),
                                                         identifier, requester)

        # log if comment editing failed
        if not comment_return:
            logging.error("%s:%s: Failed to edit comment with winners.", identifier, requester)
        logging.info("%s:%s: Completed, OK", identifier, requester)
