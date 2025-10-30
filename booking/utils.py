from datetime import date
from glob import glob
import numpy as np
import pandas as pd
import scrapy

from parse import parse


def filter_in(df, query: str) -> pd.DataFrame:
    found = df.query(query)
    print(f"removing {len(df) - len(found)}/{len(df)} rows")
    return found


def read_jsonl_files(path: str):
    DT_LEN = len("2024-12-12 18:34:25")
    merged = pd.DataFrame()
    for file_name in sorted(glob("output/*.jsonl")):
        print(f"Reading {file_name}")
        result = parse("output/{date} {time} {postfix}", file_name)
        if result is None:
            print(f"Failed to parse {file_name}")
            continue
        if result["postfix"].startswith("fast"):
            print(f"Skipping fast run")
            continue
        dt = date.fromisoformat(result["date"])
        
        newdf = pd.read_json(file_name, lines=True)
        assert newdf.ad_id.duplicated().sum() == 0, "Expected no duplicates"
        newdf.set_index("ad_id", inplace=True)
        if merged.empty:
            merged = newdf
            merged["delete_date"] = np.nan
            continue
        
        condition = ~merged.index.isin(newdf.index) & merged['delete_date'].isna()
        merged.loc[condition, 'delete_date'] = dt
        new_deleted_count = condition.sum()

        new = newdf.index.difference(merged.index)
        merged = pd.concat([merged, newdf.loc[new]])
        print(f"Total: {len(merged)} read: {len(newdf)} new: {len(new)} deleted: {new_deleted_count}")
    return merged


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
