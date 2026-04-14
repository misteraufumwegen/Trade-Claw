-- Trading Bot Database Schema v2
-- Initial schema setup with users, credentials, trades, and audit logs

CREATE SCHEMA IF NOT EXISTS trading_bot;
SET search_path TO trading_bot;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Broker credentials vault (encrypted)
CREATE TABLE credentials_vault (
    id SERIAL PRIMARY KEY,
    credential_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    broker_name VARCHAR(50) NOT NULL,
    api_key VARCHAR(255) NOT NULL,  -- Will be encrypted at application level
    api_secret VARCHAR(255) NOT NULL,  -- Will be encrypted at application level
    environment VARCHAR(20) DEFAULT 'sandbox',  -- 'sandbox' or 'live'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, broker_name)
);

-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    trade_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    broker_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    limit_price DECIMAL(15, 8),
    stop_price DECIMAL(15, 8),
    entry_price DECIMAL(15, 8) NOT NULL,
    exit_price DECIMAL(15, 8),
    commission DECIMAL(15, 8) DEFAULT 0,
    status VARCHAR(30) NOT NULL CHECK (status IN ('pending', 'filled', 'partially_filled', 'cancelled', 'rejected', 'expired')),
    time_in_force VARCHAR(10) DEFAULT 'day' CHECK (time_in_force IN ('day', 'gtc', 'ioc', 'fok')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    closed_at TIMESTAMP,
    pnl DECIMAL(15, 8),
    pnl_percent DECIMAL(10, 4),
    notes TEXT
);

-- Audit logs for compliance and debugging
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    log_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failure', 'pending')),
    details JSONB,
    ip_address INET,
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_credentials_user_id ON credentials_vault(user_id);
CREATE INDEX idx_credentials_broker ON credentials_vault(broker_name);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created_at ON trades(created_at);
CREATE INDEX idx_trades_broker ON trades(broker_name);
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);

-- Create timestamp update trigger function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to users
CREATE TRIGGER trigger_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Apply trigger to credentials_vault
CREATE TRIGGER trigger_credentials_updated_at
BEFORE UPDATE ON credentials_vault
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON SCHEMA trading_bot TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading_bot TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trading_bot TO trading_user;
