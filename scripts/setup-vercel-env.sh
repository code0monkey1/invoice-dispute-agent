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

add_env GROQ_API_KEY        "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"
add_env TAVILY_API_KEY      "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"
add_env SUPABASE_URL        "https://fdsglieendnihbfozbag.supabase.co"
add_env SUPABASE_KEY        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZkc2dsaWVlbmRuaWhiZm96YmFnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTMyODA0NCwiZXhwIjoyMDkwOTA0MDQ0fQ.842i1vDoo-RAwByHBZ-Auw3CXonGlz9S_WgJCe8LNO8"
add_env SECRET_KEY          "e994d1fd416b966ea79369f2f043c9e304c0719cb6644b364b226cd2aaa7abc2"
add_env GOOGLE_CLIENT_ID    "1071958589354-d960gbt9pc4k1r8t0396inval2bh1ntg.apps.googleusercontent.com"
add_env GOOGLE_CLIENT_SECRET "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"
add_env TELEGRAM_BOT_TOKEN  "8690631740:AAFGrA1MdL0_WC5OnpB98bDTbjfZY93n_WE"
add_env TELEGRAM_CHAT_ID    "8657502519"
add_env GOOGLE_PUBSUB_TOPIC "projects/invoice-dispute-agent/topics/gmail-notifications"

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
