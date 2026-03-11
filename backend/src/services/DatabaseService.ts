import sqlite3 from 'sqlite3';
import path from 'path';

export class DatabaseService {
  private dbPath: string;

  constructor() {
    this.dbPath = path.join(__dirname, '../../../data/skills.db');
  }

  async query(sql: string, params: any[] = []): Promise<any[]> {
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(this.dbPath);

      db.all(sql, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });

      db.close();
    });
  }

  async getSkillStats() {
    const stats = await this.query(`
      SELECT * FROM skill_stats
      ORDER BY generated_at DESC
      LIMIT 1
    `);

    const developerStats = await this.query(`
      SELECT * FROM developer_stats
      ORDER BY total_skills DESC
      LIMIT 10
    `);

    const categoryStats = await this.query(`
      SELECT * FROM category_stats
      ORDER BY skill_count DESC
    `);

    // 获取各源流行技能
    const popularSkillsBySource = {
      clawhub: await this.query(`
        SELECT name, downloads, rating, classification
        FROM skills
        WHERE source = 'clawhub'
        ORDER BY security_score DESC, downloads DESC
        LIMIT 10
      `),
      'skills.rest': await this.query(`
        SELECT name, downloads, rating, classification
        FROM skills
        WHERE source = 'skills.rest'
        ORDER BY security_score DESC, downloads DESC
        LIMIT 10
      `),
      skillsmp: await this.query(`
        SELECT name, downloads, rating, classification
        FROM skills
        WHERE source LIKE 'skillsmp%'
        ORDER BY security_score DESC, downloads DESC
        LIMIT 10
      `)
    };

    if (stats.length === 0) {
      throw new Error('No statistics found in database');
    }

    const stat = stats[0];
    return {
      totalSkills: stat.total_skills,
      sourceDistribution: {
        clawhub: stat.source_clawhub,
        skillsRest: stat.source_skills_rest,
        skillsmp: stat.source_skillsmp,
        other: 0
      },
      securityDistribution: {
        safe: stat.classification_safe,
        suspicious: stat.classification_suspicious,
        unknown: stat.classification_unknown
      },
      topDevelopers: developerStats.map((dev: any) => ({
        developer: dev.developer,
        skillCount: dev.total_skills,
        safeCount: dev.safe_skills,
        suspiciousCount: dev.suspicious_skills
      })),
      topCategories: categoryStats.map((cat: any) => ({
        category: cat.category,
        count: cat.skill_count,
        percentage: cat.percentage
      })),
      popularSkillsBySource
    };
  }

  async getAllSkills(filters: any) {
    let whereConditions = [];
    let params = [];

    if (filters.classification) {
      whereConditions.push(`classification = ?`);
      params.push(filters.classification);
    }

    if (filters.source) {
      whereConditions.push(`source = ?`);
      params.push(filters.source);
    }

    if (filters.category) {
      whereConditions.push(`category = ?`);
      params.push(filters.category);
    }

    if (filters.search) {
      whereConditions.push(`(name LIKE ? OR description LIKE ? OR maintainer LIKE ?)`);
      const searchTerm = `%${filters.search}%`;
      params.push(searchTerm, searchTerm, searchTerm);
    }

    const whereClause = whereConditions.length > 0 ? 'WHERE ' + whereConditions.join(' AND ') : '';

    // 获取总数
    const countQuery = `SELECT COUNT(*) as total FROM skills ${whereClause}`;
    const countResult = await this.query(countQuery, params);
    const total = countResult[0].total;

    // 获取分页数据
    const page = filters.page || 1;
    const limit = filters.limit || 20;
    const offset = (page - 1) * limit;

    const dataQuery = `
      SELECT id, name, version, description, category, maintainer, downloads,
             rating, verified, last_updated, security_score, permissions,
             repository, source, classification
      FROM skills ${whereClause}
      ORDER BY security_score DESC, downloads DESC
      LIMIT ? OFFSET ?
    `;

    const skills = await this.query(dataQuery, [...params, limit, offset]);

    return {
      skills: skills.map((skill: any) => ({
        ...skill,
        permissions: JSON.parse(skill.permissions || '[]'),
        verified: Boolean(skill.verified),
        lastUpdated: skill.last_updated
      })),
      total
    };
  }

  async getSkillById(skillId: string) {
    const skills = await this.query(
      'SELECT * FROM skills WHERE id = ?',
      [skillId]
    );

    if (skills.length === 0) {
      return null;
    }

    const skill = skills[0];
    return {
      ...skill,
      permissions: JSON.parse(skill.permissions || '[]'),
      verified: Boolean(skill.verified),
      dependencies: JSON.parse(skill.dependencies || '[]'),
      fileStructure: JSON.parse(skill.file_structure || '[]'),
      lastUpdated: skill.last_updated
    };
  }
}