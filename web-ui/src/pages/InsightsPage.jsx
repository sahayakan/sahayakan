import { useCallback, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Select, MenuItem, FormControl, InputLabel,
} from '@mui/material';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

const SEVERITY_COLORS = { critical: 'error', high: 'warning', medium: 'info', low: 'default' };

function InsightCard({ insight, onStatusChange }) {
  return (
    <Card sx={{ mb: 2, borderLeft: 4, borderColor: `${SEVERITY_COLORS[insight.severity] || 'info'}.main` }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h6">{insight.title}</Typography>
            <Box sx={{ display: 'flex', gap: 1, my: 1 }}>
              <Chip label={insight.insight_type?.replace(/_/g, ' ')} size="small" variant="outlined" />
              <Chip label={insight.severity} size="small" color={SEVERITY_COLORS[insight.severity] || 'default'} />
              <Chip label={`${(insight.confidence * 100).toFixed(0)}%`} size="small" />
              <Chip label={insight.status} size="small" variant={insight.status === 'active' ? 'filled' : 'outlined'} />
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {insight.status === 'active' && (
              <Button size="small" onClick={() => onStatusChange(insight.id, 'acknowledged')}>Acknowledge</Button>
            )}
            {insight.status !== 'resolved' && (
              <Button size="small" color="success" onClick={() => onStatusChange(insight.id, 'resolved')}>Resolve</Button>
            )}
          </Box>
        </Box>
        <Typography variant="body2" sx={{ mt: 1 }}>{insight.description}</Typography>
        {insight.evidence && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">Evidence:</Typography>
            {(typeof insight.evidence === 'string' ? JSON.parse(insight.evidence) : insight.evidence).map((ev, i) => (
              <Chip key={i} label={`${ev.type} #${ev.id}`} size="small" sx={{ mr: 0.5, mt: 0.5 }} variant="outlined" />
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default function InsightsPage() {
  const [statusFilter, setStatusFilter] = useState('active');
  const { data, refresh } = usePolling(
    useCallback(() => api.get(`/insights?status=${statusFilter}&limit=50`), [statusFilter]),
    10000,
  );
  const { data: summary } = usePolling(useCallback(() => api.get('/insights/summary'), []), 10000);

  const handleStatusChange = async (id, newStatus) => {
    try {
      await api.put(`/insights/${id}/status`, { status: newStatus });
      refresh();
    } catch (e) {
      alert(e.message);
    }
  };

  const insights = data?.insights || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Insights</Typography>

      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 6, md: 3 }}>
            <Card><CardContent>
              <Typography color="text.secondary">Total</Typography>
              <Typography variant="h4">{summary.total || 0}</Typography>
            </CardContent></Card>
          </Grid>
          {['critical', 'high', 'medium', 'low'].map((sev) => (
            <Grid size={{ xs: 6, md: 2 }} key={sev}>
              <Card><CardContent>
                <Typography color="text.secondary">{sev}</Typography>
                <Typography variant="h5" color={`${SEVERITY_COLORS[sev]}.main`}>
                  {summary.active_by_severity?.[sev] || 0}
                </Typography>
              </CardContent></Card>
            </Grid>
          ))}
        </Grid>
      )}

      <FormControl size="small" sx={{ mb: 2, minWidth: 150 }}>
        <InputLabel>Status</InputLabel>
        <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="acknowledged">Acknowledged</MenuItem>
          <MenuItem value="resolved">Resolved</MenuItem>
          <MenuItem value="">All</MenuItem>
        </Select>
      </FormControl>

      {insights.length === 0 && <Typography color="text.secondary">No insights found. Run the insights agent to detect patterns.</Typography>}
      {insights.map((ins) => <InsightCard key={ins.id} insight={ins} onStatusChange={handleStatusChange} />)}
    </Box>
  );
}
