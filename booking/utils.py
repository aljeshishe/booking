from datetime import date, datetime
from glob import glob
import logging
import numpy as np
import pandas as pd
import scrapy
from typing import Optional, Dict, Any, List
import json
import hashlib

from parse import parse


class DataProcessor:
    """Enhanced data processing utilities for booking data"""
    
    @staticmethod
    def validate_price_data(price_data: Dict[str, Any]) -> bool:
        """Validate price data structure"""
        required_fields = ['hotel_id', 'country']
        return all(field in price_data for field in required_fields)
    
    @staticmethod
    def calculate_price_metrics(prices: List[float]) -> Dict[str, float]:
        """Calculate comprehensive price statistics"""
        if not prices:
            return {}
        
        prices_array = np.array(prices)
        return {
            'min_price': float(np.min(prices_array)),
            'max_price': float(np.max(prices_array)),
            'avg_price': float(np.mean(prices_array)),
            'median_price': float(np.median(prices_array)),
            'std_price': float(np.std(prices_array)),
            'q25_price': float(np.percentile(prices_array, 25)),
            'q75_price': float(np.percentile(prices_array, 75)),
            'price_count': len(prices)
        }
    
    @staticmethod
    def generate_data_hash(data: Dict[str, Any]) -> str:
        """Generate hash for data deduplication"""
        # Create a deterministic string representation
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()


def filter_in(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter dataframe with logging"""
    found = df.query(query)
    print(f"removing {len(df) - len(found)}/{len(df)} rows")
    return found


def read_jsonl_files(path: str) -> pd.DataFrame:
    """Enhanced JSONL file reader with better error handling"""
    DT_LEN = len("2024-12-12 18:34:25")
    merged = pd.DataFrame()
    
    try:
        files = sorted(glob("output/*.jsonl"))
        if not files:
            print(f"No JSONL files found in output directory")
            return pd.DataFrame()
            
        for file_name in files:
            print(f"Reading {file_name}")
            try:
                result = parse("output/{date} {time} {postfix}", file_name)
                if result is None:
                    print(f"Failed to parse filename: {file_name}")
                    continue
                    
                if result["postfix"].startswith("fast"):
                    print(f"Skipping fast run: {file_name}")
                    continue
                    
                dt = date.fromisoformat(result["date"])
                
                newdf = pd.read_json(file_name, lines=True)
                
                # Handle different ID columns
                id_col = 'ad_id' if 'ad_id' in newdf.columns else 'hotel_id'
                if id_col not in newdf.columns:
                    print(f"Warning: No ID column found in {file_name}")
                    continue
                
                assert newdf[id_col].duplicated().sum() == 0, f"Expected no duplicates in {file_name}"
                newdf.set_index(id_col, inplace=True)
                
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
                
            except Exception as e:
                print(f"Error processing file {file_name}: {e}")
                continue
                
    except Exception as e:
        print(f"Error reading JSONL files: {e}")
        return pd.DataFrame()
        
    return merged


def handle_failure(spider_instance, failure):
    """Enhanced failure handler with detailed logging"""
    spider_instance.logger.error(f"Request failed: {repr(failure)}")
    
    request = failure.request
    
    # Log request details for debugging
    spider_instance.logger.debug(f"Failed request URL: {request.url}")
    spider_instance.logger.debug(f"Failed request method: {request.method}")
    spider_instance.logger.debug(f"Failed request headers: {request.headers}")
    
    if failure.check(scrapy.spidermiddlewares.httperror.HttpError):
        response = failure.value.response
        spider_instance.logger.warning(
            f"HTTP error {response.status} on {response.url}. "
            f"Response body: {response.body[:200]}"
        )
        
        # Log response headers for debugging
        spider_instance.logger.debug(f"Response headers: {response.headers}")
        
    elif failure.check(scrapy.downloadermiddlewares.retry.RetryMiddleware):
        spider_instance.logger.warning(
            f"Request failed and gave up retrying after maximum attempts: {request.url}"
        )
        
    elif failure.check(scrapy.core.downloader.handlers.http11.TunnelError):
        spider_instance.logger.warning(f"Tunnel connection failed for: {request.url}")
        
    else:
        # Log other types of failures
        spider_instance.logger.error(f"Unknown failure type: {failure.type}")
        spider_instance.logger.error(f"Failure value: {failure.value}")


def setup_logging(spider_name: str, log_level: str = "INFO") -> logging.Logger:
    """Setup enhanced logging for spiders"""
    logger = logging.getLogger(spider_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create file handler
    fh = logging.FileHandler(f'logs/{spider_name}.log')
    fh.setLevel(getattr(logging, log_level.upper()))
    fh.setFormatter(formatter)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
