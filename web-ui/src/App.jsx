import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import MainLayout from './components/Layout/MainLayout';
import DashboardPage from './pages/DashboardPage';
import JobsPage from './pages/JobsPage';
import AgentsPage from './pages/AgentsPage';
import ReportsPage from './pages/ReportsPage';
import EventsPage from './pages/EventsPage';
import SearchPage from './pages/SearchPage';
import InsightsPage from './pages/InsightsPage';

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/:id" element={<JobsPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/reports/:type/:id" element={<ReportsPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/insights" element={<InsightsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
