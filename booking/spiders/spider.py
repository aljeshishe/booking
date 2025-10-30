from collections import Counter, defaultdict
import random
import copy
from datetime import datetime
import email
from functools import partial
import gzip
import io
import json
import numpy as np
from parse import parse 
import re
import scrapy
from tqdm import tqdm

NOW_DATE_STR = datetime.now().strftime("%Y-%m-%d")
PRICES_REQUEST_DATA = {
    "operationName": "AvailabilityCalendar",
    "variables": {
        "input": {
            "travelPurpose": 2,
            "pagenameDetails": {
                "countryCode": "gr",
                "pagename": "seaside-gouves"
            },
            "searchConfig": {
                "searchConfigDate": {
                    "startDate": NOW_DATE_STR,
                    "amountOfDays": 61
                },
                "nbAdults": 1,
                "nbRooms": 1,
                "nbChildren": 0,
                "childrenAges": []
            }
        }
    },
    "extensions": {},
    "query": "query AvailabilityCalendar($input: AvailabilityCalendarQueryInput!) {\n  availabilityCalendar(input: $input) {\n    ... on AvailabilityCalendarQueryResult {\n      hotelId\n      days {\n        available\n        avgPriceFormatted\n        avgPrice\n        checkin\n        minLengthOfStay\n        __typename\n      }\n      __typename\n    }\n    ... on AvailabilityCalendarQueryError {\n      message\n      __typename\n    }\n    __typename\n  }\n}\n"
}


def getall(response, selector, replace=None):
    result = response.css(selector).getall()
    if result is None:
        return None

    result = [item.strip() for item in result]
    if replace:
        pattern = '|'.join(map(re.escape, replace.split()))
        result = [re.sub(pattern, "", item) for item in result]
        result = [item.strip() for item in result]

    return result

def get(response, selector, type=str, replace=None):
    result = response.css(selector).get()
    if result is None:
        return None
    
    result = result.strip()
    
    if replace:
        pattern = '|'.join(map(re.escape, replace.split()))
        result = re.sub(pattern, "", result)
        result = result.strip()

    result = type(result)
    return result 

def handle_failure(self, failure):
    # This is called on failure (DNS errors, timeouts, etc.)
    self.logger.error(repr(failure))

    # Optionally retry or do something else:
    request = failure.request
    if failure.check(scrapy.spidermiddlewares.httperror.HttpError):
        response = failure.value.response
        self.logger.warning(f"HTTP error {response.status} on {response.url}")
    elif failure.check(scrapy.downloadermiddlewares.retry.RetryMiddleware):
        self.logger.warning("Request failed and gave up retrying.")
    elif failure.check(scrapy.core.downloader.handlers.http11.TunnelError):
        self.logger.warning("Tunnel connection failed.")
        
class BookingSpider(scrapy.Spider):
    name = "spider"

    def __init__(self, countries: str | None = None, agg_days=False, max_hotels=None, shuffle=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.countries = countries
        self.shuffle = bool(shuffle)
        self.agg_days = bool(agg_days)
        self.archives_pb = tqdm(desc="Crawling archives", unit="page", total=0) 
        self.hotels_pb = tqdm(desc="Crawling hotels", unit="page", total=0) 
        self.url = "https://www.booking.com/sitembk-hotel-index.xml"
        self.max_hotels = int(max_hotels)
        self._counter = defaultdict(int)

    async def start(self):
        self.logger.info(f"Starting to scrape {self.url}")
        yield scrapy.Request(self.url, self.parse_hotels_archives_page, priority=10,
                    errback=partial(handle_failure, self),
                    dont_filter=True)
    
    def parse_hotels_archives_page(self, response):
        """
        Parse the initial page to find the maximum page number.
        """
        response.selector.remove_namespaces()
        urls = response.xpath('//sitemap/loc/text()').getall()
        self.logger.info(f"Found {len(urls)} URLs in sitemap")
        
        en_urls = [url for url in urls if "sitembk-hotel-en-gb" in url]
        for url in en_urls:
            yield scrapy.Request(
                url, 
                callback=self.parse_hotels_gzip_page,
                priority=5,
                errback=partial(handle_failure, self),
                dont_filter=True             
            )
        self.archives_pb.total = len(en_urls)
        self.archives_pb.refresh()
            

    def parse_hotels_gzip_page(self, response):
        """
        Parse the gzip page to find the maximum page number.
        """
        self.archives_pb.update(1)
        

        response = scrapy.http.response.text.TextResponse(
            url=response.url,
            body=gzip.GzipFile(fileobj=io.BytesIO(response.body)).read(),
            encoding='utf-8'
        )

        # Now use XPath on the new response
        urls = response.xpath('//urlset/url/loc/text()').getall()
        self.logger.info(f"Found {len(urls)} hotel URLs in gzipped sitemap")
        
        countries = self.countries.split(",") if self.countries else []
        random.shuffle(urls)
        for url in urls:
            parsed = parse("https://www.booking.com/hotel/{country}/{hotel_id}.{lang}.html", url)
            country = parsed["country"]
            if countries and country not in countries:
                continue
            
            if self._counter[country] >= self.max_hotels:
                continue
            self._counter[country] += 1

            self.hotels_pb.total += 1
            self.hotels_pb.refresh()
            prices_request_data = copy.deepcopy(PRICES_REQUEST_DATA)
            prices_request_data["variables"]["input"]["pagenameDetails"]["pagename"] = parsed["hotel_id"]
            prices_request_data["variables"]["input"]["pagenameDetails"]["countryCode"] = parsed["country"]
            yield scrapy.Request(
                "https://www.booking.com/dml/graphql?lang=en",
                body=json.dumps(prices_request_data),
                method="POST",
                callback=self.parse_prices,
                priority=0,
                errback=partial(handle_failure, self),
                dont_filter=True,
                meta=dict(hotel_id=parsed["hotel_id"], country=parsed["country"]),
            )
                
    def parse_prices(self, response):
        self.hotels_pb.update(1)
        
        days = response.json()["data"]["availabilityCalendar"]["days"]
        if self.agg_days:
            prices = [int(day["avgPrice"]) for day in days if day["available"]]
            if prices:
                result = dict(hotel_id=response.meta["hotel_id"], 
                              country=response.meta["country"],
                              min_price=min(prices),
                              max_price=max(prices),
                              avg_price=np.round(np.mean(prices)),
                              median_price=np.round(np.median(prices)))
                yield result
        else:
            for day in days:
                result = dict(hotel_id=response.meta["hotel_id"], 
                            country=response.meta["country"],
                            date=day.get("checkin", {}),
                            price=int(day["avgPrice"]) if day["available"] else None,
                            minLengthOfStay=day["minLengthOfStay"])
                yield result

    
    def closed(self, reason):  
        # Close the progress bar when the spider finishes  
        if self.archives_pb:  
            self.archives_pb.close()     
        if self.hotels_pb:  
            self.hotels_pb.close()            