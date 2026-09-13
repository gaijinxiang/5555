#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, json, base64
from urllib.parse import quote
import requests
from base.spider import Spider


class Spider(Spider):

    HOST = "https://www.bibi01.cc"

    CATEGORIES = [
        ("dianyingad", "电影"), ("dianshig", "电视剧"), ("zongyig", "综艺"),
        ("dongmang", "动漫"), ("juchangg", "AI剧场"), ("duanjug", "短剧"),
        ("yingshih", "影视解说"),
    ]

    SUB_CATEGORIES = {
        "dianyingad": [("动作片", "dianyingad/dongzuog"), ("喜剧片", "dianyingad/xijug"),
                       ("爱情片", "dianyingad/aiqingg"), ("科幻片", "dianyingad/kehuang"),
                       ("恐怖片", "dianyingad/kongbug"), ("剧情片", "dianyingad/juqingq"),
                       ("战争片", "dianyingad/zhanzhengg"), ("悬疑片", "dianyingad/xuanyig"),
                       ("犯罪片", "dianyingad/fanzuig"), ("惊悚片", "dianyingad/jingsongg"),
                       ("奇幻片", "dianyingad/qihuang"), ("冒险片", "dianyingad/maoxiang"),
                       ("灾难片", "dianyingad/zainang"), ("武侠片", "dianyingad/wuxiag"),
                       ("古装片", "dianyingad/guzhuangn"), ("动画电影", "dianyingad/donghuan"),
                       ("动画片", "dianyingad/donghuao"), ("纪录片", "dianyingad/jilug"),
                       ("短片", "dianyingad/duanpiang"), ("西部片", "dianyingad/xibug"),
                       ("历史片", "dianyingad/lishig"), ("家庭片", "dianyingad/jiatingg"),
                       ("邵氏电影", "dianyingad/shaoshig"), ("4K电影", "dianyingad/dianyingae"),
                       ("Netflix电影", "dianyingad/dianyingaf"), ("伦理片", "dianyingad/lunlin")],
        "dianshig": [("国产剧", "dianshig/guochann"), ("香港剧", "dianshig/xianggangg"),
                     ("台湾剧", "dianshig/taiwang"), ("韩国剧", "dianshig/hanguoo"),
                     ("日本剧", "dianshig/ribenv"), ("欧美剧", "dianshig/oumeiu"),
                     ("泰国剧", "dianshig/taiguog"), ("海外剧", "dianshig/haiwain"),
                     ("Netflix自制剧", "dianshig/zizhig")],
        "zongyig": [("大陆综艺", "zongyig/dalug"), ("港台综艺", "zongyig/gangtaiv"),
                    ("日韩综艺", "zongyig/rihang"), ("欧美综艺", "zongyig/oumeiv")],
        "dongmang": [("国产动漫", "dongmang/guochano"), ("日本动漫", "dongmang/ribenw"),
                     ("欧美动漫", "dongmang/oumeiw"), ("港台动漫", "dongmang/gangtaiw"),
                     ("海外动漫", "dongmang/haiwaio"), ("里番动漫", "dongmang/lifang")],
        "juchangg": [("有声动漫", "juchangg/youshengg"), ("漫剧", "juchangg/manjun"),
                     ("AI漫剧", "juchangg/manjuo")],
        "duanjug": [("现代都市", "duanjug/xiandaig"), ("女频恋爱", "duanjug/nvping"),
                    ("反转爽剧", "duanjug/fanzhuang"), ("古装仙侠", "duanjug/guzhuango"),
                    ("年代穿越", "duanjug/niandaig"), ("脑洞悬疑", "duanjug/naodongg"),
                    ("成长逆袭", "duanjug/chengzhangh"), ("战神", "duanjug/zhanshenh"),
                    ("豪门", "duanjug/haomenh"), ("擦边短剧", "duanjug/cabianh")],
        "yingshih": [("电影解说", "yingshih/dianyingag"), ("预告解说", "yingshih/yugaor"),
                     ("预告片", "yingshih/yugaos"), ("剧情介绍", "yingshih/juqingr")],
    }

    def _build_filters(self):
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2025, 2015, -1)]
        langs = [{"n": "全部", "v": ""}, {"n": "英语", "v": "英语"}, {"n": "汉语普通话", "v": "汉语普通话"},
                 {"n": "日语", "v": "日语"}, {"n": "韩语", "v": "韩语"}, {"n": "粤语", "v": "粤语"},
                 {"n": "国语", "v": "国语"}, {"n": "普通话", "v": "普通话"}, {"n": "法语", "v": "法语"},
                 {"n": "西班牙语", "v": "西班牙语"}, {"n": "德语", "v": "德语"}]
        filters = {}
        for tid, subs in self.SUB_CATEGORIES.items():
            rows = [{"n": "全部", "v": tid}] + [{"n": n, "v": sub} for n, sub in subs]
            filters[tid] = [{"key": "type_id", "name": "类型", "value": rows},
                            {"key": "year", "name": "年代", "value": years},
                            {"key": "lang", "name": "语言", "value": langs}]
        return filters

    def getName(self):
        return "松果"

    def init(self, extend=""):
        self.host = self.HOST
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def isVideoFormat(self, url):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _get(self, url):
        for _ in range(2):
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    return r.text
            except Exception as e:
                print("[%s] 请求失败: %s %s" % (self.getName(), url[:60], e))
        return ""

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.host + u
        return u

    def homeContent(self, filter):
        return {"class": [
            {"type_id": tid, "type_name": name} for tid, name in self.CATEGORIES
        ], "filters": self._build_filters()}

    def homeVideoContent(self):
        try:
            html = self._get(self.host + "/")
            lst = []
            seen = set()
            for m in re.finditer(
                    r'<a[^>]*href="(/film/1sg[a-z0-9]+\.html)"[^>]*>\s*<img[^>]*data-cover-src="([^"]+)"[^>]*alt="([^"]+)"',
                    html):
                vid, pic, name = m.group(1), m.group(2), m.group(3)
                key = vid
                if key in seen:
                    continue
                seen.add(key)
                lst.append({"vod_id": vid, "vod_name": name, "vod_pic": self._fix(pic), "vod_remarks": ""})
                if len(lst) >= 20:
                    break
            print("[%s] 首页推荐 %d 条" % (self.getName(), len(lst)))
            return {"list": lst}
        except Exception as e:
            print("[%s] 错误: 首页推荐失败 - %s" % (self.getName(), e))
            return {"list": []}

    def _parse_cards(self, html):
        lst = []
        seen = set()
        for m in re.finditer(
                r'<article class="wu-poster-card"[^>]*>.*?href="(/film/1sg[a-z0-9]+\.html)".*?data-cover-src="([^"]+)"[^>]*alt="([^"]+)".*?<h3><a[^>]*>([^<]+)</a></h3>.*?<small>([^<]*)</small>\s*</article>',
                html, re.S):
            vid, pic, alt, name, year = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5).strip()
            if vid in seen:
                continue
            seen.add(vid)
            lst.append({"vod_id": vid, "vod_name": name, "vod_pic": self._fix(pic), "vod_remarks": year})
        if not lst:
            for m in re.finditer(
                    r'<article class="wu-poster-card"[^>]*>(.*?)</article>', html, re.S):
                b = m.group(1)
                am = re.search(r'href="(/film/1sg[a-z0-9]+\.html)"', b)
                if not am or am.group(1) in seen:
                    continue
                seen.add(am.group(1))
                pm = re.search(r'data-cover-src="([^"]+)"', b)
                nm = re.search(r'<h3><a[^>]*>([^<]+)</a>', b)
                ym = re.search(r'<small>([^<]*)</small>', b)
                lst.append({"vod_id": am.group(1), "vod_name": nm.group(1) if nm else "",
                            "vod_pic": self._fix(pm.group(1)) if pm else "",
                            "vod_remarks": ym.group(1).strip() if ym else ""})
        return lst

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        try:
            route = tid
            qs = []
            if extend and isinstance(extend, dict):
                route = str(extend.get("type_id") or tid)
                if extend.get("year"):
                    qs.append("year=%s" % extend["year"])
                if extend.get("lang"):
                    qs.append("lang=%s" % quote(str(extend["lang"])))
            url = "%s/film/%s" % (self.host, route)
            if pg > 1:
                qs.append("page=%d" % pg)
            if qs:
                url += "?" + "&".join(qs)
            html = self._get(url)
            lst = self._parse_cards(html)
            m = re.search(r'class="disabled" href="">上一页</a>', html)
            pagecount = pg + (1 if lst else 0)
            pm = re.search(r'href="%s\?page=(\d+)"[^>]*>尾页' % re.escape(url.split('?')[0]), html)
            if not pm:
                pages = re.findall(r'\?page=(\d+)"', html)
                if pages:
                    pagecount = max(int(x) for x in pages)
            print("[%s] 分类 %s 第%d页: %d 条" % (self.getName(), route, pg, len(lst)))
            return {"list": lst, "page": pg, "pagecount": pagecount, "limit": 34, "total": pagecount * 34}
        except Exception as e:
            print("[%s] 错误: 分类爬取失败 - %s" % (self.getName(), e))
            return {"list": [], "page": pg, "pagecount": 1, "limit": 34, "total": 0}

    def detailContent(self, ids):
        try:
            vid = ids[0]
            html = self._get("%s/%s" % (self.host, vid))
            nm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            name = nm.group(1).strip() if nm else ""
            pm = re.search(r'data-cover-src="([^"]+)"', html)
            pic = self._fix(pm.group(1)) if pm else ""
            year = ""
            ym = re.search(r'itemprop=\"uploadDate\" content=\"((19|20)\d{2})', html)
            if not ym:
                i1 = html.find('<h1')
                ym = re.search(r'((19|20)\d{2})', html[i1:i1 + 600]) if i1 >= 0 else None
            if ym:
                year = ym.group(1)
            dm = re.search(r'<p>导演：([^<]+)</p>', html)
            actor = re.search(r'<p>演员：([^<]+)</p>', html)
            cm = re.search(r'内容简介</h2></div>\s*<p>(.*?)</p>', html, re.S)
            content = cm.group(1).strip() if cm else ""
            eps_a, eps_b = [], []
            seen_ep = set()
            for em in re.finditer(r'<a[^>]*href="(/play/1sg[a-z0-9]+-[a-z0-9]+\.html)"[^>]*>([^<]{1,30})</a>', html):
                purl, epname = em.group(1), em.group(2).strip()
                if purl in seen_ep:
                    continue
                seen_ep.add(purl)
                eps_a.append("%s$%s@@jsm3u8" % (epname, purl))
                eps_b.append("%s$%s@@local" % (epname, purl))
            if not eps_a:
                play_from = ""
                play_url = ""
            else:
                play_from = "线路A$$$线路B"
                play_url = "#".join(eps_a) + "$$$" + "#".join(eps_b)
            print("[%s] 详情 %s: A%d集/B%d集" % (self.getName(), vid, len(eps_a), len(eps_b)))
            vod = {
                "vod_id": vid, "vod_name": name, "vod_pic": pic,
                "type_name": "", "vod_year": year,
                "vod_area": "", "vod_actor": actor.group(1).strip() if actor else "",
                "vod_director": dm.group(1).strip() if dm else "",
                "vod_content": content, "vod_remarks": "",
                "vod_play_from": play_from, "vod_play_url": play_url,
            }
            return {"list": [vod]}
        except Exception as e:
            print("[%s] 错误: 详情解析失败 - %s" % (self.getName(), e))
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1
        try:
            from urllib.parse import quote
            url = "%s/film/search=%s" % (self.host, quote(key))
            if pg > 1:
                url += "?page=%d" % pg
            html = self._get(url)
            lst = self._parse_cards(html)
            print("[%s] 搜索 '%s' 第%d页: %d 条" % (self.getName(), key, pg, len(lst)))
            return {"list": lst, "page": pg, "pagecount": pg + (1 if len(lst) >= 30 else 0), "limit": 30, "total": len(lst)}
        except Exception as e:
            print("[%s] 错误: 搜索失败 - %s" % (self.getName(), e))
            return {"list": [], "page": pg, "pagecount": 1, "limit": 30, "total": 0}

    def playerContent(self, flag, pid, vipFlags):
        try:
            pid = str(pid)
            if "@@" in pid:
                purl, code = pid.split("@@", 1)
            else:
                purl, code = pid, ""
            if not purl.startswith("http"):
                html = self._get(self.host + purl)
                real = ""
                btns = re.findall(r'<button[^>]*data-player-switch[^>]*>', html)
                for b in btns:
                    cm = re.search(r'data-player-code="([^"]+)"', b)
                    tm = re.search(r'data-player-token="([^"]+)"', b)
                    if cm and tm and (not code or cm.group(1) == code):
                        try:
                            real = base64.b64decode(tm.group(1)).decode("utf-8", "ignore")
                            break
                        except Exception:
                            pass
                if not real and btns:
                    tm = re.search(r'data-player-token="([^"]+)"', btns[0])
                    if tm:
                        try:
                            real = base64.b64decode(tm.group(1)).decode("utf-8", "ignore")
                        except Exception:
                            real = ""
                if not real:
                    rm = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html)
                    if rm:
                        real = rm.group(1)
                print("[%s] 播放解析: %s [%s] -> %s" % (self.getName(), purl, code, real[:60]))
            else:
                real = purl
            header = {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"}
            return {"parse": 0, "playUrl": "", "url": real, "header": json.dumps(header)}
        except Exception as e:
            print("[%s] 错误: 播放解析失败 - %s" % (self.getName(), e))
            return {"parse": 0, "playUrl": "", "url": "", "header": ""}
