import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { SenderProfile } from '../types';
import { qk, senderProfileQuery } from './queries';

// Stable while loading, so forms seeded from the profile don't reset each render.
const EMPTY: SenderProfile = {};

export function useSenderProfile() {
  const qc = useQueryClient();
  const query = useQuery(senderProfileQuery());

  const setProfile = useCallback((next: SenderProfile) => {
    qc.setQueryData(qk.senderProfile, next);
  }, [qc]);

  const save = useCallback(async (next: SenderProfile) => {
    const saved = await api.updateSenderProfile(next);
    qc.setQueryData(qk.senderProfile, saved);
    return saved;
  }, [qc]);

  const error = query.error ? (query.error instanceof Error ? query.error.message : String(query.error)) : null;
  return { profile: query.data ?? EMPTY, loading: query.isPending, error, setProfile, save };
}
