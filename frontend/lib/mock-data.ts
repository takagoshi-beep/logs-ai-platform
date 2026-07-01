export const kpis = [
  { id: "k1", label: "今日の対応件数", value: "9", trend: "-2 vs yesterday" },
  { id: "k2", label: "注意が必要な案件", value: "2", trend: "No change" },
  { id: "k3", label: "確認待ちの提案資料", value: "4", trend: "+1 this morning" },
  { id: "k4", label: "AI提案の採用率", value: "59%", trend: "+4pt this week" },
];

export const todayUrgentCases = [
  { id: "u1", project: "Fanatics OEM", title: "Delivery confirmation by 16:00", due: "Today 16:00", owner: "Sato", status: "対応中" },
  { id: "u2", project: "BEAMS Retail", title: "Proposal storyline sign-off", due: "Today 18:00", owner: "Takagi", status: "未着手" },
  { id: "u3", project: "GOLDWIN Campaign", title: "Quote revision approval", due: "Tomorrow 10:00", owner: "Kato", status: "未着手" },
];

export const alerts = [
  {
    id: "al1",
    level: "high",
    title: "Unpurchased sales risk",
    message: "Project FAN-204 has pending purchase decisions that can impact July delivery slots.",
  },
  {
    id: "al2",
    level: "medium",
    title: "Margin trend drop",
    message: "BEAMS accessories gross margin is down 3.8pt compared to last month.",
  },
];

export const recommendedActions = [
  {
    id: "ra1",
    title: "Open Fanatics workspace and lock owner tasks",
    reason: "Two blocking tasks are waiting for assignment.",
    href: "/workspace/fanatics-oem",
  },
  {
    id: "ra2",
    title: "Move BEAMS proposal to review",
    reason: "Client review starts tomorrow morning.",
    href: "/proposals",
  },
  {
    id: "ra3",
    title: "Ask AI for GOLDWIN response plan",
    reason: "Quote response exceeded target SLA by 1 day.",
    href: "/chat",
  },
];

export const inProgressWork = [
  {
    id: "w1",
    project: "Fanatics OEM",
    owner: "Sato",
    stage: "Supplier coordination",
    progress: 62,
  },
  {
    id: "w2",
    project: "BEAMS Retail",
    owner: "Takagi",
    stage: "Proposal assembly",
    progress: 78,
  },
  {
    id: "w3",
    project: "GOLDWIN Campaign",
    owner: "Kato",
    stage: "Quote revision",
    progress: 40,
  },
];

export const aiSuggestions = [
  {
    id: "s1",
    title: "Prioritize purchase approval before shipment booking",
    confidence: "confidence 0.83",
    next: "Create approval request task set",
  },
  {
    id: "s2",
    title: "Use margin defense narrative in BEAMS slide 3",
    confidence: "confidence 0.79",
    next: "Insert benchmark chart from Q2 results",
  },
];

export const taskRecommendations = [
  {
    id: "t1",
    project: "Fanatics OEM",
    title: "納期リスクの原因を確認する",
    due: "本日15:30",
    priority: "High",
    status: "対応中",
    reason: "出荷枠の確保期限が本日中のため。",
    owner: "佐藤",
  },
  {
    id: "t2",
    project: "BEAMS Retail",
    title: "提案資料のストーリーラインを確定する",
    due: "本日18:00",
    priority: "High",
    status: "未着手",
    reason: "レビュー担当からコスト説明の更新依頼があったため。",
    owner: "高越",
  },
  {
    id: "t3",
    project: "GOLDWIN Campaign",
    title: "見積ドラフト一式を準備する",
    due: "明日10:00",
    priority: "Medium",
    status: "未着手",
    reason: "顧客から条件変更の依頼があったため。",
    owner: "加藤",
  },
  {
    id: "t4",
    project: "newhattan sales kit",
    title: "法務確認が終わるまでローンチ文言を保留する",
    due: "今週中",
    priority: "Low",
    status: "保留",
    reason: "商標に関する確認待ちのため。",
    owner: "-",
  },
];

export const projects = [
  {
    id: "fanatics-oem",
    name: "Fanatics OEM",
    summary: "Delivery risk monitoring and cost control",
    customer: "Fanatics",
    owner: "佐藤",
    status: "対応中",
    updatedAt: "今日",
    nextAction: "納期確認",
  },
  {
    id: "beams-retail",
    name: "BEAMS Retail",
    summary: "Proposal and assortment optimization",
    customer: "BEAMS",
    owner: "高越",
    status: "未着手",
    updatedAt: "昨日",
    nextAction: "提案資料確認",
  },
  {
    id: "goldwin-campaign",
    name: "GOLDWIN Campaign",
    summary: "Quote and production planning support",
    customer: "GOLDWIN",
    owner: "加藤",
    status: "保留",
    updatedAt: "7/1",
    nextAction: "見積作成",
  },
  {
    id: "newhattan-sales-kit",
    name: "newhattan sales kit",
    summary: "Launch copy and sales kit preparation",
    customer: "newhattan",
    owner: "-",
    status: "保留",
    updatedAt: "6/28",
    nextAction: "商標確認",
  },
];

export const proposalDraft = {
  customer: "BEAMS",
  purpose: "OEM proposal review",
  referenceData: [
    "Sales trend (last 6 months)",
    "Margin by category",
    "Past proposal outcomes",
    "Competitor pricing snapshot",
  ],
  outline: [
    "Current challenge and business impact",
    "Opportunity hypothesis and strategy",
    "Recommended action plan",
    "Expected impact, risk, and governance",
  ],
  reviewStatus: "社内確認待ち",
  nextAction: "Generate PowerPoint and request manager approval",
};

export const pastProposals = [
  { id: "doc1", title: "BEAMS提案資料", date: "2026/06/20" },
  { id: "doc2", title: "Fanatics提案資料", date: "2026/06/15" },
  { id: "doc3", title: "GOLDWIN企画書", date: "2026/06/10" },
];

export const pastConsultations = [
  { id: "chat1", title: "Fanatics納期相談" },
  { id: "chat2", title: "BEAMS提案相談" },
  { id: "chat3", title: "GOLDWIN見積相談" },
];

export const workspaceHistory = [
  { id: "wh1", title: "Owner assignment completed", time: "09:10", detail: "2 tasks assigned to operations." },
  { id: "wh2", title: "AI proposal draft updated", time: "09:45", detail: "Inserted margin defense section." },
  { id: "wh3", title: "Stakeholder update sent", time: "10:20", detail: "Delivery risk summary shared to channel." },
];

export const executionHistory = [
  { id: "ex-1001", type: "Proposal Draft", title: "BEAMS Q3 OEM proposal", status: "Generated", at: "2026-06-30 09:14" },
  { id: "ex-1002", type: "Task Recommendation", title: "Fanatics risk action set", status: "Accepted", at: "2026-06-30 09:36" },
  { id: "ex-1003", type: "Document Draft", title: "GOLDWIN quote response", status: "Pending Approval", at: "2026-06-30 10:01" },
];

export const debugTrace = {
  intent: "Proposal",
  meaning: "customer_proposal_draft",
  knowledge: ["Internal Database", "Business Rules", "Market Trend"],
  memory: ["customer_memory", "proposal_memory", "project_memory"],
  capability: ["Knowledge Retrieval", "Data Query", "Document Generation"],
  validation: "pass",
  evaluation: "task_planning_accuracy: 0.688",
  runtimeLogs: ["planner:ok", "capability_router:ok", "validator:ok"],
};
