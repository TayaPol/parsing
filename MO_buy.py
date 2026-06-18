import random
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
import traceback
import os

# Путь к БД
db_path = os.path.abspath("land_plot_avito.db")
engine = create_engine(f"sqlite:///{db_path}", echo=False)

Base = declarative_base()

class MO_buy_new(Base):
    __tablename__ = "mo_buy_new_parsing"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    price = Column(String, nullable=True)
    location = Column(String, nullable=True)
    link = Column(String, nullable=True)   # здесь будет храниться очищенная ссылка

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def clean_url(url: str) -> str:

    if '?' in url:
        return url.split('?')[0]
    return url

def sync_work():
    added = 0
    target = 1910

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=False, ignore_default_args=["--enable-automation"])
        page = browser.new_page()

        for pg in range(1, 40):
            if added >= target:
                print(f"Достигнуто {target} записей. Остановка.")
                break

            url = f"https://www.avito.ru/moskovskaya_oblast/zemelnye_uchastki/prodam-ASgBAgICAUSWA9oQ?context=H4sIAAAAAAAA_wEmANn_YToxOntzOjE6InkiO3M6MTY6Ikk3RklHSFRUUGFINWRvUXgiO33NZUJ0JgAAAA&f=ASgBAgECAUSWA9oQAUWUCRh7ImZyb20iOjE0Mzk0LCJ0byI6bnVsbH0&localPriority=0&p={pg}&q=купить+земельный+участок"

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_selector('div[data-marker="item"]', timeout=30000)
                time.sleep(5)
                html = page.content()
            except Exception as e:
                print(f"Ошибка загрузки страницы {pg}: {e}")
                continue

            soup = BeautifulSoup(html, 'html.parser')
            all_item = soup.select('div[data-marker="item"]')
            if not all_item:
                all_item = soup.find_all("div", class_=lambda c: c and "iva-item-root" in c)

            if not all_item:
                print(f"Не найдено объявлений на странице {pg}")
                continue

            print(f"Страница {pg}: найдено {len(all_item)} объявлений")

            for i in all_item:
                if added >= target:
                    break

                try:
                    # ---- ссылка ----
                    a_tag = i.select_one('a[data-marker="item-title"]')
                    if not a_tag:
                        raise ValueError("Не найдена ссылка")
                    href_land = a_tag.get("href")
                    if not href_land:
                        raise ValueError("Ссылка пуста")
                    raw_url = f"https://www.avito.ru{href_land}"
                    clean_link = clean_url(raw_url)
                    time.sleep(random.randint(1, 3))

                    # ---- название ----
                    name = a_tag.text.strip() if a_tag else "Без названия"
                    time.sleep(random.randint(1, 3))

                    # ---- цена ----
                    price_span = i.select_one('span[data-marker="item-price-value"]')
                    price = price_span.text.strip() if price_span else "Цена не указана"
                    time.sleep(random.randint(1, 3))

                    # ---- адрес ----
                    address_span = i.select_one('span[data-marker="item-address"]')
                    if address_span:
                        address = address_span.text.strip()
                    else:
                        geo_div = i.select_one('div[class*="geo-root"]')
                        if geo_div:
                            spans = geo_div.find_all("span")
                            address = spans[0].get_text(strip=True) if spans else "Адрес не указан"
                        else:
                            address = "Адрес не указан"
                    time.sleep(random.randint(1, 3))

                    # ---- проверка дубликата и сохранение ----
                    with Session() as session:
                        exists = session.query(MO_buy_new).filter(MO_buy_new.link == clean_link).first()
                        if exists:
                            print(f"Дубликат, пропускаем: {clean_link}")
                            continue

                        data = MO_buy_new(
                            name=name,
                            price=price,
                            location=address,
                            link=clean_link
                        )
                        session.add(data)
                        session.commit()
                        added += 1
                        total = session.query(MO_buy_new).count()
                        print(f"Сохранено записей: {added}/{target}, всего в БД: {total}")

                except Exception as e:
                    print(f"Ошибка при обработке объявления: {e}")
                    traceback.print_exc()
                    continue

        browser.close()

if __name__ == "__main__":
    sync_work()