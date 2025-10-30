.PHONY: prices_agg
prices_agg:
	scrapy crawl prices -a max_hotels=100 -a agg_days=1

.PHONY: prices
prices:
	scrapy crawl prices -a max_hotels=100 -a agg_days=0


.PHONY: prices_fast
prices_fast:
	scrapy crawl prices -a countries=it,sr,za -a max_hotels=3 -a agg_days=0

.PHONY: prices_fast_agg
prices_fast_agg:
	scrapy crawl prices -a countries=it,sr,za -a max_hotels=3 -a agg_days=1

.PHONY: countries
countries:
	scrapy crawl countries


.PHONY: sync
sync:
	aws s3 sync output s3://ab-users/grachev/marketplace/output

.PHONY: syncback
syncback:
	aws s3 sync s3://ab-users/grachev/marketplace/output output 

