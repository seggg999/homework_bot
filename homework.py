import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import APIError, SendError, StatusError

load_dotenv()

# Переменные окружения
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600  # Периодичность опроса ботом эндпоинта
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

old_message = ['']  # Хранит старое отправленное сообщение


logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s], %(asctime)s, [%(name)s.%(lineno)d], %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('log')


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        if old_message[0] != message:
            old_message[0] = message
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logger.info(f'В Telegram чат отправлено сообщение: "{message}".')
    except Exception as error:
        raise SendError(f'Ошибка [{error}]. Сообщение "{message}",'
                        f' в Telegram чат не отправленно!')


def get_api_answer(current_timestamp):
    """Функция делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    status = response.status_code
    if status == 200:
        logger.debug(f'Запрос к API-сервису [{ENDPOINT}] выполнен успешно'
                     f' код ответа: {status}')
    else:
        raise APIError(f'Ошибка запроса к API-сервису [{ENDPOINT}]:'
                       f' Сервис недоступен код ответа: {status}!')
    return response.json()


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(f'Ошибка: API не корректно {response}, отсутствует'
                        ' словарь в ответе!')
    response_homeworks = response.get('homeworks')
    if not isinstance(response_homeworks, list):
        raise TypeError('Ошибка: API не корректно, в словаре ответа'
                        f' "response["homeworks"]={response_homeworks}"'
                        f' отсутствует список!')
    logger.debug(f'API корректно ["homeworks"] = {response_homeworks}.')
    return response_homeworks


def parse_status(homework):
    """Функция получает статус домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('Ошибка: API не корректно, в homework'
                        ' отсутствует словарь!')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if (homework_name is None) or (homework_status is None):
        raise KeyError('Ошибка: API не корректно, в homework_name и/или'
                       f' homework_status [{homework_name}]/'
                       f'[{homework_status}] отсутствует значение!')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if (verdict is None):
        raise StatusError('Ошибка: В ответе API, обнаружен недокументированный'
                          ' статус домашней работы!')
    logger.debug('Получен статус проверки работы'
                 f'"{homework_name}". {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    return all(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN)


def main():
    """Основная логика работы бота."""
    logger.debug('Запуск программы.')
    if not check_tokens():
        logger.debug('Переменные окружения TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,'
                     ' PRACTICUM_TOKEN не загружены.')
        logger.critical('Завершение работы программы!')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                current_timestamp = int(time.time())
                response_ok = check_response(response)
                if not response_ok:
                    logger.debug('В ответе API,'
                                 ' статус домашней работы не обновлялся.')
                else:
                    for home_work in response_ok:
                        message = parse_status(home_work)
                        if message:
                            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
