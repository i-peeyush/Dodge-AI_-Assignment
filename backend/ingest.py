import os, json, sqlite3, glob

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "sap-o2c-data")
DB_PATH  = os.path.join(os.path.dirname(__file__), "data.db")

def read_jsonl(folder):
    rows = []
    for fpath in glob.glob(os.path.join(DATA_DIR, folder, "*.jsonl")):
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows

def create_tables(cur):
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS sales_order_headers (
        salesOrder TEXT PRIMARY KEY,
        salesOrderType TEXT, salesOrganization TEXT, distributionChannel TEXT,
        organizationDivision TEXT, salesGroup TEXT, salesOffice TEXT,
        soldToParty TEXT, creationDate TEXT, createdByUser TEXT,
        lastChangeDateTime TEXT, totalNetAmount REAL, overallDeliveryStatus TEXT,
        overallOrdReltdBillgStatus TEXT, overallSdDocReferenceStatus TEXT,
        transactionCurrency TEXT, pricingDate TEXT, requestedDeliveryDate TEXT,
        headerBillingBlockReason TEXT, deliveryBlockReason TEXT,
        incotermsClassification TEXT, incotermsLocation1 TEXT,
        customerPaymentTerms TEXT, totalCreditCheckStatus TEXT
    );

    CREATE TABLE IF NOT EXISTS sales_order_items (
        salesOrder TEXT, salesOrderItem TEXT,
        salesOrderItemCategory TEXT, material TEXT,
        requestedQuantity REAL, requestedQuantityUnit TEXT,
        transactionCurrency TEXT, netAmount REAL,
        materialGroup TEXT, productionPlant TEXT,
        storageLocation TEXT, salesDocumentRjcnReason TEXT,
        itemBillingBlockReason TEXT,
        PRIMARY KEY (salesOrder, salesOrderItem)
    );

    CREATE TABLE IF NOT EXISTS billing_documents (
        billingDocument TEXT PRIMARY KEY,
        billingDocumentType TEXT, creationDate TEXT, creationTime TEXT,
        lastChangeDateTime TEXT, billingDocumentDate TEXT,
        billingDocumentIsCancelled TEXT, cancelledBillingDocument TEXT,
        totalNetAmount REAL, transactionCurrency TEXT,
        companyCode TEXT, fiscalYear TEXT,
        accountingDocument TEXT, soldToParty TEXT
    );

    CREATE TABLE IF NOT EXISTS journal_entry_items (
        accountingDocument TEXT, accountingDocumentItem TEXT,
        companyCode TEXT, fiscalYear TEXT,
        glAccount TEXT, referenceDocument TEXT,
        costCenter TEXT, profitCenter TEXT,
        transactionCurrency TEXT, amountInTransactionCurrency REAL,
        companyCodeCurrency TEXT, amountInCompanyCodeCurrency REAL,
        postingDate TEXT, documentDate TEXT,
        accountingDocumentType TEXT, assignmentReference TEXT,
        lastChangeDateTime TEXT, customer TEXT,
        financialAccountType TEXT, clearingDate TEXT,
        clearingAccountingDocument TEXT, clearingDocFiscalYear TEXT,
        PRIMARY KEY (accountingDocument, accountingDocumentItem)
    );

    CREATE TABLE IF NOT EXISTS payments (
        accountingDocument TEXT, accountingDocumentItem TEXT,
        companyCode TEXT, fiscalYear TEXT,
        clearingDate TEXT, clearingAccountingDocument TEXT,
        clearingDocFiscalYear TEXT,
        amountInTransactionCurrency REAL, transactionCurrency TEXT,
        amountInCompanyCodeCurrency REAL, companyCodeCurrency TEXT,
        customer TEXT, invoiceReference TEXT, invoiceReferenceFiscalYear TEXT,
        salesDocument TEXT, salesDocumentItem TEXT,
        postingDate TEXT, documentDate TEXT, assignmentReference TEXT,
        glAccount TEXT, financialAccountType TEXT,
        profitCenter TEXT, costCenter TEXT,
        PRIMARY KEY (accountingDocument, accountingDocumentItem)
    );

    CREATE TABLE IF NOT EXISTS delivery_headers (
        deliveryDocument TEXT PRIMARY KEY,
        actualGoodsMovementDate TEXT, actualGoodsMovementTime TEXT,
        creationDate TEXT, creationTime TEXT,
        deliveryBlockReason TEXT,
        hdrGeneralIncompletionStatus TEXT, headerBillingBlockReason TEXT,
        lastChangeDate TEXT, overallGoodsMovementStatus TEXT,
        overallPickingStatus TEXT, overallProofOfDeliveryStatus TEXT,
        shippingPoint TEXT
    );

    CREATE TABLE IF NOT EXISTS business_partners (
        businessPartner TEXT PRIMARY KEY,
        customer TEXT, businessPartnerCategory TEXT,
        businessPartnerFullName TEXT, businessPartnerGrouping TEXT,
        businessPartnerName TEXT, correspondenceLanguage TEXT,
        createdByUser TEXT, creationDate TEXT, creationTime TEXT,
        firstName TEXT, formOfAddress TEXT, industry TEXT,
        lastChangeDate TEXT, lastName TEXT,
        organizationBpName1 TEXT, organizationBpName2 TEXT,
        businessPartnerIsBlocked TEXT, isMarkedForArchiving TEXT
    );

    CREATE TABLE IF NOT EXISTS plants (
        plant TEXT PRIMARY KEY,
        plantName TEXT, valuationArea TEXT,
        plantCustomer TEXT, plantSupplier TEXT,
        factoryCalendar TEXT, defaultPurchasingOrganization TEXT,
        salesOrganization TEXT, addressId TEXT, plantCategory TEXT,
        distributionChannel TEXT, division TEXT,
        language TEXT, isMarkedForArchiving TEXT
    );

    CREATE TABLE IF NOT EXISTS product_descriptions (
        product TEXT, language TEXT, productDescription TEXT,
        PRIMARY KEY (product, language)
    );
    """)

def insert_all(cur, rows, table, columns):
    placeholders = ",".join("?" * len(columns))
    col_str = ",".join(columns)
    for row in rows:
        vals = []
        for c in columns:
            v = row.get(c)
            # SQLite can't store dicts/lists — serialize them to string
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            vals.append(v)
        cur.execute(
            f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})",
            vals
        )

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    create_tables(cur)

    # Sales order headers
    rows = read_jsonl("sales_order_headers")
    cols = ["salesOrder","salesOrderType","salesOrganization","distributionChannel",
            "organizationDivision","salesGroup","salesOffice","soldToParty",
            "creationDate","createdByUser","lastChangeDateTime","totalNetAmount",
            "overallDeliveryStatus","overallOrdReltdBillgStatus",
            "overallSdDocReferenceStatus","transactionCurrency","pricingDate",
            "requestedDeliveryDate","headerBillingBlockReason","deliveryBlockReason",
            "incotermsClassification","incotermsLocation1","customerPaymentTerms",
            "totalCreditCheckStatus"]
    insert_all(cur, rows, "sales_order_headers", cols)
    print(f"sales_order_headers: {len(rows)} rows")

    # Sales order items
    rows = read_jsonl("sales_order_items")
    cols = ["salesOrder","salesOrderItem","salesOrderItemCategory","material",
            "requestedQuantity","requestedQuantityUnit","transactionCurrency",
            "netAmount","materialGroup","productionPlant","storageLocation",
            "salesDocumentRjcnReason","itemBillingBlockReason"]
    insert_all(cur, rows, "sales_order_items", cols)
    print(f"sales_order_items: {len(rows)} rows")

    # Billing documents
    rows = read_jsonl("billing_document_cancellations")
    cols = ["billingDocument","billingDocumentType","creationDate","creationTime",
            "lastChangeDateTime","billingDocumentDate","billingDocumentIsCancelled",
            "cancelledBillingDocument","totalNetAmount","transactionCurrency",
            "companyCode","fiscalYear","accountingDocument","soldToParty"]
    insert_all(cur, rows, "billing_documents", cols)
    print(f"billing_documents: {len(rows)} rows")

    # Journal entries
    rows = read_jsonl("journal_entry_items_accounts_receivable")
    cols = ["companyCode","fiscalYear","accountingDocument","glAccount",
            "referenceDocument","costCenter","profitCenter","transactionCurrency",
            "amountInTransactionCurrency","companyCodeCurrency",
            "amountInCompanyCodeCurrency","postingDate","documentDate",
            "accountingDocumentType","accountingDocumentItem","assignmentReference",
            "lastChangeDateTime","customer","financialAccountType","clearingDate",
            "clearingAccountingDocument","clearingDocFiscalYear"]
    insert_all(cur, rows, "journal_entry_items", cols)
    print(f"journal_entry_items: {len(rows)} rows")

    # Payments
    rows = read_jsonl("payments_accounts_receivable")
    cols = ["companyCode","fiscalYear","accountingDocument","accountingDocumentItem",
            "clearingDate","clearingAccountingDocument","clearingDocFiscalYear",
            "amountInTransactionCurrency","transactionCurrency",
            "amountInCompanyCodeCurrency","companyCodeCurrency","customer",
            "invoiceReference","invoiceReferenceFiscalYear","salesDocument",
            "salesDocumentItem","postingDate","documentDate","assignmentReference",
            "glAccount","financialAccountType","profitCenter","costCenter"]
    insert_all(cur, rows, "payments", cols)
    print(f"payments: {len(rows)} rows")

    # Delivery headers
    rows = read_jsonl("outbound_delivery_headers")
    cols = ["deliveryDocument","actualGoodsMovementDate","actualGoodsMovementTime",
            "creationDate","creationTime","deliveryBlockReason",
            "hdrGeneralIncompletionStatus","headerBillingBlockReason",
            "lastChangeDate","overallGoodsMovementStatus","overallPickingStatus",
            "overallProofOfDeliveryStatus","shippingPoint"]
    insert_all(cur, rows, "delivery_headers", cols)
    print(f"delivery_headers: {len(rows)} rows")

    # Business partners
    rows = read_jsonl("business_partners")
    cols = ["businessPartner","customer","businessPartnerCategory",
            "businessPartnerFullName","businessPartnerGrouping","businessPartnerName",
            "correspondenceLanguage","createdByUser","creationDate","creationTime",
            "firstName","formOfAddress","industry","lastChangeDate","lastName",
            "organizationBpName1","organizationBpName2",
            "businessPartnerIsBlocked","isMarkedForArchiving"]
    insert_all(cur, rows, "business_partners", cols)
    print(f"business_partners: {len(rows)} rows")

    # Plants
    rows = read_jsonl("plants")
    cols = ["plant","plantName","valuationArea","plantCustomer","plantSupplier",
            "factoryCalendar","defaultPurchasingOrganization","salesOrganization",
            "addressId","plantCategory","distributionChannel","division",
            "language","isMarkedForArchiving"]
    insert_all(cur, rows, "plants", cols)
    print(f"plants: {len(rows)} rows")

    # Product descriptions
    rows = read_jsonl("product_descriptions")
    cols = ["product","language","productDescription"]
    insert_all(cur, rows, "product_descriptions", cols)
    print(f"product_descriptions: {len(rows)} rows")

    conn.commit()
    conn.close()
    print("\nDone. data.db created.")

if __name__ == "__main__":
    main()