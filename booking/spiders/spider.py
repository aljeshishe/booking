import copy
import email
from functools import partial
import gzip
import io
import json
from parse import parse 
import re
import scrapy
from tqdm import tqdm


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
                    "startDate": "2025-05-01",
                    "amountOfDays": 61
                },
                "nbAdults": 2,
                "nbRooms": 4,
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

    def __init__(self, countries: str, fast=False, max_hotels=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.countries = countries.split(",")
        self.fast = int(fast)
        self.pb = tqdm(desc="Crawling Pages", unit="page", total=0) 
        self.url = "https://www.booking.com/sitembk-hotel-index.xml"
        self.max_hotels = int(max_hotels)

    async def start(self):
        self.logger.info(f"Starting to scrape {self.url}")
        yield scrapy.Request(self.url, self.parse_hotels_archives_page, priority=10,
                    errback=partial(handle_failure, self),
                    dont_filter=True             
                             )
    
    def parse_hotels_archives_page(self, response):
        """
        Parse the initial page to find the maximum page number.
        """
        NAMESPACES = dict(sm="http://www.sitemaps.org/schemas/sitemap/0.9")
        urls = response.xpath('//sm:sitemap/sm:loc/text()', namespaces=NAMESPACES).getall()
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
        self.pb.total = len(en_urls)
        self.pb.refresh()
            

    def parse_hotels_gzip_page(self, response):
        """
        Parse the gzip page to find the maximum page number.
        """
        self.pb.update(1)
        

        response = scrapy.http.response.text.TextResponse(
            url=response.url,
            body=gzip.GzipFile(fileobj=io.BytesIO(response.body)).read(),
            encoding='utf-8'
        )

        countries = [country for country in self.countries if f"https://www.booking.com/hotel/{country}" in response.text]
        if not countries:
            return
        
        countries_str = " ".join(countries)
        self.logger.warning(f"Found countries urls [{countries_str}] in response for {response.url}")
        # Now use XPath on the new response
        urls = response.xpath('//urlset/url/loc/text()').getall()
        self.logger.info(f"Found {len(urls)} hotel URLs in gzipped sitemap")
        
        for url in urls:
            parsed = parse("https://www.booking.com/hotel/{country}/{hotel_id}.{lang}.html", url)
            if parsed["country"] not in self.countries:
                continue
            
            self.pb.total += 1
            self.pb.refresh()
            prices_request_data = copy.deepcopy(PRICES_REQUEST_DATA)
            prices_request_data["variables"]["input"]["pagenameDetails"]["pagename"] = parsed["hotel_id"]
            prices_request_data["variables"]["input"]["pagenameDetails"]["countryCode"] = parsed["country"]
            yield scrapy.Request(
                "https://www.booking.com/dml/graphql?lang=en",
                body=json.dumps(prices_request_data),
                method="POST",
                callback=self.parse_prices,
                priority=4,
                errback=partial(handle_failure, self),
                dont_filter=True,
                meta=dict(hotel_id=parsed["hotel_id"], country=parsed["country"]),
            )
            if self.fast:
                break
                
    def parse_prices(self, response):
        self.pb.update(1)
        
        days = response.json()["data"]["availabilityCalendar"]["days"]
        for day in days:
            result = dict(hotel_id=response.meta["hotel_id"], 
                          country=response.meta["country"],
                          date=day.get("checkin", {}),
                          price=int(day["avgPrice"]) if day["available"] else None,
                          minLengthOfStay=day["minLengthOfStay"])
            yield result

    
    def closed(self, reason):  
        # Close the progress bar when the spider finishes  
        if self.pb:  
            self.pb.close()     