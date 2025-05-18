.PHONY: crawl
crawl:
	scrapy crawl spider -a countries=it -a max_hotels=1200


.PHONY: fast
fast:
	scrapy crawl spider -a countries=it -a fast=1

.PHONY: sync
sync:
	aws s3 sync output s3://ab-users/grachev/marketplace/output

.PHONY: syncback
syncback:
	aws s3 sync s3://ab-users/grachev/marketplace/output output 

