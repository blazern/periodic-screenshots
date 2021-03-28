import argparse
import logging
import os
import sys
import time
import yaml

from datetime import datetime
from datetime import date
from datetime import timedelta

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


def main(argv):
  logging.getLogger().setLevel(logging.INFO)

  parser = argparse.ArgumentParser(
    description='Periodically takes screenshots of given URLs using Selenium')
  parser.add_argument('--out-folder', required=True,
                      help='Folder which will be used to store all the screenshots')
  parser.add_argument('--period-seconds', required=True, type=int,
                      help='Seconds waited before next group of screenshots is taken. '
                           + 'To make all times of screenshots round, each day is split into '
                           + 'time periods of the provided by the parameter size, and the first '
                           + 'screenshot will be taken at the start next such a peiod. '
                           + 'For example, if you specify "3600" (1 hour) and current time is '
                           + '13:45, the first screenshot will be taken in 15 minutes at 14:00.')
  parser.add_argument('--skipped-periods', help='List of time periods which should be skipped. '
                           + 'Next format is supported: "13:15,10 18:03,20", where '
                           + '13:15 is time period start and 10 is how many minutes should be skipped.')
  parser.add_argument('--urls-config', required=True, help='YAML config with URLs. See the '
                           + '"example_urls_format.yaml" file to understand expected format. '
                           + 'Name of each of the "urls" array entries is used to create a subfolder '
                           + 'in --out-folder and screenshots are put there.')
  parser.add_argument('--window-width', required=True, type=int,
                      help='Selenium browser window width')
  parser.add_argument('--window-height', required=True, type=int,
                      help='Selenium browser window width')
  parser.add_argument('--remote-selenium-webdriver-address', required=True)
  parser.add_argument('--datetime-format', default='%Y_%m_%d__%H_%M_%S',
                      help='Format which will be used to name created screenshots')
  parser.add_argument('--wait-for-url-load-seconds', type=int, default=10,
                      help='How many seconds to wait for url to get loaded before taking a screenshot')
  options = parser.parse_args()

  urls_dict = parse_urls_config(options.urls_config)
  if not urls_dict:
    logging.error('URLs config must not be empty, but it is. Path: {}'
      .format(options.urls_config))
    return 1

  for url_name, url in urls_dict.items():
    path = os.path.join(options.out_folder, url_name)
    if os.path.exists(path):
      logging.info('Found folder {} for url {}'.format(path, url))
    else:
      os.makedirs(path)
      logging.info('Created folder {} for url {}'.format(path, url))

  skipped_periods_str = None
  if options.skipped_periods:
    periods = periods_arg_to_periods(options.skipped_periods)
    skipped_periods_str = map(
        lambda p: '{}-{}'.format(p[0].strftime('%H:%M'), p[1].strftime('%H:%M')),
        periods)
    skipped_periods_str = ' '.join(skipped_periods_str)
  logging.info('Skipped periods: {}'.format(skipped_periods_str))

  driver_options = webdriver.ChromeOptions()
  driver_options.add_argument('window-size={},{}'.format(
    options.window_width, options.window_height))

  while True:
    next_screenshot_time = calculate_next_screenshot_time(
      options.period_seconds,
      options.skipped_periods)
    now = datetime.now()
    sleep_time = (next_screenshot_time-now).total_seconds()
    if sleep_time > 0:
      logging.info('Now: ({}), next screenshots time: ({}), sleeping for {} seconds'
        .format(now, next_screenshot_time, sleep_time))
      time.sleep(sleep_time)

    logging.info('Connecting to remote Selenium')
    with webdriver.Remote(
            command_executor=options.remote_selenium_webdriver_address,
            desired_capabilities=DesiredCapabilities.CHROME,
            options=driver_options) as driver:

      for url_name, url in urls_dict.items():
        now = datetime.now()
        name = '{}.png'.format(now.strftime(options.datetime_format))
        path = os.path.join(options.out_folder, url_name, name)

        logging.info('Opening url "{}" with value {}'.format(url_name, url))
        driver.get(url)
        logging.info('Waiting {} seconds for url "{}" with value {} to load'
          .format(options.wait_for_url_load_seconds, url_name, url))
        time.sleep(options.wait_for_url_load_seconds)
        logging.info('Taking screenshot of url "{}" with value {}'.format(url_name, url))
        driver.get_screenshot_as_file(path)
        logging.info('Saving screenshot to {}'.format(path))


def parse_urls_config(path):
  with open(path, 'r') as f:
    config = yaml.safe_load(f)

  result = {}
  for item in config['urls']:
    result[item['name']] = item['url']
  return result


def calculate_next_screenshot_time(period_seconds, skipped_periods_arg):
  now = datetime.now()
  next_possible_result = datetime.combine(date.today(), datetime.min.time())
  while (next_possible_result < now
         or should_time_be_skipped(next_possible_result, skipped_periods_arg)):
    next_possible_result = next_possible_result + timedelta(seconds=period_seconds)
  return next_possible_result


def should_time_be_skipped(time, skipped_periods_arg):
  if not skipped_periods_arg:
    return False

  periods = periods_arg_to_periods(skipped_periods_arg)

  for period in periods:
    if period[0] <= time and time <= period[1]:
      logging.info('Time ({}) is skipped due to provided skipped peiod {}-{}'
        .format(time, period[0].strftime('%H:%M'), period[1].strftime('%H:%M')))
      return True

  return False


def periods_arg_to_periods(periods_strs):
  periods_strs = periods_strs.split(' ')
  def period_str_to_period(period_str):
    (time, duration) = period_str.split(',')
    today_str = date.today().strftime('%d.%m.%Y')
    period_start = datetime.strptime(
      '{} {}'.format(today_str, time),
      '%d.%m.%Y %H:%M')
    period_end = period_start + timedelta(minutes=int(duration))
    return (period_start, period_end)
  periods = list(map(period_str_to_period, periods_strs))
  return periods

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))