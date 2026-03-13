import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Card, CardContent, Grid, Typography, Button, List, ListItemButton, ListItemText, Divider } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StatusChip from '../components/StatusChip';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: jobs } = usePolling(useCallback(() => api.get('/jobs?limit=20'), []), 5000);
  const { data: agents } = usePolling(useCallback(() => api.get('/agents'), []), 15000);
  const { data: health } = usePolling(useCallback(() => api.get('/health'), []), 10000);

  const activeJobs = jobs?.filter((j) => j.status === 'running') || [];
  const pendingReviews = jobs?.filter((j) => j.status === 'awaiting_review') || [];
  const recentCompleted = jobs?.filter((j) => j.status === 'completed').slice(0, 5) || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Dashboard</Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>System</Typography>
              <StatusChip status={health?.status === 'healthy' ? 'completed' : 'failed'} />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>Active Jobs</Typography>
              <Typography variant="h4">{activeJobs.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>Pending Reviews</Typography>
              <Typography variant="h4" color={pendingReviews.length > 0 ? 'warning.main' : 'text.primary'}>{pendingReviews.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>Agents</Typography>
              <Typography variant="h4">{agents?.length || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recent Jobs</Typography>
              <List dense>
                {(jobs || []).slice(0, 8).map((job) => (
                  <ListItemButton key={job.id} onClick={() => navigate(`/jobs/${job.id}`)}>
                    <ListItemText primary={`#${job.id} ${job.agent_name}`} secondary={new Date(job.created_at).toLocaleString()} />
                    <StatusChip status={job.status} />
                  </ListItemButton>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Registered Agents</Typography>
              <List dense>
                {(agents || []).map((agent) => (
                  <ListItemButton key={agent.name} onClick={() => navigate(`/agents`)}>
                    <ListItemText primary={agent.name} secondary={agent.description} />
                    <Typography variant="caption" color="text.secondary">v{agent.version}</Typography>
                  </ListItemButton>
                ))}
              </List>
              <Divider sx={{ my: 1 }} />
              <Button variant="outlined" startIcon={<PlayArrowIcon />} onClick={() => navigate('/jobs')}>
                Run Agent
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
