import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time


class WebScraperUtility:
    def __init__(self):
        """
        クラスの初期化
        """
        pass

    @staticmethod
    def tag_visible(element):
        if element.parent and element.parent.name in [
            "style",
            "script",
            "head",
            "title",
            "meta",
            "[document]",
        ]:
            return False
        if isinstance(element, Comment):
            return False
        return True

    @staticmethod
    def get_xpath(element, driver):
        """
        指定した要素のXPathを取得する関数
        """
        script = """
        function getXPath(element) {
            if (element.id !== '') {
                return 'id("' + element.id + '")';
            }
            if (element === document.body) {
                return 'html/body';
            }
            var ix = 0;
            var siblings = element.parentNode.childNodes;
            for (var i = 0; i < siblings.length; i++) {
                var sibling = siblings[i];
                if (sibling === element) {
                    return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
        }
        return getXPath(arguments[0]);
        """
        return driver.execute_script(script, element)

    def scrape(self, url):
        """
        指定したURLの可視テキストを取得し、情報を返す
        """
        # Seleniumの設定
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920x1080")

        # WebDriverのセットアップ
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # URLにアクセス
        driver.get(url)

        # 可視の要素のみを取得
        # elements = driver.find_elements(By.CSS_SELECTOR, "div")  # 要素を取得
        elements = driver.find_elements(By.XPATH, "//*")  # すべて要素を取得
        visible_elements = [el for el in elements if el.is_displayed()]

        extracted_data = []
        for i, el in enumerate(visible_elements):
            text = el.text.strip()
            if text and len(text) <= 100:  # 文字数が1000以下の場合のみ格納
                xpath = self.get_xpath(el, driver)
                data = {
                    "id": i,
                    "document": text,
                    "xpath": xpath,
                    "url": url,
                }
                extracted_data.append(data)

        driver.quit()
        return extracted_data

    def get_full_visible_text(self, url):
        # Chrome WebDriver の設定
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # GUI を表示しない
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")  # ウィンドウサイズを指定
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # WebDriver の起動
        service = Service()  # ChromeDriver のパスが環境変数にある場合
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            driver.get(url)
            time.sleep(5)  # ページの読み込み待機

            last_height = driver.execute_script("return document.body.scrollHeight")
            full_text = ""

            while True:
                # JavaScript を使用して現在の可視部分のテキストを取得
                visible_text = driver.execute_script("return document.body.innerText;")

                # 重複を避けるため、前回のテキストとの差分を取る
                if visible_text not in full_text:
                    full_text += visible_text + "\n"

                # ページの一番下までスクロール
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # スクロール後の読み込み待機

                # 新しい高さを取得
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # これ以上スクロールできない場合は終了
                last_height = new_height

            # HTML を取得し、不要な部分を削減
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # <script> や <style> などの不要タグを削除
            for script in soup(["script", "style", "noscript"]):
                script.extract()

            # 整形したテキストを取得
            cleaned_text = "\n".join(
                line.strip() for line in full_text.splitlines() if line.strip()
            )

            return cleaned_text
        finally:
            driver.quit()  # WebDriver を終了
