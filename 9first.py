#!/usr/bin/python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import sys
import io,os
import json
import threading
import time
import re
from os.path import join, getsize
from contextlib import closing 
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, errors = 'replace', line_buffering = True)





def read_json(title):
    save_path = os.path.join(sys.path[0], title + '.json')
    if title + '.json' in [x for x in os.listdir('.')]:
        with open(save_path ,'r') as f : 
            j = json.load(f)
    else:
        j = {}
    return j
    
def savejson(title, json_dict):
    rstr = r"[\/\n\\\:\*\?\"\<\>\|]"  # '/\:*?"<>|'
    title = re.sub(rstr, "", title) 
    save_path = os.path.join(sys.path[0], title + '.json')
    with open(save_path , mode = 'w') as f : 
        json.dump(json_dict,f, ensure_ascii = False ,indent=2)              
            

def mkdir(path):
    # 引入模块
    import os
 
    # 去除首位空格
    path=path.strip()
    # 去除尾部 \ 符号
    path=path.rstrip("\\")
 
    # 判断路径是否存在
    # 存在     True
    # 不存在   False
    isExists=os.path.exists(path)
 
    # 判断结果
    if not isExists:
        # 如果不存在则创建目录
        #print (path+' 创建成功')
        # 创建目录操作函数
        os.makedirs(path)
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        #print (path+' 目录已存在')
        return False

        
        
class ProgressBar(object):

    def __init__(self, title,
                 index,
                 count=0.0,
                 run_status=None,
                 fin_status=None,
                 total=100.0,
                 unit='', sep='/',
                 chunk_size=1.0):
        super(ProgressBar, self).__init__()
        self.info = "%s.【%s】%s %.2f %s %s %.2f %s (%.2f%%)"
        self.title = title
        self.index = index
        self.total = total
        self.count = count
        self.chunk_size = chunk_size
        self.status = run_status or ""
        self.fin_status = fin_status or " " * len(self.status)
        self.unit = unit
        self.seq = sep

    def __get_info(self):
        # 【名称】状态 进度 单位 分割线 总数 单位
        _info = self.info % (self.index, self.title, self.status,
                             (self.count/self.chunk_size)/1024, self.unit, self.seq, (self.total/self.chunk_size)/1024,
                            self.unit, (self.count/self.chunk_size)/(self.total/self.chunk_size)*100)
        return _info

    def refresh(self, count=1, status=None):
        self.count += count
        # if status is not None:
        self.status = status or self.status
        end_str = "\r"
        if self.count >= self.total:
            end_str = '\n'
            self.status = status or self.fin_status
        print(self.__get_info(), end = end_str)


class _9First:
    def __init__(self, username, password, cert_id):
        self.username = username
        self.password = password
        self.s = requests.Session()
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.152 Safari/537.36"}
        self.s.headers = self.headers
        self.cert_id = cert_id
    def load(self):
        payload = {"return_type":"SCRIPT",
            "encoding":"utf-8",
            "callback":"sso.login_callback",
            "username":self.username,
            "password":self.password,
            "_":int(time.time()*1000)}
        self.s.get("http://home.9first.com/user/login")
        self.s.cookies.update({"_ga" : "GA1.2.1984221365.1473415291", "_gat" : "1"})
        self.s.post("http://home.9first.com/user/getValidTicket",data = {"username":self.username})
        self.headers.update({"Referer":"http://home.9first.com/user/login"})
        g = requests.get("http://sso.veryeast.cn/user/login",allow_redirects=False, params = payload, headers = self.headers)
        next_url = g.headers["location"]
        g = self.s.get(next_url)
        the_string = g.text
        start_index = the_string.find("ticket")
        oave_index = the_string.find(",",start_index)
        ticket = the_string[start_index+8:oave_index].replace('"',"")
        p = self.s.post("http://home.9first.com/user/saveticket", data = {"ticket":ticket})
        g = self.s.get("http://home.9first.com/ihma/index")
        if "我的课程" in g.text:
            print("登陆成功")
        else:
            print("登陆失败")
    
    #读取课程列表
    def read_course_list(self):
        global course_json_list
        n = 0
        course_list = {}
        self.s.get("http://home.9first.com/ihma/cert?id=24&tabIndex=0")
        payload = {"id":self.cert_id,
                    "isAjax":1,
                    "_":int(time.time()*1000)}
        
        self.s.cookies.update({"Referer":"http://home.9first.com/ihma/cert?id=24"})
        headers = self.headers.update({"X-Requested-With":"XMLHttpRequest"})
        t = self.s.get("http://home.9first.com/ihma/cert", params = payload, headers = headers)
        course_json_list = t.json()
        for x in course_json_list["data"]["list"]:
            n += 1
            module_name = x["module_name"]
            course_list.update({module_name:{"index":n, "data":[]}})
            for v2 in x["list"]:
                cid = v2["cid"]
                course_type = v2["course_type"]
                lecture_name = v2["lecture_name"]
                title = v2["title"]
                url = "http://home.9first.com/school/courseDetail?course_id=%s&cert_id=%s&type=%s" %(cid, self.cert_id, course_type)
                course_list[module_name]["data"].append({"cid":cid,
                                    "title":title,
                                    "course_type":course_type,
                                    "lecture_name":lecture_name,
                                    "url":url})
                                    
        #print(course_list)
        return course_list
        
    def read_video_url(self, course_list):
        video_url_list = []
        def find_video_id(id):
            data = {"lecture_id":id,
                    "action":"current"}
            headers = self.headers.update({"X-Requested-With":"XMLHttpRequest"})
            t = self.s.post("http://home.9first.com/api/study/changeLecture", data = data, headers = headers).json()
            video_url = t["data"]["hd_mp4_url"]
            introduce = t["data"]["introduce"]
            return video_url, introduce
        
        for k, v in course_list.copy().items():
            global t,video_list,y
            module_name = k
            module_index = v["index"]
            n = 0
            m = 0
            for y in v["data"]:
                n += 1
                title_index = n
                cid = y["cid"]
                course_type = y["course_type"]
                lecture_name = y["lecture_name"] #课程类别
                title = y["title"]    #课程名
                url = y["url"]
                course_list[k]["data"][n-1].update({"chapter":[]})
                t = self.s.get(url)
                soup = BeautifulSoup(t.content)
                href = soup.find("a",text = "课前自评", href = True)["href"].replace("step1", "step2")
                href = "http://home.9first.com%s" %href
                t = self.s.get(href)
                soup = BeautifulSoup(t.content)
                
                for x in soup.find("ul", id = True)("li", id = True):
                    m += 1
                    chapter = x.b.string  #章节名
                    print(chapter)
                    sub_catalog_list = []
                    for y in x.ul("li"):
                        sub_catalog = y.a.string #小节名
                        video_id = y.a["id"].replace("i_", "") #小节id
                        video_url, introduce = find_video_id(video_id)
                        sub_catalog_list.append({"sub_catalog":sub_catalog, "video_id":video_id, "video_url":video_url, "introduce":introduce})
                        print(sub_catalog, video_id)
                        video_url_dict = {"url":video_url, "sub_catalog":sub_catalog, "chapter":chapter, "title":title, "lecture_name":lecture_name, "module_name":module_name, "title_index":title_index, "module_index":module_index}
                        video_url_list.append(video_url_dict)
                    course_list[k]["data"][n-1]["chapter"].append({"chapter_name":chapter, "sub_catalog":sub_catalog_list})
        #print(course_list)
        savejson("9first",course_list)
        return course_list,video_url_list

    def download(self, url, path, video_name, index, headers = {}):
        total = 0
        finished = False
        def touch(filename):
            with open(filename, 'w') as fin:
                pass

        def remove_nonchars(name):
            (name, _) = re.subn(r'[\\\/\:\*\?\"\<\>\|]', '', name)
            name = name.replace("\t"," ")
            return name
        
        def support_continue(url):
            headers = {
                'Range': 'bytes=0-4'
            }
            try:
                r = self.s.head(url, headers = headers)
                crange = r.headers['content-range']
                total = int(re.match(r'^bytes 0-4/(\d+)$', crange).group(1))
                #total = int(r.headers['content-length'])
                return total
            except:
                pass
            try:
                total = int(r.headers['content-length'])
            except:
                total = 0
            return False
        self.size = 0
        video_name = remove_nonchars(video_name)
        local_filename = os.path.join(path, video_name)
        tmp_filename = local_filename + '.downtmp'
        size = self.size
        if support_continue(url):  # 支持断点续传
            total = support_continue(url) 
            if os.path.isfile(local_filename):
                local_filename_size = getsize(local_filename)
                if total == local_filename_size and total > 1:
                    print("%s 任务已下载完毕，跳过" %video_name)
                    index -= 1
                    return
                else:
                    #print("任务已经存在 %s" %video_name)
                    try:
                        with open(tmp_filename, 'rb') as fin:
                            self.size = int(fin.read().decode())
                            if local_filename_size < self.size -1:
                                print(local_filename_size,self.size)
                                print("文件长度跟记录不一致，采用文件长度")
                                self.size = local_filename_size
                            elif local_filename_size > total:
                                self.size = 0
                                print("本地文件文件长度异常，重新下载")
                                
                            size = self.size + 1
                            #print(size)
                            print("成功获取进度，继续下载 %s %.2f%%" %(video_name, (size/total)*100))
                    except:
                        #raise
                        touch(tmp_filename)
                    finally:
                        headers['Range'] = "bytes=%d-%s" % (self.size, total)
                        #print(headers)
        else:
            touch(tmp_filename)
            touch(local_filename)   
        
        with closing(self.s.get(url, stream=True, headers = headers)) as response:
            chunk_size = 1024 # 单次请求最大值
            if total != 0:
                content_size = total
            else:
                content_size = int(response.headers['content-length']) # 内容体总大小
            if "video/mp4" not in response.headers["Content-Type"]:
                print("资源类型不符，跳过")
                return
            nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            progress = ProgressBar(video_name, index, count = self.size, total=content_size,
                                 unit="MB", chunk_size=chunk_size, run_status="正在下载", fin_status="下载完成 (%s)" %nowtime)
            try:
                with open(local_filename, "ab+") as file:
                    file.seek(self.size)
                    file.truncate()
                    for data in response.iter_content(chunk_size=chunk_size):
                       file.write(data)
                       size += len(data)
                       file.flush()
                       progress.refresh(count=len(data))
                       with open(tmp_filename, 'wb') as ftmp:
                           ftmp.write(str(size).encode())
                finished = True
                os.remove(tmp_filename)
            except:
                print( "\nDownload pause.\n")
            finally:
                if not finished:
                    with open(tmp_filename, 'wb') as ftmp:
                        ftmp.write(str(size).encode())
                        print("成功保存进度")
                        
    def download_video(self, video_url_list):
        
        def download(url, path, video_name, index):
            #video_name = "%s. %s" %(index, video_name)
            filename = os.path.join(path, video_name)
            with closing(self.s.get(url, stream=True)) as response:
                chunk_size = 1024 # 单次请求最大值
                content_size = int(response.headers['content-length']) # 内容体总大小
                nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                progress = ProgressBar(video_name, index, total=content_size,
                                     unit="MB", chunk_size=chunk_size, run_status="正在下载", fin_status="下载完成 (%s)" %nowtime)
                with open(filename, "wb") as file:
                    for data in response.iter_content(chunk_size=chunk_size):
                       file.write(data)
                       progress.refresh(count=len(data))
        
        n = 1
        for x in video_url_list:
            url = x["url"]
            sub_catalog = x["sub_catalog"]
            chapter = x["chapter"]
            title = x["title"]
            lecture_name = x["lecture_name"]
            module_name = x["module_name"]
            title_index = x["title_index"]
            module_index = x["module_index"]
            video_path = os.path.join(sys.path[0], "9first_class", str(module_index) + "." + module_name, str(title_index) + "." + title + "【" + lecture_name + "】", chapter)
            mkdir(video_path)
            video_name = sub_catalog + ".mp4"
            self.download(url, video_path, video_name, n)
            n += 1
        
    def json_to_video_url_list(self, json_file):
        dict_file = read_json(json_file) 
        video_url_list = []
        for k,v in dict_file.items():
            n = 0
            module_name = k
            module_index = v["index"]
            for y in v["data"]:
                n += 1
                title_index = n
                lecture_name = y["lecture_name"] #课程类别
                title = y["title"]    #课程名
                url = y["url"]    
                for x in y["chapter"]:
                    chapter = x["chapter_name"]
                    for z in x["sub_catalog"]:
                        sub_catalog = z["sub_catalog"]
                        video_url = z["video_url"]
                        video_url_dict = {"url":video_url, "sub_catalog":sub_catalog, "chapter":chapter, "title":title, "lecture_name":lecture_name, "module_name":module_name, "title_index":title_index, "module_index":module_index}
                        video_url_list.append(video_url_dict)
        return video_url_list
    def auto_download(self, is_read_json):
        if is_read_json == "N":
            video_url_list = self.json_to_video_url_list("9first")
        else:
            course_list = self.read_course_list()
            course_list,video_url_list = self.read_video_url(course_list)
        self.download_video(video_url_list)

i = input("是否重新读取视频列表(Y/N)？ ")
if i == "":
    i = "N"        


while 1: 
    try:
        _9first = _9First(username = "",password = "", cert_id = 0)
        _9first.load()
        _9first.auto_download(i)
    except Exception as e:
        print(e)
        pass