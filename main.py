from bili_requests_functions import *
import os

if __name__ == '__main__':
    # up_uid = os.environ.get('UP_UID')
    # user_cookie = os.environ.get('USER_COOKIE')
    #
    # if not up_uid:
    #     raise ValueError("UP_UID 环境变量未设置")
    # if not user_cookie:
    #     raise ValueError("USER_COOKIE 环境变量未设置")

    up_uid='108919422'
    user_cookie="buvid3=285ADB51-97F2-B63C-7F72-D16A756FBE3E16395infoc; b_nut=1740126116; _uuid=55CDAAA2-3CEE-A666-7942-7A85BB610EE6D23000infoc; enable_web_push=DISABLE; enable_feed_channel=ENABLE; home_feed_column=5; browser_resolution=1655-979; buvid4=EE80E339-C0FA-5EBE-A5F7-570E11CB4B0116972-025022108-Azs0hNockNm%2BtYmGHF5HMg%3D%3D; buvid_fp=0e6ee00f0d9ee5987c15973ffb9cce04; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDIwNDg3MjcsImlhdCI6MTc0MTc4OTQ2NywicGx0IjotMX0.NMHnq6PWgJ713_9zHeboy5nDKO7xDoC17UzdLNlX3cs; bili_ticket_expires=1742048667; header_theme_version=CLOSE; bp_t_offset_531140325=1043777155730767872; CURRENT_FNVAL=16; rpdid=|(JY~|J)|J~R0J'u~R|umYlYY; fingerprint=0e6ee00f0d9ee5987c15973ffb9cce04; buvid_fp_plain=undefined; CURRENT_QUALITY=120; PVID=3; LIVE_BUVID=AUTO5817406608563424; hit-dyn-v2=1; SESSDATA=c89efa97%2C1757327186%2C2aa96%2A32CjCpWs8aFtXARSQCCLhT_jaMFZxXZo1IrI1RIab2xqm5h6sEZcSeaCPIP-PwZzwelvESVjBhVGtNRzJEaVB0OEl0ekNLMVNwT3EwaDQyZ3prM0dCcjE2OVR3WURVRTB1SzZhd242eUhQemNjQTNxbXUweE9iZTF3cWJqdEEwdlA1RGdqeTdnS3FRIIEC; bili_jct=65215689e8b17793cafe3f80ddb23362; DedeUserID=531140325; DedeUserID__ckMd5=9480e1630b93a4f3; opus-goback=1; b_lsid=102BB994D_1958F5E0CF3; sid=4lofzu1i"
    # 以上传参
    id_title_time_text_pics_list = get_id_title_time_text_pics_list(up_uid, user_cookie)
    load_rss(id_title_time_text_pics_list, up_uid)
