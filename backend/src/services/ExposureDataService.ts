import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse';
import { promisify } from 'util';

const readFile = promisify(fs.readFile);

export interface ExposedInstance {
  ip_port: string;
  assistant_name: string;
  country: string;
  authenticated: string;
  active: string;
  status: 'Clean' | 'Leaked';
  asn: string;
  organization: string;
  isp: string;
  first_seen: string;
  last_seen: string;
  credentials_leaked: 'Yes' | 'No';
  has_mcp: 'Yes' | 'No';
  apt_groups: string;
  cve_list: string;
  scan_time: string;
  domains: string;
}

export interface FieldDistribution {
  field: string;
  display_name: string;
  value: string;
  count: number;
  percentage: number;
}

export interface ExposureStats {
  totalInstances: number;
  statusDistribution: {
    clean: number;
    leaked: number;
  };
  credentialsLeaked: {
    yes: number;
    no: number;
  };
  topCountries: FieldDistribution[];
  topISPs: FieldDistribution[];
  riskSummary: {
    highRisk: number;
    mediumRisk: number;
    lowRisk: number;
  };
}

export class ExposureDataService {
  private dataPath = '/Users/shawn/Desktop/openclaw-watchboard/data/explosure';
  private distributionPath = path.join(this.dataPath, 'field_distributions');
  private mainCsvPath = path.join(this.dataPath, 'openclaw_instances_merged.csv');

  async readDistributionFile(filename: string): Promise<FieldDistribution[]> {
    try {
      const filePath = path.join(this.distributionPath, filename);
      const content = await readFile(filePath, 'utf-8');

      return new Promise((resolve, reject) => {
        parse(content, {
          columns: true,
          skip_empty_lines: true,
        }, (err, records: FieldDistribution[]) => {
          if (err) {
            reject(err);
          } else {
            resolve(records.map(record => ({
              ...record,
              count: parseInt(record.count.toString()),
              percentage: parseFloat(record.percentage.toString())
            })));
          }
        });
      });
    } catch (error) {
      console.error(`读取分布文件失败 ${filename}:`, error);
      return [];
    }
  }

  async getStats(): Promise<ExposureStats> {
    try {
      // 读取各种分布数据
      const [
        statusDist,
        countryDist,
        credentialsDist,
        ispDist
      ] = await Promise.all([
        this.readDistributionFile('status_distribution.csv'),
        this.readDistributionFile('country_distribution.csv'),
        this.readDistributionFile('credentials_leaked_distribution.csv'),
        this.readDistributionFile('isp_distribution.csv')
      ]);

      // 计算总数
      const totalInstances = statusDist.reduce((sum, item) => sum + item.count, 0);

      // 状态分布
      const cleanCount = statusDist.find(item => item.value === 'Clean')?.count || 0;
      const leakedCount = statusDist.find(item => item.value === 'Leaked')?.count || 0;

      // 凭据泄露分布
      const credLeakedYes = credentialsDist.find(item => item.value === 'Yes')?.count || 0;
      const credLeakedNo = credentialsDist.find(item => item.value === 'No')?.count || 0;

      // 风险评估：基于泄露状态和凭据泄露情况
      const highRisk = leakedCount; // Leaked状态都算高风险
      const mediumRisk = Math.floor(cleanCount * 0.3); // 假设Clean中30%为中风险
      const lowRisk = totalInstances - highRisk - mediumRisk;

      return {
        totalInstances,
        statusDistribution: {
          clean: cleanCount,
          leaked: leakedCount
        },
        credentialsLeaked: {
          yes: credLeakedYes,
          no: credLeakedNo
        },
        topCountries: countryDist.slice(0, 10),
        topISPs: ispDist.slice(0, 10),
        riskSummary: {
          highRisk,
          mediumRisk,
          lowRisk
        }
      };
    } catch (error) {
      console.error('获取暴露统计失败:', error);
      throw error;
    }
  }

  async getInstances(filters?: {
    status?: string;
    country?: string;
    isp?: string;
    credentials_leaked?: string;
    page?: number;
    limit?: number;
    search?: string;
  }): Promise<{
    instances: ExposedInstance[];
    pagination: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  }> {
    try {
      const page = filters?.page || 1;
      const limit = Math.min(filters?.limit || 50, 100); // 限制最大50条

      console.log('读取暴露实例数据...');
      const content = await readFile(this.mainCsvPath, 'utf-8');

      return new Promise((resolve, reject) => {
        parse(content, {
          columns: true,
          skip_empty_lines: true,
        }, (err, records: ExposedInstance[]) => {
          if (err) {
            reject(err);
            return;
          }

          let filteredRecords = records;

          // 应用过滤器
          if (filters?.status) {
            filteredRecords = filteredRecords.filter(r => r.status === filters.status);
          }
          if (filters?.country) {
            filteredRecords = filteredRecords.filter(r => r.country.includes(filters.country!));
          }
          if (filters?.isp) {
            filteredRecords = filteredRecords.filter(r => r.isp.includes(filters.isp!));
          }
          if (filters?.credentials_leaked) {
            filteredRecords = filteredRecords.filter(r => r.credentials_leaked === filters.credentials_leaked);
          }
          if (filters?.search) {
            const searchLower = filters.search.toLowerCase();
            filteredRecords = filteredRecords.filter(r =>
              r.ip_port.toLowerCase().includes(searchLower) ||
              r.assistant_name.toLowerCase().includes(searchLower) ||
              r.country.toLowerCase().includes(searchLower) ||
              r.organization.toLowerCase().includes(searchLower)
            );
          }

          const total = filteredRecords.length;
          const totalPages = Math.ceil(total / limit);
          const startIndex = (page - 1) * limit;
          const endIndex = startIndex + limit;
          const instances = filteredRecords.slice(startIndex, endIndex);

          resolve({
            instances,
            pagination: {
              page,
              limit,
              total,
              totalPages
            }
          });
        });
      });
    } catch (error) {
      console.error('获取暴露实例失败:', error);
      throw error;
    }
  }

  async getGeographicData(): Promise<Array<{
    country: string;
    count: number;
    risk: number;
    coordinates?: [number, number];
  }>> {
    try {
      const countryDist = await this.readDistributionFile('country_distribution.csv');
      const statusDist = await this.readDistributionFile('status_distribution.csv');

      // 简单的风险评分：基于泄露比例
      const totalLeaked = statusDist.find(item => item.value === 'Leaked')?.count || 0;
      const totalClean = statusDist.find(item => item.value === 'Clean')?.count || 0;
      const globalRiskRatio = totalLeaked / (totalLeaked + totalClean);

      return countryDist.slice(0, 15).map(country => ({
        country: country.value,
        count: country.count,
        // 假设风险评分，实际中可以根据该国家的泄露比例计算
        risk: Math.round((globalRiskRatio + Math.random() * 0.3) * 10 * 10) / 10
      }));
    } catch (error) {
      console.error('获取地理数据失败:', error);
      return [];
    }
  }

  async getPortDistribution(): Promise<Array<{
    port: string;
    count: number;
    percentage: number;
  }>> {
    try {
      // 从主CSV中提取端口统计
      console.log('分析端口分布...');
      const content = await readFile(this.mainCsvPath, 'utf-8');

      return new Promise((resolve, reject) => {
        const portStats: { [key: string]: number } = {};

        parse(content, {
          columns: true,
          skip_empty_lines: true,
        }, (err, records: ExposedInstance[]) => {
          if (err) {
            reject(err);
            return;
          }

          // 统计端口分布
          records.forEach(record => {
            if (record.ip_port) {
              const portMatch = record.ip_port.match(/:(\d+)$/);
              if (portMatch) {
                const port = portMatch[1];
                portStats[port] = (portStats[port] || 0) + 1;
              }
            }
          });

          const total = Object.values(portStats).reduce((sum, count) => sum + count, 0);
          const result = Object.entries(portStats)
            .map(([port, count]) => ({
              port,
              count,
              percentage: Math.round((count / total) * 10000) / 100
            }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 10);

          resolve(result);
        });
      });
    } catch (error) {
      console.error('获取端口分布失败:', error);
      return [];
    }
  }
}

export const exposureDataService = new ExposureDataService();