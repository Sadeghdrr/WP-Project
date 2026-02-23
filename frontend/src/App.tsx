/**
 * App — root component that composes global providers.
 *
 * Provider order (outermost → innermost):
 *  1. ErrorBoundary        — catch unhandled render errors
 *  2. QueryClientProvider  — React Query cache
 *  3. AuthProvider         — JWT auth state
 *  4. ToastProvider        — global toast notifications
 *  5. AppRouter            — routing + layouts
 */
import './App.css';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/config/queryClient';
import { AuthProvider } from '@/context/AuthContext';
import { ToastProvider } from '@/context/ToastContext';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { AppRouter } from '@/routes/AppRouter';

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastProvider>
            <AppRouter />
          </ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
