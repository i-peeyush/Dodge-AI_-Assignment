import { useEffect, useRef } from "react"
import cytoscape from "cytoscape"

const NODE_COLORS = {
  SalesOrder:     { bg: "#dbeafe", border: "#3b82f6", text: "#1e40af" },
  SalesOrderItem: { bg: "#e0f2fe", border: "#0284c7", text: "#075985" },
  BillingDocument:{ bg: "#fef9c3", border: "#ca8a04", text: "#854d0e" },
  JournalEntry:   { bg: "#dcfce7", border: "#16a34a", text: "#166534" },
  Payment:        { bg: "#f3e8ff", border: "#9333ea", text: "#581c87" },
  Customer:       { bg: "#fee2e2", border: "#dc2626", text: "#991b1b" },
  Product:        { bg: "#fff7ed", border: "#ea580c", text: "#9a3412" },
  Plant:          { bg: "#f1f5f9", border: "#64748b", text: "#334155" },
}

export default function GraphView({ graphData, highlightedNodes }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !graphData.nodes.length) return

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [...graphData.nodes, ...graphData.edges],
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele) => NODE_COLORS[ele.data("type")]?.bg || "#e2e8f0",
            "border-color":     (ele) => NODE_COLORS[ele.data("type")]?.border || "#94a3b8",
            "border-width": 1.5,
            "label": "data(label)",
            "font-size": 9,
            "color": (ele) => NODE_COLORS[ele.data("type")]?.text || "#334155",
            "text-valign": "center",
            "text-halign": "center",
            "width": (ele) => {
              const t = ele.data("type")
              if (t === "Customer") return 40
              if (t === "Plant" || t === "Product") return 28
              return 22
            },
            "height": (ele) => {
              const t = ele.data("type")
              if (t === "Customer") return 40
              if (t === "Plant" || t === "Product") return 28
              return 22
            },
            "shape": (ele) => {
              const t = ele.data("type")
              if (t === "Customer") return "ellipse"
              if (t === "Plant") return "diamond"
              return "ellipse"
            },
            "text-wrap": "ellipsis",
            "text-max-width": 60,
          }
        },
        {
          selector: "edge",
          style: {
            "line-color": "#cbd5e1",
            "target-arrow-color": "#cbd5e1",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "width": 1,
            "opacity": 0.6,
          }
        },
        {
          selector: ".highlighted",
          style: {
            "background-color": "#fbbf24",
            "border-color": "#f59e0b",
            "border-width": 3,
            "width": 40,
            "height": 40,
            "z-index": 999,
          }
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#6366f1",
            "border-width": 3,
          }
        }
      ],
      layout: {
        name: "cose",
        animate: false,
        nodeRepulsion: 4500000,
        idealEdgeLength: 100,
        nodeOverlap: 20,
        gravity: 0.1,
        numIter: 2000,
        initialTemp: 1000,
        coolingFactor: 0.99,
        minTemp: 1.0
        },
      wheelSensitivity: 0.3,
    })

    // Click node → show tooltip
    cyRef.current.on("tap", "node", (evt) => {
      const node = evt.target
      const data = node.data()
      const existing = document.getElementById("cy-tooltip")
      if (existing) existing.remove()

      const tooltip = document.createElement("div")
      tooltip.id = "cy-tooltip"
      tooltip.style.cssText = `
        position:fixed; background:#fff; border:1px solid #e0e0e0;
        border-radius:8px; padding:14px; max-width:280px;
        box-shadow:0 4px 20px rgba(0,0,0,0.12); z-index:9999;
        font-size:12px; font-family:sans-serif; line-height:1.6;
      `
      const pos = evt.renderedPosition
      const container = containerRef.current.getBoundingClientRect()
      tooltip.style.left = (container.left + pos.x + 10) + "px"
      tooltip.style.top  = (container.top  + pos.y + 10) + "px"

      const skip = ["id", "label"]
      let html = `<div style="font-weight:600;font-size:13px;margin-bottom:8px;color:#1e293b">${data.type}</div>`
      Object.entries(data).forEach(([k, v]) => {
        if (!skip.includes(k) && v) {
          html += `<div><span style="color:#64748b">${k}:</span> <span style="color:#1e293b">${v}</span></div>`
        }
      })

      // Connection count
      const degree = node.connectedEdges().length
      html += `<div style="margin-top:8px;color:#94a3b8;font-style:italic">Connections: ${degree}</div>`

      tooltip.innerHTML = html
      document.body.appendChild(tooltip)
    })

    // Click background → remove tooltip
    cyRef.current.on("tap", (evt) => {
      if (evt.target === cyRef.current) {
        const t = document.getElementById("cy-tooltip")
        if (t) t.remove()
      }
    })

    return () => {
      cyRef.current?.destroy()
      const t = document.getElementById("cy-tooltip")
      if (t) t.remove()
    }
  }, [graphData])

  // Highlight nodes from LLM response
  useEffect(() => {
    if (!cyRef.current) return
    cyRef.current.nodes().removeClass("highlighted")
    if (highlightedNodes.length > 0) {
      highlightedNodes.forEach(id => {
        cyRef.current.$(`#${id}`).addClass("highlighted")
      })
      // Pan to first highlighted node
      const first = cyRef.current.$(`#${highlightedNodes[0]}`)
      if (first.length) cyRef.current.animate({ center: { eles: first }, zoom: 1.5 }, { duration: 500 })
    }
  }, [highlightedNodes])

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
}