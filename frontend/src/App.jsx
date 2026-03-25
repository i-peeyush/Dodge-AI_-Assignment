import { useState, useEffect } from "react"
import GraphView from "./GraphView"
import ChatPanel from "./ChatPanel"

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [highlightedNodes, setHighlightedNodes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("https://dodge-ai-assignment-production.up.railway.app/graph")
      .then(r => r.json())
      .then(data => {
        setGraphData(data)
        setLoading(false)
      })
  }, [])

  return (
    <div style={{ display: "flex", height: "100vh", background: "#f5f5f5", fontFamily: "sans-serif" }}>
      {/* Header */}
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, height: 48,
        background: "#fff", borderBottom: "1px solid #e0e0e0",
        display: "flex", alignItems: "center", padding: "0 20px",
        zIndex: 100, gap: 8
      }}>
        <span style={{ color: "#999", fontSize: 14 }}>Mapping /</span>
        <span style={{ fontWeight: 600, fontSize: 14 }}>Order to Cash</span>
      </div>

      {/* Graph area */}
      <div style={{ flex: 1, marginTop: 48 }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#999" }}>
            Loading graph...
          </div>
        ) : (
          <GraphView graphData={graphData} highlightedNodes={highlightedNodes} />
        )}
      </div>

      {/* Chat sidebar */}
      <div style={{
        width: 360, marginTop: 48, background: "#fff",
        borderLeft: "1px solid #e0e0e0", display: "flex", flexDirection: "column"
      }}>
        <ChatPanel onHighlight={setHighlightedNodes} />
      </div>
    </div>
  )
}