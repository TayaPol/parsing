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


class Msk_Buy(Base):
    __tablename__ = "msk_buy_cian"
    id = Column(Integer, primary_key=True)
    size = Column(String, nullable=True)
    price = Column(String, nullable=True)
    location = Column(String, nullable=True)
    link = Column(String, nullable=True)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
s = Session()


def clean_url(url: str) -> str:

    if '?' in url:
        return url.split('?')[0]
    return url


def sync_work():
    added = 28
    target = 69

    with (sync_playwright() as p):
        # запуск Chrome
        browser = p.chromium.launch(channel='chrome', headless=False, ignore_default_args=["--enable-automation"])
        page = browser.new_page()
        for pg in range(2, 4):

            if added >= target:
                print(f"Достигнуто {target} записей. Остановка.")
                break

            url = f"https://www.cian.ru/cat.php?cats%5B0%5D=commercialLandSale&deal_type=sale&engine_version=2&minsite=80&offer_type=offices&p={pg}&region=1"

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)
                html = page.content()
            except Exception as e:
                print(f"Ошибка загрузки страницы {pg}: {e}")
                continue


            # парсим полученный HTML с помощью BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Забираем каждое объявление
            all_item = (soup.find("div", id="legacy-commercial-serp-frontend")
                        .find_all("div", class_="x02c2df23--f2641e--offer-container"))
            time.sleep(random.randint(1, 10))
            # print(all_item)
            for i in all_item:
                try:
                    # забираем ссылки с каждого объявления
                    url2 = (i.find("div", class_="x02c2df23--_42af5--header-title")
                                 .find("a").get("href"))

                    clean_link = clean_url(url2)
                    time.sleep(random.randint(1, 3))
                    # print(clean_link)

                    time.sleep(random.randint(1, 7))
                    resp = page.goto(url2, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(random.randint(1, 10))
                    # print(f"Статус-код: {resp.status}")
                    html_card = page.content()
                    time.sleep(6)

                    soup_card = BeautifulSoup(html_card, 'html.parser')

                    size = (soup_card.find("div", class_="xa15a2ab7--a331a2--page")
                            .find("div", class_="xa15a2ab7--_3d01b--center")
                            .find("div", class_="xa15a2ab7--_2be4c--item")
                            .find("div", class_="xa15a2ab7--_2be4c--text")
                            .find("span", class_="xa15a2ab7--_7735e--color_text-primary-default xa15a2ab7--_2697e--lineHeight_6u xa15a2ab7--_2697e--fontWeight_bold xa15a2ab7--_2697e--fontSize_16px xa15a2ab7--_17731--display_block xa15a2ab7--dc75cc--text").text)
                    time.sleep(random.randint(1, 7))
                    # print(size)

                    price = (soup_card.find("div", class_="xa15a2ab7--a331a2--page")
                            .find("div", class_="xa15a2ab7--fc68b9--price")
                            .find("span", class_="xa15a2ab7--_7735e--color_text-primary-default xa15a2ab7--_2697e--lineHeight_9u xa15a2ab7--_2697e--fontWeight_bold xa15a2ab7--_2697e--fontSize_28px xa15a2ab7--_17731--display_block xa15a2ab7--dc75cc--text").text)
                    time.sleep(random.randint(1, 7))
                    # print(price)

                    location = (soup_card.find("div", class_="xa15a2ab7--a331a2--page")
                                .find("div", class_="xa15a2ab7--_0c862--address-line").find_all("a", class_="xa15a2ab7--_15017--address"))
                    # print(location)
                    time.sleep(random.randint(1, 7))
                    address_parts = [link.get_text(strip=True) for link in location if link.get_text(strip=True)]
                    address = " ".join(address_parts)
                    # print(address)


                    with Session() as session:
                        exists = session.query(Msk_Buy).filter(Msk_Buy.link == clean_link).first()
                        if exists:
                            print(f"Дубликат, пропускаем: {clean_link}")
                            continue

                        data = Msk_Buy(
                            size=size,
                            price=price,
                            location=address,
                            link=clean_link
                        )
                        session.add(data)
                        session.commit()
                        added += 1
                        total = session.query(Msk_Buy).count()
                        print(f"Сохранено записей: {added}/{target}, всего в БД: {total}")

                except Exception as e:
                    print(f"Ошибка: {e}")
                    traceback.print_exc()

        browser.close()

if __name__ == "__main__":
    sync_work()


