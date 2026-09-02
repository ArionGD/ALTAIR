import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Info, TrendingUp, Sparkles, FolderArchive, 
  LayoutDashboard, Menu, X, Sun, Moon, RefreshCw, ChevronRight,
  TrendingDown, ShieldCheck, HelpCircle, Layers, LogOut,
  Lock, User, Eye, EyeOff, ArrowRight
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

// Register Chart.js elements
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    localStorage.getItem('altair_auth') === 'true'
  );
  const [loginUser, setLoginUser] = useState('Aditya.raj');
  const [loginPass, setLoginPass] = useState('Aditya@3205#');
  const [showPass, setShowPass] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  const [loginSlide, setLoginSlide] = useState(0);

  const [activeTab, setActiveTab] = useState('overview');
  const [isMobile, setIsMobile] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('altair_theme') || 'dark');
  
  // Data States
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  
  // Detail Panel States
  const [detailTicker, setDetailTicker] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Astro Scanner States
  const [astroRows, setAstroRows] = useState([]);
  const [astroLoading, setAstroLoading] = useState(false);
  const [astroLoaded, setAstroLoaded] = useState(false);
  const [astroDetail, setAstroDetail] = useState(null);
  const [astroDetailLoading, setAstroDetailLoading] = useState(false);

  // Responsive viewpoint checking
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Theme Sync
  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.style.backgroundColor = '#0b0f19';
    } else {
      root.classList.remove('dark');
      root.style.backgroundColor = '#f9fafb';
    }
    localStorage.setItem('altair_theme', theme);
  }, [theme]);

  // Load Main Financial Universe
  const loadFinancialData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/strikes');
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setRows(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(`Failed to fetch financial data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFinancialData();
  }, []);

  // Load Astro Data
  const loadAstroData = async (force = false) => {
    setAstroLoading(true);
    try {
      const res = await fetch(`/api/v1/astro-scanner${force ? '?force=true' : ''}`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setAstroRows(data);
      setAstroLoaded(true);
    } catch (err) {
      console.error(err);
    } finally {
      setAstroLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'astro_scanner' && !astroLoaded) {
      loadAstroData();
    }
  }, [activeTab]);

  // Load Forensic details for a ticker
  const openDetail = async (ticker) => {
    setDetailTicker(ticker);
    setDetailLoading(true);
    setDetailData(null);
    try {
      const res = await fetch(`/api/v1/forensic-ticker/${encodeURIComponent(ticker)}`);
      if (res.ok) {
        const data = await res.json();
        setDetailData(data);
      } else {
        const row = rows.find(r => r.ticker === ticker);
        setDetailData(row || { ticker, error: 'Could not fetch full details' });
      }
    } catch {
      const row = rows.find(r => r.ticker === ticker);
      setDetailData(row || { ticker, error: 'Network failure' });
    } finally {
      setDetailLoading(false);
    }
  };

  // Load Astro detail for a ticker
  const openAstroDetail = async (ticker) => {
    setAstroDetailLoading(true);
    setAstroDetail(null);
    try {
      const res = await fetch(`/api/v1/astro-scanner/detail/${encodeURIComponent(ticker)}`);
      if (res.ok) {
        const data = await res.json();
        setAstroDetail(data);
      } else {
        setAstroDetail({ ticker, error: 'Failed to load details' });
      }
    } catch {
      setAstroDetail({ ticker, error: 'Network error' });
    } finally {
      setAstroDetailLoading(false);
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // Stat computations
  const totalAudited = rows.length;
  const criticalVulnerable = rows.filter(r => r.avs_score > 60).length;
  const highSolvency = rows.filter(r => r.z_score > 3.0).length;
  const averageAvs = totalAudited > 0 ? (rows.reduce((sum, r) => sum + r.avs_score, 0) / totalAudited).toFixed(2) : 0;

  // Chart Setup for Overview page
  const chartData = {
    labels: rows.slice(0, 8).map(r => r.ticker),
    datasets: [
      {
        fill: true,
        label: 'AVS Fragility Score',
        data: rows.slice(0, 8).map(r => r.avs_score),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
      },
      {
        fill: true,
        label: 'Altman Z-Score',
        data: rows.slice(0, 8).map(r => r.z_score * 10), // Scale up for visual comparisons
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: theme === 'dark' ? '#f3f4f6' : '#1f2937'
        }
      }
    },
    scales: {
      y: {
        grid: {
          color: theme === 'dark' ? '#374151' : '#e5e7eb'
        },
        ticks: {
          color: theme === 'dark' ? '#9ca3af' : '#4b5563'
        }
      },
      x: {
        grid: {
          color: theme === 'dark' ? '#374151' : '#e5e7eb'
        },
        ticks: {
          color: theme === 'dark' ? '#9ca3af' : '#4b5563'
        }
      }
    }
  };

  // Nav Items Definition
  const navigationItems = [
    { id: 'overview', name: 'Overview', icon: LayoutDashboard },
    { id: 'strikes', name: 'Strike List', icon: ShieldAlert },
    { id: 'astro_scanner', name: 'Astro Scanner', icon: Sparkles },
    { id: 'swing', name: 'Swing Scanner', icon: TrendingUp },
    { id: 'archives', name: 'Archives', icon: FolderArchive },
    { id: 'guide', name: 'Guide', icon: Info },
  ];

  // Slideshow auto-advance
  useEffect(() => {
    if (isAuthenticated) return;
    const interval = setInterval(() => {
      setLoginSlide((prev) => (prev + 1) % 4);
    }, 4500);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginSubmitting(true);
    setLoginError('');

    try {
      const res = await fetch('/api/v1/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUser, password: loginPass })
      });
      if (res.ok) {
        localStorage.setItem('altair_auth', 'true');
        localStorage.setItem('altair_user', loginUser);
        setIsAuthenticated(true);
      } else {
        // Fallback local check
        if (loginUser.trim().toLowerCase() === 'aditya.raj' && loginPass === 'Aditya@3205#') {
          localStorage.setItem('altair_auth', 'true');
          localStorage.setItem('altair_user', loginUser);
          setIsAuthenticated(true);
        } else {
          setLoginError('Invalid User ID or Password.');
        }
      }
    } catch {
      if (loginUser.trim().toLowerCase() === 'aditya.raj' && loginPass === 'Aditya@3205#') {
        localStorage.setItem('altair_auth', 'true');
        localStorage.setItem('altair_user', loginUser);
        setIsAuthenticated(true);
      } else {
        setLoginError('Invalid User ID or Password.');
      }
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm('Sign out of ALTAIR?')) {
      localStorage.removeItem('altair_auth');
      setIsAuthenticated(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#060911] text-white flex flex-col md:flex-row select-none">
        {/* LEFT PANEL (50%): Animated Showcase Slideshow */}
        <div className="w-full md:w-1/2 bg-gradient-to-br from-[#0c1424] via-[#080d1a] to-[#04060d] border-b md:border-b-0 md:border-r border-gray-800 p-8 md:p-14 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -top-32 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

          {/* Top Brand */}
          <div className="flex items-center gap-3.5 z-10">
            <img src="/logo.png" alt="Altair Logo" className="w-10 h-10 rounded-xl object-contain border border-cyan-500/30 shadow-lg" />
            <div>
              <h1 className="font-black text-lg text-white tracking-wider flex items-center gap-2">
                ALTAIR <span className="text-cyan-400 text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 font-mono">FRAGILITY ENGINE</span>
              </h1>
              <p className="text-[11px] text-gray-400">Institutional Vulnerability & Financial Stress Gateway</p>
            </div>
          </div>

          {/* Animated Slides Container */}
          <div className="my-10 z-10 min-h-[260px] flex flex-col justify-center">
            {loginSlide === 0 && (
              <div className="transition-all duration-700">
                <div className="inline-flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-3 bg-cyan-500/10 border border-cyan-500/20 px-3 py-1 rounded-full">
                  <ShieldAlert size={14} /> Module I: Financial Fragility Gateway
                </div>
                <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                  Multi-Factor Solvency & Vulnerability Ranking
                </h2>
                <p className="text-sm text-gray-400 mt-3 leading-relaxed max-w-lg">
                  Diagnoses corporate fragility across liquidity stress, leverage ratios, Piotroski metrics, and earnings quality across large-cap and mid-cap equities.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 text-xs font-mono text-cyan-300">
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#FragilityRank</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#DebtStress</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#SolvencyRisk</span>
                </div>
              </div>
            )}

            {loginSlide === 1 && (
              <div className="transition-all duration-700">
                <div className="inline-flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-widest mb-3 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
                  <Sparkles size={14} /> Module II: Astro & Harmonics Scanner
                </div>
                <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                  Macro Timing Cycles & Geometric Harmonics
                </h2>
                <p className="text-sm text-gray-400 mt-3 leading-relaxed max-w-lg">
                  Correlates institutional price action with Gann planetary angle turning dates and celestial cycle pivots to identify inflection zones.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 text-xs font-mono text-emerald-300">
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#PlanetaryHarmonics</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#GannPivots</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#CycleInflection</span>
                </div>
              </div>
            )}

            {loginSlide === 2 && (
              <div className="transition-all duration-700">
                <div className="inline-flex items-center gap-2 text-yellow-400 text-xs font-mono uppercase tracking-widest mb-3 bg-yellow-500/10 border border-yellow-500/20 px-3 py-1 rounded-full">
                  <TrendingUp size={14} /> Module III: Swing & Strike Intelligence
                </div>
                <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                  Asymmetric Breakouts & Liquidity Hunting
                </h2>
                <p className="text-sm text-gray-400 mt-3 leading-relaxed max-w-lg">
                  Surfaces asymmetric short and long opportunities with calculated stop-losses, risk-reward ratios, and volume-flow confirmation.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 text-xs font-mono text-yellow-300">
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#StrikeList</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#SwingAlpha</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#RiskReward</span>
                </div>
              </div>
            )}

            {loginSlide === 3 && (
              <div className="transition-all duration-700">
                <div className="inline-flex items-center gap-2 text-purple-400 text-xs font-mono uppercase tracking-widest mb-3 bg-purple-500/10 border border-purple-500/20 px-3 py-1 rounded-full">
                  <FolderArchive size={14} /> Module IV: Scenario Modeling & EGB
                </div>
                <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                  Macro Stress Scenarios & Historical Archives
                </h2>
                <p className="text-sm text-gray-400 mt-3 leading-relaxed max-w-lg">
                  Simulates black-swan shocks, interest rate hikes, and currency devaluations against portfolio constituents in real-time.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 text-xs font-mono text-purple-300">
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#ScenarioStress</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#GovernanceAudit</span>
                  <span className="bg-gray-800/80 border border-gray-700 px-2.5 py-1 rounded-lg">#Archives</span>
                </div>
              </div>
            )}
          </div>

          {/* Slide Navigation Indicators */}
          <div className="flex items-center justify-between z-10 border-t border-gray-800 pt-4">
            <div className="flex items-center gap-2">
              {[0, 1, 2, 3].map((idx) => (
                <button
                  key={idx}
                  onClick={() => setLoginSlide(idx)}
                  className={`h-1.5 rounded-full transition-all ${
                    loginSlide === idx ? 'w-6 bg-cyan-400' : 'w-2 bg-gray-700 hover:bg-gray-500'
                  }`}
                />
              ))}
            </div>
            <div className="text-[11px] font-mono text-gray-500">
              Proprietary Institutional Gateway
            </div>
          </div>
        </div>

        {/* RIGHT PANEL (50%): Institutional Sign-In Form */}
        <div className="w-full md:w-1/2 bg-[#060911] p-8 md:p-14 flex items-center justify-center relative">
          <div className="max-w-md w-full">
            <div className="mb-8">
              <h3 className="text-2xl font-bold text-white tracking-tight">Terminal Authentication</h3>
              <p className="text-xs text-gray-400 mt-1">Enter your institutional credentials to unlock ALTAIR.</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">User ID</label>
                <div className="relative">
                  <User className="absolute left-3.5 top-3.5 text-gray-500" size={16} />
                  <input
                    type="text"
                    required
                    value={loginUser}
                    onChange={(e) => setLoginUser(e.target.value)}
                    placeholder="User ID (e.g. Aditya.raj)"
                    className="w-full bg-[#0b0f19] border border-gray-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-cyan-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3.5 text-gray-500" size={16} />
                  <input
                    type={showPass ? 'text' : 'password'}
                    required
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    placeholder="Enter password"
                    className="w-full bg-[#0b0f19] border border-gray-800 rounded-xl pl-10 pr-11 py-3 text-sm text-cyan-300 font-mono focus:outline-none focus:border-cyan-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3.5 top-3.5 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-gray-400 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded border-gray-800 bg-[#0b0f19] text-cyan-500 focus:ring-0" />
                  <span>Keep session active</span>
                </label>
                <span className="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
                  <ShieldCheck size={14} /> 256-bit Encrypted
                </span>
              </div>

              <button
                type="submit"
                disabled={loginSubmitting}
                className="w-full bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-cyan-500/20 transition-all text-sm flex items-center justify-center gap-2 mt-4"
              >
                <span>{loginSubmitting ? 'Authenticating...' : 'Sign In to Terminal'}</span>
                <ArrowRight size={14} />
              </button>

              {loginError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
                  <ShieldAlert size={16} className="shrink-0" />
                  <span>{loginError}</span>
                </div>
              )}
            </form>

            <div className="mt-8 border-t border-gray-800/60 pt-4 flex items-center justify-between text-[11px] text-gray-500">
              <span>Authorized Personnel Only</span>
              <span className="font-mono">v1.2.0 • ALTAIR</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'bg-[#0b0f19] text-gray-100' : 'bg-gray-50 text-gray-900'} flex flex-col md:flex-row`}>
      
      {/* Sidebar - Desktop Layout */}
      {!isMobile && (
        <aside className={`w-64 border-r flex-shrink-0 flex flex-col justify-between ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
          <div>
            {/* Sidebar Logo */}
            <div className="p-6 border-b flex items-center gap-3 border-inherit">
              <img src="/logo.png" className="h-9 w-9 rounded object-contain" alt="Altair Logo" />
              <div>
                <h1 className="font-bold text-lg leading-tight">ALTAIR</h1>
                <span className="text-xs text-gray-500 font-medium">Fragility Engine</span>
              </div>
            </div>

            {/* Sidebar Navigation */}
            <nav className="p-4 space-y-1.5">
              {navigationItems.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                      isActive 
                        ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' 
                        : theme === 'dark' 
                          ? 'text-gray-400 hover:bg-gray-800/50 hover:text-white' 
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon size={18} />
                    <span>{item.name}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-inherit flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button 
                onClick={toggleTheme}
                className={`p-2 rounded-lg transition-colors ${theme === 'dark' ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button 
                onClick={handleLogout}
                className="p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Sign Out of ALTAIR"
              >
                <LogOut size={18} />
              </button>
            </div>
            <span className="text-xs text-gray-500 font-semibold">v1.2.0</span>
          </div>
        </aside>
      )}

      {/* Header - Mobile Layout */}
      {isMobile && (
        <header className={`p-4 border-b flex items-center justify-between z-20 ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <img src="/logo.png" className="h-8 w-8 rounded object-contain" alt="Altair Logo" />
            <h1 className="font-bold text-md">ALTAIR</h1>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={toggleTheme}
              className={`p-2 rounded-lg ${theme === 'dark' ? 'text-yellow-400' : 'text-gray-600'}`}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={`p-2 rounded-lg ${theme === 'dark' ? 'hover:bg-gray-800' : 'hover:bg-gray-100'}`}
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </header>
      )}

      {/* Dropdown Menu - Mobile Navigation */}
      {isMobile && mobileMenuOpen && (
        <div className={`absolute top-16 left-0 right-0 border-b shadow-2xl p-4 flex flex-col gap-2 z-10 ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
          {navigationItems.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium ${
                  isActive 
                    ? 'bg-red-500 text-white' 
                    : theme === 'dark' 
                      ? 'text-gray-400 hover:bg-gray-800/50 hover:text-white' 
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <Icon size={18} />
                <span>{item.name}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Main Content Pane */}
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        {/* Top Header Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h2 className="text-2xl font-bold capitalize">{activeTab.replace('_', ' ')}</h2>
            <p className="text-sm text-gray-500">Corporate vulnerability analytics index</p>
          </div>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-xs text-gray-400 font-medium">Last Sync: {lastUpdated}</span>
            )}
            <button 
              onClick={loadFinancialData}
              disabled={loading}
              className={`flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                theme === 'dark' 
                  ? 'border-gray-800 bg-[#0f172a] hover:bg-gray-800 text-gray-200' 
                  : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-700'
              }`}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Tab Subviews */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* KPI Stat Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: 'Audited Universe', value: totalAudited, desc: 'Total tracked tickers', icon: Layers, color: 'text-blue-500' },
                { label: 'Vulnerable Stocks', value: criticalVulnerable, desc: 'AVS Score > 60', icon: ShieldAlert, color: 'text-red-500' },
                { label: 'Average AVS Score', value: averageAvs, desc: 'Aggregated fragility index', icon: TrendingUp, color: 'text-yellow-500' },
                { label: 'Strong Solvency', value: highSolvency, desc: 'Altman Z > 3.0', icon: ShieldCheck, color: 'text-green-500' },
              ].map((stat, idx) => {
                const Icon = stat.icon;
                return (
                  <div key={idx} className={`p-6 rounded-xl border shadow-sm ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-xs font-semibold text-gray-500 uppercase">{stat.label}</span>
                      <Icon className={stat.color} size={20} />
                    </div>
                    <h3 className="text-3xl font-extrabold mb-1">{stat.value}</h3>
                    <p className="text-xs text-gray-400 font-medium">{stat.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Overview Visualizations */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Chart Pane */}
              <div className={`p-6 rounded-xl border shadow-sm lg:col-span-2 ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
                <h4 className="font-bold text-sm mb-4">Fragility Score Distribution (Top 8 Tickers)</h4>
                <div className="h-64 relative">
                  {rows.length > 0 ? (
                    <Line data={chartData} options={chartOptions} />
                  ) : (
                    <div className="h-full flex items-center justify-center text-gray-400">No data loaded</div>
                  )}
                </div>
              </div>

              {/* Quick Action list */}
              <div className={`p-6 rounded-xl border shadow-sm ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
                <h4 className="font-bold text-sm mb-4">Top Fragile Candidates</h4>
                <div className="space-y-4">
                  {rows.slice(0, 5).map((row, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => openDetail(row.ticker)}
                      className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition-transform hover:scale-[1.01] ${
                        theme === 'dark' ? 'bg-[#1e293b]/30 border-gray-800 hover:bg-[#1e293b]/70' : 'bg-gray-50 border-gray-100 hover:bg-gray-100'
                      }`}
                    >
                      <div>
                        <h5 className="font-bold text-sm">{row.ticker}</h5>
                        <p className="text-xs text-gray-400">AVS Score: {row.avs_score}</p>
                      </div>
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                        AVS {row.avs_score}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab view: Strikes */}
        {activeTab === 'strikes' && (
          <div className={`rounded-xl border shadow-sm overflow-hidden ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
            <div className="p-6 border-b border-inherit flex flex-col sm:flex-row justify-between sm:items-center gap-4">
              <h4 className="font-bold text-sm">Vulnerable Company Registry</h4>
              <span className="text-xs text-gray-400 font-medium">Scored chronologically</span>
            </div>
            
            {/* Desktop Table View */}
            {!isMobile ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className={`border-b border-inherit text-xs font-semibold uppercase text-gray-500 ${theme === 'dark' ? 'bg-[#1e293b]/20' : 'bg-gray-50'}`}>
                      <th className="p-4">Ticker</th>
                      <th className="p-4">AVS Score</th>
                      <th className="p-4">Altman Z</th>
                      <th className="p-4">Sloan Ratio</th>
                      <th className="p-4">Beneish M-Score</th>
                      <th className="p-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/10 dark:divide-gray-800">
                    {rows.map((row, idx) => (
                      <tr 
                        key={idx}
                        className={`hover:bg-gray-800/5 dark:hover:bg-gray-800/30 transition-colors cursor-pointer ${idx % 2 === 0 ? '' : theme === 'dark' ? 'bg-[#1e293b]/5' : 'bg-gray-50/30'}`}
                        onClick={() => openDetail(row.ticker)}
                      >
                        <td className="p-4 font-bold text-sm">{row.ticker}</td>
                        <td className="p-4">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                            row.avs_score > 60 
                              ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' 
                              : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                          }`}>
                            {row.avs_score}%
                          </span>
                        </td>
                        <td className="p-4 text-sm font-medium">{row.z_score || 'N/A'}</td>
                        <td className="p-4 text-sm font-medium">{row.sloan_ratio || 'N/A'}</td>
                        <td className="p-4 text-sm font-medium">{row.m_score || 'N/A'}</td>
                        <td className="p-4 text-right">
                          <button className="text-red-500 hover:text-red-400 font-semibold text-xs flex items-center justify-end gap-1 w-full">
                            <span>Analyze</span>
                            <ChevronRight size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              // Mobile Cards View
              <div className="p-4 space-y-4">
                {rows.map((row, idx) => (
                  <div 
                    key={idx}
                    onClick={() => openDetail(row.ticker)}
                    className={`p-4 rounded-lg border cursor-pointer ${
                      theme === 'dark' ? 'bg-[#1e293b]/20 border-gray-800 hover:bg-[#1e293b]/40' : 'bg-gray-50 border-gray-100 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-bold text-md">{row.ticker}</h5>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        row.avs_score > 60 ? 'bg-red-500/10 text-red-500' : 'bg-yellow-500/10 text-yellow-500'
                      }`}>
                        AVS {row.avs_score}%
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
                      <div>
                        <p className="font-medium text-gray-400">Altman Z</p>
                        <p className={`font-semibold ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>{row.z_score || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="font-medium text-gray-400">Sloan</p>
                        <p className={`font-semibold ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>{row.sloan_ratio || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="font-medium text-gray-400">Beneish M</p>
                        <p className={`font-semibold ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>{row.m_score || 'N/A'}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab view: Astro Scanner */}
        {activeTab === 'astro_scanner' && (
          <div className="space-y-6">
            {/* Informational Box */}
            <div className={`p-4 rounded-xl border flex items-start gap-4 ${theme === 'dark' ? 'bg-indigo-950/10 border-indigo-900/30' : 'bg-indigo-50 border-indigo-100'}`}>
              <Sparkles className="text-indigo-500 mt-0.5 flex-shrink-0" size={20} />
              <div>
                <h5 className="font-bold text-sm text-indigo-950 dark:text-indigo-400">Astro-Financial Synergy Scanner</h5>
                <p className="text-xs text-indigo-900/60 dark:text-indigo-300/60 mt-1">
                  Combines corporate natal chart analysis (Dasha periods & active transits) with financial health metrics (Z-score, Sloan index) to discover unified alphas. Caches queries daily.
                </p>
              </div>
            </div>

            <div className={`rounded-xl border shadow-sm overflow-hidden ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
              <div className="p-6 border-b border-inherit flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                <div>
                  <h4 className="font-bold text-sm">Unified Astro-Financial Universe</h4>
                  <p className="text-xs text-gray-500 mt-0.5">Ranked by Unified Alpha Score</p>
                </div>
                <button 
                  onClick={() => loadAstroData(true)}
                  disabled={astroLoading}
                  className="px-3.5 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg text-xs font-semibold flex items-center gap-2"
                >
                  <RefreshCw size={12} className={astroLoading ? 'animate-spin' : ''} />
                  <span>Force Re-Cache</span>
                </button>
              </div>

              {astroLoading ? (
                <div className="p-12 text-center text-gray-400 flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="animate-spin text-red-500" size={28} />
                  <p className="text-sm">Querying VedAstro timing aspects & compiling rankings...</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className={`border-b border-inherit text-xs font-semibold uppercase text-gray-500 ${theme === 'dark' ? 'bg-[#1e293b]/20' : 'bg-gray-50'}`}>
                        <th className="p-4">Company</th>
                        <th className="p-4">Lagna</th>
                        <th className="p-4">Active Dasha</th>
                        <th className="p-4">Astro Score</th>
                        <th className="p-4">Financial Score</th>
                        <th className="p-4">Unified Alpha</th>
                        <th className="p-4">Recommendation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/10 dark:divide-gray-800">
                      {astroRows.map((row, idx) => (
                        <tr 
                          key={idx}
                          onClick={() => openAstroDetail(row.ticker)}
                          className={`hover:bg-gray-800/5 dark:hover:bg-gray-800/30 transition-colors cursor-pointer ${idx % 2 === 0 ? '' : theme === 'dark' ? 'bg-[#1e293b]/5' : 'bg-gray-50/30'}`}
                        >
                          <td className="p-4">
                            <div className="font-bold text-sm">{row.name}</div>
                            <span className="text-xs text-gray-400 font-semibold uppercase">{row.ticker}</span>
                          </td>
                          <td className="p-4 text-sm font-medium">{row.lagna}</td>
                          <td className="p-4 text-sm font-medium">
                            {row.active_dasha?.mahadasha} - {row.active_dasha?.bhukti}
                          </td>
                          <td className="p-4 text-sm font-medium">{row.astro_growth_score}%</td>
                          <td className="p-4 text-sm font-medium">{row.financial_quality_score}%</td>
                          <td className="p-4 font-extrabold text-sm text-red-500">{row.unified_alpha_score}%</td>
                          <td className="p-4">
                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold inline-block ${
                              row.interpreted_call?.includes('STRONG BUY')
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                                : row.interpreted_call?.includes('SHORT')
                                  ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                                  : 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
                            }`}>
                              {row.interpreted_call}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab view: Swing */}
        {activeTab === 'swing' && (
          <div className="p-12 border border-dashed rounded-xl text-center text-gray-500 flex flex-col items-center justify-center gap-3">
            <TrendingUp size={36} className="text-gray-400" />
            <h5 className="font-bold text-md">Swing Scanning Modules</h5>
            <p className="text-xs max-w-sm">Calculates daily breakouts, momentum indicators, and short-interest triggers for swing positioning.</p>
          </div>
        )}

        {/* Tab view: Archives */}
        {activeTab === 'archives' && (
          <div className="p-12 border border-dashed rounded-xl text-center text-gray-500 flex flex-col items-center justify-center gap-3">
            <FolderArchive size={36} className="text-gray-400" />
            <h5 className="font-bold text-md">Past Forensic Audits</h5>
            <p className="text-xs max-w-sm">Review historic CSV strikes and markdown report logs of previous market fragility events.</p>
          </div>
        )}

        {/* Tab view: Guide */}
        {activeTab === 'guide' && (
          <div className="space-y-6">
            <div className={`p-6 rounded-xl border ${theme === 'dark' ? 'bg-[#0f172a] border-gray-800' : 'bg-white border-gray-200'}`}>
              <h3 className="font-bold text-md mb-3 flex items-center gap-2">
                <HelpCircle size={18} className="text-red-500" />
                <span>Financial Score Dictionary</span>
              </h3>
              <div className="space-y-4 text-sm mt-4 text-gray-400">
                <div>
                  <h4 className="font-bold text-gray-100 mb-1">AVS (Altair Vulnerability Score)</h4>
                  <p className="text-xs">A consolidated index from 0 to 100 weighing insolvency, accruals, leverage, and manipulation scores. Higher means more fragile.</p>
                </div>
                <div>
                  <h4 className="font-bold text-gray-100 mb-1">Altman Z-Score</h4>
                  <p className="text-xs">A classic solvency check model. Scores below 1.8 indicate a high risk of bankruptcy (Vulnerable), while scores above 3.0 denote safe zones.</p>
                </div>
                <div>
                  <h4 className="font-bold text-gray-100 mb-1">Sloan Ratio</h4>
                  <p className="text-xs">Identifies discrepancy between earnings and cash flows (accruals). Ratio values outside [-10%, +10%] suggest low earnings quality.</p>
                </div>
                <div>
                  <h4 className="font-bold text-gray-100 mb-1">Beneish M-Score</h4>
                  <p className="text-xs">Mathematical model using eight financial ratios to identify whether a company has manipulated its earnings. Scores greater than -1.78 highlight potential manipulation.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Right Drawer Slide-Over: Financial Ticker Detail */}
      {detailTicker && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end transition-opacity">
          <div className={`w-full max-w-xl p-6 h-full flex flex-col justify-between shadow-2xl relative animate-slide-in overflow-y-auto ${
            theme === 'dark' ? 'bg-[#0f172a] text-gray-100 border-l border-gray-800' : 'bg-white text-gray-900 border-l border-gray-200'
          }`}>
            <div>
              {/* Close Button */}
              <div className="flex items-center justify-between pb-6 border-b border-inherit mb-6">
                <div>
                  <h3 className="font-extrabold text-xl">{detailTicker}</h3>
                  <span className="text-xs text-gray-500 font-semibold uppercase">Company Diagnostics</span>
                </div>
                <button 
                  onClick={() => setDetailTicker(null)}
                  className={`p-2 rounded-lg border ${theme === 'dark' ? 'border-gray-800 hover:bg-gray-800' : 'border-gray-200 hover:bg-gray-100'}`}
                >
                  <X size={18} />
                </button>
              </div>

              {detailLoading ? (
                <div className="p-12 text-center text-gray-400 flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="animate-spin text-red-500" size={24} />
                  <p className="text-sm">Pulling balance sheet metrics...</p>
                </div>
              ) : detailData ? (
                <div className="space-y-6">
                  {/* Summary Metric cards */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className={`p-4 rounded-lg border ${theme === 'dark' ? 'bg-gray-900/40 border-gray-800' : 'bg-gray-50 border-gray-100'}`}>
                      <span className="text-xs font-semibold text-gray-500 uppercase block mb-1">Fragility Score</span>
                      <span className="text-2xl font-bold text-red-500">{detailData.avs_score}%</span>
                    </div>
                    <div className={`p-4 rounded-lg border ${theme === 'dark' ? 'bg-gray-900/40 border-gray-800' : 'bg-gray-50 border-gray-100'}`}>
                      <span className="text-xs font-semibold text-gray-500 uppercase block mb-1">Altman Status</span>
                      <span className="text-md font-bold">{detailData.z_status || 'Grey Zone'}</span>
                    </div>
                  </div>

                  {/* Complete Breakdown Items */}
                  <div className={`rounded-xl border divide-y ${theme === 'dark' ? 'border-gray-800 divide-gray-800' : 'border-gray-200 divide-gray-200'}`}>
                    {Object.entries(detailData)
                      .filter(([key]) => !['ticker', 'avs_score', 'z_status'].includes(key))
                      .map(([key, val]) => (
                        <div key={key} className="p-4 flex items-center justify-between">
                          <span className="text-xs font-medium text-gray-500 uppercase">{key.replace('_', ' ')}</span>
                          <span className="text-sm font-semibold">{val !== null ? String(val) : 'N/A'}</span>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-400">Failed to load data</div>
              )}
            </div>
            
            <div className="pt-6 border-t border-inherit flex gap-3">
              <button 
                onClick={() => setDetailTicker(null)}
                className={`w-full py-2.5 rounded-lg text-sm font-bold border transition-colors ${
                  theme === 'dark' ? 'border-gray-800 hover:bg-gray-800' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                Close View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Right Drawer Slide-Over: Astro Ticker Detail */}
      {astroDetail && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end transition-opacity">
          <div className={`w-full max-w-xl p-6 h-full flex flex-col justify-between shadow-2xl relative animate-slide-in overflow-y-auto ${
            theme === 'dark' ? 'bg-[#0f172a] text-gray-100 border-l border-gray-800' : 'bg-white text-gray-900 border-l border-gray-200'
          }`}>
            <div>
              {/* Close Button */}
              <div className="flex items-center justify-between pb-6 border-b border-inherit mb-6">
                <div>
                  <h3 className="font-extrabold text-xl">{astroDetail.name}</h3>
                  <span className="text-xs text-gray-500 font-semibold uppercase">{astroDetail.ticker} Astro-Financial Summary</span>
                </div>
                <button 
                  onClick={() => setAstroDetail(null)}
                  className={`p-2 rounded-lg border ${theme === 'dark' ? 'border-gray-800 hover:bg-gray-800' : 'border-gray-200 hover:bg-gray-100'}`}
                >
                  <X size={18} />
                </button>
              </div>

              {astroDetailLoading ? (
                <div className="p-12 text-center text-gray-400 flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="animate-spin text-red-500" size={24} />
                  <p className="text-sm">Calculating planet positions...</p>
                </div>
              ) : astroDetail ? (
                <div className="space-y-6">
                  {/* Birth Profile Card */}
                  <div className={`p-4 rounded-xl border ${theme === 'dark' ? 'bg-gray-900/40 border-gray-800' : 'bg-gray-50 border-gray-100'}`}>
                    <h5 className="font-bold text-sm mb-3">Incorporation Birth Data</h5>
                    <div className="grid grid-cols-2 gap-4 text-xs text-gray-400">
                      <div>
                        <p className="font-medium text-gray-500">Date/Time</p>
                        <p className="font-semibold text-gray-200">{astroDetail.birth_data?.date} @ {astroDetail.birth_data?.time}</p>
                      </div>
                      <div>
                        <p className="font-medium text-gray-500">Coordinates</p>
                        <p className="font-semibold text-gray-200">{astroDetail.birth_data?.city} ({astroDetail.birth_data?.latitude}, {astroDetail.birth_data?.longitude})</p>
                      </div>
                    </div>
                  </div>

                  {/* Active Dasha Periods */}
                  <div className={`p-4 rounded-xl border ${theme === 'dark' ? 'bg-gray-900/40 border-gray-800' : 'bg-gray-50 border-gray-100'}`}>
                    <h5 className="font-bold text-sm mb-3">Vimshottari Dasha Lords</h5>
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div className="p-3 bg-red-500/10 rounded-lg">
                        <p className="text-[10px] uppercase font-semibold text-gray-400">Mahadasha Lord</p>
                        <p className="text-lg font-bold text-red-500">{astroDetail.active_dasha?.mahadasha}</p>
                      </div>
                      <div className="p-3 bg-indigo-500/10 rounded-lg">
                        <p className="text-[10px] uppercase font-semibold text-gray-400">Bhukti Lord</p>
                        <p className="text-lg font-bold text-indigo-500">{astroDetail.active_dasha?.bhukti}</p>
                      </div>
                    </div>
                  </div>

                  {/* Planetary Placements Table */}
                  <div className={`rounded-xl border divide-y overflow-hidden ${theme === 'dark' ? 'border-gray-800 divide-gray-800' : 'border-gray-200 divide-gray-200'}`}>
                    <div className={`p-3 text-xs font-bold uppercase text-gray-500 ${theme === 'dark' ? 'bg-gray-900/60' : 'bg-gray-50'}`}>
                      Planetary Aspects
                    </div>
                    {astroDetail.natal_planets && Object.entries(astroDetail.natal_planets).map(([planet, sign]) => (
                      <div key={planet} className="p-3 flex items-center justify-between text-xs">
                        <span className="font-semibold uppercase text-gray-400">{planet}</span>
                        <span className="font-bold">{sign}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-400">Failed to load details</div>
              )}
            </div>
            
            <div className="pt-6 border-t border-inherit">
              <button 
                onClick={() => setAstroDetail(null)}
                className={`w-full py-2.5 rounded-lg text-sm font-bold border transition-colors ${
                  theme === 'dark' ? 'border-gray-800 hover:bg-gray-800' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                Close Detail
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
