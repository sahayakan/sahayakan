import { useCallback, useState } from 'react';
import {
  Box, Typography, Button, IconButton, Switch, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, MenuItem, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

const PROVIDERS = ['github', 'gitlab', 'bitbucket'];

const EMPTY_REPO_FORM = { name: '', url: '', provider: 'github', default_branch: 'main' };
const EMPTY_JIRA_FORM = { name: '', project_key: '', base_url: '' };

export default function SettingsPage() {
  // --- Repositories ---
  const { data: repos, refresh: refreshRepos } = usePolling(
    useCallback(() => api.get('/repositories'), []),
    10000,
  );

  const [repoDialogOpen, setRepoDialogOpen] = useState(false);
  const [repoEditId, setRepoEditId] = useState(null);
  const [repoForm, setRepoForm] = useState(EMPTY_REPO_FORM);
  const [repoDeleteConfirm, setRepoDeleteConfirm] = useState(null);

  const openAddRepo = () => {
    setRepoEditId(null);
    setRepoForm(EMPTY_REPO_FORM);
    setRepoDialogOpen(true);
  };

  const openEditRepo = (repo) => {
    setRepoEditId(repo.id);
    setRepoForm({ name: repo.name, url: repo.url, provider: repo.provider, default_branch: repo.default_branch });
    setRepoDialogOpen(true);
  };

  const handleSaveRepo = async () => {
    if (repoEditId) {
      await api.put(`/repositories/${repoEditId}`, repoForm);
    } else {
      await api.post('/repositories', repoForm);
    }
    setRepoDialogOpen(false);
    refreshRepos();
  };

  const handleDeleteRepo = async (id) => {
    await api.delete(`/repositories/${id}`);
    setRepoDeleteConfirm(null);
    refreshRepos();
  };

  const handleToggleRepoActive = async (repo) => {
    await api.put(`/repositories/${repo.id}`, { is_active: !repo.is_active });
    refreshRepos();
  };

  const setRepoField = (field) => (e) => setRepoForm({ ...repoForm, [field]: e.target.value });

  // --- Jira Projects ---
  const { data: jiraProjects, refresh: refreshJira } = usePolling(
    useCallback(() => api.get('/jira-projects'), []),
    10000,
  );

  const [jiraDialogOpen, setJiraDialogOpen] = useState(false);
  const [jiraEditId, setJiraEditId] = useState(null);
  const [jiraForm, setJiraForm] = useState(EMPTY_JIRA_FORM);
  const [jiraDeleteConfirm, setJiraDeleteConfirm] = useState(null);

  const openAddJira = () => {
    setJiraEditId(null);
    setJiraForm(EMPTY_JIRA_FORM);
    setJiraDialogOpen(true);
  };

  const openEditJira = (project) => {
    setJiraEditId(project.id);
    setJiraForm({ name: project.name, project_key: project.project_key, base_url: project.base_url });
    setJiraDialogOpen(true);
  };

  const handleSaveJira = async () => {
    if (jiraEditId) {
      await api.put(`/jira-projects/${jiraEditId}`, jiraForm);
    } else {
      await api.post('/jira-projects', jiraForm);
    }
    setJiraDialogOpen(false);
    refreshJira();
  };

  const handleDeleteJira = async (id) => {
    await api.delete(`/jira-projects/${id}`);
    setJiraDeleteConfirm(null);
    refreshJira();
  };

  const handleToggleJiraActive = async (project) => {
    await api.put(`/jira-projects/${project.id}`, { is_active: !project.is_active });
    refreshJira();
  };

  const setJiraField = (field) => (e) => setJiraForm({ ...jiraForm, [field]: e.target.value });

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>Settings</Typography>

      {/* Repositories Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">Repositories</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddRepo}>
          Add Repository
        </Button>
      </Box>
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>URL</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Branch</TableCell>
              <TableCell>Active</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(repos || []).map((repo) => (
              <TableRow key={repo.id}>
                <TableCell>{repo.name}</TableCell>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{repo.url}</TableCell>
                <TableCell><Chip label={repo.provider} size="small" /></TableCell>
                <TableCell>{repo.default_branch}</TableCell>
                <TableCell>
                  <Switch checked={repo.is_active} onChange={() => handleToggleRepoActive(repo)} size="small" />
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => openEditRepo(repo)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => setRepoDeleteConfirm(repo.id)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {repos && repos.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  No repositories configured. Click &quot;Add Repository&quot; to get started.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Jira Projects Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">Jira Projects</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddJira}>
          Add Jira Project
        </Button>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Project Key</TableCell>
              <TableCell>Base URL</TableCell>
              <TableCell>Active</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(jiraProjects || []).map((project) => (
              <TableRow key={project.id}>
                <TableCell>{project.name}</TableCell>
                <TableCell><Chip label={project.project_key} size="small" variant="outlined" /></TableCell>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{project.base_url}</TableCell>
                <TableCell>
                  <Switch checked={project.is_active} onChange={() => handleToggleJiraActive(project)} size="small" />
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => openEditJira(project)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => setJiraDeleteConfirm(project.id)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {jiraProjects && jiraProjects.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  No Jira projects configured. Click &quot;Add Jira Project&quot; to get started.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Repository Add/Edit Dialog */}
      <Dialog open={repoDialogOpen} onClose={() => setRepoDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{repoEditId ? 'Edit Repository' : 'Add Repository'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField label="Name" value={repoForm.name} onChange={setRepoField('name')} required fullWidth />
          <TextField label="URL" value={repoForm.url} onChange={setRepoField('url')} required fullWidth />
          <TextField label="Provider" value={repoForm.provider} onChange={setRepoField('provider')} select fullWidth>
            {PROVIDERS.map((p) => <MenuItem key={p} value={p}>{p}</MenuItem>)}
          </TextField>
          <TextField label="Default Branch" value={repoForm.default_branch} onChange={setRepoField('default_branch')} fullWidth />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRepoDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveRepo} disabled={!repoForm.name || !repoForm.url}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Repository Delete Confirmation */}
      <Dialog open={!!repoDeleteConfirm} onClose={() => setRepoDeleteConfirm(null)}>
        <DialogTitle>Delete Repository</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this repository?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRepoDeleteConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => handleDeleteRepo(repoDeleteConfirm)}>Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Jira Add/Edit Dialog */}
      <Dialog open={jiraDialogOpen} onClose={() => setJiraDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{jiraEditId ? 'Edit Jira Project' : 'Add Jira Project'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField label="Project Name" value={jiraForm.name} onChange={setJiraField('name')} required fullWidth />
          <TextField label="Project Key" value={jiraForm.project_key} onChange={setJiraField('project_key')} required fullWidth
            helperText="e.g. PROJ, ENG, PLATFORM" />
          <TextField label="Base URL" value={jiraForm.base_url} onChange={setJiraField('base_url')} required fullWidth
            helperText="e.g. https://yourcompany.atlassian.net" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJiraDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveJira} disabled={!jiraForm.name || !jiraForm.project_key || !jiraForm.base_url}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Jira Delete Confirmation */}
      <Dialog open={!!jiraDeleteConfirm} onClose={() => setJiraDeleteConfirm(null)}>
        <DialogTitle>Delete Jira Project</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this Jira project?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJiraDeleteConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => handleDeleteJira(jiraDeleteConfirm)}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
