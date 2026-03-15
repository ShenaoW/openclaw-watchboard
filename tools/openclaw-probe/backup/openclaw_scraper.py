#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 实例信息爬虫脚本 (纯 requests 版本)
通过直接解析 HTML 中 <a class="endpoint" href="..."> 获取完整 IP，无需 Selenium。
使用多线程并发请求，大幅提升爬取速度。
爬取目标: https://openclaw.allegro.earth/
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
from datetime import datetime
import re
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openclaw_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class OpenClawScraper:
    """OpenClaw 实例信息爬虫（纯 requests + 并发版）"""

    def __init__(
        self,
        base_url: str = "https://openclaw.allegro.earth",
        max_workers: int = 8,
        delay_range: tuple = (0.5, 1.5),
        timeout: int = 20,
    ):
        self.base_url = base_url.rstrip('/')
        self.max_workers = max_workers      # 并发线程数
        self.delay_range = delay_range      # 每次请求前的随机延迟范围(秒)
        self.timeout = timeout

        self._session_lock = threading.Lock()
        # 每个线程维护独立 Session（避免锁竞争）
        self._local = threading.local()

        self.instances: List[Dict] = []
        self._instances_lock = threading.Lock()

        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ------------------------------------------------------------------
    # 内部 Session 管理：每个线程持有独立 Session，避免锁竞争
    # ------------------------------------------------------------------
    def _get_session(self) -> requests.Session:
        if not getattr(self._local, 'session', None):
            s = requests.Session()
            s.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            })
            s.proxies = {'http': None, 'https': None}
            self._local.session = s
        return self._local.session

    # ------------------------------------------------------------------
    # 页面获取
    # ------------------------------------------------------------------
    # 正常页面至少包含这些关键词，用于快速判断响应是否有效
    _VALID_PAGE_MARKERS = ('endpoint', 'openclaw', 'Page:')

    def fetch_page(self, page_num: int, retries: int = 3) -> Optional[str]:
        """获取指定页码的 HTML，失败最多重试 retries 次。"""
        url = self.base_url if page_num == 1 else f"{self.base_url}/page/{page_num}/"
        session = self._get_session()

        # 随机延迟，避免对服务器造成过大压力
        time.sleep(random.uniform(*self.delay_range))

        for attempt in range(1, retries + 1):
            try:
                logging.info(f"正在获取第 {page_num} 页（第 {attempt} 次）: {url}")
                resp = session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                resp.encoding = 'utf-8'
                html = resp.text

                # 快速有效性检查：响应太短或不含预期内容则视为无效页面
                if len(html) < 2000 or not any(m in html for m in self._VALID_PAGE_MARKERS):
                    logging.warning(
                        f"第 {page_num} 页响应异常 (长度={len(html)})，"
                        f"前200字符: {html[:200]!r}"
                    )
                    if attempt < retries:
                        time.sleep(2 ** attempt)
                        continue
                    return None

                return html
            except requests.RequestException as e:
                logging.warning(f"第 {page_num} 页第 {attempt} 次请求失败: {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)   # 指数退避
        logging.error(f"第 {page_num} 页获取彻底失败，跳过")
        return None

    # ------------------------------------------------------------------
    # 解析单行 <tr>
    # ------------------------------------------------------------------
    def _cell_text(self, cell) -> str:
        """提取单元格纯文本，去掉多余空白。"""
        return cell.get_text(' ', strip=True) if cell else ''

    def _extract_ip_port(self, endpoint_cell) -> str:
        """
        从 endpoint 单元格中可靠地提取完整 IP:PORT。

        优先级：
        1. <a class="endpoint" href="http://IP:PORT"> —— href 直接含完整地址（最可靠）
        2. data-real / data-ip / data-full-ip 属性
        3. title 属性
        4. 回退到单元格可见文本
        """
        # 最高优先级：<a class="endpoint" href="...">
        a_tag = endpoint_cell.find('a', class_='endpoint')
        if a_tag and a_tag.get('href'):
            href = a_tag['href'].strip()
            # href 格式通常是 "http://1.2.3.4:18789" 或 "http://1.2.3.4:18789/"
            m = re.search(r'https?://([^/\s]+)', href)
            if m:
                return m.group(1)   # 返回 IP:PORT

        # 次优先级：各种 data-* 属性
        for attr in ('data-real', 'data-ip', 'data-full-ip', 'data-original'):
            val = endpoint_cell.get(attr, '')
            if val and ':' in val:
                return val.strip()
            # 也检查子元素
            child = endpoint_cell.find(attrs={attr: True})
            if child:
                val = child[attr].strip()
                if ':' in val:
                    return val

        # title 属性
        title = endpoint_cell.get('title', '')
        if title and ':' in title:
            return title.strip()

        # 回退：可见文本（可能含遮挡字符，但聊胜于无）
        return self._cell_text(endpoint_cell)

    def parse_row(self, row) -> Optional[Dict]:
        """解析一行 <tr>，返回实例字典；跳过表头或空行。"""
        try:
            cells = row.find_all('td')
            if len(cells) < 2:
                return None

            # ---- IP:PORT ----
            ip_port = self._extract_ip_port(cells[0])
            if not ip_port:
                return None

            def ct(idx):
                return self._cell_text(cells[idx]) if idx < len(cells) else ''

            # ---- 国家：跳过 emoji flag，只取国家名 span ----
            country_cell = cells[2] if len(cells) > 2 else None
            country = ''
            if country_cell:
                name_span = country_cell.find('span', class_=re.compile(r'country.?name', re.I))
                country = name_span.get_text(strip=True) if name_span else self._cell_text(country_cell)

            instance = {
                'ip_port':            ip_port,
                'assistant_name':     ct(1),
                'country':            country,
                'auth_required':      ct(3),
                'is_active':          ct(4),
                'has_leaked_creds':   ct(5),
                'asn':                ct(6),
                'asn_name':           ct(7),
                'org':                ct(8),
                'first_seen':         ct(9),
                'last_seen':          ct(10),
                'asi_has_breach':     ct(11),
                'asi_has_threat_actor': ct(12),
                'asi_threat_actors':  ct(13),
                'asi_cves':           ct(14),
                'asi_enriched_at':    ct(15),
                'asi_domains':        ct(16),
            }

            # 统一清理占位符
            for k in instance:
                if instance[k] in ('-', '—', 'N/A'):
                    instance[k] = ''

            return instance

        except Exception as e:
            logging.debug(f"解析行失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 解析整页 HTML
    # ------------------------------------------------------------------
    def parse_page(self, html: str, page_num: int = 0) -> List[Dict]:
        """从 HTML 中解析所有实例行，返回列表。"""
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            if not table:
                logging.warning(
                    f"第 {page_num} 页未找到 <table>，跳过。"
                    f"响应长度={len(html)}，前300字符: {html[:300]!r}"
                )
                return results

            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            for row in rows:
                inst = self.parse_row(row)
                if inst:
                    results.append(inst)

            logging.debug(f"第 {page_num} 页解析到 {len(results)} 条")
        except Exception as e:
            logging.error(f"第 {page_num} 页解析失败: {e}")
        return results

    # ------------------------------------------------------------------
    # 获取总页数
    # ------------------------------------------------------------------
    def get_total_pages(self, html: str) -> int:
        """从首页 HTML 提取总页数。"""
        try:
            # 匹配 "Page: 1 / 2783" 或 "1 / 2783"
            match = re.search(r'Page:\s*\d+\s*/\s*(\d+)', html)
            if match:
                total = int(match.group(1))
                logging.info(f"检测到总页数: {total}")
                return total
            # 备用：找最大页码链接
            soup = BeautifulSoup(html, 'html.parser')
            page_links = soup.find_all('a', href=re.compile(r'/page/(\d+)'))
            if page_links:
                nums = [int(re.search(r'/page/(\d+)', a['href']).group(1))
                        for a in page_links if re.search(r'/page/(\d+)', a['href'])]
                if nums:
                    total = max(nums)
                    logging.info(f"从分页链接检测到总页数: {total}")
                    return total
        except Exception as e:
            logging.error(f"获取总页数失败: {e}")
        logging.warning("未能检测到总页数，默认为 1")
        return 1

    # ------------------------------------------------------------------
    # 并发爬取
    # ------------------------------------------------------------------
    def _fetch_and_parse(self, page_num: int):
        """获取并解析单页，供线程池调用。"""
        html = self.fetch_page(page_num)
        if not html:
            return page_num, []
        return page_num, self.parse_page(html, page_num)

    def scrape_all(self, max_pages: Optional[int] = None, start_page: int = 1):
        """
        并发爬取所有页面。

        Args:
            max_pages:  最大爬取页数，None 表示爬取全部
            start_page: 起始页码
        """
        # 先顺序获取首页（用于确定总页数）
        logging.info("获取首页以确定总页数…")
        first_html = self.fetch_page(1)
        if not first_html:
            logging.error("首页获取失败，爬取终止")
            return

        total_pages = self.get_total_pages(first_html)
        if max_pages:
            total_pages = min(total_pages, start_page - 1 + max_pages)

        logging.info(f"总页数: {total_pages}，并发线程: {self.max_workers}")

        # 把首页结果先放入列表
        if start_page == 1:
            page1_results = self.parse_page(first_html, 1)
            with self._instances_lock:
                self.instances.extend(page1_results)
            start_page = 2

        pages_to_fetch = list(range(start_page, total_pages + 1))
        completed = 0
        save_interval = 50   # 每完成 50 页保存一次

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {
                    executor.submit(self._fetch_and_parse, p): p
                    for p in pages_to_fetch
                }
                for future in as_completed(future_map):
                    try:
                        page_num, rows = future.result()
                        with self._instances_lock:
                            self.instances.extend(rows)
                        completed += 1
                        if completed % 10 == 0:
                            logging.info(
                                f"进度: {completed}/{len(pages_to_fetch)} 页完成，"
                                f"累计 {len(self.instances)} 条"
                            )
                        if completed % save_interval == 0:
                            self.save_data()
                    except Exception as e:
                        logging.error(f"某页处理异常: {e}")
        except KeyboardInterrupt:
            logging.info("检测到中断，保存当前数据…")

        self.save_data()
        logging.info(f"爬取完成！总共获取 {len(self.instances)} 条实例信息")

    # ------------------------------------------------------------------
    # 保存数据
    # ------------------------------------------------------------------
    def save_data(self):
        """保存数据，超过 10 万条自动分文件。"""
        with self._instances_lock:
            data = list(self.instances)   # 快照，避免长时间占锁

        if not data:
            logging.warning("暂无数据可保存")
            return

        records_per_file = 100_000
        total = len(data)
        num_files = (total + records_per_file - 1) // records_per_file

        for i in range(num_files):
            chunk = data[i * records_per_file:(i + 1) * records_per_file]
            suffix = '' if num_files == 1 else f'_part{i + 1}'
            json_path = f'openclaw_instances_{self.timestamp}{suffix}.json'
            csv_path  = f'openclaw_instances_{self.timestamp}{suffix}.csv'

            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
                logging.info(f"已保存 {json_path} ({len(chunk)} 条)")
            except Exception as e:
                logging.error(f"保存 JSON 失败: {e}")

            try:
                if chunk:
                    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=chunk[0].keys())
                        writer.writeheader()
                        writer.writerows(chunk)
                    logging.info(f"已保存 {csv_path} ({len(chunk)} 条)")
            except Exception as e:
                logging.error(f"保存 CSV 失败: {e}")

        logging.info(f"保存完成，共 {num_files} 个文件，{total} 条记录")

    # ------------------------------------------------------------------
    # 便捷：只爬取一页（调试用）
    # ------------------------------------------------------------------
    def scrape_page(self, page_num: int = 1) -> List[Dict]:
        html = self.fetch_page(page_num)
        if not html:
            return []
        results = self.parse_page(html, page_num)
        self.instances.extend(results)
        return results


# ======================================================================
# 保留与旧 selenium 版兼容的别名，以免其他脚本 import 报错
# ======================================================================
OpenClawScraperSelenium = OpenClawScraper


def main():
    """主函数"""
    print("=" * 60)
    print("OpenClaw 实例信息爬虫（纯 requests + 并发版）")
    print("=" * 60)
    print()

    # 并发线程数
    while True:
        w = input("并发线程数（默认 8，建议 4-16）: ").strip()
        if not w:
            max_workers = 8
            break
        if w.isdigit() and int(w) > 0:
            max_workers = int(w)
            break
        print("请输入正整数")

    # 爬取页数
    while True:
        p = input("爬取页数（输入 all 爬全部，默认 10）: ").strip()
        if not p:
            max_pages = 10
            break
        if p.lower() == 'all':
            max_pages = None
            break
        if p.isdigit() and int(p) > 0:
            max_pages = int(p)
            break
        print("请输入正整数或 all")

    print()
    print(f"开始爬取（线程数={max_workers}，页数={'全部' if max_pages is None else max_pages}）…")
    print()

    scraper = OpenClawScraper(max_workers=max_workers)
    scraper.scrape_all(max_pages=max_pages)

    print()
    print("爬取任务完成！")


if __name__ == "__main__":
    main()
