'use strict';

(function () {
  const SEEDED_CLIENTS = [
    {
      id: '00000001-0000-4000-8000-000000000001',
      name: 'Pedro Silva',
      cpf: '11144477735',
      rfid: '962185903074',
      password: '3443dre3t4t',
      balance: 578.0,
    },
    {
      id: '00000002-0000-4000-8000-000000000002',
      name: 'Carlo Edoardo',
      cpf: '52998224059',
      rfid: '701044494601',
      password: '43gds5yge',
      balance: 2345.0,
    },
    {
      id: '00000003-0000-4000-8000-000000000003',
      name: 'Miguel Alencar',
      cpf: '12345678908',
      rfid: '632092037175',
      password: 'miguel123456',
      balance: 21.0,
    },
    {
      id: '00000004-0000-4000-8000-000000000004',
      name: 'Sophia Bonita',
      cpf: '45678901206',
      rfid: '427066982110',
      password: 'admin1234567',
      balance: 95046.0,
    },
  ];

  const SEEDED_TEST_HINTS = {
    '962185903074': { name: 'Pedro Silva', password: '3443dre3t4t' },
    '701044494601': { name: 'Carlo Edoardo', password: '43gds5yge' },
    '632092037175': { name: 'Miguel Alencar', password: 'miguel123456' },
    '427066982110': { name: 'Sophia Bonita', password: 'admin1234567' },
  };

  const STORAGE_KEYS = {
    OFFLINE_DB: 'novobank_offline_clients_v2',
    LEDGER: 'novobank_session_ledger_v2',
  };

  const LIMITS = {
    WITHDRAW_MAX: 10000,
    DEPOSIT_MAX: 1000000,
  };

  const SESSION_TIMEOUT_SECONDS = 60;

  const state = {
    backendMode: 'checking', // 'checking' | 'api' | 'offline'
    apiBase: '',
    simRfidUrl: null,
    backendLabel: 'Verificando API...',
    currentView: 'viewStandby',
    pendingRfid: null,
    regRfid: null,
    currentUser: null,
    selectedDepositAmount: 0,
    selectedWithdrawAmount: 0,
    isReadingRfid: false,
    isSubmitting: false,
    deleteArmed: false,
    deleteArmTimer: null,
    inactivitySeconds: SESSION_TIMEOUT_SECONDS,
    inactivityInterval: null,
    audioCtx: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function formatCurrency(value) {
    const numeric = Number(value) || 0;
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(numeric);
  }

  function formatCpf(digits) {
    const clean = String(digits || '').replace(/\D/g, '');
    if (clean.length !== 11) {
      return clean || '--';
    }
    return clean.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  function getInitials(name) {
    const parts = String(name || '')
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (parts.length === 0) return 'NB';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function nowFormattedTime() {
    return new Intl.DateTimeFormat('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(new Date());
  }

  function nowFormattedDateTime() {
    const d = new Date();
    const datePart = new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
    }).format(d);
    const timePart = new Intl.DateTimeFormat('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(d);
    return `${datePart} ${timePart}`;
  }

  function isValidCpf(cpfInput) {
    const cpf = String(cpfInput || '').replace(/\D/g, '');
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
      return false;
    }
    let sum = 0;
    for (let i = 0; i < 9; i += 1) {
      sum += Number(cpf[i]) * (10 - i);
    }
    let rem = sum % 11;
    const d1 = rem < 2 ? 0 : 11 - rem;
    if (d1 !== Number(cpf[9])) return false;

    sum = 0;
    for (let i = 0; i < 10; i += 1) {
      sum += Number(cpf[i]) * (11 - i);
    }
    rem = sum % 11;
    const d2 = rem < 2 ? 0 : 11 - rem;
    return d2 === Number(cpf[10]);
  }

  function generateValidCpf() {
    let base = '';
    do {
      base = '';
      for (let i = 0; i < 9; i += 1) {
        base += String(Math.floor(Math.random() * 10));
      }
    } while (/^(\d)\1{8}$/.test(base));

    let sum1 = 0;
    for (let i = 0; i < 9; i += 1) {
      sum1 += Number(base[i]) * (10 - i);
    }
    const rem1 = sum1 % 11;
    const d1 = rem1 < 2 ? 0 : 11 - rem1;

    const withD1 = base + String(d1);
    let sum2 = 0;
    for (let i = 0; i < 10; i += 1) {
      sum2 += Number(withD1[i]) * (11 - i);
    }
    const rem2 = sum2 % 11;
    const d2 = rem2 < 2 ? 0 : 11 - rem2;

    return withD1 + String(d2);
  }

  function normalizeClient(raw) {
    if (!raw) return null;
    return {
      id: String(raw.id || ''),
      name: String(raw.name || 'Titular'),
      cpf: String(raw.cpf || ''),
      rfid: String(raw.rfid || ''),
      balance: Number(raw.balance || 0),
    };
  }

  function showAlert(el, message, type = 'error') {
    if (!el) return;
    if (!message) {
      el.style.display = 'none';
      el.textContent = '';
      return;
    }
    el.className = `inline-alert ${type}`;
    el.textContent = message;
    el.style.display = 'block';
  }

  function playTone(freq = 880, duration = 0.08, type = 'sine') {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!state.audioCtx) {
        state.audioCtx = new AudioCtx();
      }
      if (state.audioCtx.state === 'suspended') {
        state.audioCtx.resume().catch(() => {});
      }
      const osc = state.audioCtx.createOscillator();
      const gain = state.audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, state.audioCtx.currentTime);
      gain.gain.setValueAtTime(0.05, state.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, state.audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(state.audioCtx.destination);
      osc.start();
      osc.stop(state.audioCtx.currentTime + duration);
    } catch (_err) {
      // Audio playback blocked before user gesture; ignore safely
    }
  }

  function playSuccessSound() {
    playTone(880, 0.08, 'sine');
    setTimeout(() => playTone(1175, 0.11, 'sine'), 85);
  }

  function playErrorSound() {
    playTone(260, 0.14, 'triangle');
  }

  function pulseSensorGraphic() {
    const sensor = $('standbySensorGraphic');
    if (!sensor) return;
    sensor.classList.add('pulse');
    setTimeout(() => sensor.classList.remove('pulse'), 650);
  }

  // Offline storage fallback database
  function getOfflineClients() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.OFFLINE_DB);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (_err) {
      // Fallback to seed copy
    }
    const seeded = SEEDED_CLIENTS.map((c) => ({ ...c }));
    saveOfflineClients(seeded);
    return seeded;
  }

  function saveOfflineClients(clients) {
    try {
      localStorage.setItem(STORAGE_KEYS.OFFLINE_DB, JSON.stringify(clients));
    } catch (_err) {
      // Ignore storage quota errors
    }
  }

  function getLedgerMap() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEYS.LEDGER);
      return raw ? JSON.parse(raw) : {};
    } catch (_err) {
      return {};
    }
  }

  function saveLedgerMap(map) {
    try {
      sessionStorage.setItem(STORAGE_KEYS.LEDGER, JSON.stringify(map));
    } catch (_err) {
      // Ignore sessionStorage errors
    }
  }

  function appendLedgerEntry(accountId, entry) {
    if (!accountId) return;
    const map = getLedgerMap();
    const list = Array.isArray(map[accountId]) ? map[accountId] : [];
    list.unshift({
      timestamp: entry.timestamp || nowFormattedDateTime(),
      description: entry.description,
      channel: entry.channel,
      delta: Number(entry.delta || 0),
      balanceAfter: Number(entry.balanceAfter || 0),
    });
    map[accountId] = list.slice(0, 20);
    saveLedgerMap(map);
  }

  // Backend detection & HTTP helpers
  async function probeEndpoint(url, timeoutMs = 1200) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, { method: 'GET', signal: controller.signal });
      if (!res.ok) return null;
      const data = await res.json().catch(() => null);
      if (!data || typeof data !== 'object') return null;
      if (data.message || data.status === 'ok') return data;
      return null;
    } catch (_err) {
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  function updateConnectionIndicators() {
    const dot = $('statusDot');
    const headerText = $('hardwareStatusText');
    const wsStatus = $('wsConnectionStatus');
    const syncMeta = $('dashSyncMeta');

    if (state.backendMode === 'api') {
      if (dot) dot.classList.remove('waiting');
      if (headerText) headerText.textContent = state.backendLabel;
      if (wsStatus) wsStatus.textContent = `API: Conectada (${state.apiBase})`;
      if (syncMeta) {
        const span = syncMeta.querySelector('span');
        if (span) span.textContent = 'Sincronizado com backend Flask (SQLite/Redis)';
      }
    } else if (state.backendMode === 'offline') {
      if (dot) dot.classList.add('waiting');
      if (headerText) headerText.textContent = 'Simulador Offline (API indisponível)';
      if (wsStatus) wsStatus.textContent = 'API Offline · Fallback LocalStorage ativo';
      if (syncMeta) {
        const span = syncMeta.querySelector('span');
        if (span) span.textContent = 'Modo Offline (dados locais do navegador)';
      }
    } else {
      if (dot) dot.classList.add('waiting');
      if (headerText) headerText.textContent = 'Verificando API Flask...';
      if (wsStatus) wsStatus.textContent = 'API: Conectando...';
    }
  }

  async function detectApiBackend() {
    const candidates = [];
    const isHttp = window.location.protocol.startsWith('http');

    if (isHttp) {
      candidates.push({
        apiBase: '/api',
        healthUrl: '/health',
        simRfidUrl: '/api/sim-rfid',
        label: 'API Flask Conectada (Proxy)',
      });
    }
    candidates.push({
      apiBase: 'http://127.0.0.1:8080/api',
      healthUrl: 'http://127.0.0.1:8080/health',
      simRfidUrl: 'http://127.0.0.1:8080/api/sim-rfid',
      label: 'API Flask Conectada (8080)',
    });
    candidates.push({
      apiBase: 'http://127.0.0.1:5000/api',
      healthUrl: 'http://127.0.0.1:5000/',
      simRfidUrl: null,
      label: 'API Flask Direta (5000)',
    });

    for (const candidate of candidates) {
      const payload = await probeEndpoint(candidate.healthUrl, 1200);
      if (payload) {
        state.backendMode = 'api';
        state.apiBase = candidate.apiBase;
        state.simRfidUrl = candidate.simRfidUrl;
        state.backendLabel = candidate.label;
        updateConnectionIndicators();
        return true;
      }
    }

    state.backendMode = 'offline';
    state.apiBase = '';
    state.simRfidUrl = null;
    updateConnectionIndicators();
    return false;
  }

  async function apiRequest(path, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const fetchOpts = {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    };
    try {
      const res = await fetch(`${state.apiBase}${path}`, fetchOpts);
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok, status: res.status, data };
    } finally {
      clearTimeout(timer);
    }
  }

  // View navigation & session timer
  function switchView(viewId) {
    const panels = document.querySelectorAll('.view-panel');
    panels.forEach((panel) => {
      if (panel.id === viewId) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });
    state.currentView = viewId;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function syncDrawerShortcutStates() {
    const depOpen = Boolean($('modalDeposit')?.classList.contains('active'));
    const witOpen = Boolean($('modalWithdraw')?.classList.contains('active'));
    const depBtn = $('btnDepositConfirmDirect');
    const witBtn = $('btnWithdrawConfirmDirect');
    if (depBtn) depBtn.disabled = !depOpen;
    if (witBtn) witBtn.disabled = !witOpen;
  }

  function closeSimDrawer() {
    $('simDrawer')?.classList.remove('open');
    $('btnToggleSimDrawer')?.classList.remove('active');
  }

  function toggleSimDrawer() {
    const drawer = $('simDrawer');
    const toggle = $('btnToggleSimDrawer');
    if (!drawer) return;
    const isOpen = drawer.classList.toggle('open');
    if (toggle) toggle.classList.toggle('active', isOpen);
    syncDrawerShortcutStates();
  }

  function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.classList.remove('active');
    });
    disarmDeleteButton();
    showAlert($('depositErrorMsg'), '');
    showAlert($('withdrawErrorMsg'), '');
    showAlert($('updFeedbackMsg'), '');
    syncDrawerShortcutStates();
  }

  function stopInactivityTimer() {
    if (state.inactivityInterval) {
      clearInterval(state.inactivityInterval);
      state.inactivityInterval = null;
    }
  }

  function resetInactivityTimer() {
    state.inactivitySeconds = SESSION_TIMEOUT_SECONDS;
    const badge = $('logoutCountdown');
    if (badge) badge.textContent = `${state.inactivitySeconds}s`;
  }

  function startInactivityTimer() {
    stopInactivityTimer();
    resetInactivityTimer();
    state.inactivityInterval = setInterval(() => {
      if (!state.currentUser || state.currentView !== 'viewDashboard') {
        stopInactivityTimer();
        return;
      }
      state.inactivitySeconds -= 1;
      const badge = $('logoutCountdown');
      if (badge) badge.textContent = `${Math.max(0, state.inactivitySeconds)}s`;
      if (state.inactivitySeconds <= 0) {
        logout('Sessão encerrada automaticamente por inatividade.');
      }
    }, 1000);
  }

  function logout(reasonMessage = '') {
    stopInactivityTimer();
    closeModals();
    state.currentUser = null;
    state.pendingRfid = null;
    if ($('authPasswordInput')) $('authPasswordInput').value = '';
    switchView('viewStandby');
    if (reasonMessage) {
      showAlert($('standbyStatusBanner'), reasonMessage, 'info');
    } else {
      showAlert($('standbyStatusBanner'), '');
    }
  }

  // Standby & PIN Screen flows
  function openPinScreenForRfid(rfid) {
    const cleanRfid = String(rfid || '').trim();
    if (!cleanRfid) return;

    state.pendingRfid = cleanRfid;
    showAlert($('standbyStatusBanner'), '');
    showAlert($('pinErrorMsg'), '');

    const input = $('authPasswordInput');
    if (input) input.value = '';

    const rfidBadge = $('pinRfidBadge');
    if (rfidBadge) rfidBadge.textContent = `RFID: ${cleanRfid}`;

    const hint = SEEDED_TEST_HINTS[cleanRfid];
    const offlineMatch =
      state.backendMode === 'offline'
        ? getOfflineClients().find((c) => c.rfid === cleanRfid)
        : null;

    const greetingEl = $('pinGreeting');
    const avatarEl = $('pinUserAvatar');
    const fillBtn = $('btnFillTestPassword');
    const hintBox = $('pinHintBox');

    if (hint) {
      if (greetingEl) greetingEl.textContent = `Olá, ${hint.name}`;
      if (avatarEl) avatarEl.textContent = getInitials(hint.name);
      if (fillBtn) fillBtn.style.display = 'inline-flex';
      if (hintBox) {
        hintBox.textContent = `Cartão de teste identificado (${hint.name}). Digite a senha ou use o atalho abaixo.`;
      }
    } else if (offlineMatch) {
      if (greetingEl) greetingEl.textContent = `Olá, ${offlineMatch.name}`;
      if (avatarEl) avatarEl.textContent = getInitials(offlineMatch.name);
      if (fillBtn) fillBtn.style.display = 'none';
      if (hintBox) {
        hintBox.textContent = 'Cartão identificado localmente. Informe sua senha para entrar.';
      }
    } else {
      if (greetingEl) greetingEl.textContent = 'Cartão Identificado';
      if (avatarEl) avatarEl.textContent = 'NB';
      if (fillBtn) fillBtn.style.display = 'none';
      if (hintBox) {
        hintBox.textContent =
          'Se este cartão ainda não possui conta, clique em "Cartão sem conta? Cadastrar com este RFID".';
      }
    }

    switchView('viewPin');
    if (input) setTimeout(() => input.focus(), 60);
  }

  function enterPinDigit(digit) {
    const input = $('authPasswordInput');
    if (!input) return;
    if (input.value.length < 128) {
      input.value += String(digit);
      playTone(620, 0.04, 'sine');
    }
    input.focus();
  }

  function clearPin() {
    const input = $('authPasswordInput');
    if (input) {
      input.value = '';
      input.focus();
    }
    showAlert($('pinErrorMsg'), '');
  }

  function fillTestPassword() {
    if (!state.pendingRfid) return;
    const hint = SEEDED_TEST_HINTS[state.pendingRfid];
    if (!hint) return;
    const input = $('authPasswordInput');
    if (input) {
      input.value = hint.password;
      input.focus();
    }
    showAlert($('pinErrorMsg'), '');
  }

  async function submitPin() {
    if (state.isSubmitting) return;
    const rfid = state.pendingRfid;
    const password = $('authPasswordInput') ? $('authPasswordInput').value : '';
    const errEl = $('pinErrorMsg');

    if (!rfid || rfid.length < 8 || rfid.length > 15) {
      showAlert(errEl, 'RFID inválido (deve ter entre 8 e 15 caracteres).', 'error');
      return;
    }
    if (!password || password.length < 8 || password.length > 128) {
      showAlert(errEl, 'A senha deve conter entre 8 e 128 caracteres.', 'error');
      playErrorSound();
      return;
    }

    state.isSubmitting = true;
    const submitBtn = $('btnSubmitAuth');
    if (submitBtn) submitBtn.disabled = true;

    try {
      if (state.backendMode === 'api') {
        const res = await apiRequest('/auth', {
          method: 'POST',
          body: JSON.stringify({ rfid, password }),
        });
        if (!res.ok || !res.data.success) {
          const msg = res.data.message || 'Falha ao autenticar cartão e senha.';
          showAlert(errEl, msg, 'error');
          playErrorSound();
          return;
        }
        const user = normalizeClient(res.data.data);
        enterAuthenticatedDashboard(user, 'Autenticação via /api/auth');
      } else {
        const clients = getOfflineClients();
        const found = clients.find((c) => c.rfid === rfid);
        if (!found) {
          showAlert(errEl, 'Cliente não encontrado (modo offline).', 'error');
          playErrorSound();
          return;
        }
        if (found.password !== password) {
          showAlert(errEl, 'Senha incorreta.', 'error');
          playErrorSound();
          return;
        }
        enterAuthenticatedDashboard(normalizeClient(found), 'Autenticação Local');
      }
    } catch (_err) {
      showAlert(errEl, 'Erro de comunicação com o servidor Flask.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function enterAuthenticatedDashboard(user, originLabel) {
    state.currentUser = user;
    state.pendingRfid = null;
    if ($('authPasswordInput')) $('authPasswordInput').value = '';
    showAlert($('pinErrorMsg'), '');
    appendLedgerEntry(user.id, {
      description: 'Acesso ao Terminal',
      channel: originLabel,
      delta: 0,
      balanceAfter: user.balance,
    });
    renderDashboard();
    switchView('viewDashboard');
    startInactivityTimer();
    playSuccessSound();
  }

  // Registration screen flows
  function openRegisterView(prefillRfid = null) {
    showAlert($('regErrorMsg'), '');
    showAlert($('standbyStatusBanner'), '');
    const form = $('formRegister');
    if (form) form.reset();

    if (prefillRfid && prefillRfid.length >= 8 && prefillRfid.length <= 15) {
      setRegisterRfid(prefillRfid);
    } else {
      clearRegisterRfid();
    }

    switchView('viewRegister');
    if ($('regFullName')) {
      setTimeout(() => $('regFullName').focus(), 60);
    }
  }

  function setRegisterRfid(rfid) {
    state.regRfid = String(rfid || '').trim();
    const badge = $('regUidDisplay');
    const status = $('regScanStatus');
    const submit = $('btnSubmitRegister');
    if (badge) badge.textContent = `RFID: ${state.regRfid}`;
    if (status) status.textContent = 'Cartão vinculado com sucesso. Preencha os dados acima para concluir.';
    if (submit) submit.disabled = false;
  }

  function clearRegisterRfid() {
    state.regRfid = null;
    const badge = $('regUidDisplay');
    const status = $('regScanStatus');
    const submit = $('btnSubmitRegister');
    if (badge) badge.textContent = 'RFID: --';
    if (status) {
      status.textContent = 'Aproxime o cartão no sensor ou clique em um cartão novo na barra inferior.';
    }
    if (submit) submit.disabled = true;
  }

  async function completeRegistration() {
    if (state.isSubmitting) return;
    const errEl = $('regErrorMsg');
    showAlert(errEl, '');

    const name = ($('regFullName')?.value || '').trim();
    const cpfDigits = ($('regCpf')?.value || '').replace(/\D/g, '');
    const password = $('regPin')?.value || '';
    const passwordConfirm = $('regPinConfirm')?.value || '';
    const rfid = state.regRfid || '';

    if (name.length < 3 || name.length > 100) {
      showAlert(errEl, 'Nome deve ter entre 3 e 100 caracteres.', 'error');
      return;
    }
    if (!isValidCpf(cpfDigits)) {
      showAlert(errEl, 'CPF inválido. Informe 11 dígitos válidos ou use "Gerar CPF Válido".', 'error');
      return;
    }
    if (password.length < 8 || password.length > 128) {
      showAlert(errEl, 'A senha deve ter entre 8 e 128 caracteres.', 'error');
      return;
    }
    if (password !== passwordConfirm) {
      showAlert(errEl, 'A confirmação de senha não confere.', 'error');
      return;
    }
    if (rfid.length < 8 || rfid.length > 15) {
      showAlert(errEl, 'Vincule uma tag RFID válida (8 a 15 caracteres).', 'error');
      return;
    }

    state.isSubmitting = true;
    const submitBtn = $('btnSubmitRegister');
    if (submitBtn) submitBtn.disabled = true;

    try {
      if (state.backendMode === 'api') {
        const res = await apiRequest('/clients', {
          method: 'POST',
          body: JSON.stringify({ name, cpf: cpfDigits, password, rfid }),
        });
        if (!res.ok || !res.data.success) {
          showAlert(errEl, res.data.message || 'Não foi possível criar a conta.', 'error');
          playErrorSound();
          return;
        }
        const created = normalizeClient(res.data.data);
        appendLedgerEntry(created.id, {
          description: 'Abertura de Conta NovoBank',
          channel: 'POST /api/clients',
          delta: 0,
          balanceAfter: created.balance,
        });
        state.currentUser = created;
        renderDashboard();
        switchView('viewDashboard');
        startInactivityTimer();
        playSuccessSound();
      } else {
        const clients = getOfflineClients();
        if (clients.some((c) => c.cpf === cpfDigits)) {
          showAlert(errEl, 'CPF já cadastrado.', 'error');
          playErrorSound();
          return;
        }
        if (clients.some((c) => c.rfid === rfid)) {
          showAlert(errEl, 'Cartão RFID já cadastrado em outra conta.', 'error');
          playErrorSound();
          return;
        }
        const newId = `offline-${Date.now()}`;
        const newClient = {
          id: newId,
          name,
          cpf: cpfDigits,
          rfid,
          password,
          balance: 0.0,
        };
        clients.push(newClient);
        saveOfflineClients(clients);
        const created = normalizeClient(newClient);
        appendLedgerEntry(created.id, {
          description: 'Abertura de Conta (Offline)',
          channel: 'Simulador Local',
          delta: 0,
          balanceAfter: 0,
        });
        state.currentUser = created;
        renderDashboard();
        switchView('viewDashboard');
        startInactivityTimer();
        playSuccessSound();
      }
    } catch (_err) {
      showAlert(errEl, 'Erro de comunicação ao cadastrar cliente.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (submitBtn) submitBtn.disabled = !state.regRfid;
    }
  }

  // Dashboard rendering
  function renderBalance(balance) {
    const el = $('dashBalanceDisplay');
    if (!el) return;
    const numeric = Number(balance || 0);
    const formatted = numeric.toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    const [integerPart, centsPart] = formatted.split(',');
    el.innerHTML = `R$ ${integerPart}<span class="cents">,${centsPart || '00'}</span>`;
  }

  function renderLedger(accountId) {
    const tbody = $('ledgerTableBody');
    if (!tbody) return;
    const map = getLedgerMap();
    const rows = Array.isArray(map[accountId]) ? map[accountId] : [];
    tbody.innerHTML = '';

    if (rows.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 5;
      td.textContent = 'Nenhuma movimentação registrada nesta sessão.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement('tr');

      const tdDate = document.createElement('td');
      tdDate.textContent = row.timestamp;

      const tdDesc = document.createElement('td');
      tdDesc.textContent = row.description;

      const tdChan = document.createElement('td');
      tdChan.textContent = row.channel;

      const tdVal = document.createElement('td');
      tdVal.className = 'num-col';
      if (row.delta > 0) {
        tdVal.classList.add('amount-positive');
        tdVal.textContent = `+ ${formatCurrency(row.delta)}`;
      } else if (row.delta < 0) {
        tdVal.classList.add('amount-neutral');
        tdVal.textContent = `- ${formatCurrency(Math.abs(row.delta))}`;
      } else {
        tdVal.textContent = '--';
      }

      const tdBal = document.createElement('td');
      tdBal.className = 'num-col';
      tdBal.textContent = formatCurrency(row.balanceAfter);

      tr.append(tdDate, tdDesc, tdChan, tdVal, tdBal);
      tbody.appendChild(tr);
    });
  }

  function renderDashboard() {
    const user = state.currentUser;
    if (!user) return;
    if ($('dashAvatar')) $('dashAvatar').textContent = getInitials(user.name);
    if ($('dashCustomerName')) $('dashCustomerName').textContent = user.name;
    if ($('dashAccountNum')) {
      $('dashAccountNum').textContent =
        user.id.length > 13 ? `${user.id.slice(0, 8)}...` : user.id;
    }
    if ($('dashCpfDisplay')) $('dashCpfDisplay').textContent = formatCpf(user.cpf);
    if ($('dashUidDisplay')) $('dashUidDisplay').textContent = user.rfid;

    renderBalance(user.balance);
    renderLedger(user.id);
    updateConnectionIndicators();
  }

  // Deposit & Withdraw modal logic
  function openDepositModal() {
    if (!state.currentUser) return;
    resetInactivityTimer();
    state.selectedDepositAmount = 0;
    if ($('depositCustomAmount')) $('depositCustomAmount').value = '';
    document
      .querySelectorAll('#modalDeposit .preset-btn')
      .forEach((btn) => btn.classList.remove('selected'));
    showAlert($('depositErrorMsg'), '');
    $('modalDeposit')?.classList.add('active');
    syncDrawerShortcutStates();
  }

  function setDepositAmount(amount) {
    state.selectedDepositAmount = Number(amount);
    if ($('depositCustomAmount')) $('depositCustomAmount').value = String(amount);
    document.querySelectorAll('#modalDeposit .preset-btn').forEach((btn) => {
      const text = btn.textContent.replace(/\./g, '').replace(/[^\d]/g, '');
      btn.classList.toggle('selected', Number(text) === Number(amount));
    });
    showAlert($('depositErrorMsg'), '');
  }

  function getDepositValue() {
    const raw = $('depositCustomAmount')?.value || '';
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : state.selectedDepositAmount;
  }

  async function executeDeposit(verifiedRfid = null, channelLabel = 'Confirmacao no Terminal') {
    if (!state.currentUser || state.isSubmitting) return;
    resetInactivityTimer();
    const errEl = $('depositErrorMsg');
    showAlert(errEl, '');

    if (verifiedRfid && verifiedRfid !== state.currentUser.rfid) {
      showAlert(
        errEl,
        `Cartão RFID (${verifiedRfid}) não pertence a esta conta (${state.currentUser.rfid}).`,
        'error'
      );
      playErrorSound();
      return;
    }

    const amount = getDepositValue();
    if (!Number.isFinite(amount) || amount <= 0) {
      showAlert(errEl, 'Informe um valor de depósito maior que zero.', 'error');
      return;
    }
    if (amount > LIMITS.DEPOSIT_MAX) {
      showAlert(errEl, 'Limite máximo por depósito é R$ 1.000.000,00.', 'error');
      return;
    }

    state.isSubmitting = true;
    const btn = $('btnDepositConfirmDirect');
    if (btn) btn.disabled = true;

    try {
      let newBalance = state.currentUser.balance + amount;
      if (state.backendMode === 'api') {
        const res = await apiRequest(`/clients/${state.currentUser.id}/deposit`, {
          method: 'PATCH',
          body: JSON.stringify({ balance: amount }),
        });
        if (!res.ok || !res.data.success) {
          showAlert(errEl, res.data.message || 'Falha ao realizar depósito.', 'error');
          playErrorSound();
          return;
        }
        newBalance = Number(res.data.data?.balance ?? newBalance);
      } else {
        const clients = getOfflineClients();
        const target = clients.find((c) => c.id === state.currentUser.id);
        if (target) {
          target.balance = Number(target.balance || 0) + amount;
          newBalance = target.balance;
          saveOfflineClients(clients);
        }
      }

      state.currentUser.balance = newBalance;
      appendLedgerEntry(state.currentUser.id, {
        description: 'Depósito em Conta',
        channel: verifiedRfid ? `${channelLabel} (${verifiedRfid})` : channelLabel,
        delta: amount,
        balanceAfter: newBalance,
      });

      closeModals();
      renderDashboard();
      playSuccessSound();
    } catch (_err) {
      showAlert(errEl, 'Erro de conexão ao registrar depósito.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (btn) btn.disabled = false;
    }
  }

  function openWithdrawModal() {
    if (!state.currentUser) return;
    resetInactivityTimer();
    state.selectedWithdrawAmount = 0;
    if ($('withdrawCustomAmount')) $('withdrawCustomAmount').value = '';
    document
      .querySelectorAll('#modalWithdraw .preset-btn')
      .forEach((btn) => btn.classList.remove('selected'));
    showAlert($('withdrawErrorMsg'), '');
    $('modalWithdraw')?.classList.add('active');
    syncDrawerShortcutStates();
  }

  function setWithdrawAmount(amount) {
    state.selectedWithdrawAmount = Number(amount);
    if ($('withdrawCustomAmount')) $('withdrawCustomAmount').value = String(amount);
    document.querySelectorAll('#modalWithdraw .preset-btn').forEach((btn) => {
      const text = btn.textContent.replace(/\./g, '').replace(/[^\d]/g, '');
      btn.classList.toggle('selected', Number(text) === Number(amount));
    });
    showAlert($('withdrawErrorMsg'), '');
  }

  function getWithdrawValue() {
    const raw = $('withdrawCustomAmount')?.value || '';
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : state.selectedWithdrawAmount;
  }

  async function executeWithdrawal(verifiedRfid = null, channelLabel = 'Confirmacao no Terminal') {
    if (!state.currentUser || state.isSubmitting) return;
    resetInactivityTimer();
    const errEl = $('withdrawErrorMsg');
    showAlert(errEl, '');

    if (verifiedRfid && verifiedRfid !== state.currentUser.rfid) {
      showAlert(
        errEl,
        `Cartão RFID (${verifiedRfid}) não pertence a esta conta (${state.currentUser.rfid}).`,
        'error'
      );
      playErrorSound();
      return;
    }

    const amount = getWithdrawValue();
    if (!Number.isFinite(amount) || amount <= 0) {
      showAlert(errEl, 'Informe um valor de saque maior que zero.', 'error');
      return;
    }
    if (amount > LIMITS.WITHDRAW_MAX) {
      showAlert(errEl, 'Limite máximo por saque é R$ 10.000,00.', 'error');
      return;
    }
    if (amount > state.currentUser.balance) {
      showAlert(errEl, 'Saldo insuficiente para realizar este saque.', 'error');
      playErrorSound();
      return;
    }

    state.isSubmitting = true;
    const btn = $('btnWithdrawConfirmDirect');
    if (btn) btn.disabled = true;

    try {
      let newBalance = state.currentUser.balance - amount;
      if (state.backendMode === 'api') {
        const res = await apiRequest(`/clients/${state.currentUser.id}/withdraw`, {
          method: 'PATCH',
          body: JSON.stringify({ balance: amount }),
        });
        if (!res.ok || !res.data.success) {
          showAlert(errEl, res.data.message || 'Falha ao realizar saque.', 'error');
          playErrorSound();
          return;
        }
        newBalance = Number(res.data.data?.balance ?? newBalance);
      } else {
        const clients = getOfflineClients();
        const target = clients.find((c) => c.id === state.currentUser.id);
        if (target) {
          if (amount > Number(target.balance || 0)) {
            showAlert(errEl, 'Saldo insuficiente.', 'error');
            playErrorSound();
            return;
          }
          target.balance = Number(target.balance || 0) - amount;
          newBalance = target.balance;
          saveOfflineClients(clients);
        }
      }

      state.currentUser.balance = newBalance;
      appendLedgerEntry(state.currentUser.id, {
        description: 'Saque em Terminal',
        channel: verifiedRfid ? `${channelLabel} (${verifiedRfid})` : channelLabel,
        delta: -amount,
        balanceAfter: newBalance,
      });

      closeModals();
      renderDashboard();
      playSuccessSound();
    } catch (_err) {
      showAlert(errEl, 'Erro de conexão ao registrar saque.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (btn) btn.disabled = false;
    }
  }

  // Account info modal (GET / PATCH / DELETE)
  function populateInfoModalFields(user) {
    if (!user) return;
    if ($('infoCustomerName')) $('infoCustomerName').textContent = user.name;
    if ($('infoDoc')) $('infoDoc').textContent = formatCpf(user.cpf);
    if ($('infoAccountId')) $('infoAccountId').textContent = user.id;
    if ($('infoBalanceDisplay')) {
      $('infoBalanceDisplay').textContent = formatCurrency(user.balance);
    }
    if ($('infoCardUid')) $('infoCardUid').textContent = user.rfid;

    if ($('updName')) $('updName').value = user.name;
    if ($('updCpf')) $('updCpf').value = user.cpf;
    if ($('updRfid')) $('updRfid').value = user.rfid;
    if ($('updPassword')) $('updPassword').value = '';
  }

  async function openInfoModal() {
    if (!state.currentUser) return;
    resetInactivityTimer();
    disarmDeleteButton();
    showAlert($('updFeedbackMsg'), '');
    populateInfoModalFields(state.currentUser);
    $('modalInfo')?.classList.add('active');

    const syncStatusEl = $('infoSyncStatus');
    if (state.backendMode === 'api') {
      if (syncStatusEl) {
        syncStatusEl.textContent = 'Sincronizando dados com GET /api/clients/...';
      }
      try {
        const res = await apiRequest(`/clients/${state.currentUser.id}`, { method: 'GET' });
        if (res.ok && res.data.success && res.data.data) {
          state.currentUser = normalizeClient(res.data.data);
          populateInfoModalFields(state.currentUser);
          renderDashboard();
          if (syncStatusEl) {
            syncStatusEl.textContent = 'Dados sincronizados com GET /api/clients/<id>.';
          }
        } else if (syncStatusEl) {
          syncStatusEl.textContent = res.data.message || 'Exibindo dados em memória.';
        }
      } catch (_err) {
        if (syncStatusEl) {
          syncStatusEl.textContent = 'Falha ao consultar /api/clients/<id>; exibindo sessão local.';
        }
      }
    } else if (syncStatusEl) {
      syncStatusEl.textContent = 'Modo Offline: exibindo cadastro salvo em LocalStorage.';
    }
  }

  async function updateAccountInfo() {
    if (!state.currentUser || state.isSubmitting) return;
    resetInactivityTimer();
    const feedbackEl = $('updFeedbackMsg');
    showAlert(feedbackEl, '');

    const name = ($('updName')?.value || '').trim();
    const cpfDigits = ($('updCpf')?.value || '').replace(/\D/g, '');
    const rfid = ($('updRfid')?.value || '').trim();
    const passwordRaw = $('updPassword')?.value || '';

    if (name.length < 3 || name.length > 100) {
      showAlert(feedbackEl, 'Nome deve ter entre 3 e 100 caracteres.', 'error');
      return;
    }
    if (cpfDigits.length !== 11) {
      showAlert(feedbackEl, 'CPF deve conter exatamente 11 dígitos numéricos.', 'error');
      return;
    }
    if (!isValidCpf(cpfDigits)) {
      showAlert(
        feedbackEl,
        'CPF inválido segundo regra de validação do backend. Use 11 dígitos válidos.',
        'error'
      );
      return;
    }
    if (rfid.length < 8 || rfid.length > 15) {
      showAlert(feedbackEl, 'Tag RFID deve ter entre 8 e 15 caracteres.', 'error');
      return;
    }
    if (passwordRaw && (passwordRaw.length < 8 || passwordRaw.length > 128)) {
      showAlert(feedbackEl, 'A nova senha deve ter entre 8 e 128 caracteres.', 'error');
      return;
    }

    state.isSubmitting = true;
    const btn = $('btnSaveAccountUpdate');
    if (btn) btn.disabled = true;

    try {
      if (state.backendMode === 'api') {
        const res = await apiRequest(`/clients/${state.currentUser.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            name,
            cpf: cpfDigits,
            password: passwordRaw ? passwordRaw : null,
            rfid,
          }),
        });
        if (!res.ok || !res.data.success) {
          showAlert(feedbackEl, res.data.message || 'Falha ao atualizar conta.', 'error');
          playErrorSound();
          return;
        }
        state.currentUser = normalizeClient(res.data.data);
      } else {
        const clients = getOfflineClients();
        const duplicateCpf = clients.some(
          (c) => c.cpf === cpfDigits && c.id !== state.currentUser.id
        );
        const duplicateRfid = clients.some(
          (c) => c.rfid === rfid && c.id !== state.currentUser.id
        );
        if (duplicateCpf) {
          showAlert(feedbackEl, 'CPF já cadastrado em outra conta.', 'error');
          return;
        }
        if (duplicateRfid) {
          showAlert(feedbackEl, 'Cartão RFID já cadastrado em outra conta.', 'error');
          return;
        }
        const idx = clients.findIndex((c) => c.id === state.currentUser.id);
        if (idx >= 0) {
          clients[idx].name = name;
          clients[idx].cpf = cpfDigits;
          clients[idx].rfid = rfid;
          if (passwordRaw) clients[idx].password = passwordRaw;
          saveOfflineClients(clients);
          state.currentUser = normalizeClient(clients[idx]);
        }
      }

      populateInfoModalFields(state.currentUser);
      renderDashboard();
      appendLedgerEntry(state.currentUser.id, {
        description: 'Atualização Cadastral',
        channel: state.backendMode === 'api' ? 'PATCH /api/clients/<id>' : 'Modo Offline',
        delta: 0,
        balanceAfter: state.currentUser.balance,
      });
      renderLedger(state.currentUser.id);
      showAlert(feedbackEl, 'Dados atualizados com sucesso.', 'success');
      playSuccessSound();
    } catch (_err) {
      showAlert(feedbackEl, 'Erro de comunicação ao atualizar dados.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (btn) btn.disabled = false;
    }
  }

  function disarmDeleteButton() {
    state.deleteArmed = false;
    if (state.deleteArmTimer) {
      clearTimeout(state.deleteArmTimer);
      state.deleteArmTimer = null;
    }
    const delBtn = $('btnDeleteAccount');
    if (delBtn) delBtn.textContent = 'Excluir Conta';
  }

  async function handleDeleteAccountClick() {
    if (!state.currentUser || state.isSubmitting) return;
    resetInactivityTimer();
    const feedbackEl = $('updFeedbackMsg');
    const delBtn = $('btnDeleteAccount');

    if (!state.deleteArmed) {
      state.deleteArmed = true;
      if (delBtn) delBtn.textContent = 'Confirmar Exclusão Definitiva';
      showAlert(
        feedbackEl,
        'Clique novamente em "Confirmar Exclusão Definitiva" dentro de 5 segundos para remover esta conta.',
        'info'
      );
      state.deleteArmTimer = setTimeout(() => {
        disarmDeleteButton();
        showAlert(feedbackEl, '');
      }, 5000);
      return;
    }

    disarmDeleteButton();
    state.isSubmitting = true;
    if (delBtn) delBtn.disabled = true;

    try {
      const deletedName = state.currentUser.name;
      if (state.backendMode === 'api') {
        const res = await apiRequest(`/clients/${state.currentUser.id}`, {
          method: 'DELETE',
        });
        if (!res.ok || !res.data.success) {
          showAlert(feedbackEl, res.data.message || 'Falha ao excluir conta.', 'error');
          playErrorSound();
          return;
        }
      } else {
        const clients = getOfflineClients().filter((c) => c.id !== state.currentUser.id);
        saveOfflineClients(clients);
      }

      playSuccessSound();
      logout(`Conta de ${deletedName} excluída com sucesso.`);
    } catch (_err) {
      showAlert(feedbackEl, 'Erro de comunicação ao excluir conta.', 'error');
      playErrorSound();
    } finally {
      state.isSubmitting = false;
      if (delBtn) delBtn.disabled = false;
    }
  }

  // Physical RFID endpoint GET /api/rfid + Simulator coordination
  async function requestPhysicalRfidRead({ triggerBtn, alertEl, defaultLabel, onUid }) {
    if (state.isReadingRfid) return;

    if (state.backendMode !== 'api') {
      showAlert(
        alertEl,
        'API Flask desconectada. Clique em um cartão na barra "SIMULADOR RFID" abaixo para testar.',
        'info'
      );
      return;
    }

    state.isReadingRfid = true;
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.textContent = 'Aguardando cartão (15s)...';
    }
    pulseSensorGraphic();
    showAlert(
      alertEl,
      'Aproxime o cartão do leitor MFRC522 (ou clique em um cartão no simulador abaixo)...',
      'info'
    );

    try {
      const res = await apiRequest('/rfid', { method: 'GET' }, 17500);
      if (res.ok && res.data.success && res.data.data?.rfid) {
        const uid = String(res.data.data.rfid).trim();
        playTone(980, 0.08, 'sine');
        pulseSensorGraphic();
        showAlert(alertEl, '');
        onUid(uid);
      } else {
        showAlert(
          alertEl,
          res.data.message || 'Tempo esgotado aguardando cartão RFID no sensor.',
          'error'
        );
        playErrorSound();
      }
    } catch (_err) {
      showAlert(
        alertEl,
        'Não foi possível completar a leitura em /api/rfid (timeout ou desconexão).',
        'error'
      );
      playErrorSound();
    } finally {
      state.isReadingRfid = false;
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.textContent = defaultLabel;
      }
    }
  }

  async function pushSimulatedRfidToBridge(uid) {
    if (state.backendMode !== 'api' || !state.simRfidUrl) return false;
    try {
      const res = await fetch(state.simRfidUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rfid: uid }),
      });
      return res.ok;
    } catch (_err) {
      return false;
    }
  }

  function routeCardTap(uid) {
    const cleanUid = String(uid || '').trim();
    if (cleanUid.length < 8 || cleanUid.length > 15) {
      showAlert(
        $('standbyStatusBanner'),
        'O código RFID deve conter entre 8 e 15 caracteres.',
        'error'
      );
      return;
    }

    pulseSensorGraphic();
    playTone(980, 0.07, 'sine');

    if ($('modalDeposit')?.classList.contains('active')) {
      executeDeposit(cleanUid, 'RFID Simulado');
      return;
    }
    if ($('modalWithdraw')?.classList.contains('active')) {
      executeWithdrawal(cleanUid, 'RFID Simulado');
      return;
    }
    if (state.currentView === 'viewRegister') {
      setRegisterRfid(cleanUid);
      return;
    }
    if (state.currentView === 'viewDashboard' && state.currentUser) {
      // Do not interrupt active authenticated session unless user logs out
      return;
    }
    openPinScreenForRfid(cleanUid);
  }

  async function simulateCardTap(uid) {
    const cleanUid = String(uid || '').trim();
    if (cleanUid.length < 8 || cleanUid.length > 15) {
      showAlert(
        $('standbyStatusBanner'),
        'O código RFID deve conter entre 8 e 15 caracteres.',
        'error'
      );
      return;
    }

    closeSimDrawer();

    if (state.isReadingRfid && state.simRfidUrl) {
      const pushed = await pushSimulatedRfidToBridge(cleanUid);
      if (pushed) {
        return; // Blocking GET /api/rfid will receive this UID and route it
      }
    }

    routeCardTap(cleanUid);
  }

  function simulateCustomTap() {
    const input = $('customUidInput');
    const val = (input?.value || '').trim();
    if (val.length < 8 || val.length > 15) {
      showAlert(
        $('standbyStatusBanner'),
        'Digite um código RFID entre 8 e 15 caracteres no simulador.',
        'error'
      );
      if (input) input.focus();
      return;
    }
    simulateCardTap(val);
  }

  // Event bindings & Clock initialization
  function bindEvents() {
    $('btnReadPhysicalRfid')?.addEventListener('click', () => {
      requestPhysicalRfidRead({
        triggerBtn: $('btnReadPhysicalRfid'),
        alertEl: $('standbyStatusBanner'),
        defaultLabel: 'Ler Cartão no Sensor Físico',
        onUid: (uid) => openPinScreenForRfid(uid),
      });
    });

    $('btnGoToRegister')?.addEventListener('click', () => {
      openRegisterView(null);
    });

    $('btnToggleSimDrawer')?.addEventListener('click', (event) => {
      event.stopPropagation();
      toggleSimDrawer();
    });

    $('btnCloseSimDrawer')?.addEventListener('click', closeSimDrawer);

    $('btnFillTestPassword')?.addEventListener('click', () => {
      fillTestPassword();
      closeSimDrawer();
    });

    $('btnRegisterFromPin')?.addEventListener('click', () => {
      openRegisterView(state.pendingRfid);
    });

    $('btnCancelPin')?.addEventListener('click', () => {
      state.pendingRfid = null;
      if ($('authPasswordInput')) $('authPasswordInput').value = '';
      switchView('viewStandby');
    });

    $('btnGenerateValidCpf')?.addEventListener('click', () => {
      const cpfInput = $('regCpf');
      if (cpfInput) {
        cpfInput.value = generateValidCpf();
        cpfInput.focus();
      }
      showAlert($('regErrorMsg'), '');
    });

    $('btnReadRfidRegister')?.addEventListener('click', () => {
      requestPhysicalRfidRead({
        triggerBtn: $('btnReadRfidRegister'),
        alertEl: $('regErrorMsg'),
        defaultLabel: 'Ler no Sensor Físico (/api/rfid)',
        onUid: (uid) => setRegisterRfid(uid),
      });
    });

    $('btnCancelRegister')?.addEventListener('click', () => {
      clearRegisterRfid();
      switchView('viewStandby');
    });

    $('btnLogout')?.addEventListener('click', () => {
      logout('');
    });

    $('btnOpenDepositModal')?.addEventListener('click', openDepositModal);
    $('btnOpenWithdrawModal')?.addEventListener('click', openWithdrawModal);
    $('btnOpenInfoModal')?.addEventListener('click', openInfoModal);

    $('btnDepositConfirmDirect')?.addEventListener('click', () => {
      closeSimDrawer();
      executeDeposit(null, 'Terminal Web');
    });

    $('btnDepositReadRfid')?.addEventListener('click', () => {
      requestPhysicalRfidRead({
        triggerBtn: $('btnDepositReadRfid'),
        alertEl: $('depositErrorMsg'),
        defaultLabel: 'Ler Sensor Físico',
        onUid: (uid) => executeDeposit(uid, 'Sensor MFRC522'),
      });
    });

    $('btnWithdrawConfirmDirect')?.addEventListener('click', () => {
      closeSimDrawer();
      executeWithdrawal(null, 'Terminal Web');
    });

    $('btnWithdrawReadRfid')?.addEventListener('click', () => {
      requestPhysicalRfidRead({
        triggerBtn: $('btnWithdrawReadRfid'),
        alertEl: $('withdrawErrorMsg'),
        defaultLabel: 'Ler Sensor Físico',
        onUid: (uid) => executeWithdrawal(uid, 'Sensor MFRC522'),
      });
    });

    $('btnDeleteAccount')?.addEventListener('click', handleDeleteAccountClick);

    document.querySelectorAll('.modal-overlay').forEach((overlay) => {
      overlay.addEventListener('click', (event) => {
        if (event.target === overlay) {
          closeModals();
        }
      });
    });

    document.addEventListener('click', (event) => {
      const drawer = $('simDrawer');
      const toggle = $('btnToggleSimDrawer');
      if (
        drawer &&
        drawer.classList.contains('open') &&
        !drawer.contains(event.target) &&
        (!toggle || !toggle.contains(event.target))
      ) {
        closeSimDrawer();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeSimDrawer();
        closeModals();
      }
    });

    ['click', 'keydown', 'touchstart'].forEach((evt) => {
      document.addEventListener(
        evt,
        () => {
          if (state.currentUser && state.currentView === 'viewDashboard') {
            resetInactivityTimer();
          }
        },
        { passive: true }
      );
    });
  }

  function startClock() {
    const update = () => {
      const clock = $('terminalClock');
      if (clock) clock.textContent = nowFormattedTime();
    };
    update();
    setInterval(update, 1000);
  }

  window.novoBank = {
    submitPin,
    enterPinDigit,
    clearPin,
    completeRegistration,
    setDepositAmount,
    setWithdrawAmount,
    updateAccountInfo,
    closeModals,
    simulateCardTap,
    simulateCustomTap,
  };

  document.addEventListener('DOMContentLoaded', async () => {
    startClock();
    bindEvents();
    updateConnectionIndicators();
    await detectApiBackend();
    setInterval(() => {
      if (state.backendMode === 'offline') {
        detectApiBackend();
      }
    }, 10000);
  });
})();
