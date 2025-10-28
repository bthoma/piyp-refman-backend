-- Add missing columns to user_profiles table

ALTER TABLE core.user_profiles
ADD COLUMN IF NOT EXISTS auth_provider TEXT DEFAULT 'email' CHECK (auth_provider IN ('email', 'google', 'apple'));

ALTER TABLE core.user_profiles
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

ALTER TABLE core.user_profiles
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
