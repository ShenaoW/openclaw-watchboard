import path from 'path';
import sqlite3 from 'sqlite3';

type QueryValue = string | number | null;

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

class ExposureDatabaseService {
  private dbPath = path.join(__dirname, '../../../data/exposure.db');

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

  private parseJsonArray(value?: string | null): string[] {
    if (!value) {
      return [];
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
    } catch {
      return [];
    }
  }

  async getOverview() {
    const [summary] = await this.query<any>(
      `
      SELECT *
      FROM exposure_summary
      ORDER BY generated_at DESC, id DESC
      LIMIT 1
      `,
    );

    if (!summary) {
      throw new Error('No exposure summary found in database');
    }

    const topCountries = await this.query<any>(
      `
      SELECT country_name, count, critical_count, high_count, medium_count, low_count
      FROM exposure_country_stats
      ORDER BY count DESC
      LIMIT 5
      `,
    );

    const topPorts = await this.query<any>(
      `
      SELECT port, service, count, risk
      FROM exposure_port_stats
      ORDER BY count DESC
      LIMIT 5
      `,
    );

    const [chinaStats] = await this.query<any>(
      `
      SELECT
        COUNT(*) as total_china_instances,
        SUM(CASE WHEN runtime_status = 'Active' THEN 1 ELSE 0 END) as active_china_instances,
        COUNT(DISTINCT CASE WHEN province IS NOT NULL AND trim(province) != '' THEN province END) as province_count,
        COUNT(DISTINCT CASE WHEN cn_city IS NOT NULL AND trim(cn_city) != '' THEN cn_city END) as city_count
      FROM exposure_instances
      WHERE is_china_instance = 'Yes'
      `,
    );

    return {
      totalExposedServices: summary.total_instances,
      activeInstances: summary.active_instances || 0,
      chinaExposedServices: chinaStats?.total_china_instances || 0,
      chinaActiveInstances: chinaStats?.active_china_instances || 0,
      provinceCount: chinaStats?.province_count || 0,
      cityCount: chinaStats?.city_count || 0,
      criticalExposures: summary.critical_count,
      highRiskExposures: summary.high_count,
      mediumRiskExposures: summary.medium_count,
      lowRiskExposures: summary.low_count,
      lastScanTime: summary.last_scan_time,
      topCountries: topCountries.map((country) => ({
        country: country.country_name,
        count: country.count,
      })),
      topPorts: topPorts.map((port) => ({
        port: port.port,
        service: port.service,
        count: port.count,
        risk: port.risk,
      })),
    };
  }

  async getServices(filters: {
    status?: string;
    runtimeStatus?: string;
    chinaScope?: string;
    versionStatus?: string;
    country?: string;
    isp?: string;
    credentialsLeaked?: string;
    search?: string;
    page?: number;
    limit?: number;
  }) {
    const where: string[] = [];
    const params: QueryValue[] = [];

    if (filters.status) {
      where.push('status = ?');
      params.push(filters.status);
    }

    if (filters.runtimeStatus) {
      where.push('runtime_status = ?');
      params.push(filters.runtimeStatus);
    }

    if (filters.chinaScope === 'china') {
      where.push(`is_china_instance = 'Yes'`);
    }

    if (filters.chinaScope === 'overseas') {
      where.push(`(is_china_instance IS NULL OR is_china_instance != 'Yes')`);
    }

    if (filters.versionStatus === 'detected') {
      where.push(`server_version IS NOT NULL AND trim(server_version) != ''`);
    }

    if (filters.versionStatus === 'undetected') {
      where.push(`(server_version IS NULL OR trim(server_version) = '')`);
    }

    if (filters.country) {
      where.push('country_name LIKE ?');
      params.push(`%${filters.country}%`);
    }

    if (filters.isp) {
      where.push('isp LIKE ?');
      params.push(`%${filters.isp}%`);
    }

    if (filters.credentialsLeaked) {
      where.push('credentials_leaked = ?');
      params.push(filters.credentialsLeaked);
    }

    if (filters.search) {
      where.push('(ip LIKE ? OR assistant_name LIKE ? OR country_name LIKE ? OR organization LIKE ? OR domains LIKE ?)');
      const term = `%${filters.search}%`;
      params.push(term, term, term, term, term);
    }

    const whereClause = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const page = Math.max(filters.page || 1, 1);
    const limit = Math.min(Math.max(filters.limit || 20, 1), 100);
    const offset = (page - 1) * limit;

    const [countResult] = await this.query<any>(
      `SELECT COUNT(*) as total FROM exposure_instances ${whereClause}`,
      params,
    );

    const rows = await this.query<any>(
      `
      SELECT *
      FROM exposure_instances
      ${whereClause}
      ORDER BY
        CASE risk_level
          WHEN 'Critical' THEN 1
          WHEN 'High' THEN 2
          WHEN 'Medium' THEN 3
          ELSE 4
        END,
        risk_score DESC,
        last_seen DESC
      LIMIT ? OFFSET ?
      `,
      [...params, limit, offset],
    );

    const total = countResult?.total || 0;

    return {
      services: rows.map((row, index) => ({
        id: `${row.ip_port}-${offset + index}`,
        ip: row.ip,
        hostname: row.assistant_name || null,
        port: row.port,
        service: row.service,
        banner: row.assistant_name ? `OpenClaw Assistant: ${row.assistant_name}` : 'OpenClaw service',
        country: row.country_name,
        city: row.organization || '-',
        asn: row.asn,
        organization: row.organization,
        isp: row.isp,
        runtimeStatus: row.runtime_status || 'Unknown',
        serverVersion: row.server_version || null,
        isChinaInstance: row.is_china_instance === 'Yes',
        province: row.province || null,
        cnCity: row.cn_city || null,
        lastSeen: row.last_seen,
        firstSeen: row.first_seen,
        status: row.status,
        authenticated: row.authenticated,
        active: row.active,
        credentialsLeaked: row.credentials_leaked,
        hasMcp: row.has_mcp,
        aptGroups: this.parseJsonArray(row.apt_groups).join(', '),
        domains: this.parseJsonArray(row.domains).join(', '),
      })),
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      } satisfies Pagination,
    };
  }

  async getGeographicDistribution() {
    const world = await this.query<any>(
      `
      SELECT country_name, count, critical_count, high_count, medium_count, low_count
      FROM exposure_country_stats
      ORDER BY count DESC
      LIMIT 20
      `,
    );

    const provinces = await this.query<any>(
      `
      SELECT province, city, count
      FROM exposure_province_stats
      WHERE province IS NOT NULL AND province != ''
      ORDER BY count DESC
      LIMIT 50
      `,
    );

    const coordinates: Record<string, { code: string; lat: number; lng: number }> = {
      'China mainland': { code: 'CHN', lat: 35.8617, lng: 104.1954 },
      'United States': { code: 'USA', lat: 37.0902, lng: -95.7129 },
      Singapore: { code: 'SGP', lat: 1.3521, lng: 103.8198 },
      Germany: { code: 'DEU', lat: 51.1657, lng: 10.4515 },
      'Hong Kong': { code: 'HKG', lat: 22.3193, lng: 114.1694 },
      Japan: { code: 'JPN', lat: 36.2048, lng: 138.2529 },
      Russia: { code: 'RUS', lat: 61.524, lng: 105.3188 },
      Canada: { code: 'CAN', lat: 56.1304, lng: -106.3468 },
      France: { code: 'FRA', lat: 46.2276, lng: 2.2137 },
      Netherlands: { code: 'NLD', lat: 52.1326, lng: 5.2913 },
    };

    const provinceCoordinates: Record<string, { lat: number; lng: number }> = {
      Beijing: { lat: 39.9042, lng: 116.4074 },
      Shanghai: { lat: 31.2304, lng: 121.4737 },
      Tianjin: { lat: 39.3434, lng: 117.3616 },
      Chongqing: { lat: 29.4316, lng: 106.9123 },
      Guangdong: { lat: 23.379, lng: 113.7633 },
      Zhejiang: { lat: 29.1832, lng: 120.0934 },
      Jiangsu: { lat: 32.9711, lng: 119.455 },
      Shandong: { lat: 36.6683, lng: 117.0204 },
      Sichuan: { lat: 30.6517, lng: 104.0759 },
      Hubei: { lat: 30.9756, lng: 112.2707 },
      Hunan: { lat: 27.6104, lng: 111.7088 },
      Henan: { lat: 34.7657, lng: 113.7532 },
      Hebei: { lat: 38.0428, lng: 114.5149 },
      Fujian: { lat: 26.0998, lng: 119.2965 },
      Anhui: { lat: 31.8612, lng: 117.2857 },
      Jiangxi: { lat: 28.6765, lng: 115.8922 },
      Shaanxi: { lat: 34.3416, lng: 108.9398 },
      Liaoning: { lat: 41.8057, lng: 123.4315 },
      Jilin: { lat: 43.8171, lng: 125.3235 },
      Heilongjiang: { lat: 45.8038, lng: 126.5349 },
      Guangxi: { lat: 22.815, lng: 108.3275 },
      Yunnan: { lat: 25.0458, lng: 102.7103 },
      Guizhou: { lat: 26.647, lng: 106.6302 },
      Gansu: { lat: 36.0611, lng: 103.8343 },
      Shanxi: { lat: 37.8706, lng: 112.5489 },
      InnerMongolia: { lat: 40.8174, lng: 111.7652 },
      Xinjiang: { lat: 43.8256, lng: 87.6168 },
      Tibet: { lat: 29.652, lng: 91.1721 },
      Qinghai: { lat: 36.6171, lng: 101.7782 },
      Ningxia: { lat: 38.4872, lng: 106.2309 },
      Hainan: { lat: 20.044, lng: 110.1983 },
      HongKong: { lat: 22.3193, lng: 114.1694 },
      Macau: { lat: 22.1987, lng: 113.5439 },
      Taiwan: { lat: 25.033, lng: 121.5654 },
    };

    return {
      world: world.map((row) => {
        const location = coordinates[row.country_name] || { code: 'UNK', lat: 0, lng: 0 };

        return {
          country: row.country_name,
          code: location.code,
          count: row.count,
          lat: location.lat,
          lng: location.lng,
        };
      }),
      heatmap: world
        .map((row) => {
          const location = coordinates[row.country_name];
          if (!location) {
            return null;
          }

          const intensity = Math.min((row.count || 0) / Math.max(world[0]?.count || 1, 1), 1);
          return {
            lat: location.lat,
            lng: location.lng,
            intensity: Number(intensity.toFixed(2)),
          };
        })
        .filter(Boolean),
      china: provinces
        .map((row) => {
          const key = (row.province || '').replace(/\s+/g, '');
          const location = provinceCoordinates[key] || provinceCoordinates[row.province] || null;
          if (!location) {
            return null;
          }

          return {
            province: row.province,
            city: row.city,
            count: row.count,
            lat: location.lat,
            lng: location.lng,
          };
        })
        .filter(Boolean),
      provinceTop: provinces.slice(0, 5).map((row) => ({
        province: row.province,
        city: row.city,
        count: row.count,
      })),
      cityTop: provinces
        .slice()
        .sort((a, b) => b.count - a.count)
        .map((row) => ({
          province: row.province,
          city: row.city,
          count: row.count,
        }))
        .slice(0, 5),
    };
  }

  async getPortDistribution() {
    const rows = await this.query<any>(
      `
      SELECT port, service, count, percentage, risk
      FROM exposure_port_stats
      ORDER BY count DESC
      LIMIT 20
      `,
    );

    return {
      common: rows.slice(0, 10).map((row) => ({
        port: row.port,
        service: row.service,
        count: row.count,
        percentage: row.percentage,
      })),
      unusual: rows
        .filter((row) => ['high', 'medium'].includes(row.risk))
        .slice(0, 10)
        .map((row) => ({
          port: row.port,
          service: row.service,
          count: row.count,
          risk: row.risk,
        })),
    };
  }

  async getRiskLevelDistribution() {
    const [summary] = await this.query<any>(
      `
      SELECT *
      FROM exposure_summary
      ORDER BY generated_at DESC, id DESC
      LIMIT 1
      `,
    );

    if (!summary) {
      throw new Error('No exposure summary found in database');
    }

    const total = summary.total_instances || 1;
    const levels = [
      { level: 'Critical', count: summary.critical_count, color: '#ff4d4f' },
      { level: 'High', count: summary.high_count, color: '#ff7a45' },
      { level: 'Medium', count: summary.medium_count, color: '#ffa940' },
      { level: 'Low', count: summary.low_count, color: '#52c41a' },
    ];

    return {
      levels: levels.map((item) => ({
        ...item,
        percentage: Number(((item.count * 100) / total).toFixed(2)),
      })),
      trend: {
        critical: { current: summary.critical_count, previous: summary.critical_count, change: 0 },
        high: { current: summary.high_count, previous: summary.high_count, change: 0 },
        medium: { current: summary.medium_count, previous: summary.medium_count, change: 0 },
        low: { current: summary.low_count, previous: summary.low_count, change: 0 },
      },
    };
  }

  async getTrends(timeRange = '7d') {
    const dayCount = timeRange === '30d' ? 30 : timeRange === '14d' ? 14 : 7;
    const rows = await this.query<any>(
      `
      SELECT
        substr(last_seen, 1, 10) as date,
        COUNT(*) as total,
        SUM(CASE WHEN risk_level = 'Critical' THEN 1 ELSE 0 END) as critical,
        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high,
        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium,
        SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low
      FROM exposure_instances
      WHERE last_seen IS NOT NULL
      GROUP BY substr(last_seen, 1, 10)
      ORDER BY date DESC
      LIMIT ?
      `,
      [dayCount],
    );

    return {
      timeRange,
      data: rows.reverse(),
    };
  }

  async searchTarget(target: string) {
    const rows = await this.query<any>(
      `
      SELECT *
      FROM exposure_instances
      WHERE ip LIKE ? OR assistant_name LIKE ? OR domains LIKE ?
      ORDER BY last_seen DESC
      LIMIT 20
      `,
      [`%${target}%`, `%${target}%`, `%${target}%`],
    );

    return {
      target,
      found: rows.length > 0,
      services: rows.map((row) => ({
        ip: row.ip,
        port: row.port,
        service: row.service,
        banner: row.assistant_name ? `OpenClaw Assistant: ${row.assistant_name}` : 'OpenClaw service',
        status: row.status,
        runtimeStatus: row.runtime_status || 'Unknown',
        serverVersion: row.server_version || null,
        isChinaInstance: row.is_china_instance === 'Yes',
        province: row.province || null,
        cnCity: row.cn_city || null,
      })),
    };
  }
}

export const exposureDatabaseService = new ExposureDatabaseService();
