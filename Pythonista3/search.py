# -*- encoding:utf-8 -*-

# Reference
# http://omz-software.com/pythonista/docs/ios/index.html

import requests
from bs4 import BeautifulSoup as Soup
from collections import namedtuple
from urllib.parse import urljoin
import sys
from platform import os
from copy import copy

Book = namedtuple("Book", ["title", "author", "source", "link"])

Song = namedtuple("Song", ["name", "artist", "album", "source"])

iPhoneHeaders = {
    "User-Agent":
    "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1"
}


class Finder(object):
    def __init__(self, q):
        self.q = q

    def request(self):
        raise NotImplementedError

    def extract_items(self, resp):
        raise NotImplementedError

    def do(self, limit=5):
        resp = self.request()
        items = self.extract_items(resp)
        return items[:limit]


################ Find Book #################################


class KindleBook(Finder):
    def request(self):
        resp = requests.get("https://www.amazon.cn/s",
                            params={"k": self.q},
                            headers=iPhoneHeaders)
        return resp

    def extract_items(self, resp):
        books = list()
        soup = Soup(resp.content, features="html.parser")
        rowsDiv = soup.find("div",
                            class_="s-result-list s-search-results sg-row")
        if rowsDiv is None:
            return books
        rows = rowsDiv.find_all("div", class_="sg-col-inner")
        for row in rows:
            title = row.find("span",
                             class_="a-size-base a-color-base a-text-normal")
            link = row.find("a", title="product-detail")
            author = row.find("div",
                              class_="a-row a-size-small a-color-secondary")

            if all([title, link, author]):
                books.append(
                    Book(title=title.text,
                         link=urljoin("https://www.amazon.cn/", link['href']),
                         source="Kindle",
                         author=author.text))
        return books


class WeReadBook(Finder):
    def request(self):
        resp = requests.get("https://weread.qq.com/web/search/global",
                            headers=iPhoneHeaders,
                            params={
                                "keyword": self.q,
                                "count": 20,
                                "fragmentSize": 120
                            })
        return resp

    def extract_items(self, resp):
        books = list()
        data = resp.json()
        books_data = data.get("books", [])
        for b in books_data:
            bookInfo = b.get("bookInfo")
            if not bookInfo:
                continue
            books.append(
                Book(title=bookInfo.get("title"),
                     author=bookInfo.get("author"),
                     link=self.book_link(bookInfo.get("bookId")),
                     source="微信读书"))

        return books

    def book_link(self, bookId):
        # t 为 bookId
        #     e: function(t) {
        # if ("number" == typeof t && (t = t.toString()),
        # "string" != typeof t)
        #     return t;
        # var e = s.createHash("md5").update(t).digest("hex")
        #   , n = e.substr(0, 3)
        #   , r = function(t) {
        #     if (/^\d*$/.test(t)) {
        #         for (var e = t.length, n = [], r = 0; r < e; r += 9) {
        #             var i = t.slice(r, Math.min(r + 9, e));
        #             n.push(parseInt(i).toString(16))
        #         }
        #         return ["3", n]
        #     }
        #     for (var o = "", a = 0; a < t.length; a++) {
        #         o += t.charCodeAt(a).toString(16)
        #     }
        #     return ["4", [o]]
        # }(t);
        # n += r[0],
        # n += 2 + e.substr(e.length - 2, 2);
        # for (var i = r[1], o = 0; o < i.length; o++) {
        #     var a = i[o].length.toString(16);
        #     1 === a.length && (a = "0" + a),
        #     n += a,
        #     n += i[o],
        #     o < i.length - 1 && (n += "g")
        # }
        # return n.length < 20 && (n += e.substr(0, 20 - n.length)),
        # n += s.createHash("md5").update(n).digest("hex").substr(0, 3)
        # TODO 需要破解 bookid 转换成连接的加密算法, 此处暂且忽略·
        return bookId


################ Find Song #################################


class XiamiFinder(Finder):
    def request(self):
        xiami_headers = copy(iPhoneHeaders)
        xiami_headers["referer"] = "https://h.xiami.com/index.html?f=&from="
        resp = requests.get("https://api.xiami.com/web",
                            headers=xiami_headers,
                            params={
                                "v": "2.0",
                                "app_key": 1,
                                "key": self.q,
                                "page": 1,
                                "limit": 20,
                                "r": "search/songs"
                            })
        return resp

    def extract_items(self, resp):
        songs = list()
        data = resp.json()
        songs_data = data.get("data", {}).get("songs", [])
        for s in songs_data:
            songs.append(
                Song(name=s.get("song_name"),
                     artist=s.get("artist_name"),
                     source="虾米音乐",
                     album=s.get("album_name")))
        return songs


class NetEaseFinder(Finder):
    def request(self):
        netEaseHeaders = copy(iPhoneHeaders)
        netEaseHeaders["referer"] = "https://music.163.com/m/"
        netEaseHeaders["origin"] = "https://music.163.com"
        resp = requests.post("http://music.163.com/api/search/get/web",
                             headers=netEaseHeaders,
                             params={
                                 's': self.q,
                                 'type': 1,
                                 'offset': 0,
                                 'limit': 60
                             })
        return resp

    def extract_items(self, resp):
        songs = list()
        data = resp.json()
        songs_data = data.get("result", {}).get("songs")
        for s in songs_data:
            album = s.get('album', {}).get("name", "")
            name = s.get("name")
            artists = s.get("artists", [])
            if len(artists) < 1:
                continue
            artist = artists[0].get("name")
            songs.append(
                Song(
                    name=name,
                    artist=artist,
                    album=album,
                    source="网易音乐",
                ))
        return songs


class QQMusicFinder(Finder):
    def request(self):
        qqHeaders = copy(iPhoneHeaders)
        qqHeaders['referer'] = "http://m.y.qq.com"
        resp = requests.get(
            "http://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp",
            headers=qqHeaders,
            params={
                "w": self.q,
                "format": "json",
                "p": 1,
                "n": 10
            },
        )
        return resp

    def extract_items(self, resp):
        songs = list()
        data = resp.json()
        songs_data = data.get("data", {}).get("song", {}).get("list", [])
        for item in songs_data:
            album = item.get("albumname", "")
            name = item.get("songname", "")
            artist = ", ".join(
                [s.get("name", "") for s in item.get("singer", "")])

            songs.append(
                Song(name=name, artist=artist, album=album, source="QQ 音乐 "))
        return songs


############ 搜索资源聚合 ###################


class GroupFinder(Finder):
    finders = []

    def do(self, limit=15):
        avg = int(max(3, limit / len(self.finders)))
        result = list()
        for finder in self.finders:
            f = finder(self.q)
            result.extend(f.do(limit=avg))
        return result


class BookGroupFinder(GroupFinder):
    finders = [WeReadBook, KindleBook]


class MusicGroupFinder(GroupFinder):
    finders = [XiamiFinder, NetEaseFinder, QQMusicFinder]


###############################


def render_books(books):
    tmpl = """
   [{source}] {title} - {author}
   """
    result = ""
    for book in books:
        v = tmpl.format(title=book.title,
                        author=book.author,
                        source=book.source)
        result = result + v
    return result


def render_songs(songs):
    tmpl = """
   [{source}] {name}, {artist}「{album}」
   """
    result = ""
    for song in songs:
        v = tmpl.format(name=song.name,
                        album=song.album,
                        artist=song.artist,
                        source=song.source)
        result = result + v
    return result


#print(sys.argv)
if len(sys.argv) < 2:
    print("no book provided")
    sys.exit(-1)
query = sys.argv[1]
if len(sys.argv) > 2:
    media_type = sys.argv[2]

text = ""
if media_type.lower() == "song":
    sf = MusicGroupFinder(query)
    text = render_songs(sf.do(limit=12))
else:
    bf = BookGroupFinder(query)
    text = render_books(bf.do(limit=12))

# 视图层，用来展示结果。
# 如果不是 iphone 则退出.
if "iphone" not in os.uname().machine.lower():
    print(text)
    sys.exit(0)

import appex
from markdown2 import markdown
import ui

TEMPLATE = '''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Preview</title>
<style type="text/css">
body {
	font-family: helvetica;
	font-size: 15px;
	margin: 10px;
}
</style>
</head>
<body>{{CONTENT}}</body>
</html>
'''


def markdown_view(text):
    converted = markdown(text)
    html = TEMPLATE.replace('{{CONTENT}}', converted)
    webview = ui.WebView(name='搜索结果')
    webview.load_html(html)
    webview.present()


markdown_view(text)
