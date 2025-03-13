from bili_requests_functions import *
import os

if __name__ == '__main__':
    up_uid = os.environ.get('UP_UID')
    user_cookie = os.environ.get('USER_COOKIE')

    if not up_uid:
        raise ValueError("UP_UID 环境变量未设置")
    if not user_cookie:
        raise ValueError("USER_COOKIE 环境变量未设置")

    # 以上传参
    id_title_time_text_pics_list = get_id_title_time_text_pics_list(up_uid, user_cookie)
    load_rss(id_title_time_text_pics_list, up_uid)
