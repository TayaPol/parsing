import random
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import requests
import traceback

engine = create_engine("sqlite:///land_plot_avito.db", echo=False)

Base = declarative_base()

class MO_Buy(Base):
    __tablename__ = "mo_buy_yandex"
    id = Column(Integer, primary_key=True)
    size = Column(String, nullable=True)
    price = Column(String, nullable=True)
    location = Column(String, nullable=True)
    link = Column(String, nullable=True)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
s = Session()

def sync_work():
    added = 0
    target = 811
    processed_links = set()  # чтобы не дублировать внутри сессии

    with sync_playwright() as p:
        with p.chromium.launch(channel='chrome', headless=False, ignore_default_args=["--enable-automation"]) as browser:
            page = browser.new_page()
            for pg in range(5, 10):
                url = f"https://realty.yandex.ru/moskva_i_moskovskaya_oblast/kupit/uchastok/?lotAreaMin=80&subRegionId=587654&page={pg}"

                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(7)  # даём время на начальную загрузку

                # Переменная для отслеживания высоты прокрутки
                last_height = page.evaluate("document.body.scrollHeight")

                while added < target:
                    # Получаем HTML текущей страницы
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Ищем все карточки объявлений
                    items = soup.find_all("div", class_="OffersSerpItem__main")
                    if not items:
                        print("Объявления не найдены. Возможно, изменилась разметка.")
                        break

                    print(f"Найдено {len(items)} объявлений на странице (загружено всего)")

                    # Обрабатываем каждую карточку
                    for item in items:
                        if added >= target:
                            break

                        try:
                            # Извлечение ссылки
                            general_info = item.find("div", class_="OffersSerpItem__generalInfoInnerContainer")
                            if not general_info:
                                continue
                            a_tag = general_info.find("a")
                            if not a_tag:
                                continue
                            href = a_tag.get("href")
                            if not href:
                                continue
                            clean_link = f"https://realty.yandex.ru{href}"

                            # Проверяем, не обработали ли уже эту ссылку
                            if clean_link in processed_links:
                                continue
                            processed_links.add(clean_link)
                            time.sleep(random.randint(1, 3))

                            # Размер
                            size_raw_elem = general_info.find("span", class_="Text__text_m--1fDTw Text__text_weight_500--1WBBj OffersSerpItemTitle__title--1XhVm Box__clr_primary--2uNHa")
                            if size_raw_elem:
                                size_span = size_raw_elem.find("span")
                                size_raw = size_span.text if size_span else ""
                            else:
                                size_raw = ""
                            size = size_raw.split("·")[0].strip() if size_raw else None
                            time.sleep(random.randint(1, 3))

                            # Цена
                            deal_info = item.find("div", class_="OffersSerpItem__dealInfo")
                            if deal_info:
                                price_label = deal_info.find("div", class_="OfferPriceLabel__priceWithTrend--1_AZI")
                                if price_label:
                                    price_span = price_label.find("span")
                                    price = price_span.text.strip() if price_span else None
                                else:
                                    price = None
                            else:
                                price = None
                            time.sleep(random.randint(1, 3))

                            # Адрес
                            location_elem = item.find("div", class_="AddressWithGeoLinks__addressContainer--4jzfZ")
                            address = location_elem.get_text(strip=True) if location_elem else None
                            time.sleep(random.randint(1, 3))

                            # Пропускаем, если не хватает данных
                            if not size or not price or not address:
                                print(f"Пропуск из-за неполных данных: {size}, {price}, {address}")
                                continue

                            #  Сохранение в БД
                            with Session() as session:
                                exists = session.query(MO_Buy).filter(MO_Buy.link == clean_link).first()
                                if exists:
                                    print(f"Дубликат: {clean_link}")
                                    continue
                                data = MO_Buy(
                                    size=size,
                                    price=price,
                                    location=address,
                                    link=clean_link
                                )
                                session.add(data)
                                session.commit()
                                added += 1
                                total = session.query(MO_Buy).count()
                                print(f"Сохранено: {added}/{target}, всего в БД: {total}")

                        except Exception as e:
                            print(f"Ошибка при обработке карточки: {e}")
                            traceback.print_exc()
                            continue

                    # Если собрали достаточно – выходим
                    if added >= target:
                        break

                    # Прокручиваем страницу вниз, чтобы подгрузить новые объявления
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)  # ждём подгрузки новых элементов

                    # Проверяем, изменилась ли высота страницы
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        print("Новые объявления не подгрузились. Завершаем сбор.")
                        break
                    last_height = new_height


if __name__ == "__main__":
    sync_work()