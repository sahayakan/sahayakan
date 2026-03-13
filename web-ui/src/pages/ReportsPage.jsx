import { useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, Tabs, Tab, Chip,
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

function ReportList() {
  const navigate = useNavigate();
  const { data } = usePolling(useCallback(() => api.get('/knowledge/reports'), []), 10000);
  const reports = data?.reports || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Reports</Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>ID</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {reports.map((r) => (
              <TableRow key={r.path} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/reports/${r.type}/${r.id}`)}>
                <TableCell><Chip label={r.type.replace(/_/g, ' ')} size="small" /></TableCell>
                <TableCell>{r.id}</TableCell>
                <TableCell>View</TableCell>
              </TableRow>
            ))}
            {reports.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} align="center">No reports yet</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

function ReportDetail() {
  const { type, id } = useParams();
  const [tab, setTab] = useState(0);
  const { data: report } = usePolling(
    useCallback(() => api.get(`/knowledge/reports/${type}/${id}`), [type, id]),
    30000,
  );

  if (!report) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        <Chip label={type?.replace(/_/g, ' ')} size="small" sx={{ mr: 1 }} />
        Report: {id}
      </Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Report" />
        <Tab label="Raw Data" />
      </Tabs>

      {tab === 0 && report.markdown && (
        <Card>
          <CardContent>
            <ReactMarkdown>{report.markdown}</ReactMarkdown>
          </CardContent>
        </Card>
      )}

      {tab === 1 && report.data && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <pre style={{ margin: 0, fontSize: 13, overflow: 'auto' }}>
            {JSON.stringify(report.data, null, 2)}
          </pre>
        </Paper>
      )}
    </Box>
  );
}

export default function ReportsPage() {
  const { type, id } = useParams();
  return type && id ? <ReportDetail /> : <ReportList />;
}
