export const kpis = [
  { id: "k1", label: "Today Open Actions", value: "9", trend: "-2 vs yesterday" },
  { id: "k2", label: "High Risk Projects", value: "2", trend: "No change" },
  { id: "k3", label: "Proposal Review Ready", value: "4", trend: "+1 this morning" },
  { id: "k4", label: "AI Suggestion Accepted", value: "59%", trend: "+4pt this week" },
];

export const todayUrgentCases = [
  { id: "u1", project: "Fanatics OEM", title: "Delivery confirmation by 16:00", due: "Today 16:00", owner: "Sato", status: "In Progress" },
  { id: "u2", project: "BEAMS Retail", title: "Proposal storyline sign-off", due: "Today 18:00", owner: "Takagi", status: "Open" },
  { id: "u3", project: "GOLDWIN Campaign", title: "Quote revision approval", due: "Tomorrow 10:00", owner: "Kato", status: "Open" },
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
    title: "Confirm delivery risk root cause",
    due: "Today 15:30",
    priority: "High",
    status: "In Progress",
    reason: "Shipping slot lock expires today.",
  },
  {
    id: "t2",
    project: "BEAMS Retail",
    title: "Finalize proposal storyline",
    due: "Today 18:00",
    priority: "High",
    status: "Open",
    reason: "Reviewer requested cost narrative update.",
  },
  {
    id: "t3",
    project: "GOLDWIN Campaign",
    title: "Prepare quote draft package",
    due: "Tomorrow 10:00",
    priority: "Medium",
    status: "Open",
    reason: "Customer requested revised conditions.",
  },
  {
    id: "t4",
    project: "newhattan sales kit",
    title: "Hold launch copy until legal review",
    due: "This Week",
    priority: "Low",
    status: "On Hold",
    reason: "Trademark statement is pending confirmation.",
  },
];

export const projects = [
  {
    id: "fanatics-oem",
    name: "Fanatics OEM",
    summary: "Delivery risk monitoring and cost control",
    owner: "Sato",
    status: "In Progress",
  },
  {
    id: "beams-retail",
    name: "BEAMS Retail",
    summary: "Proposal and assortment optimization",
    owner: "Takagi",
    status: "Open",
  },
  {
    id: "goldwin-campaign",
    name: "GOLDWIN Campaign",
    summary: "Quote and production planning support",
    owner: "Kato",
    status: "Open",
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
  reviewStatus: "Ready for internal review",
  nextAction: "Generate PowerPoint and request manager approval",
};

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
