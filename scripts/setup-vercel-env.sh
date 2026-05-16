#!/bin/bash
# Sets all required environment variables on Vercel for all environments.
# Run AFTER `vercel link` — i.e. after you've authenticated and linked the project.
# Usage: bash scripts/setup-vercel-env.sh

set -e

ENVS="production preview development"

add_env() {
  local key=$1
  local val=$2
  for env in $ENVS; do
    echo "$val" | vercel env add "$key" "$env" --force 2>/dev/null || true
  done
  echo "✓ $key"
}

echo "Setting Vercel environment variables..."

add_env GROQ_API_KEY        "${GROQ_API_KEY:?Set GROQ_API_KEY in your shell first}"
add_env TAVILY_API_KEY      "${TAVILY_API_KEY:?Set TAVILY_API_KEY in your shell first}"
add_env SUPABASE_URL        "${SUPABASE_URL:?Set SUPABASE_URL in your shell first}"
add_env SUPABASE_KEY        "${SUPABASE_KEY:?Set SUPABASE_KEY in your shell first}"
add_env SECRET_KEY          "${SECRET_KEY:?Set SECRET_KEY in your shell first}"
add_env GOOGLE_CLIENT_ID    "${GOOGLE_CLIENT_ID:?Set GOOGLE_CLIENT_ID in your shell first}"
add_env GOOGLE_CLIENT_SECRET "${GOOGLE_CLIENT_SECRET:?Set GOOGLE_CLIENT_SECRET in your shell first}"
add_env TELEGRAM_BOT_TOKEN  "${TELEGRAM_BOT_TOKEN:-}"
add_env TELEGRAM_CHAT_ID    "${TELEGRAM_CHAT_ID:-}"
add_env GOOGLE_PUBSUB_TOPIC "${GOOGLE_PUBSUB_TOPIC:-}"
add_env SUPABASE_INVOICE_FILE_BUCKET "${SUPABASE_INVOICE_FILE_BUCKET:-invoice-files}"

echo ""
echo "⚠️  Two env vars still need manual values:"
echo ""
echo "  1. GOOGLE_REDIRECT_URI — set AFTER you know your Vercel URL:"
echo "     vercel env add GOOGLE_REDIRECT_URI production"
echo "     → value: https://YOUR-APP.vercel.app/auth/google/callback"
echo ""
echo "  2. DATABASE_URL — requires your Supabase DB password:"
echo "     vercel env add DATABASE_URL production"
echo "     → value: postgresql://postgres:YOUR-PASSWORD@db.fdsglieendnihbfozbag.supabase.co:5432/postgres"
echo "     → Get password: Supabase Dashboard → invoice-chaser → Settings → Database → Database password"
echo ""
echo "Done. Run: vercel --prod"
