import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";
import {
  getWorkspaceDetail,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  openWorkspaceInJadx,
} from "../lib/api";
import type {
  HookRecommendationSummary,
  WorkspaceDetailResponse,
  WorkspaceMethodSummary,
} from "../lib/types";

const METHOD_LIMIT = 12;
const RECOMMENDATION_LIMIT = 6;

export function CaseWorkspacePage(): JSX.Element {
  const { caseId } = useParams<{ caseId: string }>();
  const [detail, setDetail] = useState<WorkspaceDetailResponse | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(Boolean(caseId));
  const [searchValue, setSearchValue] = useState("");
  const [methodQuery, setMethodQuery] = useState("");
  const [methods, setMethods] = useState<WorkspaceMethodSummary[]>([]);
  const [methodTotal, setMethodTotal] = useState(0);
  const [isLoadingMethods, setIsLoadingMethods] = useState(false);
  const [methodsError, setMethodsError] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<HookRecommendationSummary[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);
  const [isOpeningInJadx, setIsOpeningInJadx] = useState(false);
  const [openJadxMessage, setOpenJadxMessage] = useState<string | null>(null);
  const [openJadxError, setOpenJadxError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) {
      setDetail(null);
      setDetailError(null);
      setIsLoadingDetail(false);
      setSearchValue("");
      setMethodQuery("");
      setMethods([]);
      setMethodTotal(0);
      setMethodsError(null);
      setRecommendations([]);
      setRecommendationsError(null);
      setOpenJadxMessage(null);
      setOpenJadxError(null);
      return;
    }

    let active = true;
    setIsLoadingDetail(true);
    setDetailError(null);
    setDetail(null);
    setSearchValue("");
    setMethodQuery("");
    setMethods([]);
    setMethodTotal(0);
    setMethodsError(null);
    setRecommendations([]);
    setRecommendationsError(null);
    setOpenJadxMessage(null);
    setOpenJadxError(null);

    void getWorkspaceDetail(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setDetail(response);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setDetail(null);
        setDetailError("案件工作台暂时不可用。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId || !detail) {
      return;
    }

    let active = true;
    setIsLoadingRecommendations(true);
    setRecommendationsError(null);

    void getWorkspaceRecommendations(caseId, { limit: RECOMMENDATION_LIMIT })
      .then((response) => {
        if (!active) {
          return;
        }
        setRecommendations(response.items);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setRecommendations([]);
        setRecommendationsError("离线推荐暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingRecommendations(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail || !detail.has_method_index) {
      setMethods([]);
      setMethodTotal(0);
      setMethodsError(null);
      setIsLoadingMethods(false);
      return;
    }

    let active = true;
    setIsLoadingMethods(true);
    setMethodsError(null);

    void getWorkspaceMethods(caseId, { query: methodQuery.trim(), limit: METHOD_LIMIT })
      .then((response) => {
        if (!active) {
          return;
        }
        setMethods(response.items);
        setMethodTotal(response.total);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setMethods([]);
        setMethodTotal(0);
        setMethodsError("方法索引暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingMethods(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail, methodQuery]);

  async function handleOpenInJadx(): Promise<void> {
    if (!caseId || !detail?.can_open_in_jadx) {
      return;
    }

    setIsOpeningInJadx(true);
    setOpenJadxMessage(null);
    setOpenJadxError(null);

    try {
      await openWorkspaceInJadx(caseId);
      setOpenJadxMessage("已请求打开 JADX。");
    } catch {
      setOpenJadxError("打开 JADX 失败，请检查本机配置。");
    } finally {
      setIsOpeningInJadx(false);
    }
  }

  function handleMethodSearch(): void {
    if (!detail?.has_method_index) {
      return;
    }

    setMethodQuery(searchValue.trim());
  }

  return (
    <section aria-labelledby="case-workspace-title">
      <h2 id="case-workspace-title">案件工作台</h2>
      <p>浏览静态简报、方法索引和离线 Hook 推荐，必要时可以直接打开本地 JADX。</p>
      {caseId ? <p>案件编号：{caseId}</p> : <p>请先从案件队列选择一个案件进入工作台。</p>}
      {isLoadingDetail ? <p>正在加载工作区数据...</p> : null}
      {!isLoadingDetail && detail ? <p>当前案件：{detail.title}</p> : null}
      <StaticBriefPanel detail={detail} errorMessage={detailError} isLoading={isLoadingDetail} />
      <HookStudioPanel
        canOpenInJadx={Boolean(detail?.can_open_in_jadx)}
        hasMethodIndex={Boolean(detail?.has_method_index)}
        isLoadingMethods={isLoadingMethods}
        isLoadingRecommendations={isLoadingRecommendations}
        isOpeningInJadx={isOpeningInJadx}
        methodTotal={methodTotal}
        methods={methods}
        openJadxError={openJadxError}
        openJadxMessage={openJadxMessage}
        onMethodQueryChange={setSearchValue}
        onMethodSearch={handleMethodSearch}
        onOpenInJadx={() => {
          void handleOpenInJadx();
        }}
        recommendations={recommendations}
        recommendationsError={recommendationsError}
        searchError={methodsError}
        searchValue={searchValue}
      />
    </section>
  );
}
