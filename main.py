from bili_requests_functions import *

if __name__ == '__main__':
    # 爬虫用
    up_uids = ['', ]
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
    for up_uid in up_uids:
        # 爬取数据
        if True:
            name_id_title_time_text_pics_list = get_name_id_title_time_text_pics_list(up_uid, user_cookie)
        # 直接写rss
        if False:
            load_rss(name_id_title_time_text_pics_list, up_uid)
        # 建立数据表，存储爬取下来的数据
        if True:
            create_table_data(database, user, password, host, port, table_data)
        # 建立标签表，存储筛选用的标签
        if True:
            create_table_tags(database, user, password, host, port, table_tags)
        # 建立筛选表，存储筛选后的数据
        if True:
            create_table_filtered(database, user, password, host, port, table_filtered)
        # 存数据
        if True:
            write_bili_dynamics_table(name_id_title_time_text_pics_list)
        # 筛选
        if False:
            filter_data(database, user, password, host, port, table_data, table_tags, table_filtered)
        # 用筛选后的数据生成rss
        if False:
            dic = fetch_all_data(database, user, password, host, port, table_filtered)
            load_rss(dic)
    # name_id_title_time_text_pics_type_list = get_name_id_title_time_text_pics_list(up_uid, user_cookie)
    # write_bili_dynamics_table(name_id_title_time_text_pics_type_list)
    # filter_data(database, user, password, host, port, table_data, table_tags, table_filtered)
    # dict = fetch_all_data(database, user, password, host, port, table_filtered)
    # reload_rss(dict)
    # create_bili_dynamics_table_data(database, user, password, host, port,table_data)
    # create_bili_dynamics_table_tags(database, user, password, host, port,table_tags)
    # create_table_filtered(database, user, password, host, port, table_filtered)
    # clean_table(database, user, password, host, port,table)
