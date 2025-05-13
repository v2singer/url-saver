document.addEventListener('DOMContentLoaded', function() {
  const serverList = document.getElementById('serverList');
  const addServerBtn = document.getElementById('addServer');
  const saveSettingsBtn = document.getElementById('saveSettings');
  const statusDiv = document.getElementById('status');

  // 加载保存的服务器列表
  chrome.storage.sync.get(['serverUrls'], function(result) {
    const serverUrls = result.serverUrls || ['http://localhost:8080'];
    renderServerList(serverUrls);
  });

  // 添加新服务器输入框
  addServerBtn.addEventListener('click', function() {
    const serverItem = document.createElement('div');
    serverItem.className = 'server-item';
    serverItem.innerHTML = `
      <input type="text" placeholder="Enter server URL (e.g., http://localhost:8080)" value="http://localhost:8080">
      <button class="remove-server">Remove</button>
    `;
    serverList.appendChild(serverItem);

    // 添加删除按钮事件
    serverItem.querySelector('.remove-server').addEventListener('click', function() {
      serverItem.remove();
    });
  });

  // 保存设置
  saveSettingsBtn.addEventListener('click', function() {
    const inputs = serverList.querySelectorAll('input');
    const serverUrls = Array.from(inputs).map(input => input.value.trim()).filter(url => url);

    if (serverUrls.length === 0) {
      showStatus('Please add at least one server URL', 'error');
      return;
    }

    // 验证所有URL
    validateUrls(serverUrls).then(validUrls => {
      if (validUrls.length === 0) {
        showStatus('No valid server URLs found', 'error');
        return;
      }

      // 保存到Chrome存储
      chrome.storage.sync.set({ serverUrls: validUrls }, function() {
        showStatus('Settings saved successfully!', 'success');
      });
    });
  });

  // 渲染服务器列表
  function renderServerList(serverUrls) {
    serverList.innerHTML = '';
    serverUrls.forEach(url => {
      const serverItem = document.createElement('div');
      serverItem.className = 'server-item';
      serverItem.innerHTML = `
        <input type="text" placeholder="Enter server URL" value="${url}">
        <button class="remove-server">Remove</button>
      `;
      serverList.appendChild(serverItem);

      // 添加删除按钮事件
      serverItem.querySelector('.remove-server').addEventListener('click', function() {
        serverItem.remove();
      });
    });
  }

  // 验证URL是否可访问
  async function validateUrls(urls) {
    const validUrls = [];
    for (const url of urls) {
      try {
        const response = await fetch(`${url}/extension/urls`, { method: 'HEAD' });
        if (response.ok) {
          validUrls.push(url);
        }
      } catch (error) {
        console.error(`Failed to validate URL ${url}:`, error);
      }
    }
    return validUrls;
  }

  // 显示状态信息
  function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 3000);
  }
}); 