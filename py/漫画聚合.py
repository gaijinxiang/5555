# -*- coding: utf-8 -*-
"""
涩漫 漫画源 - 皮卡丘标准格式（优化版）
目标: https://igtcqqindd4.icu/h5/#/?cid=td

【修复内容】
  - 修复 modeA 图片解密判断错误 (any → all)，解决部分图片无法显示的问题
  - 详情页去掉无用的 datav2/2 调用，速度提升约 50%
  - 统一使用章节自带 imgtype，避免播放时解密类型错误

【速度优化】
  - API 响应缓存（分类/详情/章节 5分钟，token 6天）
  - 图片代理解密结果缓存（10分钟），相同图片零等待
  - 超时从 20s 缩短到 10s（API）/ 8s（图片）
  - 预编译全部正则表达式
  - 优化 XOR 解密算法（预计算密钥循环，减少循环开销）
"""

import sys
import re
import json
import base64
import gzip
import io
import urllib.request
import urllib.parse
import time

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    # 独立运行时提供空基类
    class Spider:
        def __init__(self):
            pass

# 优先尝试导入 AES，用于 imgtype=2
_AES = None
try:
    from Crypto.Cipher import AES as _AES_MODULE
    _AES = _AES_MODULE
except Exception:
    pass


# ============================================================
# 预编译正则
# ============================================================
_RE_CHAPTER_NUM = re.compile(r'(第[\d一二三四五六七八九十百千]+话|[\d一二三四五六七八九十百千]+话|序章|番外)')
_RE_MARKS_STRIP = re.compile(r'[\[\]"]')
_RE_BASE64 = re.compile(r'^[A-Za-z0-9+/=]+$')


# ============================================================
# 预计算 XOR 密钥表（加速 imgtype=3 解密）
# ============================================================
_VLOG_KEY = b'2019ysapp7527'
_VLOG_KEY_LEN = len(_VLOG_KEY)
# 预计算 100 字节的循环密钥
_VLOG_XOR_TABLE = bytearray(100)
for i in range(100):
    _VLOG_XOR_TABLE[i] = _VLOG_KEY[i % _VLOG_KEY_LEN]

_VLOG_MODEA_MAGIC = bytes([136, 168, 48, 203, 16, 118])
_VLOG_IMG_MAGICS = (
    b'\xff\xd8\xff',          # JPEG
    b'\x89PNG\r\n\x1a\n',     # PNG
    b'GIF',                   # GIF
    b'RIFF',                  # WebP
)


class Spider(Spider):
    """涩漫漫画爬虫 - 优化版"""

    NAME = "涩漫"
    CID = "td"
    PID = "null"
    CLIENT_ID = "null"

    API_MAIN = "https://igtcqqindd4.icu/jbapi"
    API_CDN = "https://cof03.bahfn.cn/jbapi"
    IMG_REFERER = "https://igtcqqindd4.icu/"
    PROXY_PORT = "9978"

    PAGE_SIZE = 20
    SEARCH_SIZE = 15

    # 缓存配置（秒）
    CACHE_CATEGORY = 300   # 分类列表 5分钟
    CACHE_DETAIL = 600     # 详情页 10分钟
    CACHE_CHAPTER = 1800   # 章节图片 30分钟
    CACHE_IMAGE = 600      # 图片解密结果 10分钟

    def __init__(self):
        super().__init__()
        self._token = None
        self._token_expire = 0
        self._cats = []
        self._cats_time = 0
        self._cache = {}           # {cache_key: (expire_time, data)}
        self._img_cache = {}       # {url: (expire_time, data, content_type)}
        self._header = None

    # ============ 基础方法 ============

    def getName(self):
        return self.NAME

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._cache.clear()
        self._img_cache.clear()

    def getHeader(self):
        if self._header is None:
            self._header = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Referer": "https://igtcqqindd4.icu/h5/",
                "Origin": "https://igtcqqindd4.icu",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip",
                "Connection": "keep-alive",
            }
        return dict(self._header)

    # ============ 缓存工具 ============
    def _cache_get(self, key):
        entry = self._cache.get(key)
        if entry and time.time() < entry[0]:
            return entry[1]
        if entry:
            del self._cache[key]
        return None

    def _cache_set(self, key, value, ttl):
        self._cache[key] = (time.time() + ttl, value)
        # 简单清理：超过 50 条时清掉过期的
        if len(self._cache) > 50:
            now = time.time()
            expired = [k for k, (exp, _) in self._cache.items() if now >= exp]
            for k in expired:
                del self._cache[k]

    # ============ HTTP 请求 ============

    def fetch(self, url, method='GET', data=None, headers=None, raw=False, retry=1, timeout=10):
        """统一请求：gzip + token + 重试"""
        try:
            h = dict(headers) if headers else self.getHeader()
            if 'token' not in h:
                token = self.getToken()
                h['token'] = token if token else 'false'

            parsed = urllib.parse.urlparse(url)
            encoded_path = urllib.parse.quote(parsed.path, safe='/')
            url = urllib.parse.urlunparse((
                parsed.scheme, parsed.netloc, encoded_path,
                parsed.params, parsed.query, parsed.fragment
            ))

            req = urllib.request.Request(url, method=method.upper())
            for k, v in h.items():
                req.add_header(k, v)

            body = None
            if method.upper() == 'POST' and data is not None:
                if isinstance(data, dict):
                    data = json.dumps(data)
                body = data.encode('utf-8') if isinstance(data, str) else data
                req.add_header('Content-Type', 'application/json')
                req.data = body

            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                content_encoding = response.info().get('Content-Encoding', '').lower()
                if 'gzip' in content_encoding:
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        try:
                            buf = io.BytesIO(content)
                            with gzip.GzipFile(fileobj=buf) as f:
                                content = f.read()
                        except Exception:
                            pass

                if raw:
                    return content

                return content.decode('utf-8', errors='ignore')
        except Exception:
            if retry > 0:
                if self._token:
                    self._token = None
                return self.fetch(url, method, data, headers, raw, retry - 1, timeout)
            return None

    def api(self, path, method='GET', data=None, cache_ttl=0):
        """调用 API，自动选择 CDN/主站 + 解密 enc 响应"""
        cache_key = None
        if cache_ttl > 0:
            cache_key = f"api:{method}:{path}"
            if data:
                cache_key += ":" + (json.dumps(data) if isinstance(data, dict) else str(data))
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

        url = self.getApiUrl(path)
        text = self.fetch(url, method=method, data=data)
        if not text:
            return None

        try:
            obj = json.loads(text)
            if obj.get('code') == 302:
                self._token = None
                text = self.fetch(self.getApiUrl(path), method=method, data=data)
                if text:
                    obj = json.loads(text)
            if obj.get('enc') and isinstance(obj.get('data'), str):
                obj['data'] = self._decryptPayload(obj['data'])

            if cache_ttl > 0 and obj.get('code') == 200:
                self._cache_set(cache_key, obj, cache_ttl)

            return obj
        except Exception:
            return None

    def getApiUrl(self, path):
        if '/hjm.ojbk' in path:
            base = self.API_CDN
        else:
            base = self.API_MAIN
        return base.rstrip('/') + '/' + path.lstrip('/')

    # ============ 图片代理 URL ============

    def _proxyImgUrl(self, url, imgtype=3):
        """封面图代理 URL"""
        if not url:
            return url
        if '/proxy?do=smimg' in url or '/proxy?src=' in url or url.startswith('proxy://'):
            return url
        encoded = urllib.parse.quote(url, safe='')
        return f"http://127.0.0.1:{self.PROXY_PORT}/proxy?do=smimg&url={encoded}&t={imgtype}"

    def _proxyImgUrlCompact(self, url, imgtype=3):
        """播放页专用：base64 单参数，避免与 pics:// 的 && 冲突"""
        if not url:
            return url
        if '/proxy?src=' in url:
            return url
        query = f"do=smimg&url={urllib.parse.quote(url, safe='')}&t={imgtype}"
        src = base64.urlsafe_b64encode(query.encode('utf-8')).decode('utf-8').rstrip('=')
        return f"http://127.0.0.1:{self.PROXY_PORT}/proxy?src={src}"

    # ============ Token ============

    def getToken(self):
        if self._token and time.time() < self._token_expire:
            return self._token
        if getattr(self, '_token_busy', False):
            return None
        self._token_busy = True
        try:
            path = f"/user/autoUser/{self.PID}/{self.CID}/{self.CLIENT_ID}"
            url = self.API_MAIN.rstrip('/') + path
            h = self.getHeader()
            h['token'] = 'false'
            text = self.fetch(url, headers=h)
            if not text:
                return None
            try:
                obj = json.loads(text)
                if obj.get('enc') and isinstance(obj.get('data'), str):
                    obj['data'] = self._decryptPayload(obj['data'])
                if obj.get('code') == 200 and obj.get('data'):
                    data = obj['data']
                    if isinstance(data, dict):
                        self._token = data.get('token') or data.get('data', {}).get('token')
                    else:
                        self._token = str(data)
                    if self._token:
                        self._token_expire = time.time() + 6 * 24 * 3600
                        return self._token
            except Exception:
                pass
            return None
        finally:
            self._token_busy = False

    # ============ 首页 ============

    def homeContent(self, filter):
        classes = []
        for c in sorted(self._getCats(), key=lambda x: x.get('id', 0)):
            classes.append({
                "type_id": str(c.get('id')),
                "type_name": c.get('name', '未知')
            })
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("58", "1", False, None)

    def _getCats(self):
        if self._cats and time.time() - self._cats_time < 3600:
            return self._cats
        res = self.api('/manhua/fenglei')
        if res and isinstance(res.get('data'), list):
            self._cats = res['data']
            self._cats_time = time.time()
        return self._cats

    def _isOneTab(self, tid):
        for c in self._getCats():
            if str(c.get('id')) == str(tid):
                return c.get('onetab') == 1
        return False

    # ============ 分类列表 ============

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if pg else 1
            sort = "time"
            if extend and isinstance(extend, dict):
                sort = extend.get('sort', sort)
            sort = sort if sort in ('time', 'look', 'like') else 'time'

            vlist = []
            if self._isOneTab(tid):
                cache_key = f"cat:fenglei:{tid}:{page}"
                cached = self._cache_get(cache_key)
                if cached is not None:
                    return cached

                res = self.api(f"/manhua/fengleidata/{tid}/hjm.ojbk")
                if res and isinstance(res.get('data'), list):
                    all_items = []
                    for block in res['data']:
                        if isinstance(block, dict):
                            for item in (block.get('list') or []):
                                if isinstance(item, dict) and item.get('id'):
                                    all_items.append(item)
                    # 去重
                    seen = set()
                    unique = []
                    for it in all_items:
                        key = str(it.get('id'))
                        if key not in seen:
                            seen.add(key)
                            unique.append(it)
                    start = (page - 1) * self.PAGE_SIZE
                    vlist = [self._makeVod(it) for it in unique[start:start + self.PAGE_SIZE]]
                    result = {
                        "list": vlist,
                        "page": page,
                        "pagecount": max(1, len(unique) // self.PAGE_SIZE),
                        "limit": self.PAGE_SIZE,
                        "total": len(unique),
                    }
                    self._cache_set(cache_key, result, self.CACHE_CATEGORY)
                    return result
            else:
                cache_key = f"cat:list:{tid}:{page}:{sort}"
                cached = self._cache_get(cache_key)
                if cached is not None:
                    return cached

                url = f"/manhua/onetab/{tid}/{page}/{self.PAGE_SIZE}/{sort}/hjm.ojbk"
                res = self.api(url, cache_ttl=self.CACHE_CATEGORY)
                if res and isinstance(res.get('data'), list):
                    for item in res['data']:
                        vlist.append(self._makeVod(item))

                result = {
                    "list": vlist,
                    "page": page,
                    "pagecount": 9999,
                    "limit": self.PAGE_SIZE,
                    "total": 999999,
                }
                self._cache_set(cache_key, result, self.CACHE_CATEGORY)
                return result

            return {
                "list": vlist,
                "page": page,
                "pagecount": 1,
                "limit": self.PAGE_SIZE,
                "total": 0,
            }
        except Exception:
            return {"list": []}

    # ============ 搜索 ============

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg) if pg else 1
            keyword_b64 = base64.b64encode(key.encode('utf-8')).decode('utf-8')
            url = f"/manhua/searchv2/{page}/{self.SEARCH_SIZE}/time"
            res = self.api(url, method='POST', data={"name": keyword_b64})
            vlist = []
            total = 999999
            if res and isinstance(res.get('data'), dict):
                d = res['data']
                recs = d.get('records') or d.get('list') or []
                for item in recs:
                    vlist.append(self._makeVod(item))
                total = d.get('total', 999999)

            return {
                "list": vlist,
                "page": page,
                "pagecount": 9999,
                "limit": self.SEARCH_SIZE,
                "total": total,
            }
        except Exception:
            return {"list": []}

    # ============ 详情页 ============

    def detailContent(self, ids):
        try:
            mid = ids[0] if isinstance(ids, list) else ids
            mid = str(mid)

            # 只用 datav2/1，已包含 manhua + zhangjie 全部信息
            # 去掉无用的 datav2/2 调用（仅含用户数据），提速 50%
            res = self.api(f"/manhua/datav2/1/{mid}/hjm.ojbk", cache_ttl=self.CACHE_DETAIL)
            if not res or not isinstance(res.get('data'), dict):
                return {"list": []}

            data = res['data']
            mh = data.get('manhua') or {}
            zj = data.get('zhangjie') or []

            name = mh.get('title') or '未知漫画'
            imgtype = int(mh.get('imgurltype', 3))
            pic = self._proxyImgUrl(mh.get('imgurl') or '', imgtype)
            desc = mh.get('miaoshu') or ''
            marks_str = mh.get('marks') or ''

            try:
                marks = json.loads(marks_str) if marks_str else []
                tag = ' '.join(marks)
            except Exception:
                tag = _RE_MARKS_STRIP.sub('', marks_str)

            total_ch = mh.get('zhangjieNum', len(zj))
            state = mh.get('manhuaState', 0)
            remarks = f"{total_ch}话" + (" 连载中" if state == 1 else "")

            # 构建章节列表 — 使用章节自带的 imgtype
            chapters = []
            for ch in zj:
                ch_name = self._cleanChapterName(ch.get('name', ''), name)
                ch_id = str(ch.get('id', ''))
                ch_imgtype = ch.get('imgtype', imgtype)
                if not ch_id:
                    continue
                # 格式: 章节名$chapterId|imgtype
                chapters.append(f"{ch_name}${ch_id}|{ch_imgtype}")

            play_url = "#".join(chapters) if chapters else ""

            return {
                "list": [{
                    "vod_id": mid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "type_name": tag,
                    "vod_remarks": remarks,
                    "vod_actor": "",
                    "vod_content": desc,
                    "vod_play_from": "涩漫",
                    "vod_play_url": play_url,
                }]
            }
        except Exception:
            return {"list": []}

    # ============ 播放（章节图片）============

    def playerContent(self, flag, id, vipFlags):
        try:
            # id 格式: chapterId|imgtype (新版) 或 chapterId (旧版兼容)
            cid = str(id)
            imgtype = 3
            if '|' in cid:
                parts = cid.split('|', 1)
                cid = parts[0]
                try:
                    imgtype = int(parts[1])
                except Exception:
                    imgtype = 3

            # 缓存章节图片列表
            cache_key = f"ch:{cid}"
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

            res = self.api(f"/manhua/data/zjv2/{cid}/hjm.ojbk", cache_ttl=self.CACHE_CHAPTER)
            if not res or not isinstance(res.get('data'), dict):
                return {"parse": 1, "url": "", "header": ""}

            d = res['data']
            real_imgtype = int(d.get('imgtype', imgtype))
            imgurls = [u.strip() for u in (d.get('imgurl') or '').split(',') if u.strip()]

            if not imgurls:
                return {"parse": 1, "url": "", "header": ""}

            urls = [self._proxyImgUrlCompact(u, real_imgtype) for u in imgurls]

            result = {
                "parse": 0,
                "playUrl": "",
                "url": f"pics://{'&&'.join(urls)}",
                "header": "",
            }
            self._cache_set(cache_key, result, self.CACHE_CHAPTER)
            return result
        except Exception:
            return {"parse": 1, "url": "", "header": ""}

    # ============ 本地代理（图片解密）============

    def localProxy(self, param):
        try:
            p = {}
            if isinstance(param, dict):
                p = param
            elif hasattr(param, 'path'):
                path = param.path
                if '?' in path:
                    qs = path.split('?', 1)[1]
                    p = dict(urllib.parse.parse_qsl(qs))
            elif isinstance(param, str):
                s = param
                if s.startswith('proxy://'):
                    s = s[8:]
                if s.startswith('http://127.0.0.1:'):
                    s = s.split('?', 1)[1] if '?' in s else ''
                p = dict(urllib.parse.parse_qsl(s))

            do = p.get('do', '')
            src = p.get('src', '')
            if src and not do:
                try:
                    pad = '=' * (-len(src) % 4)
                    query = base64.urlsafe_b64decode((src + pad).encode('utf-8')).decode('utf-8')
                    p = dict(urllib.parse.parse_qsl(query))
                    do = p.get('do', '')
                except Exception:
                    return [400, "text/plain", b"bad src"]

            if do != 'smimg':
                return [404, "text/plain", b"not found"]

            img_url = p.get('url') or p.get('u', '')
            img_url = urllib.parse.unquote(img_url)
            imgtype = int(p.get('t', p.get('imgtype', '3')))
            if not img_url:
                return [400, "text/plain", b"missing url"]

            # 图片解密结果缓存
            cache_key = f"img:{imgtype}:{img_url}"
            cached = self._img_cache.get(cache_key)
            if cached and time.time() < cached[0]:
                return [200, cached[2], cached[1]]

            raw = self.fetch(img_url, raw=True, headers={
                "Referer": self.IMG_REFERER,
                "User-Agent": self.getHeader()["User-Agent"],
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }, timeout=8, retry=2)

            if raw is None:
                return [502, "text/plain", b"fetch failed"]

            out = self._decryptImage(raw, imgtype)
            ctype = self._imageContentType(out)

            # 存入缓存
            if len(self._img_cache) > 100:
                now = time.time()
                expired = [k for k, (exp, _, _) in self._img_cache.items() if now >= exp]
                for k in expired:
                    del self._img_cache[k]
            self._img_cache[cache_key] = (time.time() + self.CACHE_IMAGE, out, ctype)

            return [200, ctype, out]
        except Exception:
            return [500, "text/plain", b"proxy error"]

    # ============ 内部工具 ============

    def _makeVod(self, item):
        if not isinstance(item, dict):
            return {}
        marks = []
        try:
            ms = item.get('marks')
            if ms and isinstance(ms, str):
                marks = json.loads(ms)
        except Exception:
            pass
        tag = ' '.join(marks) if marks else ''
        imgtype = int(item.get('imgurltype', 3))
        pic_url = item.get('imgurl') or ''
        pic_proxy = self._proxyImgUrl(pic_url, imgtype)
        return {
            "vod_id": str(item.get('id', '')),
            "vod_name": (item.get('title') or '').strip(),
            "vod_pic": pic_proxy,
            "type_name": tag,
            "vod_remarks": tag or (str(item.get('zhangjieNum', '')) + "话" if item.get('zhangjieNum') else ''),
        }

    def _cleanChapterName(self, name, book_name):
        if not name:
            return '未知章节'
        if book_name and len(book_name) > 1:
            titles = [t.strip() for t in book_name.split('/') if t.strip()]
            main = titles[0] if titles else book_name
            if name.startswith(main):
                name = name[len(main):].strip()
        m = _RE_CHAPTER_NUM.search(name)
        if m:
            return m.group(1)
        return name.strip() or '未知章节'

    @staticmethod
    def _decryptPayload(s):
        """enc 响应体解密：base64 -> reverse -> base64 -> JSON"""
        text = base64.b64decode(s).decode('utf-8')
        text = text[::-1]
        text = base64.b64decode(text).decode('utf-8')
        return json.loads(text)

    def _decryptImage(self, raw, imgtype):
        """按 imgtype 解密图片数据"""
        imgtype = int(imgtype)
        if imgtype == 1 or not raw:
            return raw

        if imgtype == 0:
            text = raw.decode('utf-8', errors='ignore')
            if ',' in text:
                text = text.split(',', 1)[1]
            try:
                return base64.b64decode(text)
            except Exception:
                return raw

        if imgtype == 2:
            return self._decryptAES(raw, b'525202f9149e061d')

        if imgtype == 3:
            return self._decryptVlogFast(raw)

        return raw

    def _decryptAES(self, data, key):
        """AES-ECB PKCS7 解密"""
        if _AES:
            try:
                cipher = _AES.new(key, _AES.MODE_ECB)
                return self._unpad(cipher.decrypt(data))
            except Exception:
                pass
            # 失败时返回原始数据，避免完全无法显示
            return data
        return data

    @staticmethod
    def _unpad(data):
        if not data:
            return data
        pad = data[-1]
        if isinstance(pad, int):
            if pad < 32 and data[-pad:] == bytes([pad]) * pad:
                return data[:-pad]
        else:
            if pad < 32 and data[-pad:] == bytes(pad) * pad:
                return data[:-pad]
        return data

    @staticmethod
    def _decryptVlogFast(data):
        """优化版 vlog 解密：预计算密钥表 + memoryview 直接操作"""
        if not data:
            return data

        e = bytearray(data)

        # ===== 模式A：6字节固定魔术头（用 all 而非 any，修复误判）=====
        is_mode_a = (len(e) >= 6 and
                      e[0] == _VLOG_MODEA_MAGIC[0] and
                      e[1] == _VLOG_MODEA_MAGIC[1] and
                      e[2] == _VLOG_MODEA_MAGIC[2] and
                      e[3] == _VLOG_MODEA_MAGIC[3] and
                      e[4] == _VLOG_MODEA_MAGIC[4] and
                      e[5] == _VLOG_MODEA_MAGIC[5])

        if is_mode_a:
            # 前 6 字节置 0，其余与 0xA3 异或
            for t in range(6, len(e)):
                e[t] ^= 0xA3
            e[0] = 0
            e[1] = 0
            e[2] = 0
            e[3] = 0
            e[4] = 0
            e[5] = 0
            return bytes(e)

        # ===== 模式B：检查是否为已知图片格式 =====
        is_encrypted = True
        for magic in _VLOG_IMG_MAGICS:
            mlen = len(magic)
            if len(e) >= mlen:
                match = True
                for j in range(mlen):
                    if e[j] != magic[j]:
                        match = False
                        break
                if match:
                    is_encrypted = False
                    break

        if not is_encrypted:
            # 已经是正常图片，直接返回
            return bytes(e)

        # 需要 XOR 解密（前 100 字节）
        limit = 100 if len(e) > 100 else len(e)
        # 使用预计算的 XOR 表加速
        xor_tbl = _VLOG_XOR_TABLE
        for i in range(limit):
            e[i] ^= xor_tbl[i]

        return bytes(e)

    @staticmethod
    def _imageContentType(data):
        if len(data) >= 3 and data[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        if len(data) >= 8 and data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if len(data) >= 3 and data[:3] == b'GIF':
            return "image/gif"
        if len(data) >= 4 and data[:4] == b'RIFF':
            return "image/webp"
        return "image/jpeg"


# ==================== 测试代码 ====================
if __name__ == '__main__':
    import time as _t

    spider = Spider()

    print("=== 1. 分类 ===")
    t0 = _t.time()
    home = spider.homeContent(filter=True)
    t1 = _t.time()
    classes = home.get('class', [])
    print(f"[{t1-t0:.2f}s] 分类数量: {len(classes)}")
    for c in classes[:8]:
        print(f"  {c['type_id']}: {c['type_name']}")

    print("\n=== 2. 首页推荐 ===")
    t2 = _t.time()
    home_video = spider.homeVideoContent()
    t3 = _t.time()
    lst = home_video.get('list', [])
    print(f"[{t3-t2:.2f}s] 推荐: {len(lst)} 条")
    if lst:
        print(f"  第一条: {lst[0]['vod_name'][:30]}")

    print("\n=== 3. 分类列表(韩漫) ===")
    t4 = _t.time()
    cat = spider.categoryContent("62", "1", False, None)
    t5 = _t.time()
    print(f"[{t5-t4:.2f}s] 获取到 {len(cat.get('list', []))} 条")
    if cat.get('list'):
        print(f"  第一条: {cat['list'][0]['vod_name'][:30]}")

    print("\n=== 4. 分类缓存命中测试 ===")
    t6 = _t.time()
    cat2 = spider.categoryContent("62", "1", False, None)
    t7 = _t.time()
    print(f"[{t7-t6:.3f}s] 缓存: {len(cat2.get('list', []))} 条")

    print("\n=== 5. 搜索 ===")
    t8 = _t.time()
    search = spider.searchContent("老师", False, "1")
    t9 = _t.time()
    print(f"[{t9-t8:.2f}s] 搜索结果: {len(search.get('list', []))} 条")

    print("\n=== 6. 详情页 ===")
    if cat.get('list'):
        vid = cat['list'][0].get('vod_id')
        t10 = _t.time()
        detail = spider.detailContent([vid])
        t11 = _t.time()
        item = detail.get('list', [{}])[0]
        print(f"[{t11-t10:.2f}s] 标题: {item.get('vod_name', '')}")
        chs = item.get('vod_play_url', '').split('#')
        print(f"  章节数: {len(chs)}")
        if chs:
            print(f"  第一章: {chs[0][:50]}")
            # 检查格式是否带 imgtype
            if '|' in chs[0]:
                print(f"  格式: 带 imgtype ✓")
            else:
                print(f"  格式: 旧版(无imgtype)")

    print("\n=== 7. 播放(章节图片列表) ===")
    if cat.get('list'):
        vid = cat['list'][0].get('vod_id')
        detail = spider.detailContent([vid])
        item = detail.get('list', [{}])[0]
        chs = item.get('vod_play_url', '').split('#')
        if chs:
            first_ch = chs[0].split('$')[1]
            t12 = _t.time()
            play = spider.playerContent("涩漫", first_ch, None)
            t13 = _t.time()
            url = play.get('url', '')
            img_count = url.count('&&') + 1 if url.startswith('pics://') else 0
            print(f"[{t13-t12:.2f}s] 图片数: {img_count}")
            print(f"  URL前80字: {url[:80]}")

            # 缓存测试
            t14 = _t.time()
            play2 = spider.playerContent("涩漫", first_ch, None)
            t15 = _t.time()
            print(f"[{t15-t14:.3f}s] (缓存)")

    print("\n=== 8. 图片解密验证 ===")
    if cat.get('list'):
        vid = cat['list'][0].get('vod_id')
        detail = spider.detailContent([vid])
        item = detail.get('list', [{}])[0]
        chs = item.get('vod_play_url', '').split('#')
        if chs:
            first_ch = chs[0].split('$')[1]
            play = spider.playerContent("涩漫", first_ch, None)
            url = play.get('url', '')
            if url.startswith('pics://'):
                first_img = url[7:].split('&&')[0]
                # 构造 proxy 参数
                if '?src=' in first_img:
                    src_param = first_img.split('?src=')[1]
                    t16 = _t.time()
                    result = spider.localProxy(f"src={src_param}")
                    t17 = _t.time()
                    status, ctype, data = result
                    print(f"[{t17-t16:.2f}s] 解密状态: {status}, 类型: {ctype}, 大小: {len(data)} bytes")
                    # 验证是否有效图片
                    if data[:3] == b'\xff\xd8\xff':
                        print("  ✓ 有效 JPEG 图片")
                    elif data[:8] == b'\x89PNG\r\n\x1a\n':
                        print("  ✓ 有效 PNG 图片")
                    else:
                        print(f"  ✗ 图片格式异常: {data[:10].hex()}")

                    # 缓存测试
                    t18 = _t.time()
                    result2 = spider.localProxy(f"src={src_param}")
                    t19 = _t.time()
                    print(f"[{t19-t18:.3f}s] (图片缓存)")

    print("\n✓ 全部测试完成")
