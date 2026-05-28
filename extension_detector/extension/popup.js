document.getElementById('scanButton').addEventListener('click', async () => {
  const resultDiv = document.getElementById('result');
  resultDiv.innerText = "Analyzing URL string...";
  resultDiv.className = "";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    resultDiv.innerText = "Error: Unable to fetch URL.";
    resultDiv.className = "unsafe";
    return;
  }

  if (tab.url.startsWith('chrome://') || tab.url.startsWith('about:')) {
    resultDiv.innerText = "System Page - Secure Domain";
    resultDiv.className = "safe";
    return;
  }

  chrome.runtime.sendMessage({
    action: "checkUrlSecurity",
    url: tab.url
  }, (response) => {
    if (!response || !response.success) {
      resultDiv.innerText = "API Pipeline Connection Offline.";
      resultDiv.className = "unsafe";
      return;
    }

    const report = response.data;
    if (report.status === "unsafe") {
      resultDiv.innerText = `🚨 PHISHING ALERT (${(report.probability * 100).toFixed(0)}%)`;
      resultDiv.className = "unsafe";
    } else {
      resultDiv.innerText = "✅ SECURE URL VERIFIED";
      resultDiv.className = "safe";
    }
  });
});