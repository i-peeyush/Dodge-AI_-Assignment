import { useState, useRef, useEffect } from "react"

export default function ChatPanel({ onHighlight }) {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi! I can help you analyze the Order to Cash process. Ask me anything about orders, billing, payments, or deliveries." }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput("")
    setMessages(m => [...m, { role: "user", text: question }])
    setLoading(true)

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      })
      const data = await res.json()
      setMessages(m => [...m, {
        role: "assistant",
        text: data.answer,
        sql: data.sql,
        results: data.results
      }])
      if (data.highlighted_nodes?.length > 0) {
        onHighlight(data.highlighted_nodes)
      }
    } catch {
      setMessages(m => [...m, { role: "assistant", text: "Error connecting to backend." }])
    }
    setLoading(false)
  }

  return (
    <>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid #e0e0e0" }}>
        <div style={{ fontWeight: 600, fontSize: 14 }}>Chat with Graph</div>
        <div style={{ fontSize: 12, color: "#999" }}>Order to Cash</div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: "flex", gap: 10, flexDirection: m.role === "user" ? "row-reverse" : "row" }}>
            {m.role === "assistant" && (
              <div style={{
                width: 32, height: 32, borderRadius: "50%", background: "#1a1a1a",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", fontSize: 12, fontWeight: 700, flexShrink: 0
              }}>D</div>
            )}
            <div style={{ maxWidth: "80%" }}>
              {m.role === "assistant" && (
                <div style={{ fontSize: 11, color: "#999", marginBottom: 4 }}>
                  Dodge AI <span style={{ color: "#bbb" }}>· Graph Agent</span>
                </div>
              )}
              <div style={{
                background: m.role === "user" ? "#1a1a1a" : "#f8fafc",
                color: m.role === "user" ? "#fff" : "#1e293b",
                padding: "10px 14px", borderRadius: 10, fontSize: 13, lineHeight: 1.6,
                border: m.role === "assistant" ? "1px solid #e2e8f0" : "none"
              }}>
                {m.text}
              </div>
              {/* Show SQL if available */}
              {m.sql && !m.sql.includes("NOT_APPLICABLE") && (
                <details style={{ marginTop: 6 }}>
                  <summary style={{ fontSize: 11, color: "#94a3b8", cursor: "pointer" }}>View SQL</summary>
                  <pre style={{
                    fontSize: 11, background: "#f1f5f9", padding: 8,
                    borderRadius: 6, marginTop: 4, overflow: "auto",
                    color: "#334155", border: "1px solid #e2e8f0"
                  }}>{m.sql}</pre>
                </details>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", background: "#1a1a1a",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 12, fontWeight: 700
            }}>D</div>
            <div style={{
              background: "#f8fafc", border: "1px solid #e2e8f0",
              padding: "10px 14px", borderRadius: 10, fontSize: 13, color: "#94a3b8"
            }}>Thinking...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: 12, borderTop: "1px solid #e0e0e0" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          background: "#f8fafc", border: "1px solid #e2e8f0",
          borderRadius: 8, padding: "8px 12px"
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Analyze anything"
            style={{
              flex: 1, border: "none", background: "transparent",
              outline: "none", fontSize: 13, color: "#1e293b"
            }}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? "#e2e8f0" : "#1a1a1a",
              color: loading || !input.trim() ? "#94a3b8" : "#fff",
              border: "none", borderRadius: 6, padding: "6px 14px",
              fontSize: 12, cursor: "pointer", fontWeight: 500
            }}
          >Send</button>
        </div>
      </div>
    </>
  )
}