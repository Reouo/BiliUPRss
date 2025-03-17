import os
import re
import time
from datetime import datetime, timedelta

import psycopg2
import pytz
import requests
from fake_useragent import UserAgent
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator


# 日期转化(适用于rss)
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
        elif re.match(r'^昨天\s+\d{2}:\d{2}$', date_str):
            # 格式: "昨天 20:34"
            time_part = re.search(r'\d{2}:\d{2}', date_str).group()
            current_year = datetime.now(pytz.timezone('Asia/Shanghai')).year
            current_month = datetime.now(pytz.timezone('Asia/Shanghai')).month
            current_day = datetime.now(pytz.timezone('Asia/Shanghai')).day
            yesterday = datetime(current_year, current_month, current_day, 0, 0, 0, tzinfo=pytz.timezone('Asia/Shanghai')) - timedelta(days=1)
            input_format = '%Y-%m-%d %H:%M'
            dt = datetime.strptime(f"{yesterday.strftime('%Y-%m-%d')} {time_part}", input_format)
        else:
            raise ValueError(f"无法解析的日期格式: {date_str}")
    else:
        # 直接获取当前时间（用于 lastBuildDate）
        dt = datetime.now(pytz.timezone('Asia/Shanghai'))  # 北京时间

    # 转换为 UTC 时间并格式化
    dt_utc = dt.astimezone(pytz.utc)
    return dt_utc.strftime('%a, %d %b %Y %H:%M:%S %z')


# 日期转化(在parse_and_format_date基础上，适用于sql里的date)
def load_and_format_date(strf_time):
    # 解析日期字符串为 datetime 对象
    try:
        # 尝试解析为 '%a, %d %b %Y %H:%M:%S %z' 格式
        dt = datetime.strptime(strf_time, '%a, %d %b %Y %H:%M:%S %z')
    except ValueError:
        # 如果解析失败，尝试解析为其他格式
        dt = parse_and_format_date(strf_time)

    # 转换为 PostgreSQL 的 DATE 格式
    return dt.date()


# 拿到图片后缀，确定附件的解析方式(可能多余)
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


# 获取如函数名所示的各项数据的字典的列表
def get_name_id_title_time_text_pics_list(up_uid, user_cookie):
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
    up_name = data['data']['items'][0]['modules']['module_author']['name']
    name_id_title_time_text_pics_type_list = []
    for item in data['data']['items']:
        data_type = item['type']
        # 处理图文以及纯文本
        if data_type == 'DYNAMIC_TYPE_DRAW' or data_type == 'DYNAMIC_TYPE_WORD':
            data_id = item['id_str']
            data_title = item['modules']['module_dynamic']['major']['opus']['title']
            data_time = item['modules']['module_author']['pub_time']
            data_text = item['modules']['module_dynamic']['major']['opus']['summary']['text']
            data_pics = item['modules']['module_dynamic']['major']['opus']['pics']
            name_id_title_time_text_pics_type_list.append(
                {'name': up_name, 'id': data_id, 'title': data_title, 'time': data_time, 'text': data_text,
                 'pics': data_pics,
                 'type': data_type})
            print('获取了一条图文动态')
        # 处理视频
        elif data_type == 'DYNAMIC_TYPE_AV':
            data_title = item['modules']['module_dynamic']['major']['archive']['title']
            data_time = item['modules']['module_author']['pub_time']
            data_bvid = item['modules']['module_dynamic']['major']['archive']['bvid']
            data_desc = item['modules']['module_dynamic']['major']['archive']['desc']
            data_pic = item['modules']['module_dynamic']['major']['archive']['cover']
            name_id_title_time_text_pics_type_list.append(
                {'name': up_name, 'title': data_title, 'time': data_time, 'bvid': data_bvid, 'desc': data_desc,
                 'pic': data_pic,
                 'type': data_type})
            print('获取了一条视频动态')
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
            # 当专栏中有图片时
            if 'opus' in content['data']:
                content_text = ''
                content_pics = []
                for item in content['data']['opus']['content']['paragraphs']:
                    if item['para_type'] == 1:
                        content_text += item['text']['nodes'][0]['word']['words']
                    if item['para_type'] == 2:
                        content_pics.append(item['pic']['pics'][0]['url'])

                name_id_title_time_text_pics_type_list.append(
                    {'name': up_name, 'id': data_id, 'title': content_title, 'time': content_time, 'text': content_text,
                     'pics': content_pics, 'type': data_type})  # 这里的pics只需要按顺序取出就行了，里面是字符串不是字典
            # 纯文本专栏
            else:
                content_text = content['data']['content']
                content_pics = []
                name_id_title_time_text_pics_type_list.append(
                    {'name': up_name, 'id': data_id, 'title': content_title, 'time': content_time, 'text': content_text,
                     'pics': content_pics, 'type': data_type})
            time.sleep(15)
            print('获取了一个专栏动态\nsleeping···')
    return name_id_title_time_text_pics_type_list


# 生成rss
def load_rss(name_id_title_time_text_pics_list, up_uid):
    # 初始化 RSS 生成器
    fg = FeedGenerator()
    fg.id(f'https://space.bilibili.com/{up_uid}')
    fg.title(f'{name_id_title_time_text_pics_list[0]['name']}的B站动态')
    fg.link(href=f'https://space.bilibili.com/{up_uid}')
    fg.description(f'{name_id_title_time_text_pics_list[0]['name']}的B站动态')
    fg.lastBuildDate(parse_and_format_date())

    # 遍历动态数据
    for item in name_id_title_time_text_pics_list:
        # 图文或纯文本动态
        if item['type'] == 'DYNAMIC_TYPE_DRAW' or item[
            'type'] == 'DYNAMIC_TYPE_WORD':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/opus/{item['id']}")
            entry.title(item['title'])
            entry.link(href=f"https://www.bilibili.com/opus/{item['id']}")

            # 在 description 中嵌入图片
            description = item['text']
            for pic in item['pics']:
                description += f'<br><img src="{pic["url"]}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in item['pics']:
                entry.enclosure(pic['url'], 0, get_mime_type(pic['url']))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(item['time']))

            # 添加到 RSS
            fg.add_entry(entry)
        # 视频动态
        elif item['type'] == 'DYNAMIC_TYPE_AV':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/video/{item['bvid']}")
            entry.title(item['title'])
            entry.link(href=f"https://www.bilibili.com/video/{item['bvid']}")

            # 使用 iframe 嵌入视频播放器
            player_url = f"https://player.bilibili.com/player.html?aid=&bvid={item['bvid']}&cid=&p=1&as_wide=1&high_quality=1&danmaku=0&t=0"
            description = item['desc']
            description += f'<br><iframe width="560" height="315" src="{player_url}" frameborder="0" allowfullscreen></iframe>'

            # 获取封面图片链接
            cover_image_url = item['pic']
            description += f'<br><img src="{cover_image_url}">'

            entry.description(description)

            entry.pubDate(parse_and_format_date(item['time']))
            fg.add_entry(entry)


        # 专栏动态
        elif item['type'] == 'DYNAMIC_TYPE_ARTICLE':
            entry = FeedEntry()
            entry.id(f"https://www.bilibili.com/read/cv{item['id']}")
            entry.title(item['title'])
            entry.link(href=f"https://www.bilibili.com/read/cv{item['id']}")

            # 在 description 中嵌入图片
            description = item['text']
            for pic in item['pics']:
                description += f'<br><img src="{pic}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in item['pics']:
                entry.enclosure(pic, 0, get_mime_type(pic))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(item['time']))

            # 添加到 RSS
            fg.add_entry(entry)

    # 确保输出目录存在
    output_dir = 'xml_files'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 写入 RSS 到文件
    rss_output_path = os.path.join(output_dir, f'{up_uid}.xml')
    fg.rss_file(rss_output_path, pretty=True)  # 使用 rss_file 方法
    print(f'RSS文件已输出到 {rss_output_path}')


# 建表
def create_bili_dynamics_table():
    connect = psycopg2.connect(database='reouo', user='postgres', password='12345', host='127.0.0.1', port='5432')
    cursor = connect.cursor()
    sql = '''CREATE TABLE IF NOT EXISTS bili_dynamics (
        up_name CHARACTER VARYING, 
        detail_url CHARACTER VARYING PRIMARY KEY,
        title TEXT,
        time DATE,
        text TEXT,
        pics TEXT[],
        type CHARACTER VARYING
    );'''
    cursor.execute(sql)
    connect.commit()
    cursor.close()
    connect.close()
    print('Table创建成功/已存在')


# 写数据
def write_bili_dynamics_table(name_id_title_time_text_pics_type_list):
    connect = psycopg2.connect(database='reouo', user='postgres', password='12345', host='127.0.0.1', port='5432')
    cursor = connect.cursor()
    for item in name_id_title_time_text_pics_type_list:
        if item['type'] == 'DYNAMIC_TYPE_DRAW' or item['type'] == 'DYNAMIC_TYPE_WORD':
            up_name = item['name']
            detail_url = f'https://www.bilibili.com/opus/{item['id']}'
            title = item['title']
            time = load_and_format_date(parse_and_format_date(item['time']))
            text = item['text']
            pics = []
            for pic in item['pics']:
                pics.append(pic['url'])
            type = item['type']
            insert_sql = '''
            INSERT INTO bili_dynamics (up_name, detail_url, title, time, text, pics, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (detail_url) DO NOTHING;
            '''
            cursor.execute(insert_sql, (up_name, detail_url, title, time, text, pics, type))
        elif item['type'] == 'DYNAMIC_TYPE_AV':
            up_name = item['name']
            detail_url = f'https://www.bilibili.com/video/{item['bvid']}'
            title = item['title']
            time = load_and_format_date(parse_and_format_date(item['time']))
            text = item['desc']
            pics = []
            pics.append(item['pic'])
            type = item['type']
            insert_sql = '''
            INSERT INTO bili_dynamics (up_name, detail_url, title, time, text, pics, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (detail_url) DO NOTHING;
            '''
            cursor.execute(insert_sql, (up_name, detail_url, title, time, text, pics, type))
        elif item['type'] == 'DYNAMIC_TYPE_ARTICLE':
            up_name = item['name']
            detail_url = f'https://www.bilibili.com/read/cv{item['id']}'
            title = item['title']
            time = load_and_format_date(parse_and_format_date(item['time']))
            text = item['text']
            pics = []
            for pic in item['pics']:
                pics.append(pic)
            type = item['type']
            insert_sql = '''
            INSERT INTO bili_dynamics (up_name, detail_url, title, time, text, pics, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (detail_url) DO NOTHING;
            '''
            cursor.execute(insert_sql, (up_name, detail_url, title, time, text, pics, type))
    connect.commit()
    cursor.close()
    connect.close()
    print('数据成功写入数据库')
def filter_contents():
    pass

if __name__ == '__main__':
    up_uid = '145239325'
    user_cookie = "buvid3=285ADB51-97F2-B63C-7F72-D16A756FBE3E16395infoc; b_nut=1740126116; _uuid=55CDAAA2-3CEE-A666-7942-7A85BB610EE6D23000infoc; enable_web_push=DISABLE; enable_feed_channel=ENABLE; home_feed_column=5; browser_resolution=1655-979; buvid4=EE80E339-C0FA-5EBE-A5F7-570E11CB4B0116972-025022108-Azs0hNockNm%2BtYmGHF5HMg%3D%3D; buvid_fp=0e6ee00f0d9ee5987c15973ffb9cce04; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDIwNDg3MjcsImlhdCI6MTc0MTc4OTQ2NywicGx0IjotMX0.NMHnq6PWgJ713_9zHeboy5nDKO7xDoC17UzdLNlX3cs; bili_ticket_expires=1742048667; header_theme_version=CLOSE; bp_t_offset_531140325=1043777155730767872; CURRENT_FNVAL=16; rpdid=|(JY~|J)|J~R0J'u~R|umYlYY; fingerprint=0e6ee00f0d9ee5987c15973ffb9cce04; buvid_fp_plain=undefined; CURRENT_QUALITY=120; PVID=3; LIVE_BUVID=AUTO5817406608563424; hit-dyn-v2=1; SESSDATA=c89efa97%2C1757327186%2C2aa96%2A32CjCpWs8aFtXARSQCCLhT_jaMFZxXZo1IrI1RIab2xqm5h6sEZcSeaCPIP-PwZzwelvESVjBhVGtNRzJEaVB0OEl0ekNLMVNwT3EwaDQyZ3prM0dCcjE2OVR3WURVRTB1SzZhd242eUhQemNjQTNxbXUweE9iZTF3cWJqdEEwdlA1RGdqeTdnS3FRIIEC; bili_jct=65215689e8b17793cafe3f80ddb23362; DedeUserID=531140325; DedeUserID__ckMd5=9480e1630b93a4f3; opus-goback=1; b_lsid=102BB994D_1958F5E0CF3; sid=4lofzu1i"
    # 以上传参
    name_id_title_time_text_pics_type_list = get_name_id_title_time_text_pics_list(up_uid, user_cookie)
    write_bili_dynamics_table(name_id_title_time_text_pics_type_list)
