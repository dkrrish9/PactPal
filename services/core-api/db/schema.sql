-- ============================================================================
-- PactPal: Zero-Trust Multimodal Escrow Referee for Digital Freelancing
-- Draft Relational Database Schema (PostgreSQL)
-- Milestone 0 Foundation: Task C06 / A1 Data Planning
-- ============================================================================

-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. ENUM TYPES
-- ============================================================================

CREATE TYPE user_role AS ENUM (
    'BUYER',
    'SELLER',
    'ADMIN'
);

-- Master 10-State Contract Lifecycle
CREATE TYPE contract_state AS ENUM (
    'DRAFT',
    'REVIEW',
    'SIGNED',
    'FUNDED',
    'IN_PROGRESS',
    'SUBMITTED',
    'VERIFYING',
    'DECISION',
    'SETTLED',
    'DISPUTE'
);

CREATE TYPE feature_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED',
    'DISPUTED'
);

CREATE TYPE change_request_status AS ENUM (
    'PROPOSED',
    'ACCEPTED',
    'REJECTED',
    'COUNTERED'
);

CREATE TYPE payment_type AS ENUM (
    'AUTHORIZATION',
    'CAPTURE',
    'PAYOUT',
    'REFUND',
    'VOID'
);

CREATE TYPE payment_status AS ENUM (
    'PENDING',
    'COMPLETED',
    'FAILED'
);

CREATE TYPE sender_type AS ENUM (
    'BUYER',
    'SELLER',
    'AI_REFEREE',
    'ADMIN'
);

-- ============================================================================
-- 2. TABLE DEFINITIONS (The 9 Core Entities)
-- ============================================================================

-- 2.1 USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role user_role NOT NULL DEFAULT 'BUYER',
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    paypal_email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.2 CONTRACTS
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    seller_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status contract_state NOT NULL DEFAULT 'DRAFT',
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    deadline TIMESTAMPTZ NOT NULL,
    paypal_order_id VARCHAR(100) UNIQUE,
    paypal_auth_id VARCHAR(100) UNIQUE,
    auth_expires_at TIMESTAMPTZ,
    figma_url TEXT,
    repo_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.3 FEATURES (Checklist Items)
CREATE TABLE IF NOT EXISTS features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    acceptance_test TEXT NOT NULL,
    price_weight NUMERIC(5, 2) NOT NULL CHECK (price_weight >= 0 AND price_weight <= 100),
    allocated_amount NUMERIC(10, 2) NOT NULL CHECK (allocated_amount >= 0),
    status feature_status NOT NULL DEFAULT 'PENDING',
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.4 CHANGE REQUESTS (Changes)
CREATE TABLE IF NOT EXISTS change_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    proposed_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    proposed_price NUMERIC(10, 2) NOT NULL,
    proposed_extra_time_hours INT NOT NULL DEFAULT 0,
    ai_reasoning TEXT,
    status change_request_status NOT NULL DEFAULT 'PROPOSED',
    additional_auth_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.5 SUBMISSIONS
CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    seller_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    repo_url TEXT NOT NULL,
    commit_sha VARCHAR(64) NOT NULL,
    build_notes TEXT,
    submission_number INT NOT NULL DEFAULT 1 CHECK (submission_number BETWEEN 1 AND 3),
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.6 VERIFICATION REPORTS (Reports)
CREATE TABLE IF NOT EXISTS verification_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID UNIQUE NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    render_job_id VARCHAR(100),
    build_succeeded BOOLEAN NOT NULL DEFAULT FALSE,
    build_logs TEXT,
    test_suite_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    cheat_scan_findings JSONB NOT NULL DEFAULT '[]'::jsonb,
    visual_diff_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    per_feature_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    overall_score NUMERIC(4, 3) CHECK (overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 1)),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.7 PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
    payment_type payment_type NOT NULL,
    paypal_reference_id VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status payment_status NOT NULL DEFAULT 'PENDING',
    metadata JSONB DEFAULT '{}'::jsonb,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.8 RECEIPTS
CREATE TABLE IF NOT EXISTS receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
    report_id UUID UNIQUE NOT NULL REFERENCES verification_reports(id) ON DELETE RESTRICT,
    payment_id UUID REFERENCES payments(id) ON DELETE RESTRICT,
    receipt_hash VARCHAR(64) NOT NULL CHECK (length(receipt_hash) = 64),
    summary_text TEXT NOT NULL,
    passed_features_count INT NOT NULL DEFAULT 0,
    total_features_count INT NOT NULL DEFAULT 0,
    seller_payout_amount NUMERIC(10, 2) NOT NULL CHECK (seller_payout_amount >= 0),
    buyer_refund_amount NUMERIC(10, 2) NOT NULL CHECK (buyer_refund_amount >= 0),
    verification_fingerprint_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.9 MESSAGES
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sender_type sender_type NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 3. INDEXES FOR HIGH-PERFORMANCE QUERYING & GANTT RENDERING
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_contracts_buyer_id ON contracts(buyer_id);
CREATE INDEX IF NOT EXISTS idx_contracts_seller_id ON contracts(seller_id);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_features_contract_id ON features(contract_id);
CREATE INDEX IF NOT EXISTS idx_change_requests_contract_id ON change_requests(contract_id);
CREATE INDEX IF NOT EXISTS idx_submissions_contract_id ON submissions(contract_id);
CREATE INDEX IF NOT EXISTS idx_verification_reports_contract_id ON verification_reports(contract_id);
CREATE INDEX IF NOT EXISTS idx_payments_contract_id ON payments(contract_id);
CREATE INDEX IF NOT EXISTS idx_payments_paypal_ref ON payments(paypal_reference_id);
CREATE INDEX IF NOT EXISTS idx_receipts_contract_id ON receipts(contract_id);
CREATE INDEX IF NOT EXISTS idx_receipts_hash ON receipts(receipt_hash);
CREATE INDEX IF NOT EXISTS idx_messages_contract_id ON messages(contract_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);

