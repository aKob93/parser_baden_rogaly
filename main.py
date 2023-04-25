# -*- coding: utf8 -*-
import os
import re
import time
import lxml
import shutil
import sys
import aiohttp
import asyncio
from aiohttp_retry import RetryClient, ExponentialRetry
import aiofiles
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from openpyxl import load_workbook
from tqdm import tqdm
import datetime
from PIL import Image, ImageFile


class Parser:

    def __init__(self):
        ua = UserAgent()
        self.headers = {'user_agent': ua.random}
        self.token = ''
        self.secret_key = ''
        self.active_token = ''
        self.active_secret_key = ''
        self.base_url_first = 'https://baden-shop.ru'
        self.article_numbers = []
        self.found_articles = []
        self.read_data_file = ''
        self.links_products = {}

    def open_token_file(self):
        try:
            with open('token.txt', 'r') as file:
                for i, line in enumerate(file):
                    if i == 0:
                        self.token = line.split('=')[1].strip().split(', ')
                    elif i == 1:
                        self.secret_key = line.split('=')[1].strip().split(', ')
        except Exception:
            print('Не удалось прочитать token или secret_key')
            raise IndexError

    def read_file(self):
        try:
            for file in os.listdir():
                if file[:5] == 'data.':
                    print(f'Получаю артикул товаров из файла {file}')
                    self.read_data_file = file
        except Exception:
            print('Нет файла с именем data.')
            raise IndexError

    def get_article_number(self):
        try:
            wb = load_workbook(filename=self.read_data_file)
            sheets = wb.sheetnames
            # работа с первым листом
            ws = wb[sheets[0]]
            # (min_col=2, max_col=2, min_row=9) 2 столбец(B) 9 строка
            for row in ws.iter_cols(min_col=2, max_col=2, min_row=9):
                for cell in row:
                    if cell.value is None:
                        continue
                    # есть ли числа в строке
                    if re.search('\d+', cell.value.strip()):
                        self.article_numbers.append(cell.value.strip())
            # убрать дубликаты артикулов
            self.article_numbers = list(set(self.article_numbers))
        except Exception as exc:
            print(f'Ошибка {exc} в чтении табличного документа data.xlsx')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в чтении табличного документа data1.xlsm, функция - get_article_number()\n')
            raise IndexError

    async def get_link_product_from_first_site(self, session, article):
        try:

            retry_options = ExponentialRetry(attempts=5)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(
                    url=f'{self.base_url_first}/catalog/?artcl={article}') as response:
                if response.ok:

                    sys.stdout.write("\r")
                    sys.stdout.write(f'Получаю ссылку на товар {article}')
                    sys.stdout.flush()

                    resp = await response.text()
                    soup = BeautifulSoup(resp, features='lxml')
                    # если на странице нет искомого товара
                    product_not_found = soup.find('h1', class_='display-5 text-center')
                    # если на странице товар найден
                    if bool(product_not_found) is False:
                        link_product = soup.find('div', class_='part col-6 col-md-4 col-lg-4 col-xl-3').find('a')
                        # добавление в словарь найденной ссылки на товар
                        self.links_products.setdefault(article, f'{self.base_url_first}{link_product["href"]}')
                        # добавление найденных артикулов
                        self.found_articles.append(article)


        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на товары')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_from_first_site_run_async(self):
        # print(len(self.links_products))
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for article in self.article_numbers:
                # print(article)

                task = asyncio.create_task(self.get_link_product_from_first_site(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    def remove_found_articles(self):
        found_article = list(self.links_products.keys())
        self.article_numbers = (set(self.article_numbers) - set(found_article))





p = Parser()
p.read_file()
p.get_article_number()
asyncio.run(p.get_link_product_from_first_site_run_async())
p.remove_found_articles()
#TODO делать второй сайт
zz = {'AA038-011': 'https://baden-shop.ru/159122/', 'AA059-011': 'https://baden-shop.ru/158339/',
      'C255-030': 'https://baden-shop.ru/147953/', 'C675-020': 'https://baden-shop.ru/147957/',
      'C675-010': 'https://baden-shop.ru/147956/', 'C677-020': 'https://baden-shop.ru/147958/',
      'C698-093': 'https://baden-shop.ru/147962/', 'CV045-101': 'https://baden-shop.ru/153804/',
      'CV266-011': 'https://baden-shop.ru/158610/', 'CC028-012': 'https://baden-shop.ru/147964/',
      'CN154-010': 'https://baden-shop.ru/158596/', 'CJ039-011': 'https://baden-shop.ru/158169/',
      'CN121-030': 'https://baden-shop.ru/158175/', 'CV266-010': 'https://baden-shop.ru/158609/',
      'DA029-011': 'https://baden-shop.ru/139227/', 'CV105-011': 'https://baden-shop.ru/157329/',
      'CC090-010': 'https://baden-shop.ru/158595/', 'EA025-071': 'https://baden-shop.ru/158614/',
      'EC125-020': 'https://baden-shop.ru/158979/', 'EC050-011': 'https://baden-shop.ru/139027/',
      'DN040-010': 'https://baden-shop.ru/148010/', 'EA025-081': 'https://baden-shop.ru/158615/',
      'EC125-021': 'https://baden-shop.ru/158980/', 'EC163-012': 'https://baden-shop.ru/158984/',
      'FB075-081': 'https://baden-shop.ru/132825/', 'EH179-010': 'https://baden-shop.ru/158995/',
      'ES015-010': 'https://baden-shop.ru/159010/', 'FB157-011': 'https://baden-shop.ru/148039/',
      'FB178-010': 'https://baden-shop.ru/148048/', 'FB074-013': 'https://baden-shop.ru/132822/',
      'FB079-013': 'https://baden-shop.ru/132826/', 'FB232-021': 'https://baden-shop.ru/159017/',
      'GF037-016': 'https://baden-shop.ru/159031/', 'FH053-020': 'https://baden-shop.ru/132830/',
      'FF030-081': 'https://baden-shop.ru/159023/', 'FY003-010': 'https://baden-shop.ru/90277/',
      'HX067-111': 'https://baden-shop.ru/158252/', 'JH008-020': 'https://baden-shop.ru/148099/',
      'JE184-010': 'https://baden-shop.ru/157347/', 'JE079-012': 'https://baden-shop.ru/148093/',
      'JH008-021': 'https://baden-shop.ru/148100/', 'JH015-030': 'https://baden-shop.ru/159052/',
      'KF292-020': 'https://baden-shop.ru/159054/', 'LV003-011': 'https://baden-shop.ru/159204/',
      'KF295-021': 'https://baden-shop.ru/159056/', 'LM001-020': 'https://baden-shop.ru/153890/',
      'LM001-010': 'https://baden-shop.ru/153888/', 'ME195-010': 'https://baden-shop.ru/148371/',
      'ME277-020': 'https://baden-shop.ru/159070/', 'MU093-040': 'https://baden-shop.ru/132703/',
      'MU124-040': 'https://baden-shop.ru/158279/', 'NP012-060': 'https://baden-shop.ru/159190/',
      'MU128-010': 'https://baden-shop.ru/158282/', 'NK090-010': 'https://baden-shop.ru/159078/',
      'MU176-021': 'https://baden-shop.ru/158312/', 'NU249-031': 'https://baden-shop.ru/148407/',
      'NU489-012': 'https://baden-shop.ru/159101/', 'NU489-011': 'https://baden-shop.ru/159100/',
      'P200-131': 'https://baden-shop.ru/132859/', 'NU458-012': 'https://baden-shop.ru/159089/',
      'P208-011': 'https://baden-shop.ru/124087/', 'NU482-012': 'https://baden-shop.ru/159094/',
      'P120-051': 'https://baden-shop.ru/132856/', 'RA021-031': 'https://baden-shop.ru/159192/',
      'RN013-021': 'https://baden-shop.ru/132717/', 'RJ168-040': 'https://baden-shop.ru/153994/',
      'RJ166-061': 'https://baden-shop.ru/159106/', 'RN023-041': 'https://baden-shop.ru/132719/',
      'VC002-221': 'https://baden-shop.ru/148448/', 'VR013-066': 'https://baden-shop.ru/159222/',
      'WA054-015': 'https://baden-shop.ru/159226/', 'WA055-013': 'https://baden-shop.ru/148460/',
      'WA055-012': 'https://baden-shop.ru/148459/', 'WL103-013': 'https://baden-shop.ru/159241/',
      'ZN021-011': 'https://baden-shop.ru/154094/', 'ZA140-011': 'https://baden-shop.ru/148466/',
      'ZA190-012': 'https://baden-shop.ru/159253/'}

