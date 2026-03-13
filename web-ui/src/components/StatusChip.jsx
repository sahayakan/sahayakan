import { Chip } from '@mui/material';

const STATUS_COLORS = {
  pending: 'default',
  running: 'info',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
  awaiting_review: 'warning',
  started: 'info',
  collecting_data: 'info',
  analyzing: 'info',
  generating_output: 'info',
  storing_artifacts: 'info',
};

export default function StatusChip({ status }) {
  return (
    <Chip
      label={status?.replace(/_/g, ' ')}
      color={STATUS_COLORS[status] || 'default'}
      size="small"
    />
  );
}
