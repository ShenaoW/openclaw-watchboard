import path from 'path';
import sqlite3 from 'sqlite3';

type QueryValue = string | number | null;

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

interface HistoricalVulnerabilityMatch {
  vulnerability_id: string;
  title: string;
  severity: string;
  affected_versions: string;
  cve: string;
}

interface OverviewDelta {
  totalExposedServices: number;
  activeInstances: number;
  chinaExposedServices: number;
  chinaActiveInstances: number;
  countryCount: number;
  provinceCount: number;
  cityCount: number;
  historicalVulnerableInstances: number;
  historicalMatchedVulnerabilityCount: number;
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

  private parseHistoricalMatches(value?: string | null): HistoricalVulnerabilityMatch[] {
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

  private normalizeCountryName(value?: string | null) {
    return (value || '').trim();
  }

  private normalizeProvinceName(value?: string | null) {
    const trimmed = (value || '').trim();
    if (!trimmed) {
      return '';
    }

    const aliasMap: Record<string, string> = {
      北京市: 'Beijing',
      上海市: 'Shanghai',
      天津市: 'Tianjin',
      重庆市: 'Chongqing',
      广东省: 'Guangdong',
      浙江省: 'Zhejiang',
      江苏省: 'Jiangsu',
      山东省: 'Shandong',
      四川省: 'Sichuan',
      湖北省: 'Hubei',
      湖南省: 'Hunan',
      河南省: 'Henan',
      河北省: 'Hebei',
      福建省: 'Fujian',
      安徽省: 'Anhui',
      江西省: 'Jiangxi',
      陕西省: 'Shaanxi',
      辽宁省: 'Liaoning',
      吉林省: 'Jilin',
      黑龙江省: 'Heilongjiang',
      广西壮族自治区: 'Guangxi',
      云南省: 'Yunnan',
      贵州省: 'Guizhou',
      甘肃省: 'Gansu',
      山西省: 'Shanxi',
      内蒙古自治区: 'InnerMongolia',
      新疆维吾尔自治区: 'Xinjiang',
      西藏自治区: 'Tibet',
      青海省: 'Qinghai',
      宁夏回族自治区: 'Ningxia',
      海南省: 'Hainan',
      香港特别行政区: 'HongKong',
      澳门特别行政区: 'Macau',
      台湾省: 'Taiwan',
    };

    return aliasMap[trimmed] || trimmed.replace(/\s+/g, '');
  }

  async getOverview() {
    const summaries = await this.query<any>(
      `
      SELECT *
      FROM exposure_summary
      ORDER BY generated_at DESC, id DESC
      LIMIT 2
      `,
    );

    const summary = summaries[0];
    const previousSummary = summaries[1];

    if (!summary) {
      throw new Error('No exposure summary found in database');
    }

    const topCountries = await this.query<any>(
      `
      SELECT country_name, count
      FROM exposure_country_stats
      ORDER BY count DESC
      LIMIT 5
      `,
    );

    const topPorts = await this.query<any>(
      `
      SELECT port, service, count
      FROM exposure_port_stats
      ORDER BY count DESC
      LIMIT 5
      `,
    );

    const currentChinaExposedServices = Number(summary.china_exposed_services || 0);
    const currentChinaActiveInstances = Number(summary.china_active_instances || 0);
    const currentProvinceCount = Number(summary.province_count || 0);
    const currentCityCount = Number(summary.city_count || 0);

    const deltas: OverviewDelta = {
      totalExposedServices: Number(summary.total_instances || 0) - Number(previousSummary?.total_instances || 0),
      activeInstances: Number(summary.active_instances || 0) - Number(previousSummary?.active_instances || 0),
      chinaExposedServices:
        currentChinaExposedServices - Number(previousSummary?.china_exposed_services || 0),
      chinaActiveInstances:
        currentChinaActiveInstances - Number(previousSummary?.china_active_instances || 0),
      countryCount: Number(summary.country_count || 0) - Number(previousSummary?.country_count || 0),
      provinceCount: currentProvinceCount - Number(previousSummary?.province_count || 0),
      cityCount: currentCityCount - Number(previousSummary?.city_count || 0),
      historicalVulnerableInstances:
        Number(summary.historical_vulnerable_instances || 0) -
        Number(previousSummary?.historical_vulnerable_instances || 0),
      historicalMatchedVulnerabilityCount:
        Number(summary.historical_matched_vulnerability_count || 0) -
        Number(previousSummary?.historical_matched_vulnerability_count || 0),
    };

    return {
      totalExposedServices: summary.total_instances,
      activeInstances: summary.active_instances || 0,
      chinaExposedServices: currentChinaExposedServices,
      chinaActiveInstances: currentChinaActiveInstances,
      provinceCount: currentProvinceCount,
      cityCount: currentCityCount,
      countryCount: summary.country_count || 0,
      historicalVulnerableInstances: summary.historical_vulnerable_instances || 0,
      historicalVulnerableActiveInstances: summary.historical_vulnerable_active_instances || 0,
      historicalMatchedVulnerabilityCount: summary.historical_matched_vulnerability_count || 0,
      deltas,
      lastScanTime: summary.last_scan_time,
      topCountries: topCountries.map((country) => ({
        country: country.country_name,
        count: country.count,
      })),
      topPorts: topPorts.map((port) => ({
        port: port.port,
        service: port.service,
        count: port.count,
      })),
    };
  }

  async getServices(filters: {
    status?: string;
    runtimeStatus?: string;
    chinaScope?: string;
    versionStatus?: string;
    historicalVulnStatus?: string;
    historicalVulnCountRange?: string;
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

    if (filters.historicalVulnStatus === 'matched') {
      where.push(`historical_vuln_count > 0`);
    }

    if (filters.historicalVulnStatus === 'unmatched') {
      where.push(`(historical_vuln_count IS NULL OR historical_vuln_count = 0)`);
    }

    if (filters.historicalVulnCountRange === '1-2') {
      where.push(`historical_vuln_count BETWEEN 1 AND 2`);
    }

    if (filters.historicalVulnCountRange === '3-9') {
      where.push(`historical_vuln_count BETWEEN 3 AND 9`);
    }

    if (filters.historicalVulnCountRange === '10+') {
      where.push(`historical_vuln_count >= 10`);
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
    const limit = Math.min(Math.max(filters.limit || 20, 1), 30);
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
        CASE runtime_status
          WHEN 'Active' THEN 1
          ELSE 2
        END,
        historical_vuln_count DESC,
        last_seen DESC
      LIMIT ? OFFSET ?
      `,
      [...params, limit, offset],
    );

    const total = countResult?.total || 0;

    return {
      services: rows.map((row, index) => ({
        id: `exposure-${row.id ?? offset + index + 1}`,
        ip: row.masked_ip || row.ip,
        maskedIp: row.masked_ip || row.ip,
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
        historicalVulnCount: Number(row.historical_vuln_count || 0),
        historicalVulnMaxSeverity: row.historical_vuln_max_severity || null,
        historicalVulnMatches: this.parseHistoricalMatches(row.historical_vuln_matches),
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
      SELECT country_name, count
      FROM exposure_country_stats
      ORDER BY count DESC
      LIMIT 20
      `,
    );

    const provinces = await this.query<any>(
      `
      SELECT province, count
      FROM exposure_province_stats
      WHERE province IS NOT NULL AND province != ''
      ORDER BY count DESC
      LIMIT 50
      `,
    );

    const coordinates: Record<string, { code: string; lat: number; lng: number }> = {
      中国: { code: 'CHN', lat: 35.8617, lng: 104.1954 },
      'China mainland': { code: 'CHN', lat: 35.8617, lng: 104.1954 },
      美国: { code: 'USA', lat: 37.0902, lng: -95.7129 },
      'United States': { code: 'USA', lat: 37.0902, lng: -95.7129 },
      新加坡: { code: 'SGP', lat: 1.3521, lng: 103.8198 },
      Singapore: { code: 'SGP', lat: 1.3521, lng: 103.8198 },
      德国: { code: 'DEU', lat: 51.1657, lng: 10.4515 },
      Germany: { code: 'DEU', lat: 51.1657, lng: 10.4515 },
      中国香港特别行政区: { code: 'HKG', lat: 22.3193, lng: 114.1694 },
      香港特别行政区: { code: 'HKG', lat: 22.3193, lng: 114.1694 },
      'Hong Kong': { code: 'HKG', lat: 22.3193, lng: 114.1694 },
      日本: { code: 'JPN', lat: 36.2048, lng: 138.2529 },
      Japan: { code: 'JPN', lat: 36.2048, lng: 138.2529 },
      俄罗斯: { code: 'RUS', lat: 61.524, lng: 105.3188 },
      Russia: { code: 'RUS', lat: 61.524, lng: 105.3188 },
      加拿大: { code: 'CAN', lat: 56.1304, lng: -106.3468 },
      Canada: { code: 'CAN', lat: 56.1304, lng: -106.3468 },
      法国: { code: 'FRA', lat: 46.2276, lng: 2.2137 },
      France: { code: 'FRA', lat: 46.2276, lng: 2.2137 },
      荷兰: { code: 'NLD', lat: 52.1326, lng: 5.2913 },
      Netherlands: { code: 'NLD', lat: 52.1326, lng: 5.2913 },
      芬兰: { code: 'FIN', lat: 61.9241, lng: 25.7482 },
      英国: { code: 'GBR', lat: 55.3781, lng: -3.436 },
      印度: { code: 'IND', lat: 20.5937, lng: 78.9629 },
      澳大利亚: { code: 'AUS', lat: -25.2744, lng: 133.7751 },
      韩国: { code: 'KOR', lat: 35.9078, lng: 127.7669 },
      马来西亚: { code: 'MYS', lat: 4.2105, lng: 101.9758 },
      巴西: { code: 'BRA', lat: -14.235, lng: -51.9253 },
      越南: { code: 'VNM', lat: 14.0583, lng: 108.2772 },
      印度尼西亚: { code: 'IDN', lat: -0.7893, lng: 113.9213 },
      爱尔兰: { code: 'IRL', lat: 53.1424, lng: -7.6921 },
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
        const location =
          coordinates[this.normalizeCountryName(row.country_name)] || { code: 'UNK', lat: 0, lng: 0 };

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
          const location = coordinates[this.normalizeCountryName(row.country_name)];
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
          const key = this.normalizeProvinceName(row.province);
          const location = provinceCoordinates[key] || provinceCoordinates[row.province] || null;
          if (!location) {
            return null;
          }

          return {
            province: row.province,
            count: row.count,
            lat: location.lat,
            lng: location.lng,
          };
        })
        .filter(Boolean),
      provinceTop: provinces.slice(0, 5).map((row) => ({
        province: row.province,
        count: row.count,
      })),
      cityTop: [],
    };
  }

  async getPortDistribution() {
    const rows = await this.query<any>(
      `
      SELECT port, service, count, percentage
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
    };
  }

  async getTrends(timeRange = '7d') {
    const dayCount = timeRange === '30d' ? 30 : timeRange === '14d' ? 14 : 7;
    const firstSeenRows = await this.query<any>(
      `
      SELECT
        substr(first_seen, 1, 10) as date,
        COUNT(*) as count
      FROM exposure_instances
      WHERE first_seen IS NOT NULL
      GROUP BY substr(first_seen, 1, 10)
      ORDER BY date DESC
      LIMIT ?
      `,
      [dayCount],
    );

    const lastSeenRows = await this.query<any>(
      `
      SELECT
        substr(last_seen, 1, 10) as date,
        COUNT(*) as count
      FROM exposure_instances
      WHERE last_seen IS NOT NULL
      GROUP BY substr(last_seen, 1, 10)
      ORDER BY date DESC
      LIMIT ?
      `,
      [dayCount],
    );

    const activeRows = await this.query<any>(
      `
      SELECT
        substr(last_seen, 1, 10) as date,
        SUM(CASE WHEN runtime_status = 'Active' THEN 1 ELSE 0 END) as count
      FROM exposure_instances
      WHERE last_seen IS NOT NULL
      GROUP BY substr(last_seen, 1, 10)
      ORDER BY date DESC
      LIMIT ?
      `,
      [dayCount],
    );

    const byDate = new Map<string, { date: string; firstSeen: number; lastSeen: number; active: number }>();

    for (const row of firstSeenRows) {
      const item = byDate.get(row.date) || { date: row.date, firstSeen: 0, lastSeen: 0, active: 0 };
      item.firstSeen = Number(row.count || 0);
      byDate.set(row.date, item);
    }

    for (const row of lastSeenRows) {
      const item = byDate.get(row.date) || { date: row.date, firstSeen: 0, lastSeen: 0, active: 0 };
      item.lastSeen = Number(row.count || 0);
      byDate.set(row.date, item);
    }

    for (const row of activeRows) {
      const item = byDate.get(row.date) || { date: row.date, firstSeen: 0, lastSeen: 0, active: 0 };
      item.active = Number(row.count || 0);
      byDate.set(row.date, item);
    }

    const data = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));

    return {
      timeRange,
      data,
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
        ip: row.masked_ip || row.ip,
        maskedIp: row.masked_ip || row.ip,
        port: row.port,
        service: row.service,
        banner: row.assistant_name ? `OpenClaw Assistant: ${row.assistant_name}` : 'OpenClaw service',
        status: row.status,
        runtimeStatus: row.runtime_status || 'Unknown',
        serverVersion: row.server_version || null,
        historicalVulnCount: Number(row.historical_vuln_count || 0),
        historicalVulnMaxSeverity: row.historical_vuln_max_severity || null,
        isChinaInstance: row.is_china_instance === 'Yes',
        province: row.province || null,
        cnCity: row.cn_city || null,
      })),
    };
  }
}

export const exposureDatabaseService = new ExposureDatabaseService();
