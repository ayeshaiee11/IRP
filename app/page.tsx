'use client'

import { useEffect, useState } from 'react'

const forecast = [
  { month: 'Jan', value: '$12.4k', height: '22%' },
  { month: 'Feb', value: '$15.8k', height: '31%' },
  { month: 'Mar', value: '$18.2k', height: '39%' },
  { month: 'Apr', value: '$22.6k', height: '50%' },
  { month: 'May', value: '$27.4k', height: '64%' },
  { month: 'Jun', value: '$34.8k', height: '82%' },
]

function TrendChart() {
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    const frame = requestAnimationFrame(() => setAnimated(true))
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="chart-area" aria-label="Revenue forecast chart">
      <div className="chart-y-labels" aria-hidden="true">
        <span>$40k</span><span>$30k</span><span>$20k</span><span>$10k</span><span>$0</span>
      </div>
      <div className="chart-plot">
        <div className="grid-lines" aria-hidden="true"><i /><i /><i /><i /><i /></div>
        <svg className={`trend-svg ${animated ? 'is-animated' : ''}`} viewBox="0 0 600 240" preserveAspectRatio="none" role="img" aria-label="Ascending solid and projected dotted revenue trend">
          <defs>
            <linearGradient id="trendStroke" x1="0" x2="1">
              <stop offset="0" stopColor="#4A1521" />
              <stop offset="1" stopColor="#B78C8D" />
            </linearGradient>
          </defs>
          <path className="trend-shadow" d="M12 210 C78 202 94 173 150 180 S220 144 270 151 S340 112 390 122 S455 81 505 76" />
          <path className="trend-solid" d="M12 210 C78 202 94 173 150 180 S220 144 270 151 S340 112 390 122 S455 81 505 76" />
          <path className="trend-prediction" d="M505 76 C535 70 557 42 588 25" />
          <circle className="trend-dot" cx="505" cy="76" r="6" />
          <circle className="trend-end" cx="588" cy="25" r="5" />
        </svg>
        <div className="chart-months" aria-hidden="true">
          {forecast.map((item) => <span key={item.month}>{item.month}</span>)}
        </div>
      </div>
    </div>
  )
}

function DashboardCard() {
  return (
    <section className="dashboard-card">
      <div className="dashboard-main">
        <div className="dashboard-heading">
          <div>
            <p className="eyebrow">Revenue outlook</p>
            <h1>Growth projection</h1>
          </div>
          <button className="period-button" type="button" aria-label="Change time period">6 months <span>⌄</span></button>
        </div>
        <div className="metric-row">
          <div><strong>$34,800</strong><span>Projected revenue</span></div>
          <div className="metric-change"><b>+28.4%</b><span>vs. last period</span></div>
        </div>
        <TrendChart />
        <div className="chart-footer"><span><i className="legend-solid" /> Actual performance</span><span><i className="legend-dashed" /> Forecasted growth</span><b>Updated just now</b></div>
      </div>
      <aside className="overview-column">
        <div className="overview-card overview-maroon">
          <div className="mini-icon">↗</div>
          <p>Momentum score</p>
          <strong>8.6<span>/10</span></strong>
          <small>Healthy upward trajectory</small>
        </div>
        <div className="overview-card overview-rose">
          <p>Next best action</p>
          <strong>Increase ad spend</strong>
          <small>Based on 14 market signals</small>
          <div className="action-arrow">→</div>
        </div>
      </aside>
    </section>
  )
}

export default function Page() {
  return (
    <main className="page-shell">
      <div className="noise" aria-hidden="true" />
      <nav className="top-nav" aria-label="Main navigation">
        <a className="brand" href="#top"><span className="brand-mark"><i /><i /><i /></span><span>Trendlens</span></a>
        <div className="nav-links"><a href="#insights">Insights</a><a href="#platform">Platform</a><a href="#resources">Resources</a></div>
        <button className="cta-button" type="button">Get started <span>↗</span></button>
      </nav>
      <div className="hero-content" id="top">
        <div className="hero-copy">
          <p className="kicker"><span /> Intelligence for what's next</p>
          <h2>See the market shifts <br /><em>before they settle.</em></h2>
          <p className="hero-description">Turn volatile crude oil tariffs, real estate asset variables, and air quality indexes into predictable value. Trendlens gives you the clarity to act with absolute conviction.</p>
          <div className="hero-actions"><button className="primary-action" type="button">Explore the platform <span>↗</span></button><button className="play-action" type="button"><span className="play">▶</span> Watch overview</button></div>
        </div>
        <DashboardCard />
      </div>
      <div className="bottom-note"><span>Trusted by teams building what's next</span><div className="trust-list"><b>northstar</b><b>QUANTUM</b><b>arc<span>°</span></b><b>MONUMENT</b></div></div>
    </main>
  )
}

export { forecast }
