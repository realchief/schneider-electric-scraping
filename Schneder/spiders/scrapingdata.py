import re
import csv
import json
import scrapy
import urllib
import requests
import pandas as pd

from scrapy.http import FormRequest
from scrapy import Request

class SiteProductItem(scrapy.Item):
    ASIN = scrapy.Field()
    Model_Number = scrapy.Field()
    Qty = scrapy.Field()


class MyScraper(scrapy.Spider):
    name = "scrapingdata"
    allowed_domains = ['myseus.schneider-electric.com', 'ims.wsecure.schneider-electric.com']
    DOMAIN_URL = 'https://www.myseus.schneider-electric.com'
    LOGIN_URL = 'https://secureidentity.schneider-electric.com/identity/idp/login?app=0sp1H000000CabV' \
                '&lang=en&gotoNew=0LUhMag8DktqLCSR9Qk2&idpDisable=TRUE'
    LOGIN_REQUEST_URL = 'https://ims.wsecure.schneider-electric.com/opensso/UI/Login'
    START_URL = 'https://www.myseus.schneider-electric.com/mySchneider/#!/login'

    USERNAME = 'lenore@totalelectricny.com'
    PASSWORD = 'Zilch12@5614'

    def __init__(self, **kwargs):

        self.headers = {
            "authority": "ims.wsecure.schneider - electric.com",
            "method": "POST",
            "path": "/opensso/UI/Login",
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "content-length": 205,
            "Content-Type": "application/x-www-form-urlencoded",
            "cookie": {
                "JSESSIONID": "60A2AF9288C2D9712A3DB1D18FFE48DC.ims_64",
                "amlbcookie": "03",
                "atidvisitor": "%7B%22name%22%3A%22atidvisitor%22%2C%22val%22%3A%7B%22vrn%22%3A%22-592419-"
                               "%22%7D%2C%22options%22%3A%7B%22path%22%3A%22%2F%22%2C%22session%22%3A157248"
                               "00%2C%22end%22%3A15724800%7D%7D",
                "AMAuthCookie": "AQIC5wM2LY4SfcyWBWJN6gLWTBPLmFEW4dqk9DS4ndKQcoA.*"
                                "AAJTSQACMDIAAlNLABM4NDU3NzQ4NzgzNDYyNzM4OTg5AAJTMQACMDM.*"
            },
            "origin": "https://ims.wsecure.schneider-electric.com",
            "referer": "referer:https://ims.wsecure.schneider-electric.com/opensso/UI/Login?"
                       "errorMessage=auth.failed&errorMessage=auth.failed",
            "upgrade-insecure-requests": 1,
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"
        }
        self.input_file = 'Schneider_SquareD.csv'

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

        form_data = {
            'IDToken1': self.USERNAME,
            'IDToken2': self.PASSWORD,
            'IDButton': 'Log In',
            'goto': '',
            'gx_charset': 'UTF-8',
            'gotoOnFail': '',
            'SunQueryParamsString': 'ZXJyb3JNZXNzYWdlPWF1dGguZmFpbGVk',
            'encoded': 'false',
            'errorMessage': 'auth.failed'
        }


        yield FormRequest(url=self.LOGIN_REQUEST_URL,
                      callback=self.check_login,
                      headers=self.headers,
                      dont_filter=True,
                      method="POST",
                      formdata=form_data
                      )

    def check_login(self, response):
        check_login_request_url = 'https://ims.wsecure.schneider-electric.com/opensso/idm/EndUser'
        response.body = requests.get(check_login_request_url)


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
                          headers=self.headers,
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


