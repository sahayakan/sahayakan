import { useCallback } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip,
} from '@mui/material';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

export default function EventsPage() {
  const { data } = usePolling(useCallback(() => api.get('/events?limit=50'), []), 5000);
  const events = data?.events || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Events</Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Processed</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {events.map((e) => (
              <TableRow key={e.id}>
                <TableCell>{e.id}</TableCell>
                <TableCell><Chip label={e.event_type} size="small" color="primary" variant="outlined" /></TableCell>
                <TableCell>{e.source}</TableCell>
                <TableCell>{e.processed ? 'Yes' : 'No'}</TableCell>
                <TableCell>{new Date(e.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
            {events.length === 0 && (
              <TableRow><TableCell colSpan={5} align="center">No events yet</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
