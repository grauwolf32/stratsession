/* ============================================================
   OSS Security Tooling Landscape — 2025-2026
   Strategy Session Brief — Application JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initScrollSpy();
  initSectionAnimations();
  initStatCounters();
  initToolsTable();
  initCharts();
});

/* ============================================================
   SIDEBAR
   ============================================================ */
function initSidebar() {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  if (!toggle || !sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
    toggle.setAttribute('aria-expanded', 'true');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  overlay.addEventListener('click', closeSidebar);

  // Close sidebar on nav-link click (mobile)
  sidebar.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
}

/* ============================================================
   SCROLL SPY — highlights active nav link
   ============================================================ */
function initScrollSpy() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

  if (!sections.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        navLinks.forEach(link => {
          link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
        });
      }
    });
  }, {
    rootMargin: '-20% 0px -75% 0px'
  });

  sections.forEach(s => observer.observe(s));
}

/* ============================================================
   SECTION FADE-IN ANIMATIONS
   ============================================================ */
function initSectionAnimations() {
  const targets = document.querySelectorAll('.fade-in, .stagger-children');
  if (!targets.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  targets.forEach(t => observer.observe(t));
}

/* ============================================================
   STAT COUNTER ANIMATION
   ============================================================ */
function initStatCounters() {
  const counters = document.querySelectorAll('.stat-number[data-target]');
  if (!counters.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(c => observer.observe(c));
}

function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  const suffix = el.dataset.suffix || '';
  const duration = 1200;
  const start = performance.now();

  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out quad
    const eased = 1 - (1 - progress) * (1 - progress);
    const current = Math.round(eased * target);
    el.textContent = current + suffix;
    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      el.textContent = target + suffix;
      el.classList.add('counted');
    }
  }

  requestAnimationFrame(tick);
}

/* ============================================================
   TOOLS TABLE — search & filter
   ============================================================ */
const TOOLS_DATA = [
  { name: "Buttercup", category: "AI Vuln Research", side: "dual", year: 2025, license: "OSI (MIT)", vendor: "Trail of Bits", standout: true },
  { name: "Seclab Taskflow Agent", category: "AI Vuln Research", side: "offense", year: 2026, license: "MIT", vendor: "GitHub Security Lab", standout: true },
  { name: "Trivy", category: "SAST/SCA", side: "defense", year: 2015, license: "Apache-2.0", vendor: "Aqua Security", standout: true },
  { name: "Betterleaks", category: "Secret Scanning", side: "defense", year: 2026, license: "MIT", vendor: "Aikido / Zach Rice", standout: true },
  { name: "Gitleaks", category: "Secret Scanning", side: "defense", year: 2019, license: "MIT", vendor: "Zach Rice", standout: false },
  { name: "PatchLeaks", category: "Scanners", side: "defense", year: 2025, license: "MIT", vendor: "Community", standout: false },
  { name: "Sunshine", category: "SBOM", side: "defense", year: 2025, license: "Apache-2.0", vendor: "OWASP", standout: false },
  { name: "DefectDojo", category: "Vuln Management", side: "defense", year: 2017, license: "BSD-3", vendor: "OWASP", standout: true },
  { name: "Nettacker", category: "Scanners", side: "offense", year: 2020, license: "Apache-2.0", vendor: "OWASP", standout: false },
  { name: "Coraza", category: "WAF", side: "defense", year: 2021, license: "Apache-2.0", vendor: "OWASP", standout: true },
  { name: "Core Rule Set", category: "WAF", side: "defense", year: 2006, license: "Apache-2.0", vendor: "OWASP", standout: true },
  { name: "AFL++", category: "Fuzzing", side: "dual", year: 2019, license: "Apache-2.0", vendor: "Community", standout: true },
  { name: "LibAFL", category: "Fuzzing", side: "dual", year: 2021, license: "Apache-2.0 / MIT", vendor: "Community", standout: true },
  { name: "Ruzzy", category: "Fuzzing", side: "dual", year: 2024, license: "Apache-2.0", vendor: "Trail of Bits", standout: false },
  { name: "Spotter", category: "Kubernetes", side: "defense", year: 2025, license: "Apache-2.0", vendor: "Madhu Akula", standout: true },
  { name: "Kyverno", category: "Kubernetes", side: "defense", year: 2020, license: "Apache-2.0", vendor: "CNCF", standout: true },
  { name: "Kubewarden", category: "Kubernetes", side: "defense", year: 2021, license: "Apache-2.0", vendor: "SUSE", standout: false },
  { name: "Copacetic", category: "Kubernetes", side: "defense", year: 2023, license: "Apache-2.0", vendor: "CNCF", standout: false },
  { name: "Falco", category: "Runtime Detection", side: "defense", year: 2018, license: "Apache-2.0", vendor: "CNCF/Sysdig", standout: true },
  { name: "Tetragon", category: "Runtime Detection", side: "defense", year: 2022, license: "Apache-2.0", vendor: "Isovalent/Cilium", standout: true },
  { name: "Tracee", category: "Runtime Detection", side: "defense", year: 2020, license: "Apache-2.0", vendor: "Aqua Security", standout: false },
  { name: "Prowler", category: "Cloud Posture", side: "defense", year: 2018, license: "Apache-2.0", vendor: "Prowler Inc", standout: true },
  { name: "cloud-audit", category: "Cloud Posture", side: "defense", year: 2026, license: "MIT", vendor: "Community", standout: true },
  { name: "CloudFox", category: "Cloud Offense", side: "offense", year: 2022, license: "MIT", vendor: "BishopFox", standout: false },
  { name: "BloodHound CE", category: "Identity/AD", side: "offense", year: 2023, license: "Apache-2.0", vendor: "SpecterOps", standout: true },
  { name: "SAMLSmith", category: "Identity/AD", side: "offense", year: 2025, license: "Apache-2.0", vendor: "Semperis", standout: false },
  { name: "ForceHound", category: "Identity/AD", side: "offense", year: 2026, license: "MIT", vendor: "NetSPI", standout: false },
  { name: "Empire 6.0", category: "C2 Framework", side: "offense", year: 2025, license: "BSD-3", vendor: "BC-Security", standout: true },
  { name: "C4", category: "C2 Framework", side: "offense", year: 2025, license: "MIT", vendor: "Community", standout: false },
  { name: "BOAZ", category: "Evasion", side: "offense", year: 2025, license: "MIT", vendor: "Community", standout: false },
  { name: "Beaconator", category: "C2 Framework", side: "offense", year: 2025, license: "MIT", vendor: "Crood Solutions", standout: false },
  { name: "Metasploit", category: "C2 Framework", side: "offense", year: 2003, license: "BSD-3", vendor: "Rapid7", standout: true },
  { name: "SmokedMeat", category: "CI/CD Security", side: "offense", year: 2026, license: "AGPL-3.0", vendor: "Boost Security", standout: true },
  { name: "Plumber", category: "CI/CD Security", side: "defense", year: 2026, license: "MPL-2.0", vendor: "Community", standout: true },
  { name: "Brutus", category: "CI/CD Security", side: "offense", year: 2026, license: "MIT", vendor: "Praetorian", standout: true },
  { name: "Promptfoo", category: "LLM Red Team", side: "offense", year: 2023, license: "MIT", vendor: "Promptfoo Inc", standout: true },
  { name: "GARAK", category: "LLM Red Team", side: "offense", year: 2023, license: "Apache-2.0", vendor: "NVIDIA", standout: true },
  { name: "PyRIT", category: "LLM Red Team", side: "offense", year: 2024, license: "MIT", vendor: "Microsoft", standout: false },
  { name: "DeepTeam", category: "LLM Red Team", side: "offense", year: 2024, license: "Apache-2.0", vendor: "Confident AI", standout: false },
  { name: "Vespasian", category: "API Security", side: "offense", year: 2026, license: "MIT", vendor: "Praetorian", standout: true },
  { name: "Hadrian", category: "API Security", side: "offense", year: 2026, license: "MIT", vendor: "Praetorian", standout: true },
  { name: "Little Snitch for Linux", category: "Host Firewall", side: "defense", year: 2026, license: "GPL-2.0", vendor: "Objective Dev", standout: true },
  { name: "Allama", category: "SOAR", side: "defense", year: 2026, license: "AGPL-3.0", vendor: "Digitrans Lab", standout: true },
  { name: "CERT UEFI Parser", category: "Forensics", side: "defense", year: 2026, license: "BSD-3", vendor: "CMU/SEI CERT", standout: true },
  { name: "mquire", category: "Forensics", side: "defense", year: 2026, license: "Apache-2.0", vendor: "Trail of Bits", standout: true },
  { name: "Nuclei", category: "Perimeter", side: "offense", year: 2020, license: "MIT", vendor: "ProjectDiscovery", standout: true },
  { name: "httpx", category: "Perimeter", side: "offense", year: 2020, license: "MIT", vendor: "ProjectDiscovery", standout: false },
  { name: "Katana", category: "Perimeter", side: "offense", year: 2022, license: "MIT", vendor: "ProjectDiscovery", standout: false },
  { name: "Caido", category: "Perimeter", side: "offense", year: 2022, license: "Proprietary", vendor: "Caido Labs", standout: false },
  { name: "SafeUpdater", category: "Reference Design", side: "defense", year: 2026, license: "MIT", vendor: "Doyensec", standout: false },
  { name: "DVBE", category: "Reference Design", side: "dual", year: 2025, license: "MIT", vendor: "Community", standout: false },
  { name: "Sliver", category: "C2 Framework", side: "offense", year: 2020, license: "GPL-3.0", vendor: "BishopFox", standout: true },
  { name: "Mythic", category: "C2 Framework", side: "offense", year: 2020, license: "BSD-3", vendor: "Community", standout: false },
  { name: "Havoc", category: "C2 Framework", side: "offense", year: 2022, license: "GPL-3.0", vendor: "Community", standout: false },
  { name: "IDFuzz", category: "Fuzzing Research", side: "dual", year: 2025, license: "Research", vendor: "USENIX", standout: false },
  { name: "G2FUZZ", category: "Fuzzing Research", side: "dual", year: 2025, license: "Research", vendor: "USENIX", standout: true },
  { name: "Lyso", category: "Fuzzing Research", side: "dual", year: 2025, license: "Research", vendor: "USENIX", standout: false },
  { name: "DUMPLING", category: "Fuzzing Research", side: "dual", year: 2026, license: "Research", vendor: "NDSS", standout: false },
  { name: "OpenSnitch", category: "Host Firewall", side: "defense", year: 2018, license: "GPL-3.0", vendor: "Community", standout: false },
  { name: "Garuda", category: "DFIR", side: "defense", year: 2025, license: "MIT", vendor: "Community", standout: false },
  { name: "FLARE-VM", category: "DFIR", side: "defense", year: 2017, license: "Apache-2.0", vendor: "Mandiant", standout: false },
];

function initToolsTable() {
  const tbody = document.getElementById('tools-tbody');
  const searchInput = document.getElementById('tools-search');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const countEl = document.getElementById('tools-count');

  if (!tbody) return;

  let activeFilter = 'all';

  function render() {
    const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const filtered = TOOLS_DATA.filter(t => {
      const matchFilter = activeFilter === 'all' ||
        (activeFilter === 'offense' && t.side === 'offense') ||
        (activeFilter === 'defense' && t.side === 'defense') ||
        (activeFilter === 'dual' && t.side === 'dual') ||
        (activeFilter === 'standout' && t.standout) ||
        t.category.toLowerCase().replace(/[\s\/]/g, '-').includes(activeFilter);
      const matchSearch = !query ||
        t.name.toLowerCase().includes(query) ||
        t.category.toLowerCase().includes(query) ||
        t.vendor.toLowerCase().includes(query) ||
        t.license.toLowerCase().includes(query);
      return matchFilter && matchSearch;
    });

    if (countEl) countEl.textContent = filtered.length;

    if (filtered.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="no-results">No tools match your search.</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map(t => `
      <tr>
        <td class="tool-name">${t.name}${t.standout ? '<span class="standout" title="Standout pick">★</span>' : ''}</td>
        <td><span class="tag">${t.category}</span></td>
        <td><span class="badge-side ${t.side}">${t.side}</span></td>
        <td>${t.year}</td>
        <td>${t.license}</td>
        <td>${t.vendor}</td>
      </tr>
    `).join('');
  }

  if (searchInput) {
    searchInput.addEventListener('input', render);
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      render();
    });
  });

  render();
}

/* ============================================================
   CHARTS (Chart.js)
   ============================================================ */
function initCharts() {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded — skipping chart initialization.');
    return;
  }

  // Global defaults
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#1e293b';
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.plugins.legend.labels.boxWidth = 14;
  Chart.defaults.plugins.legend.labels.padding = 12;

  const blue = '#3498db';
  const amber = '#f39c12';
  const green = '#27ae60';
  const red = '#e74c3c';
  const purple = '#9b59b6';
  const teal = '#1abc9c';
  const gray = '#64748b';

  // 1. Releases by quarter
  createChart('chart-releases', 'bar', {
    labels: ['Q2 2025', 'Q3 2025', 'Q4 2025', 'Q1 2026', 'Q2 2026'],
    datasets: [{
      label: 'New tool releases',
      data: [8, 22, 11, 14, 9],
      backgroundColor: [blue + 'aa', blue, blue + 'cc', amber, amber + 'aa'],
      borderRadius: 4,
    }]
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, grid: { color: '#1e293b' } } }
  });

  // 2. Tool count by category
  createChart('chart-categories', 'bar', {
    labels: ['C2 / Red Team', 'Kubernetes', 'LLM Red Team', 'Fuzzing', 'Cloud Posture', 'CI/CD', 'SAST/SCA', 'Scanners', 'Forensics', 'Defensive Ops', 'API Security', 'Identity/AD'],
    datasets: [{
      label: 'Tools',
      data: [12, 9, 6, 8, 5, 4, 6, 4, 3, 5, 3, 4],
      backgroundColor: [red, green, purple, amber, blue, red + 'cc', teal, blue + 'aa', gray, green + 'cc', amber + 'cc', purple + 'aa'],
      borderRadius: 4,
    }]
  }, {
    indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, grid: { color: '#1e293b' } } }
  });

  // 3. Offense/Defense balance
  createChart('chart-offense-defense', 'bar', {
    labels: ['C2', 'K8s', 'LLM', 'Fuzz', 'Cloud', 'CI/CD', 'SAST', 'Scan', 'DFIR', 'DefOps', 'API', 'ID/AD'],
    datasets: [
      { label: 'Offense', data: [12, 2, 5, 3, 3, 2, 1, 2, 0, 0, 3, 3], backgroundColor: red },
      { label: 'Defense', data: [0, 7, 0, 0, 4, 2, 5, 2, 3, 5, 0, 0], backgroundColor: green },
      { label: 'Dual', data: [0, 0, 1, 5, 0, 0, 0, 0, 0, 0, 0, 1], backgroundColor: amber },
    ]
  }, {
    plugins: { legend: { position: 'bottom' } },
    scales: {
      x: { stacked: true },
      y: { stacked: true, beginAtZero: true, grid: { color: '#1e293b' } }
    }
  });

  // 4. License distribution
  createChart('chart-licenses', 'doughnut', {
    labels: ['Apache-2.0', 'MIT', 'GPL / AGPL', 'BSD-3', 'MPL-2.0', 'Research', 'Proprietary'],
    datasets: [{
      data: [18, 20, 8, 4, 1, 5, 2],
      backgroundColor: [blue, green, red, amber, teal, purple, gray],
      borderWidth: 0,
      hoverOffset: 8,
    }]
  }, {
    cutout: '55%',
    plugins: { legend: { position: 'right' } }
  });

  // 5. Top vendor concentration
  createChart('chart-vendors', 'bar', {
    labels: ['Community', 'Trail of Bits', 'OWASP', 'Praetorian', 'CNCF', 'BishopFox', 'Aqua Security', 'NVIDIA', 'Microsoft', 'Semperis', 'NetSPI'],
    datasets: [{
      label: 'Tools',
      data: [14, 5, 6, 5, 3, 3, 2, 1, 1, 2, 2],
      backgroundColor: blue,
      borderRadius: 4,
    }]
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, grid: { color: '#1e293b' } } }
  });

  // 6. MCP adoption timeline
  createChart('chart-mcp', 'line', {
    labels: ['Jun 2025', 'Aug 2025', 'Oct 2025', 'Dec 2025', 'Feb 2026', 'Apr 2026'],
    datasets: [{
      label: 'Tools with MCP support',
      data: [1, 2, 3, 4, 7, 10],
      borderColor: blue,
      backgroundColor: blue + '22',
      fill: true,
      tension: 0.3,
      pointBackgroundColor: blue,
      pointRadius: 5,
      pointHoverRadius: 7,
    }]
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, grid: { color: '#1e293b' } } }
  });

  // 7. Conference tool density
  createChart('chart-conference-heatmap', 'bar', {
    labels: ['DEF CON 33', 'BH USA 25', 'USENIX 25', 'Hexacon 25', 'KubeCon NA', 'BH EU 25', 'NDSS 26', 'RSA 26', 'OWASP EU 25', 'OWASP US 25'],
    datasets: [{
      label: 'Tools released / demoed',
      data: [42, 30, 12, 8, 10, 14, 8, 6, 9, 7],
      backgroundColor: [blue, red, purple, amber, green, red + 'aa', purple + 'aa', amber + 'aa', teal, teal + 'aa'],
      borderRadius: 4,
    }]
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, grid: { color: '#1e293b' } } }
  });

  // 8. Language distribution
  createChart('chart-language', 'doughnut', {
    labels: ['Go', 'Python', 'Rust', 'TypeScript/JS', 'C/C++', 'Ruby', 'WASM', 'Other'],
    datasets: [{
      data: [16, 18, 8, 7, 5, 2, 3, 4],
      backgroundColor: [blue, amber, red, green, gray, purple, teal, '#bdc3c7'],
      borderWidth: 0,
      hoverOffset: 8,
    }]
  }, {
    cutout: '55%',
    plugins: { legend: { position: 'right' } }
  });
}

function createChart(id, type, data, options) {
  const canvas = document.getElementById(id);
  if (!canvas) return;

  new Chart(canvas.getContext('2d'), {
    type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 800, easing: 'easeOutQuart' },
      ...options,
    }
  });
}
