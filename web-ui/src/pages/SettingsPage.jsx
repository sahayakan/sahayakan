import { useCallback, useState } from 'react';
import {
  Box, Typography, Button, IconButton, Switch, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, MenuItem, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Chip, Alert,
  CircularProgress,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SyncIcon from '@mui/icons-material/Sync';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

const PROVIDERS = ['github', 'gitlab', 'bitbucket'];

const EMPTY_REPO_FORM = { name: '', url: '', provider: 'github', default_branch: 'main' };
const EMPTY_JIRA_FORM = { name: '', project_key: '', base_url: '' };
const EMPTY_GITHUB_APP_FORM = { app_id: '', app_name: '', private_key: '', webhook_secret: '' };
const EMPTY_INSTALLATION_FORM = { installation_id: '', account_login: '', account_type: 'Organization' };

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

  // --- GitHub App ---
  const { data: githubApps, refresh: refreshApps } = usePolling(
    useCallback(() => api.get('/github-app'), []),
    10000,
  );

  const [appDialogOpen, setAppDialogOpen] = useState(false);
  const [appEditId, setAppEditId] = useState(null);
  const [appForm, setAppForm] = useState(EMPTY_GITHUB_APP_FORM);
  const [appDeleteConfirm, setAppDeleteConfirm] = useState(null);
  const [appTestResult, setAppTestResult] = useState(null);
  const [appTesting, setAppTesting] = useState(false);

  // Installations
  const [instAppId, setInstAppId] = useState(null);
  const [installations, setInstallations] = useState([]);
  const [instDialogOpen, setInstDialogOpen] = useState(false);
  const [instForm, setInstForm] = useState(EMPTY_INSTALLATION_FORM);
  const [instDeleteConfirm, setInstDeleteConfirm] = useState(null);
  const [discoveringInstId, setDiscoveringInstId] = useState(null);
  const [discoverResult, setDiscoverResult] = useState(null);

  const handleDiscoverRepos = async (instId) => {
    setDiscoveringInstId(instId);
    setDiscoverResult(null);
    try {
      const result = await api.post(`/github-app/${instAppId}/installations/${instId}/discover`);
      setDiscoverResult({ success: true, count: result.discovered });
      refreshRepos();
    } catch (err) {
      setDiscoverResult({ success: false, error: err?.response?.data?.detail || 'Discovery failed' });
    }
    setDiscoveringInstId(null);
  };

  const openAddApp = () => {
    setAppEditId(null);
    setAppForm(EMPTY_GITHUB_APP_FORM);
    setAppTestResult(null);
    setAppDialogOpen(true);
  };

  const openEditApp = (app) => {
    setAppEditId(app.id);
    setAppForm({ app_id: app.app_id, app_name: app.app_name, private_key: '', webhook_secret: app.webhook_secret || '' });
    setAppTestResult(null);
    setAppDialogOpen(true);
  };

  const handleSaveApp = async () => {
    const payload = { ...appForm, app_id: Number(appForm.app_id) };
    if (appEditId) {
      const updates = {};
      if (payload.app_name) updates.app_name = payload.app_name;
      if (payload.private_key) updates.private_key = payload.private_key;
      if (payload.webhook_secret !== undefined) updates.webhook_secret = payload.webhook_secret;
      await api.put(`/github-app/${appEditId}`, updates);
    } else {
      await api.post('/github-app', payload);
    }
    setAppDialogOpen(false);
    refreshApps();
  };

  const handleDeleteApp = async (id) => {
    await api.delete(`/github-app/${id}`);
    setAppDeleteConfirm(null);
    refreshApps();
  };

  const handleTestApp = async (id) => {
    setAppTesting(true);
    setAppTestResult(null);
    try {
      const result = await api.post(`/github-app/${id}/test`);
      setAppTestResult({ success: true, ...result });
    } catch (err) {
      setAppTestResult({ success: false, error: err?.response?.data?.detail || 'Connection test failed' });
    }
    setAppTesting(false);
  };

  const setAppField = (field) => (e) => setAppForm({ ...appForm, [field]: e.target.value });

  const openInstallations = async (appDbId) => {
    setInstAppId(appDbId);
    try {
      const data = await api.get(`/github-app/${appDbId}/installations`);
      setInstallations(data);
    } catch { setInstallations([]); }
  };

  const handleAddInstallation = async () => {
    await api.post(`/github-app/${instAppId}/installations`, {
      ...instForm,
      installation_id: Number(instForm.installation_id),
    });
    setInstDialogOpen(false);
    openInstallations(instAppId);
  };

  const handleDeleteInstallation = async (instId) => {
    await api.delete(`/github-app/${instAppId}/installations/${instId}`);
    setInstDeleteConfirm(null);
    openInstallations(instAppId);
  };

  const setInstField = (field) => (e) => setInstForm({ ...instForm, [field]: e.target.value });

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

      {/* GitHub Integration Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, mt: 4 }}>
        <Typography variant="h6">GitHub Integration</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddApp}>
          Add GitHub App
        </Button>
      </Box>
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>App Name</TableCell>
              <TableCell>App ID</TableCell>
              <TableCell>Webhook Secret</TableCell>
              <TableCell>Installations</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(githubApps || []).map((app) => (
              <TableRow key={app.id}>
                <TableCell>{app.app_name}</TableCell>
                <TableCell><Chip label={app.app_id} size="small" variant="outlined" /></TableCell>
                <TableCell>{app.webhook_secret ? 'Configured' : 'Not set'}</TableCell>
                <TableCell>
                  <Button size="small" onClick={() => openInstallations(app.id)}>View</Button>
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => handleTestApp(app.id)} disabled={appTesting}>
                    Test
                  </Button>
                  <IconButton size="small" onClick={() => openEditApp(app)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => setAppDeleteConfirm(app.id)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {githubApps && githubApps.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  No GitHub App configured. Add one to enable GitHub sync.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {appTestResult && (
        <Alert severity={appTestResult.success ? 'success' : 'error'} sx={{ mb: 2 }} onClose={() => setAppTestResult(null)}>
          {appTestResult.success
            ? `Connected to GitHub App "${appTestResult.app_name}" (${appTestResult.app_slug})`
            : appTestResult.error}
        </Alert>
      )}

      {/* Installations panel */}
      {instAppId && (
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle1">Installations for App #{instAppId}</Typography>
            <Box>
              <Button size="small" startIcon={<AddIcon />} onClick={() => { setInstForm(EMPTY_INSTALLATION_FORM); setInstDialogOpen(true); }}>
                Add Installation
              </Button>
              <Button size="small" onClick={() => setInstAppId(null)}>Close</Button>
            </Box>
          </Box>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Installation ID</TableCell>
                  <TableCell>Account</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Active</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {installations.map((inst) => (
                  <TableRow key={inst.id}>
                    <TableCell>{inst.installation_id}</TableCell>
                    <TableCell>{inst.account_login}</TableCell>
                    <TableCell><Chip label={inst.account_type} size="small" /></TableCell>
                    <TableCell>{inst.is_active ? <CheckCircleIcon color="success" fontSize="small" /> : 'No'}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" title="Discover Repos" onClick={() => handleDiscoverRepos(inst.id)}
                        disabled={discoveringInstId === inst.id}>
                        {discoveringInstId === inst.id ? <CircularProgress size={18} /> : <SyncIcon fontSize="small" />}
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => setInstDeleteConfirm(inst.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {installations.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 2 }}>
                      No installations. Add one to enable GitHub App auth for repositories.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          {discoverResult && (
            <Alert severity={discoverResult.success ? 'success' : 'error'} sx={{ mt: 1 }} onClose={() => setDiscoverResult(null)}>
              {discoverResult.success
                ? `Discovered ${discoverResult.count} repositories`
                : discoverResult.error}
            </Alert>
          )}
        </Box>
      )}

      {/* GitHub App Add/Edit Dialog */}
      <Dialog open={appDialogOpen} onClose={() => setAppDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{appEditId ? 'Edit GitHub App' : 'Add GitHub App'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField label="App ID" value={appForm.app_id} onChange={setAppField('app_id')} required fullWidth
            type="number" disabled={!!appEditId} />
          <TextField label="App Name" value={appForm.app_name} onChange={setAppField('app_name')} required fullWidth />
          <TextField label="Private Key (PEM)" value={appForm.private_key} onChange={setAppField('private_key')}
            required={!appEditId} fullWidth multiline rows={4}
            helperText={appEditId ? 'Leave blank to keep existing key' : 'Paste the .pem file contents'} />
          <TextField label="Webhook Secret" value={appForm.webhook_secret} onChange={setAppField('webhook_secret')} fullWidth
            helperText="Optional. Used to verify webhook payloads from this app." />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAppDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveApp}
            disabled={!appForm.app_name || (!appEditId && (!appForm.app_id || !appForm.private_key))}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* GitHub App Delete Confirmation */}
      <Dialog open={!!appDeleteConfirm} onClose={() => setAppDeleteConfirm(null)}>
        <DialogTitle>Delete GitHub App</DialogTitle>
        <DialogContent>
          <Typography>Are you sure? This will also remove all installations linked to this app.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAppDeleteConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => handleDeleteApp(appDeleteConfirm)}>Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Installation Add Dialog */}
      <Dialog open={instDialogOpen} onClose={() => setInstDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Installation</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField label="Installation ID" value={instForm.installation_id} onChange={setInstField('installation_id')}
            required fullWidth type="number" helperText="Find this in your GitHub App's installation settings URL" />
          <TextField label="Account Login" value={instForm.account_login} onChange={setInstField('account_login')}
            required fullWidth helperText="Organization or user name where the app is installed" />
          <TextField label="Account Type" value={instForm.account_type} onChange={setInstField('account_type')} select fullWidth>
            <MenuItem value="Organization">Organization</MenuItem>
            <MenuItem value="User">User</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddInstallation}
            disabled={!instForm.installation_id || !instForm.account_login}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Installation Delete Confirmation */}
      <Dialog open={!!instDeleteConfirm} onClose={() => setInstDeleteConfirm(null)}>
        <DialogTitle>Remove Installation</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to remove this installation?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstDeleteConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => handleDeleteInstallation(instDeleteConfirm)}>Remove</Button>
        </DialogActions>
      </Dialog>

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
