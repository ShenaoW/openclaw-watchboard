#!/usr/bin/env python3

import argparse
import hashlib
import os
import re
import sqlite3
from datetime import datetime, timezone

LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
)


def parse_args():
    parser = argparse.ArgumentParser(description='Import Nginx access logs into analytics.db')
    parser.add_argument('logs', nargs='+', help='Nginx access log files to import')
    parser.add_argument(
        '--db',
        default=os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics.db'),
        help='Path to analytics SQLite database',
    )
    parser.add_argument(
        '--source-label',
        default='nginx-access-log',
        help='Source label written into imported_from',
    )
    return parser.parse_args()


def ensure_schema(conn):
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS analytics_page_views (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          recorded_at TEXT NOT NULL,
          page_path TEXT NOT NULL,
          client_ip TEXT NOT NULL,
          user_agent TEXT,
          referer TEXT,
          imported_from TEXT,
          source_hash TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS analytics_visitors (
          client_ip TEXT PRIMARY KEY,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          visit_count INTEGER NOT NULL DEFAULT 1,
          last_path TEXT
        );

        CREATE TABLE IF NOT EXISTS analytics_daily_visitors (
          day TEXT NOT NULL,
          client_ip TEXT NOT NULL,
          first_seen_at TEXT NOT NULL,
          PRIMARY KEY (day, client_ip)
        );

        CREATE TABLE IF NOT EXISTS analytics_daily_stats (
          day TEXT PRIMARY KEY,
          page_views INTEGER NOT NULL DEFAULT 0,
          unique_visitors INTEGER NOT NULL DEFAULT 0,
          last_seen_at TEXT NOT NULL
        );
        '''
    )


def should_track(method, path, status):
    if method != 'GET':
        return False
    if status >= 400:
        return False
    return path == '/' or path == '/home'


def normalize_timestamp(raw_timestamp):
    parsed = datetime.strptime(raw_timestamp, '%d/%b/%Y:%H:%M:%S %z')
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def import_logs(conn, log_paths, source_label):
    inserted = 0

    for log_path in log_paths:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue

                match = LOG_PATTERN.match(line)
                if not match:
                    continue

                method = match.group('method')
                path = match.group('path')
                status = int(match.group('status'))

                if not should_track(method, path, status):
                    continue

                recorded_at = normalize_timestamp(match.group('timestamp'))
                client_ip = match.group('ip')
                user_agent = match.group('user_agent')
                referer = match.group('referer')
                imported_from = f'{source_label}:{os.path.basename(log_path)}'
                source_hash = hashlib.sha1(line.encode('utf-8')).hexdigest()
                day = recorded_at[:10]

                cursor = conn.execute(
                    '''
                    INSERT OR IGNORE INTO analytics_page_views (
                      recorded_at, page_path, client_ip, user_agent, referer, imported_from, source_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (recorded_at, path, client_ip, user_agent, referer, imported_from, source_hash),
                )

                if cursor.rowcount == 0:
                    continue

                inserted += 1
                visitor_exists = conn.execute(
                    'SELECT 1 FROM analytics_visitors WHERE client_ip = ?',
                    (client_ip,),
                ).fetchone()

                if visitor_exists:
                    conn.execute(
                        '''
                        UPDATE analytics_visitors
                        SET last_seen_at = ?, visit_count = visit_count + 1, last_path = ?
                        WHERE client_ip = ?
                        ''',
                        (recorded_at, path, client_ip),
                    )
                else:
                    conn.execute(
                        '''
                        INSERT INTO analytics_visitors (
                          client_ip, first_seen_at, last_seen_at, visit_count, last_path
                        ) VALUES (?, ?, ?, 1, ?)
                        ''',
                        (client_ip, recorded_at, recorded_at, path),
                    )

                daily_cursor = conn.execute(
                    '''
                    INSERT OR IGNORE INTO analytics_daily_visitors (day, client_ip, first_seen_at)
                    VALUES (?, ?, ?)
                    ''',
                    (day, client_ip, recorded_at),
                )

                conn.execute(
                    '''
                    INSERT INTO analytics_daily_stats (day, page_views, unique_visitors, last_seen_at)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(day) DO UPDATE SET
                      page_views = page_views + 1,
                      unique_visitors = unique_visitors + excluded.unique_visitors,
                      last_seen_at = excluded.last_seen_at
                    ''',
                    (day, 1 if daily_cursor.rowcount > 0 else 0, recorded_at),
                )

    return inserted


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    conn = sqlite3.connect(args.db)

    try:
        ensure_schema(conn)
        inserted = import_logs(conn, args.logs, args.source_label)
        conn.commit()
        print(f'Imported {inserted} page views into {args.db}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
