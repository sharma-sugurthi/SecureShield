'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter, usePathname } from 'next/navigation';

export default function AuthProvider({ children }) {
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    const isAuthPage = pathname === '/login' || pathname === '/signup';
    const isPublicPage = pathname === '/chat' || pathname === '/about' || pathname === '/how-it-works';

    useEffect(() => {
        const handleAuth = (session) => {
            if (!session) {
                if (pathname === '/') {
                    router.push('/chat');
                } else if (!isAuthPage && !isPublicPage) {
                    router.push('/login');
                }
            } else if (session && isAuthPage) {
                router.push('/');
            }
        };

        // Initial session check
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
            handleAuth(session);
        });

        // Listen for auth changes (login, logout, token refresh)
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
            handleAuth(session);
        });

        return () => subscription.unsubscribe();
    }, [pathname, isAuthPage, isPublicPage, router]);

    if (loading) {
        return <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--gray-50)' }}>
            <div className="spinner" style={{ width: 40, height: 40, borderTopColor: 'var(--primary-500)' }} />
        </div>;
    }

    return children;
}
