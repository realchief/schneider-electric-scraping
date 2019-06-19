import scrapy
import re
import csv
import pandas as pd
from scrapy import FormRequest
import json
import urllib
from scrapy import Request


class SiteProductItem(scrapy.Item):
    ASIN = scrapy.Field()
    Model_Number = scrapy.Field()
    Qty = scrapy.Field()


class MyScraper(scrapy.Spider):
    name = "scrapingdata"
    allowed_domains = ['www.myseus.schneider-electric.com']
    DOMAIN_URL = 'https://www.myseus.schneider-electric.com'
    LOGIN_URL = 'https://www.myseus.schneider-electric.com/mySchneider/#!/login'
    START_URL = 'https://www.myseus.schneider-electric.com/mySchneider/#!/login'
    USERNAME = 'lenore@totalelectricny.com'
    PASSWORD = 'Zilch12@5614'

    def __init__(self, **kwargs):

        self.input_file = 'Schneider_SquareD.csv'
        self.headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
                                      " Chrome/70.0.3538.102 Safari/537.36"
                        }

        with open(self.input_file, 'r+', encoding='utf-8', errors='ignore') as csvfile:
            reader = csv.reader(csvfile)
            self.sku_list = []
            for row_index, row in enumerate(reader):
                if row_index != 0:
                    self.sku_list.append(row[0])

    def start_requests(self):

        start_url = self.START_URL
        yield scrapy.Request(url=start_url, callback=self.login)

    def login(self, response):
        view_state = response.xpath("//input[@id='__VIEWSTATE']/@value").extract()[0]
        payload = {
            '__VIEWSTATE': view_state,
            'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol$userControlElem$txtUsername': self.USERNAME,
            'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol$userControlElem$txtPassword': self.PASSWORD,
            'lng': 'en-US',
            '__VIEWSTATEGENERATOR': 'A5343185',
            'manScript_HiddenField': '',
            'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol$userControlElem$ImgBtnLogin.x': '10',
            'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol$userControlElem$ImgBtnLogin.y': '5',
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': '',

        }
        yield Request(url=self.LOGIN_URL,
                      callback=self.parse_pages,
                      headers=self.headers,
                      dont_filter=True,
                      method="POST",
                      body=urllib.parse.urlencode(payload)
                      )

    def parse_pages(self, response):

        request_url = response.url
        view_state = response.xpath("//input[@id='__VIEWSTATE']/@value").extract()[0]
        row_numbers = len(self.sku_list)
        for index in range(0, row_numbers - 1):
            response.meta['asin'] = self.asin_list[index]
            sku = self.sku_list[index]
            response.meta['sku'] = sku

            payload = {
                'manScript': 'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$pnlUpdate|p$lt$zoneContent$pageplaceholde'
                             'r$p$lt$zoneLeft$usercontrol1$userControlElem$btnApply',
                '__VIEWSTATE': view_state,
                'lng': 'en-US',
                '__VIEWSTATEGENERATOR': 'A5343185',
                'manScript_HiddenField': '',
                'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol1$userControlElem$txtSearch': sku,
                'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol1$userControlElem$ddListSrcIn': 'All',
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATEENCRYPTED': '',
                '__ASYNCPOST': 'true',
                'p$lt$zoneContent$pageplaceholder$p$lt$zoneLeft$usercontrol1$userControlElem$btnApply': 'Search'
            }

            yield Request(url=request_url,
                          callback=self.parse_product,
                          headers=self.headers_search,
                          dont_filter=True,
                          method="POST",
                          body=urllib.parse.urlencode(payload),
                          meta=response.meta
                          )

    def parse_product(self, response):

        prod_item = SiteProductItem()
        qty = self._parse_qty(response)
        prod_item['Model_Number'] = response.meta['sku']
        prod_item['ASIN'] = response.meta['asin']
        prod_item['Qty'] = qty

        yield prod_item

    @staticmethod
    def _parse_qty(response):
        td_list = response.xpath('.//tr[@class="navigator_row_first"]/td')
        assert_available = td_list[2].xpath('./text()').extract()
        qty = ''
        if assert_available:
            qty = str(assert_available[0].strip())
        return qty


