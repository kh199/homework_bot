import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from simplejson.errors import JSONDecodeError
from telegram.error import TelegramError

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(sys.stdout)
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Message send: {message}')
    except TelegramError as error:
        logger.error(f'Failed sending message: {error}')


def get_api_answer(current_timestamp):
    """Отправляем запрос к API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception('Failed request to API')
        logger.info('Got response')
        return response.json()
    except JSONDecodeError:
        logger.error('JSON Decode Error')
    except requests.exceptions.HTTPError as HTTPError:
        status_code = response.status_code
        logger.error(f'Failed request to API: {HTTPError} {status_code}')
    except requests.exceptions.ConnectionError as ConnectionError:
        logger.error(f'Failed request to API: {ConnectionError}')
    except requests.exceptions.Timeout as Timeout:
        logger.error(f'Failed request to API: {Timeout}')
    except requests.exceptions.RequestException as RequestException:
        logger.error(f'Failed request to API: {RequestException}')


def check_response(response):
    """Проверяем ответ API на корректность."""
    if type(response) == dict:
        if 'homeworks' in response:
            homework = response['homeworks']
            if homework is not None:
                if (type(homework) == list):
                    if (len(homework) != 0):
                        return homework[0]
                    else:
                        raise Exception("Empty homework list")
                else:
                    raise Exception("Homework type is not list")
            else:
                raise Exception("Homeworks not found")
        else:
            raise KeyError("Key is not in dict")
    else:
        raise TypeError("Response is not dict")


def parse_status(homework):
    """Проверяем статус работы."""
    if 'homework_name' in homework:
        if 'status' in homework:
            if homework['status'] in HOMEWORK_STATUSES:
                homework_name = homework['homework_name']
                homework_status = homework['status']
                verdict = HOMEWORK_STATUSES[homework_status]
                return (f'Изменился статус проверки работы '
                        f'"{homework_name}". {verdict}')
            else:
                raise KeyError("Homework status is not in dict")
        else:
            raise KeyError("Homework status key is not in dict")
    else:
        raise KeyError("Homework name key is not in dict")


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens_exist = True
    if PRACTICUM_TOKEN is None:
        tokens_exist = False
    if TELEGRAM_TOKEN is None:
        tokens_exist = False
    if TELEGRAM_CHAT_ID is None:
        tokens_exist = False
    return tokens_exist


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    while True:
        try:
            if check_tokens():
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                if homework:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
                    current_timestamp = response.get(
                        'current_date', current_timestamp
                    )
                time.sleep(RETRY_TIME)
            logger.critical("Unavailable variable")
            raise SystemExit
        except Exception as error:
            logger.error(error, exc_info=True)
            message = f'Сбой в работе программы: {error}'
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
