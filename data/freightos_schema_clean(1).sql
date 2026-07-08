-- ============================================================================
-- FreightOS – PostgreSQL schema (Neon-compatible) — CLEANED
-- Run order matters: tables are created parents-first so FKs resolve.
-- Key fixes vs. original: creation order (inquiry moved before rate tables),
-- duplicate PRIMARY KEY tokens removed, DATETIME -> TIMESTAMPTZ, dual-PK on
-- fine_charge resolved, port FK columns sized to VARCHAR(10), dead indexes
-- removed, and `transit` added to all rate tables.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Core reference entities
-- ----------------------------------------------------------------------------

CREATE TABLE trade_lane (
    tr_ln_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tr_ln_name      VARCHAR(100) NOT NULL
);

CREATE TABLE liner (
    lin_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100),
    is_on_intra     BOOLEAN      DEFAULT FALSE,
    has_portal      BOOLEAN      DEFAULT FALSE
);

-- M:N — Liner "supports" Trade Lane
CREATE TABLE liner_trade_lane (
    lin_id          BIGINT NOT NULL REFERENCES liner (lin_id) ON DELETE CASCADE,
    tr_ln_id        BIGINT NOT NULL REFERENCES trade_lane (tr_ln_id) ON DELETE CASCADE,
    PRIMARY KEY (lin_id, tr_ln_id)
);

CREATE TABLE port (
    unlocode        VARCHAR(10)  PRIMARY KEY,        -- UN/LOCODE
    name            VARCHAR(100) NOT NULL,
    country         VARCHAR(60)
);

CREATE TABLE zip_code (
    zip             VARCHAR(15)  PRIMARY KEY,
    region_state    VARCHAR(80),
    tr_ln_id        BIGINT       REFERENCES trade_lane (tr_ln_id),
    port_id         VARCHAR(10)  REFERENCES port (unlocode)
);

-- PortPair: POL/POD pairing, grouped under a trade lane
CREATE TABLE port_pair (
    pol_id          VARCHAR(10) NOT NULL REFERENCES port (unlocode),   -- Port of Loading
    pod_id          VARCHAR(10) NOT NULL REFERENCES port (unlocode),   -- Port of Discharge
    tr_ln_id        BIGINT      REFERENCES trade_lane (tr_ln_id),
    is_bookable     BOOLEAN     DEFAULT TRUE,
    PRIMARY KEY (pol_id, pod_id),
    CHECK (pol_id <> pod_id)
);

-- ----------------------------------------------------------------------------
-- 2. People: employees, clients, contact persons
-- ----------------------------------------------------------------------------

CREATE TABLE employee (
    emp_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    desig           VARCHAR(80),
    dept            VARCHAR(80)
);

CREATE TABLE trade_lane_assignment (
    tr_ln_id        BIGINT NOT NULL REFERENCES trade_lane (tr_ln_id),
    emp_id_assigned BIGINT NOT NULL REFERENCES employee (emp_id),
    assigned_date   DATE   DEFAULT CURRENT_DATE,
    PRIMARY KEY (tr_ln_id, emp_id_assigned)
);

-- Team Member "requestsRates" from another Team Member
CREATE TABLE rate_request (
    request_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id_requester    BIGINT NOT NULL REFERENCES employee (emp_id),
    emp_id_requested    BIGINT NOT NULL REFERENCES employee (emp_id),
    is_given            BOOLEAN DEFAULT FALSE,
    remark              TEXT
);

-- Multivalued "Option" attribute of requestsRates (Rate, Remark)
CREATE TABLE rate_request_option (
    option_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id      BIGINT NOT NULL REFERENCES rate_request (request_id) ON DELETE CASCADE,
    rate            NUMERIC(12,2),
    remark          TEXT
);

CREATE TABLE client (
    cli_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    vat_no          VARCHAR(40),
    tin             VARCHAR(40),
    credit_limit    NUMERIC(14,2),
    kyc_completed   BOOLEAN      DEFAULT FALSE,
    -- composite "Address" attribute flattened:
    addr_street_ln  VARCHAR(150),
    addr_city       VARCHAR(80)
);

CREATE TABLE contact_person (
    cpid            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cli_id          BIGINT NOT NULL REFERENCES client (cli_id) ON DELETE CASCADE,
    emp_id          BIGINT REFERENCES employee (emp_id),        -- handling employee
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(120),
    whatsapp        VARCHAR(30),
    wechat          VARCHAR(50)
);

-- ----------------------------------------------------------------------------
-- 3. Inquiry and its dependents
--    (moved before the rate tables: contracted_rates, spot_rate, and
--     cont_rt_assignment all reference inquiry, so it must exist first)
-- ----------------------------------------------------------------------------

-- Inquiry ISA {Door-To-Door, Port-to-Port} → service_mode discriminator
CREATE TABLE inquiry (
    inq_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cpid             BIGINT REFERENCES contact_person (cpid),   -- "files"
    cli_id           BIGINT REFERENCES client (cli_id),
    emp_id           BIGINT REFERENCES employee (emp_id),       -- "Process"
    description      TEXT,
    sbu              VARCHAR(40),
    remark           TEXT,
    origin           VARCHAR(10) NOT NULL REFERENCES port (unlocode),
    incoterm         VARCHAR(50),
    cargo_ready_date DATE,
    priority         VARCHAR(20),
    preferred_liners TEXT,
    service_mode     VARCHAR(15) CHECK (service_mode IN ('DOOR_TO_DOOR', 'PORT_TO_PORT'))
);

CREATE TABLE commodity (
    com_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inq_id          BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,  -- "contain"
    name            VARCHAR(120),
    type            VARCHAR(60),
    description     TEXT,
    weight          NUMERIC(12,3),
    remark          TEXT
);

CREATE TABLE container (
    cont_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inq_id          BIGINT REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    com_id          BIGINT REFERENCES commodity (com_id),       -- "transported"
    container_type  VARCHAR(20),
    qty             INTEGER CHECK (qty IS NULL OR qty > 0),
    destination     VARCHAR(10) NOT NULL REFERENCES port (unlocode),
    zip_code        VARCHAR(15) REFERENCES zip_code (zip),
    is_fully_loaded BOOLEAN DEFAULT FALSE,
    free_time       VARCHAR(50)
);

-- Weak entity: Fine/Charge on an Inquiry (partial key char_id)
CREATE TABLE fine_charge (
    inq_id          BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    char_id         BIGINT GENERATED ALWAYS AS IDENTITY,
    name            VARCHAR(100),
    amt             NUMERIC(12,2),
    remark          TEXT,
    PRIMARY KEY (inq_id, char_id)
);

-- Surcharge "Calculated" for an Inquiry
CREATE TABLE surcharge (
    sur_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inq_id          BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    type            VARCHAR(50),
    amt             NUMERIC(12,2),
    currency        CHAR(3)
);

-- Weak entity: Special Rate that a Commodity can "get"
CREATE TABLE special_rate (
    sprid           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inq_id          BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    com_id          BIGINT NOT NULL REFERENCES commodity (com_id) ON DELETE CASCADE,
    valid_from      DATE,
    valid_to        DATE,
    rate            NUMERIC(12,2),
    transit         VARCHAR(50),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

-- ----------------------------------------------------------------------------
-- 4. Rates
-- ----------------------------------------------------------------------------

CREATE TABLE contracted_rates (
    crate_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lin_id            BIGINT NOT NULL REFERENCES liner (lin_id),
    tr_ln_id          BIGINT REFERENCES trade_lane (tr_ln_id),
    inq_id            BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    contract_ref_id   VARCHAR(50),
    valid_from        DATE,
    valid_to          DATE,
    contracted_volume INT,
    iwe               VARCHAR(30),
    container_type    VARCHAR(20),
    transit           VARCHAR(50),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE fak_rates (
    fak_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lin_id            BIGINT NOT NULL REFERENCES liner (lin_id),
    tr_ln_id          BIGINT REFERENCES trade_lane (tr_ln_id),
    valid_from        DATE,
    valid_to          DATE,
    contracted_volume INT,
    remaining_volume  INT,                       -- was "remaning_volume" (typo)
    iwe               VARCHAR(30),
    container_type    VARCHAR(20),
    transit           VARCHAR(50),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE cont_rt_assignment (
    fak_id           BIGINT NOT NULL REFERENCES fak_rates (fak_id),
    inq_id           BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    volume_allocated INT,
    PRIMARY KEY (fak_id, inq_id)
);

-- Spot Rate ISA {Vessel-by-Vessel Rate, Liner Rate}
CREATE TABLE spot_rate (
    srid                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lin_id              BIGINT NOT NULL REFERENCES liner (lin_id),
    tr_ln_id            BIGINT REFERENCES trade_lane (tr_ln_id),
    inq_id              BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    valid_from          DATE,
    valid_to            DATE,
    container_type      VARCHAR(20),
    iwe                 VARCHAR(30),
    rate                NUMERIC(12,2),
    transit             VARCHAR(50),
    is_sold             BOOLEAN DEFAULT FALSE,
    is_cancelled        BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    rate_kind           VARCHAR(20) NOT NULL DEFAULT 'LINER_RATE'
                        CHECK (rate_kind IN ('VESSEL_BY_VESSEL', 'LINER_RATE')),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

-- Subtype: Vessel-by-Vessel Rate (extra attributes; PK = FK to spot_rate)
-- transit lives on spot_rate, so the subtype inherits it via the join.
CREATE TABLE vessel_by_vessel_rate (
    srid            BIGINT PRIMARY KEY REFERENCES spot_rate (srid) ON DELETE CASCADE,
    inq_id          BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    voyage          VARCHAR(40)  NOT NULL,
    vessel_name     VARCHAR(100) NOT NULL,
    departure_date  DATE,
    eta             DATE,
    etd             DATE,
    rate            NUMERIC(12,2),
    fcl_opening     TIMESTAMPTZ,                 -- was DATETIME (not a PG type)
    fcl_cutoff      TIMESTAMPTZ                  -- was DATETIME (not a PG type)
);
-- "Liner Rate" subtype adds no attributes → represented by rate_kind = 'LINER_RATE'.

-- ----------------------------------------------------------------------------
-- 5. NAC (Named Account Contract) — weak entity of Contact Person / Client
-- ----------------------------------------------------------------------------

CREATE TABLE nac (
    nac_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cli_id          BIGINT REFERENCES client (cli_id),
    cpid            BIGINT REFERENCES contact_person (cpid),    -- Contact Person "has" NAC
    emp_id          BIGINT REFERENCES employee (emp_id),
    tr_ln_id        BIGINT REFERENCES trade_lane (tr_ln_id),
    nac_ref_id      VARCHAR(50),
    origin          VARCHAR(80),
    destination     VARCHAR(10) REFERENCES port (unlocode),
    valid_from      DATE,
    valid_to        DATE,
    rate            NUMERIC(12,2),
    transit         VARCHAR(50),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

-- Employee "Access" to NAC (M:N)
CREATE TABLE employee_nac_access (
    emp_id          BIGINT NOT NULL REFERENCES employee (emp_id) ON DELETE CASCADE,
    nac_id          BIGINT NOT NULL REFERENCES nac (nac_id) ON DELETE CASCADE,
    PRIMARY KEY (emp_id, nac_id)
);

-- ----------------------------------------------------------------------------
-- 6. Quotation
-- ----------------------------------------------------------------------------

CREATE TABLE quotation (
    quote_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inq_id              BIGINT NOT NULL REFERENCES inquiry (inq_id) ON DELETE CASCADE,
    emp_id              BIGINT REFERENCES employee (emp_id),    -- "Preps"
    status              VARCHAR(30),
    quote_date          DATE    DEFAULT CURRENT_DATE,
    is_follow_up        BOOLEAN DEFAULT FALSE,
    acceptance_deadline DATE,
    sent_via            VARCHAR(30)
);

-- Multivalued "Option" attribute of Quotation (Rate, Remark)
CREATE TABLE quotation_option (
    option_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quote_id        BIGINT NOT NULL REFERENCES quotation (quote_id) ON DELETE CASCADE,
    rate            NUMERIC(12,2),
    remark          TEXT
);

-- ----------------------------------------------------------------------------
-- 7. Indexes on frequently joined / filtered FKs
-- ----------------------------------------------------------------------------

CREATE INDEX idx_zip_code_port           ON zip_code (port_id);
CREATE INDEX idx_zip_code_tradelane      ON zip_code (tr_ln_id);
CREATE INDEX idx_port_pair_tradelane     ON port_pair (tr_ln_id);
CREATE INDEX idx_contact_person_client   ON contact_person (cli_id);
CREATE INDEX idx_contracted_rates_liner  ON contracted_rates (lin_id);
CREATE INDEX idx_contracted_rates_inq    ON contracted_rates (inq_id);
CREATE INDEX idx_fak_rates_liner         ON fak_rates (lin_id);
CREATE INDEX idx_fak_rates_tradelane     ON fak_rates (tr_ln_id);
CREATE INDEX idx_spot_rate_liner         ON spot_rate (lin_id);
CREATE INDEX idx_spot_rate_tradelane     ON spot_rate (tr_ln_id);
CREATE INDEX idx_spot_rate_inquiry       ON spot_rate (inq_id);
CREATE INDEX idx_spot_rate_validity      ON spot_rate (valid_from, valid_to);
CREATE INDEX idx_nac_client              ON nac (cli_id);
CREATE INDEX idx_inquiry_contact         ON inquiry (cpid);
CREATE INDEX idx_inquiry_client          ON inquiry (cli_id);
CREATE INDEX idx_inquiry_employee        ON inquiry (emp_id);
CREATE INDEX idx_commodity_inquiry       ON commodity (inq_id);
CREATE INDEX idx_container_inquiry       ON container (inq_id);
CREATE INDEX idx_container_commodity     ON container (com_id);
CREATE INDEX idx_surcharge_inquiry       ON surcharge (inq_id);
CREATE INDEX idx_quotation_inquiry       ON quotation (inq_id);
CREATE INDEX idx_quotation_employee      ON quotation (emp_id);

COMMIT;
