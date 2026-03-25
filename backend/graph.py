import sqlite3
import networkx as nx
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

def build_graph():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    cur = conn.cursor()

    G = nx.DiGraph()  # directed graph — edges have direction

    # ── 1. SALES ORDER HEADERS ──────────────────────────────────────
    cur.execute("SELECT * FROM sales_order_headers")
    for row in cur.fetchall():
        G.add_node(row["salesOrder"],
            type="SalesOrder",
            label=row["salesOrder"],
            totalNetAmount=row["totalNetAmount"],
            currency=row["transactionCurrency"],
            status=row["overallDeliveryStatus"],
            billingStatus=row["overallOrdReltdBillgStatus"],
            creationDate=row["creationDate"],
            soldToParty=row["soldToParty"]
        )

    # ── 2. SALES ORDER ITEMS ────────────────────────────────────────
    cur.execute("SELECT * FROM sales_order_items")
    for row in cur.fetchall():
        node_id = f"{row['salesOrder']}-{row['salesOrderItem']}"
        G.add_node(node_id,
            type="SalesOrderItem",
            label=node_id,
            material=row["material"],
            quantity=row["requestedQuantity"],
            unit=row["requestedQuantityUnit"],
            netAmount=row["netAmount"],
            plant=row["productionPlant"]
        )
        # Edge: SalesOrder → SalesOrderItem
        if row["salesOrder"] in G:
            G.add_edge(row["salesOrder"], node_id,
                relation="HAS_ITEM")

    # ── 3. BILLING DOCUMENTS ────────────────────────────────────────
    cur.execute("SELECT * FROM billing_documents")
    for row in cur.fetchall():
        G.add_node(row["billingDocument"],
            type="BillingDocument",
            label=row["billingDocument"],
            totalNetAmount=row["totalNetAmount"],
            currency=row["transactionCurrency"],
            isCancelled=row["billingDocumentIsCancelled"],
            creationDate=row["creationDate"],
            accountingDocument=row["accountingDocument"],
            soldToParty=row["soldToParty"]
        )
        # Edge: Customer → BillingDocument
        if row["soldToParty"] and row["soldToParty"] in G:
            G.add_edge(row["soldToParty"], row["billingDocument"],
                relation="HAS_BILLING")

    # ── 4. JOURNAL ENTRY ITEMS ──────────────────────────────────────
    cur.execute("SELECT * FROM journal_entry_items")
    for row in cur.fetchall():
        node_id = f"JE-{row['accountingDocument']}-{row['accountingDocumentItem']}"
        G.add_node(node_id,
            type="JournalEntry",
            label=node_id,
            accountingDocument=row["accountingDocument"],
            amount=row["amountInCompanyCodeCurrency"],
            currency=row["companyCodeCurrency"],
            postingDate=row["postingDate"],
            glAccount=row["glAccount"],
            referenceDocument=row["referenceDocument"]
        )
        # Edge: BillingDocument → JournalEntry (via accountingDocument)
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT billingDocument FROM billing_documents WHERE accountingDocument=?",
            (row["accountingDocument"],)
        )
        bd = cur2.fetchone()
        if bd:
            G.add_edge(bd["billingDocument"], node_id,
                relation="HAS_JOURNAL_ENTRY")

    # ── 5. PAYMENTS ─────────────────────────────────────────────────
    cur.execute("SELECT * FROM payments")
    for row in cur.fetchall():
        node_id = f"PAY-{row['accountingDocument']}-{row['accountingDocumentItem']}"
        G.add_node(node_id,
            type="Payment",
            label=node_id,
            amount=row["amountInCompanyCodeCurrency"],
            currency=row["companyCodeCurrency"],
            clearingDate=row["clearingDate"],
            invoiceReference=row["invoiceReference"],
            salesDocument=row["salesDocument"]
        )
        # Edge: BillingDocument → Payment (via invoiceReference)
        if row["invoiceReference"] and row["invoiceReference"] in G:
            G.add_edge(row["invoiceReference"], node_id,
                relation="PAID_BY")

    # ── 6. CUSTOMERS (Business Partners) ────────────────────────────
    cur.execute("SELECT * FROM business_partners")
    for row in cur.fetchall():
        cust_id = row["customer"]
        if cust_id:
            G.add_node(cust_id,
                type="Customer",
                label=row["businessPartnerFullName"] or cust_id,
                fullName=row["businessPartnerFullName"],
                industry=row["industry"],
                country=row["correspondenceLanguage"]
            )
            # Edge: Customer → SalesOrder
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT salesOrder FROM sales_order_headers WHERE soldToParty=?",
                (cust_id,)
            )
            for so in cur2.fetchall():
                if so["salesOrder"] in G:
                    G.add_edge(cust_id, so["salesOrder"],
                        relation="PLACED_ORDER")

    # ── 7. PRODUCTS ─────────────────────────────────────────────────
    cur.execute("SELECT * FROM product_descriptions WHERE language='EN'")
    for row in cur.fetchall():
        G.add_node(row["product"],
            type="Product",
            label=row["productDescription"] or row["product"],
            productId=row["product"]
        )
        # Edge: SalesOrderItem → Product
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT salesOrder, salesOrderItem FROM sales_order_items WHERE material=?",
            (row["product"],)
        )
        for item in cur2.fetchall():
            item_id = f"{item['salesOrder']}-{item['salesOrderItem']}"
            if item_id in G:
                G.add_edge(item_id, row["product"],
                    relation="IS_PRODUCT")

    # ── 8. PLANTS ───────────────────────────────────────────────────
    cur.execute("SELECT * FROM plants")
    for row in cur.fetchall():
        G.add_node(row["plant"],
            type="Plant",
            label=row["plantName"] or row["plant"],
            plantId=row["plant"],
            salesOrganization=row["salesOrganization"]
        )
        # Edge: SalesOrderItem → Plant
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT salesOrder, salesOrderItem FROM sales_order_items WHERE productionPlant=?",
            (row["plant"],)
        )
        for item in cur2.fetchall():
            item_id = f"{item['salesOrder']}-{item['salesOrderItem']}"
            if item_id in G:
                G.add_edge(item_id, row["plant"],
                    relation="FULFILLED_BY")

    conn.close()
    return G


def graph_to_json(G):
    """Convert NetworkX graph to Cytoscape-compatible JSON format."""
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "data": {
                "id": str(node_id),
                "label": str(data.get("label", node_id)),
                "type": data.get("type", "Unknown"),
                **{k: str(v) if v is not None else "" 
                   for k, v in data.items() 
                   if k not in ("label", "type")}
            }
        })

    edges = []
    for src, tgt, data in G.edges(data=True):
        edges.append({
            "data": {
                "source": str(src),
                "target": str(tgt),
                "relation": data.get("relation", "RELATED_TO")
            }
        })

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    G = build_graph()
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")

    # Print node type breakdown
    from collections import Counter
    types = Counter(data["type"] for _, data in G.nodes(data=True))
    for t, count in types.items():
        print(f"  {t}: {count}")