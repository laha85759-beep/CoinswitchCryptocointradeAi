-- ═══════════════════════════════════════════════════════════════════════════
-- SUPABASE POSTGRESQL PRODUCTION SAAS SUBSCRIPTION & PERMISSION SCHEMA
-- Platform: trade.thesmartmag.com
-- Settlement: Rise Business USD Account
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Users Table (Synchronized with Supabase Auth auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id BIGSERIAL PRIMARY KEY,
    supabase_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT DEFAULT '',
    name TEXT DEFAULT '',
    role TEXT DEFAULT 'trader', -- 'superadmin', 'admin', 'trader', 'support', 'finance'
    is_active BOOLEAN DEFAULT TRUE,
    referred_by_code TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    country TEXT DEFAULT 'US',
    preferred_exchange TEXT DEFAULT 'both',
    plan_name TEXT DEFAULT 'starter', -- 'starter', 'pro', 'elite', 'enterprise', 'free'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. SaaS Plans Table
CREATE TABLE IF NOT EXISTS public.plans (
    id TEXT PRIMARY KEY, -- 'starter', 'pro', 'elite', 'enterprise'
    name TEXT NOT NULL,
    monthly_price NUMERIC(10, 2) NOT NULL,
    yearly_price NUMERIC(10, 2) NOT NULL,
    description TEXT,
    features JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. User Subscriptions Table
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
    plan_id TEXT REFERENCES public.plans(id),
    status TEXT DEFAULT 'active', -- 'active', 'trialing', 'past_due', 'canceled', 'expired', 'unpaid'
    billing_interval TEXT DEFAULT 'monthly', -- 'monthly', 'yearly', 'lifetime'
    expires_at TIMESTAMPTZ NOT NULL,
    stripe_subscription_id TEXT DEFAULT '',
    stripe_customer_id TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Granular User Service Permissions & Admin Overrides Table
CREATE TABLE IF NOT EXISTS public.permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL, -- 'dashboard', 'ai_chat', 'signals', 'voice', 'risk', 'portfolio', 'api', 'white_label', etc.
    enabled BOOLEAN DEFAULT TRUE,
    is_override BOOLEAN DEFAULT FALSE, -- TRUE if manually assigned/revoked by Super Admin
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, service_name)
);

-- 6. Payments & Billing Transactions Table (USD Currency)
CREATE TABLE IF NOT EXISTS public.payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    stripe_payment_id TEXT DEFAULT '',
    stripe_session_id TEXT DEFAULT '',
    plan_or_addon_id TEXT DEFAULT '',
    status TEXT DEFAULT 'succeeded', -- 'succeeded', 'pending', 'failed', 'refunded'
    payout_account TEXT DEFAULT 'Rise Business USD',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Platform Activity & Audit Logs Table
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ── INDEXES FOR HIGH-THROUGHPUT PERFORMANCE ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON public.subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_permissions_user_service ON public.permissions(user_id, service_name);
CREATE INDEX IF NOT EXISTS idx_payments_user ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_created ON public.payments(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON public.activity_logs(timestamp);

-- ── SEED INITIAL PLANS (USD PRICING) ────────────────────────────────────
INSERT INTO public.plans (id, name, monthly_price, yearly_price, description, features)
VALUES 
    ('starter', 'Starter Trader', 19.00, 190.00, 'Best for beginners', '["Market dashboard", "BTC, ETH, Gold market overview", "Basic AI Assistant (50 prompts/day)", "Economic calendar", "News dashboard", "Watchlist (20 assets)", "Mobile access"]'::jsonb),
    ('pro', 'Pro Trader', 49.00, 490.00, 'Most popular plan for active traders', '["Everything in Starter", "Unlimited AI Assistant", "Trading signals", "AI market analysis", "Jarvis Voice Assistant", "Trade journal", "Risk calculator", "100 watchlist assets", "Email alerts"]'::jsonb),
    ('elite', 'Elite Trader', 99.00, 990.00, 'For professional traders & prop firm accounts', '["Everything in Pro", "Advanced AI predictions", "Institutional dashboard", "Order flow analysis", "Portfolio analytics", "API access", "Webhook alerts", "Priority support"]'::jsonb),
    ('enterprise', 'Enterprise Custom', 0.00, 0.00, 'For institutions, funds & white-label brokers', '["Unlimited users", "White-label platform", "Dedicated manager", "Custom integrations", "SLA support", "Unlimited AI models", "Direct FIX/WebSocket routing"]'::jsonb)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    monthly_price = EXCLUDED.monthly_price,
    yearly_price = EXCLUDED.yearly_price,
    description = EXCLUDED.description,
    features = EXCLUDED.features;

-- ── ROW LEVEL SECURITY (RLS) POLICIES ───────────────────────────────────
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile; Super Admin has unrestricted access
CREATE POLICY "Users can view own data" ON public.users 
    FOR SELECT USING (auth.uid() = supabase_id OR EXISTS (SELECT 1 FROM public.users WHERE supabase_id = auth.uid() AND role = 'superadmin'));

CREATE POLICY "Users can view own subscriptions" ON public.subscriptions 
    FOR SELECT USING (user_id IN (SELECT id FROM public.users WHERE supabase_id = auth.uid()) OR EXISTS (SELECT 1 FROM public.users WHERE supabase_id = auth.uid() AND role = 'superadmin'));

CREATE POLICY "Users can view own permissions" ON public.permissions 
    FOR SELECT USING (user_id IN (SELECT id FROM public.users WHERE supabase_id = auth.uid()) OR EXISTS (SELECT 1 FROM public.users WHERE supabase_id = auth.uid() AND role = 'superadmin'));

CREATE POLICY "Users can view own payments" ON public.payments 
    FOR SELECT USING (user_id IN (SELECT id FROM public.users WHERE supabase_id = auth.uid()) OR EXISTS (SELECT 1 FROM public.users WHERE supabase_id = auth.uid() AND role = 'superadmin'));
