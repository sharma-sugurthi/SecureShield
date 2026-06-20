'use client';

/**
 * AutoKeyProvider — Automatically fetches the API key from the backend on mount.
 * No more manual copy-paste from backend logs!
 */

import { useEffect } from 'react';
import { getApiKey, autoFetchApiKey } from '@/lib/api';

export default function AutoKeyProvider() {
    useEffect(() => {
        autoFetchApiKey().then((key) => {
            if (key) {
                console.log('[PolicyEye] 🔑 API key auto-configured');
                window.dispatchEvent(new Event('apikey_updated'));
            }
        });
    }, []);

    return null; // This is a headless component
}
