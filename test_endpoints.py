import requests
import json

BASE = "http://localhost:8000"

# -- helpers -------------------------------------------------------------------

def pr(label, r):
    print(f"\n{'-'*64}")
    print(f"  {label}")
    print(f"  {r.request.method} {r.url}  ->  {r.status_code}")
    try:
        print(f"  {json.dumps(r.json(), indent=2, default=str)}")
    except Exception:
        print(f"  {r.text}")

def safe_id(response, key, fallback=1):
    try:
        return response.json()[key]
    except Exception:
        return fallback

def safe_list_id(response, key, fallback=1):
    try:
        ids = response.json()[key]
        return ids[0] if ids else fallback
    except Exception:
        return fallback

# -- root ----------------------------------------------------------------------

pr("GET /", requests.get(f"{BASE}/"))

# -- clients -------------------------------------------------------------------

r_client = requests.post(f"{BASE}/clients/clients", json={
    "emp_id": 1,
    "name": "Acme Corp",
    "vat_no": "VAT-001",
    "tin": "TIN-001",
    "kyc_completed": False,
    "addr_street_ln": "1 Test Street",
    "addr_city": "Shanghai",
    "primary_contact": {
        "name": "Alice Wong",
        "emp_id": 1,
        "email": "alice@acme.com",
        "whatsapp": "+8612345678",
        "wechat": None
    }
})
pr("POST /clients/clients", r_client)
cli_id = safe_id(r_client, "cli_id")
cpid   = safe_id(r_client, "cpid")

r = requests.patch(f"{BASE}/clients/clients/{cli_id}", json={
    "updated_by": 1,
    "name": "Acme Corp Ltd",
    "addr_street_ln": "2 Updated Road",
    "addr_city": "Beijing"
})
pr(f"PATCH /clients/clients/{cli_id}", r)

r = requests.patch(f"{BASE}/clients/clients/{cli_id}/contacts/{cpid}", json={
    "updated_by": 1,
    "name": "Alice Chan",
    "email": "alice.chan@acme.com"
})
pr(f"PATCH /clients/clients/{cli_id}/contacts/{cpid}", r)

# -- inquiries -----------------------------------------------------------------

r_inq1 = requests.post(f"{BASE}/inquiries/inquiries-new-new", json={
    "client":  {"name": "New Corp", "kyc_completed": False},
    "contact": {"name": "Bob Lee", "emp_id": 1, "email": "bob@newcorp.com"},
    "inquiry": {"emp_id": 1, "origin": "CNSHA", "sbu": "FCL", "incoterm": "FOB"},
    "commodities": [
        {"name": "Electronics", "com_type": "General", "description": "Consumer electronics"}
    ],
    "containers": [
        {"commodity_index": 0, "container_type": "20GP", "qty": 2,
         "destination": "SGSIN", "address": "SGSIN", "is_fully_loaded": False}
    ]
})
pr("POST /inquiries/inquiries-new-new", r_inq1)
inq_id  = safe_id(r_inq1, "inq_id")
com_id  = safe_list_id(r_inq1, "com_ids")
cont_id = safe_list_id(r_inq1, "cont_ids")

r_inq2 = requests.post(f"{BASE}/inquiries/inquiries-old-new", json={
    "cli_id":  cli_id,
    "contact": {"name": "Carol Tan", "emp_id": 1},
    "inquiry": {"emp_id": 1, "origin": "CNSHA", "sbu": "LCL"},
    "commodities": [],
    "containers": []
})
pr("POST /inquiries/inquiries-old-new", r_inq2)

r_inq3 = requests.post(f"{BASE}/inquiries/inquiries-old-old", json={
    "cli_id": cli_id,
    "cp_id":  cpid,
    "inquiry": {"emp_id": 1, "origin": "CNSHA", "service_mode": "PORT_TO_PORT"},
    "commodities": [],
    "containers": []
})
pr("POST /inquiries/inquiries-old-old", r_inq3)

r = requests.patch(f"{BASE}/inquiries/inquiries/{inq_id}", json={
    "updated_by": 1,
    "priority": "HIGH"
})
pr(f"PATCH /inquiries/inquiries/{inq_id}", r)

r = requests.patch(f"{BASE}/inquiries/inquiries/{inq_id}/commodities/{com_id}", json={
    "com_type": "Hazardous",
    "description": "Updated - lithium batteries",
    "weight": 500.0
})
pr(f"PATCH /inquiries/inquiries/{inq_id}/commodities/{com_id}", r)

r = requests.patch(f"{BASE}/inquiries/inquiries/{inq_id}/containers/{cont_id}", json={
    "container_type": "40HC",
    "qty": 4,
    "is_fully_loaded": True
})
pr(f"PATCH /inquiries/inquiries/{inq_id}/containers/{cont_id}", r)

# -- rates – tariff ------------------------------------------------------------

r_tar = requests.post(f"{BASE}/rates/tariff-rates", json={
    "lin_id": 1,
    "tr_ln_id": 1,
    "updated_by": 1,
    "salesperson": 1,
    "origin": "LKCMB",
    "destination": "SGSIN",
    "valid_from": "2025-01-01",
    "valid_to": "2025-12-31",
    "max_weight": 28000,
    "container_type": "20GP",
    "rate": 1250.00,
    "currency": "USD",
    "transit": "14 days"
})
pr("POST /rates/tariff-rates", r_tar)
tar_id = safe_id(r_tar, "tar_id")

r = requests.patch(f"{BASE}/rates/tariff-rates/{tar_id}", json={
    "updated_by": 1,
    "rate": 1350.00,
    "transit": "12 days"
})
pr(f"PATCH /rates/tariff-rates/{tar_id}", r)

# -- rates – NAC ---------------------------------------------------------------

r_nac = requests.post(f"{BASE}/rates/nac-rates", json={
    "cli_id": cli_id,
    "emp_id": 1,
    "lin_id": 1,
    "tr_ln_id": 1,
    "nac_ref_id": "NAC-2025-001",
    "origin": "CNSHA",
    "destination": "SGSIN",
    "valid_from": "2025-01-01",
    "valid_to": "2025-06-30",
    "container_type": "40HC",
    "rate": 2100.00,
    "currency": "USD",
    "contracted_volume": 50,
    "updated_by": 1
})
pr("POST /rates/nac-rates", r_nac)
nac_id = safe_id(r_nac, "nac_id")

r = requests.patch(f"{BASE}/rates/nac-rates/{nac_id}", json={
    "updated_by": 1,
    "rate": 1950.00,
    "contracted_volume": 60
})
pr(f"PATCH /rates/nac-rates/{nac_id}", r)

# -- rates – contracted --------------------------------------------------------

r_con = requests.post(f"{BASE}/rates/contracted-rates", json={
    "lin_id": 1,
    "tr_ln_id": 1,
    "inq_id": inq_id,
    "contract_ref_id": "CTR-2025-001",
    "valid_from": "2025-01-01",
    "valid_to": "2025-12-31",
    "contracted_volume": 100,
    "container_type": "40GP",
    "updated_by": 1,
    "origin": "LKCMB",
    "destination": "SGSIN",
    "rate": 1800.00,
    "currency": "USD",
    "emp_id_sales": 1,
    "emp_id_cs": 1,
    "client_ids": [cli_id]
})
pr("POST /rates/contracted-rates", r_con)
crate_id = safe_id(r_con, "crate_id")

r = requests.patch(f"{BASE}/rates/contracted-rates/{crate_id}", json={
    "container_type": "40GP",
    "updated_by": 1,
    "rate": 1700.00,
    "client_ids": [cli_id]
})
pr(f"PATCH /rates/contracted-rates/{crate_id}", r)

# -- rates – vessel ------------------------------------------------------------

r_ves = requests.post(f"{BASE}/rates/vessel-rates", json={
    "inq_id": inq_id,
    "voyage": "VOY-001W",
    "vessel_name": "MSC OSCAR",
    "eta": "2025-03-15",
    "etd": "2025-02-28",
    "rate": 950.00,
    "currency": "USD",
    "fcl_opening": "2025-02-20T00:00:00",
    "fcl_cutoff": "2025-02-26T12:00:00",
    "origin": "LKCMB",
    "destination": "SGSIN",
    "tr_ln_id": 1,
    "emp_id": 1,
    "container_type": "20GP",
    "volume": 5,
    "updated_by": 1
})
pr("POST /rates/vessel-rates", r_ves)
ves_srid = safe_id(r_ves, "sr_id")

r = requests.patch(f"{BASE}/rates/vessel-rates/{ves_srid}", json={
    "inq_id": inq_id,
    "container_type": "20GP",
    "rate": 1000.00,
    "updated_by": 1
})
pr(f"PATCH /rates/vessel-rates/{ves_srid}", r)

r = requests.delete(f"{BASE}/rates/vessel-rates/{ves_srid}")
pr(f"DELETE /rates/vessel-rates/{ves_srid}", r)

# -- rates – FAK ---------------------------------------------------------------

r_fak = requests.post(f"{BASE}/rates/fak-rates", json={
    "lin_id": 1,
    "tr_ln_id": 1,
    "inq_id": inq_id,
    "emp_id": 1,
    "valid_from": "2025-01-01T00:00:00",
    "valid_to": "2025-06-30T23:59:59",
    "volume": 10,
    "container_type": "40GP",
    "origin": "LKCMB",
    "destination": "SGSIN",
    "rate": 800.00,
    "currency": "USD"
})
pr("POST /rates/fak-rates", r_fak)
fak_srid = safe_id(r_fak, "fak_id")

r = requests.patch(f"{BASE}/rates/fak-rates/{fak_srid}", json={
    "updated_by": 1,
    "rate": 850.00,
    "volume": 12
})
pr(f"PATCH /rates/fak-rates/{fak_srid}", r)

r = requests.delete(f"{BASE}/rates/fak-rates/{fak_srid}")
pr(f"DELETE /rates/fak-rates/{fak_srid}", r)

# -- rates – special -----------------------------------------------------------

r_spc = requests.post(f"{BASE}/rates/special-rates", json={
    "lin_id": 1,
    "tr_ln_id": 1,
    "inq_id": inq_id,
    "emp_id": 1,
    "com_id": com_id,
    "valid_from": "2025-01-01T00:00:00",
    "valid_to": "2025-06-30T23:59:59",
    "rate": 1100.00,
    "origin": "LKCMB",
    "destination": "SGSIN",
    "container_type": "20GP",
    "volume": 3,
    "currency": "USD"
})
pr("POST /rates/special-rates", r_spc)
spc_sprid = safe_id(r_spc, "sprid")

r = requests.patch(f"{BASE}/rates/special-rates/{spc_sprid}", json={
    "updated_by": 1,
    "rate": 1050.00
})
pr(f"PATCH /rates/special-rates/{spc_sprid}", r)

r = requests.delete(f"{BASE}/rates/special-rates/{spc_sprid}")
pr(f"DELETE /rates/special-rates/{spc_sprid}", r)

# -- rate requests -------------------------------------------------------------

r_rr = requests.post(f"{BASE}/rate-requests", json={
    "emp_id_requester": 1,
    "emp_id_requested": 2,
    "is_given": False,
    "remark": "Please provide a competitive rate for CNSHA-USLAX"
})
pr("POST /rate-requests", r_rr)
request_id = safe_id(r_rr, "request_id")

r_opt = requests.post(f"{BASE}/rate-requests/{request_id}/options", json={
    "request_id": request_id,
    "updated_by": 1,
    "rate_type": "tariff",
    "rate_id": tar_id
})
pr(f"POST /rate-requests/{request_id}/options", r_opt)
option_id = safe_id(r_opt, "option_id")

r = requests.patch(f"{BASE}/rate-requests/{request_id}/options/{option_id}", json={
    "updated_by": 1,
    "rate_type": "nac",
    "rate_id": nac_id
})
pr(f"PATCH /rate-requests/{request_id}/options/{option_id}", r)

r = requests.delete(f"{BASE}/rate-requests/{request_id}/options/{option_id}")
pr(f"DELETE /rate-requests/{request_id}/options/{option_id}", r)

r = requests.delete(f"{BASE}/rate-requests/{request_id}")
pr(f"DELETE /rate-requests/{request_id}", r)

# -- KYC ----------------------------------------------------------------------

r_kyc = requests.post(f"{BASE}/kyc/kyc-requests", json={
    "cli_id": cli_id,
    "br_number": "BR-2025-001",
    "parent_organization": "Acme Holdings",
    "emp_id": 1,
    "emp_id_sales": 1,
    "document_submission_deadline": "2025-06-30",
    "cli_type": "shipper",
    "currency": "USD",
    "website": "https://acme.com",
    "tax_exemptions": "none",
    "sea_imports": True,
    "sea_exports": True,
    "general_cargo": True,
    "contact_person": {
        "name": "Alice Wong",
        "emp_id": 1,
        "email": "alice@acme.com"
    },
    "docs": {
        "cli_id": cli_id,
        "br_form": "br_form_001.pdf",
        "vat_certificate": "vat_cert_001.pdf"
    }
})
pr("POST /kyc/kyc-requests", r_kyc)
kyc_id = safe_id(r_kyc, "kyc_id", 1)
doc_id = safe_id(r_kyc, "doc_id", 1)

r = requests.patch(f"{BASE}/kyc/kyc-requests/{kyc_id}", json={
    "updated_by": 1,
    "document_submission_deadline": "2025-07-31",
    "currency": "LKR",
    "dangerous_goods": True
})
pr(f"PATCH /kyc/kyc-requests/{kyc_id}", r)

r = requests.patch(f"{BASE}/kyc/kyc-requests/{kyc_id}/documents/{doc_id}", json={
    "tin_certificate": "tin_cert_001.pdf",
    "form20": "form20_001.pdf"
})
pr(f"PATCH /kyc/kyc-requests/{kyc_id}/documents/{doc_id}", r)

print(f"\n{'-'*64}")
print("  Done.")
print(f"{'-'*64}\n")
