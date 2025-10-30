.PHONY: crawl
crawl:
	scrapy crawl spider -a max_hotels=100 -a agg_days=1


.PHONY: fast
fast:
	scrapy crawl spider -a countries=it,sr,za -a max_hotels=10 -a agg_days=1

.PHONY: countries
countries:
	scrapy crawl countries


.PHONY: sync
sync:
	aws s3 sync output s3://ab-users/grachev/marketplace/output

.PHONY: syncback
syncback:
	aws s3 sync s3://ab-users/grachev/marketplace/output output 

