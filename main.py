import reddit
import utils
import config
import logging
import time



if __name__ == '__main__':
    logging.info("Starting giveaway script...")
    utils.scheduler.add_job(
        reddit.check_pms,
        'interval',
        minutes=config.check_pm_interval,
        id='CHECK_PMS',
        replace_existing=True
    )
    logging.info("Scheduled <check_pms> job at %s minutes interval.", config.check_pm_interval)

    utils.scheduler.add_job(
        reddit.check_mentions,
        'interval',
        minutes=config.check_mentions_interval,
        id='CHECK_MENTIONS',
        replace_existing=True
    )
    logging.info("Scheduled <check_mentions> job at %s minutes interval.", config.check_mentions_interval)

    utils.scheduler.add_job(
        utils.check_logs,
        'interval',
        minutes=config.check_logs,
        id='CHECK_LOGS',
        replace_existing=True
    )
    logging.info("Scheduled <check_logs> job at %s minutes interval.", config.check_logs)

    try:
        logging.info("Launching scheduler...")
        utils.scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

    logging.info("Exiting giveaway script...")