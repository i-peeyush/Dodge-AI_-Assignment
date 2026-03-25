import sqlite3
import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from graph import build_graph, graph_to_json

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print("Building graph...")
G = build_graph()
GRAPH_JSON = graph_to_json(G)
print(f"Graph ready: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


# ── SCHEMA (fed to LLM) ──────────────────────────────────────────────────────
DB_SCHEMA = """
Tables in the SAP Order-to-Cash SQLite database:

1. sales_order_headers(salesOrder PK, salesOrderType, salesOrganization,
   distributionChannel, soldToParty, creationDate, totalNetAmount,
   overallDeliveryStatus, overallOrdReltdBillgStatus, transactionCurrency,
   requestedDeliveryDate, customerPaymentTerms)

2. sales_order_items(salesOrder, salesOrderItem, material, requestedQuantity,
   requestedQuantityUnit, netAmount, materialGroup, productionPlant,
   storageLocation)

3. billing_documents(billingDocument PK, billingDocumentType, creationDate,
   billingDocumentDate, billingDocumentIsCancelled, cancelledBillingDocument,
   totalNetAmount, transactionCurrency, companyCode, fiscalYear,
   accountingDocument, soldToParty)

4. journal_entry_items(accountingDocument, accountingDocumentItem,
   companyCode, fiscalYear, glAccount, referenceDocument,
   amountInTransactionCurrency, amountInCompanyCodeCurrency,
   transactionCurrency, postingDate, documentDate, accountingDocumentType,
   customer, clearingDate, clearingAccountingDocument)

5. payments(accountingDocument, accountingDocumentItem, clearingDate,
   clearingAccountingDocument, amountInTransactionCurrency,
   amountInCompanyCodeCurrency, transactionCurrency, customer,
   invoiceReference, salesDocument, salesDocumentItem, postingDate)

6. delivery_headers(deliveryDocument PK, actualGoodsMovementDate,
   creationDate, deliveryBlockReason, overallGoodsMovementStatus,
   overallPickingStatus, shippingPoint)

7. business_partners(businessPartner PK, customer, businessPartnerFullName,
   businessPartnerName, industry, businessPartnerIsBlocked)

8. plants(plant PK, plantName, valuationArea, salesOrganization,
   distributionChannel, division)

9. product_descriptions(product, language, productDescription)

Key relationships:
- sales_order_items.salesOrder → sales_order_headers.salesOrder
- sales_order_headers.soldToParty → business_partners.customer
- billing_documents.soldToParty → business_partners.customer
- billing_documents.accountingDocument → journal_entry_items.accountingDocument
- payments.invoiceReference → billing_documents.billingDocument
- payments.salesDocument → sales_order_headers.salesOrder
- sales_order_items.material → product_descriptions.product
- sales_order_items.productionPlant → plants.plant
"""

# ── GUARDRAIL ────────────────────────────────────────────────────────────────
DOMAIN_KEYWORDS = [
    "order", "sales", "billing", "invoice", "payment", "delivery",
    "customer", "product", "journal", "plant", "material", "document",
    "amount", "status", "account", "flow", "trace", "shipment", "stock",
    "partner", "fiscal", "currency", "quantity", "item", "entry"
]

def is_domain_relevant(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in DOMAIN_KEYWORDS)


# ── ENDPOINTS ────────────────────────────────────────────────────────────────
@app.get("/graph")
def get_graph():
    return GRAPH_JSON


@app.get("/schema")
def get_schema():
    return {"schema": DB_SCHEMA}


class QueryRequest(BaseModel):
    question: str


@app.post("/query")
def query(req: QueryRequest):
    question = req.question.strip()

    # Step 1: Guardrail check
    if not is_domain_relevant(question):
        return {
            "answer": "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. Please ask about orders, billing, payments, deliveries, or related topics.",
            "sql": None,
            "results": None,
            "highlighted_nodes": []
        }

    # Step 2: Generate SQL using Gemini
    sql_prompt = f"""You are a SQL expert working with a SAP Order-to-Cash database.
Given this schema:
{DB_SCHEMA}

Generate a single valid SQLite SQL query to answer this question:
"{question}"

Rules:
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
- Use only tables and columns defined in the schema above
- If the question cannot be answered from this schema, return: SELECT 'NOT_APPLICABLE'
"""

    try:
        sql_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": sql_prompt}],
            temperature=0
        )
        sql = sql_response.choices[0].message.content.strip()
        sql = re.sub(r"```sql|```", "", sql).strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    # Step 3: Execute SQL
    results = []
    columns = []
    if "NOT_APPLICABLE" not in sql:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
            results = [dict(row) for row in rows]
            conn.close()
        except Exception as e:
            results = []
            sql = f"-- Error executing SQL: {str(e)}\n{sql}"

    # Step 4: Format natural language answer
    answer_prompt = f"""You are an analyst for an SAP Order-to-Cash system.
The user asked: "{question}"

The SQL query run was:
{sql}

The results were:
{json.dumps(results[:50], indent=2)}

Write a clear, concise answer in 2-4 sentences based strictly on the data above.
Do not make up information not present in the results.
If results are empty, say no matching data was found.
"""

    try:
        answer_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": answer_prompt}],
            temperature=0
        )
        answer = answer_response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Query executed successfully but could not format response: {str(e)}"

    # Step 5: Extract node IDs to highlight in the graph
    highlighted = []
    for row in results[:20]:
        for val in row.values():
            if val and str(val) in G.nodes:
                highlighted.append(str(val))

    return {
        "answer": answer,
        "sql": sql,
        "results": results[:50],
        "highlighted_nodes": list(set(highlighted))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)