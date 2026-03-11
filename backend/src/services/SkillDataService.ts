import path from 'path';
import sqlite3 from 'sqlite3';

type QueryValue = string | number | null;

class SkillDataService {
  private dbPath = path.join(__dirname, '../../../data/skills.db');

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

  private normalizeSource(source?: string) {
    if (!source) {
      return 'other';
    }
    if (source.startsWith('skillsmp')) {
      return 'skillsmp';
    }
    return source;
  }

  private normalizeClassification(classification?: string) {
    if (!classification) {
      return 'unknown';
    }
    return classification;
  }

  private parseJsonArray(value?: string | null) {
    if (!value) {
      return [];
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  private mapSkillRow(row: any) {
    return {
      id: row.id,
      name: row.name,
      version: row.version || '1.0.0',
      description: row.description || '',
      category: row.category || 'Uncategorized',
      maintainer: row.maintainer || 'Unknown',
      downloads: Number(row.downloads || 0),
      rating: Number(row.rating || 0),
      verified: Boolean(row.verified),
      lastUpdated: row.last_updated,
      securityScore: Number(row.security_score || 0),
      permissions: this.parseJsonArray(row.permissions),
      repository: row.repository || '',
      source: this.normalizeSource(row.source),
      classification: this.normalizeClassification(row.classification),
      fileStructure: this.parseJsonArray(row.file_structure),
      dependencies: this.parseJsonArray(row.dependencies),
      skillContent: row.skill_content || '',
    };
  }

  async getStats() {
    const [stats] = await this.query<any>(
      `
      SELECT *
      FROM skill_stats
      ORDER BY generated_at DESC, id DESC
      LIMIT 1
      `,
    );

    if (!stats) {
      throw new Error('No skill statistics found in database');
    }

    const developerStats = await this.query<any>(
      `
      SELECT developer, total_skills, safe_skills, suspicious_skills
      FROM developer_stats
      ORDER BY total_skills DESC
      LIMIT 10
      `,
    );

    const categoryStats = await this.query<any>(
      `
      SELECT category, skill_count, percentage
      FROM category_stats
      ORDER BY skill_count DESC
      LIMIT 12
      `,
    );

    const popularRows = await this.query<any>(
      `
      SELECT source, name, downloads, rating, classification
      FROM skills
      ORDER BY security_score DESC, downloads DESC, rating DESC
      LIMIT 60
      `,
    );

    const popularSkillsBySource: Record<string, any[]> = {
      clawhub: [],
      'skills.rest': [],
      skillsmp: [],
      other: [],
    };

    for (const row of popularRows) {
      const source = this.normalizeSource(row.source);
      if (popularSkillsBySource[source]?.length >= 5) {
        continue;
      }

      popularSkillsBySource[source] ||= [];
      popularSkillsBySource[source].push({
        name: row.name,
        downloads: Number(row.downloads || 0),
        rating: Number(row.rating || 0),
        classification: this.normalizeClassification(row.classification),
      });
    }

    return {
      totalSkills: stats.total_skills,
      sourceDistribution: {
        clawhub: stats.source_clawhub,
        skillsRest: stats.source_skills_rest,
        skillsmp: stats.source_skillsmp,
        other: Math.max(
          stats.total_skills - stats.source_clawhub - stats.source_skills_rest - stats.source_skillsmp,
          0,
        ),
      },
      securityDistribution: {
        safe: stats.classification_safe,
        suspicious: stats.classification_suspicious,
        malicious: stats.classification_malicious || 0,
        unknown: stats.classification_unknown,
      },
      topDevelopers: developerStats.map((row) => ({
        developer: row.developer,
        skillCount: row.total_skills,
        safeCount: row.safe_skills,
        suspiciousCount: row.suspicious_skills,
        maliciousCount: row.malicious_skills || 0,
      })),
      topCategories: categoryStats.map((row) => ({
        category: row.category,
        count: row.skill_count,
        percentage: row.percentage,
      })),
      popularSkillsBySource,
    };
  }

  async getSkills(filters: {
    classification?: string;
    source?: string;
    category?: string;
    search?: string;
    page?: number;
    limit?: number;
  }) {
    const where: string[] = [];
    const params: QueryValue[] = [];

    if (filters.classification) {
      where.push('classification = ?');
      params.push(filters.classification);
    }

    if (filters.source) {
      if (filters.source === 'skillsmp') {
        where.push(`source LIKE 'skillsmp%'`);
      } else {
        where.push('source = ?');
        params.push(filters.source);
      }
    }

    if (filters.category) {
      where.push('category = ?');
      params.push(filters.category);
    }

    if (filters.search) {
      const term = `%${filters.search}%`;
      where.push('(name LIKE ? OR description LIKE ? OR maintainer LIKE ? OR repository LIKE ?)');
      params.push(term, term, term, term);
    }

    const whereClause = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const page = Math.max(filters.page || 1, 1);
    const limit = Math.min(Math.max(filters.limit || 20, 1), 100);
    const offset = (page - 1) * limit;

    const [countResult] = await this.query<any>(
      `SELECT COUNT(*) as total FROM skills ${whereClause}`,
      params,
    );

    const rows = await this.query<any>(
      `
      SELECT *
      FROM skills
      ${whereClause}
      ORDER BY
        CASE WHEN classification IN ('suspicious', 'malicious') THEN security_score END ASC,
        CASE WHEN classification = 'safe' THEN security_score END DESC,
        downloads DESC,
        rating DESC
      LIMIT ? OFFSET ?
      `,
      [...params, limit, offset],
    );

    return {
      skills: rows.map((row) => this.mapSkillRow(row)),
      pagination: {
        page,
        limit,
        total: countResult?.total || 0,
        totalPages: Math.ceil((countResult?.total || 0) / limit),
      },
    };
  }

  async getTrustedSkills(filters: any) {
    return this.getSkills({ ...filters, classification: 'safe' });
  }

  async getSuspiciousSkills(filters: any) {
    return this.getSkills({ ...filters, classification: 'suspicious' });
  }

  async getMaliciousSkills(filters: any) {
    return this.getSkills({ ...filters, classification: 'malicious' });
  }

  async getSkillById(skillId: string) {
    const [row] = await this.query<any>(
      `
      SELECT *
      FROM skills
      WHERE id = ? OR name = ?
      LIMIT 1
      `,
      [skillId, skillId],
    );

    return row ? this.mapSkillRow(row) : null;
  }
}

export const skillDataService = new SkillDataService();
