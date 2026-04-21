import { useEffect, useState } from "react";

import { copyTextToClipboard } from "../../lib/clipboard";
import { pickHarFile } from "../../lib/desktop";
import type {
  GuidanceStepStatus,
  HookRecommendationSummary,
  LiveTrafficPreviewItem,
  LiveTrafficPreviewResponse,
  LiveCaptureNetworkSummary,
  SslHookGuidanceStatus,
  TrafficEvidenceExternalContext,
  TrafficCaptureResponse,
  TrafficFlowSummary,
  TrafficHostSummary,
  WorkspaceMethodScope,
} from "../../lib/types";

type TrafficEvidencePanelProps = {
  capture: TrafficCaptureResponse | null;
  externalContext: TrafficEvidenceExternalContext | null;
  harErrorMessage: string | null;
  harImportMessage: string | null;
  isImporting: boolean;
  isSavingRuntimeSettings: boolean;
  isStartingLiveCapture: boolean;
  isStoppingLiveCapture: boolean;
  liveArtifactPath: string | null;
  liveCaptureListenHost: string;
  liveCaptureListenPort: string;
  liveErrorMessage: string | null;
  liveMessage: string | null;
  liveCertificateDirectoryPath: string | null;
  liveCertificateExists: boolean;
  liveCertificateHelpText: string | null;
  liveCertificatePath: string | null;
  liveInstallUrl: string | null;
  livePreview: LiveTrafficPreviewResponse | null;
  liveProxyAddressHint: string | null;
  liveRuntimeAvailable: boolean;
  liveRuntimeDetail: string | null;
  liveRuntimeHelpText: string | null;
  liveSetupSteps: string[];
  liveProxySteps: string[];
  liveCertificateSteps: string[];
  liveRecommendedActions: string[];
  liveSetupStepDetails: GuidanceStepStatus[];
  liveProxyStepDetails: GuidanceStepStatus[];
  liveCertificateStepDetails: GuidanceStepStatus[];
  liveNetworkSummary: LiveCaptureNetworkSummary | null;
  liveSslHookGuidance: SslHookGuidanceStatus | null;
  liveRuntimeListenHost: string;
  liveRuntimeListenPort: number;
  liveStatusText: string;
  onAddRecommendationToPlan: (recommendationId: string) => void;
  onAddTemplateToPlan: (template: {
    template_id: string;
    template_name: string;
    plugin_id: string;
  }) => void;
  onClearExternalContext: () => void;
  onInspectHookContext: (payload: {
    hint: string;
    query: string;
    scope: WorkspaceMethodScope;
  }) => void;
  onLiveCaptureListenHostChange: (value: string) => void;
  onLiveCaptureListenPortChange: (value: string) => void;
  onOpenPath: (path: string) => void;
  onHarPathChange: (value: string) => void;
  onImport: () => void;
  onSaveLiveCaptureSettings: () => void;
  onStartLiveCapture: () => void;
  onStopLiveCapture: () => void;
  runtimeSettingsError: string | null;
  runtimeSettingsMessage: string | null;
  startLiveCaptureDisabled: boolean;
  stopLiveCaptureDisabled: boolean;
  trafficRecommendations: HookRecommendationSummary[];
  harPath: string;
};

function formatStatusCode(value: number | null): string {
  return value === null ? "未知" : String(value);
}

function validatePortInput(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }
  if (!/^\d+$/.test(trimmed)) {
    return "端口必须是数字。";
  }
  const numeric = Number(trimmed);
  if (numeric < 1 || numeric > 65535) {
    return "端口范围必须在 1 – 65535。";
  }
  return null;
}

function isUnexpectedStatus(statusCode: number | null): boolean {
  return statusCode !== null && (statusCode < 200 || statusCode >= 400);
}

function getTimestampValue(value: string | null): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function extractHost(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

function formatTimestampLabel(value: string | null): string {
  if (!value) {
    return "时间未记录";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function sortPreviewItems(items: LiveTrafficPreviewItem[]): LiveTrafficPreviewItem[] {
  return [...items].sort((left, right) => {
    const suspiciousDelta = Number(right.suspicious) - Number(left.suspicious);
    if (suspiciousDelta !== 0) {
      return suspiciousDelta;
    }
    const indicatorDelta = right.matched_indicators.length - left.matched_indicators.length;
    if (indicatorDelta !== 0) {
      return indicatorDelta;
    }
    const statusDelta = Number(isUnexpectedStatus(right.status_code)) - Number(isUnexpectedStatus(left.status_code));
    if (statusDelta !== 0) {
      return statusDelta;
    }
    return getTimestampValue(right.timestamp) - getTimestampValue(left.timestamp);
  });
}

function sortCaptureFlows(flows: TrafficFlowSummary[]): TrafficFlowSummary[] {
  return [...flows].sort((left, right) => {
    const suspiciousDelta = Number(right.suspicious) - Number(left.suspicious);
    if (suspiciousDelta !== 0) {
      return suspiciousDelta;
    }
    const indicatorDelta = right.matched_indicators.length - left.matched_indicators.length;
    if (indicatorDelta !== 0) {
      return indicatorDelta;
    }
    return Number(isUnexpectedStatus(right.status_code)) - Number(isUnexpectedStatus(left.status_code));
  });
}

function describePreviewFocus(item: LiveTrafficPreviewItem): string {
  const reasons: string[] = [];
  if (item.suspicious) {
    reasons.push("已标记为可疑请求");
  }
  if (item.matched_indicators.length > 0) {
    reasons.push(`命中 ${item.matched_indicators.length} 条已知线索`);
  }
  if (isUnexpectedStatus(item.status_code)) {
    reasons.push(`状态码 ${formatStatusCode(item.status_code)} 需要复核`);
  }
  const host = extractHost(item.url);
  if (host) {
    reasons.push(`主机 ${host}`);
  }
  return reasons.join("；") || "最近一批请求里最值得优先复核的一条。";
}

function describeCaptureFocus(flow: TrafficFlowSummary): string {
  const reasons: string[] = [];
  if (flow.suspicious) {
    reasons.push("已被流量规则标记为可疑");
  }
  if (flow.matched_indicators.length > 0) {
    reasons.push(`命中线索：${flow.matched_indicators.join("、")}`);
  }
  if (flow.mime_type) {
    reasons.push(`内容类型：${flow.mime_type}`);
  }
  if (isUnexpectedStatus(flow.status_code)) {
    reasons.push(`状态码 ${formatStatusCode(flow.status_code)} 需要复核`);
  }
  return reasons.join("；") || "当前导入流量中优先级最高的一条。";
}

function deriveNextStepText({
  capture,
  liveCertificateExists,
  liveProxyAddressHint,
  liveRuntimeAvailable,
  liveStatusText,
}: {
  capture: TrafficCaptureResponse | null;
  liveCertificateExists: boolean;
  liveProxyAddressHint: string | null;
  liveRuntimeAvailable: boolean;
  liveStatusText: string;
}): string {
  if (!liveRuntimeAvailable) {
    return "先补齐 mitmdump 或自定义抓包命令，再回到这里启动实时抓包。";
  }
  if (!liveProxyAddressHint) {
    return "先确认分析机监听地址和端口，让测试设备能连到代理。";
  }
  if (!liveCertificateExists) {
    return "先在设备安装 mitm 证书，再复现登录、上报、心跳等可疑操作。";
  }
  if (liveStatusText === "抓包中") {
    return "抓包已经开始，优先在设备里复现登录、上报、心跳或证书校验相关动作。";
  }
  if (capture !== null && capture.suspicious_count > 0) {
    return "已经拿到可疑流量，先看摘要里的高优请求，再决定是否把网络 Hook 建议加入计划。";
  }
  return "先把设备代理到当前地址，安装证书，然后开始实时抓包或导入现成 HAR。";
}

function renderRecommendationHint(recommendation: HookRecommendationSummary): string {
  if (recommendation.template_name) {
    return `模板：${recommendation.template_name}`;
  }
  if (recommendation.method) {
    return `函数：${recommendation.method.class_name}.${recommendation.method.method_name}`;
  }
  return "可直接同步到 Hook 工作台继续编排。";
}

function summarizeHostGroups(hosts: TrafficHostSummary[], limit = 3): string {
  if (hosts.length === 0) {
    return "";
  }
  return hosts
    .slice(0, limit)
    .map((host) => `${host.host}（${host.flow_count}）`)
    .join("、");
}

function summarizeSuspiciousHosts(hosts: TrafficHostSummary[], limit = 3): string {
  if (hosts.length === 0) {
    return "当前还没有可疑主机。";
  }
  return hosts
    .slice(0, limit)
    .map((host) => `${host.host}（可疑 ${host.suspicious_count}，HTTPS ${host.https_flow_count}）`)
    .join("；");
}

function stepToText(step: GuidanceStepStatus): string {
  return `${step.title}：${step.detail}`;
}

function dedupeTerms(terms: string[]): string[] {
  const normalized = new Set<string>();
  const ordered: string[] = [];
  for (const term of terms) {
    const trimmed = term.trim();
    if (!trimmed) {
      continue;
    }
    const key = trimmed.toLowerCase();
    if (normalized.has(key)) {
      continue;
    }
    normalized.add(key);
    ordered.push(trimmed);
  }
  return ordered;
}

function buildHookStudioQuery(options: {
  guidanceTerms: string[];
  recommendation: HookRecommendationSummary | null;
}): string {
  const recommendationTerms = options.recommendation?.matched_terms ?? [];
  return dedupeTerms([...recommendationTerms, ...options.guidanceTerms]).slice(0, 3).join(" ");
}

function buildHookStudioHint(options: {
  guidanceTerms: string[];
  recommendation: HookRecommendationSummary | null;
  templateName: string | null;
}): string {
  const query = buildHookStudioQuery({
    guidanceTerms: options.guidanceTerms,
    recommendation: options.recommendation,
  });
  const subject =
    options.recommendation?.title ??
    options.templateName ??
    "当前 SSL / 网络线索";
  if (query) {
    return `已根据 ${subject} 切到 Hook 工作台，并预填关键词：${query}。`;
  }
  return `已根据 ${subject} 切到 Hook 工作台的相关候选范围。`;
}

function normalizeGuidanceSteps(details: GuidanceStepStatus[], fallback: string[]): string[] {
  if (details.length > 0) {
    return details.map(stepToText);
  }
  return fallback;
}

function pickFirstStep(steps: string[]): string | null {
  return steps.map((step) => step.trim()).find((step) => step.length > 0) ?? null;
}

function summarizeWorkflowSteps(steps: string[]): string | null {
  const normalized = steps.map((step) => step.trim()).filter((step) => step.length > 0);
  if (normalized.length === 0) {
    return null;
  }
  return normalized.slice(0, 3).join(" -> ");
}

function describeNetworkSummary(summary: LiveCaptureNetworkSummary | null): string | null {
  if (!summary) {
    return null;
  }
  const parts = [
    summary.proxy_ready ? "代理可下发" : "代理待确认",
    summary.certificate_ready ? "证书链路已就绪" : "证书链路待补齐",
    summary.supports_https_intercept ? "支持 HTTPS 解密" : "暂不支持 HTTPS 解密",
    summary.supports_ssl_hooking ? "可联动 SSL Hook" : "暂不建议叠加 SSL Hook",
  ];
  return parts.join(" · ");
}

function describeSslGuidanceSummary(guidance: SslHookGuidanceStatus | null): string | null {
  if (!guidance) {
    return null;
  }
  const templateText =
    guidance.suggested_templates.length > 0 ? `模板候选：${guidance.suggested_templates.join("、")}` : null;
  const termText = guidance.suggested_terms.length > 0 ? `关键词：${guidance.suggested_terms.join("、")}` : null;
  return [guidance.summary, templateText, termText].filter(Boolean).join("；");
}

function describeProxyAction(liveProxyAddressHint: string | null, liveProxySteps: string[]): string {
  if (liveProxyAddressHint) {
    return `把测试设备 HTTP/HTTPS 代理改为手动，并填入 ${liveProxyAddressHint}。`;
  }
  return pickFirstStep(liveProxySteps) ?? "先保存抓包参数，再把设备 HTTP / HTTPS 代理指向分析机可达地址。";
}

function describeCertificateAction({
  liveCertificatePath,
  liveCertificateSteps,
  liveInstallUrl,
}: {
  liveCertificatePath: string | null;
  liveCertificateSteps: string[];
  liveInstallUrl: string | null;
}): string {
  if (liveInstallUrl) {
    return `优先在设备浏览器访问 ${liveInstallUrl}；没有浏览器时再直接安装导出的 mitm 证书。`;
  }
  if (liveCertificatePath) {
    return `优先直接安装导出的 mitm 证书：${liveCertificatePath}。`;
  }
  return pickFirstStep(liveCertificateSteps) ?? "先确认 mitm 证书可安装，再测试目标请求能否正常解密。";
}

function describeSslRecommendationTiming({
  capture,
  captureHttpsCount,
  liveCertificateExists,
  liveProxyAddressHint,
  liveRuntimeAvailable,
  liveStatusText,
  recommendationAvailable,
}: {
  capture: TrafficCaptureResponse | null;
  captureHttpsCount: number;
  liveCertificateExists: boolean;
  liveProxyAddressHint: string | null;
  liveRuntimeAvailable: boolean;
  liveStatusText: string;
  recommendationAvailable: boolean;
}): string {
  if (!recommendationAvailable) {
    if (!liveRuntimeAvailable) {
      return "先让抓包引擎就绪，再判断是否需要补充 SSL / 网络 Hook。";
    }
    if (!liveProxyAddressHint || !liveCertificateExists) {
      return "先完成代理和证书，再观察 HTTPS 是否能拿到明文；只有仍失败时再回到 Hook 工作台。";
    }
    return "先抓到一轮 HTTPS 请求，再判断是否需要补充 SSL / 网络 Hook。";
  }

  if (!liveProxyAddressHint || !liveCertificateExists) {
    return "先完成代理和证书；如果 HTTPS 仍报证书错误、握手失败或没有明文，再把当前 SSL 建议加入 Hook 计划。";
  }
  if (capture !== null && captureHttpsCount > 0) {
    return "已经有 HTTPS 流量时，优先看是否仍有证书错误、握手失败或关键字段没有明文；命中这些情况时再把当前 SSL 建议加入 Hook 计划。";
  }
  if (liveStatusText === "抓包中") {
    return "先在当前抓包会话里复现登录、上报或心跳；如果 HTTPS 仍没有明文，再把当前 SSL 建议加入 Hook 计划。";
  }
  if (!liveRuntimeAvailable) {
    return "先让抓包引擎恢复可用，再判断是否要把当前 SSL 建议加入 Hook 计划。";
  }
  return "先启动抓包并复现关键 HTTPS 动作；只有证书错误、握手失败或没有明文时，再把当前 SSL 建议加入 Hook 计划。";
}

export function TrafficEvidencePanel({
  capture,
  externalContext,
  harErrorMessage,
  harImportMessage,
  isImporting,
  isSavingRuntimeSettings,
  isStartingLiveCapture,
  isStoppingLiveCapture,
  liveArtifactPath,
  liveCaptureListenHost,
  liveCaptureListenPort,
  liveCertificateDirectoryPath,
  liveCertificateExists,
  liveCertificateHelpText,
  liveCertificatePath,
  liveErrorMessage,
  liveInstallUrl,
  liveMessage,
  livePreview,
  liveProxyAddressHint,
  liveRuntimeAvailable,
  liveRuntimeDetail,
  liveRuntimeHelpText,
  liveSetupSteps,
  liveProxySteps,
  liveCertificateSteps,
  liveRecommendedActions,
  liveSetupStepDetails,
  liveProxyStepDetails,
  liveCertificateStepDetails,
  liveNetworkSummary,
  liveSslHookGuidance,
  liveRuntimeListenHost,
  liveRuntimeListenPort,
  liveStatusText,
  onAddRecommendationToPlan,
  onAddTemplateToPlan,
  onClearExternalContext,
  onInspectHookContext,
  onLiveCaptureListenHostChange,
  onLiveCaptureListenPortChange,
  onOpenPath,
  onHarPathChange,
  onImport,
  onSaveLiveCaptureSettings,
  onStartLiveCapture,
  onStopLiveCapture,
  runtimeSettingsError,
  runtimeSettingsMessage,
  startLiveCaptureDisabled,
  stopLiveCaptureDisabled,
  trafficRecommendations,
  harPath,
}: TrafficEvidencePanelProps): JSX.Element {
  const [isPickingFile, setIsPickingFile] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [copyErrorMessage, setCopyErrorMessage] = useState<string | null>(null);
  const portValidationMessage = validatePortInput(liveCaptureListenPort);
  const prioritizedPreviewItems = sortPreviewItems(livePreview?.items ?? []);
  const previewFocus = prioritizedPreviewItems[0] ?? null;
  const remainingPreviewItems = previewFocus
    ? prioritizedPreviewItems.filter((item) => item.flow_id !== previewFocus.flow_id)
    : prioritizedPreviewItems;
  const previewSuspiciousCount = prioritizedPreviewItems.filter((item) => item.suspicious).length;
  const previewIndicatorCount = prioritizedPreviewItems.filter((item) => item.matched_indicators.length > 0).length;
  const prioritizedCaptureFlows = sortCaptureFlows(capture?.flows ?? []);
  const captureFocus = prioritizedCaptureFlows[0] ?? null;
  const captureSummary = capture?.summary;
  const captureHttpsCount = captureSummary?.https_flow_count ?? capture?.https_flow_count ?? 0;
  const captureMatchedIndicatorCount =
    captureSummary?.matched_indicator_count ?? capture?.matched_indicator_count ?? 0;
  const captureTopHosts = captureSummary?.top_hosts ?? capture?.top_hosts ?? [];
  const captureSuspiciousHosts = captureSummary?.suspicious_hosts ?? capture?.suspicious_hosts ?? [];
  const normalizedSetupSteps = normalizeGuidanceSteps(liveSetupStepDetails, liveSetupSteps);
  const normalizedProxySteps = normalizeGuidanceSteps(liveProxyStepDetails, liveProxySteps);
  const normalizedCertificateSteps = normalizeGuidanceSteps(liveCertificateStepDetails, liveCertificateSteps);
  const fallbackHostSummary = Array.from(
    new Set(
      prioritizedCaptureFlows
        .map((flow) => extractHost(flow.url))
        .filter((host): host is string => Boolean(host)),
    ),
  )
    .slice(0, 3)
    .join("、");
  const captureHostSummary = summarizeHostGroups(captureTopHosts) || fallbackHostSummary;
  const prioritizedTrafficRecommendations = trafficRecommendations.slice(0, 2);
  const primaryTrafficRecommendation = prioritizedTrafficRecommendations[0] ?? null;
  const guidanceTemplateEntries =
    liveSslHookGuidance?.suggested_template_entries?.filter(
      (entry) =>
        entry.template_id.length > 0 &&
        entry.template_name.length > 0 &&
        entry.plugin_id.length > 0,
    ) ?? [];
  const primaryGuidanceTemplate = guidanceTemplateEntries[0] ?? null;
  const hasDirectSslGuidance = primaryTrafficRecommendation !== null || primaryGuidanceTemplate !== null;
  const hookStudioQuery = buildHookStudioQuery({
    guidanceTerms: liveSslHookGuidance?.suggested_terms ?? [],
    recommendation: primaryTrafficRecommendation,
  });
  const hookStudioHint = buildHookStudioHint({
    guidanceTerms: liveSslHookGuidance?.suggested_terms ?? [],
    recommendation: primaryTrafficRecommendation,
    templateName: primaryGuidanceTemplate?.template_name ?? null,
  });
  const workflowSummary = summarizeWorkflowSteps(normalizedSetupSteps);
  const proxyActionText = describeProxyAction(liveProxyAddressHint, normalizedProxySteps);
  const proxySupportText =
    pickFirstStep(normalizedProxySteps.filter((step) => step.trim() !== proxyActionText)) ??
    "代理保存后，测试设备就可以按当前地址接入抓包。";
  const certificateActionText = describeCertificateAction({
    liveCertificatePath,
    liveCertificateSteps: normalizedCertificateSteps,
    liveInstallUrl,
  });
  const certificateSupportText =
    pickFirstStep(normalizedCertificateSteps.filter((step) => step.trim() !== certificateActionText)) ??
    liveCertificateHelpText ??
    "安装证书后，优先验证登录、上报、心跳这类 HTTPS 请求是否能看到明文。";
  const sslActionText = describeSslRecommendationTiming({
    capture,
    captureHttpsCount,
    liveCertificateExists,
    liveProxyAddressHint,
    liveRuntimeAvailable,
    liveStatusText,
    recommendationAvailable: hasDirectSslGuidance,
  });
  const sslSupportText =
    liveRecommendedActions[0] ??
    describeSslGuidanceSummary(liveSslHookGuidance) ??
    primaryTrafficRecommendation?.reason ??
    "如果当前流量已经足够清晰，就先保持面板轻量，不急着叠更多 Hook。";
  const networkSummaryText = describeNetworkSummary(liveNetworkSummary);
  const nextStepText = deriveNextStepText({
    capture,
    liveCertificateExists,
    liveProxyAddressHint,
    liveRuntimeAvailable,
    liveStatusText,
  });

  // C7: 复制成功 / 失败提示 3 秒后自动消失，避免回到面板看到陈旧反馈。
  useEffect(() => {
    if (copyMessage === null && copyErrorMessage === null) {
      return undefined;
    }
    const timerId = window.setTimeout(() => {
      setCopyMessage(null);
      setCopyErrorMessage(null);
    }, 3000);
    return () => window.clearTimeout(timerId);
  }, [copyMessage, copyErrorMessage]);

  async function handlePickHarFile(): Promise<void> {
    setIsPickingFile(true);
    try {
      const selected = await pickHarFile();
      if (selected) {
        onHarPathChange(selected);
      }
    } catch {
      // ignore and leave manual path entry available
    } finally {
      setIsPickingFile(false);
    }
  }

  async function handleCopy(value: string): Promise<void> {
    setCopyMessage(null);
    setCopyErrorMessage(null);
    try {
      await copyTextToClipboard(value);
      setCopyMessage("已复制到剪贴板。");
    } catch {
      setCopyErrorMessage("复制失败，请手动复制。");
    }
  }

  return (
    <section className="workspace-panel traffic-evidence-panel" aria-labelledby="traffic-evidence-title">
      <h3 id="traffic-evidence-title">流量证据</h3>
      <p>把抓包准备、实时预览、HAR 导入和网络 Hook 联动收在同一个面板里，默认先看摘要，再按需展开细节。</p>
      {externalContext ? (
        <div className="detail-card hook-context-banner" aria-live="polite">
          <div>
            <strong>{externalContext.title}</strong>
            <p>{externalContext.summary}</p>
            {externalContext.recommendation_title ? <p>{`焦点推荐：${externalContext.recommendation_title}`}</p> : null}
          </div>
          <button type="button" className="button-ghost" onClick={onClearExternalContext}>
            收起提示
          </button>
        </div>
      ) : null}

      <div className="metric-grid metric-grid--four">
        <div className="detail-card">
          <strong>实时状态</strong>
          <p>{`实时抓包状态：${liveStatusText}`}</p>
          <p>{`最近产物路径：${liveArtifactPath ?? "暂无"}`}</p>
        </div>
        <div className="detail-card">
          <strong>抓包引擎</strong>
          <p>{liveRuntimeDetail ?? "等待环境探测结果"}</p>
          <p>{liveRuntimeAvailable ? "当前可直接进入抓包准备。" : "当前还不能直接开始实时抓包。"}</p>
          {networkSummaryText ? <p>{networkSummaryText}</p> : null}
        </div>
        <div className="detail-card">
          <strong>已导入流量</strong>
          <p>{capture ? `${capture.flow_count} 条流量，${capture.suspicious_count} 条可疑` : "暂未导入 HAR 证据"}</p>
          <p>{captureHostSummary ? `主机摘要：${captureHostSummary}` : "等待导入 HAR 或实时抓包产物"}</p>
        </div>
        <div className="detail-card">
          <strong>Hook 联动</strong>
          <p>
            {trafficRecommendations.length > 0
              ? `${trafficRecommendations.length} 条网络建议可直接加入计划`
              : guidanceTemplateEntries.length > 0
                ? `${guidanceTemplateEntries.length} 条 SSL 模板建议可直接加入计划`
                : "暂无网络/SSL 相关建议"}
          </p>
          <p>这里只保留网络、SSL、HTTPS 相关项，避免和 Hook 工作台重复堆叠。</p>
        </div>
      </div>

      <div className="detail-card">
        <strong>{capture ? "已导入流量摘要" : "抓包工作流摘要"}</strong>
        {captureFocus ? (
          <>
            <p>{`${captureFocus.method} · ${formatStatusCode(captureFocus.status_code)} · ${captureFocus.url}`}</p>
            <p>{describeCaptureFocus(captureFocus)}</p>
            <p>{`HTTPS 请求：${captureHttpsCount} 条；命中线索：${captureMatchedIndicatorCount} 次。`}</p>
            {captureSuspiciousHosts.length > 0 ? (
              <p>{`优先主机：${summarizeSuspiciousHosts(captureSuspiciousHosts)}`}</p>
            ) : null}
          </>
        ) : (
          <>
            <p>{capture ? "当前 HAR 暂无可展示的重点流量。" : "当前还没有导入流量证据。你可以先实时抓包，或导入现成 HAR。"}</p>
            <p>{nextStepText}</p>
          </>
        )}
      </div>

      <div className="subsurface">
        <h4>抓包准备清单</h4>
        <ul className="compact-list compact-list--cards" aria-label="抓包准备清单">
          <li>
            <strong>抓包引擎</strong>
            <span className={`status-pill ${liveRuntimeAvailable ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveRuntimeAvailable ? "已就绪" : "未就绪"}</strong>
              {liveRuntimeDetail ?? "等待检测"}
            </span>
          </li>
          <li>
            <strong>代理地址</strong>
            <span className={`status-pill ${liveProxyAddressHint ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveProxyAddressHint ? "可下发" : "待确认"}</strong>
              {liveProxyAddressHint ?? "先保存抓包参数以生成代理地址"}
            </span>
          </li>
          <li>
            <strong>证书状态</strong>
            <span className={`status-pill ${liveCertificateExists ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveCertificateExists ? "证书已就绪" : "证书待安装"}</strong>
              {liveCertificatePath ?? "可通过 mitm.it 安装或检查证书输出目录"}
            </span>
          </li>
          <li>
            <strong>安装入口</strong>
            <span className={`status-pill ${liveInstallUrl ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveInstallUrl ? "可直接访问" : "未提供"}</strong>
              {liveInstallUrl ?? "当前运行时没有提供安装入口 URL"}
            </span>
          </li>
        </ul>
        <p>{`下一步提示：${nextStepText}`}</p>
        {liveSslHookGuidance ? (
          <p>{`当前 SSL / 网络建议：${liveSslHookGuidance.summary}`}</p>
        ) : null}
      </div>

      <div className="subsurface">
        <h4>下一步操作卡片</h4>
        <p>{workflowSummary ? `默认顺序：${workflowSummary}` : `默认顺序：${nextStepText}`}</p>
        <ul className="compact-list compact-list--cards" aria-label="下一步操作卡片">
          <li>
            <strong>1. 配置代理</strong>
            <span className={`status-pill ${liveProxyAddressHint ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveProxyAddressHint ? "现在可配" : "先确认地址"}</strong>
              {liveProxyAddressHint ? "设备代理已具备下发条件" : "先保存抓包参数"}
            </span>
            <span>{proxyActionText}</span>
            <span>{proxySupportText}</span>
            {liveProxyAddressHint ? (
              <div className="button-row">
                <button type="button" className="button-secondary" onClick={() => void handleCopy(liveProxyAddressHint)}>
                  复制这一步的代理地址
                </button>
              </div>
            ) : null}
          </li>
          <li>
            <strong>2. 安装证书</strong>
            <span className={`status-pill ${liveCertificateExists ? "status-pill--ready" : "status-pill--down"}`}>
              <strong>{liveCertificateExists ? "已可验证" : "优先安装"}</strong>
              {liveCertificateExists ? "证书已可用于验证 HTTPS" : "优先使用浏览器安装或导出证书"}
            </span>
            <span>{certificateActionText}</span>
            <span>{certificateSupportText}</span>
            <div className="button-row">
              {liveInstallUrl ? (
                <button type="button" className="button-secondary" onClick={() => void handleCopy(liveInstallUrl)}>
                  复制这一步的安装地址
                </button>
              ) : null}
              {liveCertificateExists && liveCertificatePath ? (
                <button type="button" className="button-secondary" onClick={() => onOpenPath(liveCertificatePath)}>
                  打开这一步的证书文件
                </button>
              ) : null}
            </div>
          </li>
          <li>
            <strong>3. 评估 SSL / 网络 Hook</strong>
            <span
              className={`status-pill ${
                hasDirectSslGuidance || liveSslHookGuidance?.recommended ? "status-pill--ready" : "status-pill--down"
              }`}
            >
              <strong>{hasDirectSslGuidance || liveSslHookGuidance?.recommended ? "建议已准备" : "暂无现成建议"}</strong>
              {primaryTrafficRecommendation
                ? "已根据当前流量线索归纳出一条 SSL / 网络建议"
                : primaryGuidanceTemplate
                  ? "已根据 live capture guidance 准备一条可直接加入计划的 SSL 模板"
                  : liveSslHookGuidance?.summary ?? "先看抓包结果再决定是否需要补 Hook"}
            </span>
            {primaryTrafficRecommendation ? <span>{`当前候选：${primaryTrafficRecommendation.title}`}</span> : null}
            {!primaryTrafficRecommendation && primaryGuidanceTemplate ? (
              <span>{`当前候选：${primaryGuidanceTemplate.template_name}`}</span>
            ) : null}
            {!primaryTrafficRecommendation && liveSslHookGuidance?.suggested_templates.length ? (
              <span>{`候选模板：${liveSslHookGuidance.suggested_templates.join("、")}`}</span>
            ) : null}
            <span>{sslActionText}</span>
            <span>{sslSupportText}</span>
            {primaryTrafficRecommendation ? (
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onAddRecommendationToPlan(primaryTrafficRecommendation.recommendation_id)}
                >
                  将当前 SSL 建议加入计划
                </button>
                <button
                  type="button"
                  className="button-ghost"
                  onClick={() =>
                    onInspectHookContext({
                      hint: hookStudioHint,
                      query: hookStudioQuery,
                      scope: "related_candidates",
                    })
                  }
                >
                  在 Hook 工作台中查看 SSL/网络线索
                </button>
              </div>
            ) : guidanceTemplateEntries.length ? (
              <div className="button-row">
                {guidanceTemplateEntries.map((entry) => (
                  <button
                    key={entry.source_id}
                    type="button"
                    className="button-secondary"
                    onClick={() =>
                      onAddTemplateToPlan({
                        template_id: entry.template_id as string,
                        template_name: entry.template_name as string,
                        plugin_id: entry.plugin_id as string,
                      })
                    }
                  >
                    {`将 ${entry.template_name} 加入计划`}
                  </button>
                ))}
                <button
                  type="button"
                  className="button-ghost"
                  onClick={() =>
                    onInspectHookContext({
                      hint: hookStudioHint,
                      query: hookStudioQuery,
                      scope: "related_candidates",
                    })
                  }
                >
                  在 Hook 工作台中查看 SSL/网络线索
                </button>
              </div>
            ) : null}
          </li>
        </ul>
      </div>

      <div className="subsurface">
        <h4>实时抓包</h4>
        {liveRuntimeDetail ? <p>{`抓包引擎：${liveRuntimeDetail}`}</p> : null}
        {liveRuntimeHelpText ? <p>{liveRuntimeHelpText}</p> : null}
        <label>
          抓包监听地址
          <input
            aria-label="抓包监听地址"
            type="text"
            value={liveCaptureListenHost}
            onChange={(event) => onLiveCaptureListenHostChange(event.target.value)}
            placeholder="例如：0.0.0.0"
          />
        </label>
        <label>
          抓包监听端口
          <input
            aria-label="抓包监听端口"
            aria-invalid={portValidationMessage !== null}
            aria-describedby={portValidationMessage ? "live-capture-port-hint" : undefined}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            value={liveCaptureListenPort}
            onChange={(event) => onLiveCaptureListenPortChange(event.target.value)}
            placeholder="例如：8080（1 – 65535）"
          />
        </label>
        {portValidationMessage ? (
          <p id="live-capture-port-hint" role="alert">{portValidationMessage}</p>
        ) : null}
        <p>{`当前生效：${liveRuntimeListenHost}:${liveRuntimeListenPort}`}</p>
        <p>保存后会更新内置 Mitmdump 的监听地址；自定义抓包命令也可使用 {"{listen_host}"} / {"{listen_port}"} 占位符。</p>
        <div className="button-row">
          <button
            type="button"
            onClick={onSaveLiveCaptureSettings}
            disabled={isSavingRuntimeSettings || portValidationMessage !== null}
          >
            {isSavingRuntimeSettings ? "正在保存..." : "保存抓包参数"}
          </button>
          <button type="button" onClick={onStartLiveCapture} disabled={startLiveCaptureDisabled}>
            {isStartingLiveCapture ? "正在启动..." : "开始实时抓包"}
          </button>
          <button type="button" onClick={onStopLiveCapture} disabled={stopLiveCaptureDisabled}>
            {isStoppingLiveCapture ? "正在停止..." : "停止实时抓包"}
          </button>
        </div>
        {runtimeSettingsMessage ? <p>{runtimeSettingsMessage}</p> : null}
        {runtimeSettingsError ? <p role="alert">{runtimeSettingsError}</p> : null}
        {liveProxyAddressHint ? (
          <p>
            代理地址：{liveProxyAddressHint}
            <button type="button" onClick={() => void handleCopy(liveProxyAddressHint)}>
              复制代理地址
            </button>
          </p>
        ) : null}
        {liveInstallUrl ? (
          <p>
            安装地址：{liveInstallUrl}
            <button type="button" onClick={() => void handleCopy(liveInstallUrl)}>
              复制安装地址
            </button>
          </p>
        ) : null}
        {liveCertificatePath ? (
          <p>
            证书路径：{liveCertificatePath}
            <button type="button" onClick={() => void handleCopy(liveCertificatePath)}>
              复制证书路径
            </button>
          </p>
        ) : null}
        {liveCertificateHelpText ? <p>{liveCertificateHelpText}</p> : null}
        {liveCertificateExists && liveCertificatePath ? (
          <button type="button" onClick={() => onOpenPath(liveCertificatePath)}>
            打开证书文件
          </button>
        ) : null}
        {liveCertificateDirectoryPath ? (
          <button type="button" onClick={() => onOpenPath(liveCertificateDirectoryPath)}>
            打开证书目录
          </button>
        ) : null}
        {liveMessage ? <p>{liveMessage}</p> : null}
        {liveErrorMessage ? <p role="alert">{liveErrorMessage}</p> : null}
        {copyMessage ? <p>{copyMessage}</p> : null}
        {copyErrorMessage ? <p role="alert">{copyErrorMessage}</p> : null}
      </div>

      {livePreview && (livePreview.items.length > 0 || livePreview.preview_path) ? (
        <div className="subsurface">
          <h4>最近请求预览</h4>
          {previewFocus ? (
            <div className="detail-card">
              <strong>{`${previewFocus.method} · ${previewFocus.status_code ?? "未知"} · ${previewFocus.url}`}</strong>
              <p>{describePreviewFocus(previewFocus)}</p>
              <p>{`时间：${formatTimestampLabel(previewFocus.timestamp)}`}</p>
              {previewFocus.matched_indicators.length > 0 ? (
                <p>{`命中线索：${previewFocus.matched_indicators.join("、")}`}</p>
              ) : (
                <p>未命中已知回连线索</p>
              )}
            </div>
          ) : null}
          {livePreview.preview_path ? <p>{`预览文件：${livePreview.preview_path}`}</p> : null}
          <p>{`当前预览共 ${prioritizedPreviewItems.length} 条请求摘要，其中 ${previewSuspiciousCount} 条可疑，${previewIndicatorCount} 条命中线索。`}</p>
          {livePreview.truncated ? <p>当前仅展示最近一批请求摘要。</p> : null}
          {remainingPreviewItems.length > 0 ? (
            <details className="brief-disclosure">
              <summary>{`展开最近请求列表（${remainingPreviewItems.length} 条补充请求）`}</summary>
              <div className="brief-disclosure__content">
                <ul className="compact-list compact-list--cards" aria-label="实时抓包预览列表">
                  {remainingPreviewItems.map((item) => (
                    <li key={item.flow_id}>
                      <strong>{`${item.method} · ${item.status_code ?? "未知"} · ${item.url}`}</strong>
                      <span>{`时间：${formatTimestampLabel(item.timestamp)}`}</span>
                      {item.matched_indicators.length > 0 ? (
                        <span>{`命中线索：${item.matched_indicators.join("、")}`}</span>
                      ) : (
                        <span>未命中已知回连线索</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          ) : null}
        </div>
      ) : null}

      {trafficRecommendations.length > 0 ? (
        <div className="subsurface">
          <h4>Hook 联动建议</h4>
          <p>这里只显示网络、HTTPS、SSL 相关建议，点击后会直接同步到 Hook 工作台，不重复展开完整细节。</p>
          {liveRecommendedActions.length > 0 ? (
            <div className="detail-card">
              <strong>推荐动作</strong>
              <ul className="compact-list" aria-label="抓包推荐动作">
                {liveRecommendedActions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <ul className="compact-list compact-list--cards" aria-label="流量相关 Hook 建议列表">
            {prioritizedTrafficRecommendations.map((recommendation) => (
              <li
                key={recommendation.recommendation_id}
                data-active={
                  externalContext?.recommendation_id === recommendation.recommendation_id ? "true" : undefined
                }
              >
                <strong>{recommendation.title}</strong>
                <span>{recommendation.reason}</span>
                <span>{renderRecommendationHint(recommendation)}</span>
                {recommendation.matched_terms.length > 0 ? (
                  <span>{`命中词：${recommendation.matched_terms.join("、")}`}</span>
                ) : null}
                <div className="button-row">
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => onAddRecommendationToPlan(recommendation.recommendation_id)}
                  >
                    加入 Hook 计划
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {trafficRecommendations.length > prioritizedTrafficRecommendations.length ? (
            <p>{`其余 ${trafficRecommendations.length - prioritizedTrafficRecommendations.length} 条网络建议仍可在 Hook 工作台继续查看。`}</p>
          ) : null}
        </div>
      ) : null}

      <div className="subsurface">
        <h4>HAR 导入</h4>
        <label>
          HAR 文件路径
          <input
            aria-label="HAR 文件路径"
            type="text"
            value={harPath}
            onChange={(event) => onHarPathChange(event.target.value)}
            placeholder="输入或选择本地 HAR 文件路径"
          />
        </label>
        <div className="button-row">
          <button type="button" onClick={() => void handlePickHarFile()} disabled={isPickingFile}>
            {isPickingFile ? "正在选择..." : "选择 HAR 文件"}
          </button>
          <button type="button" onClick={onImport} disabled={isImporting}>
            {isImporting ? "正在导入..." : "导入 HAR"}
          </button>
        </div>
        {harImportMessage ? <p>{harImportMessage}</p> : null}
        {harErrorMessage ? <p role="alert">{harErrorMessage}</p> : null}
      </div>

      {capture !== null ? (
        <div className="subsurface">
          <h4>已导入流量摘要</h4>
          <p>已加载流量证据</p>
          <p>{`来源类型：${capture.provenance.label}`}</p>
          <p>{`来源路径：${capture.source_path}`}</p>
          <p>{`总流量：${capture.flow_count}`}</p>
          <p>{`可疑流量：${capture.suspicious_count}`}</p>
          <p>{`HTTPS 请求：${captureHttpsCount}`}</p>
          <p>{`命中线索：${captureMatchedIndicatorCount}`}</p>
          <details className="brief-disclosure">
            <summary>展开主机摘要</summary>
            <div className="brief-disclosure__content">
              <div className="detail-card">
                <strong>Top Hosts</strong>
                <p>{captureHostSummary || "暂无主机摘要"}</p>
              </div>
              <div className="detail-card">
                <strong>可疑主机</strong>
                <p>{summarizeSuspiciousHosts(captureSuspiciousHosts)}</p>
              </div>
            </div>
          </details>
          <div className="button-row">
            <button type="button" onClick={() => onOpenPath(capture.source_path)}>
              打开来源文件
            </button>
          </div>
          <details className="brief-disclosure">
            <summary>{`展开详细 flows（${capture.flows.length} 条）`}</summary>
            <div className="brief-disclosure__content">
              <ul className="compact-list compact-list--cards" aria-label="流量列表">
                {prioritizedCaptureFlows.length === 0 ? <li>当前 HAR 中没有可展示的流量。</li> : null}
                {prioritizedCaptureFlows.map((flow) => (
                  <li key={flow.flow_id}>
                    <strong>{flow.url}</strong>
                    <p>{`${flow.method} · 状态码 ${formatStatusCode(flow.status_code)} · ${flow.suspicious ? "可疑" : "普通"}`}</p>
                    {flow.matched_indicators.length > 0 ? (
                      <p>{`命中线索：${flow.matched_indicators.join("、")}`}</p>
                    ) : null}
                    {flow.request_preview ? <p>{`请求预览：${flow.request_preview}`}</p> : null}
                    {flow.response_preview ? <p>{`响应预览：${flow.response_preview}`}</p> : null}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      ) : (
        <p>当前还没有导入流量证据。</p>
      )}
    </section>
  );
}
