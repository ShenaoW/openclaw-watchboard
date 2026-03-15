import crypto from 'crypto';
import path from 'path';
import sqlite3 from 'sqlite3';

interface PageViewRecordInput {
  pagePath: string;
  clientIp: string;
  userAgent?: string;
  referer?: string;
  recordedAt?: string;
  importedFrom?: string;
  sourceHash?: string;
}

interface AnalyticsSummary {
  totalPageViews: number;
  totalUniqueVisitors: number;
  firstRecordedAt: string | null;
  lastRecordedAt: string | null;
}

class AnalyticsService {
  private readonly dbPath = path.join(__dirname, '../../../data/analytics.db');
  private readonly readyPromise: Promise<void>;

  constructor() {
    this.readyPromise = this.initialize().catch((error) => {
      console.error('Failed to initialize analytics database', error);
    });
  }

  private async withDatabase<T>(handler: (db: sqlite3.Database) => Promise<T>): Promise<T> {
    const db = await new Promise<sqlite3.Database>((resolve, reject) => {
      const database = new sqlite3.Database(this.dbPath, (error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve(database);
      });
    });

    try {
      return await handler(db);
    } finally {
      await new Promise<void>((resolve, reject) => {
        db.close((error) => {
          if (error) {
            reject(error);
            return;
          }

          resolve();
        });
      });
    }
  }

  private run(db: sqlite3.Database, sql: string, params: Array<string | number | null> = []) {
    return new Promise<{ lastID: number; changes: number }>((resolve, reject) => {
      db.run(sql, params, function runCallback(error) {
        if (error) {
          reject(error);
          return;
        }

        resolve({
          lastID: this.lastID,
          changes: this.changes,
        });
      });
    });
  }

  private get<T>(db: sqlite3.Database, sql: string, params: Array<string | number | null> = []) {
    return new Promise<T | undefined>((resolve, reject) => {
      db.get(sql, params, (error, row) => {
        if (error) {
          reject(error);
          return;
        }

        resolve(row as T | undefined);
      });
    });
  }

  private async initialize() {
    await this.withDatabase(async (db) => {
      await this.run(
        db,
        `
        CREATE TABLE IF NOT EXISTS analytics_page_views (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          recorded_at TEXT NOT NULL,
          page_path TEXT NOT NULL,
          client_ip TEXT NOT NULL,
          user_agent TEXT,
          referer TEXT,
          imported_from TEXT,
          source_hash TEXT UNIQUE
        )
        `,
      );

      await this.run(
        db,
        `
        CREATE TABLE IF NOT EXISTS analytics_visitors (
          client_ip TEXT PRIMARY KEY,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          visit_count INTEGER NOT NULL DEFAULT 1,
          last_path TEXT
        )
        `,
      );

      await this.run(
        db,
        `
        CREATE TABLE IF NOT EXISTS analytics_daily_visitors (
          day TEXT NOT NULL,
          client_ip TEXT NOT NULL,
          first_seen_at TEXT NOT NULL,
          PRIMARY KEY (day, client_ip)
        )
        `,
      );

      await this.run(
        db,
        `
        CREATE TABLE IF NOT EXISTS analytics_daily_stats (
          day TEXT PRIMARY KEY,
          page_views INTEGER NOT NULL DEFAULT 0,
          unique_visitors INTEGER NOT NULL DEFAULT 0,
          last_seen_at TEXT NOT NULL
        )
        `,
      );
    });
  }

  private createSourceHash(input: PageViewRecordInput) {
    if (input.sourceHash) {
      return input.sourceHash;
    }

    if (!input.importedFrom) {
      return null;
    }

    return crypto
      .createHash('sha1')
      .update([
        input.importedFrom,
        input.recordedAt || '',
        input.clientIp,
        input.pagePath,
        input.userAgent || '',
        input.referer || '',
      ].join('|'))
      .digest('hex');
  }

  async recordPageView(input: PageViewRecordInput) {
    await this.readyPromise;

    const recordedAt = input.recordedAt || new Date().toISOString();
    const day = recordedAt.slice(0, 10);
    const sourceHash = this.createSourceHash({ ...input, recordedAt });

    return this.withDatabase(async (db) => {
      await this.run(db, 'BEGIN TRANSACTION');

      try {
        const insertResult = await this.run(
          db,
          `
          INSERT OR IGNORE INTO analytics_page_views (
            recorded_at, page_path, client_ip, user_agent, referer, imported_from, source_hash
          ) VALUES (?, ?, ?, ?, ?, ?, ?)
          `,
          [
            recordedAt,
            input.pagePath,
            input.clientIp,
            input.userAgent || null,
            input.referer || null,
            input.importedFrom || null,
            sourceHash,
          ],
        );

        if (insertResult.changes === 0) {
          await this.run(db, 'ROLLBACK');
          return { inserted: false };
        }

        const existingVisitor = await this.get<{ client_ip: string }>(
          db,
          'SELECT client_ip FROM analytics_visitors WHERE client_ip = ?',
          [input.clientIp],
        );

        if (existingVisitor) {
          await this.run(
            db,
            `
            UPDATE analytics_visitors
            SET last_seen_at = ?, visit_count = visit_count + 1, last_path = ?
            WHERE client_ip = ?
            `,
            [recordedAt, input.pagePath, input.clientIp],
          );
        } else {
          await this.run(
            db,
            `
            INSERT INTO analytics_visitors (
              client_ip, first_seen_at, last_seen_at, visit_count, last_path
            ) VALUES (?, ?, ?, 1, ?)
            `,
            [input.clientIp, recordedAt, recordedAt, input.pagePath],
          );
        }

        const dailyVisitorInsert = await this.run(
          db,
          `
          INSERT OR IGNORE INTO analytics_daily_visitors (day, client_ip, first_seen_at)
          VALUES (?, ?, ?)
          `,
          [day, input.clientIp, recordedAt],
        );

        await this.run(
          db,
          `
          INSERT INTO analytics_daily_stats (day, page_views, unique_visitors, last_seen_at)
          VALUES (?, 1, ?, ?)
          ON CONFLICT(day) DO UPDATE SET
            page_views = page_views + 1,
            unique_visitors = unique_visitors + excluded.unique_visitors,
            last_seen_at = excluded.last_seen_at
          `,
          [day, dailyVisitorInsert.changes > 0 ? 1 : 0, recordedAt],
        );

        await this.run(db, 'COMMIT');
        return { inserted: true };
      } catch (error) {
        await this.run(db, 'ROLLBACK');
        throw error;
      }
    });
  }

  async getSummary(): Promise<AnalyticsSummary> {
    await this.readyPromise;

    return this.withDatabase(async (db) => {
      const summary = await this.get<AnalyticsSummary>(
        db,
        `
        SELECT
          (SELECT COUNT(*) FROM analytics_page_views) AS totalPageViews,
          (SELECT COUNT(*) FROM analytics_visitors) AS totalUniqueVisitors,
          (SELECT MIN(recorded_at) FROM analytics_page_views) AS firstRecordedAt,
          (SELECT MAX(recorded_at) FROM analytics_page_views) AS lastRecordedAt
        `,
      );

      return {
        totalPageViews: summary?.totalPageViews || 0,
        totalUniqueVisitors: summary?.totalUniqueVisitors || 0,
        firstRecordedAt: summary?.firstRecordedAt || null,
        lastRecordedAt: summary?.lastRecordedAt || null,
      };
    });
  }
}

export const analyticsService = new AnalyticsService();
