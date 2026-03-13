import path from 'path';
import sqlite3 from 'sqlite3';

type QueryValue = string | number | null;

const STAGE_NAME_MAP: Record<string, string> = {
  'Gateway Authorization & Routing Stage': '网关鉴权与路由',
  'Authentication & Authorization Decision Stage': '网关鉴权与路由',
  'Auth State': '网关鉴权与路由',
  'Resource Access Stage': '工具与技能执行',
  'Execution Stage': '工具与技能执行',
  'Persistence & Output Presentation Stage': '消息回传与持久化',
  'Input Ingress Stage': '消息输入与通道适配',
};

class RiskDatabaseService {
  private dbPath = path.join(__dirname, '../../../data/risks.db');

  private query<T = any>(sql: string, params: QueryValue[] = []): Promise<T[]> {
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(this.dbPath);
      db.all(sql, params, (err, rows) => {
        db.close();
        if (err) {
          reject(err);
          return;
        }
        resolve(rows as T[]);
      });
    });
  }

  private parseCsvString(value?: string | null) {
    if (!value) {
      return [];
    }
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  private normalizeStage(value?: string | null) {
    const cleaned = value?.trim() || '';
    return STAGE_NAME_MAP[cleaned] || cleaned;
  }

  async getVulnerabilities() {
    const rows = await this.query<any>(
      `
      SELECT *
      FROM vulnerabilities
      ORDER BY
        CASE vulnerability_nature_id
          WHEN 'llm_system_specific' THEN 0
          ELSE 1
        END,
        CASE WHEN top10_rank IS NULL OR top10_rank = 0 THEN 999 ELSE top10_rank END,
        CASE severity
          WHEN 'Critical' THEN 0
          WHEN 'High' THEN 1
          WHEN 'Moderate' THEN 2
          WHEN 'Low' THEN 3
          ELSE 4
        END,
        source_index ASC
      `,
    );

    const [summary] = await this.query<any>(
      `
      SELECT *
      FROM vulnerability_summary
      ORDER BY generated_at DESC, id DESC
      LIMIT 1
      `,
    );

    return {
      total: summary?.total_count || rows.length,
      summary: {
        llmSpecific: summary?.llm_specific_count || 0,
        generalSoftware: summary?.general_software_count || 0,
        mappedTop10: summary?.mapped_top10_count || 0,
      },
      vulnerabilities: rows.map((row) => ({
        index: Number(row.source_index || 0),
        title: row.vulnerability_title || '',
        stage: this.normalizeStage(row.stage),
        reason: row.reason || '',
        vulnerabilityId: row.vulnerability_id || '',
        severity: row.severity || '',
        affectedVersions: row.affected_versions || '',
        cve: row.cve || '',
        cwe: row.cwe || '',
        link: row.vulnerability_link || '',
        vulnerabilityNatureId: row.vulnerability_nature_id || '',
        vulnerabilityNatureLabel: row.vulnerability_nature_label || '',
        top10PrimaryId: row.top10_primary_id || '',
        top10PrimaryLabel: row.top10_primary_label || '',
        top10MatchIds: this.parseCsvString(row.top10_match_ids),
        top10MatchLabels: this.parseCsvString(row.top10_match_labels),
        top10Rank: row.top10_rank ? Number(row.top10_rank) : null,
        top10MatchCount: Number(row.top10_match_count || 0),
        mappingConfidence: Number(row.mapping_confidence || 0),
        analysisReason: row.analysis_reason || '',
      })),
    };
  }
}

export default RiskDatabaseService;
