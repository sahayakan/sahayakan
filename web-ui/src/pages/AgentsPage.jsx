import { useCallback, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Switch, FormControlLabel,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
} from '@mui/material';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

const STAGES = ['after_input', 'after_context', 'after_analysis', 'after_output'];

function GateConfig({ agentName }) {
  const { data: gates, refresh } = usePolling(
    useCallback(() => api.get(`/agents/${agentName}/gates`), [agentName]),
    10000,
  );

  const gateMap = {};
  (gates || []).forEach((g) => { gateMap[g.stage] = g.enabled; });

  const toggleGate = async (stage, enabled) => {
    await api.put(`/agents/${agentName}/gates`, [{ stage, enabled }]);
    refresh();
  };

  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="subtitle2" gutterBottom>Review Gates</Typography>
      {STAGES.map((stage) => (
        <FormControlLabel
          key={stage}
          control={<Switch size="small" checked={!!gateMap[stage]} onChange={(e) => toggleGate(stage, e.target.checked)} />}
          label={stage.replace(/_/g, ' ')}
          sx={{ display: 'block' }}
        />
      ))}
    </Box>
  );
}

export default function AgentsPage() {
  const { data: agents } = usePolling(useCallback(() => api.get('/agents'), []), 10000);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Agents</Typography>
      <Grid container spacing={2}>
        {(agents || []).map((agent) => (
          <Grid size={{ xs: 12, md: 6 }} key={agent.name}>
            <Card>
              <CardContent>
                <Typography variant="h6">{agent.name}</Typography>
                <Typography color="text.secondary" gutterBottom>{agent.description}</Typography>
                <Typography variant="body2"><strong>Version:</strong> {agent.version}</Typography>
                <Typography variant="body2"><strong>Registered:</strong> {new Date(agent.created_at).toLocaleDateString()}</Typography>
                <GateConfig agentName={agent.name} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
