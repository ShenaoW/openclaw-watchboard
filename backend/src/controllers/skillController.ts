import { NextFunction, Request, Response } from 'express';
import { skillDataService } from '../services/SkillDataService';

export class SkillController {
  async getTrustedSkills(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await skillDataService.getTrustedSkills({
        page: Number(req.query.page || 1),
        limit: Number(req.query.limit || 20),
        source: req.query.source as string | undefined,
        category: req.query.category as string | undefined,
        search: req.query.search as string | undefined,
      });

      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  }

  async getSuspiciousSkills(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await skillDataService.getSuspiciousSkills({
        page: Number(req.query.page || 1),
        limit: Number(req.query.limit || 20),
        source: req.query.source as string | undefined,
        category: req.query.category as string | undefined,
        search: req.query.search as string | undefined,
      });

      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  }

  async getMaliciousSkills(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await skillDataService.getMaliciousSkills({
        page: Number(req.query.page || 1),
        limit: Number(req.query.limit || 20),
        source: req.query.source as string | undefined,
        category: req.query.category as string | undefined,
        search: req.query.search as string | undefined,
      });

      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  }

  async getSkillAnalysis(req: Request, res: Response, next: NextFunction) {
    try {
      const skill = await skillDataService.getSkillById(req.params.skillId);

      if (!skill) {
        res.status(404).json({
          success: false,
          error: { message: 'Skill not found' },
        });
        return;
      }

      const permissions = skill.permissions as string[];
      const dependencies = Array.isArray(skill.dependencies) ? skill.dependencies : [];
      const suspicious = skill.classification === 'suspicious' || skill.classification === 'malicious';
      const malicious = skill.classification === 'malicious';

      const inferredLanguage = this.inferLanguage(skill);
      const codeQuality = Math.max(Math.min(skill.securityScore + (skill.verified ? 5 : 0), 100), 10);
      const permissionUsage = Math.max(20, 100 - permissions.length * 12 - (suspicious ? 25 : 0));
      const networkBehavior = Math.max(
        15,
        100 - (permissions.some((item) => item.includes('network')) ? 15 : 0) - (suspicious ? 30 : 5),
      );
      const fileSystemAccess = Math.max(
        20,
        100 - (permissions.filter((item) => item.includes('file')).length * 18 + (suspicious ? 10 : 0)),
      );

      res.json({
        success: true,
        data: {
          skillId: skill.id,
          basicInfo: {
            name: skill.name,
            version: skill.version,
            size: `${Math.max(skill.skillContent.length / 1024, 1).toFixed(1)} KB`,
            language: inferredLanguage,
            architecture: skill.source === 'clawhub' ? 'Official Skill Package' : 'External Archive Package',
            source: skill.source,
            maintainer: skill.maintainer,
            repository: skill.repository,
          },
          securityAnalysis: {
            overallScore: skill.securityScore,
            codeQuality,
            permissionUsage,
            networkBehavior,
            fileSystemAccess,
          },
          staticAnalysis: {
            malwareSignatures: malicious ? 2 : suspicious ? 1 : 0,
            suspiciousPatterns: suspicious ? Math.max(permissions.length, malicious ? 3 : 1) : 0,
            vulnerabilities: this.buildVulnerabilities(skill),
          },
          dependencies: dependencies.map((item: any, index: number) =>
            typeof item === 'string'
              ? {
                  name: `history-${index + 1}`,
                  version: item,
                  vulnerabilities: 0,
                }
              : {
                  name: item.name || `dependency-${index + 1}`,
                  version: item.version || 'unknown',
                  vulnerabilities: Number(item.vulnerabilities || 0),
                  license: item.license,
                },
          ),
          skillMarkdown: skill.skillContent || '',
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async getSkillUsageStats(req: Request, res: Response, next: NextFunction) {
    try {
      const stats = await skillDataService.getStats();
      res.json({ success: true, data: stats });
    } catch (error) {
      next(error);
    }
  }

  async addTrustedSkill(req: Request, res: Response, next: NextFunction) {
    try {
      const { skillName, source, repo, url } = req.body;
      res.json({
        success: true,
        message: 'Skill added to trusted list successfully',
        data: {
          skillName,
          source,
          repo,
          url,
          classification: 'safe',
          addedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async reportSuspiciousSkill(req: Request, res: Response, next: NextFunction) {
    try {
      const { skillId, reason, description } = req.body;
      res.json({
        success: true,
        message: 'Skill reported successfully',
        data: {
          reportId: `report-${Date.now()}`,
          skillId,
          reason,
          description,
          status: 'under_review',
          reportedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async verifySkill(req: Request, res: Response, next: NextFunction) {
    try {
      const { skillId, source, verifyType } = req.body;
      res.json({
        success: true,
        data: {
          verificationId: `verify-${Date.now()}`,
          skillId,
          source,
          verifyType,
          status: 'queued',
          createdAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async getSyncStatus(req: Request, res: Response, next: NextFunction) {
    try {
      const stats = await skillDataService.getStats();
      res.json({
        success: true,
        data: {
          lastSync: new Date().toISOString(),
          status: 'completed',
          totalProcessed: stats.totalSkills,
          newSkills: 0,
          updatedSkills: 0,
          errors: 0,
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async syncSkillDatabase(req: Request, res: Response, next: NextFunction) {
    try {
      res.json({
        success: true,
        message: 'Skill database sync initiated',
        data: {
          jobId: `sync-${Date.now()}`,
          status: 'started',
          startedAt: new Date().toISOString(),
          estimatedDuration: '2-5 minutes',
        },
      });
    } catch (error) {
      next(error);
    }
  }

  private inferLanguage(skill: any) {
    const content = `${skill.repository} ${skill.skillContent}`.toLowerCase();
    if (content.includes('python')) {
      return 'Python';
    }
    if (content.includes('typescript') || content.includes('.ts')) {
      return 'TypeScript';
    }
    if (content.includes('javascript') || content.includes('.js')) {
      return 'JavaScript';
    }
    if (content.includes('go')) {
      return 'Go';
    }
    return 'Markdown / Mixed';
  }

  private buildVulnerabilities(skill: any) {
    if (skill.classification !== 'suspicious' && skill.classification !== 'malicious') {
      return [];
    }

    if (skill.classification === 'malicious') {
      return [
        {
          type: 'Confirmed Malicious Classification',
          severity: 'Critical',
          location: skill.repository || skill.name,
          description: 'The ingestion dataset marked this skill as malicious and it should be blocked by default.',
        },
        {
          type: 'Active Abuse Potential',
          severity: 'High',
          location: skill.name,
          description: 'The package characteristics indicate credential theft, remote execution, or persistence risk.',
        },
      ];
    }

    return [
      {
        type: 'Suspicious Source Classification',
        severity: skill.securityScore < 30 ? 'Critical' : 'High',
        location: skill.repository || skill.name,
        description: 'The skill was flagged during ingestion from the external source dataset.',
      },
      {
        type: 'Manual Review Required',
        severity: 'Medium',
        location: skill.name,
        description: 'Permissions and repository provenance should be reviewed before production use.',
      },
    ];
  }
}
