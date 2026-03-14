-- Migration 009: Remove auth_mode column from repositories
-- GitHub App is now the only authentication method (PAT support removed)
ALTER TABLE repositories DROP COLUMN IF EXISTS auth_mode;
