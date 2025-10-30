import gzip
import io
import re
import scrapy
from functools import partial

from tqdm import tqdm


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


class CountriesSpider(scrapy.Spider):
    name = "countries"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = "https://www.booking.com/sitembk-country-en-gb.0000.xml.gz"
        self.pb = tqdm(desc="Crawling countries", unit="page", total=0) 

    async def start(self):
        self.logger.info(f"Starting to scrape countries from {self.url}")
        yield scrapy.Request(
            self.url, 
            self.parse_countries_gzip,
            priority=10,
            errback=partial(handle_failure, self),
            dont_filter=True
        )
    
    async def parse_countries_gzip(self, response):
        """
        Parse the gzipped XML file to extract country codes and generate country URLs.
        """
        self.logger.info("Parsing gzipped countries XML file")
        
        # Decompress the gzipped response
        response = scrapy.http.response.text.TextResponse(
            url=response.url,
            body=gzip.GzipFile(fileobj=io.BytesIO(response.body)).read(),
            encoding='utf-8'
        )
        response.selector.remove_namespaces()
        urls = response.xpath('//url/loc/text()').getall()
        
        self.logger.info(f"Found {len(urls)} country URLs in sitemap")
        
        # Extract country codes from URLs and generate destination URLs
        country_codes = set()
        for url in urls:
            # Extract country code from URLs like https://www.booking.com/country/xy.en-gb.html
            match = re.search(r'/country/([a-z]{2})\.en-gb\.html', url)
            if match:
                country_code = match.group(1)
                country_codes.add(country_code)
        
        self.logger.info(f"Found {len(country_codes)} unique country codes")
        
        # Generate destination URLs for each country code
        for country_code in country_codes:
            destination_url = f"https://www.booking.com/destination/country/{country_code}.en-gb.html"
            yield scrapy.Request(
                destination_url,
                callback=self.parse_country_page,
                priority=5,
                errback=partial(handle_failure, self),
                dont_filter=True,
                meta={'country_code': country_code}
            )
        self.pb.total = len(country_codes)
        self.pb.refresh()

    def parse_country_page(self, response):
        """
        Parse the country destination page to extract the full country name.
        """
        self.pb.update(1)
        country_code = response.meta['country_code']
        
        # Search for the country name using the regex pattern: country_name: 'Northern Cyprus',
        country_name_pattern = r"country_name:\s*'([^']+)'"
        
        # Search in the page source
        page_text = response.text
        match = re.search(country_name_pattern, page_text)
        
        if match:
            country_name = match.group(1)
            self.logger.info(f"Found country: {country_code} -> {country_name}")
            
            yield {
                'code': country_code,
                'name': country_name
            }
        else:
            self.logger.warning(f"Could not find country name for code: {country_code}")
            # Still yield the result with just the code
            yield {
                'code': country_code,
                'name': None
            }