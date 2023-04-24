# -*- coding: utf8 -*-
import os
import re
import time
import lxml
import shutil
import sys
import aiohttp
import asyncio
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
        self.base_url = 'https://baden-shop.ru/'
        self.article_numbers = []


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
                if file[:6] == 'data.':
                    print(f'Получаю артикул товаров из файла {file}')
                    self.read_data_file = file
        except Exception:
            print('Нет файла с именем data.')
            raise IndexError

    def get_article_number(self):
        try:
            wb = load_workbook(filename=self.read_data_file)
            sheets = wb.sheetnames
            ws = wb[sheets[0]]

            for row in ws.iter_cols(min_col=2, max_col=2, min_row=9):
                for cell in row:
                    if cell.value is None:
                        continue
                    # есть ли числа в строке
                    if re.search('\d+', cell.value.strip().split(' ')[0]):
                        self.article_numbers.append(cell.value.strip().split(' ')[0])

            self.article_numbers = list(dict.fromkeys(self.article_numbers))
        except Exception as exc:
            print(f'Ошибка {exc} в чтении табличного документа data1.xlsx')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в чтении табличного документа data1.xlsm, функция - get_article_number()\n')
            raise IndexError