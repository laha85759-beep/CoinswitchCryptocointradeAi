-- ==============================================================================
-- SUPABASE POSTGRESQL SCHEMA FOR TRADE.THESMARTMAG.COM SAAS PLATFORM
-- Multi-tier Subscription, Stripe Checkout (USD) & Rise Business USD Settlement
-- ==============================================================================

-- 1. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Users Table (Synchronized with Supabase Auth or Standalone)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    name TEXT,
    role TEXT DEFAULT 'trader', -- 'superadmin', 'admin', 'support', 'finance', 'moderator', 'trader'
    is_active BOOLEAN DEFAULT true,
    referred_by_code TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    country TEXT DEFAULT 'US',
    preferred_exchange TEXT DEFAULT 'both',
    plan_name TEXT DEFAULT 'free', -- 'free', 'starter', 'pro', 'elite', 'enterprise'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Subscription Plans Table
CREATE TABLE IF NOT EXISTS public.plans (
    id TEXT PRIMARY KEY, -- 'starter', 'pro', 'elite', 'enterprise'
    name TEXT NOT NULL,
    monthly_price NUMERIC(10,2) NOT NULL,
    yearly_price NUMERIC(10,2) NOT NULL,
    features JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Plans
INSERT INTO public.plans (id, name, monthly_price, yearly_price, features)
VALUES 
    ('starter', 'Starter Trader', 19.00, 190.00, '["Market Dashboard", "BTC, ETH, Gold Market Overview", "Basic AI Assistant (50 prompts/day)", "Economic Calendar", "News Dashboard", "Watchlist (20 assets)", "Mobile Access"]'::jsonb),
    ('pro', 'Pro Trader', 49.00, 490.00, '["Everything in Starter", "Unlimited AI Assistant", "Real-Time Trading Signals", "AI Market Analysis", "Jarvis Voice Assistant", "Institutional Trade Journal", "Risk Calculator", "100 Watchlist Assets", "Email & Push Alerts"]'::jsonb),
    ('elite', 'Elite Trader', 99.00, 990.00, '["Everything in Pro", "Advanced AI Predictions & SMC", "Institutional Cockpit", "Order Flow & Imbalance Analysis", "Portfolio Analytics", "Institutional API Access", "Webhook Alerts", "Priority 24/7 Support"]'::jsonb),
    ('enterprise', 'Enterprise Custom', 499.00, 4990.00, '["Unlimited Users & Sub-accounts", "Full White-Label Platform", "Dedicated Account Manager", "Custom Broker & Liquidity Integrations", "SLA Guarantee", "Full Source Code Access Option"]'::jsonb)
ON CONFLICT (id) DO UPDATE SET 
    name = EXCLUDED.name,
    monthly_price = EXCLUDED.monthly_price,
    yearly_price = EXCLUDED.yearly_price,
    features = EXCLUDED.features;

-- 4. User Subscriptions Table
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    plan_id TEXT REFERENCES public.plans(id) ON DELETE RESTRICT,
    billing_cycle TEXT DEFAULT 'monthly', -- 'monthly' or 'yearly'
    status TEXT DEFAULT 'active', -- 'active', 'trialing', 'past_due', 'canceled', 'expired', 'unpaid'
    expires_at TIMESTAMPTZ NOT NULL,
    stripe_subscription_id TEXT,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expiry ON public.subscriptions(expires_at);

-- 5. Granular User Permissions Table (Manual Admin Override & Add-ons)
CREATE TABLE IF NOT EXISTS public.permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL, -- 'dashboard', 'ai_chat', 'signals', 'voice_jarvis', 'risk_calculator', 'portfolio_analytics', 'api_access', 'white_label', 'ai_signal_pack', 'gold_strategy_pack', 'prop_firm_toolkit', 'indicator_bundle', 'ai_voice_upgrade'
    enabled BOOLEAN DEFAULT true,
    granted_by TEXT DEFAULT 'plan_rule', -- 'plan_rule', 'admin_manual', 'addon_purchase'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, service_name)
);

CREATE INDEX IF NOT EXISTS idx_permissions_user_service ON public.permissions(user_id, service_name);

-- 6. Payments & Revenue Table (Stripe USD -> Rise Business USD Settlement)
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    amount NUMERIC(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    stripe_payment_id TEXT,
    stripe_invoice_id TEXT,
    stripe_customer_id TEXT,
    payment_type TEXT DEFAULT 'subscription', -- 'subscription', 'addon', 'custom'
    plan_id TEXT,
    status TEXT DEFAULT 'succeeded', -- 'succeeded', 'pending', 'failed', 'refunded'
    settlement_account TEXT DEFAULT 'Rise Business USD',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);

-- 7. SaaS Activity & Security Audit Logs Table
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON public.activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_time ON public.activity_logs(timestamp);

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

-- Super Admin bypasses RLS
CREATE POLICY "Superadmin full access users" ON public.users 
    FOR ALL TO authenticated 
    USING (auth.jwt() ->> 'role' = 'superadmin' OR email = 'admin@thesmartmag.com');

CREATE POLICY "Users read own profile" ON public.users 
    FOR SELECT TO authenticated 
    USING (id = auth.uid() OR email = auth.jwt() ->> 'email');

CREATE POLICY "Users read own subscription" ON public.subscriptions 
    FOR SELECT TO authenticated 
    USING (user_id = auth.uid());

CREATE POLICY "Users read own permissions" ON public.permissions 
    FOR SELECT TO authenticated 
    USING (user_id = auth.uid());

CREATE POLICY "Users read own payments" ON public.payments 
    FOR SELECT TO authenticated 
    USING (user_id = auth.uid());

-- Triggers for automatic updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON public.permissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
