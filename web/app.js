// ==========================================================================
// AHA DRIVE ASTRAL ENGINE - CLIENT CONTROLLER (pywebview API Bridge)
// ==========================================================================

let activeTab = 'dashboard';
let telemetryInterval = null;
let currentUnionData = null;
let stage1HideTimer = null;
let stage1HandledDone = false;
let stage1Dismissed = false;

// Wait for pywebviewReady
window.addEventListener('pywebviewready', () => {
  console.log('pywebview is ready!');
  initApp();
});

// Fallback initialization if pywebview already fired or running
document.addEventListener('DOMContentLoaded', () => {
  setupTabNavigation();
  // If pywebview is already attached
  if (window.pywebview && window.pywebview.api) {
    initApp();
  } else {
    // Wait briefly for pywebview bridge injection
    setTimeout(() => {
      initApp();
    }, 400);
  }
});

function getApi() {
  if (window.pywebview && window.pywebview.api) {
    return window.pywebview.api;
  }
  return null;
}

function initApp() {
  loadDashboard();
  loadTransfers();
  startTelemetryLoop();
}

// ==================== TAB NAVIGATION ====================
function setupTabNavigation() {
  const navButtons = document.querySelectorAll('.nav-item');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-tab');
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  activeTab = tabId;

  // Update Nav Items
  document.querySelectorAll('.nav-item').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update Panes
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });

  const activePane = document.getElementById(`pane-${tabId}`);
  if (activePane) {
    activePane.classList.add('active');
  }

  // Trigger Tab Specific Loaders
  if (tabId === 'dashboard') loadDashboard();
  else if (tabId === 'transfers') loadTransfers();
  else if (tabId === 'accounts') loadAccounts();
  else if (tabId === 'union') loadUnion();
  else if (tabId === 'settings') loadSettings();
  else if (tabId === 'logs') loadLogs();
}

// ==================== TELEMETRY LOOP ====================
function startTelemetryLoop() {
  if (telemetryInterval) clearInterval(telemetryInterval);
  telemetryInterval = setInterval(() => {
    if (activeTab === 'dashboard') {
      loadDashboard(true);
    } else if (activeTab === 'transfers') {
      loadTransfers(true);
    }
  }, 1600);
}

// ==================== 1. DASHBOARD ====================
async function loadDashboard(silent = false) {
  const api = getApi();
  if (!api) return;

  try {
    const data = await api.get_dashboard_status();
    const heroCard = document.getElementById('mountHeroCard');
    const heroHeadline = document.getElementById('heroMountHeadline');
    const heroDesc = document.getElementById('heroMountDesc');
    const heroDot = document.getElementById('heroStatusDot');
    const btnToggle = document.getElementById('btnToggleMount');
    const lblToggle = document.getElementById('lblToggleMount');
    const btnExplorer = document.getElementById('btnOpenExplorer');
    const badgeMountState = document.getElementById('badgeMountState');
    const topBadge = document.getElementById('topStatusBadge');

    // Values
    document.getElementById('dashRemote').textContent = `${data.remote}:`;
    document.getElementById('dashLetter').textContent = `${data.drive_letter}\\`;
    document.getElementById('dashVolume').textContent = data.volume_name;
    if (document.getElementById('dashCacheUsedVal')) {
      document.getElementById('dashCacheUsedVal').textContent = data.cache_used;
    }
    if (document.getElementById('dashCachePath')) {
      document.getElementById('dashCachePath').textContent = data.cache_dir;
    }
    if (document.getElementById('dashCacheUsed')) {
      document.getElementById('dashCacheUsed').textContent = `${data.cache_dir} (${data.cache_used})`;
    }

    const diskFreeEl = document.getElementById('dashDiskFree');
    diskFreeEl.textContent = `${data.disk_free} ${data.disk_critical ? '⚠️ [KRITIS]' : '[AMAN]'}`;
    diskFreeEl.className = `t-val ${data.disk_critical ? 'badge-danger' : 'badge-safe'}`;

    document.getElementById('switchAutoStart').checked = data.auto_start;

    if (data.is_mounted) {
      heroCard.classList.add('mounted');
      heroDot.classList.add('online');
      badgeMountState.textContent = 'ONLINE';
      badgeMountState.className = 'badge-pill live-mount';
      topBadge.textContent = `● MOUNTED (${data.drive_letter})`;
      topBadge.className = 'status-indicator-badge live-pulse';

      heroHeadline.textContent = `STATUS: TERPASANG PADA DRIVE ${data.drive_letter} (${data.volume_name})`;
      heroDesc.textContent = 'Virtual drive Google Drive aktif dan siap digunakan di File Explorer Windows.';

      btnToggle.className = 'btn-danger-dark btn-large';
      lblToggle.textContent = '🛑 LEPAS (UNMOUNT) DRIVE';
      btnExplorer.disabled = false;
      btnExplorer.style.opacity = '1';
    } else {
      heroCard.classList.remove('mounted');
      heroDot.classList.remove('online');
      badgeMountState.textContent = 'DISMOUNTED';
      badgeMountState.className = 'badge-pill';
      topBadge.textContent = '○ DRIVE DISMOUNTED';
      topBadge.className = 'status-indicator-badge';
      topBadge.style.color = 'var(--text-muted)';

      heroHeadline.textContent = 'STATUS: TIDAK AKTIF (UNMOUNTED)';
      heroDesc.textContent = 'Virtual drive belum dipasang ke File Explorer.';

      btnToggle.className = 'btn-primary-gold btn-large';
      lblToggle.textContent = '⚡ PASANG (MOUNT) DRIVE';
      btnExplorer.disabled = true;
      btnExplorer.style.opacity = '0.5';
    }

    // Diagnostics
    const diagRclone = document.getElementById('diagRclone');
    if (diagRclone) {
      diagRclone.innerHTML = `<span class="diag-dot ${data.rclone_ready ? 'dot-green' : 'dot-red'}"></span><span class="diag-label">Rclone: ${data.rclone_ready ? 'Ready' : 'Missing'}</span>`;
    }
    const diagWinfsp = document.getElementById('diagWinfsp');
    if (diagWinfsp) {
      diagWinfsp.innerHTML = `<span class="diag-dot ${data.winfsp_ready ? 'dot-green' : 'dot-red'}"></span><span class="diag-label">WinFsp: ${data.winfsp_ready ? 'Mounted' : 'Missing'}</span>`;
    }

    // Mini Transfer Status
    const stats = await api.get_transfer_telemetry();
    const miniCard = document.getElementById('transferMiniCard');
    const miniTitle = document.getElementById('lblMiniTransferTitle');
    const miniDesc = document.getElementById('lblMiniTransferDesc');

    if (stats.is_uploading) {
      miniCard.classList.add('active-upload');
      const transferring = stats.transferring || [];
      const queued = stats.queued || [];
      miniTitle.textContent = `🚀 MENGUNGGAH: ${transferring.length} FILE AKTIF • ${queued.length} ANTREAN | ⚡ ${stats.speed_str}`;
      if (transferring.length > 0) {
        const first = transferring[0];
        miniDesc.textContent = `Mentransfer: ${first.name} (${first.percentage}%) • ${first.bytes_str}/${first.size_str}`;
      }
    } else {
      miniCard.classList.remove('active-upload');
      if (data.is_mounted) {
        miniTitle.textContent = 'STATUS SINKRONISASI: ● IDLE (SEMUA FILE TERSINKRON)';
        miniDesc.textContent = 'Semua data di cache lokal telah tersimpan rapi di Google Drive.';
      } else {
        miniTitle.textContent = 'STATUS SINKRONISASI: ○ DRIVE TIDAK AKTIF';
        miniDesc.textContent = 'Pasang virtual drive untuk memulai sinkronisasi otomatis.';
      }
    }

  } catch (err) {
    if (!silent) console.error('Dashboard error:', err);
  }
}

async function toggleMount() {
  const api = getApi();
  if (!api) return;

  const btnToggle = document.getElementById('btnToggleMount');
  btnToggle.disabled = true;
  btnToggle.style.opacity = '0.6';

  showToast('Memproses perintah Mount / Unmount...');
  try {
    const res = await api.toggle_mount();
    showToast(res.message);
  } catch (err) {
    showToast('Error: ' + err);
  } finally {
    setTimeout(() => {
      btnToggle.disabled = false;
      btnToggle.style.opacity = '1';
      loadDashboard();
    }, 1500);
  }
}

async function openExplorer() {
  const api = getApi();
  if (!api) return;
  await api.open_explorer();
}

async function toggleAutoStart(checked) {
  const api = getApi();
  if (!api) return;
  await api.toggle_autostart(checked);
  showToast(checked ? 'Auto-Start diaktifkan saat boot Windows.' : 'Auto-Start dimatikan.');
}

// ==================== 2. TRANSFERS ====================
async function loadTransfers(silent = false) {
  const api = getApi();
  if (!api) return;

  try {
    const stats = await api.get_transfer_telemetry();

    const mStatus = document.getElementById('mCardStatus');
    const mSpeed = document.getElementById('mCardSpeed');
    const mTotal = document.getElementById('mCardTotal');
    const mComp = document.getElementById('mCardCompleted');
    const navBadge = document.getElementById('navTransferBadge');

    const transferring = stats.transferring || [];
    const queued = stats.queued || [];

    if (!stats.is_connected) {
      mStatus.textContent = '○ MOUNT MATI';
      mStatus.style.color = 'var(--text-muted)';
      mSpeed.textContent = '0 B/s';
    } else if (stats.is_uploading) {
      mStatus.textContent = `🚀 UPLOAD (+${queued.length})`;
      mStatus.style.color = 'var(--gold-primary)';
      mSpeed.textContent = stats.speed_str;
    } else if (queued.length > 0) {
      mStatus.textContent = `⏳ ${queued.length} ANTREAN`;
      mStatus.style.color = 'var(--color-warning)';
      mSpeed.textContent = '0 B/s';
    } else {
      mStatus.textContent = '● IDLE (SINKRON)';
      mStatus.style.color = 'var(--color-success)';
      mSpeed.textContent = '0 B/s';
    }

    mTotal.textContent = stats.transferred_str || '0 B';
    mComp.textContent = `${stats.transfers_completed || 0} File`;

    // Nav Badge
    const totalActive = transferring.length + queued.length;
    if (totalActive > 0) {
      navBadge.style.display = 'inline-block';
      navBadge.textContent = totalActive;
    } else {
      navBadge.style.display = 'none';
    }

    // Stage 1 Local Buffer Progress
    const st1 = stats.stage1;
    const stage1Box = document.getElementById('stage1ProgressBox');
    const stage1CancelBtn = document.getElementById('stage1CancelBtn');
    const stage1Title = document.getElementById('stage1Title');
    const stage1BarFill = document.getElementById('stage1BarFill');

    if (stage1Box && st1) {
      if (st1.is_busy) {
        stage1HandledDone = false;
        stage1Dismissed = false;
        if (stage1HideTimer) {
          clearTimeout(stage1HideTimer);
          stage1HideTimer = null;
        }
        stage1Box.style.display = 'block';
        if (stage1CancelBtn) stage1CancelBtn.style.display = 'inline-flex';
        if (stage1Title) {
          stage1Title.textContent = `📥 Tahap 1: ${st1.current_file} (${st1.percentage}% • ${st1.copied_str}/${st1.total_str} • ${st1.speed_str})`;
        }
        if (stage1BarFill) {
          stage1BarFill.style.width = `${st1.percentage}%`;
        }
      } else if (st1.success === true) {
        if (!stage1Dismissed) {
          stage1Box.style.display = 'block';
          if (stage1CancelBtn) stage1CancelBtn.style.display = 'none';
          if (stage1Title) {
            stage1Title.textContent = `✅ ${st1.message} (Masuk antrean Google Drive)`;
          }
          if (stage1BarFill) {
            stage1BarFill.style.width = '100%';
          }
          if (!stage1HandledDone) {
            stage1HandledDone = true;
            if (stage1HideTimer) clearTimeout(stage1HideTimer);
            stage1HideTimer = setTimeout(() => {
              stage1Box.style.display = 'none';
              stage1Dismissed = true;
              if (api && api.ack_stage1_done) {
                api.ack_stage1_done().catch(() => { });
              }
            }, 3500);
          }
        }
      } else if (st1.success === false) {
        if (!stage1Dismissed) {
          stage1Box.style.display = 'block';
          if (stage1CancelBtn) stage1CancelBtn.style.display = 'none';
          if (stage1Title) {
            stage1Title.textContent = `⚠️ ${st1.message || 'Proses salin buffer dihentikan.'}`;
          }
          if (stage1BarFill) {
            stage1BarFill.style.width = '0%';
          }
          if (!stage1HandledDone) {
            stage1HandledDone = true;
            if (stage1HideTimer) clearTimeout(stage1HideTimer);
            stage1HideTimer = setTimeout(() => {
              stage1Box.style.display = 'none';
              stage1Dismissed = true;
              if (api && api.ack_stage1_done) {
                api.ack_stage1_done().catch(() => { });
              }
            }, 3500);
          }
        }
      } else {
        if (stage1Dismissed || !stage1HandledDone) {
          stage1Box.style.display = 'none';
        }
      }
    } else if (stage1Box) {
      stage1Box.style.display = 'none';
    }

    // Render Cloud Queue List
    const queueContainer = document.getElementById('cloudTransfersList');
    if (transferring.length === 0 && queued.length === 0) {
      queueContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">✨</div>
          <p>Semua file sudah tersinkronisasi sempurna!<br>Tidak ada antrean upload yang tertunda saat ini.</p>
        </div>
      `;
    } else {
      let html = '';
      // Active Uploading Items
      transferring.forEach(item => {
        html += `
          <div class="cloud-item-card active">
            <div class="cloud-item-top">
              <div class="cloud-item-title-col">
                <span class="chip-status chip-active">⚡ AKTIF UPLOAD</span>
                <span class="cloud-item-name">📁 ${escapeHtml(item.name)}</span>
              </div>
              <span class="cloud-item-pct">${item.percentage}%</span>
            </div>
            <div class="progress-bar-shell">
              <div class="progress-bar-fill" style="width: ${item.percentage}%;"></div>
            </div>
            <div class="cloud-item-sub">
              <span>📦 ${item.bytes_str} / ${item.size_str} &nbsp;•&nbsp; ⚡ ${item.speed_str} &nbsp;•&nbsp; ⏳ ETA: ${item.eta_str}</span>
              <button class="btn-cancel-small" onclick="cancelCloudFile('${escapeJs(item.name)}')">❌ BATALKAN & PURGE</button>
            </div>
          </div>
        `;
      });

      // Queued Items
      queued.forEach((item, idx) => {
        html += `
          <div class="cloud-item-card">
            <div class="cloud-item-top">
              <div class="cloud-item-title-col">
                <span class="chip-status chip-queue">#${idx + 1}</span>
                <span class="cloud-item-name">📄 ${escapeHtml(item.name)}</span>
              </div>
              <span class="cloud-item-sub">📦 ${item.size_str} &nbsp;•&nbsp; ⏳ Menunggu Giliran</span>
              <button class="btn-cancel-small" onclick="cancelCloudFile('${escapeJs(item.name)}')">❌ BATALKAN</button>
            </div>
          </div>
        `;
      });

      queueContainer.innerHTML = html;
    }

  } catch (err) {
    if (!silent) console.error('Transfer load error:', err);
  }
}

async function selectAndUploadFiles() {
  const api = getApi();
  if (!api) return;
  const files = await api.pick_files();
  if (files && files.length > 0) {
    stage1HandledDone = false;
    stage1Dismissed = false;
    if (stage1HideTimer) {
      clearTimeout(stage1HideTimer);
      stage1HideTimer = null;
    }
    const target = document.getElementById('transferTargetPath').textContent;
    showToast(`Memulai upload ${files.length} file...`);
    const res = await api.start_upload(files, target);
    if (!res.ok) showToast(res.message);
  }
}

async function selectAndUploadFolder() {
  const api = getApi();
  if (!api) return;
  const folder = await api.pick_folder();
  if (folder) {
    stage1HandledDone = false;
    stage1Dismissed = false;
    if (stage1HideTimer) {
      clearTimeout(stage1HideTimer);
      stage1HideTimer = null;
    }
    const target = document.getElementById('transferTargetPath').textContent;
    showToast(`Memulai upload folder...`);
    const res = await api.start_upload([folder], target);
    if (!res.ok) showToast(res.message);
  }
}

async function pickTargetSubfolder() {
  const api = getApi();
  if (!api) return;
  const folder = await api.pick_folder();
  if (folder) {
    document.getElementById('transferTargetPath').textContent = folder;
  }
}

function resetTargetFolder() {
  const api = getApi();
  if (!api) return;
  api.get_dashboard_status().then(d => {
    document.getElementById('transferTargetPath').textContent = `${d.drive_letter}\\`;
  });
}

async function cancelStage1() {
  const api = getApi();
  if (!api) return;
  stage1HandledDone = false;
  stage1Dismissed = false;
  if (stage1HideTimer) {
    clearTimeout(stage1HideTimer);
    stage1HideTimer = null;
  }
  await api.cancel_stage1_upload();
  showToast('Proses salin buffer dibatalkan.');
}

async function cancelCloudFile(fileName) {
  if (!confirm(`Batalkan upload dan purge cache untuk '${fileName}'?`)) return;
  const api = getApi();
  if (!api) return;
  await api.cancel_cloud_file(fileName);
  showToast(`File '${fileName}' dibatalkan.`);
}

// ==================== 3. ACCOUNTS ====================
async function loadAccounts() {
  const api = getApi();
  if (!api) return;

  const grid = document.getElementById('accountsGrid');
  grid.innerHTML = '<div class="loading-state">Memeriksa kuota dan status akun...</div>';

  try {
    const remotes = await api.get_accounts_list();
    if (!remotes || remotes.length === 0) {
      grid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">👥</div>
          <p>Belum ada akun Google Drive yang terdaftar.<br>Klik tombol <strong>➕ TAMBAH AKUN BARU</strong> di atas untuk memulai.</p>
        </div>
      `;
      return;
    }

    const quotas = await api.check_all_quotas();
    let html = '';

    remotes.forEach(r => {
      const q = quotas[r] || { ok: false, error: 'Memeriksa...' };
      const ok = q.ok;

      html += `
        <div class="account-card">
          <div class="acc-header">
            <div class="acc-name-box">
              <span class="acc-tag">[ GDRIVE ]</span>
              <span class="acc-name">${escapeHtml(r)}</span>
            </div>
            <span class="status-dot ${ok ? 'dot-green' : 'dot-red'}"></span>
          </div>

          <div class="acc-quota-meter">
            ${ok ? `
              <div class="quota-label-row">
                <span>Terpakai: ${q.used} / ${q.total}</span>
                <span>${q.used_percent}%</span>
              </div>
              <div class="progress-bar-shell">
                <div class="progress-bar-fill" style="width: ${q.used_percent}%;"></div>
              </div>
              <div class="quota-label-row">
                <span>Sisa Ruang: <strong>${q.free}</strong></span>
              </div>
            ` : `
              <div class="quota-label-row">
                <span style="color: var(--color-danger);">⚠️ ${escapeHtml(q.error || 'Token Expired')}</span>
              </div>
            `}
          </div>

          <div class="acc-actions">
            <button class="btn-outline-gold" onclick="reconnectAccount('${escapeJs(r)}')">🔑 LOGIN ULANG</button>
            <button class="btn-danger-dark" onclick="deleteAccount('${escapeJs(r)}')">🗑️ HAPUS</button>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Error memuat akun: ${err}</div>`;
  }
}

async function checkAllQuotas() {
  showToast('Memeriksa kuota seluruh akun...');
  await loadAccounts();
}

function openAddAccountModal() {
  document.getElementById('inputNewAccountName').value = '';
  document.getElementById('addAccountModal').style.display = 'flex';
}

function closeAddAccountModal() {
  document.getElementById('addAccountModal').style.display = 'none';
}

async function submitAddAccount() {
  const name = document.getElementById('inputNewAccountName').value.trim();
  if (!name) {
    alert('Masukkan nama alias akun terlebih dahulu.');
    return;
  }

  const api = getApi();
  if (!api) return;

  closeAddAccountModal();
  showToast(`Membuka browser untuk otentikasi '${name}'...`);
  const res = await api.add_account(name);
  showToast(res.message);

  setTimeout(loadAccounts, 3000);
}

async function reconnectAccount(name) {
  const api = getApi();
  if (!api) return;
  showToast(`Membuka browser login ulang untuk '${name}'...`);
  const res = await api.reconnect_account(name);
  showToast(res.message);
}

async function deleteAccount(name) {
  if (!confirm(`Apakah Anda yakin ingin menghapus akun '${name}' dari Rclone?`)) return;
  const api = getApi();
  if (!api) return;
  await api.delete_account(name);
  showToast(`Akun '${name}' berhasil dihapus.`);
  loadAccounts();
}

// ==================== 4. UNION POOL ====================
async function loadUnion() {
  const api = getApi();
  if (!api) return;

  try {
    const data = await api.get_union_data();
    currentUnionData = data;

    document.getElementById('inputUnionName').value = data.union_name || 'Gdrive_union';
    document.getElementById('selectUnionPolicy').value = data.policy || 'epmfs';
    updatePolicyDesc(data.policy || 'epmfs');

    renderUnionAccountsList();
  } catch (err) {
    console.error('Union error:', err);
  }
}

function renderUnionAccountsList() {
  const container = document.getElementById('unionAccountsList');
  if (!currentUnionData || !currentUnionData.all_accounts || currentUnionData.all_accounts.length === 0) {
    container.innerHTML = '<div class="empty-state">Tidak ada akun Google Drive yang tersedia.</div>';
    return;
  }

  // Combine upstreams order
  const ordered = [];
  currentUnionData.upstreams.forEach(acc => {
    if (currentUnionData.all_accounts.includes(acc) && !ordered.includes(acc)) {
      ordered.push({ name: acc, checked: true });
    }
  });

  currentUnionData.all_accounts.forEach(acc => {
    if (!ordered.some(o => o.name === acc)) {
      ordered.push({ name: acc, checked: currentUnionData.upstreams.length === 0 });
    }
  });

  currentUnionData._orderedList = ordered;

  let html = '';
  ordered.forEach((item, idx) => {
    html += `
      <div class="union-account-row">
        <div class="union-acc-left">
          <span class="priority-badge">#${idx + 1}</span>
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
            <input type="checkbox" ${item.checked ? 'checked' : ''} onchange="toggleUnionCheck(${idx}, this.checked)">
            <span style="font-weight:700; font-size:14px;">📁 ${escapeHtml(item.name)}</span>
          </label>
        </div>
        <div class="union-acc-actions">
          <button class="btn-subtle" onclick="moveUnionOrder(${idx}, -1)" ${idx === 0 ? 'disabled' : ''}>⬆️</button>
          <button class="btn-subtle" onclick="moveUnionOrder(${idx}, 1)" ${idx === ordered.length - 1 ? 'disabled' : ''}>⬇️</button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function toggleUnionCheck(idx, checked) {
  if (currentUnionData && currentUnionData._orderedList) {
    currentUnionData._orderedList[idx].checked = checked;
  }
}

function moveUnionOrder(idx, dir) {
  const list = currentUnionData._orderedList;
  const newIdx = idx + dir;
  if (newIdx >= 0 && newIdx < list.length) {
    const temp = list[idx];
    list[idx] = list[newIdx];
    list[newIdx] = temp;
    renderUnionAccountsList();
  }
}

function updatePolicyDesc(val) {
  const box = document.getElementById('policyDescBox');
  if (val === 'epmfs') {
    box.innerHTML = '💡 <strong>Rekomendasi Resmi (epmfs):</strong> File baru otomatis dialihkan ke akun yang memiliki sisa kuota paling besar (kapasitas terbagi seimbang & aman).';
  } else if (val === 'epff') {
    box.innerHTML = '💡 <strong>First Found (epff):</strong> File baru dialihkan ke akun yang merespons koneksi tercepat saat pembuatan file.';
  } else if (val === 'eplfs') {
    box.innerHTML = '💡 <strong>Least Free Space (eplfs):</strong> File baru dialihkan ke akun yang sisa kuotanya paling sedikit untuk dihabiskan terlebih dahulu.';
  }
}

async function saveUnion() {
  const api = getApi();
  if (!api || !currentUnionData || !currentUnionData._orderedList) return;

  const unionName = document.getElementById('inputUnionName').value.trim() || 'Gdrive_union';
  const policy = document.getElementById('selectUnionPolicy').value;
  const selected = currentUnionData._orderedList.filter(o => o.checked).map(o => o.name);

  if (selected.length === 0) {
    alert('Pilih minimal 1 akun untuk digabung ke Union!');
    return;
  }

  showToast('Menyimpan konfigurasi Union...');
  const res = await api.save_union_config(unionName, selected, policy);
  const msgEl = document.getElementById('unionStatusMsg');
  if (res.ok) {
    msgEl.textContent = `✅ ${res.message}`;
    msgEl.style.color = 'var(--color-success)';
    showToast(res.message);
  } else {
    msgEl.textContent = `❌ ${res.message}`;
    msgEl.style.color = 'var(--color-danger)';
    showToast(res.message);
  }
}

async function testUnion() {
  const api = getApi();
  if (!api) return;

  const unionName = document.getElementById('inputUnionName').value.trim() || 'Gdrive_union';
  const msgEl = document.getElementById('unionStatusMsg');
  msgEl.textContent = '⏳ Memverifikasi koneksi union ke Google...';
  msgEl.style.color = 'var(--color-warning)';

  const res = await api.test_union_health(unionName);
  if (res.ok) {
    msgEl.textContent = `✅ ${res.message}`;
    msgEl.style.color = 'var(--color-success)';
  } else {
    msgEl.textContent = `❌ ${res.message}`;
    msgEl.style.color = 'var(--color-danger)';
  }
}

// ==================== 5. SETTINGS ====================
async function loadSettings() {
  const api = getApi();
  if (!api) return;

  try {
    const s = await api.get_settings();
    const sel = document.getElementById('settingDriveLetter');
    sel.innerHTML = '';
    s.available_letters.forEach(ltr => {
      const opt = document.createElement('option');
      opt.value = ltr;
      opt.textContent = `${ltr}:`;
      if (ltr === s.drive_letter) opt.selected = true;
      sel.appendChild(opt);
    });

    document.getElementById('settingVolumeName').value = s.volume_name;
    document.getElementById('settingCacheDir').value = s.cache_dir;
    document.getElementById('settingCacheSize').value = s.cache_max_size;
    document.getElementById('settingCacheAge').value = s.cache_max_age;

    document.getElementById('settingCacheUsageText').textContent = `Penggunaan Cache Saat Ini: ${s.cache_used} (Batas VFS: ${s.cache_max_size})`;

    const gauge = document.getElementById('settingDiskGauge');
    if (s.disk_free_gb < 5.0) {
      gauge.textContent = `⚠️ Sisa ruang disk cache: ${s.disk_free} / ${s.disk_total} [KRITIS - Alihkan ke drive lain]`;
      gauge.style.color = 'var(--color-danger)';
    } else {
      gauge.textContent = `✅ Sisa ruang disk cache: ${s.disk_free} / ${s.disk_total} [AMAN]`;
      gauge.style.color = 'var(--color-success)';
    }

  } catch (err) {
    console.error('Settings error:', err);
  }
}

async function browseCacheFolder() {
  const api = getApi();
  if (!api) return;
  const folder = await api.browse_cache_folder();
  if (folder) {
    document.getElementById('settingCacheDir').value = folder;
  }
}

async function openCurrentCacheFolder() {
  const api = getApi();
  if (!api) return;
  const path = document.getElementById('settingCacheDir').value.trim();
  await api.open_folder(path);
}

async function refreshSettingsCache() {
  await loadSettings();
  showToast('Ukuran cache diperbarui.');
}

async function saveSettings() {
  const api = getApi();
  if (!api) return;

  const payload = {
    drive_letter: document.getElementById('settingDriveLetter').value,
    volume_name: document.getElementById('settingVolumeName').value,
    cache_dir: document.getElementById('settingCacheDir').value,
    cache_max_size: document.getElementById('settingCacheSize').value,
    cache_max_age: document.getElementById('settingCacheAge').value
  };

  const res = await api.save_settings(payload);
  const statusEl = document.getElementById('settingsSaveStatus');
  if (res.ok) {
    statusEl.textContent = '✅ Pengaturan berhasil disimpan!';
    showToast(res.message);
    setTimeout(() => { statusEl.textContent = ''; }, 3000);
  }
}

// ==================== 6. LOGS ====================
async function loadLogs() {
  const api = getApi();
  if (!api) return;

  try {
    const logs = await api.get_logs();
    const body = document.getElementById('terminalLogBody');
    body.textContent = logs || 'Belum ada log tercatat.';
    body.scrollTop = body.scrollHeight;
  } catch (err) {
    console.error('Logs error:', err);
  }
}

async function refreshLogs() {
  await loadLogs();
  showToast('Log diperbarui.');
}

async function clearLogs() {
  if (!confirm('Bersihkan seluruh log kernel?')) return;
  const api = getApi();
  if (!api) return;
  await api.clear_logs();
  await loadLogs();
  showToast('File log dibersihkan.');
}

async function openLogFolder() {
  const api = getApi();
  if (!api) return;
  await api.open_log_folder();
}

// ==================== HELPERS ====================
function showToast(msg) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  })[m]);
}

function escapeJs(str) {
  if (!str) return '';
  return str.replace(/['"\\]/g, '\\$&');
}
