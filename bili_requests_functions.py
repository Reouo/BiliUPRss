import os
import re
import time
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import psycopg2.sql
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
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            # 格式: "2024-03-25"
            input_format = '%Y-%m-%d'
            dt = datetime.strptime(date_str, input_format)
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
            # time_part = re.search(r'\d{2}:\d{2}', date_str).group()
            # current_year = datetime.now(pytz.timezone('Asia/Shanghai')).year
            # current_month = datetime.now(pytz.timezone('Asia/Shanghai')).month
            # current_day = datetime.now(pytz.timezone('Asia/Shanghai')).day
            # yesterday = datetime(current_year, current_month, current_day, 0, 0, 0, tzinfo=pytz.timezone('Asia/Shanghai')) - timedelta(days=1)
            # input_format = '%Y-%m-%d %H:%M'
            # dt = datetime.strptime(f"{yesterday.strftime('%Y-%m-%d')} {time_part}", input_format)
            dt = datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(days=1)
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
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif',
                  '.bmp': 'image/bmp', '.webp': 'image/webp'}
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
    headers = {'User-Agent': user_agent, 'Referer': space_dynamic_url, 'Origin': origin_url, 'Cookie': user_cookie}
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
                 'pics': data_pics, 'type': data_type})
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
                 'pic': data_pic, 'type': data_type})
            print('获取了一条视频动态')
        # 处理专栏
        elif data_type == 'DYNAMIC_TYPE_ARTICLE':
            data_id = item['basic']['rid_str']
            # 专栏板块需要重新请求
            # 设置User-Agent
            user_agent = UserAgent().random
            article_origin_url = 'https://www.bilibili.com'
            article_dynamic_url = f'https://www.bilibili.com/read/cv{data_id}/'
            headers = {'User-Agent': user_agent, 'Referer': article_dynamic_url, 'Origin': article_origin_url,
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
        if item['type'] == 'DYNAMIC_TYPE_DRAW' or item['type'] == 'DYNAMIC_TYPE_WORD':
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


# 生成rss(因为数据库里忘记放uid了，只好更新该函数)
def reload_rss(name_id_title_time_text_pics_list):
    # 初始化 RSS 生成器
    fg = FeedGenerator()
    fg.id(f'https://bilibili.com')
    fg.title('筛选后的B站动态')
    fg.link(href=f'https://bilibili.com')
    fg.description('经tags筛选后的的B站动态')
    fg.lastBuildDate(parse_and_format_date())

    # 遍历动态数据
    for item in name_id_title_time_text_pics_list:
        # 图文或纯文本动态
        if item['type'] == 'DYNAMIC_TYPE_DRAW' or item['type'] == 'DYNAMIC_TYPE_WORD':
            entry = FeedEntry()
            entry.id(item['detail_url'])
            entry.title(item['title'])
            entry.link(href=item['detail_url'])

            # 在 description 中嵌入图片
            description = item['text']
            for pic in item['pics']:
                description += f'<br><img src="{pic}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in item['pics']:
                entry.enclosure(pic, 0, get_mime_type(pic))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(str(item['time'])))

            # 添加到 RSS
            fg.add_entry(entry)
        # 视频动态
        elif item['type'] == 'DYNAMIC_TYPE_AV':
            entry = FeedEntry()
            entry.id(item['detail_url'])
            entry.title(item['title'])
            entry.link(href=item['detail_url'])

            # 使用正则表达式匹配 bvid= 之后的内容
            pattern = r"bvid=([^&]+)"
            match = re.search(pattern, item['detail_url'])
            bvid = match.group(1)
            # 使用 iframe 嵌入视频播放器
            player_url = f"https://player.bilibili.com/player.html?aid=&bvid={bvid}&cid=&p=1&as_wide=1&high_quality=1&danmaku=0&t=0"
            description = item['desc']
            description += f'<br><iframe width="560" height="315" src="{player_url}" frameborder="0" allowfullscreen></iframe>'

            # 获取封面图片链接
            cover_image_url = item['pics'][0]
            description += f'<br><img src="{cover_image_url}">'

            entry.description(description)

            entry.pubDate(parse_and_format_date(str(item['time'])))
            fg.add_entry(entry)


        # 专栏动态
        elif item['type'] == 'DYNAMIC_TYPE_ARTICLE':
            entry = FeedEntry()
            entry.id(item['detail_url'])
            entry.title(item['title'])
            entry.link(href=item['detail_url'])

            # 在 description 中嵌入图片
            description = item['text']
            for pic in item['pics']:
                description += f'<br><img src="{pic}">'
            entry.description(description)

            # 添加图片附件（保留 enclosure）
            for pic in item['pics']:
                entry.enclosure(pic, 0, get_mime_type(pic))

            # 设置发布时间
            entry.pubDate(parse_and_format_date(str(item['time'])))

            # 添加到 RSS
            fg.add_entry(entry)

    # 确保输出目录存在
    output_dir = 'xml_files'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 写入 RSS 到文件
    rss_output_path = os.path.join(output_dir, 'filtered.xml')
    fg.rss_file(rss_output_path, pretty=True)  # 使用 rss_file 方法
    print(f'RSS文件已输出到 {rss_output_path}')


# 获取组成RSS所需数据
def fetch_all_data(database, user, password, host, port, table):
    # 连接到数据库
    connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cursor = connect.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # 构建 SQL 查询
    sql = psycopg2.sql.SQL("SELECT * FROM {table}").format(table=psycopg2.sql.Identifier(table))
    # 执行查询
    cursor.execute(sql)
    # 获取所有行数据
    rows = cursor.fetchall()
    # 将每一行数据转换为字典，并放入列表中
    dict_list = [dict(row) for row in rows]
    cursor.close()
    connect.close()
    print('数据库字典获取成功')
    print(dict_list)
    return dict_list


# 建表
def create_table_data(database, user, password, host, port, table_data):
    connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cursor = connect.cursor()
    sql = psycopg2.sql.SQL('''CREATE TABLE IF NOT EXISTS {table_data} (
        up_name CHARACTER VARYING, 
        detail_url CHARACTER VARYING PRIMARY KEY,
        title TEXT,
        time DATE,
        text TEXT,
        pics TEXT[],
        type CHARACTER VARYING
    );''').format(table_data=psycopg2.sql.Identifier(table_data))
    cursor.execute(sql)
    connect.commit()
    cursor.close()
    connect.close()
    print('数据表创建成功/已存在')


def create_table_tags(database, user, password, host, port, table_tags):
    connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cursor = connect.cursor()
    sql = psycopg2.sql.SQL('''CREATE TABLE IF NOT EXISTS {table_tags} (
        tag CHARACTER VARYING  PRIMARY KEY
    );''').format(table_tags=psycopg2.sql.Identifier(table_tags))
    cursor.execute(sql)
    connect.commit()
    cursor.close()
    connect.close()
    print('标签表创建成功/已存在')


def create_table_filtered(database, user, password, host, port, table_filtered):
    connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cursor = connect.cursor()
    sql = psycopg2.sql.SQL("""
        CREATE TABLE IF NOT EXISTS {table_filtered} (
            up_name CHARACTER VARYING, 
            detail_url CHARACTER VARYING PRIMARY KEY,
            title TEXT,
            time DATE,
            text TEXT,
            pics TEXT[],
            type CHARACTER VARYING,
            tags TEXT[]
        );
    """).format(table_filtered=psycopg2.sql.Identifier(table_filtered))
    cursor.execute(sql)
    connect.commit()
    cursor.close()
    connect.close()
    print('过滤表创建成功/已存在')


# 写数据
def write_bili_dynamics_table(name_id_title_time_text_pics_type_list):
    connect = psycopg2.connect(database='reouo', user='postgres', password='12345', host='127.0.0.1', port='5432')
    cursor = connect.cursor()
    insert_sql = '''
            INSERT INTO bili_dynamics (up_name, detail_url, title, time, text, pics, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (detail_url) DO NOTHING;
            '''
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
            cursor.execute(insert_sql, (up_name, detail_url, title, time, text, pics, type))
    connect.commit()
    cursor.close()
    connect.close()
    print('数据成功写入数据库')


def filter_data(database, user, password, host, port, table_data, table_tags, table_filtered):
    connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cursor = connect.cursor()

    # SQL 查询，用于匹配 tags 表中的 tag 与 bili_dynamics 表中的 text 和 title，并获取匹配的 tag
    sql = psycopg2.sql.SQL("""
        SELECT bd.up_name, bd.detail_url, bd.title, bd.time, bd.text, bd.pics, bd.type, array_agg(t.tag) AS tags
        FROM {table_data} bd
        JOIN {table_tags} t ON bd.text LIKE '%' || t.tag || '%' OR bd.title LIKE '%' || t.tag || '%'
        GROUP BY bd.up_name, bd.detail_url, bd.title, bd.time, bd.text, bd.pics, bd.type
    """).format(table_data=psycopg2.sql.Identifier(table_data), table_tags=psycopg2.sql.Identifier(table_tags))

    cursor.execute(sql)
    results = cursor.fetchall()

    # 批量插入筛选结果到新表，使用 ON CONFLICT DO UPDATE 来处理重复键
    insert_sql = psycopg2.sql.SQL("""
        INSERT INTO {table_filtered} (up_name, detail_url, title, time, text, pics, type, tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (detail_url) DO UPDATE SET
            up_name = EXCLUDED.up_name,
            title = EXCLUDED.title,
            time = EXCLUDED.time,
            text = EXCLUDED.text,
            pics = EXCLUDED.pics,
            type = EXCLUDED.type,
            tags = EXCLUDED.tags;
    """).format(table_filtered=psycopg2.sql.Identifier(table_filtered))

    # 使用 executemany 进行批量插入
    psycopg2.extras.execute_batch(cursor, insert_sql, results, page_size=1000)

    connect.commit()
    cursor.close()
    connect.close()
    print('筛选数据已插入到新表')


def clean_table(database, user, password, host, port, table):
    try:
        connect = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    except:
        print('连接失败')
    cursor = connect.cursor()
    # 使用 psycopg2.sql 模块构建安全的 SQL 查询
    sql = psycopg2.sql.SQL('''
            DELETE FROM {table}
        ''').format(table=psycopg2.sql.Identifier(table))
    cursor.execute(sql)
    connect.commit()
    cursor.close()
    connect.close()
    print('数据成功清除')


if __name__ == '__main__':
    # 爬虫用
    up_uid = ''
    user_cookie = ''
    # 数据库用
    database = ''
    user = ''
    password = ''
    host = ''
    port = ''
    table_data = ''
    table_tags = ''
    table_filtered = ''
    # 以下实行功能
    # name_id_title_time_text_pics_type_list = get_name_id_title_time_text_pics_list(up_uid, user_cookie)
    # write_bili_dynamics_table(name_id_title_time_text_pics_type_list)
    # filter_data(database, user, password, host, port, table_data, table_tags, table_filtered)
    # dict = fetch_all_data(database, user, password, host, port, table_filtered)
    # reload_rss(dict)
    # create_bili_dynamics_table_data(database, user, password, host, port,table_data)
    # create_bili_dynamics_table_tags(database, user, password, host, port,table_tags)
    # create_table_filtered(database, user, password, host, port, table_filtered)
    # clean_table(database, user, password, host, port,table)
