import { useState, useEffect, createContext, useContext, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import { Toaster, toast } from "sonner";
import {
  TrendingUp,
  TrendingDown,
  History,
  Settings,
  LogOut,
  User,
  BarChart3,
  Target,
  Zap,
  AlertTriangle,
  Check,
  X,
  Plus,
  RefreshCw,
  Volume2,
  VolumeX,
  Bell,
  BellOff,
  ChevronRight,
  Activity,
  Award,
  Flame,
  Circle,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from "recharts";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setUser(response.data);
        } catch (error) {
          localStorage.removeItem("token");
          setToken(null);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    localStorage.setItem("token", response.data.access_token);
    setToken(response.data.access_token);
    setUser(response.data.user);
    return response.data;
  };

  const register = async (email, password, name) => {
    const response = await axios.post(`${API}/auth/register`, { email, password, name });
    localStorage.setItem("token", response.data.access_token);
    setToken(response.data.access_token);
    setUser(response.data.user);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const authAxios = axios.create({
    baseURL: API,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading, authAxios }}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// ==================== COMPONENTS ====================

// Probability Circle Component
const ProbabilityCircle = ({ percentage, color, size = 120, label }) => {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const colorMap = {
    red: "#dc2626",
    black: "#71717a",
    white: "#ffffff",
  };

  const bgColorMap = {
    red: "rgba(220, 38, 38, 0.1)",
    black: "rgba(39, 39, 42, 0.5)",
    white: "rgba(255, 255, 255, 0.1)",
  };

  return (
    <div className="probability-circle flex flex-col items-center gap-2">
      <div
        className="relative rounded-full p-1"
        style={{ background: bgColorMap[color] }}
      >
        <svg width={size} height={size}>
          <circle
            className="circle-bg"
            strokeWidth={strokeWidth}
            fill="transparent"
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            className="circle-progress"
            stroke={colorMap[color]}
            strokeWidth={strokeWidth}
            fill="transparent"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: offset,
            }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-2xl font-bold" style={{ color: colorMap[color] }}>
            {percentage.toFixed(1)}%
          </span>
        </div>
      </div>
      <span className="text-zinc-400 text-sm font-medium uppercase tracking-wider">{label}</span>
    </div>
  );
};

// Color Ball Component
const ColorBall = ({ color, size = "md", onClick, active }) => {
  const sizeMap = {
    sm: "w-6 h-6",
    md: "w-10 h-10",
    lg: "w-14 h-14",
    xl: "w-20 h-20",
  };

  const colorClass = {
    red: "color-red",
    black: "color-black",
    white: "color-white",
  };

  return (
    <button
      onClick={onClick}
      data-testid={`color-ball-${color}`}
      className={`
        ${sizeMap[size]} 
        ${colorClass[color]} 
        rounded-full 
        transition-all 
        duration-300
        ${active ? "ring-4 ring-offset-2 ring-offset-[#09090b] ring-white/50 scale-110" : ""}
        ${onClick ? "cursor-pointer hover:scale-110 hover:brightness-110" : ""}
      `}
    />
  );
};

// Status Badge Component
const StatusBadge = ({ status }) => {
  const statusConfig = {
    win: { icon: Check, className: "status-win", label: "WIN" },
    loss: { icon: X, className: "status-loss", label: "LOSS" },
    pending: { icon: RefreshCw, className: "status-pending", label: "AGUARDANDO" },
  };

  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <span className={`${config.className} px-3 py-1 rounded-full text-xs font-bold uppercase flex items-center gap-1`}>
      <Icon size={12} className={status === "pending" ? "animate-spin" : ""} />
      {config.label}
    </span>
  );
};

// Navbar Component
const Navbar = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="glass sticky top-0 z-50 border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center animate-pulse-red">
              <Flame size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">BLAZE AI</h1>
              <p className="text-xs text-zinc-500">Análise Inteligente</p>
            </div>
          </div>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            {[
              { id: "dashboard", icon: Activity, label: "Dashboard" },
              { id: "history", icon: History, label: "Histórico" },
              { id: "stats", icon: BarChart3, label: "Estatísticas" },
              { id: "settings", icon: Settings, label: "Configurações" },
            ].map((item) => (
              <button
                key={item.id}
                data-testid={`nav-${item.id}`}
                onClick={() => setActiveTab(item.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${activeTab === item.id
                    ? "bg-red-600/20 text-red-500"
                    : "text-zinc-400 hover:text-white hover:bg-white/5"
                  }
                `}
              >
                <item.icon size={18} />
                {item.label}
              </button>
            ))}
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center">
                <User size={16} className="text-zinc-400" />
              </div>
              <span className="text-sm text-zinc-300">{user?.name}</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              data-testid="logout-btn"
              className="text-zinc-400 hover:text-red-500 hover:bg-red-500/10"
            >
              <LogOut size={18} />
            </Button>
          </div>
        </div>

        {/* Mobile Nav */}
        <div className="md:hidden flex items-center gap-1 pb-3 overflow-x-auto">
          {[
            { id: "dashboard", icon: Activity },
            { id: "history", icon: History },
            { id: "stats", icon: BarChart3 },
            { id: "settings", icon: Settings },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`
                p-3 rounded-lg transition-all
                ${activeTab === item.id ? "bg-red-600/20 text-red-500" : "text-zinc-400"}
              `}
            >
              <item.icon size={20} />
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
};

// ==================== PAGES ====================

// Login Page
const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login, register, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Login realizado com sucesso!");
      } else {
        await register(email, password, name);
        toast.success("Conta criada com sucesso!");
      }
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao processar solicitação");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen hero-gradient flex items-center justify-center p-4">
      <div className="noise-overlay" />
      
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-red-600/5 rounded-full blur-3xl animate-float" style={{ animationDelay: "1s" }} />
      </div>

      <Card className="w-full max-w-md bg-[#121214]/80 border-zinc-800/50 backdrop-blur-xl animate-slideIn">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center mb-4 animate-pulse-red">
            <Flame size={32} className="text-white" />
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight">BLAZE AI BOT</CardTitle>
          <CardDescription className="text-zinc-400">
            Análise inteligente com IA para suas decisões
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs value={isLogin ? "login" : "register"} className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-zinc-900/50 mb-6">
              <TabsTrigger
                value="login"
                onClick={() => setIsLogin(true)}
                data-testid="tab-login"
                className="data-[state=active]:bg-red-600 data-[state=active]:text-white"
              >
                Entrar
              </TabsTrigger>
              <TabsTrigger
                value="register"
                onClick={() => setIsLogin(false)}
                data-testid="tab-register"
                className="data-[state=active]:bg-red-600 data-[state=active]:text-white"
              >
                Cadastrar
              </TabsTrigger>
            </TabsList>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-2 animate-fadeIn">
                  <Label htmlFor="name" className="text-zinc-300">Nome</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Seu nome"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={!isLogin}
                    data-testid="input-name"
                    className="bg-zinc-900/50 border-zinc-800 focus:border-red-600"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-zinc-300">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  data-testid="input-email"
                  className="bg-zinc-900/50 border-zinc-800 focus:border-red-600"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-zinc-300">Senha</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    data-testid="input-password"
                    className="bg-zinc-900/50 border-zinc-800 focus:border-red-600 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                data-testid="submit-btn"
                className="w-full btn-primary h-12 text-base font-bold"
              >
                {loading ? (
                  <RefreshCw className="animate-spin mr-2" size={18} />
                ) : null}
                {isLogin ? "Entrar" : "Criar Conta"}
              </Button>
            </form>
          </Tabs>

          <p className="text-center text-xs text-zinc-500 mt-6">
            Ao continuar, você concorda com nossos termos de uso e reconhece os riscos envolvidos em apostas.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

// Dashboard Page
const DashboardPage = () => {
  const { authAxios } = useAuth();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      // First load fast data
      const [histRes, resultsRes, statsRes, settingsRes, chartRes] = await Promise.all([
        authAxios.get("/history?limit=20"),
        authAxios.get("/results?limit=30"),
        authAxios.get("/statistics"),
        authAxios.get("/settings"),
        authAxios.get("/chart-data?days=7"),
      ]);

      setHistory(histRes.data);
      setResults(resultsRes.data);
      setStats(statsRes.data);
      setSettings(settingsRes.data);
      setChartData(chartRes.data);
      setLoading(false);

      // Then load AI prediction (slower)
      const predRes = await authAxios.get("/prediction");
      setPrediction(predRes.data);
    } catch (error) {
      toast.error("Erro ao carregar dados");
      setLoading(false);
    }
  }, [authAxios]);

  useEffect(() => {
    fetchData();
    
    // Auto refresh every 30 seconds
    const interval = setInterval(() => {
      fetchData();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchData]);

  const refreshPrediction = async () => {
    setRefreshing(true);
    try {
      const response = await authAxios.get("/prediction");
      setPrediction(response.data);
      toast.success("Análise atualizada!");
      
      // Play sound if enabled
      if (settings?.sound_enabled) {
        const audio = new Audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleijgqNv8uocg");
        audio.volume = 0.3;
        audio.play().catch(() => {});
      }
    } catch (error) {
      toast.error("Erro ao atualizar análise");
    } finally {
      setRefreshing(false);
    }
  };

  const addResult = async (color) => {
    try {
      await authAxios.post("/result", { color });
      toast.success(`Resultado ${color.toUpperCase()} adicionado`);
      fetchData();
    } catch (error) {
      toast.error("Erro ao adicionar resultado");
    }
  };

  const updateSettings = async (newSettings) => {
    try {
      const response = await authAxios.put("/settings", newSettings);
      setSettings(response.data);
      toast.success("Configurações salvas!");
    } catch (error) {
      toast.error("Erro ao salvar configurações");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-zinc-400">Carregando análise...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b]">
      <div className="noise-overlay" />
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "dashboard" && (
          <DashboardContent
            prediction={prediction}
            results={results}
            stats={stats}
            settings={settings}
            refreshPrediction={refreshPrediction}
            refreshing={refreshing}
            addResult={addResult}
          />
        )}

        {activeTab === "history" && (
          <HistoryContent history={history} />
        )}

        {activeTab === "stats" && (
          <StatsContent stats={stats} chartData={chartData} />
        )}

        {activeTab === "settings" && (
          <SettingsContent settings={settings} updateSettings={updateSettings} />
        )}
      </main>
    </div>
  );
};

// Dashboard Content
const DashboardContent = ({ prediction, results, stats, settings, refreshPrediction, refreshing, addResult }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold">Análise Atual</h2>
          <p className="text-zinc-400 text-sm">
            Atualizado: {prediction?.timestamp ? new Date(prediction.timestamp).toLocaleTimeString('pt-BR') : '-'}
          </p>
        </div>
        <Button
          onClick={refreshPrediction}
          disabled={refreshing}
          data-testid="refresh-prediction-btn"
          className="btn-primary"
        >
          <RefreshCw size={18} className={refreshing ? "animate-spin mr-2" : "mr-2"} />
          Nova Análise
        </Button>
      </div>

      {/* Main Prediction Card */}
      <Card className="bg-[#121214] border-red-600/30 overflow-hidden relative">
        <div className="absolute inset-0 bg-gradient-to-br from-red-600/10 to-transparent pointer-events-none" />
        
        <CardContent className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Probability Circles */}
            <div className="flex flex-wrap justify-center gap-6 lg:col-span-1">
              <ProbabilityCircle
                percentage={prediction?.red_probability || 0}
                color="red"
                size={130}
                label="Vermelho"
              />
              <ProbabilityCircle
                percentage={prediction?.black_probability || 0}
                color="black"
                size={130}
                label="Preto"
              />
              <ProbabilityCircle
                percentage={prediction?.white_probability || 0}
                color="white"
                size={100}
                label="Branco"
              />
            </div>

            {/* Recommendation */}
            <div className="lg:col-span-2 space-y-6">
              {/* Main Signal */}
              <div className="flex items-center justify-center gap-4 p-6 rounded-xl bg-black/30">
                <ColorBall color={prediction?.recommended_color || 'red'} size="xl" />
                <div>
                  <p className="text-zinc-400 text-sm uppercase tracking-wider">Recomendação</p>
                  <h3 className="text-4xl font-bold uppercase" style={{
                    color: prediction?.recommended_color === 'red' ? '#dc2626' : 
                           prediction?.recommended_color === 'black' ? '#71717a' : '#ffffff'
                  }}>
                    {prediction?.recommended_color === 'red' ? 'VERMELHO' :
                     prediction?.recommended_color === 'black' ? 'PRETO' : 'BRANCO'}
                  </h3>
                  <div className="flex items-center gap-2 mt-2">
                    <Target size={16} className="text-green-500" />
                    <span className="text-green-500 font-mono font-bold">
                      {prediction?.confidence?.toFixed(1)}% de confiança
                    </span>
                  </div>
                </div>
              </div>

              {/* Martingale Levels */}
              <div className="bg-black/20 rounded-xl p-4">
                <h4 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
                  <Zap size={16} className="text-yellow-500" />
                  Níveis de Martingale (máx {settings?.max_martingales || 2})
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-zinc-500 text-xs uppercase">
                        <th className="text-left py-2">Entrada</th>
                        <th className="text-center py-2">Probabilidade</th>
                        <th className="text-center py-2">Hora</th>
                        <th className="text-right py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prediction?.martingale_levels?.map((level, idx) => (
                        <tr key={idx} className="border-t border-zinc-800/50">
                          <td className="py-3 font-medium">{level.level}</td>
                          <td className="py-3 text-center font-mono">
                            <span className={level.level === 'Loss' ? 'text-red-500' : 'text-green-500'}>
                              {level.probability?.toFixed(2)}%
                            </span>
                          </td>
                          <td className="py-3 text-center text-zinc-400">{level.time}</td>
                          <td className="py-3 text-right">
                            <StatusBadge status={level.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          {/* AI Analysis */}
          <div className="mt-6 p-4 rounded-xl bg-zinc-900/50 border border-zinc-800">
            <h4 className="text-sm font-medium text-zinc-300 mb-2 flex items-center gap-2">
              <Activity size={16} className="text-red-500" />
              Análise IA (GPT-5.2)
            </h4>
            <p className="text-zinc-400 text-sm whitespace-pre-line leading-relaxed">
              {prediction?.ai_analysis || 'Carregando análise...'}
            </p>
            {prediction?.sequence_info && (
              <div className="mt-3 flex items-center gap-2">
                <Badge variant="outline" className="border-yellow-500/30 text-yellow-500">
                  {prediction.sequence_info}
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats & Add Result */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quick Stats */}
        <Card className="bg-[#121214] border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Award size={20} className="text-yellow-500" />
              Estatísticas Rápidas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 rounded-lg bg-zinc-900/50">
                <p className="text-3xl font-bold text-green-500">{stats?.win_rate?.toFixed(1)}%</p>
                <p className="text-xs text-zinc-500 uppercase mt-1">Taxa de Acerto</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-zinc-900/50">
                <p className="text-3xl font-bold text-white">{stats?.total_predictions || 0}</p>
                <p className="text-xs text-zinc-500 uppercase mt-1">Total Análises</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-zinc-900/50">
                <div className="flex items-center justify-center gap-1">
                  <p className="text-3xl font-bold" style={{ 
                    color: stats?.streak_type === 'win' ? '#22c55e' : '#ef4444' 
                  }}>
                    {stats?.streak || 0}
                  </p>
                  {stats?.streak_type === 'win' ? 
                    <TrendingUp size={24} className="text-green-500" /> : 
                    <TrendingDown size={24} className="text-red-500" />
                  }
                </div>
                <p className="text-xs text-zinc-500 uppercase mt-1">Sequência Atual</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-zinc-900/50">
                <p className="text-3xl font-bold text-white">{stats?.today_wins || 0}</p>
                <p className="text-xs text-zinc-500 uppercase mt-1">Wins Hoje</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Add Result */}
        <Card className="bg-[#121214] border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Plus size={20} className="text-blue-500" />
              Adicionar Resultado
            </CardTitle>
            <CardDescription>Registre o resultado da última jogada</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex justify-center gap-6">
              {['red', 'black', 'white'].map((color) => (
                <button
                  key={color}
                  onClick={() => addResult(color)}
                  data-testid={`add-result-${color}`}
                  className="group flex flex-col items-center gap-2"
                >
                  <ColorBall color={color} size="lg" onClick={() => {}} />
                  <span className="text-xs text-zinc-500 uppercase group-hover:text-white transition-colors">
                    {color === 'red' ? 'Vermelho' : color === 'black' ? 'Preto' : 'Branco'}
                  </span>
                </button>
              ))}
            </div>

            {/* Recent Results */}
            <div className="mt-6">
              <p className="text-xs text-zinc-500 uppercase mb-3">Últimos Resultados</p>
              <div className="flex flex-wrap gap-2">
                {results.slice(0, 15).map((result, idx) => (
                  <ColorBall key={result.id || idx} color={result.color} size="sm" />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
        <AlertTriangle size={20} className="text-yellow-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-yellow-200/80">
          <strong>Aviso:</strong> As recomendações são baseadas em análise estatística e IA, mas não garantem resultados. 
          Aposte com responsabilidade e gerencie sua banca com cautela.
        </p>
      </div>
    </div>
  );
};

// History Content
const HistoryContent = ({ history }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <h2 className="text-2xl font-bold">Histórico de Análises</h2>
        <p className="text-zinc-400 text-sm">Suas últimas análises e resultados</p>
      </div>

      <Card className="bg-[#121214] border-zinc-800 overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-zinc-900/50">
                <tr className="text-xs text-zinc-500 uppercase">
                  <th className="text-left p-4">Data/Hora</th>
                  <th className="text-center p-4">Recomendação</th>
                  <th className="text-center p-4">Confiança</th>
                  <th className="text-center p-4">Resultado</th>
                  <th className="text-right p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-12 text-zinc-500">
                      Nenhuma análise registrada ainda
                    </td>
                  </tr>
                ) : (
                  history.map((item, idx) => (
                    <tr 
                      key={item.id || idx} 
                      className="border-t border-zinc-800/50 hover:bg-white/[0.02] transition-colors"
                      style={{ animationDelay: `${idx * 50}ms` }}
                    >
                      <td className="p-4 text-sm text-zinc-300">
                        {new Date(item.timestamp).toLocaleString('pt-BR')}
                      </td>
                      <td className="p-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <ColorBall color={item.recommended_color} size="sm" />
                          <span className="text-sm capitalize">{item.recommended_color}</span>
                        </div>
                      </td>
                      <td className="p-4 text-center">
                        <span className="font-mono text-green-500">{item.confidence?.toFixed(1)}%</span>
                      </td>
                      <td className="p-4 text-center">
                        {item.actual_result ? (
                          <div className="flex items-center justify-center gap-2">
                            <ColorBall color={item.actual_result} size="sm" />
                            <span className="text-sm capitalize">{item.actual_result}</span>
                          </div>
                        ) : (
                          <span className="text-zinc-500">-</span>
                        )}
                      </td>
                      <td className="p-4 text-right">
                        <StatusBadge status={item.status} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Stats Content
const StatsContent = ({ stats, chartData }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <h2 className="text-2xl font-bold">Estatísticas</h2>
        <p className="text-zinc-400 text-sm">Análise detalhada do seu desempenho</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total", value: stats?.total_predictions || 0, icon: BarChart3, color: "text-blue-500" },
          { label: "Wins", value: stats?.wins || 0, icon: TrendingUp, color: "text-green-500" },
          { label: "Losses", value: stats?.losses || 0, icon: TrendingDown, color: "text-red-500" },
          { label: "Taxa", value: `${stats?.win_rate?.toFixed(1) || 0}%`, icon: Target, color: "text-yellow-500" },
        ].map((stat, idx) => (
          <Card key={idx} className="bg-[#121214] border-zinc-800 card-hover">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <stat.icon size={24} className={stat.color} />
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              </div>
              <p className="text-xs text-zinc-500 uppercase mt-2">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Chart */}
      <Card className="bg-[#121214] border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg">Desempenho dos Últimos 7 Dias</CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorWins" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorLosses" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="date" stroke="#71717a" fontSize={12} />
                  <YAxis stroke="#71717a" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#121214",
                      border: "1px solid #27272a",
                      borderRadius: "8px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="wins"
                    stroke="#22c55e"
                    fillOpacity={1}
                    fill="url(#colorWins)"
                    name="Wins"
                  />
                  <Area
                    type="monotone"
                    dataKey="losses"
                    stroke="#ef4444"
                    fillOpacity={1}
                    fill="url(#colorLosses)"
                    name="Losses"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-80 flex items-center justify-center text-zinc-500">
              Dados insuficientes para gerar gráfico
            </div>
          )}
        </CardContent>
      </Card>

      {/* Win Rate Progress */}
      <Card className="bg-[#121214] border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg">Taxa de Acerto</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Progress 
              value={stats?.win_rate || 0} 
              className="h-4 bg-zinc-800"
            />
            <div className="flex justify-between text-sm">
              <span className="text-zinc-400">0%</span>
              <span className="text-green-500 font-bold">{stats?.win_rate?.toFixed(1) || 0}%</span>
              <span className="text-zinc-400">100%</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Settings Content
const SettingsContent = ({ settings, updateSettings }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleSave = () => {
    updateSettings(localSettings);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <h2 className="text-2xl font-bold">Configurações</h2>
        <p className="text-zinc-400 text-sm">Personalize sua experiência</p>
      </div>

      <div className="grid gap-6 max-w-2xl">
        {/* Analysis Settings */}
        <Card className="bg-[#121214] border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Target size={20} className="text-red-500" />
              Configurações de Análise
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label className="text-zinc-300">Máximo de Martingales</Label>
              <Select
                value={String(localSettings?.max_martingales || 2)}
                onValueChange={(value) => setLocalSettings({ ...localSettings, max_martingales: parseInt(value) })}
              >
                <SelectTrigger data-testid="select-martingales" className="bg-zinc-900/50 border-zinc-800">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n} martingale{n > 1 ? 's' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-zinc-500">
                Número máximo de entradas após a principal
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-zinc-300">Probabilidade Mínima</Label>
              <Select
                value={String(localSettings?.min_probability || 70)}
                onValueChange={(value) => setLocalSettings({ ...localSettings, min_probability: parseInt(value) })}
              >
                <SelectTrigger data-testid="select-probability" className="bg-zinc-900/50 border-zinc-800">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[50, 60, 70, 75, 80, 85, 90].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n}%
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-zinc-500">
                Exibir apenas análises com confiança acima deste valor
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card className="bg-[#121214] border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Bell size={20} className="text-yellow-500" />
              Notificações
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-zinc-300">Notificações Push</Label>
                <p className="text-xs text-zinc-500">Receber alertas de novas análises</p>
              </div>
              <Switch
                checked={localSettings?.notifications_enabled}
                onCheckedChange={(checked) => setLocalSettings({ ...localSettings, notifications_enabled: checked })}
                data-testid="switch-notifications"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-zinc-300">Sons</Label>
                <p className="text-xs text-zinc-500">Reproduzir som ao atualizar análise</p>
              </div>
              <Switch
                checked={localSettings?.sound_enabled}
                onCheckedChange={(checked) => setLocalSettings({ ...localSettings, sound_enabled: checked })}
                data-testid="switch-sound"
              />
            </div>
          </CardContent>
        </Card>

        <Button 
          onClick={handleSave} 
          data-testid="save-settings-btn"
          className="btn-primary w-full"
        >
          Salvar Configurações
        </Button>
      </div>
    </div>
  );
};

// ==================== APP ====================

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster 
          position="top-right" 
          richColors 
          theme="dark"
          toastOptions={{
            style: {
              background: '#121214',
              border: '1px solid #27272a',
            },
          }}
        />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
