const { useEffect, useMemo, useRef, useState } = React;

const PROJECT_TYPES = [
  {
    key: "major_hospitals",
    name: "المستشفيات الكبرى",
    description: "إعطاء الأولوية للمجمعات الطبية الحيوية مثل الشفاء وناصر.",
    icon: "✚",
    tone: "critical",
  },
  {
    key: "healthcare",
    name: "العيادات والمراكز الصحية",
    description: "إعادة بناء المرافق الصحية المحلية ومراكز الخدمة اليومية.",
    icon: "⚕",
    tone: "health",
  },
  {
    key: "education",
    name: "المؤسسات التعليمية",
    description: "المدارس والمرافق التعليمية التي تخدم الأحياء السكنية.",
    icon: "◫",
    tone: "education",
  },
  {
    key: "universities",
    name: "الجامعات والتعليم العالي",
    description: "الحرم الجامعي والبنية الداعمة للتعليم العالي.",
    icon: "◭",
    tone: "education",
  },
  {
    key: "transportation",
    name: "الشوارع والنقل",
    description: "إصلاح المحاور المرورية والطرق والشبكات الحيوية.",
    icon: "═",
    tone: "transport",
  },
  {
    key: "municipal",
    name: "البنية البلدية",
    description: "مقار الإدارة المحلية والخدمات المرتبطة بها.",
    icon: "▣",
    tone: "municipal",
  },
  {
    key: "utilities",
    name: "الخدمات والمرافق",
    description: "المياه والطاقة والوقود والبنية التشغيلية الأساسية.",
    icon: "◉",
    tone: "utilities",
  },
];

const FILE_LABELS = {
  priority_map: "خريطة أولويات الإعمار",
  interactive_dashboard: "لوحة البيانات التفاعلية",
  dashboard_png: "اللوحة الإحصائية",
  projects_excel: "ملف المشاريع",
  streets_projects_excel: "ملف مشاريع الشوارع",
  phased_projects_excel: "ملف المراحل التنفيذية",
  summary_report: "الملخص النصي",
  damage_heatmap: "الخريطة الحرارية للأضرار",
  damaged_streets_map: "خريطة الشوارع المتضررة",
  streets_damage_map: "خريطة أضرار الشوارع",
  streets_reconstruction_map: "خريطة أولويات الشوارع",
  damage_animation: "رسوم الأضرار",
  damage_3d: "التصور ثلاثي الأبعاد",
  documentation_docx: "التوثيق النهائي",
  erd_report: "توثيق البيانات",
};

const STEP_LABELS = {
  queued: "تم استلام الطلب",
  load_data: "تحميل البيانات",
  damage_analysis: "تحليل الأضرار",
  grid: "بناء الشبكة المكانية",
  strategy: "تحديد استراتيجية الإعمار",
  scoring: "حساب الأولويات",
  explanations: "إعداد التفسيرات",
  needs: "مراجعة الاحتياجات",
  projects: "توليد المشاريع",
  exports: "تصدير الملفات",
  visuals: "إنشاء الواجهات البصرية",
  extended_visuals: "إنشاء التقارير الموسعة",
  documentation: "إعداد التوثيق",
  complete: "اكتمل التنفيذ",
  error: "حدث خطأ",
};

function App() {
  const [selectedProjects, setSelectedProjects] = useState(["healthcare", "transportation"]);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState({
    status: "idle",
    step: null,
    progress: 0,
    message: "لم يبدأ التحليل بعد.",
    logs: [],
    result: null,
  });
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const selectedLabels = useMemo(
    () => PROJECT_TYPES.filter((item) => selectedProjects.includes(item.key)).map((item) => item.name),
    [selectedProjects]
  );

  const previewEntries = useMemo(() => {
    const outputs = status.result?.outputs || {};
    const ordered = [
      "priority_map",
      "interactive_dashboard",
      "dashboard_png",
      "projects_excel",
      "streets_projects_excel",
      "phased_projects_excel",
      "summary_report",
    ];
    return ordered.filter((key) => outputs[key]).map((key) => ({ key, path: outputs[key] }));
  }, [status.result]);

  const allEntries = useMemo(() => {
    const outputs = status.result?.outputs || {};
    return Object.entries(outputs).map(([key, path]) => ({ key, path }));
  }, [status.result]);

  const toggleProject = (key) => {
    setSelectedProjects((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    );
  };

  const selectAll = () => setSelectedProjects(PROJECT_TYPES.map((item) => item.key));
  const clearAll = () => setSelectedProjects([]);

  const startPolling = (newJobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const response = await fetch(`/api/status?job_id=${newJobId}`);
      const payload = await response.json();
      setStatus(payload);
      if (payload.status === "done" || payload.status === "error") {
        clearInterval(pollRef.current);
      }
    }, 1800);
  };

  const runAnalysis = async () => {
    if (!selectedProjects.length) {
      setStatus({
        status: "idle",
        step: null,
        progress: 0,
        message: "اختر قطاعًا واحدًا على الأقل قبل التشغيل.",
        logs: ["[ui] No sector selected."],
        result: null,
      });
      return;
    }

    setStatus({
      status: "running",
      step: "queued",
      progress: 2,
      message: "جاري بدء التشغيل...",
      logs: ["[ui] Starting a new run..."],
      result: null,
    });

    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_projects: selectedProjects }),
    });
    const payload = await response.json();
    setJobId(payload.job_id);
    startPolling(payload.job_id);
  };

  const resolveOutputHref = (absolutePath) => {
    const normalized = absolutePath.replaceAll("\\", "/");
    const marker = "/output/";
    const index = normalized.indexOf(marker);
    return index >= 0 ? normalized.slice(index) : `/output/${normalized.split("/").pop()}`;
  };

  const isHtmlPreview = (key) => ["priority_map", "interactive_dashboard"].includes(key);
  const isImagePreview = (key) => key === "dashboard_png";

  return (
    <div className="page-shell">
      <div className="ambient ambient-a"></div>
      <div className="ambient ambient-b"></div>

      <header className="hero">
        <div className="hero-copy">
          <span className="eyebrow">React Control Center</span>
          <h1>واجهة أوضح لتشغيل مخرجات إعادة إعمار غزة</h1>
          <p>
            الواجهة الجديدة تنظّم النتائج بصريًا، وتفصل بين الملفات، والمعاينات، وحالة المعالجة
            الحالية بدل عرض كل شيء بطريقة مزدحمة وغير واضحة.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={runAnalysis}>تشغيل التحليل</button>
            <button className="btn btn-secondary" onClick={selectAll}>اختيار كل القطاعات</button>
            <button className="btn btn-ghost" onClick={clearAll}>مسح التحديد</button>
          </div>
        </div>

        <div className="hero-panel">
          <div className="metric">
            <span>القطاعات المختارة</span>
            <strong>{selectedProjects.length}</strong>
          </div>
          <div className="metric">
            <span>حالة المهمة</span>
            <strong>{status.status === "running" ? "قيد التنفيذ" : status.status === "done" ? "مكتمل" : status.status === "error" ? "فشل" : "جاهز"}</strong>
          </div>
          <div className="metric metric-wide">
            <span>المرحلة الحالية</span>
            <strong>{STEP_LABELS[status.step] || "بانتظار التشغيل"}</strong>
          </div>
        </div>
      </header>

      <section className="section-grid">
        <section className="card card-sectors">
          <div className="section-head">
            <div>
              <h2>اختيار القطاعات</h2>
              <p>اختر المجالات التي تريد إدخالها في دورة التحليل الحالية.</p>
            </div>
            <div className="selection-summary">
              {selectedLabels.length ? selectedLabels.map((label) => <span key={label} className="chip">{label}</span>) : <span className="chip muted">لا يوجد تحديد</span>}
            </div>
          </div>

          <div className="sector-grid">
            {PROJECT_TYPES.map((item) => (
              <button
                key={item.key}
                className={`sector-card tone-${item.tone} ${selectedProjects.includes(item.key) ? "selected" : ""}`}
                onClick={() => toggleProject(item.key)}
              >
                <div className="sector-icon">{item.icon}</div>
                <div className="sector-title">{item.name}</div>
                <div className="sector-desc">{item.description}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="card card-status">
          <div className="section-head">
            <div>
              <h2>حالة التنفيذ</h2>
              <p>تتبّع واضح للخطوة الحالية والتقدم الفعلي.</p>
            </div>
            {jobId ? <span className="job-badge">Job: {jobId.slice(0, 8)}</span> : null}
          </div>

          <div className="status-box">
            <div className="status-topline">
              <strong>{STEP_LABELS[status.step] || "لم يبدأ التحليل"}</strong>
              <span>{status.progress || 0}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${status.progress || 0}%` }}></div>
            </div>
            <p className="status-message">{status.message || "بانتظار التنفيذ."}</p>
          </div>

          <div className="logs-panel">
            {(status.logs || []).slice(-8).map((line, index) => (
              <div className="log-line" key={`${line}-${index}`}>{line}</div>
            ))}
          </div>
        </section>
      </section>

      <section className="results-layout">
        <section className="card results-main">
          <div className="section-head">
            <div>
              <h2>النتائج الرئيسية</h2>
              <p>المخرجات الأساسية مرتبة بشكل سهل: معاينات أولًا، ثم الملفات القابلة للتنزيل.</p>
            </div>
          </div>

          {status.result?.success ? (
            <>
              <div className="result-summary-grid">
                <div className="summary-tile">
                  <span>المشاريع الرئيسية</span>
                  <strong>{status.result.projects_count}</strong>
                </div>
                <div className="summary-tile">
                  <span>مشاريع الشوارع</span>
                  <strong>{status.result.street_projects_count}</strong>
                </div>
                <div className="summary-tile">
                  <span>مواقع الضرر</span>
                  <strong>{status.result.damage_site_count}</strong>
                </div>
                <div className="summary-tile">
                  <span>نمط التشغيل</span>
                  <strong>{status.result.profile}</strong>
                </div>
              </div>

              <div className="preview-grid">
                {previewEntries.map((entry) => {
                  const href = resolveOutputHref(entry.path);
                  return (
                    <article className="preview-card" key={entry.key}>
                      <div className="preview-head">
                        <h3>{FILE_LABELS[entry.key] || entry.key}</h3>
                        <a href={href} target="_blank" rel="noreferrer">فتح</a>
                      </div>
                      {isHtmlPreview(entry.key) ? <iframe title={entry.key} src={href}></iframe> : null}
                      {isImagePreview(entry.key) ? <img src={href} alt={entry.key} /> : null}
                      {!isHtmlPreview(entry.key) && !isImagePreview(entry.key) ? (
                        <div className="file-placeholder">
                          <span>ملف جاهز للفتح أو التنزيل</span>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <strong>لا توجد نتائج معروضة بعد</strong>
              <p>بعد تشغيل التحليل ستظهر الخرائط والملفات هنا بشكل منظم وواضح.</p>
            </div>
          )}
        </section>

        <aside className="card file-sidebar">
          <div className="section-head">
            <div>
              <h2>الملفات</h2>
              <p>قائمة مباشرة بكل ملف تم إنتاجه.</p>
            </div>
          </div>
          <div className="file-list">
            {allEntries.length ? allEntries.map((entry) => {
              const href = resolveOutputHref(entry.path);
              return (
                <a key={entry.key} className="file-item" href={href} target="_blank" rel="noreferrer">
                  <div>
                    <strong>{FILE_LABELS[entry.key] || entry.key}</strong>
                    <span>{entry.path.split(/[\\/]/).pop()}</span>
                  </div>
                  <b>فتح</b>
                </a>
              );
            }) : (
              <div className="empty-mini">لم يتم إنشاء ملفات بعد.</div>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
