import argparse
import sys
import os
import time
import yaml

from datetime import datetime
from datetime import date
from datetime import timedelta

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


def main(argv):
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
  options = parser.parse_args()

  urls_dict = parse_urls_config(options.urls_config)
  if not urls_dict:
    sys.stderr.write('URLs config must not be empty\n')
    return 1

  for url_name in urls_dict.keys():
    path = os.path.join(options.out_folder, url_name)
    if not os.path.exists(path):
      os.makedirs(path)

  driver_options = webdriver.ChromeOptions()
  driver_options.add_argument('window-size={},{}'.format(
    options.window_width, options.window_height))

  while True:
    next_screenshot_time = calculate_next_screenshot_time(options.period_seconds)
    now = datetime.now()
    sleep_time = (next_screenshot_time-now).total_seconds()
    if sleep_time > 0:
      time.sleep(sleep_time)

    with webdriver.Remote(
            command_executor=options.remote_selenium_webdriver_address,
            desired_capabilities=DesiredCapabilities.CHROME,
            options=driver_options) as driver:

      for url_name, url in urls_dict.items():
        name = '{}.png'.format(next_screenshot_time.strftime(options.datetime_format))
        path = os.path.join(options.out_folder, url_name, name)

        driver.get(url)
        driver.get_screenshot_as_file(path)


def parse_urls_config(path):
  with open(path, 'r') as f:
    config = yaml.safe_load(f)

  result = {}
  for item in config['urls']:
    result[item['name']] = item['url']
  return result


def calculate_next_screenshot_time(period_seconds):
  now = datetime.now()
  today = date.today()
  next_possible_result = datetime.combine(today, datetime.min.time())
  while next_possible_result < now:
    next_possible_result = next_possible_result + timedelta(seconds=period_seconds)
  return next_possible_result


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))