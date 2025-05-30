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

document.addEventListener('DOMContentLoaded', function() {
  // 获取当前标签页的URL和标题
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    const currentUrl = tabs[0].url;
    const currentTitle = tabs[0].title;
    document.getElementById('current-url').textContent = currentUrl;
    document.getElementById('current-title').textContent = currentTitle;
    
    // 获取服务器地址列表并校验后获取建议标签
    chrome.storage.sync.get(['serverUrls'], async function(result) {
      const serverUrls = result.serverUrls || ['http://localhost:8080'];
      const validUrls = await validateUrls(serverUrls);
      if (validUrls.length > 0) {
        getSuggestedTags(currentTitle, currentUrl, validUrls[0]);
      } else {
        const suggestedTagsContainer = document.getElementById('suggested-tags');
        suggestedTagsContainer.innerHTML = '<div class="error">No available server for suggestions</div>';
      }
    });
  });

  // 打开配置页面按钮点击事件
  document.getElementById('openOptions').addEventListener('click', function() {
    chrome.runtime.openOptionsPage();
  });

  // 保存按钮点击事件
  document.getElementById('save').addEventListener('click', function() {
    const tags = document.getElementById('tags').value;
    const notes = document.getElementById('notes').value;
    const statusDiv = document.getElementById('status');

    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      const currentUrl = tabs[0].url;
      const currentTitle = tabs[0].title;
      const data = {
        url: currentUrl,
        title: currentTitle,
        tags: tags.split(',').map(tag => tag.trim()).filter(tag => tag),
        notes: notes
      };

      // 获取服务器地址列表并校验后尝试保存
      chrome.storage.sync.get(['serverUrls'], async function(result) {
        const serverUrls = result.serverUrls || ['http://localhost:8080'];
        const validUrls = await validateUrls(serverUrls);
        if (validUrls.length > 0) {
          saveToServer([validUrls[0]], data, statusDiv);
        } else {
          statusDiv.textContent = 'No available server to save URL.';
          statusDiv.style.color = '#f44336';
        }
      });
    });
  });

  // 显示最近URL列表按钮点击事件
  document.getElementById('show-list').addEventListener('click', function() {
    const urlList = document.getElementById('url-list');
    const urlListContent = document.getElementById('url-list-content');
    const statusDiv = document.getElementById('status');

    // 切换显示状态
    if (urlList.style.display === 'none') {
      // 获取服务器地址列表并尝试获取URL列表
      chrome.storage.sync.get(['serverUrls'], function(result) {
        const serverUrls = result.serverUrls || ['http://localhost:8080'];
        fetchUrlsFromServer(serverUrls, urlList, urlListContent, statusDiv);
      });
    } else {
      urlList.style.display = 'none';
    }
  });
});

// 获取建议标签，增加 serverUrl 参数
async function getSuggestedTags(title, url, serverUrl) {
  const suggestedTagsContainer = document.getElementById('suggested-tags');
  suggestedTagsContainer.innerHTML = '<div class="loading">Loading suggestions...</div>';

  try {
    const response = await fetch(`${serverUrl}/extension/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, url })
    });

    if (response.ok) {
      const data = await response.json();
      suggestedTagsContainer.innerHTML = '';
      
      data.suggestions.forEach(tag => {
        const tagElement = document.createElement('div');
        tagElement.className = 'suggested-tag';
        tagElement.textContent = tag;
        tagElement.addEventListener('click', () => {
          const tagsInput = document.getElementById('tags');
          const currentTags = tagsInput.value ? tagsInput.value.split(',').map(t => t.trim()) : [];
          
          if (!currentTags.includes(tag)) {
            currentTags.push(tag);
            tagsInput.value = currentTags.join(', ');
          }
          
          tagElement.classList.toggle('selected');
        });
        suggestedTagsContainer.appendChild(tagElement);
      });
    } else {
      suggestedTagsContainer.innerHTML = '<div class="error">Failed to load suggestions</div>';
    }
  } catch (error) {
    console.error('Error fetching suggestions:', error);
    suggestedTagsContainer.innerHTML = '<div class="error">Failed to load suggestions</div>';
  }
}

// 尝试保存到服务器，如果失败则尝试下一个服务器
async function saveToServer(serverUrls, data, statusDiv) {
  for (const serverUrl of serverUrls) {
    try {
      const response = await fetch(`${serverUrl}/extension/urls`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        const result = await response.json();
        statusDiv.textContent = 'URL saved successfully!';
        statusDiv.style.color = '#4CAF50';
        // 清空输入框
        document.getElementById('tags').value = '';
        document.getElementById('notes').value = '';
        return;
      }
    } catch (error) {
      console.error(`Failed to save to ${serverUrl}:`, error);
      continue;
    }
  }

  // 如果所有服务器都失败
  statusDiv.textContent = 'Error saving URL. All servers are unavailable.';
  statusDiv.style.color = '#f44336';
}

// 尝试从服务器获取URL列表，如果失败则尝试下一个服务器
async function fetchUrlsFromServer(serverUrls, urlList, urlListContent, statusDiv) {
  let lastError = null;
  
  for (const serverUrl of serverUrls) {
    try {
      const response = await fetch(`${serverUrl}/extension/urls`);
      if (response.ok) {
        const urls = await response.json();
        urlListContent.innerHTML = ''; // 清空现有内容
        
        if (urls.length === 0) {
          urlListContent.innerHTML = '<p>No saved URLs yet.</p>';
        } else {
          urls.forEach(url => {
            const urlItem = document.createElement('div');
            urlItem.className = 'url-item';
            urlItem.innerHTML = `
              <div class="title">${url.title || 'No title'}</div>
              <div class="url">
                <a href="${url.url}" target="_blank" title="Open in new tab">${url.url}</a>
              </div>
              <div class="tags">Tags: ${url.tags.join(', ') || 'No tags'}</div>
              <div class="notes">${url.notes || 'No notes'}</div>
              <div class="date">${new Date(url.created_at).toLocaleString()}</div>
            `;
            urlListContent.appendChild(urlItem);
          });
        }
        
        urlList.style.display = 'block';
        statusDiv.textContent = '';
        return;
      } else {
        // 处理非200响应
        lastError = new Error(`Server ${serverUrl} returned status ${response.status}`);
        console.error(`Server ${serverUrl} returned status ${response.status}`);
        continue;
      }
    } catch (error) {
      lastError = error;
      console.error(`Failed to fetch from ${serverUrl}:`, error);
      continue;
    }
  }

  // 如果所有服务器都失败
  urlList.style.display = 'none';
  statusDiv.textContent = `Error loading URLs: ${lastError?.message || 'All servers are unavailable'}`;
  statusDiv.style.color = '#f44336';
} 