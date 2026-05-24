import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { SenderProfile } from '../types';

export function useSenderProfile() {
  const [profile, setProfile] = useState<SenderProfile>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getSenderProfile()
      .then(p => { if (!cancelled) setProfile(p ?? {}); })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const save = useCallback(async (next: SenderProfile) => {
    const saved = await api.updateSenderProfile(next);
    setProfile(saved);
    return saved;
  }, []);

  return { profile, loading, error, setProfile, save };
}
