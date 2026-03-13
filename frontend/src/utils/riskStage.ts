const stageNameMap: Record<string, string> = {
  "Gateway Authorization & Routing Stage": "网关鉴权与路由",
  "Authentication & Authorization Decision Stage": "网关鉴权与路由",
  "Auth State": "网关鉴权与路由",
  "Resource Access Stage": "工具与技能执行",
  "Execution Stage": "工具与技能执行",
  "Persistence & Output Presentation Stage": "消息回传与持久化",
  "Input Ingress Stage": "消息输入与通道适配",
};

export function normalizeRiskStage(stage?: string | null) {
  const cleaned = stage?.trim() || "";
  return stageNameMap[cleaned] || cleaned;
}
