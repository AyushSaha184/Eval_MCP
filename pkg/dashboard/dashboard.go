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
  <title>Eval_MCP Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #090D16;
      --bg-card: rgba(17, 24, 39, 0.7);
      --bg-card-hover: rgba(31, 41, 55, 0.8);
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #F3F4F6;
      --text-muted: #9CA3AF;
      --accent-cyan: #06B6D4;
      --accent-violet: #8B5CF6;
      --accent-emerald: #10B981;
      --accent-rose: #F43F5E;
      --accent-amber: #F59E0B;
      --glow-cyan: rgba(6, 182, 212, 0.25);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      background-image: 
        radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 50%);
      background-attachment: fixed;
    }
    header {
      border-bottom: 1px solid var(--border-color);
      backdrop-filter: blur(16px);
      background: rgba(9, 13, 22, 0.8);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .nav-container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 1.25rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .logo {
      font-family: 'Outfit', sans-serif;
      font-size: 1.5rem;
      font-weight: 700;
      background: linear-gradient(135deg, #06B6D4, #8B5CF6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .logo-badge {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      background: rgba(6, 182, 212, 0.15);
      color: var(--accent-cyan);
      border: 1px solid rgba(6, 182, 212, 0.3);
      -webkit-text-fill-color: var(--accent-cyan);
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 2.5rem 2rem;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2.5rem;
    }
    .stat-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      backdrop-filter: blur(12px);
      border-radius: 1rem;
      padding: 1.5rem;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .stat-title {
      font-size: 0.875rem;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }
    .stat-value {
      font-family: 'Outfit', sans-serif;
      font-size: 2.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }
    .section-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.35rem;
      font-weight: 600;
    }
    .table-container {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      backdrop-filter: blur(12px);
      border-radius: 1rem;
      overflow: hidden;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    th {
      background: rgba(255, 255, 255, 0.03);
      padding: 1rem 1.5rem;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
    }
    td {
      padding: 1.1rem 1.5rem;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.9rem;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: capitalize;
    }
    .badge-completed { background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-queued { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-running { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3); }
    .badge-failed { background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }
    .run-id {
      font-family: 'JetBrains Mono', monospace;
      color: var(--accent-cyan);
      font-weight: 500;
    }
    .btn {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-violet));
      color: white;
      border: none;
      padding: 0.6rem 1.2rem;
      border-radius: 0.5rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
  </style>
</head>
<body>
  <header>
    <div class="nav-container">
      <div class="logo">
        Eval_MCP <span class="logo-badge">Go Engine</span>
      </div>
      <div>
        <button class="btn" onclick="fetchRuns()">Refresh Runs</button>
      </div>
    </div>
  </header>

  <main>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">Total Evaluations</div>
        <div class="stat-value" id="stat-total">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Completed Runs</div>
        <div class="stat-value" style="color: var(--accent-emerald)" id="stat-completed">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Average Pass Rate</div>
        <div class="stat-value" style="color: var(--accent-cyan)" id="stat-passrate">0%</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Engine Status</div>
        <div class="stat-value" style="color: var(--accent-violet)">Active</div>
      </div>
    </div>

    <div class="section-header">
      <h2 class="section-title">Evaluation Runs</h2>
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Processed Cases</th>
            <th>Pass Rate</th>
            <th>Created At</th>
          </tr>
        </thead>
        <tbody id="runs-tbody">
          <tr>
            <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading evaluation runs...</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>

  <script>
    async function fetchRuns() {
      try {
        const res = await fetch('/v1/history/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project: '', page: 1, page_size: 50 })
        });
        const data = await res.json();
        if (!data.ok) return;

        const items = data.items || [];
        document.getElementById('stat-total').innerText = data.total || 0;
        
        const completed = items.filter(r => r.status === 'completed');
        document.getElementById('stat-completed').innerText = completed.length;

        let totalPass = 0;
        let countPass = 0;
        items.forEach(r => {
          if (r.pass_rate !== null && r.pass_rate !== undefined) {
            totalPass += r.pass_rate;
            countPass++;
          }
        });
        const avgPass = countPass > 0 ? Math.round((totalPass / countPass) * 100) : 0;
        document.getElementById('stat-passrate').innerText = avgPass + '%';

        const tbody = document.getElementById('runs-tbody');
        if (items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No evaluation runs found yet. Run an evaluation via MCP or API!</td></tr>';
          return;
        }

        tbody.innerHTML = items.map(function(r) {
          var passRateText = (r.pass_rate !== null && r.pass_rate !== undefined) ? Math.round(r.pass_rate * 100) + '%' : 'N/A';
          var created = new Date(r.created_at).toLocaleString();
          var typeText = (r.run_type || '').replace('_', ' ');
          var passColor = (r.pass_rate >= 0.8) ? 'var(--accent-emerald)' : 'var(--accent-amber)';
          return '<tr>' +
            '<td class="run-id">' + r.run_id + '</td>' +
            '<td style="text-transform: capitalize">' + typeText + '</td>' +
            '<td><span class="badge badge-' + r.status + '">' + r.status + '</span></td>' +
            '<td>' + r.processed_cases + ' / ' + r.total_cases + '</td>' +
            '<td style="font-weight: 600; color: ' + passColor + '">' + passRateText + '</td>' +
            '<td style="color: var(--text-muted)">' + created + '</td>' +
          '</tr>';
        }).join('');
      } catch (err) {
        console.error('Error fetching runs:', err);
      }
    }

    fetchRuns();
    setInterval(fetchRuns, 5000);
  </script>
</body>
</html>
`
