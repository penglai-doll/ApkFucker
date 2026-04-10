export default function App(): JSX.Element {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div>
          <p className="app-shell__eyebrow">Android APK 分析工作台</p>
          <h1>APKHacker</h1>
        </div>

        <nav className="app-shell__nav" aria-label="工作台主导航">
          <button type="button">案件队列</button>
          <button type="button">案件工作台</button>
        </nav>
      </header>

      <main className="app-shell__main">
        <section className="app-shell__hero" aria-labelledby="workspace-title">
          <h2 id="workspace-title">案件工作台</h2>
          <p>先搭建桌面壳层，再逐步接入静态分析、动态 Hook 和报告面板。</p>
        </section>
      </main>
    </div>
  );
}
