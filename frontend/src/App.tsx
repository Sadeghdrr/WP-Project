/**
 * App — root component that composes global providers.
 *
 * Provider order (outermost → innermost):
 *  1. QueryClientProvider  — React Query cache
 *  2. AuthProvider         — JWT auth state
 *  3. AppRouter            — routing + layouts
 */
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/config/queryClient';
import { AuthProvider } from '@/context/AuthContext';
import { AppRouter } from '@/routes/AppRouter';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
