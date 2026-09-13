import { load, _ } from 'assets://js/lib/cat.js';
import 'assets://js/lib/crypto-js.js';

const host = 'https://v.qq.com';
const apihost = 'https://pbaccess.video.qq.com';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0';

// 第三方解析接口
const parseApi = 'https://jx.xmflv.cc/?url=';

// 频道列表接口（筛选/分类）
const API_CHANNEL = 'trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?video_appid=1000005&vplatform=2&vversion_name=8.9.10&new_mark_label_enabled=1';
// 详情页接口（选集/简介）
const API_DETAIL = 'trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?video_appid=3000010&vplatform=2&vversion_name=8.2.96';
// 搜索接口
const API_SEARCH = 'trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vplatform=2';

let danmakuAPI = '';

async function init(cfg) {
    danmakuAPI = (cfg && cfg.ext) || '';
}

async function request(baseUrl, apiPath, params = {}, method = 'get') {
    const url = apiPath.startsWith('http') ? apiPath : `${baseUrl}/${apiPath}`;
    let reqOptions = {
        method: method,
        headers: {
            'User-Agent': UA,
            'Referer': host,
            'Origin': host
        }
    };

    if (method.toLowerCase() === 'get') {
        const queryString = Object.entries(params)
            .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
            .join('&');
        reqOptions.url = queryString ? `${url}${url.includes('?') ? '&' : '?'}${queryString}` : url;
    } else if (method.toLowerCase() === 'post') {
        reqOptions.body = JSON.stringify(params);
        reqOptions.headers['Content-Type'] = 'application/json';
    }

    const res = await req(reqOptions.url || url, reqOptions);
    try {
        return typeof res.content === 'string' ? JSON.parse(res.content) : (res.content || {});
    } catch (e) {
        return {};
    }
}

// 遍历 module_list_datas，取出所有 item_datas
function collectItems(json) {
    const out = [];
    const mods = (json && json.data && json.data.module_list_datas) || [];
    for (const mod of mods) {
        for (const d of (mod.module_datas || [])) {
            const items = (d.item_data_lists && d.item_data_lists.item_datas) || [];
            out.push(...items);
        }
    }
    return out;
}

async function home() {
    const classes = [
        { type_id: '100113', type_name: '电视剧' },
        { type_id: '100173', type_name: '电影' },
        { type_id: '100109', type_name: '综艺' },
        { type_id: '100119', type_name: '动漫' },
        { type_id: '100105', type_name: '纪录片' },
        { type_id: '100150', type_name: '少儿' },
        { type_id: '110755', type_name: '短剧' }
    ];

    // 以下筛选项均取自当前线上接口返回的 filter 数据
    const filters = {
        "100113": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最新上架", "v": "79" }, { "n": "高分好评", "v": "85" }] },
            { "key": "itype", "name": "类型", "value": [{ "n": "全部", "v": "-1" }, { "n": "爱情", "v": "1" }, { "n": "都市", "v": "2" }, { "n": "青春", "v": "3" }, { "n": "奇幻", "v": "4" }, { "n": "武侠", "v": "5" }, { "n": "古装", "v": "6" }, { "n": "科幻", "v": "7" }, { "n": "猎奇", "v": "8" }, { "n": "竞技", "v": "9" }, { "n": "传奇", "v": "10" }, { "n": "逆袭", "v": "19" }, { "n": "军旅", "v": "11" }, { "n": "家庭", "v": "12" }, { "n": "喜剧", "v": "13" }, { "n": "悬疑", "v": "14" }, { "n": "权谋", "v": "15" }, { "n": "革命", "v": "16" }, { "n": "现实", "v": "17" }, { "n": "刑侦", "v": "18" }, { "n": "民国", "v": "20" }, { "n": "IP改编", "v": "21" }] },
            { "key": "iarea", "name": "地区", "value": [{ "n": "全部", "v": "-1" }, { "n": "内地", "v": "0" }, { "n": "中国香港", "v": "14" }, { "n": "中国台湾", "v": "4" }, { "n": "美国", "v": "8" }, { "n": "泰国", "v": "9" }, { "n": "英国", "v": "1" }, { "n": "韩国", "v": "5" }, { "n": "日本", "v": "10" }, { "n": "其他", "v": "9999" }] },
            { "key": "iyear", "name": "年份", "value": [{ "n": "全部", "v": "-1" }, { "n": "即将上线", "v": "1" }, { "n": "2026", "v": "2026" }, { "n": "2025", "v": "2025" }, { "n": "2024", "v": "2" }, { "n": "2023", "v": "3" }, { "n": "2022", "v": "4" }, { "n": "2021", "v": "5" }, { "n": "2020-2016", "v": "6" }, { "n": "2015-2011", "v": "7" }, { "n": "2010-2000", "v": "8" }, { "n": "更早", "v": "9" }] },
            { "key": "ipay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "1" }, { "n": "限免", "v": "2" }, { "n": "会员", "v": "3" }] }
        ],
        "100173": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最新", "v": "83" }, { "n": "高分好评", "v": "81" }] },
            { "key": "itype", "name": "类型", "value": [{ "n": "全部", "v": "-1" }, { "n": "动作", "v": "4" }, { "n": "喜剧", "v": "3" }, { "n": "爱情", "v": "5" }, { "n": "科幻", "v": "12" }, { "n": "犯罪", "v": "6" }, { "n": "冒险", "v": "7" }, { "n": "恐怖", "v": "11" }, { "n": "动画", "v": "15" }, { "n": "战争", "v": "8" }, { "n": "悬疑", "v": "10" }, { "n": "灾难", "v": "25" }, { "n": "青春", "v": "26" }] },
            { "key": "iarea", "name": "地区", "value": [{ "n": "全部", "v": "-1" }, { "n": "内地", "v": "100024" }, { "n": "中国香港", "v": "100025" }, { "n": "中国台湾", "v": "100026" }, { "n": "美国", "v": "100029" }, { "n": "日本", "v": "100027" }, { "n": "韩国", "v": "100028" }, { "n": "泰国", "v": "100031" }, { "n": "印度", "v": "100030" }, { "n": "英国", "v": "15" }, { "n": "法国", "v": "16" }, { "n": "德国", "v": "17" }, { "n": "加拿大", "v": "18" }, { "n": "西班牙", "v": "19" }, { "n": "意大利", "v": "20" }, { "n": "澳大利亚", "v": "21" }, { "n": "其他", "v": "100033" }] },
            { "key": "iyear", "name": "年份", "value": [{ "n": "全部", "v": "-1" }, { "n": "即将上线", "v": "999" }, { "n": "2026", "v": "2026" }, { "n": "2025", "v": "2025" }, { "n": "2024", "v": "2024" }, { "n": "2023", "v": "2023" }, { "n": "2022", "v": "2022" }, { "n": "2021", "v": "2021" }, { "n": "2020", "v": "2020" }, { "n": "2019", "v": "20" }, { "n": "2018", "v": "2018" }, { "n": "2017", "v": "1" }, { "n": "2016", "v": "2" }, { "n": "2015", "v": "3" }, { "n": "2014", "v": "4" }, { "n": "2013-2011", "v": "5" }, { "n": "2010-2006", "v": "6" }, { "n": "2005-2000", "v": "7" }, { "n": "90年代", "v": "8" }, { "n": "80年代", "v": "9" }, { "n": "其他", "v": "10" }] },
            { "key": "ipay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "1" }, { "n": "会员", "v": "8" }, { "n": "付费", "v": "4" }] },
            { "key": "characteristic", "name": "特色", "value": [{ "n": "全部", "v": "-1" }, { "n": "院线电影", "v": "1" }, { "n": "网络电影", "v": "2" }, { "n": "独播", "v": "5" }, { "n": "原声", "v": "8" }, { "n": "粤语", "v": "9" }, { "n": "获奖佳片", "v": "6" }] }
        ],
        "100109": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最近更新", "v": "23" }, { "n": "高分好评", "v": "85" }] },
            { "key": "itype", "name": "类型", "value": [{ "n": "全部", "v": "-1" }, { "n": "游戏", "v": "10" }, { "n": "脱口秀", "v": "2" }, { "n": "音乐舞台", "v": "11" }, { "n": "情感", "v": "12" }, { "n": "生活", "v": "22" }, { "n": "职场", "v": "20" }, { "n": "喜剧", "v": "14" }, { "n": "美食", "v": "19" }, { "n": "潮流运动", "v": "21" }, { "n": "竞技", "v": "24" }, { "n": "影视", "v": "16" }, { "n": "电竞", "v": "15" }, { "n": "推理", "v": "25" }, { "n": "访谈", "v": "3" }, { "n": "亲子", "v": "17" }, { "n": "文化", "v": "26" }, { "n": "晚会", "v": "6" }, { "n": "资讯", "v": "7" }] },
            { "key": "iarea", "name": "地区", "value": [{ "n": "全部", "v": "-1" }, { "n": "国内", "v": "1" }, { "n": "海外", "v": "2" }] },
            { "key": "iyear", "name": "年份", "value": [{ "n": "全部", "v": "-1" }, { "n": "2026", "v": "2026" }, { "n": "2025", "v": "2025" }, { "n": "2024", "v": "2024" }, { "n": "2023", "v": "2023" }, { "n": "2022", "v": "2022" }, { "n": "2021", "v": "2021" }, { "n": "2020", "v": "50" }, { "n": "2019", "v": "7" }, { "n": "2018", "v": "1" }, { "n": "2017", "v": "2" }, { "n": "2016", "v": "3" }, { "n": "2015", "v": "4" }, { "n": "更早", "v": "99" }] },
            { "key": "ipay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "1" }, { "n": "会员", "v": "6" }] },
            { "key": "exclusive", "name": "出品", "value": [{ "n": "全部", "v": "-1" }, { "n": "腾讯自制", "v": "1" }, { "n": "独播", "v": "2" }] }
        ],
        "100119": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最近更新", "v": "23" }, { "n": "高分好评", "v": "85" }] },
            { "key": "itype", "name": "类型", "value": [{ "n": "全部", "v": "-1" }, { "n": "玄幻", "v": "9" }, { "n": "科幻", "v": "4" }, { "n": "奇幻", "v": "21" }, { "n": "武侠", "v": "13" }, { "n": "仙侠", "v": "23" }, { "n": "都市", "v": "24" }, { "n": "恋爱", "v": "7" }, { "n": "搞笑", "v": "1" }, { "n": "冒险", "v": "2" }, { "n": "悬疑", "v": "17" }, { "n": "竞技", "v": "20" }, { "n": "日常", "v": "15" }, { "n": "真人", "v": "18" }, { "n": "治愈", "v": "25" }, { "n": "游戏", "v": "26" }, { "n": "异能", "v": "27" }, { "n": "历史", "v": "19" }, { "n": "古风", "v": "28" }, { "n": "智斗", "v": "29" }, { "n": "恐怖", "v": "30" }, { "n": "美食", "v": "31" }, { "n": "音乐", "v": "32" }, { "n": "其他", "v": "12" }] },
            { "key": "iarea", "name": "地区", "value": [{ "n": "全部", "v": "-1" }, { "n": "内地", "v": "1" }, { "n": "日本", "v": "2" }, { "n": "欧美", "v": "3" }, { "n": "其他", "v": "4" }] },
            { "key": "iyear", "name": "年份", "value": [{ "n": "全部", "v": "-1" }, { "n": "2026", "v": "2026" }, { "n": "2025", "v": "2025" }, { "n": "2024", "v": "2024" }, { "n": "2023", "v": "2023" }, { "n": "2022", "v": "2022" }, { "n": "2021", "v": "2021" }, { "n": "2020", "v": "50" }, { "n": "2019", "v": "11" }, { "n": "2018", "v": "2018" }, { "n": "2017", "v": "2017" }, { "n": "2016", "v": "1" }, { "n": "2015", "v": "2" }, { "n": "00年代", "v": "7" }, { "n": "90年代", "v": "8" }, { "n": "更早", "v": "10" }] },
            { "key": "anime_status", "name": "状态", "value": [{ "n": "全部", "v": "-1" }, { "n": "即将上线", "v": "46" }, { "n": "更新中", "v": "44" }, { "n": "已完结", "v": "45" }] },
            { "key": "ipay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "867" }, { "n": "会员", "v": "6" }] }
        ],
        "100105": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最新", "v": "74" }, { "n": "高分好评", "v": "85" }] },
            { "key": "itype", "name": "分类", "value": [{ "n": "全部", "v": "-1" }, { "n": "自然", "v": "4" }, { "n": "美食", "v": "10" }, { "n": "社会", "v": "3" }, { "n": "人文", "v": "6" }, { "n": "历史", "v": "1" }, { "n": "军事", "v": "2" }, { "n": "科技", "v": "8" }, { "n": "财经", "v": "14" }, { "n": "探险", "v": "15" }, { "n": "罪案", "v": "7" }, { "n": "竞技", "v": "12" }, { "n": "旅游", "v": "11" }] },
            { "key": "iregion", "name": "地区", "value": [{ "n": "全部", "v": "0" }, { "n": "国内", "v": "1" }, { "n": "国外", "v": "2" }] },
            { "key": "iyear", "name": "年份", "value": [{ "n": "全部", "v": "-1" }, { "n": "2026", "v": "2026" }, { "n": "2025", "v": "2025" }, { "n": "2024", "v": "1" }, { "n": "2023", "v": "2" }, { "n": "2022", "v": "3" }, { "n": "2021", "v": "4" }, { "n": "2020", "v": "5" }, { "n": "2019-2015", "v": "6" }, { "n": "2014-2010", "v": "7" }, { "n": "2009-2005", "v": "8" }, { "n": "更早", "v": "9" }] },
            { "key": "pay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "1" }, { "n": "会员", "v": "2" }, { "n": "限免", "v": "3" }] },
            { "key": "itrailer", "name": "出品机构", "value": [{ "n": "全部", "v": "-1" }, { "n": "腾讯出品", "v": "15" }, { "n": "央视", "v": "8" }, { "n": "BBC", "v": "1" }, { "n": "国家地理", "v": "4" }, { "n": "探索频道", "v": "3174" }, { "n": "HBO", "v": "3175" }, { "n": "NHK", "v": "2" }, { "n": "ITV", "v": "3530" }, { "n": "历史频道", "v": "7" }] }
        ],
        "100150": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最新", "v": "76" }] },
            { "key": "itype", "name": "类型", "value": [{ "n": "全部", "v": "-1" }, { "n": "磨耳朵", "v": "22" }, { "n": "涨知识", "v": "23" }, { "n": "冒险", "v": "10" }, { "n": "儿歌", "v": "1" }, { "n": "交通工具", "v": "11" }, { "n": "益智早教", "v": "2" }, { "n": "玩具", "v": "4" }, { "n": "魔幻·科幻", "v": "12" }, { "n": "动物", "v": "13" }, { "n": "真人·特摄", "v": "14" }, { "n": "家长甄选", "v": "17" }, { "n": "动画电影", "v": "20" }, { "n": "科普纪录片", "v": "21" }] },
            { "key": "iyear", "name": "年龄", "value": [{ "n": "全部", "v": "-1" }, { "n": "0-3岁", "v": "1" }, { "n": "4-6岁", "v": "2" }, { "n": "7-9岁", "v": "3" }, { "n": "10岁以上", "v": "4" }, { "n": "全年龄", "v": "7" }] },
            { "key": "gender", "name": "性别", "value": [{ "n": "全部", "v": "-1" }, { "n": "女孩", "v": "1" }, { "n": "男孩", "v": "2" }] },
            { "key": "language", "name": "语言", "value": [{ "n": "全部", "v": "-1" }, { "n": "普通话版", "v": "3" }, { "n": "英文版", "v": "1" }] },
            { "key": "ipay", "name": "资费", "value": [{ "n": "全部", "v": "-1" }, { "n": "免费", "v": "1" }, { "n": "会员", "v": "2" }] }
        ],
        "110755": [
            { "key": "sort", "name": "排序", "value": [{ "n": "最热", "v": "75" }, { "n": "最新上架", "v": "76" }, { "n": "限免中", "v": "90" }] },
            { "key": "prefer", "name": "偏好", "value": [{ "n": "全部", "v": "-1" }, { "n": "男频", "v": "2" }, { "n": "女频", "v": "1" }] },
            { "key": "story", "name": "背景", "value": [{ "n": "全部", "v": "-1" }, { "n": "古装爱情", "v": "1" }, { "n": "都市爱情", "v": "2" }, { "n": "都市奇幻", "v": "3" }, { "n": "古装权谋", "v": "5" }, { "n": "年代", "v": "6" }, { "n": "青春", "v": "8" }, { "n": "职场", "v": "10" }, { "n": "民国", "v": "11" }, { "n": "末日", "v": "12" }, { "n": "乡村", "v": "15" }, { "n": "悬疑推理", "v": "18" }, { "n": "玄幻", "v": "19" }, { "n": "喜剧", "v": "21" }] },
            { "key": "identity", "name": "人设", "value": [{ "n": "全部", "v": "-1" }, { "n": "总裁", "v": "1" }, { "n": "大女主", "v": "2" }, { "n": "战神", "v": "3" }, { "n": "萌娃", "v": "4" }, { "n": "神医", "v": "5" }, { "n": "落难千金", "v": "6" }, { "n": "赘婿", "v": "7" }, { "n": "神豪", "v": "8" }, { "n": "大男主", "v": "9" }, { "n": "女帝", "v": "10" }, { "n": "皇后王妃", "v": "11" }, { "n": "青梅竹马", "v": "13" }, { "n": "欢喜冤家", "v": "16" }, { "n": "大叔", "v": "24" }, { "n": "小人物", "v": "28" }, { "n": "团宠", "v": "29" }] },
            { "key": "attraction", "name": "看点", "value": [{ "n": "全部", "v": "-1" }, { "n": "穿越", "v": "3" }, { "n": "重生", "v": "4" }, { "n": "逆袭", "v": "5" }, { "n": "家庭伦理", "v": "6" }, { "n": "虐心", "v": "7" }, { "n": "曲折爱情", "v": "8" }, { "n": "破镜重圆", "v": "9" }, { "n": "马甲", "v": "10" }, { "n": "异能", "v": "11" }, { "n": "甜宠爱情", "v": "12" }, { "n": "奇幻爱情", "v": "13" }, { "n": "闪婚", "v": "15" }, { "n": "系统流", "v": "16" }, { "n": "亲情", "v": "20" }, { "n": "宅门风云", "v": "21" }, { "n": "家族恩怨", "v": "22" }, { "n": "身份之谜", "v": "23" }, { "n": "追妻", "v": "25" }, { "n": "虐渣复仇", "v": "29" }, { "n": "权力争夺", "v": "47" }, { "n": "娱乐圈", "v": "88" }] }
        ]
    };
    return JSON.stringify({ class: classes, filters: filters });
}

async function homeVod() {
    // 首页推荐直接复用电视剧最热首页
    try {
        const data = await fetchChannel('100113', 'sort=75', 0);
        return JSON.stringify({ list: data.list });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

// 把 extend 转成接口需要的 filter_params，仅提交用户实际选择的项
function buildFilterParams(extend) {
    const parts = [];
    let hasSort = false;
    for (const key of Object.keys(extend || {})) {
        const val = extend[key];
        if (val === undefined || val === null || val === '' || val === '-1') continue;
        if (key === 'sort') hasSort = true;
        parts.push(`${key}=${val}`);
    }
    if (!hasSort) parts.unshift('sort=75');
    return parts.join('&');
}

function pickPic(p) {
    return p.new_pic_vt || p.pic_vt || p.new_pic_hz || p.pic_hz || '';
}

// 频道列表分页：接口按 page_index 从 0 开始，每页 21 条
async function fetchChannel(tid, filter_params, pageIndex) {
    const json = await request(apihost, API_CHANNEL, {
        "page_params": {
            "channel_id": tid,
            "filter_params": filter_params,
            "page_type": "channel_operation",
            "page_id": "channel_list_second_page"
        },
        "page_context": {
            "page_index": String(pageIndex),
            "video_un_page_index": String(pageIndex)
        }
    }, "POST");

    const seen = {};
    const list = [];
    for (const item of collectItems(json)) {
        if (item.item_type !== '2') continue;
        const p = item.item_params || {};
        if (!p.cid || seen[p.cid]) continue;
        seen[p.cid] = 1;
        list.push({
            vod_id: `${p.cid}&&&${p.title || ''}&&&${p.second_title || ''}`,
            vod_name: p.title,
            vod_pic: pickPic(p),
            vod_year: p.year && p.year !== '0' ? p.year : '',
            vod_remarks: p.timelong || p.second_title || ''
        });
    }
    const hasNext = !!(json.data && json.data.has_next_page);
    return { list: list, hasNext: hasNext };
}

async function category(tid, pg, filter, extend) {
    const page = parseInt(pg) || 1;
    const filter_params = buildFilterParams(extend);
    try {
        const data = await fetchChannel(tid, filter_params, page - 1);
        // 接口的 has_next_page 并不可靠（末页仍为 true），改以本页条数判断
        const more = data.hasNext && data.list.length >= 21;
        return JSON.stringify({
            page: page,
            pagecount: more ? page + 1 : page,
            limit: 21,
            total: more ? (page + 1) * 21 : (page - 1) * 21 + data.list.length,
            list: data.list
        });
    } catch (e) {
        return JSON.stringify({ page: page, pagecount: page, limit: 21, total: 0, list: [] });
    }
}

async function episodeList(cid, page_context) {
    const json = await request(apihost, API_DETAIL, {
        "page_params": {
            "req_from": "web_vsite",
            "page_id": "vsite_episode_list",
            "page_type": "detail_operation",
            "cid": cid,
            "page_context": page_context || '',
            "detail_page_type": "1"
        }
    }, "POST");

    const mods = (json.data && json.data.module_list_datas) || [];
    const mod = mods.length ? mods[0].module_datas[0] : null;
    if (!mod) return { items: [], tabs: [] };
    const items = ((mod.item_data_lists && mod.item_data_lists.item_datas) || []).filter(x => x.item_type === '1');
    let tabs = [];
    try {
        tabs = JSON.parse((mod.module_params && mod.module_params.tabs) || '[]') || [];
    } catch (e) {
        tabs = [];
    }
    return { items: items, tabs: tabs };
}

// 简介、年份、地区等
async function introInfo(cid) {
    const info = {};
    try {
        const json = await request(apihost, API_DETAIL, {
            "page_params": {
                "req_from": "web_vsite",
                "page_id": "detail_page_introduction",
                "page_type": "detail_operation",
                "cid": cid,
                "detail_page_type": "1"
            }
        }, "POST");
        const items = collectItems(json);
        if (items.length) {
            const p = items[0].item_params || {};
            info.vod_name = p.title || '';
            info.vod_year = p.year || p.cover_year || '';
            info.vod_area = p.area_name || '';
            info.vod_content = p.cover_description || p.short_description || '';
            info.vod_pic = p.new_pic_vt || p.new_pic_hz || '';
            const genres = [p.main_genres, p.sub_genre].filter(Boolean).join(' ');
            info.type_name = genres;
            info.vod_remarks = p.timelong || p.update_notify_desc || (p.episode_all ? `全${p.episode_all}集` : '');
        }
    } catch (e) { }
    return info;
}

// 演员/导演只有搜索接口返回，按标题反查
async function castInfo(cid, title) {
    const info = { vod_actor: '', vod_director: '', vod_lang: '' };
    if (!title) return info;
    try {
        const json = await request(apihost, API_SEARCH, {
            "version": "25031901", "clientType": 1, "uuid": uuidv4().toUpperCase(),
            "query": title, "pagenum": 0, "pagesize": 20, "extraInfo": { "isNewMarkLabel": "1" }
        }, "POST");
        let list = (json.data && json.data.normalList && json.data.normalList.itemList) || [];
        const boxes = (json.data && json.data.areaBoxList) || [];
        for (const box of boxes) list = list.concat(box.itemList || []);
        const hit = list.find(i => i.doc && i.doc.id === cid);
        if (hit && hit.videoInfo) {
            const v = hit.videoInfo;
            info.vod_actor = (v.actors || []).join(' ');
            info.vod_director = (v.directors || []).join(' ');
            info.vod_lang = (v.language || []).join(' ');
        }
    } catch (e) { }
    return info;
}

function episodeName(p, vodName) {
    let name = p.title || '';
    // 剧集接口里 title 可能只是集数（"1"），这时用 play_title 去掉剧名前缀
    if (!name || /^\d+$/.test(name)) {
        let alt = p.play_title || '';
        if (vodName && alt.indexOf(vodName) === 0) alt = alt.substring(vodName.length).trim();
        name = alt || (name ? `第${name}集` : '');
    } else if (vodName && name.indexOf(vodName) === 0 && name.length > vodName.length) {
        name = name.substring(vodName.length).trim();
    }
    if (!name) name = p.vid || '正片';
    return name.replace(/#/g, '＃').replace(/\$/g, '＄');
}

async function detail(id) {
    const [cid, title, second_title] = String(id).split('&&&');
    try {
        const first = await episodeList(cid, '');
        let items = first.items.slice();

        // 长剧集分段在 module_params.tabs 里，next_page_context 已废弃
        const tabs = (first.tabs || []).filter(t => t && t.page_context && !t.selected);
        for (const tab of tabs.slice(0, 30)) {
            try {
                const more = await episodeList(cid, tab.page_context);
                items = items.concat(more.items);
            } catch (e) { }
        }

        const info = await introInfo(cid);
        const vodName = info.vod_name || title || '';
        const cast = await castInfo(cid, vodName);

        const allData = items;
        const plays = allData
            .filter(item => item.item_params && item.item_params.play_title && !item.item_params.play_title.includes("预"))
            .map(item => `${item.item_params.title}$${host}/x/cover/${cid}/${item.item_id}.html`);
        if (!plays.length) {
            plays.push(`正片$${host}/x/cover/${cid}.html`);
        }

        return JSON.stringify({
            list: [{
                vod_id: id,
                vod_name: vodName || '视频详情',
                vod_pic: info.vod_pic || '',
                type_name: info.type_name || '',
                vod_year: info.vod_year || '',
                vod_area: info.vod_area || '',
                vod_lang: cast.vod_lang || '',
                vod_remarks: info.vod_remarks || second_title || '',
                vod_actor: cast.vod_actor || '',
                vod_director: cast.vod_director || '',
                vod_content: info.vod_content || second_title || '',
                vod_play_from: '腾讯视频',
                vod_play_url: plays.join('#')
            }]
        });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

// 播放解析 - 已内置接口
async function play(flag, id, flags) {
    try {
        const res = await request('', parseApi + encodeURIComponent(id), {}, "GET");
        // 尝试获取解析后的视频流地址
        const finalUrl = res.url || (res.data && res.data.url);
        if (finalUrl) {
            return JSON.stringify({
                parse: 0,
                url: finalUrl,
                danmaku: danmakuAPI + id
            });
        }
    } catch (e) {}
    
    // 如果解析口失效，回退给软件外壳解析
    return JSON.stringify({
        jx: 1,
        url: id,
        danmaku: danmakuAPI + id
    });
}

function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = (Math.random() * 16) | 0, v = c == 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

async function search(wd, quick, pg) {
    const page = parseInt(pg || 1) || 1;
    try {
        const json = await request(apihost, API_SEARCH, {
            "version": "25031901", "clientType": 1, "uuid": uuidv4().toUpperCase(),
            "query": wd, "pagenum": page - 1, "pagesize": 30, "extraInfo": { "isNewMarkLabel": "1" }
        }, "POST");

        let result = (json.data && json.data.normalList && json.data.normalList.itemList) || [];
        const boxes = (json.data && json.data.areaBoxList) || [];
        for (const box of boxes) result = result.concat(box.itemList || []);

        const seen = {};
        const vod = [];
        for (const i of result) {
            if (!i.doc || i.doc.dataType !== 2 || !i.videoInfo) continue;
            const id = i.doc.id;
            if (!id || seen[id]) continue;
            seen[id] = 1;
            const v = i.videoInfo;
            const name = String(v.title || '').replace(/<[^>]+>/g, '');
            vod.push({
                vod_id: `${id}&&&${name}&&&${v.subTitle || ''}`,
                vod_name: name,
                vod_pic: v.imgUrl || '',
                vod_year: v.year && v.year !== 0 ? String(v.year) : '',
                vod_remarks: [v.typeName, v.subTitle].filter(Boolean).join(' ')
            });
        }
        return JSON.stringify({ list: vod, page: page, pagecount: page, limit: vod.length, total: vod.length });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, play, search };
}
