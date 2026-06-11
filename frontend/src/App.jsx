import { useState, useEffect } from "react"
import axios from "axios"
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts"
import {
  ChefHat, TrendingUp, CheckCircle,
  Send, Clock, MapPin,
  DollarSign, BarChart2, Zap, RefreshCw, ChevronDown
} from "lucide-react"

// ── Utility Components ────────────────────────────────────────────

const RiskBadge = ({ level }) => {
  const styles = {
    LOW:    "bg-green-100 text-green-800 border border-green-200",
    MEDIUM: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    HIGH:   "bg-red-100 text-red-800 border border-red-200",
  }
  const icons = { LOW: "🟢", MEDIUM: "🟡", HIGH: "🔴" }
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${styles[level] || styles.LOW}`}>
      {icons[level]} {level}
    </span>
  )
}

const ConfidenceBar = ({ percentage, level }) => {
  const colors = { HIGH: "#22c55e", MEDIUM: "#f59e0b", LOW: "#ef4444" }
  const color = colors[level] || colors.MEDIUM
  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-500">Confidence</span>
        <span className="text-sm font-bold" style={{ color }}>
          {percentage?.toFixed(0)}% {level}
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-3">
        <div
          className="h-3 rounded-full transition-all duration-700"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

const StatCard = ({ icon, label, value, sub, color = "blue" }) => {
  const colors = {
    blue:   "bg-blue-50 text-blue-600",
    green:  "bg-green-50 text-green-600",
    yellow: "bg-yellow-50 text-yellow-600",
    purple: "bg-purple-50 text-purple-600",
  }
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-xl ${colors[color]}`}>{icon}</div>
        <span className="text-xs text-gray-500 font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

// ── Vendor Selector ───────────────────────────────────────────────

const VendorSelector = ({ vendors, selected, onSelect }) => {
  const [open, setOpen] = useState(false)
  const current = vendors.find(v => v.vendor_id === selected)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm hover:border-blue-300 transition-colors w-full"
      >
        <div className="w-8 h-8 bg-blue-100 rounded-xl flex items-center justify-center">
          <ChefHat size={16} className="text-blue-600" />
        </div>
        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-gray-900">
            {current?.stall_name || "Select a stall"}
          </p>
          <p className="text-xs text-gray-400">{current?.hawker_centre || "Choose vendor"}</p>
        </div>
        <ChevronDown size={16} className="text-gray-400" />
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-2xl shadow-xl z-50 overflow-hidden">
          {vendors.map(v => (
            <button
              key={v.vendor_id}
              onClick={() => { onSelect(v.vendor_id); setOpen(false) }}
              className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-blue-50 transition-colors text-left
                ${v.vendor_id === selected ? "bg-blue-50" : ""}`}
            >
              <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center text-sm">
                🍜
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{v.stall_name}</p>
                <p className="text-xs text-gray-400">{v.hawker_centre} · {v.area_type}</p>
              </div>
              {v.vendor_id === selected && (
                <CheckCircle size={14} className="text-blue-500 ml-auto" />
              )}
            </button>
          ))}
          <div className="border-t border-gray-100 p-2">
            <button
              onClick={() => { onSelect("register"); setOpen(false) }}
              className="w-full text-center text-xs text-blue-600 font-medium py-2 hover:bg-blue-50 rounded-xl"
            >
              + Register your stall
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Register Vendor Form ──────────────────────────────────────────

const RegisterVendorForm = ({ onSuccess, onCancel }) => {
  const [form, setForm] = useState({
    stall_name: "", owner_name: "", hawker_centre: "",
    address: "", area_type: "heartland", near_mrt: false,
    mrt_station: "", near_school: false, school_name: "",
    items: "", avg_price_sgd: "4.50", daily_capacity: "100",
    operating_days: ["Mon","Tue","Wed","Thu","Fri"],
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

  const toggleDay = (day) => {
    setForm(f => ({
      ...f,
      operating_days: f.operating_days.includes(day)
        ? f.operating_days.filter(d => d !== day)
        : [...f.operating_days, day]
    }))
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = {
        ...form,
        items: form.items.split(",").map(i => i.trim()).filter(Boolean),
        avg_price_sgd: parseFloat(form.avg_price_sgd),
        daily_capacity: parseInt(form.daily_capacity),
      }
      const res = await axios.post("/api/v1/vendors/register", payload)
      onSuccess(res.data.vendor_id, res.data.stall_name)
    } catch (e) {
      setError(e.response?.data?.detail || "Registration failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-bold text-gray-900 mb-4">Register Your Stall</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          ["stall_name","Stall Name","e.g. Ah Kow Chicken Rice"],
          ["owner_name","Owner Name","e.g. Mr Tan"],
          ["hawker_centre","Hawker Centre","e.g. Toa Payoh Lorong 8"],
          ["address","Address","Block and street"],
          ["mrt_station","MRT Station (if near)","e.g. Toa Payoh MRT"],
          ["school_name","Nearby School (if any)","e.g. CHIJ Primary"],
        ].map(([key, label, placeholder]) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
            <input
              value={form[key]}
              onChange={e => setForm({...form, [key]: e.target.value})}
              placeholder={placeholder}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        ))}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Area Type</label>
          <select
            value={form.area_type}
            onChange={e => setForm({...form, area_type: e.target.value})}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {["heartland","cbd","tourist","suburban"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Menu Items (comma separated)</label>
          <input
            value={form.items}
            onChange={e => setForm({...form, items: e.target.value})}
            placeholder="Chicken Rice, Roast Duck Rice"
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Avg Price (SGD)</label>
          <input
            type="number" step="0.50"
            value={form.avg_price_sgd}
            onChange={e => setForm({...form, avg_price_sgd: e.target.value})}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Daily Capacity (portions)</label>
          <input
            type="number"
            value={form.daily_capacity}
            onChange={e => setForm({...form, daily_capacity: e.target.value})}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      <div className="mt-4">
        <label className="block text-xs font-medium text-gray-600 mb-2">Operating Days</label>
        <div className="flex gap-2 flex-wrap">
          {days.map(d => (
            <button
              key={d}
              onClick={() => toggleDay(d)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors
                ${form.operating_days.includes(d)
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600"}`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4 mt-3">
        <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
          <input type="checkbox" checked={form.near_mrt}
            onChange={e => setForm({...form, near_mrt: e.target.checked})} />
          Near MRT
        </label>
        <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
          <input type="checkbox" checked={form.near_school}
            onChange={e => setForm({...form, near_school: e.target.checked})} />
          Near School
        </label>
      </div>

      {error && <p className="text-red-500 text-xs mt-3">{error}</p>}

      <div className="flex gap-3 mt-5">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold px-5 py-2 rounded-xl text-sm"
        >
          {loading ? "Registering..." : "Register Stall"}
        </button>
        <button
          onClick={onCancel}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold px-5 py-2 rounded-xl text-sm"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── 7-Day Forecast Chart ──────────────────────────────────────────

const WeekForecastChart = ({ vendorId, itemName }) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!vendorId || !itemName) return
    setLoading(true)
    axios.post("/api/v1/forecast/week", {
      item_name: itemName,
      vendor_id: vendorId,
    })
    .then(r => setData(r.data))
    .catch(console.error)
    .finally(() => setLoading(false))
  }, [vendorId, itemName])

  if (loading) return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 h-48 flex items-center justify-center">
      <RefreshCw size={20} className="animate-spin text-blue-400" />
    </div>
  )
  if (!data) return null

  const chartData = data.days.map(d => ({
    day: d.day_name.slice(0, 3),
    predicted: d.predicted_quantity,
    lower: d.confidence_lower,
    upper: d.confidence_upper,
    rain: d.rain_probability > 0.6,
    holiday: d.is_holiday || d.is_school_holiday,
    fullDay: d.day_name,
  }))

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-lg text-xs">
        <p className="font-bold text-gray-800">{d?.fullDay}</p>
        <p className="text-blue-600">Forecast: <strong>{payload[0]?.value} portions</strong></p>
        <p className="text-gray-400">Range: {d?.lower} – {d?.upper}</p>
        {d?.rain && <p className="text-blue-400">🌧️ Rain expected</p>}
        {d?.holiday && <p className="text-orange-400">📅 Holiday</p>}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-800">7-Day Demand Forecast</h3>
        <div className="flex gap-3 text-xs text-gray-400">
          <span>📈 Avg: <strong>{data.avg_predicted}</strong></span>
          <span>🔝 Peak: <strong>{data.peak_day}</strong></span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="day" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="predicted" stroke="#3b82f6"
            strokeWidth={2.5} dot={{ fill: "#3b82f6", r: 4 }} activeDot={{ r: 6 }} />
          <Line type="monotone" dataKey="upper" stroke="#93c5fd"
            strokeWidth={1} strokeDasharray="4 4" dot={false} />
          <Line type="monotone" dataKey="lower" stroke="#93c5fd"
            strokeWidth={1} strokeDasharray="4 4" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Recommendation History ────────────────────────────────────────

const HistoryFeed = ({ vendorId }) => {
  const [history, setHistory] = useState([])

  useEffect(() => {
    if (!vendorId) return
    axios.get(`/api/v1/vendors/${vendorId}/history?limit=5`)
      .then(r => setHistory(r.data.history || []))
      .catch(console.error)
  }, [vendorId])

  if (!history.length) return null

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Recent Recommendations</h3>
      <div className="space-y-2">
        {history.map(h => (
          <div key={h.id}
            className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
          >
            <div>
              <p className="text-xs font-medium text-gray-800">{h.item_name}</p>
              <p className="text-xs text-gray-400">{h.forecast_date}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-blue-600">
                {h.recommended_prep_quantity}
              </span>
              <span className="text-xs text-gray-400">portions</span>
              <RiskBadge level={h.confidence_level} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Demo Mode Components ──────────────────────────────────────────

const FeatureBar = ({ label, value, max = 1 }) => {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-36 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-700 w-12 text-right">
        {typeof value === "number" && value < 1 ? value.toFixed(3) : value}
      </span>
    </div>
  )
}

const ConfidenceBreakdownPanel = ({ breakdown }) => {
  if (!breakdown) return null
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">
        🎯 Confidence Score Breakdown
      </h3>
      <div className="space-y-3">
        <FeatureBar label="Retrieval Quality"  value={breakdown.retrieval_quality}  max={30} />
        <FeatureBar label="Sales Stability"    value={breakdown.sales_stability}    max={30} />
        <FeatureBar label="Weather Certainty"  value={breakdown.weather_certainty}  max={20} />
        <FeatureBar label="Day Predictability" value={breakdown.day_predictability} max={15} />
        <FeatureBar label="Lag Signal"         value={breakdown.lag_signal}         max={5}  />
      </div>
      <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between items-center">
        <span className="text-xs text-red-400">
          Penalties: -{breakdown.penalties?.toFixed(1)} pts
        </span>
        <span className="text-sm font-bold text-blue-600">
          Final: {breakdown.final_percentage?.toFixed(1)}% ({breakdown.final_level})
        </span>
      </div>
    </div>
  )
}

const LayerTracePanel = ({ trace }) => {
  if (!trace) return null
  return (
    <div className="space-y-4">

      {/* Layer 1 */}
      <div className="bg-white rounded-2xl border-l-4 border-blue-500 border border-gray-100 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="bg-blue-600 text-white text-xs font-bold px-2 py-0.5 rounded-lg">
            LAYER 1
          </span>
          <span className="text-sm font-semibold text-gray-800">
            XGBoost Forecast Engine
          </span>
        </div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-blue-50 rounded-xl p-3 text-center">
            <p className="text-xs text-blue-400">Predicted</p>
            <p className="text-xl font-bold text-blue-700">{trace.layer1_predicted}</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-400">Lower Bound</p>
            <p className="text-xl font-bold text-gray-600">{trace.layer1_confidence_lower}</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-400">Upper Bound</p>
            <p className="text-xl font-bold text-gray-600">{trace.layer1_confidence_upper}</p>
          </div>
        </div>
        <p className="text-xs font-medium text-gray-600 mb-2">Top Feature Importances</p>
        <div className="space-y-2">
          {Object.entries(trace.layer1_top_features || {}).map(([k, v]) => (
            <FeatureBar key={k} label={k} value={v} max={0.5} />
          ))}
        </div>
      </div>

      {/* Layer 2 */}
      <div className="bg-white rounded-2xl border-l-4 border-purple-500 border border-gray-100 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="bg-purple-600 text-white text-xs font-bold px-2 py-0.5 rounded-lg">
            LAYER 2
          </span>
          <span className="text-sm font-semibold text-gray-800">
            FAISS Vector Retrieval
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-purple-50 rounded-xl p-3 text-center">
            <p className="text-xs text-purple-400">Scenarios Found</p>
            <p className="text-xl font-bold text-purple-700">{trace.layer2_scenarios_found}</p>
          </div>
          <div className="bg-purple-50 rounded-xl p-3 text-center">
            <p className="text-xs text-purple-400">Avg Similarity</p>
            <p className="text-xl font-bold text-purple-700">
              {(trace.layer2_avg_similarity * 100).toFixed(1)}%
            </p>
          </div>
        </div>
        <p className="text-xs font-medium text-gray-600 mb-2">Top 3 Similar Historical Days</p>
        <div className="space-y-2">
          {trace.layer2_top_scenarios?.map((s, i) => (
            <div key={i}
              className="flex items-center justify-between bg-gray-50 rounded-xl px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-purple-500">#{i + 1}</span>
                <span className="text-xs text-gray-700">{s.date} ({s.day_name})</span>
                {s.rain_flag && <span className="text-xs">🌧️</span>}
                {s.is_holiday && <span className="text-xs">🎉</span>}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-gray-800">{s.quantity_sold} portions</span>
                <span className="text-xs text-gray-400">
                  {(s.similarity_score * 100).toFixed(1)}% match
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Layer 3 */}
      <div className="bg-white rounded-2xl border-l-4 border-green-500 border border-gray-100 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="bg-green-600 text-white text-xs font-bold px-2 py-0.5 rounded-lg">
            LAYER 3
          </span>
          <span className="text-sm font-semibold text-gray-800">
            GPT-4o-mini Reasoning
          </span>
        </div>
        <div className="bg-green-50 rounded-xl p-3 text-center">
          <p className="text-xs text-green-400 mb-1">Model Used</p>
          <p className="text-sm font-bold text-green-700">{trace.layer3_model}</p>
          <p className="text-xs text-green-500 mt-1">
            Synthesizes L1 + L2 → operational recommendation
          </p>
        </div>
      </div>
    </div>
  )
}

const ArchitectureDiagram = () => (
  <div className="bg-gray-900 rounded-2xl p-6 text-white">
    <h3 className="text-sm font-semibold mb-4 text-gray-300">🏗️ System Architecture</h3>
    <div className="space-y-3">
      {[
        {
          layer: "L1", color: "bg-blue-500",
          title: "Core Forecast Engine",
          desc: "XGBoost · TimeSeriesSplit CV · 20 SG features"
        },
        {
          layer: "L2", color: "bg-purple-500",
          title: "Intelligence Retrieval",
          desc: "FAISS · all-MiniLM-L6-v2 · Hybrid RAG"
        },
        {
          layer: "L3", color: "bg-green-500",
          title: "AI Copilot",
          desc: "GPT-4o-mini · Structured JSON output · Vendor-aware"
        },
      ].map((l, i) => (
        <div key={i}>
          <div className="flex items-center gap-3 bg-gray-800 rounded-xl p-3">
            <span className={`${l.color} text-white text-xs font-bold px-2 py-1 rounded-lg`}>
              {l.layer}
            </span>
            <div>
              <p className="text-sm font-semibold">{l.title}</p>
              <p className="text-xs text-gray-400">{l.desc}</p>
            </div>
          </div>
          {i < 2 && (
            <div className="flex justify-center my-1">
              <span className="text-gray-600 text-xs">↓</span>
            </div>
          )}
        </div>
      ))}
    </div>
    <div className="mt-4 pt-4 border-t border-gray-700 grid grid-cols-3 gap-2 text-center">
      {[["5","Vendors"],["20+","SG Features"],["180","Training Days"]].map(([val, label]) => (
        <div key={label}>
          <p className="text-lg font-bold text-white">{val}</p>
          <p className="text-xs text-gray-400">{label}</p>
        </div>
      ))}
    </div>
  </div>
)

// ── Main App ──────────────────────────────────────────────────────

export default function App() {
  const [demoMode, setDemoMode] = useState(false)
  const [vendors, setVendors] = useState([])
  const [selectedVendor, setSelectedVendor] = useState("vendor_001")
  const [vendorDetail, setVendorDetail] = useState(null)
  const [selectedItem, setSelectedItem] = useState("")
  const [forecastDate, setForecastDate] = useState(
    new Date(Date.now() + 86400000).toISOString().split("T")[0]
  )
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showRegister, setShowRegister] = useState(false)
  const [alertSent, setAlertSent] = useState(false)

  useEffect(() => {
    axios.get("/api/v1/vendors/")
      .then(r => setVendors(r.data))
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (!selectedVendor || selectedVendor === "register") return
    axios.get(`/api/v1/vendors/${selectedVendor}`)
      .then(r => {
        setVendorDetail(r.data)
        setSelectedItem(r.data.items?.[0] || "")
        setResult(null)
        setAlertSent(false)
      })
      .catch(console.error)
  }, [selectedVendor])

  const handleVendorSelect = (id) => {
    if (id === "register") {
      setShowRegister(true)
    } else {
      setSelectedVendor(id)
      setShowRegister(false)
    }
  }

  const handleGetRecommendation = async () => {
    setLoading(true)
    setError(null)
    setAlertSent(false)
    try {
      const res = await axios.post("/api/v1/copilot/recommend", {
        item_name: selectedItem,
        forecast_date: forecastDate,
        location: "Singapore",
        vendor_id: selectedVendor,
      })
      setResult(res.data)
      setAlertSent(!!vendorDetail?.telegram_chat_id)
    } catch (e) {
      setError(e.response?.data?.detail || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  const handleRegisterSuccess = (vendorId) => {
    setShowRegister(false)
    axios.get("/api/v1/vendors/").then(r => setVendors(r.data))
    setSelectedVendor(vendorId)
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <ChefHat size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">Hawker Copilot</h1>
              <p className="text-xs text-gray-400">AI-powered prep intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Demo Mode Toggle */}
            <div className="flex items-center bg-gray-100 rounded-xl p-1">
              <button
                onClick={() => setDemoMode(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${!demoMode ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
              >
                Vendor View
              </button>
              <button
                onClick={() => setDemoMode(true)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${demoMode ? "bg-blue-600 text-white shadow-sm" : "text-gray-500"}`}
              >
                🔬 Demo Mode
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs text-green-600 bg-green-50 px-3 py-1 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              AI Active
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-5">

        {/* Vendor Selector */}
        {showRegister ? (
          <RegisterVendorForm
            onSuccess={handleRegisterSuccess}
            onCancel={() => setShowRegister(false)}
          />
        ) : (
          <VendorSelector
            vendors={vendors}
            selected={selectedVendor}
            onSelect={handleVendorSelect}
          />
        )}

        {/* Vendor Info Strip */}
        {vendorDetail && !showRegister && (
          <div className="bg-white rounded-2xl border border-gray-100 px-5 py-3 shadow-sm">
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <MapPin size={12} /> {vendorDetail.hawker_centre}
              </span>
              <span className="flex items-center gap-1">
                <BarChart2 size={12} /> Capacity: {vendorDetail.daily_capacity}/day
              </span>
              <span className="flex items-center gap-1">
                <DollarSign size={12} /> Avg ${vendorDetail.avg_price_sgd?.toFixed(2)}/portion
              </span>
              {vendorDetail.near_mrt && (
                <span className="flex items-center gap-1">
                  🚇 {vendorDetail.mrt_station}
                </span>
              )}
              {vendorDetail.near_school && (
                <span className="flex items-center gap-1">
                  🏫 Near school
                </span>
              )}
            </div>
          </div>
        )}

        {/* Request Controls */}
        {!showRegister && (
          <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-800 mb-4">Get AI Recommendation</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Menu Item</label>
                <select
                  value={selectedItem}
                  onChange={e => setSelectedItem(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {vendorDetail?.items?.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Forecast Date</label>
                <input
                  type="date"
                  value={forecastDate}
                  onChange={e => setForecastDate(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleGetRecommendation}
                  disabled={loading || !selectedItem}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold px-4 py-2 rounded-xl text-sm flex items-center justify-center gap-2 transition-colors"
                >
                  {loading
                    ? <><RefreshCw size={14} className="animate-spin" /> Analyzing...</>
                    : <><Zap size={14} /> Get Recommendation</>
                  }
                </button>
              </div>
            </div>
            {error && <p className="text-red-500 text-xs mt-3">⚠️ {error}</p>}
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Main Recommendation Card */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 text-white shadow-lg">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-blue-200 text-xs font-medium mb-1">
                    {result.stall_name} · {result.item_name}
                  </p>
                  <h2 className="text-lg font-bold">Tonight's Prep Recommendation</h2>
                </div>
                {alertSent && (
                  <div className="flex items-center gap-1 bg-white/20 rounded-full px-3 py-1 text-xs">
                    <Send size={10} /> Alert sent
                  </div>
                )}
              </div>
              <div className="flex items-end gap-3 mb-4">
                <span className="text-7xl font-black">
                  {result.recommended_prep_quantity}
                </span>
                <span className="text-blue-200 mb-3 text-lg">portions</span>
              </div>
              <ConfidenceBar
                percentage={result.confidence_percentage}
                level={result.confidence_level}
              />
              <p className="text-blue-100 text-sm mt-4 leading-relaxed">
                {result.recommendation_text}
              </p>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard
                icon={<TrendingUp size={16} />}
                label="ML Forecast"
                value={result.predicted_quantity}
                sub="portions predicted"
                color="blue"
              />
              <StatCard
                icon={<DollarSign size={16} />}
                label="Expected Revenue"
                value={`$${result.revenue_estimate?.expected_revenue?.toFixed(0)}`}
                sub={`${result.revenue_estimate?.expected_sellthrough_pct?.toFixed(0)}% sell-through`}
                color="green"
              />
              <StatCard
                icon={<CheckCircle size={16} />}
                label="AI Saves You"
                value={`$${result.revenue_estimate?.vs_overprepare_savings?.toFixed(0)}`}
                sub="vs gut-feel overprepare"
                color="purple"
              />
              <StatCard
                icon={<Clock size={16} />}
                label="Capacity Used"
                value={`${vendorDetail
                  ? Math.round((result.recommended_prep_quantity / vendorDetail.daily_capacity) * 100)
                  : "--"}%`}
                sub={`of ${vendorDetail?.daily_capacity} daily capacity`}
                color="yellow"
              />
            </div>

            {/* AI Explanation + Risk */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-800 mb-3">🧠 AI Explanation</h3>
                <ul className="space-y-2">
                  {result.primary_factors?.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="text-blue-500 mt-0.5 text-xs">→</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-gray-50">
                  {result.historical_context}
                </p>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-800 mb-3">⚠️ Risk Assessment</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Waste Risk</span>
                    <RiskBadge level={result.waste_risk} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Shortage Risk</span>
                    <RiskBadge level={result.shortage_risk} />
                  </div>
                  <div className="border-t border-gray-50 pt-3">
                    <p className="text-xs text-gray-500 mb-2">Revenue Breakdown</p>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-400">Potential</span>
                      <span className="font-medium">
                        ${result.revenue_estimate?.potential_revenue?.toFixed(0)}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-gray-400">Expected</span>
                      <span className="font-medium text-green-600">
                        ${result.revenue_estimate?.expected_revenue?.toFixed(0)}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-gray-400">Waste cost</span>
                      <span className="font-medium text-red-400">
                        -${result.revenue_estimate?.waste_cost?.toFixed(0)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Event Context */}
            {result.event_context &&
              Object.values(result.event_context).some(Boolean) && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">
                  📅 Active Context Signals
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.event_context.is_public_holiday && (
                    <span className="bg-amber-100 text-amber-800 text-xs px-3 py-1 rounded-full">
                      🎉 {result.event_context.public_holiday_name}
                    </span>
                  )}
                  {result.event_context.is_school_holiday && (
                    <span className="bg-amber-100 text-amber-800 text-xs px-3 py-1 rounded-full">
                      🏫 School Holidays
                    </span>
                  )}
                  {result.event_context.is_payday_period && (
                    <span className="bg-amber-100 text-amber-800 text-xs px-3 py-1 rounded-full">
                      💰 Payday Period
                    </span>
                  )}
                  {result.event_context.is_monsoon_season && (
                    <span className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full">
                      🌧️ Monsoon Season
                    </span>
                  )}
                  {result.event_context.nearby_event_name && (
                    <span className="bg-purple-100 text-purple-800 text-xs px-3 py-1 rounded-full">
                      🎪 {result.event_context.nearby_event_name}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* 7-Day Chart */}
            <WeekForecastChart
              vendorId={selectedVendor}
              itemName={selectedItem}
            />

            {/* History */}
            <HistoryFeed vendorId={selectedVendor} />

            {/* Demo Mode Panels */}
            {demoMode && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 py-2">
                  <div className="h-px flex-1 bg-gray-200" />
                  <span className="text-xs font-semibold text-gray-400 px-3">
                    🔬 DEMO MODE — SYSTEM INTERNALS
                  </span>
                  <div className="h-px flex-1 bg-gray-200" />
                </div>
                <ConfidenceBreakdownPanel breakdown={result.confidence_breakdown} />
                <LayerTracePanel trace={result.layer_trace} />
                <ArchitectureDiagram />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}