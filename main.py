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
        self.base_url_first = 'https://opt.baden.ru'
        self.base_url_second = 'https://baden-shop.ru'
        self.base_url_third = 'https://robek.ru'
        self.base_url_fourth = 'https://respect-shoes.ru'
        self.article_numbers = []
        self.found_articles = []
        self.read_data_file = ''
        self.links_products = {}
        self.article_imgs = {}
        self.article_save_imgs = {}

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

    def remove_found_articles(self):
        found_article = list(self.links_products.keys())
        self.article_numbers = (set(self.article_numbers) - set(found_article))

    async def get_link_product_from_first_site(self, session, article):
        try:

            retry_options = ExponentialRetry(attempts=3)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(
                    url=f'{self.base_url_first}/search/?q={article}') as response:
                if response.ok:

                    sys.stdout.write("\r")
                    sys.stdout.write(f'Получаю ссылку на товар {article}')
                    sys.stdout.flush()

                    resp = await response.text()
                    soup = BeautifulSoup(resp, features='lxml')
                    # если на странице нет искомого товара
                    try:
                        product_not_found = soup.find('div', class_='info').find('h3')
                    except Exception:
                        # если на странице товар найден
                        # if bool(product_not_found) is False:
                        found_links_imgs = soup.find('div', class_='slideBox').find_all('a')
                        links_imgs = [f"{self.base_url_first}{link['href']}" for link in found_links_imgs]
                        self.article_imgs.setdefault(article, links_imgs)
                        # добавление в словарь артикула если найдено
                        self.links_products.setdefault(article, 'найдено')
                        # добавление найденных артикулов
                        self.found_articles.append(article)


        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на товары')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_from_first_site_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for article in self.article_numbers:
                task = asyncio.create_task(self.get_link_product_from_first_site(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def get_link_product_from_second_site(self, session, article):
        try:

            retry_options = ExponentialRetry(attempts=3)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(
                    url=f'{self.base_url_second}/catalog/?artcl={article}') as response:
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
                        self.links_products.setdefault(article, f'{self.base_url_second}{link_product["href"]}')
                        # добавление найденных артикулов
                        self.found_articles.append(article)


        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на товары')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_from_second_site_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for article in self.article_numbers:
                # print(article)

                task = asyncio.create_task(self.get_link_product_from_second_site(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def get_link_product_from_third_site(self, session, article):
        try:

            retry_options = ExponentialRetry(attempts=3)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(
                    url=f'{self.base_url_third}/search/?s={article}') as response:
                if response.ok:

                    sys.stdout.write("\r")
                    sys.stdout.write(f'Получаю ссылку на товар {article}')
                    sys.stdout.flush()

                    resp = await response.text()
                    soup = BeautifulSoup(resp, features='lxml')
                    # если на странице нет искомого товара
                    product_not_found = soup.find('div', id='contentbody').find('p')
                    # если на странице товар найден
                    if bool(product_not_found) is False:
                        link_product = soup.find('a', class_='tooltips')
                        # добавление в словарь найденной ссылки на товар
                        self.links_products.setdefault(article, f'https:{link_product["href"]}')
                        # добавление найденных артикулов
                        self.found_articles.append(article)


        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на товары')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_from_third_site_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for article in self.article_numbers:
                task = asyncio.create_task(self.get_link_product_from_third_site(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def get_link_product_from_fourth_site(self, session, article):
        try:

            retry_options = ExponentialRetry(attempts=3)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(
                    url=f'{self.base_url_fourth}/catalog/search/?q={article}') as response:
                if response.ok:

                    sys.stdout.write("\r")
                    sys.stdout.write(f'Получаю ссылку на товар {article}')
                    sys.stdout.flush()

                    resp = await response.text()
                    soup = BeautifulSoup(resp, features='lxml')
                    # если на странице нет искомого товара
                    product_not_found = soup.find('div', class_='page-massage')
                    # если на странице товар найден
                    if bool(product_not_found) is False:
                        link_product = soup.find('a', class_='card__img')
                        # добавление в словарь найденной ссылки на товар
                        self.links_products.setdefault(article, f'{self.base_url_fourth}{link_product["href"]}')
                        # добавление найденных артикулов
                        self.found_articles.append(article)


        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на товары')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_from_fourth_site_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for article in self.article_numbers:
                task = asyncio.create_task(self.get_link_product_from_fourth_site(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def get_link_img(self, session, link):
        try:

            retry_options = ExponentialRetry(attempts=5)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            if f'{self.links_products[link].rstrip()}' != 'найдено':
                async with retry_client.get(url=f'{self.links_products[link].rstrip()}') as response:
                    if response.ok:

                        sys.stdout.write("\r")
                        sys.stdout.write(f'Ищу ссылки на изображения {link}')
                        sys.stdout.flush()

                        resp = await response.text()
                        soup = BeautifulSoup(resp, features='lxml')
                        # второй сайт
                        if 'baden-shop.ru' in self.links_products[link]:

                            link_image = soup.find('ul', class_='thumbs').find_all('img')
                            if bool(link_image) is False:
                                self.article_imgs[link] = ''
                            else:
                                self.article_imgs[link] = [f"{self.base_url_second}{link['src']}" for link in
                                                           link_image]
                        # для третьего сайта
                        elif 'robek.ru' in self.links_products[link]:

                            link_image = soup.find('div', class_='multizoom1 thumbs product-thumbs').find_all('a')
                            if bool(link_image) is False:
                                self.article_imgs[link] = ''
                            else:
                                self.article_imgs[link] = [f"https:{link['href']}" for link in link_image]
                        # для четвертого сайта
                        elif 'respect-shoes.ru' in self.links_products[link]:

                            link_image = soup.find_all('div', class_='sp-slide jq-zoom')
                            if bool(link_image) is False:
                                self.article_imgs[link] = ''
                            else:

                                self.article_imgs[link] = [f"{self.base_url_fourth}{link.find('img')['data-src']}" for
                                                           link in link_image]



        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на изображения товаров')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на изображения товаров, функция - get_link_img()\n')

    async def get_link_img_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for link in self.links_products:
                task = asyncio.create_task(self.get_link_img(session, link))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def save_images(self, session, urls, name_img):
        try:
            images = []

            sys.stdout.write("\r")
            sys.stdout.write(f'Сохраняю изображение для {name_img}')
            sys.stdout.flush()

            for a, url in enumerate(urls):
                date_now = datetime.datetime.now()
                async with aiofiles.open(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg', mode='wb') as f:
                    async with session.get(url) as response:
                        images.append(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg')
                        async for x in response.content.iter_chunked(1024):
                            await f.write(x)

            self.article_imgs[name_img] = images
        except Exception as exc:
            print(f'Ошибка {exc} в сохранении изображений товаров')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в сохранении изображений товаров, функция - save_images()\n')

    async def save_images_run_async(self):
        if not os.path.isdir('./img/'):
            os.mkdir('./img/')
        async with aiohttp.ClientSession() as session:
            tasks = []
            for link in self.article_imgs:
                # [:3] - сохраняется три первых изображения
                task = asyncio.create_task(self.save_images(session, urls=self.article_imgs[link][:3], name_img=link))
                tasks.append(task)
                await asyncio.gather(*tasks)

    def resize_img(self):
        try:
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            fixed_height = 426
            for img_file in tqdm(os.listdir('./img/')):
                if img_file[-4:] == '.jpg':
                    img = Image.open(f'./img/{img_file}')
                    height_percent = (fixed_height / float(img.size[1]))
                    width_size = int((float(img.size[0]) * float(height_percent)))
                    new_image = img.resize((width_size, fixed_height))
                    new_image.save(f'./img/{img_file}')
        except Exception as exc:
            print(f'Ошибка {exc} в изменении разрешения изображений')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в изменении разрешения изображений, функция - resize_img()\n')

    def sending_to_fotohosting(self):
        self.active_token = self.token[0]
        self.active_secret_key = self.secret_key[0]
        headers = {
            'Authorization': f'TOKEN {self.active_token}',
        }
        for img_url in self.article_imgs:

            img_short_link = []

            sys.stdout.write("\r")
            sys.stdout.write(f'Загружаю изображение для - {img_url}')
            sys.stdout.flush()
            img_links = self.article_imgs[img_url]

            for img in img_links:

                try:
                    files = {
                        'image': open(img, 'rb'),
                        'secret_key': (None, self.active_secret_key),
                    }
                    response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
                    if response.json()['status'] == 200:
                        img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
                                              f"[/IMG][/URL]")
                    else:
                        print(f'Не удалось загрузить {img}')
                        continue
                except KeyError:
                    print(f'{img_url} ошибка загрузки изображения - {response.json()["error"]["message"]}\n')
                    with open('error.txt', 'a', encoding='utf-8') as file:
                        file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                                   f'{img} ошибка загрузки изображения, функция - sending_to_fotohosting()\n')
                    if response.json()["error"]["message"] == 'File reception error':
                        continue
                    elif response.json()["error"]["message"] == \
                            'Exceeded the daily limit of uploaded images for your account':
                        print('Переключение на второй аккаунт')

                        self.active_token = self.token[1]
                        self.active_secret_key = self.secret_key[1]

                        files = {
                            'image': open(img, 'rb'),
                            'secret_key': (None, self.active_secret_key),
                        }
                        response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
                        if response.json()['status'] == 200:
                            img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
                                                  f"[/IMG][/URL]")
                        else:
                            print(f'Не удалось загрузить {img}')
                    continue
                except FileNotFoundError:
                    continue
                self.article_save_imgs[img_url] = img_short_link

    def write_final_file(self):
        try:
            columns = ['I', 'J', 'K']
            wb = load_workbook(filename=self.read_data_file)
            ws = wb.active

            ws['I8'] = 'Ссылки на фотографии'
            date_now = datetime.datetime.now()
            for article in self.article_save_imgs:
                for i, link in enumerate(self.article_save_imgs[article]):
                    for row in ws.iter_cols(min_col=2, max_col=2, min_row=9):
                        for cell in row:
                            if cell.value == article:
                                ws[f'{columns[i]}{cell.row}'] = link

            file_name = f'data_final_{date_now.strftime("%d-%m-%y_%H-%M")}.xlsx'
            wb.save(filename=file_name)
            shutil.rmtree('./img/')
            print(f'Файл {file_name} сохранён')
        except Exception as exc:
            print(f'Ошибка {exc} в записи итогового файла')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в записи итогового файла, функция - write_final_file()\n')

    def run(self):
        try:
            # для винды
            # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print('Начало работы')
            self.open_token_file()
            self.read_file()
            print('Получаю артикул товаров и ссылки на них')
            self.get_article_number()
            print('\rАртикулы получил')
            print('---------------------------\n')
            print('Получаю ссылки на товары')
            print('Поиск на первом сайте')
            asyncio.run(self.get_link_product_from_first_site_run_async())
            self.remove_found_articles()
            print('Поиск на втором сайте')
            asyncio.run(self.get_link_product_from_second_site_run_async())
            self.remove_found_articles()
            print('Поиск на третьем сайте')
            asyncio.run(self.get_link_product_from_third_site_run_async())
            self.remove_found_articles()
            print('Поиск на четвёртом сайте')
            asyncio.run(self.get_link_product_from_fourth_site_run_async())
            self.remove_found_articles()
            print('\nСсылки получены')
            print('---------------------------\n')
            print('Получение изображения товаров')
            asyncio.run(self.get_link_img_run_async())
            print('\nИзображения получены')
            print('---------------------------\n')
            print('Скачиваю изображения')
            asyncio.run(self.save_images_run_async())
            print('\nСкачивание завершено')
            print('---------------------------\n')
            print('Измененяю размер изображений')
            self.resize_img()
            print('\rРазмеры изменены')
            print('---------------------------\n')
            print('Загружаю изображения на фотохостинг')
            self.sending_to_fotohosting()
            print('\nЗагрузка завершена')
            print('---------------------------\n')
            print('Записываю в итоговый файл data_final')
            self.write_final_file()
            print('Работа завершена')
            print('Для выхода нажмите Enter')
            input()
            shutil.rmtree('./img/')
            print('---------------------------\n')
        except Exception as exc:
            print(f'Произошла ошибка {exc}')
            print('Для выхода нажмите Enter')
            input()
            print('---------------------------\n')


def main():
    p = Parser()
    p.run()


if __name__ == '__main__':
    main()
