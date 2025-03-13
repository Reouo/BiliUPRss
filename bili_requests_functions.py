import os
import requests
from fake_useragent import UserAgent
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from datetime import datetime, timedelta
import pytz
import re
import time


# 日期转化
def parse_and_format_date(date_str=None):
    if date_str:
        # 处理不同格式的日期字符串
        if isinstance(date_str, int):
            # 默认是时间戳
            dt = datetime.fromtimestamp(date_str)
        elif re.match(r'^\d{4}年\d{2}月\d{2}日$', date_str):
            # 格式: "2024年03月25日"
            input_format = '%Y年%m月%d日'
            dt = datetime.strptime(date_str, input_format)
        elif re.match(r'^\d{2}月\d{2}日$', date_str):
            # 格式: "03月25日"
            current_year = datetime.now(pytz.timezone('Asia/Shanghai')).year
            date_str = f"{current_year}年{date_str}"
            input_format = '%Y年%m月%d日'
            dt = datetime.strptime(date_str, input_format)
        elif re.match(r'^\d+分钟前$', date_str):
            # 格式: "n分钟前"
            minutes = int(re.search(r'\d+', date_str).group())
            dt = datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(minutes=minutes)
        elif re.match(r'^\d+小时前$', date_str):
            # 格式: "n小时前"
            hours = int(re.search(r'\d+', date_str).group())
            dt = datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(hours=hours)
        elif re.match(r'^\d+天前$', date_str):
            # 格式: "n天前"
            days = int(re.search(r'\d+', date_str).group())
            dt = datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(days=days)
        else:
            raise ValueError(f"无法解析的日期格式: {date_str}")
    else:
        # 直接获取当前时间（用于 lastBuildDate）
        dt = datetime.now(pytz.timezone('Asia/Shanghai'))  # 北京时间

    # 转换为 UTC 时间并格式化
    dt_utc = dt.astimezone(pytz.utc)
    return dt_utc.strftime('%a, %d %b %Y %H:%M:%S %z')


# 拿到图片后缀
def get_mime_type(url):
    # 分析图片后缀
    _, ext = os.path.splitext(url)
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext.lower(), 'application/octet-stream')


def get_id_title_time_text_pics_list(up_uid, user_cookie):
    # features可能因人而异
    features = 'itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,forwardListHidden,decorationCard,commentsNewVersion,onlyfansAssetsV2,ugcDelete,onlyfansQaCard'
    origin_url = 'https://space.bilibili.com'
    space_dynamic_url = f'https://space.bilibili.com/{up_uid}/dynamic'
    space_items_url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?offset=&host_mid={up_uid}'
    space_items_url = space_items_url + f'&features={features}&timezone_offset=-480&platform=web'
    space_items_url = space_items_url + '&x-bili-device-req-json={"platform":"web","device":"pc"}'

    # 设置User-Agent
    user_agent = UserAgent().random
    headers = {
        'User-Agent': user_agent,
        'Referer': space_dynamic_url,
        'Origin': origin_url,
        'Cookie': user_cookie}
    response = requests.get(space_items_url, headers=headers)
    data = response.json()

    id_title_time_text_pics_type_list = []
    for item in data['data']['items']:
        data_type = item['type']
        # 处理图文以及纯文本
        if data_type == 'DYNAMIC_TYPE_DRAW' or data_type == 'DYNAMIC_TYPE_WORD':
            data_id = item['id_str']
            data_title = item['modules']['module_dynamic']['major']['opus']['title']
            data_time = item['modules']['module_author']['pub_time']
            data_text = item['modules']['module_dynamic']['major']['opus']['summary']['text']
            data_pics = item['modules']['module_dynamic']['major']['opus']['pics']
            id_title_time_text_pics_type_list.append(
                {'id': data_id, 'title': data_title, 'time': data_time, 'text': data_text, 'pics': data_pics,
                 'type': data_type})
        # 处理视频
        elif data_type == 'DYNAMIC_TYPE_AV':
            data_title = item['modules']['module_dynamic']['major']['archive']['title']
            data_time = item['modules']['module_author']['pub_time']
            data_bvid = item['modules']['module_dynamic']['major']['archive']['bvid']
            data_desc = item['modules']['module_dynamic']['major']['archive']['desc']
            data_pic = item['modules']['module_dynamic']['major']['archive']['cover']
            id_title_time_text_pics_type_list.append(
                {'title': data_title, 'time': data_time, 'bvid': data_bvid, 'desc': data_desc, 'pic': data_pic,
                 'type': data_type})
        # 处理专栏
        elif data_type == 'DYNAMIC_TYPE_ARTICLE':
            data_id = item['basic']['rid_str']
            # 专栏板块需要重新请求
            # 设置User-Agent
            user_agent = UserAgent().random
            article_origin_url = 'https://www.bilibili.com'
            article_dynamic_url = f'https://www.bilibili.com/read/cv{data_id}/'
            headers = {
                'User-Agent': user_agent,
                'Referer': article_dynamic_url,
                'Origin': article_origin_url,
                'Cookie': user_cookie}
            article_detail_url = f'https://api.bilibili.com/x/article/view?id={data_id}&gaia_source=main_web'
            response = requests.get(article_detail_url, headers=headers)
            content = response.json()
            content_title = content['data']['title']
            content_time = content['data']['publish_time']
            print(content_time)
            print(type(content_time))
            # 当专栏中有图片时
            if 'opus' in content['data']:
                content_text = ''
                content_pics = []
                for item in content['data']['opus']['content']['paragraphs']:
                    if item['para_type'] == 1:
                        content_text += item['text']['nodes'][0]['word']['words']
                    if item['para_type'] == 2:
                        content_pics.append(item['pic']['pics'][0]['url'])

                id_title_time_text_pics_type_list.append(
                    {'id': data_id, 'title': content_title, 'time': content_time, 'text': content_text,
                     'pics': content_pics, 'type': data_type})  # 这里的pics只需要按顺序取出就行了，里面是字符串不是字典
            # 纯文本专栏
            else:
                content_text = content['data']['content']
                content_pics = []
                id_title_time_text_pics_type_list.append(
                    {'id': data_id, 'title': content_title, 'time': content_time, 'text': content_text,
                     'type': data_type})
            time.sleep(15)
    return id_title_time_text_pics_type_list


def load_rss(id_title_time_text_pics_list, up_uid):
    # 初始化 RSS 生成器
    fg = FeedGenerator()
    fg.id(f'https://space.bilibili.com/{up_uid}')
    fg.title(f'{up_uid}的B站动态')
    fg.link(href=f'https://space.bilibili.com/{up_uid}')
    fg.description(f'{up_uid}的B站动态')
    fg.lastBuildDate(parse_and_format_date())

    # 遍历动态数据
    for id_title_time_text_pics_dict in id_title_time_text_pics_list:
        # 图文或纯文本动态
        if id_title_time_text_pics_dict['type'] == 'DYNAMIC_TYPE_DRAW' or id_title_time_text_pics_dict[
            'type'] == 'DYNAMIC_TYPE_WORD':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/opus/{id_title_time_text_pics_dict['id']}")
            entry.title(id_title_time_text_pics_dict['title'])
            entry.link(href=f"https://www.bilibili.com/opus/{id_title_time_text_pics_dict['id']}")

            # 在 description 中嵌入图片
            description = id_title_time_text_pics_dict['text']
            for pic in id_title_time_text_pics_dict['pics']:
                description += f'<br><img src="{pic["url"]}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in id_title_time_text_pics_dict['pics']:
                entry.enclosure(pic['url'], 0, get_mime_type(pic['url']))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(id_title_time_text_pics_dict['time']))

            # 添加到 RSS
            fg.add_entry(entry)
        # 视频动态
        elif id_title_time_text_pics_dict['type'] == 'DYNAMIC_TYPE_AV':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/video/{id_title_time_text_pics_dict['bvid']}")
            entry.title(id_title_time_text_pics_dict['title'])
            entry.link(href=f"https://www.bilibili.com/video/{id_title_time_text_pics_dict['bvid']}")

            # 使用 iframe 嵌入视频播放器
            player_url = f"https://player.bilibili.com/player.html?aid=&bvid={id_title_time_text_pics_dict['bvid']}&cid=&p=1&as_wide=1&high_quality=1&danmaku=0&t=0"
            description = id_title_time_text_pics_dict['desc']
            description += f'<br><iframe width="560" height="315" src="{player_url}" frameborder="0" allowfullscreen></iframe>'

            # 获取封面图片链接
            cover_image_url = id_title_time_text_pics_dict['pic']
            description += f'<br><img src="{cover_image_url}">'

            entry.description(description)

            entry.pubDate(parse_and_format_date(id_title_time_text_pics_dict['time']))
            fg.add_entry(entry)


        # 专栏动态
        elif id_title_time_text_pics_dict['type'] == 'DYNAMIC_TYPE_ARTICLE':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/read/cv{id_title_time_text_pics_dict['id']}")
            entry.title(id_title_time_text_pics_dict['title'])
            entry.link(href=f"https://www.bilibili.com/read/cv{id_title_time_text_pics_dict['id']}")

            # 在 description 中嵌入图片
            description = id_title_time_text_pics_dict['text']
            for pic in id_title_time_text_pics_dict['pics']:
                description += f'<br><img src="{pic}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in id_title_time_text_pics_dict['pics']:
                entry.enclosure(pic, 0, get_mime_type(pic))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(id_title_time_text_pics_dict['time']))

            # 添加到 RSS
            fg.add_entry(entry)

    # 确保输出目录存在
    output_dir = 'xml_files'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 写入 RSS 到文件
    rss_output_path = os.path.join(output_dir, f'{up_uid}.xml')
    fg.rss_file(rss_output_path, pretty=True)  # 使用 rss_file 方法
    print(f'RSS 文件已输出到 {rss_output_path}')
