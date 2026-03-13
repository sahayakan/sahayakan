import { useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, Select, MenuItem, FormControl, InputLabel, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Card, CardContent,
  Grid, Chip, List, ListItem, ListItemText,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StatusChip from '../components/StatusChip';
import LogViewer from '../components/Logs/LogViewer';
import usePolling from '../hooks/usePolling';
import useWebSocket from '../hooks/useWebSocket';
import { api } from '../api/client';

function JobList() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('');
  const { data: jobs, refresh } = usePolling(
    useCallback(() => api.get(`/jobs?limit=50${statusFilter ? `&status=${statusFilter}` : ''}`), [statusFilter]),
    5000,
  );

  const [runOpen, setRunOpen] = useState(false);
  const [runAgent, setRunAgent] = useState('issue-triage');
  const [runParams, setRunParams] = useState('{"issue_id": 2800}');
  const { data: agents } = usePolling(useCallback(() => api.get('/agents'), []), 30000);

  const handleRun = async () => {
    try {
      await api.post('/jobs/run', { agent: runAgent, parameters: JSON.parse(runParams) });
      setRunOpen(false);
      refresh();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Jobs</Typography>
        <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={() => setRunOpen(true)}>Run Agent</Button>
      </Box>

      <FormControl size="small" sx={{ mb: 2, minWidth: 150 }}>
        <InputLabel>Status</InputLabel>
        <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="pending">Pending</MenuItem>
          <MenuItem value="running">Running</MenuItem>
          <MenuItem value="completed">Completed</MenuItem>
          <MenuItem value="failed">Failed</MenuItem>
          <MenuItem value="awaiting_review">Awaiting Review</MenuItem>
        </Select>
      </FormControl>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Agent</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Completed</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(jobs || []).map((job) => (
              <TableRow key={job.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/jobs/${job.id}`)}>
                <TableCell>{job.id}</TableCell>
                <TableCell>{job.agent_name}</TableCell>
                <TableCell><StatusChip status={job.status} /></TableCell>
                <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                <TableCell>{job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={runOpen} onClose={() => setRunOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Run Agent</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 1, mb: 2 }}>
            <InputLabel>Agent</InputLabel>
            <Select value={runAgent} label="Agent" onChange={(e) => setRunAgent(e.target.value)}>
              {(agents || []).map((a) => <MenuItem key={a.name} value={a.name}>{a.name}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField fullWidth multiline rows={3} label="Parameters (JSON)" value={runParams} onChange={(e) => setRunParams(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRunOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleRun}>Run</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function JobDetail() {
  const { id } = useParams();
  const jobId = parseInt(id);
  const { data: job, refresh } = usePolling(useCallback(() => api.get(`/jobs/${jobId}`), [jobId]), 3000);
  const { data: reviewStatus } = usePolling(useCallback(() => api.get(`/jobs/${jobId}/review-status`), [jobId]), 3000);
  const { logs } = useWebSocket(jobId);
  const { data: archivedLogs } = usePolling(useCallback(() => api.get(`/logs/${jobId}?limit=500`), [jobId]), 5000);

  const allLogs = logs.length > 0 ? logs : (archivedLogs?.logs || []);

  const [reviewComment, setReviewComment] = useState('');

  const handleReview = async (decision) => {
    try {
      await api.post(`/jobs/${jobId}/review`, { decision, comments: reviewComment || undefined });
      setReviewComment('');
      refresh();
    } catch (e) {
      alert(e.message);
    }
  };

  if (!job) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Job #{job.id}</Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Details</Typography>
              <Typography><strong>Agent:</strong> {job.agent_name}</Typography>
              <Typography><strong>Status:</strong> <StatusChip status={job.status} /></Typography>
              <Typography><strong>Created:</strong> {new Date(job.created_at).toLocaleString()}</Typography>
              {job.started_at && <Typography><strong>Started:</strong> {new Date(job.started_at).toLocaleString()}</Typography>}
              {job.completed_at && <Typography><strong>Completed:</strong> {new Date(job.completed_at).toLocaleString()}</Typography>}
              <Typography sx={{ mt: 1 }}><strong>Parameters:</strong></Typography>
              <Paper variant="outlined" sx={{ p: 1, mt: 0.5, fontFamily: 'monospace', fontSize: 13 }}>
                {JSON.stringify(job.parameters, null, 2)}
              </Paper>
            </CardContent>
          </Card>
        </Grid>

        {reviewStatus?.awaiting_review && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ borderLeft: 4, borderColor: 'warning.main' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom color="warning.main">Review Required</Typography>
                <TextField fullWidth size="small" label="Comment (optional)" value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} sx={{ mb: 1 }} />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button variant="contained" color="success" onClick={() => handleReview('approved')}>Approve</Button>
                  <Button variant="outlined" color="error" onClick={() => handleReview('rejected')}>Reject</Button>
                </Box>
                {reviewStatus.decisions?.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2">Review History</Typography>
                    <List dense>
                      {reviewStatus.decisions.map((d, i) => (
                        <ListItem key={i}>
                          <ListItemText primary={`${d.stage}: ${d.decision}`} secondary={d.comments || ''} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      <LogViewer logs={allLogs} />
    </Box>
  );
}

export default function JobsPage() {
  const { id } = useParams();
  return id ? <JobDetail /> : <JobList />;
}
