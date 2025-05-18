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
HEADERS_STR = """Host: www.booking.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0
Accept: */*
Accept-Language: en-GB,en;q=0.5
Referer: https://www.booking.com/hotel/gr/sea-breeze-apartment-nei-epivates.es.html
apollographql-client-name: b-property-web-property-page_rust
apollographql-client-version: YTCATMca
content-type: application/json
x-apollo-operation-name: AvailabilityCalendar
x-booking-context-action: hotel
x-booking-context-action-name: hotel
x-booking-context-aid: 304142
x-booking-csrf-token: eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJjb250ZXh0LWVucmljaG1lbnQtYXBpIiwic3ViIjoiY3NyZi10b2tlbiIsImlhdCI6MTc0NzU3MTg3OSwiZXhwIjoxNzQ3NjU4Mjc5fQ.ko9GVaTCYEnCCBcWONudVnh9JXoNrrHtZ8sAFHIQjBQPaBBmT4tKj_RwY3sj9ZwWsbgyuK1ZcrMrMwmAh1dpWg
x-booking-dml-cluster: rust
x-booking-et-serialized-state: E_l2nKlEKtgKvRWE5vxwun_-NtUkOGY0oL2Cwpz1QsoXMz-M7fTtgQihU4l_pg-mv
x-booking-pageview-id: a99e58d3311c087c
x-booking-site-type-id: 1
x-booking-topic: capla_browser_b-property-web-property-page
Content-Length: 772
Origin: https://www.booking.com
DNT: 1
Sec-GPC: 1
Connection: keep-alive
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
Priority: u=4
Pragma: no-cache
Cache-Control: no-cache
TE: trailers
"""
# Cookie: bkng=11UmFuZG9tSVYkc2RlIyh9Yaa29%2F3xUOLbca8KLfxLPeceNlp74nKlBMzqY9%2FRpLTX61fvWKLiriKj6MlAofO6Ai7FQ8tOuy7EzqzIBW5TTEh0iR9aJ6kc0QMTjVRmYmk5cEuTF38d5hfmv2xU%2Fj0Nq4rMILLTelqzFZOHaJRtFk05PXQLcBxpLNL6uwFzG43jIh92PKBRazs%3D; pcm_personalization_disabled=0; bkng_sso_auth=CAIQ0+WGHxp4Rfa7DgKgeHPfgKSy4Glk9Bby/XCW3/nWZFB36XCiCpecGUX4jL4+4VrwU38XRVtcSRI2bOIctfFTZgYZypb7fHDKjKqQ31pRU+c9fKFGNyBmvPJu3lKzdF0l1934tY8HnbZP7Js6xS/T/xeTD8x9YPM0Udc6rnYV; pcm_consent=consentedAt%3D2025-05-18T12%3A38%3A04.935Z%26countryCode%3DCY%26expiresAt%3D2025-11-14T12%3A38%3A04.935Z%26implicit%3Dfalse%26regionCode%3D01%26regulation%3Dgdpr%26legacyRegulation%3Dgdpr%26consentId%3D74b9c266-1d8c-476d-94f0-7f9623d95ec3%26analytical%3Dtrue%26marketing%3Dtrue; cors_js=1; OptanonConsent=isGpcEnabled=1&datestamp=Sun+May+18+2025+15%3A38%3A04+GMT%2B0300+(Eastern+European+Summer+Time)&version=202501.2.0&browserGpcFlag=1&isIABGlobal=false&hosts=&consentId=744eb1b9-3e21-4d53-9907-315cc01ff711&interactionCount=0&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0004%3A1&implicitConsentCountry=GDPR&implicitConsentDate=1747571881084&backfilled_at=1747571884926&backfilled_seed=1; BJS=-; lastSeen=0; b=%7B%22countLang%22%3A2%7D; bkng_sso_session=e30; bkng_sso_ses=eyJib29raW5nX2dsb2JhbCI6W3siaCI6IkI5NXRmZlpsWnJQQ2VJak9xdHRGZUFpTFc0OXZHNWtWSE15SE1RZWZ0YWsiLCJhIjoxfV19; OptanonAlertBoxClosed=2025-05-18T12:38:04.515Z; bkng_sso_auth_1747571884=CAIQ0+WGHxp4Rfa7DgKgeHPfgKSy4Glk9Bby/XCW3/nWZFB36XCiCpecGUX4jL4+4VrwU38XRVtcSRI2bOIctfFTZgYZypb7fHDKjKqQ31pRU+c9fKFGNyBmvPJu3lKzdF0l1934tY8HnbZP7Js6xS/T/xeTD8x9YPM0Udc6rnYV; _gcl_au=1.1.338031275.1747571885; bkng_prue=1; _ga_A12345=GS2.1.s1747571885$o1$g1$t1747571888$j0$l0$h2109803579; _ga=GA1.1.1287742929.1747571885; FPID=FPID2.2.48U%2BqaROuyMKzZ4x3zVUhhbm9bGD2ax984BoBu8Ivlo%3D.1747571885; FPLC=YXKsliKc5CY7TRn2QMIckUp%2BZwKDN7oiX7611JsEmPJYf4%2BxzbQY4Ie9ENpuhQrlUFDXI2sL3UA7aneM%2FfswcqSVLjnzAFPBDOmMe3A4VFYgB%2Fz6LD9cpGF%2B0XEmGA%3D%3D; FPAU=1.1.338031275.1747571885; _yjsu_yjad=1747571886.76ab9f7e-910d-496d-a785-219a95222ae9; aws-waf-token=3aca211b-8568-4ce1-9162-bfe14018f053:IAoAhF1Yo+JSAAAA:vEU+/8unq7y3Dc+8868lM2yfRr9BDZISlfD8BgBRwrUTecCLzuhPd4FDfqAwIUnzwMxZtZ7YWlg7VXyyV5l29qlkwINCrodEsYLcUHdeadz1enOYVi7ML6MOj67EnBpLL8nxqKMQTLxeEFshCe9mbsbILUabg2hvzMbetWC/GBoiEcmpT2u6dJUFsNF7LsvgVjrcMCPAjMdBVoaz4Aq/A9DVVVqz0OeBmysExm539B+esr28iaf/MNBtxPQbhqRh7yCAMA==

HEADERS = email.message_from_string(HEADERS_STR)
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
                # headers=dict(HEADERS),
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