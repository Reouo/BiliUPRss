# BiliUPRss
## 功能
提供up主的uid和cookie后可以爬取12条动态并转为符合rss规范的xml格式
* 注：
1. 自动忽略分享动态，
2. 由于没有代理和cookie，爬取专栏时候需要反复请求，故设计了sleep(15),爬取速度不如其他动态类型
3. 发布时间后的时分为00:00时候，请忽略具体时间(日期是准的)
---
