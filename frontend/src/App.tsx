/**
 * App — root component that composes global providers.
 *
 * Provider order (outermost → innermost):
 *  1. QueryClientProvider  — React Query cache
 *  2. AuthProvider         — JWT auth state
 *  3. ToastProvider        — global toast notifications
 *  4. AppRouter            — routing + layouts
 */
import './App.css';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/config/queryClient';
import { AuthProvider } from '@/context/AuthContext';
import { ToastProvider } from '@/context/ToastContext';
import { AppRouter } from '@/routes/AppRouter';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <AppRouter />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
