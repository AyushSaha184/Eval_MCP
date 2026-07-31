package dashboard

import (
	"fmt"
	"net/http"

	"github.com/AyushSaha184/Eval_MCP/pkg/config"
	"github.com/AyushSaha184/Eval_MCP/pkg/services"
	"github.com/go-chi/chi/v5"
)

type Dashboard struct {
	cfg *config.Config
	svc *services.Services
}

func NewDashboard(cfg *config.Config, svc *services.Services) *Dashboard {
	return &Dashboard{
		cfg: cfg,
		svc: svc,
	}
}

func (d *Dashboard) Router() http.Handler {
	r := chi.NewRouter()
	r.Get("/", d.indexHandler)
	return r
}

func (d *Dashboard) indexHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, dashboardHTML)
}

const dashboardHTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Eval_MCP — Intelligent Evaluation Studio</title>
  
  <!-- Modern Typography from Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  
  <style>
    :root {
      --bg-dark: #050711;
      --bg-card: rgba(13, 17, 29, 0.75);
      --bg-card-hover: rgba(22, 28, 45, 0.85);
      --border-card: rgba(255, 255, 255, 0.08);
      --border-card-hover: rgba(6, 182, 212, 0.35);
      
      --text-main: #F3F4F6;
      --text-muted: #9CA3AF;
      --text-subtle: #6B7280;
      
      --accent-cyan: #06B6D4;
      --accent-cyan-glow: rgba(6, 182, 212, 0.25);
      --accent-violet: #8B5CF6;
      --accent-violet-glow: rgba(139, 92, 246, 0.25);
      --accent-emerald: #10B981;
      --accent-emerald-glow: rgba(16, 185, 129, 0.25);
      --accent-rose: #F43F5E;
      --accent-rose-glow: rgba(244, 63, 94, 0.25);
      --accent-amber: #F59E0B;
      --accent-amber-glow: rgba(245, 158, 11, 0.25);

      --radius-lg: 1.25rem;
      --radius-md: 0.875rem;
      --radius-sm: 0.5rem;
      --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
      --font-display: 'Outfit', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--font-sans);
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100dvh;
      line-height: 1.5;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 15% 10%, rgba(139, 92, 246, 0.14) 0px, transparent 45%),
        radial-gradient(circle at 85% 60%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
        radial-gradient(circle at 50% 90%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
      background-attachment: fixed;
    }

    /* Ambient Film Noise Overlay */
    .ambient-noise {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 999;
      opacity: 0.025;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    }

    /* Double Bezel Architecture */
    .bezel-outer {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 0.35rem;
      backdrop-filter: blur(20px);
      box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
      transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    .bezel-outer:hover {
      border-color: rgba(255, 255, 255, 0.14);
    }
    .bezel-inner {
      background: var(--bg-card);
      border-radius: calc(var(--radius-lg) - 0.35rem);
      padding: 1.5rem;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
      position: relative;
    }

    /* Floating Navigation Header */
    header {
      position: sticky;
      top: 1rem;
      z-index: 50;
      margin: 0 auto;
      max-width: 1320px;
      padding: 0 1.5rem;
    }
    .nav-inner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem 1.5rem;
      background: rgba(13, 17, 29, 0.82);
      backdrop-filter: blur(24px);
      border: 1px solid var(--border-card);
      border-radius: 9999px;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      text-decoration: none;
    }
    .brand-logo {
      font-family: var(--font-display);
      font-size: 1.4rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      background: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 50%, #EC4899 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand-badge {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.2rem 0.65rem;
      border-radius: 9999px;
      background: rgba(6, 182, 212, 0.12);
      color: var(--accent-cyan);
      border: 1px solid rgba(6, 182, 212, 0.3);
    }
    .live-pulse {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--accent-emerald);
      background: rgba(16, 185, 129, 0.1);
      padding: 0.3rem 0.75rem;
      border-radius: 9999px;
      border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      background: var(--accent-emerald);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--accent-emerald);
      animation: pulseGlow 2s infinite;
    }
    @keyframes pulseGlow {
      0% { transform: scale(0.95); opacity: 0.8; }
      50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 15px var(--accent-emerald); }
      100% { transform: scale(0.95); opacity: 0.8; }
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.55rem 1.15rem;
      border-radius: 9999px;
      font-family: var(--font-sans);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      text-decoration: none;
      white-space: nowrap;
    }
    .btn:active {
      transform: scale(0.97);
    }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-violet));
      color: #FFFFFF;
      box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
    }
    .btn-primary:hover {
      box-shadow: 0 6px 20px rgba(6, 182, 212, 0.5);
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-main);
      border: 1px solid var(--border-card);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .btn-icon-wrapper {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* Layout Main */
    main {
      max-width: 1320px;
      margin: 2rem auto 4rem;
      padding: 0 1.5rem;
    }

    /* Hero Section Header */
    .hero-title-section {
      margin-bottom: 2rem;
    }
    .eyebrow {
      display: inline-block;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      color: var(--accent-cyan);
      margin-bottom: 0.35rem;
    }
    .hero-headline {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.15;
    }

    /* Bento Grid */
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }
    .bento-col-3 { grid-column: span 3; }
    .bento-col-4 { grid-column: span 4; }
    .bento-col-6 { grid-column: span 6; }
    .bento-col-12 { grid-column: span 12; }

    @media (max-width: 1024px) {
      .bento-col-3, .bento-col-4, .bento-col-6 { grid-column: span 12; }
    }

    .stat-label {
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .stat-value-large {
      font-family: var(--font-display);
      font-size: 2.5rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      font-variant-numeric: tabular-nums;
      line-height: 1;
      margin-bottom: 0.5rem;
    }
    .stat-subtext {
      font-size: 0.8rem;
      color: var(--text-subtle);
    }
    
    /* Progress Bar */
    .progress-bar-bg {
      width: 100%;
      height: 8px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 9999px;
      overflow: hidden;
      margin-top: 0.85rem;
    }
    .progress-bar-fill {
      height: 100%;
      border-radius: 9999px;
      transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Status Pills in Cards */
    .pill-group {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-top: 0.75rem;
    }
    .pill {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      border: 1px solid transparent;
    }

    /* Toolbar & Filter Bar */
    .toolbar-container {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }
    .search-box {
      position: relative;
      flex: 1;
      min-width: 260px;
    }
    .search-input {
      width: 100%;
      padding: 0.65rem 1rem 0.65rem 2.6rem;
      background: rgba(13, 17, 29, 0.7);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-md);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.2s;
    }
    .search-input:focus {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 0 3px var(--accent-cyan-glow);
    }
    .search-icon {
      position: absolute;
      left: 0.85rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }

    .filter-tabs {
      display: flex;
      gap: 0.35rem;
      background: rgba(13, 17, 29, 0.7);
      padding: 0.3rem;
      border-radius: var(--radius-md);
      border: 1px solid var(--border-card);
    }
    .tab-btn {
      padding: 0.4rem 0.85rem;
      border-radius: calc(var(--radius-md) - 0.2rem);
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text-muted);
      background: transparent;
      border: none;
      cursor: pointer;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: var(--text-main); }
    .tab-btn.active {
      background: rgba(255, 255, 255, 0.1);
      color: var(--accent-cyan);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    .select-dropdown {
      padding: 0.6rem 1rem;
      background: rgba(13, 17, 29, 0.7);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-md);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 0.82rem;
      outline: none;
      cursor: pointer;
    }
    .select-dropdown option {
      background: #0D111D;
      color: #FFF;
    }

    /* Table Component */
    .table-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      overflow: hidden;
      backdrop-filter: blur(20px);
      box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.5);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    th {
      background: rgba(255, 255, 255, 0.02);
      padding: 1rem 1.35rem;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      font-weight: 700;
      border-bottom: 1px solid var(--border-card);
    }
    td {
      padding: 1.1rem 1.35rem;
      border-bottom: 1px solid var(--border-card);
      font-size: 0.875rem;
      vertical-align: middle;
    }
    tr:last-child td { border-bottom: none; }
    tr { transition: background 0.2s; }
    tr:hover td { background: rgba(255, 255, 255, 0.025); }

    .run-id-cell {
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--accent-cyan);
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      cursor: pointer;
    }
    .run-id-cell:hover { text-decoration: underline; }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: capitalize;
    }
    .status-completed { background: rgba(16, 185, 129, 0.12); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }
    .status-running { background: rgba(6, 182, 212, 0.12); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3); }
    .status-queued { background: rgba(245, 158, 11, 0.12); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
    .status-failed { background: rgba(244, 63, 94, 0.12); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }

    .action-btn-group {
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .btn-action-sm {
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-main);
      border: 1px solid var(--border-card);
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-action-sm:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .btn-action-ai {
      background: rgba(139, 92, 246, 0.15);
      color: #A78BFA;
      border-color: rgba(139, 92, 246, 0.3);
    }
    .btn-action-ai:hover {
      background: rgba(139, 92, 246, 0.25);
      border-color: rgba(139, 92, 246, 0.5);
    }

    /* Modal Backdrop & Container */
    .modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(5, 7, 17, 0.85);
      backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .modal-overlay.active {
      opacity: 1;
      pointer-events: auto;
    }
    .modal-box {
      width: 100%;
      max-width: 680px;
      max-height: 85vh;
      overflow-y: auto;
      background: #0D111D;
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 2rem;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      transform: scale(0.95) translateY(10px);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .modal-overlay.active .modal-box {
      transform: scale(1) translateY(0);
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border-card);
    }
    .modal-title {
      font-family: var(--font-display);
      font-size: 1.35rem;
      font-weight: 700;
    }
    .btn-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.25rem;
      cursor: pointer;
      padding: 0.25rem;
    }
    .btn-close:hover { color: #FFF; }

    /* Form controls */
    .form-group {
      margin-bottom: 1.25rem;
    }
    .form-label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 0.4rem;
      color: var(--text-muted);
    }
    .form-input, .form-textarea, .form-select {
      width: 100%;
      padding: 0.65rem 0.9rem;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-md);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 0.875rem;
      outline: none;
    }
    .form-input:focus, .form-textarea:focus, .form-select:focus {
      border-color: var(--accent-cyan);
    }
    .form-textarea {
      resize: vertical;
      min-height: 90px;
    }

    /* JSON Box */
    .json-code-block {
      background: #060811;
      border: 1px solid var(--border-card);
      border-radius: var(--radius-md);
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #A78BFA;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 280px;
      overflow-y: auto;
    }

    /* Toast System */
    .toast-container {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 200;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .toast {
      padding: 0.85rem 1.25rem;
      border-radius: var(--radius-md);
      background: #0D111D;
      border: 1px solid var(--accent-cyan);
      color: var(--text-main);
      font-size: 0.85rem;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      animation: toastIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes toastIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  </style>
</head>
<body>

  <!-- Ambient Noise Layer -->
  <div class="ambient-noise"></div>

  <!-- Header Container -->
  <header>
    <div class="nav-inner">
      <a href="#" class="brand">
        <span class="brand-logo">Eval_MCP</span>
        <span class="brand-badge">Engine v1.0</span>
      </a>

      <div class="nav-actions">
        <div class="live-pulse">
          <div class="pulse-dot"></div>
          <span>Engine Active</span>
        </div>

        <select id="project-select" class="select-dropdown" onchange="fetchRuns()">
          <option value="">All Projects</option>
        </select>

        <button class="btn btn-secondary" onclick="openCompareModal()">
          <span>Compare Prompts</span>
        </button>

        <button class="btn btn-primary" onclick="openNewEvalModal()">
          <div class="btn-icon-wrapper">+</div>
          <span>New Evaluation</span>
        </button>
      </div>
    </div>
  </header>

  <main>
    <!-- Hero Headline -->
    <div class="hero-title-section">
      <span class="eyebrow">AI Model & RAG Performance Dashboard</span>
      <h1 class="hero-headline">Evaluation Intelligence</h1>
    </div>

    <!-- Bento Grid Metrics -->
    <div class="bento-grid">
      <!-- Card 1: Total Evaluations -->
      <div class="bento-col-3">
        <div class="bezel-outer">
          <div class="bezel-inner">
            <div class="stat-label">
              <span>Total Evaluations</span>
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
            </div>
            <div class="stat-value-large" id="stat-total">0</div>
            <div class="stat-subtext" id="stat-total-sub">Total evaluation suites executed</div>
          </div>
        </div>
      </div>

      <!-- Card 2: Pass Rate Gauge -->
      <div class="bento-col-3">
        <div class="bezel-outer">
          <div class="bezel-inner">
            <div class="stat-label">
              <span>Average Pass Rate</span>
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
            <div class="stat-value-large" style="color: var(--accent-emerald)" id="stat-passrate">0%</div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" id="passrate-bar" style="width: 0%; background: var(--accent-emerald)"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Card 3: Status Breakdown -->
      <div class="bento-col-3">
        <div class="bezel-outer">
          <div class="bezel-inner">
            <div class="stat-label">
              <span>Run Status Distribution</span>
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            </div>
            <div class="stat-value-large" style="color: var(--accent-cyan)" id="stat-completed-count">0</div>
            <div class="pill-group">
              <span class="pill status-completed" id="pill-completed">0 Completed</span>
              <span class="pill status-running" id="pill-running">0 Active</span>
              <span class="pill status-failed" id="pill-failed">0 Failed</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Card 4: Engine Architecture & Supported Metrics -->
      <div class="bento-col-3">
        <div class="bezel-outer">
          <div class="bezel-inner">
            <div class="stat-label">
              <span>System Topology</span>
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            </div>
            <div class="stat-value-large" style="color: var(--accent-violet)" id="stat-metrics-count">12</div>
            <div class="stat-subtext" id="stat-storage-backend">Storage: Memory JSON | Queue: Redis</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toolbar & Filter Controls -->
    <div class="toolbar-container">
      <div class="search-box">
        <svg class="search-icon" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" id="search-input" class="search-input" placeholder="Search by Run ID or type..." oninput="filterTable()">
      </div>

      <div class="filter-tabs">
        <button class="tab-btn active" onclick="setFilterStatus('all', this)">All</button>
        <button class="tab-btn" onclick="setFilterStatus('completed', this)">Completed</button>
        <button class="tab-btn" onclick="setFilterStatus('running', this)">Running</button>
        <button class="tab-btn" onclick="setFilterStatus('failed', this)">Failed</button>
      </div>

      <select id="run-type-select" class="select-dropdown" onchange="fetchRuns()">
        <option value="">All Run Types</option>
        <option value="prompt_eval">Prompt Eval</option>
        <option value="rag_eval">RAG Eval</option>
        <option value="suggestion_eval">Suggestion Eval</option>
      </select>

      <button class="btn btn-secondary" onclick="fetchRuns()">
        <span>Refresh</span>
      </button>
    </div>

    <!-- Data Table -->
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Cases</th>
            <th>Pass Rate</th>
            <th>Created At</th>
            <th style="text-align: right">Actions</th>
          </tr>
        </thead>
        <tbody id="runs-tbody">
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 3rem;">
              Initializing evaluation telemetry data...
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>

  <!-- MODAL 1: Run Inspection Modal -->
  <div class="modal-overlay" id="modal-inspect">
    <div class="modal-box">
      <div class="modal-header">
        <h3 class="modal-title">Evaluation Run Inspector</h3>
        <button class="btn-close" onclick="closeModal('modal-inspect')">&times;</button>
      </div>
      <div id="inspect-content">Loading run details...</div>
    </div>
  </div>

  <!-- MODAL 2: AI Fix Suggestion Modal -->
  <div class="modal-overlay" id="modal-suggestion">
    <div class="modal-box">
      <div class="modal-header">
        <h3 class="modal-title">AI Fix & Optimization Suggestion</h3>
        <button class="btn-close" onclick="closeModal('modal-suggestion')">&times;</button>
      </div>
      <div id="suggestion-content">Fetching AI recommendations...</div>
    </div>
  </div>

  <!-- MODAL 3: New Evaluation Launcher Modal -->
  <div class="modal-overlay" id="modal-new-eval">
    <div class="modal-box">
      <div class="modal-header">
        <h3 class="modal-title">Trigger New Evaluation Suite</h3>
        <button class="btn-close" onclick="closeModal('modal-new-eval')">&times;</button>
      </div>
      <form onsubmit="submitNewEval(event)">
        <div class="form-group">
          <label class="form-label">Evaluation Type</label>
          <select id="eval-type" class="form-select" onchange="toggleEvalFields()">
            <option value="prompt">Prompt Eval Suite</option>
            <option value="rag">RAG Pipeline Scoring</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Project Name</label>
          <input type="text" id="eval-project" class="form-input" placeholder="e.g. core-ai-assistant" required>
        </div>
        <div class="form-group">
          <label class="form-label">Dataset Name</label>
          <input type="text" id="eval-dataset" class="form-input" placeholder="e.g. qa_benchmark_v1" required>
        </div>
        <div class="form-group">
          <label class="form-label">Target Model</label>
          <input type="text" id="eval-model" class="form-input" value="gemini-1.5-pro" required>
        </div>
        <div class="form-group">
          <label class="form-label">System Prompt / Template</label>
          <textarea id="eval-prompt" class="form-textarea" placeholder="You are an expert AI assistant..."></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-new-eval')">Cancel</button>
          <button type="submit" class="btn btn-primary">Launch Run</button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL 4: Compare Prompts Modal -->
  <div class="modal-overlay" id="modal-compare">
    <div class="modal-box">
      <div class="modal-header">
        <h3 class="modal-title">Prompt Version Regression Comparison</h3>
        <button class="btn-close" onclick="closeModal('modal-compare')">&times;</button>
      </div>
      <form onsubmit="submitCompare(event)">
        <div class="form-group">
          <label class="form-label">Project</label>
          <input type="text" id="compare-project" class="form-input" placeholder="e.g. core-ai-assistant" required>
        </div>
        <div class="form-group">
          <label class="form-label">Baseline Run ID</label>
          <input type="text" id="compare-baseline" class="form-input" placeholder="run_xxxxxxxx" required>
        </div>
        <div class="form-group">
          <label class="form-label">Candidate Run ID</label>
          <input type="text" id="compare-candidate" class="form-input" placeholder="run_yyyyyyyy" required>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-compare')">Cancel</button>
          <button type="submit" class="btn btn-primary">Run Comparison</button>
        </div>
      </form>
      <div id="compare-result" style="margin-top: 1.5rem;"></div>
    </div>
  </div>

  <!-- MODAL 5: Annotate Run Modal -->
  <div class="modal-overlay" id="modal-annotate">
    <div class="modal-box">
      <div class="modal-header">
        <h3 class="modal-title">Annotate Evaluation Run</h3>
        <button class="btn-close" onclick="closeModal('modal-annotate')">&times;</button>
      </div>
      <form onsubmit="submitAnnotation(event)">
        <input type="hidden" id="annotate-run-id">
        <div class="form-group">
          <label class="form-label">Label / Tag</label>
          <input type="text" id="annotate-label" class="form-input" placeholder="e.g. baseline-v2, regression-test" required>
        </div>
        <div class="form-group">
          <label class="form-label">Notes & Observations</label>
          <textarea id="annotate-note" class="form-textarea" placeholder="Observed drop in toxicity metric due to prompt formatting change..."></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-annotate')">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Annotation</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Toast Container -->
  <div class="toast-container" id="toast-container"></div>

  <script>
    let rawRunsData = [];
    let currentFilterStatus = 'all';

    // Fetch Supported System Metrics & Projects on Boot
    async function loadMeta() {
      try {
        const [metaRes, projRes] = await Promise.all([
          fetch('/v1/meta/supported-metrics'),
          fetch('/v1/projects')
        ]);
        const meta = await metaRes.json();
        const proj = await projRes.json();

        if (meta.ok) {
          document.getElementById('stat-metrics-count').innerText = (meta.metrics || []).length;
          document.getElementById('stat-storage-backend').innerText = 'Storage: ' + (meta.storage_provider || 'memory') + ' | Queue: ' + (meta.queue_backend || 'redis');
        }

        if (proj.ok && proj.items) {
          const select = document.getElementById('project-select');
          select.innerHTML = '<option value="">All Projects</option>' + 
            proj.items.map(p => '<option value="' + p.slug + '">' + p.name + '</option>').join('');
        }
      } catch (e) {
        console.error('Error fetching meta telemetry:', e);
      }
    }

    // Main Run Query Fetcher
    async function fetchRuns() {
      try {
        const project = document.getElementById('project-select').value;
        const runType = document.getElementById('run-type-select').value;

        const res = await fetch('/v1/history/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project: project, run_type: runType, page: 1, page_size: 100 })
        });
        const data = await res.json();
        if (!data.ok) return;

        rawRunsData = data.items || [];
        updateMetricsOverview(data.total || 0, rawRunsData);
        renderRunsTable(rawRunsData);
      } catch (err) {
        console.error('Error querying history:', err);
      }
    }

    function updateMetricsOverview(totalCount, items) {
      document.getElementById('stat-total').innerText = totalCount;
      
      const completed = items.filter(r => r.status === 'completed');
      const running = items.filter(r => r.status === 'running' || r.status === 'queued');
      const failed = items.filter(r => r.status === 'failed');

      document.getElementById('stat-completed-count').innerText = completed.length;
      document.getElementById('pill-completed').innerText = completed.length + ' Completed';
      document.getElementById('pill-running').innerText = running.length + ' Active';
      document.getElementById('pill-failed').innerText = failed.length + ' Failed';

      let totalPass = 0, countPass = 0;
      items.forEach(r => {
        if (r.pass_rate !== null && r.pass_rate !== undefined) {
          totalPass += r.pass_rate;
          countPass++;
        }
      });
      const avgPass = countPass > 0 ? Math.round((totalPass / countPass) * 100) : 0;
      document.getElementById('stat-passrate').innerText = avgPass + '%';
      document.getElementById('passrate-bar').style.width = avgPass + '%';
    }

    function renderRunsTable(items) {
      const tbody = document.getElementById('runs-tbody');
      const search = document.getElementById('search-input').value.toLowerCase();

      let filtered = items.filter(r => {
        if (currentFilterStatus !== 'all' && r.status !== currentFilterStatus) return false;
        if (search && !r.run_id.toLowerCase().includes(search) && !(r.run_type || '').toLowerCase().includes(search)) return false;
        return true;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 3rem;">No evaluation runs match the specified filter criteria.</td></tr>';
        return;
      }

      tbody.innerHTML = filtered.map(r => {
        const passRateText = (r.pass_rate !== null && r.pass_rate !== undefined) ? Math.round(r.pass_rate * 100) + '%' : 'N/A';
        const passColor = (r.pass_rate >= 0.8) ? 'var(--accent-emerald)' : ((r.pass_rate >= 0.5) ? 'var(--accent-amber)' : 'var(--accent-rose)');
        const created = new Date(r.created_at || Date.now()).toLocaleString();
        const typeText = (r.run_type || 'eval').replace('_', ' ');

        return '<tr>' +
          '<td><span class="run-id-cell" onclick="inspectRun(\'' + r.run_id + '\')">' + r.run_id + '</span></td>' +
          '<td style="text-transform: capitalize; font-weight: 500">' + typeText + '</td>' +
          '<td><span class="status-badge status-' + r.status + '">' + r.status + '</span></td>' +
          '<td>' + (r.processed_cases || 0) + ' / ' + (r.total_cases || 0) + '</td>' +
          '<td style="font-weight: 700; font-family: var(--font-mono); color: ' + passColor + '">' + passRateText + '</td>' +
          '<td style="color: var(--text-muted); font-size: 0.8rem">' + created + '</td>' +
          '<td style="text-align: right">' +
            '<div class="action-btn-group" style="justify-content: flex-end">' +
              '<button class="btn-action-sm" onclick="inspectRun(\'' + r.run_id + '\')">Inspect</button>' +
              '<button class="btn-action-sm btn-action-ai" onclick="openAIFix(\'' + r.run_id + '\')">✦ AI Fix</button>' +
              '<button class="btn-action-sm" onclick="openAnnotateModal(\'' + r.run_id + '\')">Annotate</button>' +
            '</div>' +
          '</td>' +
        '</tr>';
      }).join('');
    }

    function setFilterStatus(status, btn) {
      currentFilterStatus = status;
      document.querySelectorAll('.filter-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderRunsTable(rawRunsData);
    }

    function filterTable() {
      renderRunsTable(rawRunsData);
    }

    // Modal Control Helpers
    function openModal(id) {
      document.getElementById(id).classList.add('active');
    }
    function closeModal(id) {
      document.getElementById(id).classList.remove('active');
    }

    // Inspect Run Modal
    async function inspectRun(runID) {
      openModal('modal-inspect');
      const container = document.getElementById('inspect-content');
      container.innerHTML = '<p style="color: var(--text-muted)">Loading telemetry status for ' + runID + '...</p>';

      try {
        const res = await fetch('/v1/runs/' + runID + '/status?include_suggestion=true');
        const data = await res.json();
        if (data.ok) {
          container.innerHTML = 
            '<div style="margin-bottom: 1rem;">' +
              '<h4 style="font-size: 1.1rem; color: var(--accent-cyan); font-family: var(--font-mono)">' + data.run_id + '</h4>' +
              '<p style="color: var(--text-muted); font-size: 0.85rem">Status: <span class="status-badge status-' + data.status + '">' + data.status + '</span> | Type: ' + data.run_type + '</p>' +
            '</div>' +
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">' +
              '<div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 0.5rem;">' +
                '<span style="font-size: 0.75rem; color: var(--text-muted)">PROCESSED CASES</span>' +
                '<div style="font-size: 1.25rem; font-weight: 700">' + data.processed_cases + ' / ' + data.total_cases + '</div>' +
              '</div>' +
              '<div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 0.5rem;">' +
                '<span style="font-size: 0.75rem; color: var(--text-muted)">PASS RATE</span>' +
                '<div style="font-size: 1.25rem; font-weight: 700; color: var(--accent-emerald)">' + Math.round((data.pass_rate || 0) * 100) + '%</div>' +
              '</div>' +
            '</div>' +
            (data.error_message ? '<div style="color: var(--accent-rose); background: rgba(244,63,94,0.1); padding: 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem;">Error: ' + data.error_message + '</div>' : '') +
            '<h5 style="font-size: 0.85rem; margin-bottom: 0.5rem;">Raw Telemetry Payload</h5>' +
            '<div class="json-code-block">' + JSON.stringify(data, null, 2) + '</div>';
        }
      } catch (e) {
        container.innerHTML = '<p style="color: var(--accent-rose)">Failed to fetch run details.</p>';
      }
    }

    // AI Fix Suggestion Modal
    async function openAIFix(runID) {
      openModal('modal-suggestion');
      const container = document.getElementById('suggestion-content');
      container.innerHTML = '<p style="color: var(--text-muted)">Retrieving automated LLM fix suggestions for ' + runID + '...</p>';

      try {
        const res = await fetch('/v1/runs/' + runID + '/suggestions/latest');
        const data = await res.json();
        
        if (data.ok && data.suggestion_text) {
          container.innerHTML = 
            '<div style="margin-bottom: 1rem; background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); padding: 1rem; border-radius: 0.75rem;">' +
              '<h4 style="color: #A78BFA; font-size: 0.95rem; margin-bottom: 0.5rem;">✦ AI Optimization Summary</h4>' +
              '<p style="font-size: 0.9rem; line-height: 1.6;">' + (data.summary || 'Fix recommendation generated for evaluation errors.') + '</p>' +
            '</div>' +
            '<h5 style="font-size: 0.85rem; margin-bottom: 0.5rem;">Recommended Prompt & Pipeline Edits</h5>' +
            '<div class="json-code-block" style="color: var(--text-main); font-family: var(--font-sans)">' + data.suggestion_text + '</div>';
        } else {
          container.innerHTML = 
            '<p style="color: var(--text-muted); margin-bottom: 1rem;">No automated fix suggestion has been generated for this run yet.</p>' +
            '<button class="btn btn-primary" onclick="requestFix(\'' + runID + '\')">Generate AI Fix Suggestion</button>';
        }
      } catch (e) {
        container.innerHTML = '<p style="color: var(--accent-rose)">Failed to fetch AI suggestions.</p>';
      }
    }

    async function requestFix(runID) {
      showToast('Queueing AI fix analysis job...');
      try {
        const res = await fetch('/v1/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: runID, model: 'gemini-1.5-pro' })
        });
        const data = await res.json();
        if (data.ok) {
          showToast('AI Fix analysis queued successfully!');
          openAIFix(runID);
        }
      } catch (e) {
        showToast('Error requesting fix suggestion');
      }
    }

    // Modal Triggers
    function openNewEvalModal() { openModal('modal-new-eval'); }
    function openCompareModal() { openModal('modal-compare'); }
    function openAnnotateModal(runID) {
      document.getElementById('annotate-run-id').value = runID;
      openModal('modal-annotate');
    }

    // Form Submissions
    async function submitNewEval(e) {
      e.preventDefault();
      const type = document.getElementById('eval-type').value;
      const project = document.getElementById('eval-project').value;
      const dataset = document.getElementById('eval-dataset').value;
      const model = document.getElementById('eval-model').value;
      const prompt = document.getElementById('eval-prompt').value;

      const endpoint = (type === 'rag') ? '/v1/runs/rag' : '/v1/runs/eval';
      const payload = { project, dataset_name: dataset, model, system_prompt: prompt };

      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) {
          showToast('Evaluation run launched! ID: ' + data.run_id);
          closeModal('modal-new-eval');
          fetchRuns();
        } else {
          showToast('Error: ' + (data.error || 'Failed to trigger run'));
        }
      } catch (err) {
        showToast('API Connection Error');
      }
    }

    async function submitCompare(e) {
      e.preventDefault();
      const project = document.getElementById('compare-project').value;
      const baseline = document.getElementById('compare-baseline').value;
      const candidate = document.getElementById('compare-candidate').value;

      try {
        const res = await fetch('/v1/comparisons/prompt-versions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project, baseline_run_id: baseline, candidate_run_id: candidate })
        });
        const data = await res.json();
        const container = document.getElementById('compare-result');
        if (data.ok) {
          container.innerHTML = '<div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); padding: 1rem; border-radius: 0.5rem; color: var(--accent-emerald); font-weight: 600;">Comparison complete! Status: ' + data.status + '</div>';
          showToast('Prompt comparison completed!');
        } else {
          container.innerHTML = '<div style="color: var(--accent-rose)">' + (data.error || 'Comparison failed') + '</div>';
        }
      } catch (err) {
        showToast('Error executing comparison');
      }
    }

    async function submitAnnotation(e) {
      e.preventDefault();
      const runID = document.getElementById('annotate-run-id').value;
      const label = document.getElementById('annotate-label').value;
      const note = document.getElementById('annotate-note').value;

      try {
        const res = await fetch('/v1/runs/annotate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: runID, label: label, note: note, created_by: 'Dashboard User' })
        });
        const data = await res.json();
        if (data.ok) {
          showToast('Annotation saved for ' + runID);
          closeModal('modal-annotate');
        }
      } catch (err) {
        showToast('Error saving annotation');
      }
    }

    function showToast(msg) {
      const container = document.getElementById('toast-container');
      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.innerText = msg;
      container.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }

    // Initial Load & Auto Refresh Interval
    loadMeta();
    fetchRuns();
    setInterval(fetchRuns, 5000);
  </script>
</body>
</html>
`
