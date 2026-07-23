from __future__ import annotations
"""PartsHub OEM Parts Online crawler.

Crawler output is stored only in the backend SQLite database. The frontend consumes
that data exclusively through REST API calls, so neither layer imports the other.
"""
import argparse, hashlib, re, sqlite3, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup

USER_AGENT="PartsHubCrawler/4.0 (+https://github.com/Eddy-Max-Lee/partsHub)"
IMAGE_HOSTS={"cdn-product-images.revolutionparts.io","cdn-illustrations.revolutionparts.io"}

def now(): return datetime.now(timezone.utc).isoformat()

def clean(text: str | None) -> str:
    return re.sub(r"\s+"," ",(text or "")).strip()

@dataclass
class ImageRecord:
    url: str
    image_type: str
    label_zh: str

class OemPartsCrawler:
    def __init__(self, db_path: Path, delay: float=1.2, usd_twd_rate: float=32.3582, obey_robots: bool=True):
        self.db_path=db_path; self.delay=delay; self.rate=usd_twd_rate; self.obey_robots=obey_robots
        self.client=httpx.Client(headers={"User-Agent":USER_AGENT,"Accept-Language":"zh-TW,zh;q=0.9,en;q=0.8"},follow_redirects=True,timeout=30)
        self._robots: dict[str,RobotFileParser]={}

    def allowed(self,url: str) -> bool:
        if not self.obey_robots: return True
        parsed=urlparse(url); root=f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots:
            rp=RobotFileParser(); rp.set_url(root+"/robots.txt")
            try: rp.read()
            except Exception: return True
            self._robots[root]=rp
        return self._robots[root].can_fetch(USER_AGENT,url)

    def fetch(self,url: str) -> str:
        if not self.allowed(url): raise PermissionError(f"robots.txt 不允許爬取：{url}")
        response=self.client.get(url); response.raise_for_status(); time.sleep(self.delay)
        return response.text

    def gallery(self,soup: BeautifulSoup, page_url: str) -> list[ImageRecord]:
        found=[]; seen=set()
        for img in soup.find_all('img'):
            raw=img.get('data-src') or img.get('data-zoom-image') or img.get('src')
            if not raw: continue
            url=urljoin(page_url,raw); host=urlparse(url).netloc
            if host not in IMAGE_HOSTS or url in seen: continue
            seen.add(url)
            typ='product' if 'cdn-product-images' in host else 'diagram'
            label='商品圖片' if typ=='product' else '原廠零件分解圖'
            found.append(ImageRecord(url,typ,label))
        return found

    def parse_product(self,url: str,html: str) -> dict:
        soup=BeautifulSoup(html,'html.parser')
        title=clean(soup.find('h1').get_text(' ',strip=True) if soup.find('h1') else '')
        pn_match=re.search(r'\(([0-9A-Z-]+)\)',title,re.I)
        part_number=pn_match.group(1).upper() if pn_match else ''
        name_en=clean(title.split(' - Audi')[0])
        page_text=clean(soup.get_text(' ',strip=True))
        msrp_match=re.search(r'MSRP\s*\$([0-9,.]+)',page_text,re.I)
        msrp=float(msrp_match.group(1).replace(',','')) if msrp_match else None
        years_match=re.search(r'(19|20)\d{2}-(19|20)\d{2}',page_text)
        return {'part_number':part_number,'name_en':name_en,'msrp_usd':msrp,'msrp_twd':round(msrp*self.rate) if msrp else None,'years':years_match.group(0) if years_match else '', 'source_url':url,'gallery':self.gallery(soup,url)}

    def crawl_product_urls(self, urls: list[str]):
        con=sqlite3.connect(self.db_path)
        for url in urls:
            html=self.fetch(url); parsed=self.parse_product(url,html)
            row=con.execute('SELECT id FROM products WHERE part_number=?',(parsed['part_number'],)).fetchone()
            if not row: continue
            pid=row[0]
            con.execute('UPDATE products SET name_en=?,msrp_usd=COALESCE(?,msrp_usd),msrp_twd=COALESCE(?,msrp_twd),years=COALESCE(NULLIF(?,''),years),crawled_at=? WHERE id=?',(parsed['name_en'],parsed['msrp_usd'],parsed['msrp_twd'],parsed['years'],now(),pid))
            con.execute('DELETE FROM product_images WHERE product_id=?',(pid,))
            for order,image in enumerate(parsed['gallery']):
                con.execute('INSERT OR IGNORE INTO product_images(product_id,label_zh,image_type,source_url,sort_order) VALUES(?,?,?,?,?)',(pid,image.label_zh,image.image_type,image.url,order))
            con.execute('INSERT INTO source_pages(url,page_type,http_status,fetched_at,content_sha256,notes) VALUES(?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET http_status=excluded.http_status,fetched_at=excluded.fetched_at,content_sha256=excluded.content_sha256,notes=excluded.notes',(url,'product',200,now(),hashlib.sha256(html.encode()).hexdigest(),f"抓到 {len(parsed['gallery'])} 張相簿圖片"))
            con.commit()
        con.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--db',default='data/parts.db'); parser.add_argument('--delay',type=float,default=1.2); parser.add_argument('urls',nargs='+')
    args=parser.parse_args(); OemPartsCrawler(Path(args.db),args.delay).crawl_product_urls(args.urls)
