from datetime import datetime, timezone
from pathlib import Path
import re
import json
from urllib.parse import urlparse
from itemadapter import ItemAdapter


def escape(s):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s)

class BookingPipeline:
    def open_spider(self, spider):
        now_str = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.file_path = Path(f"output/{now_str}.jsonl_")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.file_path.open("w")
        spider.logger.info(f"Writing to {self.file_path}")

    def close_spider(self, spider):
        self.file.close()
        self.file_path.rename(self.file_path.with_suffix(".jsonl"))
        

    def process_item(self, item, spider):
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        self.file.write(line)
        return item