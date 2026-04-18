import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { ROUTES } from '@/utils/constants';

/**
 * Root route – immediately redirects to the Dashboard page.
 */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    void router.replace(ROUTES.DASHBOARD);
  }, [router]);

  return null;
}
