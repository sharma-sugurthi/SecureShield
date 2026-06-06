'use client';

/**
 * AutoKeyProvider — Automatically fetches the API key from the backend on mount.
 * No more manual copy-paste from backend logs!
 */

import { useEffect } from 'react';
import { getApiKey, autoFetchApiKey } from '@/lib/api';

export default function AutoKeyProvider() {
    useEffect(() => {
        // Only auto-fetch if no key is already saved
        if (!getApiKey()) {
            autoFetchApiKey().then((key) => {
                if (key) {
                    console.log('[SecureShield] 🔑 API key auto-configured');
                }
            });
        }
    }, []);

    return null; // This is a headless component
}
