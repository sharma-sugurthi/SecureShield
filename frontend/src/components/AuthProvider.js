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

    useEffect(() => {
        // Initial session check
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
            
            if (!session && !isAuthPage) {
                // If not logged in and trying to access a protected route
                router.push('/login');
            } else if (session && isAuthPage) {
                // If logged in and trying to access login/signup
                router.push('/');
            }
        });

        // Listen for auth changes (login, logout, token refresh)
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
            
            if (!session && !isAuthPage) {
                router.push('/login');
            } else if (session && isAuthPage) {
                router.push('/');
            }
        });

        return () => subscription.unsubscribe();
    }, [pathname, isAuthPage, router]);

    if (loading) {
        return <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--gray-50)' }}>
            <div className="spinner" style={{ width: 40, height: 40, borderTopColor: 'var(--primary-500)' }} />
        </div>;
    }

    return children;
}
